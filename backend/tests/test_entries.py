"""Phase 2 API tests for Experiment Entries."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


VALID_TEMPLATE_DEF = {
    "experiment_name": "Entry Test",
    "protocol_steps": ["a"],
    "transfer_steps": [],
    "result_columns": [],
    "mandatory_review_count": 0,
    "entries": [
        {
            "entry_type": "experiment_detail",
            "name": "Conditions",
            "sort_order": 0,
            "fields": [],
        },
        {
            "entry_type": "sample_data",
            "name": "QC Data",
            "sort_order": 1,
            "fields": [],
        },
    ],
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def template_with_entries(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl Entries {uuid4().hex[:8]}",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def experiment(client: TestClient, auth_headers, template_with_entries):
    r = client.post(
        "/v1/experiments",
        json={
            "name": f"Exp {uuid4().hex[:8]}",
            "experiment_template_id": template_with_entries["id"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestEntries:
    def test_auto_instantiate_on_experiment_create(
        self, client: TestClient, auth_headers, experiment
    ):
        r = client.get(
            f"/v1/experiments/{experiment['id']}/entries",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2
        names = {e["name"] for e in body["entries"]}
        assert "Conditions" in names
        assert "QC Data" in names

    def test_create_entry_manual_and_values(
        self, client: TestClient, auth_headers, experiment, db_session, test_admin_user
    ):
        # Create a FieldDefinition
        from models.field_definition import FieldDefinition

        fd = FieldDefinition(
            name=f"note_{uuid4().hex[:6]}",
            entity_type="experiment",
            data_type="text",
            display_name="Note",
            is_materialized_column=False,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        # BaseModel requires unique name - FieldDefinition extends BaseModel
        db_session.add(fd)
        db_session.commit()

        r = client.post(
            f"/v1/experiments/{experiment['id']}/entries",
            json={
                "experiment_id": experiment["id"],
                "entry_type": "experiment_detail",
                "name": "Manual Notes",
                "fields": [
                    {
                        "field_definition_id": str(fd.id),
                        "sort_order": 0,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        entry = r.json()
        assert len(entry["field_definition_links"]) == 1

        r = client.put(
            f"/v1/entries/{entry['id']}/values",
            json={
                "values": [
                    {
                        "field_definition_id": str(fd.id),
                        "value_text": "hello world",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()[0]["value_text"] == "hello world"

        # Upsert again
        r = client.put(
            f"/v1/entries/{entry['id']}/values",
            json={
                "values": [
                    {
                        "field_definition_id": str(fd.id),
                        "value_text": "updated",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()[0]["value_text"] == "updated"

        r = client.get(f"/v1/entries/{entry['id']}/values", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_invalid_entry_type(self, client: TestClient, auth_headers, experiment):
        r = client.post(
            f"/v1/experiments/{experiment['id']}/entries",
            json={
                "experiment_id": experiment["id"],
                "entry_type": "not_real",
                "name": "Bad",
            },
            headers=auth_headers,
        )
        assert r.status_code == 400
