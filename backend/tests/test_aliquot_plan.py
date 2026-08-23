"""P0: aliquot/pool method matrix + plan save + execute."""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
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
                "config": {
                    "method": "aliquot_by_volume",
                    "default_dest_sample_type": None,
                },
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
    plan = next(
        e for e in entries if e.get("predefined_entry_key") == "aliquot_pool_plan"
    )
    return {"experiment": exp, "entry": plan}


class TestAliquotMethods:
    def test_list_methods(self, client: TestClient, auth_headers):
        r = client.get("/v1/entries/aliquot-methods", headers=auth_headers)
        assert r.status_code == 200, r.text
        methods = {m["method"] for m in r.json()["methods"]}
        assert methods == {
            "aliquot_by_volume",
            "aliquot_by_target_amount",
            "aliquot_by_target_concentration",
            "aliquot_n_way_equal_split",
            "pool_by_volume_per_source",
            "pool_equal_volume_each",
            "pool_by_target_amount_per_source",
            "pool_consolidate_remaining",
        }
        assert not any("equimolar" in method for method in methods)


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
            self._link_cohort(db_session, experiment_id, sample.id, test_admin_user.id)
        return sample, tube, ctype

    def test_method_resolve_by_volume_dry_run(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, experiment_id=exp_id
        )
        entry_id = plan_entry["entry"]["id"]
        # volume 2 uses tracked source concentration 10 → mass 20
        r = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={
                "dry_run": True,
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 2,
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

    def test_execute_by_target_amount_reduces_source(
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
                "method": "aliquot_by_target_amount",
                "default_dest_sample_type": None,
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "target_amount": 15,
                        "dest_container_type_id": str(ctype.id),
                        "dest_container_name": f"DEST-{uuid4().hex[:6]}",
                    }
                ],
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
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 99,
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
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 0.5,
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
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 0.5,
                        "dest_container_type_id": str(ctype.id),
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "source_amount_null"

    def test_destination_type_options_and_execute(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        from models.list import ListEntry
        from models.sample import Sample, SampleTypeTransition

        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        source_type = (
            db_session.query(ListEntry).filter(ListEntry.id == sample.sample_type).one()
        )
        destination_type = ListEntry(
            list_id=source_type.list_id,
            name=f"dest_{uuid4().hex[:6]}",
        )
        db_session.add(destination_type)
        db_session.flush()
        db_session.add(
            SampleTypeTransition(
                client_id=test_org.id,
                source_sample_type=sample.sample_type,
                operation="aliquot",
                allowed_dest_sample_type=destination_type.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        options = client.get(
            "/v1/entries/dest-sample-types",
            params={
                "source_sample_id": str(sample.id),
                "operation": "aliquot",
            },
            headers=auth_headers,
        )
        assert options.status_code == 200, options.text
        assert options.json() == {
            "source_sample_type": {
                "id": str(sample.sample_type),
                "name": source_type.name,
            },
            "operation": "aliquot",
            "options": [
                {
                    "id": str(destination_type.id),
                    "name": destination_type.name,
                }
            ],
        }

        execute = client.post(
            f"/v1/entries/{plan_entry['entry']['id']}/execute",
            json={
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 0.5,
                        "dest_container_type_id": str(ctype.id),
                        "dest_sample_type": str(destination_type.id),
                        "inherit_entry_dest_sample_type": False,
                    }
                ]
            },
            headers=auth_headers,
        )
        assert execute.status_code == 200, execute.text
        destination = (
            db_session.query(Sample)
            .filter(Sample.id == execute.json()["results"][0]["dest_sample_id"])
            .first()
        )
        assert destination.sample_type == destination_type.id

    def test_mixed_source_type_pool_is_refused(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        first, first_tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        second, second_tube, _ = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        method_update = client.patch(
            f"/v1/entries/{plan_entry['entry']['id']}",
            json={
                "config": {
                    "status": "draft",
                    "method": "pool_by_target_amount_per_source",
                    "default_dest_sample_type": None,
                }
            },
            headers=auth_headers,
        )
        assert method_update.status_code == 200, method_update.text

        response = client.post(
            f"/v1/entries/{plan_entry['entry']['id']}/execute",
            json={
                "lines": [
                    {
                        "source_sample_id": str(first.id),
                        "source_container_id": str(first_tube.id),
                        "target_amount": 5,
                        "dest_container_type_id": str(ctype.id),
                        "pool_group": "mixed-pool",
                    },
                    {
                        "source_sample_id": str(second.id),
                        "source_container_id": str(second_tube.id),
                        "target_amount": 5,
                        "dest_container_type_id": str(ctype.id),
                        "pool_group": "mixed-pool",
                    },
                ]
            },
            headers=auth_headers,
        )

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["code"] == "mixed_pool_source_types"

    def test_aliquot_entry_refuses_pool_lines(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )

        response = client.post(
            f"/v1/entries/{plan_entry['entry']['id']}/execute",
            json={
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 0.5,
                        "dest_container_type_id": str(ctype.id),
                        "pool_group": "not-allowed",
                    }
                ]
            },
            headers=auth_headers,
        )

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["code"] == "dual_mint_not_allowed"

    def test_entry_default_line_clear_and_method_lock(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        from models.list import ListEntry
        from models.sample import Sample, SampleTypeTransition

        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        source_type = (
            db_session.query(ListEntry).filter(ListEntry.id == sample.sample_type).one()
        )
        destination_type = ListEntry(
            list_id=source_type.list_id,
            name=f"default_dest_{uuid4().hex[:6]}",
        )
        db_session.add(destination_type)
        db_session.flush()
        db_session.add(
            SampleTypeTransition(
                client_id=test_org.id,
                source_sample_type=sample.sample_type,
                operation="aliquot",
                allowed_dest_sample_type=destination_type.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        entry_id = plan_entry["entry"]["id"]
        inherited = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "aliquot_by_target_amount",
                "default_dest_sample_type": str(destination_type.id),
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "target_amount": 5,
                        "dest_container_type_id": str(ctype.id),
                        "inherit_entry_dest_sample_type": True,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert inherited.status_code == 200, inherited.text
        execute = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={},
            headers=auth_headers,
        )
        assert execute.status_code == 200, execute.text
        inherited_dest = (
            db_session.query(Sample)
            .filter(Sample.id == execute.json()["results"][0]["dest_sample_id"])
            .one()
        )
        assert inherited_dest.sample_type == destination_type.id

        cleared = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "aliquot_by_target_amount",
                "default_dest_sample_type": str(destination_type.id),
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "target_amount": 5,
                        "dest_container_type_id": str(ctype.id),
                        "dest_sample_type": None,
                        "inherit_entry_dest_sample_type": False,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert cleared.status_code == 200, cleared.text
        execute = client.post(
            f"/v1/entries/{entry_id}/execute",
            json={},
            headers=auth_headers,
        )
        assert execute.status_code == 200, execute.text
        cleared_dest = (
            db_session.query(Sample)
            .filter(Sample.id == execute.json()["results"][0]["dest_sample_id"])
            .one()
        )
        assert cleared_dest.sample_type == sample.sample_type

        method_change = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "pool_by_target_amount_per_source",
                "default_dest_sample_type": None,
                "lines": [],
            },
            headers=auth_headers,
        )
        assert method_change.status_code == 409, method_change.text
        assert method_change.json()["detail"]["code"] == "method_change_requires_cancel"

    def test_normalization_requires_prior_result_and_rejects_free_concentration(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        from models.analysis import Analysis, Analyte
        from models.list import ListEntry
        from models.result import Result
        from models.test import Test as LabTest

        exp_id = plan_entry["experiment"]["id"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session, test_admin_user, test_org, amount=50.0, experiment_id=exp_id
        )
        entry_id = plan_entry["entry"]["id"]
        line = {
            "source_sample_id": str(sample.id),
            "source_container_id": str(tube.id),
            "target_concentration": 5,
            "target_amount": 5,
            "dest_container_type_id": str(ctype.id),
        }

        missing_result = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "aliquot_by_target_concentration",
                "default_dest_sample_type": None,
                "lines": [line],
            },
            headers=auth_headers,
        )
        assert missing_result.status_code == 400, missing_result.text
        assert missing_result.json()["detail"]["code"] == "prior_concentration_required"

        analysis = Analysis(
            name=f"Concentration analysis {uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        analyte = Analyte(
            name=f"DNA concentration {uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add_all([analysis, analyte])
        db_session.flush()
        available = (
            db_session.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        test = LabTest(
            name=f"Concentration test {uuid4().hex[:6]}",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=available.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(test)
        db_session.flush()
        db_session.add(
            Result(
                test_id=test.id,
                analyte_id=analyte.id,
                reported_result="10",
                entered_by=test_admin_user.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        free_concentration = dict(line)
        free_concentration["concentration"] = 12
        refused = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "aliquot_by_target_concentration",
                "default_dest_sample_type": None,
                "lines": [free_concentration],
            },
            headers=auth_headers,
        )
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "free_text_concentration_not_allowed"

        accepted = client.put(
            f"/v1/entries/{entry_id}/aliquot-plan",
            json={
                "method": "aliquot_by_target_concentration",
                "default_dest_sample_type": None,
                "lines": [line],
            },
            headers=auth_headers,
        )
        assert accepted.status_code == 200, accepted.text

    def test_execute_minted_destination_joins_process_after_start(
        self, client, auth_headers, plan_entry, db_session, test_admin_user, test_org
    ):
        from models.entry import ELNProcess, ELNProcessSample, ELNProcessStep, Entry

        exp = plan_entry["experiment"]
        sample, tube, ctype = self._seed_sample_with_content(
            db_session,
            test_admin_user,
            test_org,
            amount=50.0,
            experiment_id=exp["id"],
        )
        process = ELNProcess(
            name=f"Process {uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(process)
        db_session.flush()
        step = ELNProcessStep(
            process_id=process.id,
            experiment_template_id=exp["experiment_template_id"],
            experiment_id=exp["id"],
            name="Started extraction",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(step)
        db_session.flush()
        entry = (
            db_session.query(Entry).filter(Entry.id == plan_entry["entry"]["id"]).one()
        )
        entry.process_step_id = step.id
        db_session.commit()

        execute = client.post(
            f"/v1/entries/{entry.id}/execute",
            json={
                "lines": [
                    {
                        "source_sample_id": str(sample.id),
                        "source_container_id": str(tube.id),
                        "volume": 0.5,
                        "dest_container_type_id": str(ctype.id),
                    }
                ]
            },
            headers=auth_headers,
        )
        assert execute.status_code == 200, execute.text
        dest_id = execute.json()["results"][0]["dest_sample_id"]
        process_sample = (
            db_session.query(ELNProcessSample)
            .filter(
                ELNProcessSample.process_id == process.id,
                ELNProcessSample.sample_id == dest_id,
            )
            .one()
        )
        assert process_sample.current_step_id == step.id
        assert process_sample.status == "in_progress"
