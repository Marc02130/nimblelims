"""P1 data-parsers: versioned parsers, config validation, analysis-required runs."""
import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def instrument_and_analysis(client: TestClient, auth_headers, db_session):
    from models.analysis import Analysis

    t = client.post(
        "/v1/instrument-types",
        headers=auth_headers,
        json={"name": f"T-{uuid.uuid4().hex[:6]}"},
    ).json()
    inst = client.post(
        "/v1/instruments",
        headers=auth_headers,
        json={
            "name": f"I-{uuid.uuid4().hex[:6]}",
            "instrument_type_id": t["id"],
        },
    ).json()
    analysis = Analysis(
        name=f"A-{uuid.uuid4().hex[:6]}",
        method="EPA",
        active=True,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return inst, analysis


def _parser_config():
    return {
        "schema_version": "1",
        "delimiter": ",",
        "encoding": "utf-8",
        "skip_rows": 0,
        "header_row": 0,
        "columns": [
            {"source_col": "Well", "field_name": "well_position", "data_type": "string"},
            {"source_col": "Value", "field_name": "raw_value", "data_type": "float"},
        ],
        "well_col": "Well",
    }


def test_create_and_activate_data_parser(client, auth_headers, instrument_and_analysis):
    inst, analysis = instrument_and_analysis
    body = {
        "name": f"P-{uuid.uuid4().hex[:6]}",
        "instrument_id": inst["id"],
        "parser_config": _parser_config(),
        "analyses": [{"analysis_id": str(analysis.id), "is_default": True}],
        "activate": True,
    }
    r = client.post("/v1/data-parsers", headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["active"] is True
    assert data["version"] == 1
    assert data["version_group_id"] == data["id"]
    assert str(analysis.id) in [str(x) for x in data["analysis_ids"]]


def test_new_version_deactivates_prior_on_activate(
    client, auth_headers, instrument_and_analysis
):
    inst, analysis = instrument_and_analysis
    r1 = client.post(
        "/v1/data-parsers",
        headers=auth_headers,
        json={
            "name": f"P-{uuid.uuid4().hex[:6]}",
            "instrument_id": inst["id"],
            "parser_config": _parser_config(),
            "analyses": [{"analysis_id": str(analysis.id), "is_default": True}],
            "activate": True,
        },
    )
    assert r1.status_code == 201, r1.text
    v1 = r1.json()

    r2 = client.post(
        f"/v1/data-parsers/groups/{v1['version_group_id']}/versions",
        headers=auth_headers,
        json={
            "parser_config": _parser_config(),
            "analyses": [{"analysis_id": str(analysis.id), "is_default": True}],
            "activate": True,
        },
    )
    assert r2.status_code == 201, r2.text
    v2 = r2.json()
    assert v2["version"] == 2
    assert v2["active"] is True

    r1g = client.get(f"/v1/data-parsers/{v1['id']}", headers=auth_headers)
    assert r1g.json()["active"] is False


def test_test_suite_csv(client, auth_headers):
    csv_bytes = b"Well,Value\nA1,1.5\nB1,2.0\n"
    files = [("files", ("t.csv", io.BytesIO(csv_bytes), "text/csv"))]
    r = client.post(
        "/v1/data-parsers/test",
        headers=auth_headers,
        data={"parser_config": json.dumps(_parser_config())},
        files=files,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["all_clean"] is True
    assert body["files"][0]["row_count"] == 2


def test_create_run_requires_analysis(client, auth_headers, db_session):
    from models.experiment import ExperimentTemplate

    tpl = ExperimentTemplate(
        name=f"Tpl-{uuid.uuid4().hex[:6]}",
        template_definition={"lifecycle_type": "standard", "protocol_steps": []},
    )
    db_session.add(tpl)
    db_session.commit()
    db_session.refresh(tpl)

    r = client.post(
        "/v1/lims-runs",
        headers=auth_headers,
        json={
            "name": f"Run-{uuid.uuid4().hex[:6]}",
            "experiment_template_id": str(tpl.id),
        },
    )
    # analysis_id required by schema
    assert r.status_code in (400, 422), r.text
