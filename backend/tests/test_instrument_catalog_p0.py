"""Instrument types (list), instruments, and CRO sources. No DELETE routes."""
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def config_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def tech_headers(client: TestClient, test_user):
    r = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_instrument_type_crud(client, config_headers):
    r = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={
            "name": f"Type-{uuid.uuid4().hex[:8]}",
            "description": "LCMS",
        },
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    data = r.json()
    type_id = data["id"]
    assert data["active"] is True
    assert "vendor" not in data or data.get("vendor") in (None, "")

    r = client.get("/v1/instrument-types", headers=config_headers)
    assert r.status_code == 200
    assert any(t["id"] == type_id for t in r.json())

    r = client.get(f"/v1/instrument-types/{type_id}", headers=config_headers)
    assert r.status_code == 200
    assert r.json()["description"] == "LCMS"

    r = client.patch(
        f"/v1/instrument-types/{type_id}",
        headers=config_headers,
        json={"description": "LC-MS updated"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "LC-MS updated"

    r = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={"name": data["name"]},
    )
    assert r.status_code == 400


def test_instrument_instance_requires_type(client, config_headers):
    t = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={"name": f"T-{uuid.uuid4().hex[:8]}"},
    ).json()

    r = client.post(
        "/v1/instruments",
        headers=config_headers,
        json={
            "name": f"LCMS-{uuid.uuid4().hex[:6]}",
            "instrument_type_id": t["id"],
            "serial_number": f"SN-{uuid.uuid4().hex[:8]}",
        },
    )
    assert r.status_code == 201, r.text
    inst = r.json()
    assert inst["instrument_type_id"] == t["id"]
    assert inst["instrument_type_name"] == t["name"]
    assert inst["status"] == "in_service"

    r = client.post(
        "/v1/instruments",
        headers=config_headers,
        json={
            "name": f"Bad-{uuid.uuid4().hex[:6]}",
            "instrument_type_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 400

    r = client.delete(f"/v1/instruments/{inst['id']}", headers=config_headers)
    assert r.status_code == 405
    r = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=config_headers,
        json={"status": "retired"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "retired"
    assert r.json()["active"] is False


def test_cro_source_crud(client, config_headers):
    name = f"CRO-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/v1/cro-sources",
        headers=config_headers,
        json={"name": name, "description": "Metals export"},
    )
    assert r.status_code == 201, r.text
    cro_id = r.json()["id"]

    r = client.patch(
        f"/v1/cro-sources/{cro_id}",
        headers=config_headers,
        json={"description": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Updated"

    r = client.get("/v1/cro-sources", headers=config_headers)
    assert r.status_code == 200
    assert any(c["id"] == cro_id for c in r.json())

    r = client.delete(f"/v1/cro-sources/{cro_id}", headers=config_headers)
    assert r.status_code == 405
    r = client.patch(
        f"/v1/cro-sources/{cro_id}",
        headers=config_headers,
        json={"active": False},
    )
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_catalog_write_requires_config_edit(client, tech_headers):
    r = client.post(
        "/v1/instrument-types",
        headers=tech_headers,
        json={"name": f"Nope-{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code in (401, 403)


def test_no_delete_routes_on_instrument_catalog(client, config_headers):
    t = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={"name": f"T-{uuid.uuid4().hex[:8]}"},
    ).json()
    assert client.delete(f"/v1/instrument-types/{t['id']}", headers=config_headers).status_code == 405
    inst = client.post(
        "/v1/instruments",
        headers=config_headers,
        json={"name": f"I-{uuid.uuid4().hex[:6]}", "instrument_type_id": t["id"]},
    ).json()
    assert client.delete(f"/v1/instruments/{inst['id']}", headers=config_headers).status_code == 405
    cro = client.post(
        "/v1/cro-sources",
        headers=config_headers,
        json={"name": f"CRO-{uuid.uuid4().hex[:8]}"},
    ).json()
    assert client.delete(f"/v1/cro-sources/{cro['id']}", headers=config_headers).status_code == 405
    retired = client.patch(
        f"/v1/instrument-types/{t['id']}",
        headers=config_headers,
        json={"active": False, "reason": "retire unused type"},
    )
    assert retired.status_code == 200
    assert retired.json()["active"] is False
