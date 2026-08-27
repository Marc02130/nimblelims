"""Phase 3 atomic receive: optional asked-for analyses (A-13 / AC-AR-7) + A-14 DELETE."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.analysis import Analysis, Analyte
from models.container import ContainerType
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.result import Result
from models.sample import Sample
from models.test import Test
from models.user import User


@pytest.fixture
def receive_seed(db_session: Session, test_admin_user: User):
    status_list = List(name="Sample Status", description="Sample statuses")
    type_list = List(name="Sample Type", description="Sample types")
    matrix_list = List(name="Matrix", description="Matrices")
    project_status_list = List(name="Project Status", description="Project statuses")
    test_status_list = List(name="Test Status", description="Test statuses")
    db_session.add_all(
        [status_list, type_list, matrix_list, project_status_list, test_status_list]
    )
    db_session.flush()

    available = ListEntry(
        list_id=status_list.id, name="Available for Testing", description="Ready"
    )
    sample_type = ListEntry(list_id=type_list.id, name="Blood", description="Blood")
    matrix = ListEntry(list_id=matrix_list.id, name="Serum", description="Serum")
    project_active = ListEntry(
        list_id=project_status_list.id, name="Active", description="Active"
    )
    assigned_pending = ListEntry(
        list_id=test_status_list.id,
        name="Assigned/Pending",
        description="Asked for, not started",
    )
    in_process = ListEntry(
        list_id=test_status_list.id, name="In Process", description="Work started"
    )
    db_session.add_all(
        [available, sample_type, matrix, project_active, assigned_pending, in_process]
    )

    tube = ContainerType(
        name="Tube",
        description="Default tube",
        capacity=5,
        material="plastic",
        dimensions="1x1",
    )
    db_session.add(tube)

    analysis_a = Analysis(
        name=f"ELISA-{uuid4().hex[:6]}",
        description="Asked-for A",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    analysis_b = Analysis(
        name=f"Viability-{uuid4().hex[:6]}",
        description="Asked-for B",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([analysis_a, analysis_b])
    db_session.flush()

    project = Project(
        name=f"AR-P3-{uuid4().hex[:8]}",
        description="Phase 3 receive project",
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
        "matrix": matrix,
        "tube": tube,
        "project": project,
        "assigned_pending": assigned_pending,
        "in_process": in_process,
        "analysis_a": analysis_a,
        "analysis_b": analysis_b,
    }


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _body(receive_seed, *, barcode="NBIO-P3-0001", analysis_ids=None, **overrides):
    payload = {
        "container_barcode": barcode,
        "additional_container_barcodes": [],
        "sample_type": str(receive_seed["sample_type"].id),
        "matrix": str(receive_seed["matrix"].id),
        "project_id": str(receive_seed["project"].id),
        "analysis_ids": analysis_ids if analysis_ids is not None else [],
    }
    payload.update(overrides)
    return payload


class TestAtomicReceivePhase3:
    def test_ac_ar_7_empty_analysis_ids_ok(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        r = client.post(
            "/samples/receive",
            json=_body(receive_seed, barcode="NBIO-P3-EMPTY"),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["tests"] == []
        assert (
            db_session.query(Test)
            .filter(Test.sample_id == data["sample_id"], Test.active == True)
            .count()
            == 0
        )

    def test_ac_ar_7_asked_for_assigned_pending_not_in_process(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        r = client.post(
            "/samples/receive",
            json=_body(
                receive_seed,
                barcode="NBIO-P3-ASK",
                analysis_ids=[
                    str(receive_seed["analysis_a"].id),
                    str(receive_seed["analysis_b"].id),
                ],
            ),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert len(data["tests"]) == 2
        for t in data["tests"]:
            assert t["status"] == str(receive_seed["assigned_pending"].id)
            assert t["status_name"] == "Assigned/Pending"
            assert t["status"] != str(receive_seed["in_process"].id)

        db_tests = (
            db_session.query(Test)
            .filter(Test.sample_id == data["sample_id"], Test.active == True)
            .all()
        )
        assert len(db_tests) == 2
        for t in db_tests:
            assert t.status == receive_seed["assigned_pending"].id

    def test_unknown_analysis_400_full_rollback(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        before_samples = db_session.query(Sample).count()
        before_tests = db_session.query(Test).count()
        r = client.post(
            "/samples/receive",
            json=_body(
                receive_seed,
                barcode="NBIO-P3-BADAN",
                analysis_ids=[str(uuid4())],
            ),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 400, r.text
        assert db_session.query(Sample).count() == before_samples
        assert db_session.query(Test).count() == before_tests
        assert (
            db_session.query(Sample)
            .filter(Sample.name.ilike("%NBIO-P3-BADAN%"))
            .count()
            == 0
        )

    def test_dedupe_analysis_ids(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        aid = str(receive_seed["analysis_a"].id)
        r = client.post(
            "/samples/receive",
            json=_body(
                receive_seed,
                barcode="NBIO-P3-DEDUP",
                analysis_ids=[aid, aid],
            ),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        assert len(r.json()["tests"]) == 1
        assert (
            db_session.query(Test)
            .filter(Test.sample_id == r.json()["sample_id"], Test.active == True)
            .count()
            == 1
        )

    def test_a14_delete_test_without_results_ok(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        r = client.post(
            "/samples/receive",
            json=_body(
                receive_seed,
                barcode="NBIO-P3-DEL-OK",
                analysis_ids=[str(receive_seed["analysis_a"].id)],
            ),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        test_id = r.json()["tests"][0]["id"]

        d = client.delete(
            f"/tests/{test_id}",
            headers=_auth_header(admin_token),
        )
        assert d.status_code == 200, d.text
        test = db_session.query(Test).filter(Test.id == test_id).one()
        assert test.active is False

    def test_a14_delete_test_with_results_400(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        r = client.post(
            "/samples/receive",
            json=_body(
                receive_seed,
                barcode="NBIO-P3-DEL-RES",
                analysis_ids=[str(receive_seed["analysis_a"].id)],
            ),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        test_id = r.json()["tests"][0]["id"]

        analyte = Analyte(
            name=f"IgG-{uuid4().hex[:6]}",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(analyte)
        db_session.flush()
        db_session.add(
            Result(
                test_id=test_id,
                analyte_id=analyte.id,
                reported_result="1.0",
                entered_by=test_admin_user.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        d = client.delete(
            f"/tests/{test_id}",
            headers=_auth_header(admin_token),
        )
        assert d.status_code == 400, d.text
        assert "results" in d.json()["detail"].lower()
        test = db_session.query(Test).filter(Test.id == test_id).one()
        assert test.active is True
