"""P0 data-parsers: instrument types, instruments, cro sources CRUD."""
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
            "vendor": "Agilent",
            "model": "6495C",
            "description": "LCMS",
        },
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    data = r.json()
    type_id = data["id"]
    assert data["vendor"] == "Agilent"
    assert data["active"] is True

    r = client.get("/v1/instrument-types", headers=config_headers)
    assert r.status_code == 200
    assert any(t["id"] == type_id for t in r.json())

    r = client.get(f"/v1/instrument-types/{type_id}", headers=config_headers)
    assert r.status_code == 200
    assert r.json()["model"] == "6495C"

    r = client.patch(
        f"/v1/instrument-types/{type_id}",
        headers=config_headers,
        json={"model": "6495D"},
    )
    assert r.status_code == 200
    assert r.json()["model"] == "6495D"

    r = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={"name": data["name"], "vendor": "X"},
    )
    assert r.status_code == 400


def test_instrument_instance_requires_type(client, config_headers):
    t = client.post(
        "/v1/instrument-types",
        headers=config_headers,
        json={"name": f"T-{uuid.uuid4().hex[:8]}", "vendor": "Thermo"},
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
    assert r.status_code == 204
    r = client.get(f"/v1/instruments/{inst['id']}", headers=config_headers)
    assert r.status_code == 200
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


def test_catalog_write_requires_config_edit(client, tech_headers):
    r = client.post(
        "/v1/instrument-types",
        headers=tech_headers,
        json={"name": f"Nope-{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code in (401, 403)
