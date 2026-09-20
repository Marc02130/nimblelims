"""E-14 sample type transition catalog mutate API (config:edit)."""

from uuid import uuid4

from fastapi.testclient import TestClient
from models.list import List as ListModel, ListEntry


def _auth(client: TestClient, username: str, password: str):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _two_types(db_session, user):
    lst = ListModel(
        name=f"sample_types_{uuid4().hex[:8]}",
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(lst)
    db_session.flush()
    source = ListEntry(
        list_id=lst.id,
        name=f"src_{uuid4().hex[:6]}",
        created_by=user.id,
        modified_by=user.id,
    )
    dest = ListEntry(
        list_id=lst.id,
        name=f"dst_{uuid4().hex[:6]}",
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add_all([source, dest])
    db_session.commit()
    return source, dest


def test_create_list_and_refuse_without_config_edit(
    client: TestClient, test_user, db_session
):
    source, dest = _two_types(db_session, test_user)
    tech = _auth(client, "testuser", "testpassword")
    r = client.post(
        "/v1/sample-type-transitions",
        json={
            "source_sample_type": str(source.id),
            "operation": "aliquot",
            "allowed_dest_sample_type": str(dest.id),
        },
        headers=tech,
    )
    assert r.status_code == 403, r.text


def test_crud_roundtrip(client: TestClient, test_admin_user, db_session):
    source, dest = _two_types(db_session, test_admin_user)
    headers = _auth(client, "admin", "adminpassword")
    created = client.post(
        "/v1/sample-type-transitions",
        json={
            "source_sample_type": str(source.id),
            "operation": "aliquot",
            "allowed_dest_sample_type": str(dest.id),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["operation"] == "aliquot"
    assert body["source_sample_type_name"] == source.name
    assert body["allowed_dest_sample_type_name"] == dest.name
    row_id = body["id"]

    listed = client.get("/v1/sample-type-transitions", headers=headers)
    assert listed.status_code == 200
    assert any(row["id"] == row_id for row in listed.json())

    dup = client.post(
        "/v1/sample-type-transitions",
        json={
            "source_sample_type": str(source.id),
            "operation": "aliquot",
            "allowed_dest_sample_type": str(dest.id),
        },
        headers=headers,
    )
    assert dup.status_code == 409, dup.text
    assert dup.json()["detail"]["code"] == "transition_exists"

    patched = client.patch(
        f"/v1/sample-type-transitions/{row_id}",
        json={"operation": "pool"},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["operation"] == "pool"

    deleted = client.delete(
        f"/v1/sample-type-transitions/{row_id}", headers=headers
    )
    assert deleted.status_code == 204, deleted.text
    after = client.get("/v1/sample-type-transitions", headers=headers).json()
    match = next(row for row in after if row["id"] == row_id)
    assert match["active"] is False


def test_template_default_dest_sample_type_roundtrip(
    client: TestClient, test_admin_user, db_session
):
    _source, dest = _two_types(db_session, test_admin_user)
    headers = _auth(client, "admin", "adminpassword")
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl dest {uuid4().hex[:8]}",
            "template_definition": {
                "entries": [
                    {
                        "predefined_entry_key": "aliquot_pool_plan",
                        "name": "Aliquot / pool plan",
                        "sort_order": 0,
                        "config": {
                            "method": "aliquot_by_volume",
                            "default_dest_sample_type": str(dest.id),
                        },
                    }
                ]
            },
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    plan = next(
        e
        for e in r.json()["template_definition"]["entries"]
        if e.get("predefined_entry_key") == "aliquot_pool_plan"
    )
    assert plan["config"]["default_dest_sample_type"] == str(dest.id)
    assert plan["config"]["method"] == "aliquot_by_volume"
