"""P0: LIMS run cohort required at start + lock."""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def analysis_and_template(client: TestClient, auth_headers, db_session, test_admin_user):
    from models.analysis import Analysis
    from models.experiment import ExperimentTemplate

    a = Analysis(
        name=f"An {uuid4().hex[:6]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(a)
    db_session.flush()
    t = ExperimentTemplate(
        name=f"Tpl Run {uuid4().hex[:6]}",
        template_definition={
            "experiment_name": "R",
            "protocol_steps": [],
            "transfer_steps": [],
            "result_columns": [],
            "mandatory_review_count": 0,
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(t)
    db_session.commit()
    return {"analysis_id": str(a.id), "template_id": str(t.id)}


class TestLimsRunCohort:
    def test_start_requires_cohort(
        self, client: TestClient, auth_headers, analysis_and_template
    ):
        r = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "experiment_template_id": analysis_and_template["template_id"],
                "analysis_id": analysis_and_template["analysis_id"],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        r = client.patch(f"/v1/lims-runs/{run_id}/start", json={}, headers=auth_headers)
        assert r.status_code == 400, r.text
        detail = r.json()["detail"]
        assert detail.get("code") == "cohort_required" or "cohort" in str(detail).lower()

    def test_start_with_samples(
        self,
        client: TestClient,
        auth_headers,
        analysis_and_template,
        db_session,
        test_admin_user,
        test_org,
    ):
        from models.sample import Sample
        from models.list import List, ListEntry
        from models.project import Project

        avail = (
            db_session.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        if not avail:
            lst = List(name=f"st_{uuid4().hex[:6]}")
            db_session.add(lst)
            db_session.flush()
            avail = ListEntry(list_id=lst.id, name="Available for Testing")
            db_session.add(avail)
            db_session.flush()
        lst2 = List(name=f"l_{uuid4().hex[:6]}")
        db_session.add(lst2)
        db_session.flush()
        st = ListEntry(list_id=lst2.id, name=f"t_{uuid4().hex[:4]}")
        mx = ListEntry(list_id=lst2.id, name=f"m_{uuid4().hex[:4]}")
        db_session.add_all([st, mx])
        db_session.flush()
        project = Project(
            name=f"P {uuid4().hex[:6]}",
            client_id=test_org.id,
            status=avail.id,
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(project)
        db_session.flush()
        sample = Sample(
            name=f"S {uuid4().hex[:6]}",
            sample_type=st.id,
            status=avail.id,
            matrix=mx.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(sample)
        db_session.commit()

        r = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run2 {uuid4().hex[:8]}",
                "experiment_template_id": analysis_and_template["template_id"],
                "analysis_id": analysis_and_template["analysis_id"],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        r = client.patch(
            f"/v1/lims-runs/{run_id}/start",
            json={"sample_ids": [str(sample.id)]},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "running"
        assert body["cohort"]["sample_ids"] == [str(sample.id)]
        assert body["cohort"].get("locked_at")
