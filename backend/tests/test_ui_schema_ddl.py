"""UI schema DDL: S-UI-1…6, allow-list, types, deprecate, no JSONB-as-config."""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from models.user import Permission, Role, User, role_permissions


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user_with_perms(
    db_session: Session,
    test_admin_user: User,
    *,
    role_name: str,
    username: str,
    perm_names: list[str],
):
    role = Role(name=role_name, description=role_name)
    db_session.add(role)
    db_session.flush()
    perms = db_session.query(Permission).filter(Permission.name.in_(perm_names)).all()
    for p in perms:
        db_session.execute(
            role_permissions.insert().values(role_id=role.id, permission_id=p.id)
        )
    user = User(
        name=username,
        username=username,
        email=f"{username}-{uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("Labtech1234!"),
        role_id=role.id,
        client_id=test_admin_user.client_id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": role_name,
            "permissions": perm_names,
        }
    )
    return user, token


def test_schema_edit_required_for_create_table(
    client: TestClient, db_session: Session, test_admin_user: User, admin_token: str
):
    _, tech_token = _user_with_perms(
        db_session,
        test_admin_user,
        role_name="Lab Technician",
        username="tech-schema",
        perm_names=["sample:read", "sample:update", "config:edit", "test:assign"],
    )
    r = client.post(
        "/v1/schema/tables",
        json={"display_name": "Lot Notes"},
        headers=_auth(tech_token),
    )
    assert r.status_code == 403, r.text


def test_layout_edit_cannot_create_table(
    client: TestClient, db_session: Session, test_admin_user: User
):
    _, token = _user_with_perms(
        db_session,
        test_admin_user,
        role_name="Layout Clerk",
        username="layout-clerk",
        perm_names=["layout:edit", "sample:read"],
    )
    r = client.post(
        "/v1/schema/tables",
        json={"display_name": "Should Fail"},
        headers=_auth(token),
    )
    assert r.status_code == 403, r.text


def test_jsonb_type_rejected(
    client: TestClient, admin_token: str, db_session: Session, test_admin_user: User
):
    tables = client.get("/v1/schema/tables", headers=_auth(admin_token))
    assert tables.status_code == 200, tables.text
    samples = next(t for t in tables.json() if t["physical_name"] == "samples")
    r = client.post(
        "/v1/schema/columns",
        json={
            "table_id": samples["id"],
            "display_name": "Blob",
            "data_type": "jsonb",
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text


def test_privilege_put_does_not_mint_schema_edit(
    client: TestClient, db_session: Session, test_admin_user: User, admin_token: str
):
    tables = client.get("/v1/schema/tables", headers=_auth(admin_token))
    assert tables.status_code == 200, tables.text
    samples = next(t for t in tables.json() if t["physical_name"] == "samples")
    tech, _ = _user_with_perms(
        db_session,
        test_admin_user,
        role_name="Lab Tech Priv",
        username="tech-priv",
        perm_names=["sample:read", "sample:update"],
    )
    r = client.put(
        "/v1/schema/privileges",
        json=[
            {
                "role_id": str(tech.role_id),
                "table_id": samples["id"],
                "access": "write",
            }
        ],
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    names = [
        p.name
        for p in db_session.query(Permission)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .filter(role_permissions.c.role_id == tech.role_id)
        .all()
    ]
    assert "schema:edit" not in names


def test_drop_requires_confirm(
    client: TestClient, admin_token: str
):
    tables = client.get("/v1/schema/tables", headers=_auth(admin_token))
    assert tables.status_code == 200
    samples = next(t for t in tables.json() if t["physical_name"] == "samples")
    cols = client.get(
        "/v1/schema/columns",
        params={"table_id": samples["id"]},
        headers=_auth(admin_token),
    )
    ident = next(c for c in cols.json() if c["physical_name"] == "name")
    r = client.post(
        f"/v1/schema/columns/{ident['id']}/drop",
        json={"confirm": False},
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text


def test_identity_column_cannot_deprecate(
    client: TestClient, admin_token: str
):
    tables = client.get("/v1/schema/tables", headers=_auth(admin_token))
    samples = next(t for t in tables.json() if t["physical_name"] == "samples")
    cols = client.get(
        "/v1/schema/columns",
        params={"table_id": samples["id"]},
        headers=_auth(admin_token),
    )
    ident = next(c for c in cols.json() if c["physical_name"] == "parent_sample_id")
    r = client.post(
        f"/v1/schema/columns/{ident['id']}/deprecate",
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text


def test_create_table_real_postgres(migrated_engine):
    import pytest
    from sqlalchemy.exc import DatabaseError

    conn = migrated_engine.connect()
    trans = conn.begin()
    try:
        slug = "x_lot_notes"
        conn.execute(text("SELECT ui_schema_create_table(:n)"), {"n": slug})
        present = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name='client_id'"
            ),
            {"t": slug},
        ).scalar()
        assert present
        forced = conn.execute(
            text(
                "SELECT c.relforcerowsecurity FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:t"
            ),
            {"t": slug},
        ).scalar()
        assert forced is True
        conn.execute(
            text("SELECT ui_schema_add_column(:t,:c,:ty,:n,:fk)"),
            {"t": slug, "c": "notes", "ty": "text", "n": True, "fk": False},
        )
        col = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name='notes'"
            ),
            {"t": slug},
        ).scalar()
        assert col
        with pytest.raises(DatabaseError):
            conn.execute(text("SELECT ui_schema_create_table('samples')"))
    finally:
        trans.rollback()
        conn.close()


def test_add_column_rejects_asked_for_physical():
    from app.services.ui_schema_service import ADD_COLUMN_OUT

    assert "asked_for" in ADD_COLUMN_OUT
    assert "routing_map" in ADD_COLUMN_OUT


def test_ddl_log_seq_not_null(db_session: Session, test_admin_user: User):
    """A: ORM must not INSERT NULL seq (UAT Fail 500 NotNullViolation)."""
    from models.ui_schema import SchemaChange, UiSchemaDdlLog

    change = SchemaChange(
        client_id=test_admin_user.client_id,
        actor_id=test_admin_user.id,
        op="create_table",
        table_physical="x_lot_notes",
        after_status="active",
    )
    db_session.add(change)
    db_session.flush()
    log = UiSchemaDdlLog(
        client_id=test_admin_user.client_id,
        change_id=change.id,
        op="create_table",
        table_physical="x_lot_notes",
    )
    db_session.add(log)
    db_session.flush()
    assert log.seq is not None


def test_add_column_on_samples_real_postgres(migrated_engine):
    """B: ADD COLUMN on samples must succeed (schema_apply was not owner)."""
    conn = migrated_engine.connect()
    trans = conn.begin()
    col = f"lab_note_{uuid4().hex[:8]}"
    try:
        conn.execute(
            text("SELECT ui_schema_add_column(:t,:c,:ty,:n,:fk)"),
            {"t": "samples", "c": col, "ty": "text", "n": True, "fk": False},
        )
        present = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='samples' AND column_name=:c"
            ),
            {"c": col},
        ).scalar()
        assert present
    finally:
        trans.rollback()
        conn.close()
