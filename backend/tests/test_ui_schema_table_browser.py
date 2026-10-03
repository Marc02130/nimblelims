"""Schema table browser + side-link relations (stem ``ui-schema-tables-cleanup``).

Covers the product locks:
* Tables list = every allow-listed lab table + system reference tables (``lists``
  first); engine internals hidden; Lab vs System badge.
* System columns (id, timestamps, created-by, relationship FKs, ``list_id``)
  are not editable and not removable. Reflected built-ins are described only.
* One-to-many / one-to-one are registry entries over a *real* FK column on the
  child. No junction tables; many-to-many refused; declaring never issues DDL.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.services import ui_schema_catalog as catalog
from app.services.ui_schema_service import UiSchemaService
from models.ui_schema import SchemaTable
from models.user import Permission, Role, User, role_permissions


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _tables(client: TestClient, token: str) -> dict[str, dict]:
    r = client.get("/v1/schema/tables", headers=_auth(token))
    assert r.status_code == 200, r.text
    return {t["physical_name"]: t for t in r.json()}


def _columns(client: TestClient, token: str, table_id: str) -> dict[str, dict]:
    r = client.get("/v1/schema/columns", params={"table_id": table_id}, headers=_auth(token))
    assert r.status_code == 200, r.text
    return {c["physical_name"]: c for c in r.json()}


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
        db_session.execute(role_permissions.insert().values(role_id=role.id, permission_id=p.id))
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


# ----------------------------------------------------------------- catalog rules


def test_allow_list_classifies_lab_system_and_hides_internals():
    assert catalog.kind_for("samples") == "core"
    assert catalog.kind_for("projects") == "core"
    assert catalog.kind_for("lists") == "system"
    assert catalog.kind_for("list_entries") == "system"
    for internal in catalog.ENGINE_INTERNAL:
        assert catalog.kind_for(internal) is None, internal
    assert "alembic_version" in catalog.ENGINE_INTERNAL
    assert "revoked_tokens" in catalog.ENGINE_INTERNAL
    assert "ui_schema_ddl_log" in catalog.ENGINE_INTERNAL
    assert not set(catalog.LAB_TABLES) & set(catalog.SYSTEM_TABLES)
    assert not set(catalog.LAB_TABLES) & set(catalog.ENGINE_INTERNAL)
    assert catalog.category_for_kind("core") == "lab"
    assert catalog.category_for_kind("ui") == "lab"
    assert catalog.category_for_kind("system") == "system"


@pytest.mark.parametrize(
    "name,kwargs,expected",
    [
        ("id", dict(is_platform=True, is_identity=False, is_fk=False, fk_table=None, table_kind="core"), "platform"),
        ("created_at", dict(is_platform=False, is_identity=False, is_fk=False, fk_table=None, table_kind="core"), "platform"),
        ("created_by", dict(is_platform=False, is_identity=False, is_fk=True, fk_table="users", table_kind="core"), "platform"),
        ("project_id", dict(is_platform=False, is_identity=False, is_fk=True, fk_table="projects", table_kind="core"), "relationship_key"),
        ("list_id", dict(is_platform=False, is_identity=False, is_fk=True, fk_table="lists", table_kind="core"), "relationship_key"),
        ("name", dict(is_platform=False, is_identity=True, is_fk=False, fk_table=None, table_kind="core"), "identity"),
        ("name", dict(is_platform=False, is_identity=False, is_fk=False, fk_table=None, table_kind="system"), "system_table"),
        # A list binding is a lab column, not a relationship key.
        ("colour", dict(is_platform=False, is_identity=False, is_fk=True, fk_table="list_entries", table_kind="core"), None),
        ("lab_note", dict(is_platform=False, is_identity=False, is_fk=False, fk_table=None, table_kind="ui"), None),
    ],
)
def test_system_column_rules(name, kwargs, expected):
    assert catalog.is_system_column(name, **kwargs) == expected


def test_pg_type_mapping_keeps_p1_and_marks_keys():
    assert catalog.map_pg_type("varchar", False, None) == "text"
    assert catalog.map_pg_type("numeric", False, None) == "numeric"
    assert catalog.map_pg_type("int4", False, None) == "integer"
    assert catalog.map_pg_type("bool", False, None) == "boolean"
    assert catalog.map_pg_type("timestamp", False, None) == "timestamptz"
    assert catalog.map_pg_type("uuid", True, "list_entries") == "list"
    assert catalog.map_pg_type("uuid", True, "projects") == "uuid"
    assert catalog.map_pg_type("jsonb", False, None) == "jsonb"
    assert catalog.map_pg_type("bytea", False, None) == "other"


# ------------------------------------------------------------- tables list filter


def test_tables_list_shows_lab_tables_and_system_reference_tables(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    for lab in ("samples", "containers", "tests", "results", "batches", "projects"):
        assert lab in tables, f"{lab} missing from Schema tables"
        assert tables[lab]["category"] == "lab"
        assert tables[lab]["kind"] == "core"
    assert "lists" in tables
    assert tables["lists"]["category"] == "system"
    assert tables["lists"]["kind"] == "system"
    assert tables["lists"]["display_name"] == "Lists"
    assert tables["list_entries"]["category"] == "system"
    assert tables["units"]["category"] == "system"
    assert tables["samples"]["display_name"] == "Samples"
    assert tables["samples"]["column_count"] > 13, "Samples should describe every real column"


def test_tables_list_hides_engine_internals(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    for internal in (
        "schema_tables",
        "schema_columns",
        "schema_relations",
        "schema_privileges",
        "schema_changes",
        "ui_schema_ddl_log",
        "alembic_version",
        "revoked_tokens",
        "login_throttle",
        "custom_attributes_config",
        "permissions",
        "role_permissions",
    ):
        assert internal not in tables, f"{internal} must stay hidden"


def test_tables_list_only_registers_tables_that_exist(client: TestClient, admin_token: str, db_session: Session):
    tables = _tables(client, admin_token)
    present = {
        r[0]
        for r in db_session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        ).all()
    }
    for name in tables:
        assert name in present, f"{name} registered but not in Postgres"


def test_system_tables_cannot_take_new_fields_or_be_removed(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    lists = tables["lists"]
    assert lists["can_add_columns"] is False
    assert lists["can_remove"] is False
    r = client.post(
        "/v1/schema/columns",
        json={"table_id": lists["id"], "display_name": "Nope", "data_type": "text"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    r = client.post(f"/v1/schema/tables/{lists['id']}/deprecate", headers=_auth(admin_token))
    assert r.status_code == 422, r.text
    r = client.post(
        f"/v1/schema/tables/{lists['id']}/drop",
        json={"confirm": True},
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    assert tables["samples"]["can_add_columns"] is True
    assert tables["tests"]["can_add_columns"] is False
    assert tables["samples"]["can_remove"] is False


def test_layout_edit_can_browse_tables_and_columns(client: TestClient, db_session: Session, test_admin_user: User):
    _, token = _user_with_perms(
        db_session,
        test_admin_user,
        role_name="Layout Clerk",
        username="layout-browse",
        perm_names=["layout:edit", "sample:read"],
    )
    tables = _tables(client, token)
    assert "lists" in tables and "samples" in tables
    cols = _columns(client, token, tables["lists"]["id"])
    assert "name" in cols


# ------------------------------------------------------- read-only system columns


def test_reflected_columns_carry_fk_facts(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    tests_cols = _columns(client, admin_token, tables["tests"]["id"])
    sample_id = tests_cols["sample_id"]
    assert sample_id["is_fk"] is True
    assert sample_id["fk_table"] == "samples"
    assert sample_id["data_type"] == "uuid"
    assert sample_id["is_system"] is True
    assert sample_id["system_reason"] == "relationship_key"
    assert sample_id["editable"] is False
    assert sample_id["origin"] == "reflected"
    # A list binding on a lab table is a list column, not a relationship key.
    status_col = tests_cols["status"]
    assert status_col["fk_table"] == "list_entries"
    assert status_col["data_type"] == "list"
    assert status_col["is_system"] is False
    # ...but a built-in column owned by migrations is still not editable here.
    assert status_col["editable"] is False


def test_platform_and_fk_columns_are_locked_in_api(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    tests_cols = _columns(client, admin_token, tables["tests"]["id"])
    for name in ("id", "created_at", "created_by", "sample_id"):
        col = tests_cols[name]
        assert col["is_system"] is True, name
        r = client.post(f"/v1/schema/columns/{col['id']}/deprecate", headers=_auth(admin_token))
        assert r.status_code == 422, f"{name}: {r.text}"
        r = client.post(
            f"/v1/schema/columns/{col['id']}/drop",
            json={"confirm": True},
            headers=_auth(admin_token),
        )
        assert r.status_code == 422, f"{name}: {r.text}"


def test_list_id_on_list_entries_is_system(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    cols = _columns(client, admin_token, tables["list_entries"]["id"])
    list_id = cols["list_id"]
    assert list_id["is_fk"] is True and list_id["fk_table"] == "lists"
    assert list_id["is_system"] is True
    assert list_id["editable"] is False
    for col in cols.values():
        assert col["is_system"] is True, col["physical_name"]
        assert col["editable"] is False, col["physical_name"]
    r = client.post(f"/v1/schema/columns/{list_id['id']}/deprecate", headers=_auth(admin_token))
    assert r.status_code == 422, r.text


def test_reflected_builtin_lab_column_cannot_be_dropped(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    cols = _columns(client, admin_token, tables["samples"]["id"])
    desc = cols["description"]
    assert desc["is_system"] is False
    assert desc["origin"] == "reflected"
    assert desc["editable"] is False
    r = client.post(
        f"/v1/schema/columns/{desc['id']}/drop",
        json={"confirm": True},
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    assert "migrations" in r.json()["detail"]


def test_reflected_columns_stay_out_of_extra_fields_path(db_session: Session, test_admin_user: User):
    svc = UiSchemaService(db_session, test_admin_user)
    svc.ensure_catalog(only=("samples",))
    extras = svc.extra_sample_columns()
    assert all(c.origin == "ui" for c in extras)
    assert "description" not in {c.physical_name for c in extras}


def test_catalog_sync_is_idempotent(db_session: Session, test_admin_user: User):
    svc = UiSchemaService(db_session, test_admin_user)
    svc.ensure_catalog()
    first = {
        (t.physical_name, len(t.columns))
        for t in db_session.query(SchemaTable).filter(SchemaTable.client_id == test_admin_user.client_id).all()
    }
    svc.ensure_catalog()
    second = {
        (t.physical_name, len(t.columns))
        for t in db_session.query(SchemaTable).filter(SchemaTable.client_id == test_admin_user.client_id).all()
    }
    assert first == second


# ------------------------------------------------------------------ relations


def test_one_to_many_relation_over_real_fk(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    project_id = samples_cols["project_id"]
    assert project_id["is_fk"] and project_id["fk_table"] == "projects"
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Project samples",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": project_id["id"],
            "cardinality": "one_to_many",
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cardinality"] == "one_to_many"
    assert body["from_physical_name"] == "projects"
    assert body["to_physical_name"] == "samples"
    assert body["fk_physical_name"] == "project_id"

    listed = client.get("/v1/schema/relations", headers=_auth(admin_token)).json()
    assert any(x["id"] == body["id"] for x in listed)

    # Parent shows a read-only link to the child table; child shows its parent.
    parent_links = client.get(f"/v1/schema/tables/{tables['projects']['id']}/links", headers=_auth(admin_token))
    assert parent_links.status_code == 200, parent_links.text
    assert [c["to_physical_name"] for c in parent_links.json()["children"]] == ["samples"]
    child_links = client.get(f"/v1/schema/tables/{tables['samples']['id']}/links", headers=_auth(admin_token)).json()
    assert [p["from_physical_name"] for p in child_links["parents"]] == ["projects"]
    keys = {k["physical_name"]: k for k in child_links["keys"]}
    assert keys["project_id"]["fk_table_id"] == tables["projects"]["id"]
    # list bindings are not relationship keys
    assert "sample_type" not in keys

    tables_after = _tables(client, admin_token)
    assert tables_after["projects"]["relation_count"] == 1
    assert tables_after["samples"]["relation_count"] == 1

    dup = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Again",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": project_id["id"],
        },
        headers=_auth(admin_token),
    )
    assert dup.status_code == 409, dup.text

    gone = client.delete(f"/v1/schema/relations/{body['id']}", headers=_auth(admin_token))
    assert gone.status_code == 204, gone.text
    assert client.get("/v1/schema/relations", headers=_auth(admin_token)).json() == []


def test_relation_requires_real_fk_to_parent(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    # Not a foreign key at all.
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Bogus",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["description"]["id"],
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    # A foreign key, but to a different parent.
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Wrong parent",
            "from_table_id": tables["tests"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["project_id"]["id"],
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    # Column must belong to the child table.
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Wrong child",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["tests"]["id"],
            "fk_column_id": samples_cols["project_id"]["id"],
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text


def test_one_to_one_requires_unique_key(client: TestClient, admin_token: str, db_session: Session):
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "One project per sample?",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["project_id"]["id"],
            "cardinality": "one_to_one",
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text
    assert "UNIQUE" in r.json()["detail"]

    # A dependent table with a UNIQUE FK (made by migration, not by the UI).
    db_session.execute(
        text(
            "CREATE TABLE x_sample_passport ("
            " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
            " client_id uuid NOT NULL REFERENCES clients(id),"
            " sample_id uuid NOT NULL UNIQUE REFERENCES samples(id),"
            " created_at timestamptz NOT NULL DEFAULT now(),"
            " active boolean NOT NULL DEFAULT true)"
        )
    )
    admin = db_session.query(User).filter(User.username == "admin").one()
    passport = SchemaTable(
        client_id=admin.client_id,
        display_name="Sample passport",
        physical_name="x_sample_passport",
        kind="ui",
        status="active",
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(passport)
    db_session.commit()
    cols = _columns(client, admin_token, str(passport.id))
    assert cols["sample_id"]["is_unique"] is True
    assert cols["sample_id"]["is_system"] is True
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Passport",
            "from_table_id": tables["samples"]["id"],
            "to_table_id": str(passport.id),
            "fk_column_id": cols["sample_id"]["id"],
            "cardinality": "one_to_one",
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    assert r.json()["cardinality"] == "one_to_one"
    # UI-created table shows up on the list as Lab.
    assert _tables(client, admin_token)["x_sample_passport"]["category"] == "lab"


def test_many_to_many_and_junctions_are_refused(client: TestClient, admin_token: str):
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Tags",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["project_id"]["id"],
            "cardinality": "many_to_many",
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 422, r.text


def test_declaring_relation_does_not_mutate_database(client: TestClient, admin_token: str, db_session: Session):
    before = {
        (r[0], r[1])
        for r in db_session.execute(
            text("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public'")
        ).all()
    }
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Parent sample",
            "from_table_id": tables["samples"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["parent_sample_id"]["id"],
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    after = {
        (r[0], r[1])
        for r in db_session.execute(
            text("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public'")
        ).all()
    }
    assert before == after


def test_relations_need_schema_edit(client: TestClient, db_session: Session, test_admin_user: User, admin_token: str):
    tables = _tables(client, admin_token)
    samples_cols = _columns(client, admin_token, tables["samples"]["id"])
    _, token = _user_with_perms(
        db_session,
        test_admin_user,
        role_name="Layout Clerk",
        username="layout-rel",
        perm_names=["layout:edit", "sample:read"],
    )
    r = client.post(
        "/v1/schema/relations",
        json={
            "display_name": "Nope",
            "from_table_id": tables["projects"]["id"],
            "to_table_id": tables["samples"]["id"],
            "fk_column_id": samples_cols["project_id"]["id"],
        },
        headers=_auth(token),
    )
    assert r.status_code == 403, r.text
    assert client.get("/v1/schema/relations", headers=_auth(token)).status_code == 200
