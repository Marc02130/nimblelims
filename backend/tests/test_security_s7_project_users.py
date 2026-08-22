"""S7 UAT hold: lab staff need project_users; Client keeps same-client."""
import uuid

import pytest
from sqlalchemy import text


@pytest.fixture(scope="module")
def s7_fixture(migrated_engine):
    """NovaBio-like client, two lab techs, one project; only bob on project_users."""
    conn = migrated_engine.connect()
    conn.execute(text("BEGIN"))

    tech_role = conn.execute(
        text("SELECT id FROM roles WHERE name = 'Lab Technician'")
    ).scalar_one()
    client_role = conn.execute(
        text("SELECT id FROM roles WHERE name = 'Client'")
    ).scalar()
    system_client = conn.execute(
        text(
            "SELECT id FROM clients WHERE id = '00000000-0000-0000-0000-000000000001'"
        )
    ).scalar()
    if system_client is None:
        system_client = "00000000-0000-0000-0000-000000000001"
        conn.execute(
            text(
                """
                INSERT INTO clients (id, name, active, billing_info)
                VALUES (:id, 'System', true, '{}')
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": system_client},
        )

    tenant = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO clients (id, name, active, billing_info)
            VALUES (:id, 'S7 NovaBio', true, '{}')
            """
        ),
        {"id": str(tenant)},
    )

    from app.core.security import get_password_hash

    pw = get_password_hash("LabTech1!xxxx")
    alice = uuid.uuid4()
    bob = uuid.uuid4()
    for uid, uname in ((alice, "s7_alice"), (bob, "s7_bob")):
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, name, username, email, password_hash, role_id, client_id,
                    active, must_change_password
                )
                VALUES (
                    :id, :name, :uname, :email, :pw, :role, :client, true, false
                )
                """
            ),
            {
                "id": str(uid),
                "name": uname,
                "uname": uname,
                "email": f"{uname}@test.com",
                "pw": pw,
                "role": str(tech_role),
                "client": str(tenant),
            },
        )

    # System-client lab tech (org-wide)
    sys_tech = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO users (
                id, name, username, email, password_hash, role_id, client_id,
                active, must_change_password
            )
            VALUES (
                :id, 'S7 SysTech', 's7_systech', 's7sys@test.com', :pw,
                :role, :client, true, false
            )
            """
        ),
        {
            "id": str(sys_tech),
            "pw": pw,
            "role": str(tech_role),
            "client": str(system_client),
        },
    )

    # Client-role user on tenant
    client_user = None
    if client_role:
        client_user = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, name, username, email, password_hash, role_id, client_id,
                    active, must_change_password
                )
                VALUES (
                    :id, 'S7 Client', 's7_client', 's7client@test.com', :pw,
                    :role, :client, true, false
                )
                """
            ),
            {
                "id": str(client_user),
                "pw": pw,
                "role": str(client_role),
                "client": str(tenant),
            },
        )

    # Status list entry for project FK if required
    status_id = conn.execute(text("SELECT id FROM list_entries LIMIT 1")).scalar()
    if status_id is None:
        lst = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO lists (id, name, active, created_at, modified_at)
                VALUES (:id, 'S7 Lists', true, NOW(), NOW())
                """
            ),
            {"id": str(lst)},
        )
        status_id = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO list_entries (
                    id, list_id, name, active, created_at, modified_at
                )
                VALUES (:id, :lid, 'Active', true, NOW(), NOW())
                """
            ),
            {"id": str(status_id), "lid": str(lst)},
        )

    project = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO projects (
                id, name, client_id, status, start_date, due_date,
                active, created_at, modified_at
            )
            VALUES (
                :id, 'S7 CAR-T', :client, :status, NOW(), NOW() + interval '30 days',
                true, NOW(), NOW()
            )
            """
        ),
        {"id": str(project), "client": str(tenant), "status": str(status_id)},
    )

    # Only bob on project_users
    conn.execute(
        text(
            """
            INSERT INTO project_users (project_id, user_id, granted_at)
            VALUES (:pid, :uid, NOW())
            """
        ),
        {"pid": str(project), "uid": str(bob)},
    )

    conn.execute(text("COMMIT"))
    conn.close()
    return {
        "tenant": tenant,
        "project": project,
        "alice": alice,
        "bob": bob,
        "sys_tech": sys_tech,
        "client_user": client_user,
    }


def _access(conn, user_id, project_id) -> bool:
    conn.execute(text("SET ROLE app_test_role"))
    conn.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"),
        {"v": str(user_id)},
    )
    ok = conn.execute(
        text("SELECT has_project_access(CAST(:pid AS uuid))"),
        {"pid": str(project_id)},
    ).scalar()
    conn.execute(text("RESET ROLE"))
    return bool(ok)


class TestS7HasProjectAccess:
    def test_unassigned_same_client_labtech_denied(self, migrated_engine, s7_fixture):
        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            assert _access(conn, s7_fixture["alice"], s7_fixture["project"]) is False
            conn.execute(text("ROLLBACK"))

    def test_assigned_labtech_allowed(self, migrated_engine, s7_fixture):
        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            assert _access(conn, s7_fixture["bob"], s7_fixture["project"]) is True
            conn.execute(text("ROLLBACK"))

    def test_system_client_labtech_allowed(self, migrated_engine, s7_fixture):
        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            assert _access(conn, s7_fixture["sys_tech"], s7_fixture["project"]) is True
            conn.execute(text("ROLLBACK"))

    def test_client_role_same_client_allowed(self, migrated_engine, s7_fixture):
        if not s7_fixture["client_user"]:
            pytest.skip("Client role not seeded")
        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            assert (
                _access(conn, s7_fixture["client_user"], s7_fixture["project"]) is True
            )
            conn.execute(text("ROLLBACK"))
