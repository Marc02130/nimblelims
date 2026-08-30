"""P2 routing map, Route → work_order, WO-7 Test at LimsRun start."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.analysis import Analysis
from models.asked_for import AskedFor
from models.container import ContainerType
from models.entry import ELNProcess
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.test import Test
from models.user import User
from models.work_order import StepAcceptedSampleType, WorkOrder


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _asked_for_body(sample_ids, analysis_id, tat_days=5, params=None):
    return {
        "sample_ids": [str(s) for s in sample_ids],
        "analysis_id": str(analysis_id),
        "tat_days": tat_days,
        "params": params if params is not None else {},
    }


def _receive_body(seed, *, barcode: str, sample_type_id=None):
    return {
        "container_barcode": barcode,
        "additional_container_barcodes": [],
        "sample_type": str(sample_type_id or seed["sample_type"].id),
        "project_id": str(seed["project"].id),
        "container_type_id": str(seed["tube"].id),
        "analysis_ids": [],
    }


def _receive_sample(
    client: TestClient, token: str, seed, barcode: str, sample_type_id=None
) -> str:
    r = client.post(
        "/samples/receive",
        json=_receive_body(seed, barcode=barcode, sample_type_id=sample_type_id),
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["sample_id"]


@pytest.fixture
def p2_seed(db_session: Session, test_admin_user: User):
    status_list = List(name="Sample Status", description="Sample statuses")
    type_list = List(name="Sample Type", description="Sample types")
    matrix_list = List(name="Matrix", description="Matrices")
    project_status_list = List(name="Project Status", description="Project statuses")
    test_status_list = List(name="test_status", description="Test statuses")
    db_session.add_all(
        [status_list, type_list, matrix_list, project_status_list, test_status_list]
    )
    db_session.flush()

    available = ListEntry(
        list_id=status_list.id, name="Available for Testing", description="Ready"
    )
    sample_type = ListEntry(list_id=type_list.id, name="Plasma", description="Plasma")
    dna_type = ListEntry(
        list_id=type_list.id, name="Purified DNA", description="Purified DNA"
    )
    matrix = ListEntry(list_id=matrix_list.id, name="Serum", description="Serum")
    project_active = ListEntry(
        list_id=project_status_list.id, name="Active", description="Active"
    )
    assigned = ListEntry(
        list_id=test_status_list.id, name="Assigned/Pending", description="Pending"
    )
    db_session.add_all(
        [available, sample_type, dna_type, matrix, project_active, assigned]
    )

    tube = ContainerType(
        name="Tube",
        description="Default tube",
        capacity=5,
        material="plastic",
        rows=1,
        columns=1,
    )
    db_session.add(tube)

    analysis_a = Analysis(
        name=f"PlateQC-{uuid4().hex[:6]}",
        description="P2 QC analysis",
        turnaround_time=5,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    analysis_b = Analysis(
        name=f"TargetSeq-{uuid4().hex[:6]}",
        description="P2 later-route analysis",
        turnaround_time=7,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([analysis_a, analysis_b])
    db_session.flush()

    project = Project(
        name=f"WO-P2-{uuid4().hex[:8]}",
        description="Work-order P2 project",
        start_date=datetime.utcnow(),
        client_id=test_admin_user.client_id,
        status=project_active.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectUser(project_id=project.id, user_id=test_admin_user.id))
    db_session.commit()

    return {
        "available": available,
        "sample_type": sample_type,
        "dna_type": dna_type,
        "matrix": matrix,
        "tube": tube,
        "project": project,
        "project_active": project_active,
        "analysis_a": analysis_a,
        "analysis_b": analysis_b,
        "assigned": assigned,
    }


def _create_lims_run_definition(client: TestClient, admin_token: str, analysis_id) -> dict:
    r = client.post(
        "/v1/eln-process-definitions",
        json={
            "name": f"SOP {uuid4().hex[:8]}",
            "steps": [
                {
                    "analysis_id": str(analysis_id),
                    "step_kind": "lims_run",
                    "execution_mode": "lims_run",
                    "name": "Plate QC",
                    "sort_order": 0,
                }
            ],
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _put_step_types(client, token, definition, sample_type_id):
    step_id = definition["steps"][0]["id"]
    r = client.put(
        f"/v1/eln-process-definitions/{definition['id']}/steps/{step_id}/accepted-sample-types",
        json={"sample_type_ids": [str(sample_type_id)]},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def _create_extract_process(client, token, *, dest_type_id, inbound_type_id, name="Extract"):
    tpl = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl {uuid4().hex[:8]}",
            "template_definition": {
                "experiment_name": name,
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
                            "default_dest_sample_type": (
                                str(dest_type_id) if dest_type_id else None
                            ),
                        },
                    }
                ],
            },
        },
        headers=_auth(token),
    )
    assert tpl.status_code == 201, tpl.text
    created = client.post(
        "/v1/eln-process-definitions",
        json={
            "name": f"SOP {name} {uuid4().hex[:8]}",
            "steps": [
                {
                    "experiment_template_id": tpl.json()["id"],
                    "step_kind": "eln_experiment",
                    "execution_mode": "eln_experiment",
                    "name": name,
                    "sort_order": 0,
                }
            ],
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    definition = created.json()
    _put_step_types(client, token, definition, inbound_type_id)
    return definition


def _create_map(
    client,
    token,
    *,
    analysis_id=None,
    definition_id=None,
    definition_ids=None,
    tat_min=1,
    tat_max=10,
    sample_type_id=None,
):
    ids = definition_ids if definition_ids is not None else [definition_id]
    body = {
        "tat_min": tat_min,
        "tat_max": tat_max,
        "process_definition_ids": [str(i) for i in ids],
    }
    if analysis_id is not None:
        body["analysis_id"] = str(analysis_id)
    if sample_type_id is not None:
        body["sample_type_id"] = str(sample_type_id)
    return client.post("/v1/routing-map", json=body, headers=_auth(token))


class TestWorkOrderP2:
    def test_empty_map_route_422(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-NOROUTE")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        assert created.status_code == 201, created.text
        af_id = created.json()["items"][0]["id"]
        before = db_session.query(WorkOrder).count()
        r = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"
        got = client.get(f"/v1/asked-for/{af_id}", headers=_auth(admin_token))
        assert got.json()["status"] == "requested"
        assert db_session.query(WorkOrder).count() == before

    def test_map_save_without_first_step_types_422(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        r = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"

    def test_later_step_different_type_still_routes(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        """Routing does not require every step to accept the inbound sample type."""
        created_def = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"SOP extract-then-qc {uuid4().hex[:8]}",
                "steps": [
                    {
                        "analysis_id": str(p2_seed["analysis_a"].id),
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "Extract",
                        "sort_order": 0,
                    },
                    {
                        "analysis_id": str(p2_seed["analysis_a"].id),
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "Plate QC",
                        "sort_order": 1,
                    },
                ],
            },
            headers=_auth(admin_token),
        )
        assert created_def.status_code == 201, created_def.text
        definition = created_def.json()
        steps = sorted(definition["steps"], key=lambda s: s["sort_order"])
        first_id = steps[0]["id"]
        second_id = steps[1]["id"]
        r1 = client.put(
            f"/v1/eln-process-definitions/{definition['id']}/steps/{first_id}/accepted-sample-types",
            json={"sample_type_ids": [str(p2_seed["sample_type"].id)]},
            headers=_auth(admin_token),
        )
        assert r1.status_code == 200, r1.text
        r2 = client.put(
            f"/v1/eln-process-definitions/{definition['id']}/steps/{second_id}/accepted-sample-types",
            json={"sample_type_ids": [str(p2_seed["dna_type"].id)]},
            headers=_auth(admin_token),
        )
        assert r2.status_code == 200, r2.text

        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert mapped.status_code == 201, mapped.text
        items = mapped.json()
        assert isinstance(items, list)
        assert {row["sample_type_id"] for row in items} == {
            str(p2_seed["sample_type"].id)
        }

        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-DEST")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        before = db_session.query(WorkOrder).count()
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text
        item = routed.json()["items"][0]
        assert item["no_route"] is False
        assert item["work_order"] is not None
        assert db_session.query(WorkOrder).count() == before + 1

        dna_id = _receive_sample(
            client,
            admin_token,
            p2_seed,
            "NBIO-P2-DEST-DNA",
            sample_type_id=p2_seed["dna_type"].id,
        )
        dna_af = client.post(
            "/v1/asked-for",
            json=_asked_for_body([dna_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        dna_routed = client.post(
            f"/v1/asked-for/{dna_af.json()['items'][0]['id']}/route",
            headers=_auth(admin_token),
        )
        assert dna_routed.status_code == 422, dna_routed.text
        detail = dna_routed.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"

    def test_ordered_process_chain_on_map_and_work_order(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        analysis = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        reporting = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, analysis, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, reporting, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_ids=[extract["id"], analysis["id"], reporting["id"]],
        )
        assert mapped.status_code == 201, mapped.text
        items = mapped.json()
        assert {row["sample_type_id"] for row in items} == {
            str(p2_seed["sample_type"].id)
        }
        chain = items[0]["process_definition_ids"]
        assert chain == [
            str(extract["id"]),
            str(analysis["id"]),
            str(reporting["id"]),
        ]
        dup = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_ids=[extract["id"], extract["id"]],
            tat_min=11,
            tat_max=20,
        )
        assert dup.status_code == 422, dup.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-CHAIN")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text
        wo = routed.json()["items"][0]["work_order"]
        assert wo["process_definition_ids"] == chain

    def test_route_422_when_first_step_types_go_stale(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert mapped.status_code == 201, mapped.text
        step_id = definition["steps"][0]["id"]
        db_session.query(StepAcceptedSampleType).filter(
            StepAcceptedSampleType.step_id == step_id
        ).delete()
        db_session.add(
            StepAcceptedSampleType(
                step_id=step_id, sample_type_id=p2_seed["dna_type"].id
            )
        )
        db_session.commit()
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-STALE")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 422, routed.text
        detail = routed.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"

    def test_first_step_type_change_updates_map(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert mapped.status_code == 201, mapped.text
        _put_step_types(client, admin_token, definition, p2_seed["dna_type"].id)
        rows = client.get(
            "/v1/routing-map?active_only=false",
            headers=_auth(admin_token),
        )
        assert rows.status_code == 200, rows.text
        types = {
            row["sample_type_id"]
            for row in rows.json()
            if str(definition["id"]) in (row.get("process_definition_ids") or [])
        }
        assert types == {str(p2_seed["dna_type"].id)}

    def test_tat_overlap_409(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        first = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
            tat_min=1,
            tat_max=7,
        )
        assert first.status_code == 201, first.text
        second = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
            tat_min=5,
            tat_max=10,
        )
        assert second.status_code == 409, second.text

    def test_route_mints_work_order(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert mapped.status_code == 201, mapped.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-ROUTE")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body(
                [sample_id], p2_seed["analysis_a"].id, tat_days=5, params={}
            ),
            headers=_auth(admin_token),
        )
        assert created.status_code == 201, created.text
        tests_before = db_session.query(Test).count()
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text
        item = routed.json()["items"][0]
        assert item["no_route"] is False
        wo = item["work_order"]
        assert wo is not None
        assert wo["status"] == "queued"
        assert wo["asked_for_id"] == af_id
        assert str(definition["id"]) in wo["process_definition_ids"]
        got = client.get(f"/v1/asked-for/{af_id}", headers=_auth(admin_token))
        assert got.json()["status"] == "routed"
        assert got.json()["routed_work_order_id"] == wo["id"]
        assert db_session.query(Test).count() == tests_before

        listed = client.get("/v1/work-orders", headers=_auth(admin_token))
        assert listed.status_code == 200, listed.text
        assert listed.json()["count"] >= 1

        started = client.post(
            f"/v1/work-orders/{wo['id']}/start", headers=_auth(admin_token)
        )
        assert started.status_code == 200, started.text
        assert started.json()["status"] == "in_progress"
        assert started.json()["process_id"] is not None
        assert started.json()["started_count"] == 1

    def test_wo7_mints_test_at_lims_run_start(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        assert (
            _create_map(
                client,
                admin_token,
                analysis_id=p2_seed["analysis_a"].id,
                definition_id=definition["id"],
            ).status_code
            == 201
        )
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-WO7")
        defs = client.put(
            f"/analyses/{p2_seed['analysis_a'].id}/param-defs",
            json={
                "items": [
                    {
                        "key": "cell_line",
                        "data_type": "text",
                        "required": False,
                        "sort_order": 0,
                    }
                ]
            },
            headers=_auth(admin_token),
        )
        assert defs.status_code == 200, defs.text
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body(
                [sample_id],
                p2_seed["analysis_a"].id,
                params={"cell_line": "A549"},
            ),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text
        tests_before = db_session.query(Test).count()

        run = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "analysis_id": str(p2_seed["analysis_a"].id),
            },
            headers=_auth(admin_token),
        )
        assert run.status_code == 201, run.text
        run_id = run.json()["id"]
        started = client.patch(
            f"/v1/lims-runs/{run_id}/start",
            json={"sample_ids": [sample_id]},
            headers=_auth(admin_token),
        )
        assert started.status_code == 200, started.text
        db_session.expire_all()
        assert db_session.query(Test).count() == tests_before + 1
        test = (
            db_session.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == p2_seed["analysis_a"].id,
            )
            .one()
        )
        assert test.asked_for_params == {"cell_line": "A549"}

        db_session.delete(test)
        db_session.commit()
        review = client.patch(
            f"/v1/lims-runs/{run_id}/review", headers=_auth(admin_token)
        )
        assert review.status_code == 200, review.text
        published = client.patch(
            f"/v1/lims-runs/{run_id}/complete", headers=_auth(admin_token)
        )
        assert published.status_code == 422, published.text
        body = published.json()
        detail = body.get("detail") if isinstance(body, dict) else body
        text = detail if isinstance(detail, str) else str(detail)
        assert "WO-7" in text or "Test missing" in text or "test_missing" in text
        still = client.get(f"/v1/lims-runs/{run_id}", headers=_auth(admin_token))
        assert still.status_code == 200, still.text
        assert still.json()["status"] == "complete"

    def test_wo7_first_start_freeze(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        definition = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, definition, p2_seed["sample_type"].id)
        assert (
            _create_map(
                client,
                admin_token,
                analysis_id=p2_seed["analysis_a"].id,
                definition_id=definition["id"],
            ).status_code
            == 201
        )
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-FREEZE")
        defs = client.put(
            f"/analyses/{p2_seed['analysis_a'].id}/param-defs",
            json={
                "items": [
                    {
                        "key": "cell_line",
                        "data_type": "text",
                        "required": False,
                        "sort_order": 0,
                    }
                ]
            },
            headers=_auth(admin_token),
        )
        assert defs.status_code == 200, defs.text
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body(
                [sample_id],
                p2_seed["analysis_a"].id,
                params={"cell_line": "A549"},
            ),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text

        run = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "analysis_id": str(p2_seed["analysis_a"].id),
            },
            headers=_auth(admin_token),
        )
        run_id = run.json()["id"]
        started = client.patch(
            f"/v1/lims-runs/{run_id}/start",
            json={"sample_ids": [sample_id]},
            headers=_auth(admin_token),
        )
        assert started.status_code == 200, started.text
        db_session.expire_all()
        test = (
            db_session.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == p2_seed["analysis_a"].id,
            )
            .one()
        )
        assert test.asked_for_params == {"cell_line": "A549"}

        asked = db_session.query(AskedFor).filter(AskedFor.id == af_id).one()
        asked.params = {"cell_line": "HeLa"}
        db_session.commit()

        run2 = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "analysis_id": str(p2_seed["analysis_a"].id),
            },
            headers=_auth(admin_token),
        )
        started2 = client.patch(
            f"/v1/lims-runs/{run2.json()['id']}/start",
            json={"sample_ids": [sample_id]},
            headers=_auth(admin_token),
        )
        assert started2.status_code == 200, started2.text
        db_session.expire_all()
        test = (
            db_session.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == p2_seed["analysis_a"].id,
            )
            .one()
        )
        assert test.asked_for_params == {"cell_line": "A549"}

        asked = db_session.query(AskedFor).filter(AskedFor.id == af_id).one()
        asked.status = "cancelled"
        db_session.commit()
        run3 = client.post(
            "/v1/lims-runs",
            json={
                "name": f"Run {uuid4().hex[:8]}",
                "analysis_id": str(p2_seed["analysis_a"].id),
            },
            headers=_auth(admin_token),
        )
        started3 = client.patch(
            f"/v1/lims-runs/{run3.json()['id']}/start",
            json={"sample_ids": [sample_id]},
            headers=_auth(admin_token),
        )
        assert started3.status_code == 200, started3.text
        db_session.expire_all()
        test = (
            db_session.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == p2_seed["analysis_a"].id,
            )
            .one()
        )
        assert test.asked_for_params == {"cell_line": "A549"}

    def test_extract_vs_qubit_same_tat_saves(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        qubit = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, qubit, p2_seed["dna_type"].id)
        first = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=extract["id"],
            tat_min=1,
            tat_max=10,
        )
        assert first.status_code == 201, first.text
        second = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=qubit["id"],
            tat_min=1,
            tat_max=10,
        )
        assert second.status_code == 201, second.text

    def test_route_409_when_two_maps_accept_type(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        qubit = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, qubit, p2_seed["dna_type"].id)
        assert (
            _create_map(
                client,
                admin_token,
                analysis_id=p2_seed["analysis_a"].id,
                definition_id=extract["id"],
            ).status_code
            == 201
        )
        assert (
            _create_map(
                client,
                admin_token,
                analysis_id=p2_seed["analysis_a"].id,
                definition_id=qubit["id"],
            ).status_code
            == 201
        )
        both = client.put(
            f"/v1/eln-process-definitions/{qubit['id']}/steps/{qubit['steps'][0]['id']}/accepted-sample-types",
            json={
                "sample_type_ids": [
                    str(p2_seed["sample_type"].id),
                    str(p2_seed["dna_type"].id),
                ]
            },
            headers=_auth(admin_token),
        )
        assert both.status_code == 200, both.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-AMBIG")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        before = db_session.query(WorkOrder).count()
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 409, routed.text
        assert db_session.query(WorkOrder).count() == before

    def test_later_start_advances_and_gates_type(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        analysis = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        reporting = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, analysis, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, reporting, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_ids=[extract["id"], analysis["id"], reporting["id"]],
        )
        assert mapped.status_code == 201, mapped.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-LATER")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        wo_id = routed.json()["items"][0]["work_order"]["id"]

        first = client.post(
            f"/v1/work-orders/{wo_id}/start", headers=_auth(admin_token)
        )
        assert first.status_code == 200, first.text
        assert first.json()["started_count"] == 1
        first_process = first.json()["process_id"]

        second = client.post(
            f"/v1/work-orders/{wo_id}/start", headers=_auth(admin_token)
        )
        assert second.status_code == 200, second.text
        assert second.json()["started_count"] == 2
        assert second.json()["process_id"] == first_process
        assert second.json()["latest_process_id"] != first_process

        third = client.post(
            f"/v1/work-orders/{wo_id}/start", headers=_auth(admin_token)
        )
        assert third.status_code == 200, third.text
        assert third.json()["started_count"] == 3
        done = client.post(
            f"/v1/work-orders/{wo_id}/start", headers=_auth(admin_token)
        )
        assert done.status_code == 422, done.text
        db_session.expire_all()
        positions = [
            p.work_order_route_position
            for p in db_session.query(ELNProcess).filter(
                ELNProcess.work_order_id == wo_id
            )
        ]
        assert sorted(positions) == [1, 2, 3]

    def test_later_process_start_incompatible_type_422(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        qubit = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, qubit, p2_seed["dna_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_ids=[extract["id"], qubit["id"]],
        )
        assert mapped.status_code == 422, mapped.text
        detail = mapped.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"
        assert "emerging" in str(detail.get("message", "")).lower()

    def test_later_step_start_incompatible_type_422(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        created_def = client.post(
            "/v1/eln-process-definitions",
            json={
                "name": f"SOP extract-qc {uuid4().hex[:8]}",
                "steps": [
                    {
                        "analysis_id": str(p2_seed["analysis_a"].id),
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "Extract",
                        "sort_order": 0,
                    },
                    {
                        "analysis_id": str(p2_seed["analysis_a"].id),
                        "step_kind": "lims_run",
                        "execution_mode": "lims_run",
                        "name": "QC",
                        "sort_order": 1,
                    },
                ],
            },
            headers=_auth(admin_token),
        )
        definition = created_def.json()
        steps = sorted(definition["steps"], key=lambda s: s["sort_order"])
        client.put(
            f"/v1/eln-process-definitions/{definition['id']}/steps/{steps[0]['id']}/accepted-sample-types",
            json={"sample_type_ids": [str(p2_seed["sample_type"].id)]},
            headers=_auth(admin_token),
        )
        client.put(
            f"/v1/eln-process-definitions/{definition['id']}/steps/{steps[1]['id']}/accepted-sample-types",
            json={"sample_type_ids": [str(p2_seed["dna_type"].id)]},
            headers=_auth(admin_token),
        )
        mapped = _create_map(
            client,
            admin_token,
            analysis_id=p2_seed["analysis_a"].id,
            definition_id=definition["id"],
        )
        assert mapped.status_code == 201, mapped.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-STEP")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        routed = client.post(
            f"/v1/asked-for/{created.json()['items'][0]['id']}/route",
            headers=_auth(admin_token),
        )
        wo_id = routed.json()["items"][0]["work_order"]["id"]
        started = client.post(
            f"/v1/work-orders/{wo_id}/start", headers=_auth(admin_token)
        )
        process_id = started.json()["process_id"]
        proc = client.get(
            f"/v1/eln-processes/{process_id}", headers=_auth(admin_token)
        )
        assert proc.status_code == 200, proc.text
        inst_steps = sorted(proc.json()["steps"], key=lambda s: s["sort_order"])
        first_step = client.post(
            f"/v1/eln-processes/{process_id}/steps/{inst_steps[0]['id']}/start",
            json={},
            headers=_auth(admin_token),
        )
        assert first_step.status_code == 201, first_step.text
        second_step = client.post(
            f"/v1/eln-processes/{process_id}/steps/{inst_steps[1]['id']}/start",
            json={},
            headers=_auth(admin_token),
        )
        assert second_step.status_code == 422, second_step.text
        detail = second_step.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"

    def test_route_matches_analysis_on_later_lims_run(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        later = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_b"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, later, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            definition_ids=[extract["id"], later["id"]],
        )
        assert mapped.status_code == 201, mapped.text
        analysis_ids = {
            aid
            for row in mapped.json()
            for aid in (row.get("analysis_ids") or [])
        }
        assert str(p2_seed["analysis_b"].id) in analysis_ids
        assert str(p2_seed["analysis_a"].id) in analysis_ids

        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-LATERAN")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_b"].id),
            headers=_auth(admin_token),
        )
        af_id = created.json()["items"][0]["id"]
        routed = client.post(f"/v1/asked-for/{af_id}/route", headers=_auth(admin_token))
        assert routed.status_code == 200, routed.text
        wo = routed.json()["items"][0]["work_order"]
        assert wo["analysis_id"] == str(p2_seed["analysis_b"].id)
        assert wo["process_definition_ids"] == [
            str(extract["id"]),
            str(later["id"]),
        ]

    def test_route_422_when_analysis_not_in_chain(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
        db_session: Session,
    ):
        extract = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, extract, p2_seed["sample_type"].id)
        assert (
            _create_map(
                client, admin_token, definition_id=extract["id"]
            ).status_code
            == 201
        )
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-NOAN")
        created = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_b"].id),
            headers=_auth(admin_token),
        )
        before = db_session.query(WorkOrder).count()
        routed = client.post(
            f"/v1/asked-for/{created.json()['items'][0]['id']}/route",
            headers=_auth(admin_token),
        )
        assert routed.status_code == 422, routed.text
        detail = routed.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"
        assert db_session.query(WorkOrder).count() == before

    def test_same_first_types_different_analyses_same_tat_saves(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        elisa = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        ngs = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_b"].id
        )
        _put_step_types(client, admin_token, elisa, p2_seed["sample_type"].id)
        _put_step_types(client, admin_token, ngs, p2_seed["sample_type"].id)
        first = _create_map(
            client, admin_token, definition_id=elisa["id"], tat_min=1, tat_max=10
        )
        assert first.status_code == 201, first.text
        second = _create_map(
            client, admin_token, definition_id=ngs["id"], tat_min=1, tat_max=10
        )
        assert second.status_code == 201, second.text
        sample_id = _receive_sample(client, admin_token, p2_seed, "NBIO-P2-SPLIT")
        asked_a = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        routed_a = client.post(
            f"/v1/asked-for/{asked_a.json()['items'][0]['id']}/route",
            headers=_auth(admin_token),
        )
        assert routed_a.status_code == 200, routed_a.text
        asked_b = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], p2_seed["analysis_b"].id),
            headers=_auth(admin_token),
        )
        routed_b = client.post(
            f"/v1/asked-for/{asked_b.json()['items'][0]['id']}/route",
            headers=_auth(admin_token),
        )
        assert routed_b.status_code == 200, routed_b.text

    def test_map_save_handoff_dest_type_accepted(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_extract_process(
            client,
            admin_token,
            dest_type_id=p2_seed["dna_type"].id,
            inbound_type_id=p2_seed["sample_type"].id,
        )
        qubit = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, qubit, p2_seed["dna_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            definition_ids=[extract["id"], qubit["id"]],
        )
        assert mapped.status_code == 201, mapped.text
        got = client.get(
            f"/v1/eln-process-definitions/{extract['id']}",
            headers=_auth(admin_token),
        )
        assert got.status_code == 200, got.text
        assert str(p2_seed["dna_type"].id) in [
            str(t) for t in got.json().get("emerging_sample_type_ids") or []
        ]

    def test_map_save_handoff_dest_type_rejected(
        self,
        client: TestClient,
        admin_token: str,
        p2_seed,
    ):
        extract = _create_extract_process(
            client,
            admin_token,
            dest_type_id=p2_seed["dna_type"].id,
            inbound_type_id=p2_seed["sample_type"].id,
        )
        later = _create_lims_run_definition(
            client, admin_token, p2_seed["analysis_a"].id
        )
        _put_step_types(client, admin_token, later, p2_seed["sample_type"].id)
        mapped = _create_map(
            client,
            admin_token,
            definition_ids=[extract["id"], later["id"]],
        )
        assert mapped.status_code == 422, mapped.text
        detail = mapped.json()["detail"]
        assert isinstance(detail, dict)
        assert detail["code"] == "route_sample_type"
        assert "emerging" in str(detail.get("message", "")).lower()


class TestListNameAlias:
    def test_sample_type_alias_resolves_sample_types(
        self,
        client: TestClient,
        admin_token: str,
        db_session: Session,
    ):
        lst = List(name="sample_types", description="Sample types slug")
        db_session.add(lst)
        db_session.flush()
        db_session.add(ListEntry(list_id=lst.id, name="Plasma"))
        db_session.commit()
        r = client.get("/lists/sample_type/entries", headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        assert any(e.get("name") == "Plasma" for e in r.json())
