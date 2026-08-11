"""P0: resolve-scan + start experiment cohort (queue / plate-tube)."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


VALID_TEMPLATE_DEF = {
    "experiment_name": "Cohort Test",
    "protocol_steps": [],
    "transfer_steps": [],
    "result_columns": [],
    "mandatory_review_count": 0,
    "entries": [
        {
            "predefined_entry_key": "experiment_header",
            "name": "Experiment header",
            "sort_order": 0,
        },
        {
            "predefined_entry_key": "samples",
            "name": "Samples",
            "sort_order": 1,
        },
    ],
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def experiment(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl Cohort {uuid4().hex[:8]}",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    tpl = r.json()
    r = client.post(
        "/v1/experiments",
        json={
            "name": f"Exp Cohort {uuid4().hex[:8]}",
            "experiment_template_id": tpl["id"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestStartCohort:
    def test_predefined_entries_instantiate(self, client: TestClient, auth_headers, experiment):
        r = client.get(
            f"/v1/experiments/{experiment['id']}/entries",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] >= 2
        by_key = {
            e.get("predefined_entry_key"): e
            for e in body["entries"]
            if e.get("predefined_entry_key")
        }
        assert "experiment_header" in by_key
        assert by_key["experiment_header"]["entry_type"] == "experiment_data"
        assert "samples" in by_key
        assert by_key["samples"]["entry_type"] == "experiment_sample_data"

    def test_resolve_scan_none(self, client: TestClient, auth_headers):
        r = client.post(
            "/v1/experiments/resolve-scan",
            json={"barcode": f"no-such-{uuid4().hex[:8]}"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["match_type"] == "none"
        assert body["total"] == 0

    def test_start_requires_samples(self, client: TestClient, auth_headers, experiment):
        r = client.post(
            f"/v1/experiments/{experiment['id']}/start",
            json={"sample_ids": []},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_start_and_lock_cohort(
        self,
        client: TestClient,
        auth_headers,
        experiment,
        db_session,
        test_admin_user,
        test_org,
    ):
        from datetime import datetime, timedelta
        from models.sample import Sample
        from models.list import List, ListEntry
        from models.project import Project
        from models.container import Container, ContainerType, Contents

        lst = List(name=f"c_list_{uuid4().hex[:6]}", description="cohort test")
        db_session.add(lst)
        db_session.flush()
        sample_type = ListEntry(list_id=lst.id, name=f"type_{uuid4().hex[:4]}")
        status = ListEntry(list_id=lst.id, name=f"status_{uuid4().hex[:4]}")
        matrix = ListEntry(list_id=lst.id, name=f"matrix_{uuid4().hex[:4]}")
        db_session.add_all([sample_type, status, matrix])
        db_session.flush()
        project = Project(
            name=f"CProj {uuid4().hex[:8]}",
            client_id=test_org.id,
            status=status.id,
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(project)
        db_session.flush()

        csid = f"CS-{uuid4().hex[:6]}"
        s = Sample(
            name=f"samp_{uuid4().hex[:8]}",
            sample_type=sample_type.id,
            status=status.id,
            matrix=matrix.id,
            project_id=project.id,
            client_sample_id=csid,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(s)
        db_session.flush()

        # Plate with two samples for container scan
        s_plate = Sample(
            name=f"plate_samp_{uuid4().hex[:8]}",
            sample_type=sample_type.id,
            status=status.id,
            matrix=matrix.id,
            project_id=project.id,
            client_sample_id=f"CS-P-{uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(s_plate)
        db_session.flush()
        ctype = ContainerType(
            name=f"plate_type_{uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(ctype)
        db_session.flush()
        plate_name = f"PLATE-{uuid4().hex[:6]}"
        plate = Container(
            name=plate_name,
            type_id=ctype.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(plate)
        db_session.flush()
        db_session.add(Contents(container_id=plate.id, sample_id=s.id))
        db_session.add(Contents(container_id=plate.id, sample_id=s_plate.id))
        db_session.commit()

        r = client.post(
            f"/v1/experiments/{experiment['id']}/start",
            json={"sample_ids": [str(s.id)], "set_started_at": True},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["linked_count"] == 1
        assert body["cohort_locked"] is True
        assert body["experiment"]["started_at"] is not None

        # Mid-flight add rejected
        s2 = Sample(
            name=f"samp2_{uuid4().hex[:8]}",
            sample_type=sample_type.id,
            status=status.id,
            matrix=matrix.id,
            project_id=project.id,
            client_sample_id=f"CS2-{uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(s2)
        db_session.commit()

        r = client.post(
            f"/v1/experiments/{experiment['id']}/samples",
            json={"sample_id": str(s2.id)},
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text

        # Resolve by client_sample_id
        r = client.post(
            "/v1/experiments/resolve-scan",
            json={"barcode": csid},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["match_type"] == "sample"
        assert r.json()["total"] == 1
        assert r.json()["samples"][0]["sample_id"] == str(s.id)

        # Resolve plate → all contents
        r = client.post(
            "/v1/experiments/resolve-scan",
            json={"barcode": plate_name},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["match_type"] == "container"
        assert r.json()["total"] == 2
