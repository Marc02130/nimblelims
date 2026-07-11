"""Phase 3: process definitions, typed steps, instantiate, start lims_run step."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

VALID_TEMPLATE_DEF = {
    "experiment_name": "Def Test",
    "protocol_steps": ["a"],
    "transfer_steps": [],
    "result_columns": [],
    "mandatory_review_count": 0,
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def template_id(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl {uuid4().hex[:8]}",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestProcessDefinitions:
    def test_create_definition_and_instantiate(
        self, client: TestClient, auth_headers, template_id
    ):
        r = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"SOP {uuid4().hex[:8]}",
                "description": "NGS prep",
                "steps": [
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "eln_experiment",
                        "execution_mode": "eln_experiment",
                        "name": "Extraction",
                        "sort_order": 0,
                    },
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "Plate QC",
                        "sort_order": 1,
                    },
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        definition = r.json()
        assert len(definition["steps"]) == 2
        assert definition["steps"][1]["step_kind"] == "lims_run"
        def_id = definition["id"]

        r = client.post(
            f"/v1/eln-process-definitions/{def_id}/instantiate",
            json={"name": f"Run {uuid4().hex[:8]}"},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        inst = r.json()
        assert inst["process_definition_id"] == def_id
        assert len(inst["steps"]) == 2
        assert inst["steps"][0]["step_kind"] == "eln_experiment"
        assert inst["steps"][1]["step_kind"] == "lims_run"

    def test_start_eln_and_lims_run_steps(
        self, client: TestClient, auth_headers, template_id
    ):
        r = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"SOP2 {uuid4().hex[:8]}",
                "steps": [
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "eln_experiment",
                        "name": "Prep",
                        "sort_order": 0,
                    },
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "QC",
                        "sort_order": 1,
                    },
                ],
            },
            headers=auth_headers,
        )
        def_id = r.json()["id"]
        r = client.post(
            f"/v1/eln-process-definitions/{def_id}/instantiate",
            json={"name": f"Inst {uuid4().hex[:8]}"},
            headers=auth_headers,
        )
        process = r.json()
        process_id = process["id"]
        step_eln = process["steps"][0]
        step_run = process["steps"][1]

        r = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_eln['id']}/start",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["experiment_id"] is not None
        assert r.json()["step"]["experiment_id"] == r.json()["experiment_id"]

        r = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_run['id']}/start",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["lims_run_id"] is not None
        assert r.json()["step"]["current_lims_run_id"] == r.json()["lims_run_id"]

    def test_freeform_create_auto_definition(
        self, client: TestClient, auth_headers, template_id
    ):
        r = client.post(
            "/v1/eln-processes",
            json={
                "name": f"Adhoc {uuid4().hex[:8]}",
                "steps": [
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "eln_experiment",
                        "name": "Only",
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["process_definition_id"] is not None

    def test_sample_journey(
        self, client: TestClient, auth_headers, template_id, db_session, test_admin_user, test_org
    ):
        from datetime import datetime, timedelta
        from models.sample import Sample
        from models.project import Project
        from models.list import List, ListEntry

        lst = List(name=f"j_list_{uuid4().hex[:6]}", description="test")
        db_session.add(lst)
        db_session.flush()
        sample_type = ListEntry(list_id=lst.id, name=f"type_{uuid4().hex[:4]}")
        status = ListEntry(list_id=lst.id, name=f"status_{uuid4().hex[:4]}")
        matrix = ListEntry(list_id=lst.id, name=f"matrix_{uuid4().hex[:4]}")
        db_session.add_all([sample_type, status, matrix])
        db_session.flush()
        project = Project(
            name=f"JProj {uuid4().hex[:8]}",
            client_id=test_org.id,
            status=status.id,
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(project)
        db_session.flush()
        s = Sample(
            name=f"JSample {uuid4().hex[:8]}",
            description="journey test",
            sample_type=sample_type.id,
            status=status.id,
            matrix=matrix.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(s)
        db_session.commit()
        sample_id = str(s.id)

        r = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"Journey SOP {uuid4().hex[:8]}",
                "steps": [
                    {
                        "experiment_template_id": template_id,
                        "step_kind": "eln_experiment",
                        "name": "Step A",
                        "sort_order": 0,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        def_id = r.json()["id"]
        r = client.post(
            f"/v1/eln-process-definitions/{def_id}/instantiate",
            json={"name": f"Journey inst {uuid4().hex[:8]}", "sample_ids": [sample_id]},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        process = r.json()

        r = client.get(f"/v1/samples/{sample_id}/journey", headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["sample_id"] == sample_id
        assert any(p["process_id"] == process["id"] for p in body["processes"])
