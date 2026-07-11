"""
Phase 1 API tests for ELN Processes:
  - Process CRUD
  - Ordered steps (template refs)
  - Sample assign / remove / advance
  - RBAC (experiment:manage required)
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


VALID_TEMPLATE_DEF = {
    "experiment_name": "ELN Process Test",
    "description": "test",
    "protocol_steps": ["step 1"],
    "transfer_steps": [],
    "result_columns": [],
    "acceptance_criteria": "",
    "mandatory_review_count": 0,
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def client_headers(client: TestClient, client_user_token):
    return {"Authorization": f"Bearer {client_user_token}"}


@pytest.fixture
def template_a(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"TplA {uuid4().hex[:8]}",
            "description": "a",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def template_b(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"TplB {uuid4().hex[:8]}",
            "description": "b",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def sample_id(db_session, test_admin_user, test_org):
    """Create a minimal sample via ORM (required FKs stubbed like other tests)."""
    from datetime import datetime, timedelta
    from models.sample import Sample
    from models.project import Project
    from models.list import List, ListEntry

    lst = List(name=f"eln_list_{uuid4().hex[:6]}", description="test")
    db_session.add(lst)
    db_session.flush()

    sample_type = ListEntry(list_id=lst.id, name=f"type_{uuid4().hex[:4]}")
    status = ListEntry(list_id=lst.id, name=f"status_{uuid4().hex[:4]}")
    matrix = ListEntry(list_id=lst.id, name=f"matrix_{uuid4().hex[:4]}")
    db_session.add_all([sample_type, status, matrix])
    db_session.flush()

    project = Project(
        name=f"Proj {uuid4().hex[:8]}",
        client_id=test_org.id,
        status=status.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(project)
    db_session.flush()

    s = Sample(
        name=f"Sample {uuid4().hex[:8]}",
        description="eln process test",
        sample_type=sample_type.id,
        status=status.id,
        matrix=matrix.id,
        project_id=project.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(s)
    db_session.commit()
    return str(s.id)


class TestELNProcessCRUD:
    def test_create_list_get_update_delete(
        self, client: TestClient, auth_headers, template_a
    ):
        name = f"Process {uuid4().hex[:8]}"
        r = client.post(
            "/v1/eln-processes",
            json={
                "name": name,
                "description": "NGS prep",
                "steps": [
                    {
                        "experiment_template_id": template_a["id"],
                        "name": "Extraction",
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == name
        assert body["active"] is True
        assert len(body["steps"]) == 1
        assert body["steps"][0]["sort_order"] == 0
        process_id = body["id"]

        r = client.get("/v1/eln-processes", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["total"] >= 1
        assert any(p["id"] == process_id for p in r.json()["processes"])

        r = client.get(f"/v1/eln-processes/{process_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == process_id

        r = client.patch(
            f"/v1/eln-processes/{process_id}",
            json={"description": "updated"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["description"] == "updated"

        r = client.delete(f"/v1/eln-processes/{process_id}", headers=auth_headers)
        assert r.status_code == 204

        r = client.get(f"/v1/eln-processes/{process_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["active"] is False

    def test_duplicate_name_rejected(self, client: TestClient, auth_headers):
        name = f"Dup {uuid4().hex[:8]}"
        r = client.post(
            "/v1/eln-processes",
            json={"name": name},
            headers=auth_headers,
        )
        assert r.status_code == 201
        r = client.post(
            "/v1/eln-processes",
            json={"name": name},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_client_denied(self, client: TestClient, client_headers):
        r = client.get("/v1/eln-processes", headers=client_headers)
        assert r.status_code == 403

    def test_404(self, client: TestClient, auth_headers):
        r = client.get(
            f"/v1/eln-processes/{uuid4()}",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestELNProcessSteps:
    def test_add_reorder_remove(
        self, client: TestClient, auth_headers, template_a, template_b
    ):
        r = client.post(
            "/v1/eln-processes",
            json={"name": f"Steps {uuid4().hex[:8]}"},
            headers=auth_headers,
        )
        process_id = r.json()["id"]

        r = client.post(
            f"/v1/eln-processes/{process_id}/steps",
            json={
                "experiment_template_id": template_a["id"],
                "name": "Step A",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        step_a = r.json()

        r = client.post(
            f"/v1/eln-processes/{process_id}/steps",
            json={
                "experiment_template_id": template_b["id"],
                "name": "Step B",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        step_b = r.json()

        r = client.get(f"/v1/eln-processes/{process_id}/steps", headers=auth_headers)
        assert r.status_code == 200
        assert [s["id"] for s in r.json()] == [step_a["id"], step_b["id"]]

        # Reorder: B then A
        r = client.post(
            f"/v1/eln-processes/{process_id}/steps/reorder",
            json={"step_ids": [step_b["id"], step_a["id"]]},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        ordered = r.json()
        assert [s["id"] for s in ordered] == [step_b["id"], step_a["id"]]
        assert [s["sort_order"] for s in ordered] == [0, 1]

        r = client.delete(
            f"/v1/eln-processes/{process_id}/steps/{step_b['id']}",
            headers=auth_headers,
        )
        assert r.status_code == 204

        r = client.get(f"/v1/eln-processes/{process_id}/steps", headers=auth_headers)
        assert len(r.json()) == 1
        assert r.json()[0]["id"] == step_a["id"]
        assert r.json()[0]["sort_order"] == 0

    def test_bad_template(self, client: TestClient, auth_headers):
        r = client.post(
            "/v1/eln-processes",
            json={"name": f"BadTpl {uuid4().hex[:8]}"},
            headers=auth_headers,
        )
        process_id = r.json()["id"]
        r = client.post(
            f"/v1/eln-processes/{process_id}/steps",
            json={"experiment_template_id": str(uuid4())},
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestELNProcessInstantiate:
    def test_instantiate_step_creates_experiment(
        self, client: TestClient, auth_headers, template_a
    ):
        r = client.post(
            "/v1/eln-processes",
            json={
                "name": f"Inst {uuid4().hex[:8]}",
                "steps": [
                    {
                        "experiment_template_id": template_a["id"],
                        "name": "Extraction",
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        process_id = r.json()["id"]
        step_id = r.json()["steps"][0]["id"]

        r = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_id}/instantiate",
            json={"name": f"Exp from step {uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["step"]["experiment_id"] is not None
        assert body["experiment"]["id"] == body["step"]["experiment_id"]
        assert body["experiment"]["experiment_template_id"] == template_a["id"]

        # Second instantiate rejected
        r = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_id}/instantiate",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestELNProcessSamples:
    def test_assign_advance_remove(
        self, client: TestClient, auth_headers, template_a, template_b, sample_id
    ):
        r = client.post(
            "/v1/eln-processes",
            json={
                "name": f"Samples {uuid4().hex[:8]}",
                "steps": [
                    {"experiment_template_id": template_a["id"], "name": "S1"},
                    {"experiment_template_id": template_b["id"], "name": "S2"},
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        process_id = r.json()["id"]
        steps = r.json()["steps"]
        assert len(steps) == 2

        r = client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [sample_id], "set_to_first_step": True},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assignments = r.json()
        assert len(assignments) == 1
        assert assignments[0]["sample_id"] == sample_id
        assert assignments[0]["current_step_id"] == steps[0]["id"]
        assert assignments[0]["status"] == "in_progress"

        # Duplicate assign rejected
        r = client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [sample_id]},
            headers=auth_headers,
        )
        assert r.status_code == 400

        # Advance to second step
        r = client.post(
            f"/v1/eln-processes/{process_id}/samples/{sample_id}/advance",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["current_step_id"] == steps[1]["id"]
        assert r.json()["status"] == "in_progress"

        # Advance past last → completed
        r = client.post(
            f"/v1/eln-processes/{process_id}/samples/{sample_id}/advance",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
        assert r.json()["current_step_id"] == steps[1]["id"]

        r = client.delete(
            f"/v1/eln-processes/{process_id}/samples/{sample_id}",
            headers=auth_headers,
        )
        assert r.status_code == 204

        r = client.get(
            f"/v1/eln-processes/{process_id}/samples",
            headers=auth_headers,
        )
        assert r.json() == []

    def test_filter_samples_by_step(
        self, client: TestClient, auth_headers, template_a, template_b, sample_id
    ):
        r = client.post(
            "/v1/eln-processes",
            json={
                "name": f"Filter {uuid4().hex[:8]}",
                "steps": [
                    {"experiment_template_id": template_a["id"], "name": "S1"},
                    {"experiment_template_id": template_b["id"], "name": "S2"},
                ],
            },
            headers=auth_headers,
        )
        process_id = r.json()["id"]
        steps = r.json()["steps"]

        r = client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [sample_id], "set_to_first_step": True},
            headers=auth_headers,
        )
        assert r.status_code == 201

        r = client.get(
            f"/v1/eln-processes/{process_id}/samples",
            params={"current_step_id": steps[0]["id"]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()) == 1

        r = client.get(
            f"/v1/eln-processes/{process_id}/samples",
            params={"current_step_id": steps[1]["id"]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json() == []
