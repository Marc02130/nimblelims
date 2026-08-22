"""Sec9: non-admin can INSERT containers when created_by = current_user_id."""
import uuid

import pytest
from sqlalchemy import text


@pytest.fixture(scope="module")
def sec9_users(migrated_engine):
    """Seed a Lab Technician on System client; return ids."""
    conn = migrated_engine.connect()
    conn.execute(text("BEGIN"))
    tech_role = conn.execute(
        text("SELECT id FROM roles WHERE name = 'Lab Technician'")
    ).scalar_one()
    system_client = conn.execute(
        text("SELECT id FROM clients WHERE name = 'System' LIMIT 1")
    ).scalar()
    if system_client is None:
        system_client = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO clients (id, name, active, billing_info)
                VALUES (:id, 'System', true, '{}')
                """
            ),
            {"id": str(system_client)},
        )

    user_id = uuid.uuid4()
    from app.core.security import get_password_hash

    pw = get_password_hash("LabTech1!xxxx")
    conn.execute(
        text(
            """
            INSERT INTO users (
                id, name, username, email, password_hash, role_id, client_id,
                active, must_change_password
            )
            VALUES (
                :id, 'Sec9 Lab Tech', 'sec9_labtech', 'sec9@test.com', :pw,
                :role, :client, true, false
            )
            """
        ),
        {
            "id": str(user_id),
            "pw": pw,
            "role": str(tech_role),
            "client": str(system_client),
        },
    )

    # Need a container type for FK
    ctype = conn.execute(text("SELECT id FROM container_types LIMIT 1")).scalar()
    if ctype is None:
        ctype = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO container_types (id, name, active, created_at, modified_at)
                VALUES (:id, 'Sec9 Tube', true, NOW(), NOW())
                """
            ),
            {"id": str(ctype)},
        )
    conn.execute(text("COMMIT"))
    conn.close()
    return {"user_id": user_id, "ctype_id": ctype}


class TestContainersRlsSec9:
    def test_labtech_can_insert_container_with_created_by(
        self, migrated_engine, sec9_users
    ):
        """After 0062, empty container INSERT allowed when created_by = current user."""
        user_id = sec9_users["user_id"]
        ctype_id = sec9_users["ctype_id"]
        container_id = uuid.uuid4()

        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            # App role feels RLS (same as production lims_app)
            conn.execute(text("SET ROLE app_test_role"))
            conn.execute(
                text("SELECT set_config('app.current_user_id', :v, true)"),
                {"v": str(user_id)},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO containers (
                        id, name, active, type_id, created_by, modified_by,
                        "row", "column", created_at, modified_at
                    )
                    VALUES (
                        :id, :name, true, :tid, :uid, :uid, 1, 1, NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": str(container_id),
                    "name": f"SEC9-{container_id.hex[:8]}",
                    "tid": str(ctype_id),
                    "uid": str(user_id),
                },
            )
            # INSERT succeeded under containers_insert policy
            conn.execute(text("RESET ROLE"))
            found = conn.execute(
                text("SELECT id FROM containers WHERE id = :id"),
                {"id": str(container_id)},
            ).scalar()
            assert found is not None
            conn.execute(text("COMMIT"))

    def test_labtech_insert_without_created_by_denied(
        self, migrated_engine, sec9_users
    ):
        user_id = sec9_users["user_id"]
        ctype_id = sec9_users["ctype_id"]
        container_id = uuid.uuid4()

        with migrated_engine.connect() as conn:
            conn.execute(text("BEGIN"))
            conn.execute(text("SET ROLE app_test_role"))
            conn.execute(
                text("SELECT set_config('app.current_user_id', :v, true)"),
                {"v": str(user_id)},
            )
            with pytest.raises(Exception) as exc:
                conn.execute(
                    text(
                        """
                        INSERT INTO containers (
                            id, name, active, type_id, created_by, modified_by,
                            "row", "column", created_at, modified_at
                        )
                        VALUES (
                            :id, :name, true, :tid, NULL, NULL, 1, 1, NOW(), NOW()
                        )
                        """
                    ),
                    {
                        "id": str(container_id),
                        "name": f"SEC9BAD-{container_id.hex[:8]}",
                        "tid": str(ctype_id),
                    },
                )
            msg = str(exc.value).lower()
            assert "row-level security" in msg or "policy" in msg
            conn.execute(text("ROLLBACK"))
