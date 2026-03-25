"""
RLS tenant-isolation tests for the flexible experiment engine (migration 0041).

These tests verify that the client-scoped RLS policies applied by migration 0041
actually enforce tenant boundaries at the database layer:

    is_admin() OR (
        has_experiment_access() AND
        created_by IN (
            SELECT u.id FROM users u
            WHERE u.client_id = (
                SELECT u2.client_id FROM users u2
                WHERE u2.id = current_user_id()
            )
        )
    )

Critical setup requirements:
  1. migrated_engine (not db_engine) — runs the real Alembic chain so RLS policies,
     SECURITY DEFINER functions, and FORCE ROW LEVEL SECURITY are all present.
  2. SET ROLE app_test_role before querying — PostgreSQL superusers bypass RLS even
     with FORCE ROW LEVEL SECURITY. Only non-superuser roles feel RLS enforcement.
  3. SET app.current_user_id — the current_user_id() SECURITY DEFINER function reads
     this session variable to identify the calling user for policy evaluation.
"""
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(migrated_engine):
    """Create an autocommit-false session bound to migrated_engine."""
    Session = sessionmaker(bind=migrated_engine)
    return Session()


def _set_rls_context(conn, user_id: uuid.UUID | None):
    """Switch to non-superuser role and set current_user_id for RLS evaluation.

    SET ROLE makes PostgreSQL apply RLS (superuser connections bypass it).
    SET LOCAL app.current_user_id makes current_user_id() return the given UUID.
    Both settings persist for the duration of the transaction / connection.

    When user_id is None we simulate an unauthenticated / background-job context
    by setting the variable to the all-zeros sentinel UUID.  current_user_id()
    COALESCEs to that value anyway (via the COALESCE fallback in migration 0003),
    and no real user has that id, so the RLS subquery returns an empty set.
    Using a direct RESET would leave the GUC as '' which PostgreSQL cannot cast
    to UUID, causing a runtime error in the SECURITY DEFINER function.
    """
    conn.execute(text("SET ROLE app_test_role"))
    if user_id is not None:
        conn.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    else:
        # Sentinel UUID that matches no real user — triggers the "no access" branch
        conn.execute(text("SET LOCAL app.current_user_id = '00000000-0000-0000-0000-000000000000'"))


# ---------------------------------------------------------------------------
# Session-scoped seed data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rls_seed(migrated_engine):
    """Seed two client orgs, four users, and experiment_runs belonging to each.

    Uses a superuser connection (bypasses RLS) for setup.
    All data is cleaned up after the module.

    Returns a dict with UUIDs needed by individual tests.
    """
    conn = migrated_engine.connect()
    # Use superuser connection (no SET ROLE) so inserts go through unrestricted
    conn.execute(text("BEGIN"))

    # --- Roles (seeded by migration 0004 — query existing rather than inserting) ---
    lab_tech_role_id = conn.execute(
        text("SELECT id FROM roles WHERE name = 'Lab Technician'")
    ).scalar_one()
    admin_role_id = conn.execute(
        text("SELECT id FROM roles WHERE name = 'Administrator'")
    ).scalar_one()

    # --- Clients (org A and org B) ---
    client_a_id = uuid.uuid4()
    client_b_id = uuid.uuid4()

    conn.execute(text("""
        INSERT INTO clients (id, name, active, billing_info)
        VALUES (:a, 'Org Alpha', true, '{}'), (:b, 'Org Beta', true, '{}')
    """), {"a": str(client_a_id), "b": str(client_b_id)})

    # --- Users ---
    user_a_id = uuid.uuid4()   # Org A, Lab Technician
    user_b_id = uuid.uuid4()   # Org B, Lab Technician
    admin_id = uuid.uuid4()    # Org A, Administrator (is_admin() → True)

    pw = get_password_hash("testpw")
    conn.execute(text("""
        INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active)
        VALUES
            (:ua, 'User Alpha', 'user_alpha', 'alpha@test.com', :pw, :lt, :ca, true),
            (:ub, 'User Beta',  'user_beta',  'beta@test.com',  :pw, :lt, :cb, true),
            (:adm, 'Admin',     'admin_rls',  'admin@test.com', :pw, :adm_r, :ca, true)
    """), {
        "ua": str(user_a_id), "ub": str(user_b_id), "adm": str(admin_id),
        "pw": pw,
        "lt": str(lab_tech_role_id), "adm_r": str(admin_role_id),
        "ca": str(client_a_id), "cb": str(client_b_id),
    })

    # --- ExperimentTemplate (required FK) ---
    tmpl_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO experiment_templates (id, name, description, template_definition, created_by, modified_by)
        VALUES (:tid, 'RLS Test Template', NULL, '{}', :ua, :ua)
    """), {"tid": str(tmpl_id), "ua": str(user_a_id)})

    # --- ExperimentRuns: two for Org A, one for Org B ---
    run_a1_id = uuid.uuid4()
    run_a2_id = uuid.uuid4()
    run_b1_id = uuid.uuid4()

    conn.execute(text("""
        INSERT INTO experiment_runs (id, name, status, experiment_template_id, created_by)
        VALUES
            (:r_a1, 'Alpha Run 1', 'draft', :tmpl, :ua),
            (:r_a2, 'Alpha Run 2', 'draft', :tmpl, :ua),
            (:r_b1, 'Beta Run 1',  'draft', :tmpl, :ub)
    """), {
        "r_a1": str(run_a1_id), "r_a2": str(run_a2_id), "r_b1": str(run_b1_id),
        "tmpl": str(tmpl_id), "ua": str(user_a_id), "ub": str(user_b_id),
    })

    conn.execute(text("COMMIT"))
    conn.close()

    yield {
        "client_a_id": client_a_id,
        "client_b_id": client_b_id,
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "admin_id": admin_id,
        "tmpl_id": tmpl_id,
        "run_a1_id": run_a1_id,
        "run_a2_id": run_a2_id,
        "run_b1_id": run_b1_id,
    }

    # Teardown: clean up seed data (superuser, no RLS restrictions)
    conn = migrated_engine.connect()
    conn.execute(text("BEGIN"))
    conn.execute(text("DELETE FROM experiment_runs WHERE name IN ('Alpha Run 1', 'Alpha Run 2', 'Beta Run 1')"))
    conn.execute(text("DELETE FROM experiment_templates WHERE name = 'RLS Test Template'"))
    conn.execute(text("DELETE FROM users WHERE username IN ('user_alpha', 'user_beta', 'admin_rls')"))
    conn.execute(text("DELETE FROM clients WHERE name IN ('Org Alpha', 'Org Beta')"))
    # Roles are seeded by migration 0004 — do not delete them
    conn.execute(text("COMMIT"))
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExperimentRlsIsolation:
    """Client-scoped RLS enforcement for experiment_runs (migration 0041)."""

    def test_user_cannot_read_other_clients_rows(self, migrated_engine, rls_seed):
        """User Alpha (Org A) must not see Beta Run 1 (Org B)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed["user_a_id"])
            result = conn.execute(
                text("SELECT id FROM experiment_runs WHERE id = :rid"),
                {"rid": str(rls_seed["run_b1_id"])},
            ).fetchall()
        assert result == [], (
            "User Alpha (Org A) must not see experiment_runs created by Org B"
        )

    def test_user_can_read_own_clients_rows(self, migrated_engine, rls_seed):
        """User Alpha (Org A) sees both Alpha Run 1 and Alpha Run 2."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed["user_a_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_runs WHERE name LIKE 'Alpha Run%' ORDER BY name"),
            ).fetchall()
        ids = {str(r[0]) for r in rows}
        assert str(rls_seed["run_a1_id"]) in ids
        assert str(rls_seed["run_a2_id"]) in ids
        assert str(rls_seed["run_b1_id"]) not in ids

    def test_admin_sees_all_clients(self, migrated_engine, rls_seed):
        """Administrator sees runs from all client orgs (is_admin() path)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed["admin_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_runs WHERE name IN ('Alpha Run 1', 'Alpha Run 2', 'Beta Run 1') ORDER BY name"),
            ).fetchall()
        ids = {str(r[0]) for r in rows}
        assert str(rls_seed["run_a1_id"]) in ids
        assert str(rls_seed["run_a2_id"]) in ids
        assert str(rls_seed["run_b1_id"]) in ids

    def test_user_cannot_update_other_clients_row(self, migrated_engine, rls_seed):
        """User Alpha (Org A) UPDATE on Beta's row is silently filtered — 0 rows touched."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed["user_a_id"])
            result = conn.execute(
                text("UPDATE experiment_runs SET name = 'PWNED' WHERE id = :rid RETURNING id"),
                {"rid": str(rls_seed["run_b1_id"])},
            )
            touched = result.fetchall()
        assert touched == [], (
            "UPDATE on another client's row should return 0 affected rows"
        )

    def test_user_b_sees_only_org_b_rows(self, migrated_engine, rls_seed):
        """User Beta (Org B) sees Beta Run 1 but not Alpha runs."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed["user_b_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_runs WHERE name IN ('Alpha Run 1', 'Alpha Run 2', 'Beta Run 1')"),
            ).fetchall()
        ids = {str(r[0]) for r in rows}
        assert str(rls_seed["run_b1_id"]) in ids
        assert str(rls_seed["run_a1_id"]) not in ids
        assert str(rls_seed["run_a2_id"]) not in ids

    def test_null_current_user_id_sees_nothing(self, migrated_engine, rls_seed):
        """Unauthenticated/background context (no app.current_user_id) returns 0 rows.

        current_user_id() returns NULL when the session variable is unset.
        The subquery WHERE u2.id = NULL evaluates to FALSE for every row,
        so non-admins with no user context see an empty result set.
        This is the documented background-job behaviour (see migration 0041 notes).
        """
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, user_id=None)  # no app.current_user_id
            rows = conn.execute(
                text("SELECT id FROM experiment_runs WHERE name IN ('Alpha Run 1', 'Beta Run 1')"),
            ).fetchall()
        assert rows == [], (
            "No app.current_user_id set → current_user_id() returns NULL → "
            "subquery matches nothing → empty result for non-admin role"
        )
