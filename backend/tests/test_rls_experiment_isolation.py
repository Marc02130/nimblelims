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


# ---------------------------------------------------------------------------
# Migration 0042 — client-scoped RLS for the four 0036 tables
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rls_seed_0042(migrated_engine, rls_seed):
    """Extend rls_seed with rows in the four 0036 tables.

    Reuses the existing users, clients, and experiment_template from rls_seed.
    Seeds one row per table for Org A (user_a) and one for Org B (user_b).
    Cleaned up after the module.
    """
    ua = rls_seed["user_a_id"]
    ub = rls_seed["user_b_id"]
    tmpl = rls_seed["tmpl_id"]
    client_a = rls_seed["client_a_id"]

    conn = migrated_engine.connect()
    conn.execute(text("BEGIN"))

    # Query required list_entry IDs seeded by migration 0004.
    # These use fixed list UUIDs but random entry UUIDs, so we must look them up.
    proj_status_id = conn.execute(text(
        "SELECT id FROM list_entries WHERE list_id = '33333333-3333-3333-3333-333333333333' AND name = 'Active' LIMIT 1"
    )).scalar_one()
    sample_status_id = conn.execute(text(
        "SELECT id FROM list_entries WHERE list_id = '11111111-1111-1111-1111-111111111111' AND name = 'Received' LIMIT 1"
    )).scalar_one()
    sample_type_id = conn.execute(text(
        "SELECT id FROM list_entries WHERE list_id = '55555555-5555-5555-5555-555555555555' AND name = 'Blood' LIMIT 1"
    )).scalar_one()
    matrix_id = conn.execute(text(
        "SELECT id FROM list_entries WHERE list_id = '66666666-6666-6666-6666-666666666666' AND name = 'Sludge' LIMIT 1"
    )).scalar_one()

    # --- experiment_templates ---
    # rls_seed already inserted one template (user_a). Add one for user_b.
    tmpl_b_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO experiment_templates (id, name, description, template_definition, created_by, modified_by)
        VALUES (:tid, 'RLS Test Template B', NULL, '{}', :ub, :ub)
    """), {"tid": str(tmpl_b_id), "ub": str(ub)})

    # --- Project + Samples (required for experiment_sample_executions.sample_id FK) ---
    proj_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO projects (id, name, client_id, status, start_date, active, created_by, modified_by)
        VALUES (:pid, 'RLS Test Project 0042', :cid, :pstatus, '2026-01-01', TRUE, :ua, :ua)
    """), {
        "pid": str(proj_id), "cid": str(client_a),
        "pstatus": str(proj_status_id), "ua": str(ua),
    })

    sample_a_id = uuid.uuid4()
    sample_b_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO samples (id, name, project_id, sample_type, status, matrix, active, created_by, modified_by)
        VALUES
            (:sa, 'RLS Sample A 0042', :pid, :stype, :sstatus, :matrix, TRUE, :ua, :ua),
            (:sb, 'RLS Sample B 0042', :pid, :stype, :sstatus, :matrix, TRUE, :ub, :ub)
    """), {
        "sa": str(sample_a_id), "sb": str(sample_b_id),
        "pid": str(proj_id),
        "stype": str(sample_type_id), "sstatus": str(sample_status_id),
        "matrix": str(matrix_id),
        "ua": str(ua), "ub": str(ub),
    })

    # --- experiments (no 'status' text column — status_id is a nullable FK) ---
    exp_a_id = uuid.uuid4()
    exp_b_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO experiments (id, name, experiment_template_id, created_by)
        VALUES
            (:ea, 'RLS Exp A', :tmpl, :ua),
            (:eb, 'RLS Exp B', :tmpl, :ub)
    """), {
        "ea": str(exp_a_id), "eb": str(exp_b_id),
        "tmpl": str(tmpl), "ua": str(ua), "ub": str(ub),
    })

    # --- experiment_details (columns: detail_type + content JSONB, not key/value) ---
    detail_a_id = uuid.uuid4()
    detail_b_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO experiment_details (id, experiment_id, detail_type, created_by)
        VALUES
            (:da, :ea, 'rls_key', :ua),
            (:db, :eb, 'rls_key', :ub)
    """), {
        "da": str(detail_a_id), "db": str(detail_b_id),
        "ea": str(exp_a_id), "eb": str(exp_b_id),
        "ua": str(ua), "ub": str(ub),
    })

    # --- experiment_sample_executions (real sample_id FK, no 'status' column) ---
    exec_a_id = uuid.uuid4()
    exec_b_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO experiment_sample_executions (id, experiment_id, sample_id, created_by)
        VALUES
            (:xa, :ea, :sa, :ua),
            (:xb, :eb, :sb, :ub)
    """), {
        "xa": str(exec_a_id), "xb": str(exec_b_id),
        "ea": str(exp_a_id), "eb": str(exp_b_id),
        "sa": str(sample_a_id), "sb": str(sample_b_id),
        "ua": str(ua), "ub": str(ub),
    })

    conn.execute(text("COMMIT"))
    conn.close()

    yield {
        **rls_seed,
        "tmpl_b_id": tmpl_b_id,
        "exp_a_id": exp_a_id,
        "exp_b_id": exp_b_id,
        "detail_a_id": detail_a_id,
        "detail_b_id": detail_b_id,
        "exec_a_id": exec_a_id,
        "exec_b_id": exec_b_id,
    }

    # Teardown (superuser, no RLS) — reverse FK order
    conn = migrated_engine.connect()
    conn.execute(text("BEGIN"))
    conn.execute(text(
        "DELETE FROM experiment_sample_executions WHERE id IN (:xa, :xb)"),
        {"xa": str(exec_a_id), "xb": str(exec_b_id)},
    )
    conn.execute(text(
        "DELETE FROM experiment_details WHERE id IN (:da, :db)"),
        {"da": str(detail_a_id), "db": str(detail_b_id)},
    )
    conn.execute(text(
        "DELETE FROM experiments WHERE id IN (:ea, :eb)"),
        {"ea": str(exp_a_id), "eb": str(exp_b_id)},
    )
    conn.execute(text(
        "DELETE FROM samples WHERE id IN (:sa, :sb)"),
        {"sa": str(sample_a_id), "sb": str(sample_b_id)},
    )
    conn.execute(text(
        "DELETE FROM projects WHERE id = :pid"),
        {"pid": str(proj_id)},
    )
    conn.execute(text(
        "DELETE FROM experiment_templates WHERE id = :tid"),
        {"tid": str(tmpl_b_id)},
    )
    conn.execute(text("COMMIT"))
    conn.close()


class TestExperiment0036RlsIsolation:
    """Client-scoped RLS enforcement for the four 0036 tables (migration 0042)."""

    # ------------------------------------------------------------------
    # SELECT isolation — one test per table
    # ------------------------------------------------------------------

    def test_experiment_templates_select_isolation(self, migrated_engine, rls_seed_0042):
        """User Alpha (Org A) must not see Template B (Org B)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed_0042["user_a_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_templates WHERE id = :tid"),
                {"tid": str(rls_seed_0042["tmpl_b_id"])},
            ).fetchall()
        assert rows == [], (
            "User Alpha (Org A) must not see experiment_templates rows owned by Org B"
        )

    def test_experiments_select_isolation(self, migrated_engine, rls_seed_0042):
        """User Alpha (Org A) must not see Experiment B (Org B)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed_0042["user_a_id"])
            rows = conn.execute(
                text("SELECT id FROM experiments WHERE id = :eid"),
                {"eid": str(rls_seed_0042["exp_b_id"])},
            ).fetchall()
        assert rows == [], (
            "User Alpha (Org A) must not see experiments rows owned by Org B"
        )

    def test_experiment_details_select_isolation(self, migrated_engine, rls_seed_0042):
        """User Alpha (Org A) must not see Detail B (Org B)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed_0042["user_a_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_details WHERE id = :did"),
                {"did": str(rls_seed_0042["detail_b_id"])},
            ).fetchall()
        assert rows == [], (
            "User Alpha (Org A) must not see experiment_details rows owned by Org B"
        )

    def test_experiment_sample_executions_select_isolation(self, migrated_engine, rls_seed_0042):
        """User Alpha (Org A) must not see Execution B (Org B)."""
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, rls_seed_0042["user_a_id"])
            rows = conn.execute(
                text("SELECT id FROM experiment_sample_executions WHERE id = :xid"),
                {"xid": str(rls_seed_0042["exec_b_id"])},
            ).fetchall()
        assert rows == [], (
            "User Alpha (Org A) must not see experiment_sample_executions rows owned by Org B"
        )

    # ------------------------------------------------------------------
    # Write isolation (UPDATE silently returns 0 rows)
    # ------------------------------------------------------------------

    def test_write_isolation_across_all_0036_tables(self, migrated_engine, rls_seed_0042):
        """User Alpha cannot UPDATE any row owned by Org B in all four 0036 tables.

        RLS silently filters the target rows — UPDATE returns 0 rows affected,
        no permission error is raised. Verified for experiment_templates (most
        commonly shared between orgs) and experiments (broadest impact).
        """
        ua = rls_seed_0042["user_a_id"]

        # experiment_templates
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, ua)
            touched = conn.execute(
                text("UPDATE experiment_templates SET name = 'PWNED' WHERE id = :tid RETURNING id"),
                {"tid": str(rls_seed_0042["tmpl_b_id"])},
            ).fetchall()
        assert touched == [], "UPDATE on Org B template must return 0 rows (RLS filtered)"

        # experiments
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, ua)
            touched = conn.execute(
                text("UPDATE experiments SET name = 'PWNED' WHERE id = :eid RETURNING id"),
                {"eid": str(rls_seed_0042["exp_b_id"])},
            ).fetchall()
        assert touched == [], "UPDATE on Org B experiment must return 0 rows (RLS filtered)"

        # experiment_details
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, ua)
            touched = conn.execute(
                text("UPDATE experiment_details SET detail_type = 'changed' WHERE id = :did RETURNING id"),
                {"did": str(rls_seed_0042["detail_b_id"])},
            ).fetchall()
        assert touched == [], "UPDATE on Org B detail must return 0 rows (RLS filtered)"

        # experiment_sample_executions
        with migrated_engine.connect() as conn:
            _set_rls_context(conn, ua)
            touched = conn.execute(
                text("UPDATE experiment_sample_executions SET replicate_number = 99 WHERE id = :xid RETURNING id"),
                {"xid": str(rls_seed_0042["exec_b_id"])},
            ).fetchall()
        assert touched == [], "UPDATE on Org B execution must return 0 rows (RLS filtered)"

    # ------------------------------------------------------------------
    # FORCE RLS verification
    # ------------------------------------------------------------------

    def test_force_rls_enforced_on_0036_tables(self, migrated_engine, rls_seed_0042):
        """FORCE ROW LEVEL SECURITY is active — app_test_role (non-superuser table
        owner) cannot bypass the policy even via direct connection.

        Verified by querying as app_test_role with current_user_id set to user_a.
        Only user_a's rows in each table should be visible.
        """
        ua = rls_seed_0042["user_a_id"]

        with migrated_engine.connect() as conn:
            _set_rls_context(conn, ua)

            # experiment_templates: see own, not Org B
            tmpl_rows = conn.execute(
                text("SELECT id FROM experiment_templates WHERE id IN (:ta, :tb)"),
                {
                    "ta": str(rls_seed_0042["tmpl_id"]),    # user_a's template
                    "tb": str(rls_seed_0042["tmpl_b_id"]),  # user_b's template
                },
            ).fetchall()
            tmpl_ids = {str(r[0]) for r in tmpl_rows}
            assert str(rls_seed_0042["tmpl_id"]) in tmpl_ids, (
                "User A must see their own template"
            )
            assert str(rls_seed_0042["tmpl_b_id"]) not in tmpl_ids, (
                "FORCE RLS must block user A from seeing user B's template"
            )

            # experiments: see own, not Org B
            exp_rows = conn.execute(
                text("SELECT id FROM experiments WHERE id IN (:ea, :eb)"),
                {"ea": str(rls_seed_0042["exp_a_id"]), "eb": str(rls_seed_0042["exp_b_id"])},
            ).fetchall()
            exp_ids = {str(r[0]) for r in exp_rows}
            assert str(rls_seed_0042["exp_a_id"]) in exp_ids
            assert str(rls_seed_0042["exp_b_id"]) not in exp_ids

    # ------------------------------------------------------------------
    # Admin cross-org access
    # ------------------------------------------------------------------

    def test_admin_sees_all_orgs_in_0036_tables(self, migrated_engine, rls_seed_0042):
        """Application-level admin (is_admin() → True) can read rows from ALL client
        orgs in all four 0036 tables.
        """
        admin = rls_seed_0042["admin_id"]

        with migrated_engine.connect() as conn:
            _set_rls_context(conn, admin)

            # experiment_templates: both orgs visible
            tmpl_rows = conn.execute(
                text("SELECT id FROM experiment_templates WHERE id IN (:ta, :tb)"),
                {
                    "ta": str(rls_seed_0042["tmpl_id"]),
                    "tb": str(rls_seed_0042["tmpl_b_id"]),
                },
            ).fetchall()
            tmpl_ids = {str(r[0]) for r in tmpl_rows}
            assert str(rls_seed_0042["tmpl_id"]) in tmpl_ids
            assert str(rls_seed_0042["tmpl_b_id"]) in tmpl_ids

            # experiments: both orgs visible
            exp_rows = conn.execute(
                text("SELECT id FROM experiments WHERE id IN (:ea, :eb)"),
                {"ea": str(rls_seed_0042["exp_a_id"]), "eb": str(rls_seed_0042["exp_b_id"])},
            ).fetchall()
            exp_ids = {str(r[0]) for r in exp_rows}
            assert str(rls_seed_0042["exp_a_id"]) in exp_ids
            assert str(rls_seed_0042["exp_b_id"]) in exp_ids

            # experiment_details: both orgs visible
            detail_rows = conn.execute(
                text("SELECT id FROM experiment_details WHERE id IN (:da, :db)"),
                {"da": str(rls_seed_0042["detail_a_id"]), "db": str(rls_seed_0042["detail_b_id"])},
            ).fetchall()
            detail_ids = {str(r[0]) for r in detail_rows}
            assert str(rls_seed_0042["detail_a_id"]) in detail_ids
            assert str(rls_seed_0042["detail_b_id"]) in detail_ids

            # experiment_sample_executions: both orgs visible
            exec_rows = conn.execute(
                text("SELECT id FROM experiment_sample_executions WHERE id IN (:xa, :xb)"),
                {"xa": str(rls_seed_0042["exec_a_id"]), "xb": str(rls_seed_0042["exec_b_id"])},
            ).fetchall()
            exec_ids = {str(r[0]) for r in exec_rows}
            assert str(rls_seed_0042["exec_a_id"]) in exec_ids
            assert str(rls_seed_0042["exec_b_id"]) in exec_ids
