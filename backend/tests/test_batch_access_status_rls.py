"""Cross-client batch reads under the real row-level security policies.

The default pytest database is built with create_all and has no policies, so a
hidden batch is still visible to the superuser connection. These tests use
migrated_engine, which runs Alembic (including FORCE ROW LEVEL SECURITY) and
then speaks as lims_app. CI runs this file in the pytest job. No extra CI step
is required.

batch_access_status returns only not_found, forbidden, or visible. It reads
app.current_user_id. PUBLIC cannot execute it.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, get_password_hash
from app.database import get_db
from app.main import app

CLIENT_ROLE = "dddddddd-dddd-dddd-dddd-dddddddddddd"
BATCH_READ = "e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1"
FN = "public.batch_access_status(uuid)"


def _scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def _grant_lims_app(conn) -> None:
    conn.execute(text("GRANT USAGE ON SCHEMA public TO lims_app"))
    conn.execute(
        text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lims_app"
        )
    )


def _insert_side(conn, suffix: str, label: str, user_name: str, client_name: str) -> dict:
    client_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()
    sample_id = uuid4()
    container_id = uuid4()
    batch_id = uuid4()
    test_id = uuid4()
    type_id = uuid4()
    analysis_id = uuid4()
    status_id = _scalar(
        conn,
        """
        SELECT id FROM list_entries
        WHERE list_id = '11111111-1111-1111-1111-111111111111' AND name = 'Received'
        """,
    )
    project_status = _scalar(
        conn,
        """
        SELECT id FROM list_entries
        WHERE list_id = '33333333-3333-3333-3333-333333333333' AND name = 'Active'
        """,
    )
    batch_status = _scalar(
        conn,
        """
        SELECT id FROM list_entries
        WHERE list_id = '44444444-4444-4444-4444-444444444444' AND name = 'Created'
        """,
    )
    sample_type = _scalar(
        conn,
        """
        SELECT id FROM list_entries
        WHERE list_id = '55555555-5555-5555-5555-555555555555' AND name = 'Blood'
        """,
    )
    conn.execute(
        text(
            """
            INSERT INTO clients (id, name, description, active, billing_info, created_at, modified_at)
            VALUES (:id, :name, '', true, '{}'::jsonb, NOW(), NOW())
            """
        ),
        {"id": client_id, "name": client_name},
    )
    conn.execute(
        text(
            """
            INSERT INTO users (
                id, name, username, email, password_hash, role_id, client_id,
                active, must_change_password, password_epoch, created_at, modified_at
            )
            VALUES (
                :id, :name, :username, :email, :password_hash, :role_id, :client_id,
                true, false, 0, NOW(), NOW()
            )
            """
        ),
        {
            "id": user_id,
            "name": user_name,
            "username": f"{label}-{suffix}",
            "email": f"{label}-{suffix}@example.com",
            "password_hash": get_password_hash("batch-access-pass"),
            "role_id": CLIENT_ROLE,
            "client_id": client_id,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO projects (
                id, name, client_id, status, start_date, active, created_at, modified_at,
                created_by, modified_by
            )
            VALUES (
                :id, :name, :client_id, :status, NOW(), true, NOW(), NOW(), :user_id, :user_id
            )
            """
        ),
        {
            "id": project_id,
            "name": f"{label}-project-{suffix}",
            "client_id": client_id,
            "status": project_status,
            "user_id": user_id,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO samples (
                id, name, sample_type, status, project_id, active,
                created_at, modified_at, created_by, modified_by
            )
            VALUES (
                :id, :name, :sample_type, :status, :project_id, true,
                NOW(), NOW(), :user_id, :user_id
            )
            """
        ),
        {
            "id": sample_id,
            "name": f"{label}-sample-{suffix}",
            "sample_type": sample_type,
            "status": status_id,
            "project_id": project_id,
            "user_id": user_id,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO container_types (
                id, name, rows, columns, active, created_at, modified_at, created_by, modified_by
            )
            VALUES (:id, :name, 1, 1, true, NOW(), NOW(), :user_id, :user_id)
            """
        ),
        {"id": type_id, "name": f"{label}-type-{suffix}", "user_id": user_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO containers (
                id, name, row, "column", type_id, active,
                created_at, modified_at, created_by, modified_by
            )
            VALUES (
                :id, :name, 1, 1, :type_id, true,
                NOW(), NOW(), :user_id, :user_id
            )
            """
        ),
        {
            "id": container_id,
            "name": f"{label}-tube-{suffix}",
            "type_id": type_id,
            "user_id": user_id,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO contents (container_id, sample_id)
            VALUES (:container_id, :sample_id)
            """
        ),
        {"container_id": container_id, "sample_id": sample_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO batches (
                id, name, description, status, active,
                created_at, modified_at, created_by, modified_by
            )
            VALUES (
                :id, :name, :description, :status, true,
                NOW(), NOW(), :user_id, :user_id
            )
            """
        ),
        {
            "id": batch_id,
            "name": f"{label}-batch-{suffix}",
            "description": f"{label} batch",
            "status": batch_status,
            "user_id": user_id,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO batch_containers (batch_id, container_id)
            VALUES (:batch_id, :container_id)
            """
        ),
        {"batch_id": batch_id, "container_id": container_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO analyses (
                id, name, active, created_at, modified_at, created_by, modified_by
            )
            VALUES (:id, :name, true, NOW(), NOW(), :user_id, :user_id)
            """
        ),
        {"id": analysis_id, "name": f"{label}-assay-{suffix}", "user_id": user_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO tests (
                id, name, sample_id, analysis_id, status, active,
                created_at, modified_at, created_by, modified_by
            )
            VALUES (
                :id, :name, :sample_id, :analysis_id, :status, true,
                NOW(), NOW(), :user_id, :user_id
            )
            """
        ),
        {
            "id": test_id,
            "name": f"{label}-test-{suffix}",
            "sample_id": sample_id,
            "analysis_id": analysis_id,
            "status": status_id,
            "user_id": user_id,
        },
    )
    return {
        "client_id": client_id,
        "client_name": client_name,
        "user_id": user_id,
        "user_name": user_name,
        "project_id": project_id,
        "sample_id": sample_id,
        "sample_name": f"{label}-sample-{suffix}",
        "container_id": container_id,
        "container_name": f"{label}-tube-{suffix}",
        "batch_id": batch_id,
        "batch_name": f"{label}-batch-{suffix}",
        "test_id": test_id,
        "test_name": f"{label}-test-{suffix}",
        "type_id": type_id,
        "analysis_id": analysis_id,
    }


def _cleanup(conn, rows: list) -> None:
    test_ids = [row["test_id"] for row in rows]
    analysis_ids = [row["analysis_id"] for row in rows]
    batch_ids = [row["batch_id"] for row in rows]
    container_ids = [row["container_id"] for row in rows]
    type_ids = [row["type_id"] for row in rows]
    sample_ids = [row["sample_id"] for row in rows]
    project_ids = [row["project_id"] for row in rows]
    user_ids = [row["user_id"] for row in rows]
    client_ids = [row["client_id"] for row in rows]
    conn.execute(text("DELETE FROM tests WHERE id = ANY(:ids)"), {"ids": test_ids})
    conn.execute(text("DELETE FROM analyses WHERE id = ANY(:ids)"), {"ids": analysis_ids})
    conn.execute(
        text("DELETE FROM batch_containers WHERE batch_id = ANY(:ids)"),
        {"ids": batch_ids},
    )
    conn.execute(text("DELETE FROM batches WHERE id = ANY(:ids)"), {"ids": batch_ids})
    conn.execute(
        text("DELETE FROM contents WHERE container_id = ANY(:ids)"),
        {"ids": container_ids},
    )
    conn.execute(text("DELETE FROM containers WHERE id = ANY(:ids)"), {"ids": container_ids})
    conn.execute(
        text("DELETE FROM container_types WHERE id = ANY(:ids)"),
        {"ids": type_ids},
    )
    conn.execute(text("DELETE FROM samples WHERE id = ANY(:ids)"), {"ids": sample_ids})
    conn.execute(text("DELETE FROM projects WHERE id = ANY(:ids)"), {"ids": project_ids})
    conn.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": user_ids})
    conn.execute(text("DELETE FROM clients WHERE id = ANY(:ids)"), {"ids": client_ids})


def _headers(user_id) -> dict:
    token = create_access_token(
        {
            "sub": str(user_id),
            "username": "batch-access",
            "role": "Client",
            "permissions": ["batch:read", "batch:update", "batch:delete", "batch:manage"],
            "pwd_epoch": 0,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _assert_no_identifiers(body: str, *needles: str) -> None:
    for needle in needles:
        assert needle not in body, needle


@pytest.fixture(scope="module")
def batch_world(migrated_engine):
    suffix = uuid4().hex[:8]
    caller_name = f"CallerClient{suffix}"
    owner_name = f"OwnerClient{suffix}"
    caller_user = f"CallerUser{suffix}"
    owner_user = f"OwnerUser{suffix}"
    conn = migrated_engine.connect()
    trans = conn.begin()
    try:
        _grant_lims_app(conn)
        conn.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :role_id, id FROM permissions
                WHERE name IN ('batch:read', 'batch:update', 'batch:delete', 'batch:manage')
                ON CONFLICT DO NOTHING
                """
            ),
            {"role_id": CLIENT_ROLE},
        )
        conn.execute(
            text("REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM app_test_role")
        )
        caller = _insert_side(conn, suffix, "caller", caller_user, caller_name)
        owner = _insert_side(conn, suffix, "owner", owner_user, owner_name)
        mixed_id = uuid4()
        mixed_name = f"MixedBatch{suffix}"
        conn.execute(
            text(
                """
                INSERT INTO batches (
                    id, name, description, status, active,
                    created_at, modified_at, created_by, modified_by
                )
                SELECT :id, :name, 'mixed', status, true, NOW(), NOW(), :user_id, :user_id
                FROM batches WHERE id = :source
                """
            ),
            {
                "id": mixed_id,
                "name": mixed_name,
                "user_id": caller["user_id"],
                "source": caller["batch_id"],
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO batch_containers (batch_id, container_id)
                VALUES (:batch_id, :caller_container), (:batch_id, :owner_container)
                """
            ),
            {
                "batch_id": mixed_id,
                "caller_container": caller["container_id"],
                "owner_container": owner["container_id"],
            },
        )
        trans.commit()
    except Exception:
        trans.rollback()
        conn.close()
        raise

    world = {
        "suffix": suffix,
        "caller": caller,
        "owner": owner,
        "mixed_id": mixed_id,
        "mixed_name": mixed_name,
        "caller_name": caller_name,
        "owner_name": owner_name,
        "caller_user": caller_user,
        "owner_user": owner_user,
    }
    try:
        yield world
    finally:
        cleanup = migrated_engine.connect()
        done = cleanup.begin()
        try:
            cleanup.execute(
                text("DELETE FROM batch_containers WHERE batch_id = :id"),
                {"id": mixed_id},
            )
            cleanup.execute(text("DELETE FROM batches WHERE id = :id"), {"id": mixed_id})
            _cleanup(cleanup, [caller, owner])
            cleanup.execute(
                text(
                    """
                    DELETE FROM role_permissions
                    WHERE role_id = :role_id
                      AND permission_id IN (
                        SELECT id FROM permissions
                        WHERE name IN ('batch:read', 'batch:update', 'batch:delete', 'batch:manage')
                      )
                    """
                ),
                {"role_id": CLIENT_ROLE},
            )
            done.commit()
        except Exception:
            done.rollback()
            raise
        finally:
            cleanup.close()
        conn.close()


@pytest.fixture
def lims_app_client(migrated_engine):
    """Requests run as lims_app so FORCE ROW LEVEL SECURITY applies."""

    def override_get_db():
        connection = migrated_engine.connect()
        transaction = connection.begin()
        Session = sessionmaker(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )
        session = Session()
        session.execute(text("SET ROLE lims_app"))
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.execute(text("RESET ROLE"))
            connection.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _needles(world) -> tuple:
    caller = world["caller"]
    owner = world["owner"]
    return (
        world["caller_name"],
        world["owner_name"],
        world["caller_user"],
        world["owner_user"],
        str(caller["client_id"]),
        str(owner["client_id"]),
        str(caller["user_id"]),
        str(owner["user_id"]),
        owner["batch_name"],
        owner["sample_name"],
        owner["container_name"],
        world["mixed_name"],
    )


def test_function_lockdown(migrated_engine, batch_world):
    del batch_world
    with migrated_engine.connect() as conn:
        owner_bypasses = conn.execute(
            text(
                """
                SELECT r.rolsuper OR r.rolbypassrls
                FROM pg_proc p
                JOIN pg_roles r ON r.oid = p.proowner
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname = 'batch_access_status'
                """
            )
        ).scalar()
        assert owner_bypasses is True
        config = conn.execute(
            text(
                """
                SELECT proconfig
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname = 'batch_access_status'
                """
            )
        ).scalar()
        assert config is not None
        assert any(item.startswith("search_path=pg_catalog, public") for item in config)
        definers = conn.execute(
            text(
                """
                SELECT p.prosecdef
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname = 'batch_access_status'
                """
            )
        ).scalar()
        assert definers is True
        assert conn.execute(
            text("SELECT has_function_privilege('public', :fn, 'EXECUTE')"),
            {"fn": FN},
        ).scalar() is False
        assert conn.execute(
            text("SELECT has_function_privilege('lims_app', :fn, 'EXECUTE')"),
            {"fn": FN},
        ).scalar() is True
        assert conn.execute(
            text("SELECT has_function_privilege('app_test_role', :fn, 'EXECUTE')"),
            {"fn": FN},
        ).scalar() is False
    nobody_conn = migrated_engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    nobody_conn.execute(text("CREATE ROLE batch_access_nobody NOLOGIN"))
    try:
        nobody = nobody_conn.execute(
            text(
                "SELECT has_function_privilege('batch_access_nobody', :fn, 'EXECUTE')"
            ),
            {"fn": FN},
        ).scalar()
        assert nobody is False
    finally:
        nobody_conn.execute(text("DROP ROLE IF EXISTS batch_access_nobody"))
        nobody_conn.close()


def _status(conn, user_id, batch_id) -> str:
    conn.execute(text("SET ROLE lims_app"))
    conn.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )
    seen = conn.execute(
        text("SELECT public.batch_access_status(CAST(:batch_id AS uuid))"),
        {"batch_id": str(batch_id)},
    ).scalar()
    conn.execute(text("RESET ROLE"))
    return seen


def test_downgrade_drops_the_function(migrated_engine, batch_world):
    """The revision's downgrade removes the probe. Upgrade puts it back."""
    del batch_world
    import os
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    url = migrated_engine.url.render_as_string(hide_password=False)
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", url)
    os.environ["DATABASE_URL"] = url
    try:
        command.downgrade(cfg, "0097_list_entry_code")
        with migrated_engine.connect() as conn:
            present = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public'
                      AND p.proname = 'batch_access_status'
                    """
                )
            ).scalar()
        assert present is None
    finally:
        command.upgrade(cfg, "head")
        os.environ.pop("DATABASE_URL", None)
        with migrated_engine.connect() as conn:
            restored = conn.execute(
                text("SELECT has_function_privilege('lims_app', :fn, 'EXECUTE')"),
                {"fn": FN},
            ).scalar()
        assert restored is True


def test_status_words_only(migrated_engine, batch_world):
    caller = batch_world["caller"]
    owner = batch_world["owner"]
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        try:
            hidden = _status(conn, caller["user_id"], owner["batch_id"])
            own = _status(conn, caller["user_id"], caller["batch_id"])
            missing = _status(conn, caller["user_id"], uuid4())
        finally:
            trans.rollback()
    assert hidden == "forbidden"
    assert own == "visible"
    assert missing == "not_found"
    for word in (hidden, own, missing):
        assert word in ("not_found", "forbidden", "visible")
        assert str(owner["client_id"]) not in word
        assert str(caller["client_id"]) not in word


def test_cross_client_is_403_without_identifiers(lims_app_client, batch_world):
    caller = batch_world["caller"]
    owner = batch_world["owner"]
    headers = _headers(caller["user_id"])
    paths = [
        f"/batches/{owner['batch_id']}",
        f"/batches/{owner['batch_id']}/containers",
        f"/batches/{owner['batch_id']}/tests",
    ]
    for path in paths:
        response = lims_app_client.get(path, headers=headers)
        assert response.status_code == 403, response.text
        body = response.json()
        assert body["detail"]["code"] == "batch_forbidden"
        assert body["detail"]["message"] == "Access denied"
        _assert_no_identifiers(response.text, *_needles(batch_world))

    patch = lims_app_client.patch(
        f"/batches/{owner['batch_id']}",
        headers=headers,
        json={"description": "nope"},
    )
    assert patch.status_code == 403, patch.text
    assert patch.json()["detail"]["code"] == "batch_forbidden"
    _assert_no_identifiers(patch.text, *_needles(batch_world))

    deleted = lims_app_client.delete(f"/batches/{owner['batch_id']}", headers=headers)
    assert deleted.status_code == 403, deleted.text
    assert deleted.json()["detail"]["code"] == "batch_forbidden"

    posted = lims_app_client.post(
        f"/batches/{owner['batch_id']}/containers",
        headers=headers,
        json={"container_id": str(uuid4())},
    )
    assert posted.status_code == 403, posted.text
    assert posted.json()["detail"]["code"] == "batch_forbidden"

    removed = lims_app_client.delete(
        f"/batches/{owner['batch_id']}/containers/{owner['container_id']}",
        headers=headers,
    )
    assert removed.status_code == 403, removed.text
    assert removed.json()["detail"]["code"] == "batch_forbidden"


def test_unknown_batch_is_404(lims_app_client, batch_world):
    headers = _headers(batch_world["caller"]["user_id"])
    missing = uuid4()
    for path in (
        f"/batches/{missing}",
        f"/batches/{missing}/containers",
        f"/batches/{missing}/tests",
    ):
        response = lims_app_client.get(path, headers=headers)
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == "Batch not found"
        assert "batch_forbidden" not in response.text


def test_own_client_is_200(lims_app_client, batch_world):
    caller = batch_world["caller"]
    owner = batch_world["owner"]
    headers = _headers(caller["user_id"])
    batch = lims_app_client.get(f"/batches/{caller['batch_id']}", headers=headers)
    assert batch.status_code == 200, batch.text
    assert batch.json()["name"] == caller["batch_name"]
    assert owner["batch_name"] not in batch.text
    assert owner["sample_name"] not in batch.text

    containers = lims_app_client.get(
        f"/batches/{caller['batch_id']}/containers", headers=headers
    )
    assert containers.status_code == 200, containers.text
    body = containers.json()
    assert len(body) == 1
    assert body[0]["name"] == caller["container_name"]
    assert body[0]["contents"][0]["sample_name"] == caller["sample_name"]

    tests = lims_app_client.get(
        f"/batches/{caller['batch_id']}/tests", headers=headers
    )
    assert tests.status_code == 200, tests.text
    assert len(tests.json()) == 1
    assert tests.json()[0]["name"] == caller["test_name"]


def test_mixed_batch_returns_only_the_callers_rows(lims_app_client, batch_world):
    caller = batch_world["caller"]
    owner = batch_world["owner"]
    headers = _headers(caller["user_id"])
    mixed = batch_world["mixed_id"]
    containers = lims_app_client.get(f"/batches/{mixed}/containers", headers=headers)
    assert containers.status_code == 200, containers.text
    names = [row["name"] for row in containers.json()]
    assert names == [caller["container_name"]]
    assert owner["container_name"] not in containers.text
    assert owner["sample_name"] not in containers.text
    assert str(owner["client_id"]) not in containers.text
    assert owner["client_name"] not in containers.text

    tests = lims_app_client.get(f"/batches/{mixed}/tests", headers=headers)
    assert tests.status_code == 200, tests.text
    test_names = [row["name"] for row in tests.json()]
    assert test_names == [caller["test_name"]]
    assert owner["test_name"] not in tests.text

    detail = lims_app_client.get(f"/batches/{mixed}", headers=headers)
    assert detail.status_code == 200, detail.text
    container_ids = [row["container_id"] for row in detail.json()["containers"]]
    assert container_ids == [str(caller["container_id"])]
    assert str(owner["container_id"]) not in detail.text
    assert owner["container_name"] not in detail.text
