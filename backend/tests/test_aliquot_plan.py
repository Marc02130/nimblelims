"""P0: aliquot/pool method matrix + plan save + execute."""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def plan_entry(client: TestClient, auth_headers):
    tpl_def = {
        "experiment_name": "Aliquot Plan",
        "protocol_steps": [],
        "transfer_steps": [],
        "result_columns": [],
        "mandatory_review_count": 0,
        "entries": [
            {
                "predefined_entry_key": "aliquot_pool_plan",
                "name": "Aliquot / pool plan",
                "sort_order": 0,
            }
        ],
    }
    r = client.post(
        "/v1/experiment-templates",
        json={"name": f"Tpl ALQ {uuid4().hex[:8]}", "template_definition": tpl_def},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    tpl = r.json()
    r = client.post(
        "/v1/experiments",
        json={
            "name": f"Exp ALQ {uuid4().hex[:8]}",
            "experiment_template_id": tpl["id"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    exp = r.json()
    r = client.get(f"/v1/experiments/{exp['id']}/entries", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()["entries"]
    plan = next(e for e in entries if e.get("predefined_entry_key") == "aliquot_pool_plan")
    return {"experiment": exp, "entry": plan}


class TestAliquotMethods:
    def test_list_methods(self, client: TestClient, auth_headers):
        r = client.get("/v1/entries/aliquot-methods", headers=auth_headers)
        assert r.status_code == 200, r.text
        methods = {m["method"] for m in r.json()["methods"]}
        for expected in (
            "by_mass",
            "by_volume",
            "by_count",
            "target_mass",
            "target_volume",
            "target_concentration",
            "target_count",
        ):
            assert expected in methods


class TestAliquotPlanExecute:
    def _link_cohort(self, db_session, experiment_id, sample_id, user_id):
        from models.experiment import ExperimentSampleExecution

        db_session.add(
            ExperimentSampleExecution(
                experiment_id=experiment_id,
                sample_id=sample_id,
                created_by=user_id,
                modified_by=user_id,
            )
        )
        db_session.commit()

    def _seed_sample_with_content(
        self,
        db_session,
        test_admin_user,
        test_org,
        amount=100.0,
        *,
        experiment_id=None,
        amount_null=False,
    ):
        from models.sample import Sample
        from models.list import List, ListEntry
        from models.project import Project
        from models.container import Container, ContainerType, Contents

        # Reuse global status entry if present (name is unique)
        avail = (
            db_session.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        if not avail:
            status_list = (
                db_session.query(List).filter(List.name == "sample_status").first()
            )
            if not status_list:
                status_list = List(name="sample_status")
                db_session.add(status_list)
                db_session.flush()
            avail = ListEntry(list_id=status_list.id, name="Available for Testing")
            db_session.add(avail)
            db_session.flush()

        lst = List(name=f"alq_list_{uuid4().hex[:6]}")
        db_session.add(lst)
        db_session.flush()
        sample_type = ListEntry(list_id=lst.id, name=f"t_{uuid4().hex[:6]}")
        matrix = ListEntry(list_id=lst.id, name=f"m_{uuid4().hex[:6]}")
        db_session.add_all([sample_type, matrix])
        db_session.flush()

        project = Project(
            name=f"ALQ {uuid4().hex[:8]}",
            client_id=test_org.id,
            status=avail.id,
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(project)
        db_session.flush()
        sample = Sample(
            name=f"SRC {uuid4().hex[:6]}",
            sample_type=sample_type.id,
            status=avail.id,
            matrix=matrix.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(sample)
        db_session.flush()
        ctype = ContainerType(
            name=f"tube_{uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(ctype)
        db_session.flush()
        tube = Container(
            name=f"TUBE-{uuid4().hex[:6]}",
            type_id=ctype.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(tube)
        db_session.flush()
        db_session.add(
            Contents(
                container_id=tube.id,
                sample_id=sample.id,
                amount=None if amount_null else Decimal(str(amount)),
                concentration=Decimal("10"),
            )
        )
        db_session.commit()
        if experiment_id is not None:
            self._link_cohort(
                db_session, experiment_id, sample.id, test_admin_user.id
            )
        return sample, tube, ctype

    def test_method_resolve_by_volume_dry_run(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, experiment_id=exp_id
        )
        entry_id = plan_entry["entry"]["id"]
        # volume 2, conc 10 → mass 20
        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={
                "dry_run": True,
                "lines": [
                    {
                        "method": "by_volume",
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 2,
                        "concentration": 10,
                        "dest_container_type_id": str(ctype.id),
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["dry_run"] is True
        assert body["success_count"] == 1
        assert body["results"][0]["transfer_amount"] == 20.0

    def test_execute_by_mass_reduces_source(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        from models.container import Contents
        from models.sample import Sample

        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        entry_id = plan_entry["entry"]["id"]

        r = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "lines": [
                    {
                        "method": "by_mass",
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "amount": 15,
                        "dest_container_type_id": str(ctype.id),
                        "dest_container_name": f"DEST-{uuid4().hex[:6]}",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["line_count"] == 1

        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success_count"] == 1, body
        assert body["results"][0]["dest_sample_id"] is not None
        assert body["results"][0]["transfer_amount"] == 15.0

        db_session.expire_all()
        content = (
            db_session.query(Contents)
            .filter(Contents.sample_id == sample.id, Contents.container_id == tube.id)
            .first()
        )
        assert float(content.amount) == 35.0

        dest_id = body["results"][0]["dest_sample_id"]
        dest = db_session.query(Sample).filter(Sample.id == dest_id).first()
        assert dest is not None
        assert dest.parent_sample_id == sample.id

    def test_insufficient_amount(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=5.0, experiment_id=exp_id
        )
        entry_id = plan_entry["entry"]["id"]
        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={
                "lines": [
                    {
                        "method": "target_mass",
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "target_amount": 99,
                        "dest_container_type_id": str(ctype.id),
                    }
                ]
            },
            headers=auth_headers,
        )
        # S5: fail closed — entire execute rolls back (no partial result payload)
        assert r.status_code == 400, r.text
        detail = r.json()["detail"]
        assert "Insufficient" in str(detail)

    def test_source_not_in_cohort_refused(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0
        )
        entry_id = plan_entry["entry"]["id"]
        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={
                "lines": [
                    {
                        "method": "by_mass",
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "amount": 5,
                        "dest_container_type_id": str(ctype.id),
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "source_not_in_cohort"

    def test_null_source_amount_refused(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session,
            test_admin_user,
            test_org,
            experiment_id=exp_id,
            amount_null=True,
        )
        entry_id = plan_entry["entry"]["id"]
        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={
                "lines": [
                    {
                        "method": "by_mass",
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "amount": 5,
                        "dest_container_type_id": str(ctype.id),
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "source_amount_null"
