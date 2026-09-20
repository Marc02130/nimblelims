"""E-7: sample-type gate on experiment / LimsRun start, not template/entry."""
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project
from models.sample import Sample
from models.user import User


def _auth(client: TestClient, username: str = "admin", password: str = "adminpassword"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def headers(client: TestClient, test_admin_user):
    return _auth(client)


@pytest.fixture
def types_and_samples(db_session: Session, test_admin_user: User, test_org):
    lst = List(name=f"e7_{uuid4().hex[:6]}", description="e7")
    db_session.add(lst)
    db_session.flush()
    blood = ListEntry(list_id=lst.id, name="Blood")
    dna = ListEntry(list_id=lst.id, name="DNA")
    available = ListEntry(list_id=lst.id, name="Available for Testing")
    matrix = ListEntry(list_id=lst.id, name="Whole blood")
    db_session.add_all([blood, dna, available, matrix])
    db_session.flush()
    project = Project(
        name=f"E7 {uuid4().hex[:8]}",
        client_id=test_org.id,
        status=available.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(project)
    db_session.flush()
    ctype = ContainerType(
        name=f"tube_{uuid4().hex[:6]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(ctype)
    db_session.flush()

    def _sample(type_id):
        s = Sample(
            name=f"s_{uuid4().hex[:8]}",
            sample_type=type_id,
            status=available.id,
            matrix=matrix.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(s)
        db_session.flush()
        tube = Container(
            name=f"T-{uuid4().hex[:6]}",
            type_id=ctype.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(tube)
        db_session.flush()
        db_session.add(
            Contents(container_id=tube.id, sample_id=s.id, amount=Decimal("1"))
        )
        db_session.flush()
        return s

    blood_sample = _sample(blood.id)
    dna_sample = _sample(dna.id)
    db_session.commit()
    return {
        "blood": blood,
        "dna": dna,
        "blood_sample": blood_sample,
        "dna_sample": dna_sample,
    }


def _template(client, headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"E7 tpl {uuid4().hex[:8]}",
            "template_definition": {
                "experiment_name": "E7",
                "protocol_steps": [],
                "transfer_steps": [],
                "result_columns": [],
                "mandatory_review_count": 0,
                "entries": [
                    {
                        "predefined_entry_key": "experiment_header",
                        "name": "Experiment header",
                        "sort_order": 0,
                    }
                ],
            },
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _experiment_def(client, headers, template_id, dna_id):
    created = client.post(
        "/v1/eln-process-definitions",
        json={
            "name": f"E7 SOP {uuid4().hex[:8]}",
            "steps": [
                {
                    "experiment_template_id": template_id,
                    "step_kind": "eln_experiment",
                    "execution_mode": "eln_experiment",
                    "name": "Extract",
                    "sort_order": 0,
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    definition = created.json()
    step_id = definition["steps"][0]["id"]
    put = client.put(
        f"/v1/eln-process-definitions/{definition['id']}/steps/{step_id}/accepted-sample-types",
        json={"sample_type_ids": [str(dna_id)]},
        headers=headers,
    )
    assert put.status_code == 200, put.text
    return definition


def _instantiate(client, headers, definition):
    r = client.post(
        f"/v1/eln-process-definitions/{definition['id']}/instantiate",
        json={"name": f"E7 inst {uuid4().hex[:8]}"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestE7TemplateRefuse:
    def test_template_accepted_sample_types_422(self, client: TestClient, headers):
        r = client.post(
            "/v1/experiment-templates",
            json={
                "name": f"E7 bad {uuid4().hex[:8]}",
                "template_definition": {
                    "experiment_name": "bad",
                    "accepted_sample_types": [str(uuid4())],
                    "protocol_steps": [],
                    "transfer_steps": [],
                    "result_columns": [],
                    "mandatory_review_count": 0,
                },
            },
            headers=headers,
        )
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "accepted_sample_types_not_on_template"

    def test_entry_config_accepted_sample_types_422(self, client: TestClient, headers):
        r = client.post(
            "/v1/experiment-templates",
            json={
                "name": f"E7 entry {uuid4().hex[:8]}",
                "template_definition": {
                    "experiment_name": "bad",
                    "protocol_steps": [],
                    "transfer_steps": [],
                    "result_columns": [],
                    "mandatory_review_count": 0,
                    "entries": [
                        {
                            "predefined_entry_key": "experiment_header",
                            "name": "Header",
                            "sort_order": 0,
                            "config": {"accepted_sample_types": [str(uuid4())]},
                        }
                    ],
                },
            },
            headers=headers,
        )
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "accepted_sample_types_not_on_template"


class TestE7ExperimentStart:
    def test_wrong_type_422_and_matching_starts(
        self, client: TestClient, headers, types_and_samples
    ):
        tpl = _template(client, headers)
        definition = _experiment_def(
            client, headers, tpl["id"], types_and_samples["dna"].id
        )
        process = _instantiate(client, headers, definition)
        process_id = process["id"]
        step_id = process["steps"][0]["id"]
        blood_id = str(types_and_samples["blood_sample"].id)
        dna_id = str(types_and_samples["dna_sample"].id)

        started = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_id}/start",
            json={},
            headers=headers,
        )
        assert started.status_code == 201, started.text
        experiment_id = started.json()["experiment_id"]

        assigned = client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [blood_id], "set_to_first_step": True},
            headers=headers,
        )
        assert assigned.status_code == 201, assigned.text

        refuse = client.post(
            f"/v1/experiments/{experiment_id}/start",
            json={"sample_ids": [blood_id]},
            headers=headers,
        )
        assert refuse.status_code == 422, refuse.text
        assert refuse.json()["detail"]["code"] == "route_sample_type"

        removed = client.delete(
            f"/v1/eln-processes/{process_id}/samples/{blood_id}",
            headers=headers,
        )
        assert removed.status_code == 204, removed.text

        assigned_dna = client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [dna_id], "set_to_first_step": True},
            headers=headers,
        )
        assert assigned_dna.status_code == 201, assigned_dna.text

        ok = client.post(
            f"/v1/experiments/{experiment_id}/start",
            json={"sample_ids": [dna_id]},
            headers=headers,
        )
        assert ok.status_code == 200, ok.text

    def test_ad_hoc_experiment_ungated(
        self, client: TestClient, headers, types_and_samples
    ):
        tpl = _template(client, headers)
        exp = client.post(
            "/v1/experiments",
            json={
                "name": f"E7 ad hoc {uuid4().hex[:8]}",
                "experiment_template_id": tpl["id"],
            },
            headers=headers,
        )
        assert exp.status_code == 201, exp.text
        blood_id = str(types_and_samples["blood_sample"].id)
        r = client.post(
            f"/v1/experiments/{exp.json()['id']}/start",
            json={"sample_ids": [blood_id]},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_eligible_list_marks_wrong_type(
        self, client: TestClient, headers, types_and_samples
    ):
        tpl = _template(client, headers)
        definition = _experiment_def(
            client, headers, tpl["id"], types_and_samples["dna"].id
        )
        process = _instantiate(client, headers, definition)
        process_id = process["id"]
        step_id = process["steps"][0]["id"]
        blood_id = str(types_and_samples["blood_sample"].id)
        dna_id = str(types_and_samples["dna_sample"].id)
        client.post(
            f"/v1/eln-processes/{process_id}/samples",
            json={"sample_ids": [blood_id, dna_id], "set_to_first_step": True},
            headers=headers,
        )
        listed = client.get(
            f"/v1/eln-processes/{process_id}/steps/{step_id}/eligible-samples",
            headers=headers,
        )
        assert listed.status_code == 200, listed.text
        rows = {str(r["sample_id"]): r for r in listed.json()["samples"]}
        assert rows[blood_id]["eligible"] is False
        assert "not accepted" in (rows[blood_id]["ineligible_reason"] or "").lower()
        assert rows[dna_id]["eligible"] is True


class TestE7LimsRunStart:
    def test_wrong_type_422(self, client: TestClient, headers, types_and_samples):
        analysis = client.post(
            "/analyses",
            json={"name": f"E7 Qubit {uuid4().hex[:8]}", "method": "qc"},
            headers=headers,
        )
        assert analysis.status_code == 201, analysis.text
        created = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"E7 QC {uuid4().hex[:8]}",
                "steps": [
                    {
                        "analysis_id": analysis.json()["id"],
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "Qubit",
                        "sort_order": 0,
                    }
                ],
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        definition = created.json()
        step_def_id = definition["steps"][0]["id"]
        put = client.put(
            f"/v1/eln-process-definitions/{definition['id']}/steps/{step_def_id}/accepted-sample-types",
            json={"sample_type_ids": [str(types_and_samples["dna"].id)]},
            headers=headers,
        )
        assert put.status_code == 200, put.text
        process = _instantiate(client, headers, definition)
        process_id = process["id"]
        step_id = process["steps"][0]["id"]
        started = client.post(
            f"/v1/eln-processes/{process_id}/steps/{step_id}/start",
            json={},
            headers=headers,
        )
        assert started.status_code == 201, started.text
        run_id = started.json()["lims_run_id"]
        blood_id = str(types_and_samples["blood_sample"].id)
        refuse = client.patch(
            f"/v1/lims-runs/{run_id}/start",
            json={"sample_ids": [blood_id]},
            headers=headers,
        )
        assert refuse.status_code == 422, refuse.text
        assert refuse.json()["detail"]["code"] == "route_sample_type"
