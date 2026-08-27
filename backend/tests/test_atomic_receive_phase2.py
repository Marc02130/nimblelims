"""Phase 2 atomic receive: field body hygiene (A-9 / A-10 / A-11, RQ-AR-5/8/9).

Banned body fields must 422 (extra=forbid). System sample name + default tube off-form.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.sample import Sample
from models.user import User


BANNED_FIELDS = {
    "name": "HACKED-SAMPLE-ID",
    "sample_name": "HACKED-SAMPLE-ID",
    "lab_id": "HACKED-LAB-ID",
    "status": str(uuid4()),
    "container_type_id": str(uuid4()),
    "container_type": str(uuid4()),
    "due_date": datetime.utcnow().isoformat(),
    "qc_type": str(uuid4()),
    "client_id": str(uuid4()),
}


@pytest.fixture
def receive_seed(db_session: Session, test_admin_user: User):
    status_list = List(name="Sample Status", description="Sample statuses")
    type_list = List(name="Sample Type", description="Sample types")
    matrix_list = List(name="Matrix", description="Matrices")
    project_status_list = List(name="Project Status", description="Project statuses")
    db_session.add_all([status_list, type_list, matrix_list, project_status_list])
    db_session.flush()

    available = ListEntry(
        list_id=status_list.id, name="Available for Testing", description="Ready"
    )
    sample_type = ListEntry(list_id=type_list.id, name="Blood", description="Blood")
    matrix = ListEntry(list_id=matrix_list.id, name="Serum", description="Serum")
    project_active = ListEntry(
        list_id=project_status_list.id, name="Active", description="Active"
    )
    db_session.add_all([available, sample_type, matrix, project_active])

    tube = ContainerType(
        name="Tube",
        description="Default tube",
        capacity=5,
        material="plastic",
        dimensions="1x1",
    )
    db_session.add(tube)
    db_session.flush()

    project = Project(
        name=f"AR-P2-{uuid4().hex[:8]}",
        description="Phase 2 receive project",
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
    }


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _body(receive_seed, *, barcode="NBIO-P2-0001", **overrides):
    payload = {
        "container_barcode": barcode,
        "additional_container_barcodes": [],
        "sample_type": str(receive_seed["sample_type"].id),
        "matrix": str(receive_seed["matrix"].id),
        "project_id": str(receive_seed["project"].id),
        "analysis_ids": [],
    }
    payload.update(overrides)
    return payload


class TestAtomicReceivePhase2:
    @pytest.mark.parametrize("field,value", list(BANNED_FIELDS.items()))
    def test_a11_banned_fields_422(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        field: str,
        value,
        db_session: Session,
    ):
        before = db_session.query(Sample).count()
        body = _body(receive_seed, barcode=f"NBIO-P2-{field[:8]}")
        body[field] = value
        r = client.post(
            "/samples/receive",
            json=body,
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 422, r.text
        assert db_session.query(Sample).count() == before

    def test_a9_system_sample_name_not_user_typed(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        r = client.post(
            "/samples/receive",
            json=_body(receive_seed, barcode="NBIO-P2-SYSNAME"),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        data = r.json()
        # Barcode is vessel identity; sample name comes from template/UUID fallback
        assert data["sample_name"] != "NBIO-P2-SYSNAME"
        sample = db_session.query(Sample).filter(Sample.id == data["sample_id"]).one()
        assert sample.name == data["sample_name"]

    def test_a10_default_tube_off_form(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
    ):
        other = ContainerType(
            name="Plate-96",
            description="Not the default",
            capacity=96,
            dimensions="8x12",
        )
        db_session.add(other)
        db_session.commit()

        r = client.post(
            "/samples/receive",
            json=_body(receive_seed, barcode="NBIO-P2-TUBE"),
            headers=_auth_header(admin_token),
        )
        assert r.status_code == 201, r.text
        cid = r.json()["containers"][0]["id"]
        container = db_session.query(Container).filter(Container.id == cid).one()
        assert container.type_id == receive_seed["tube"].id
        assert container.type_id != other.id

        contents = (
            db_session.query(Contents).filter(Contents.container_id == container.id).one()
        )
        assert contents.sample_id is not None
