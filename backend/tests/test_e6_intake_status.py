"""E-6: intake (accession / bulk) writes Available for Testing, not Received."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.container import ContainerType
from models.list import List, ListEntry
from models.project import Project
from models.sample import Sample
from models.user import User


@pytest.fixture
def headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def intake_seed(db_session: Session, test_admin_user: User, test_org):
    status_list = (
        db_session.query(List)
        .filter(List.name.in_(("Sample Status", "sample_status")))
        .first()
    )
    if not status_list:
        status_list = List(name="sample_status", description="E-6 statuses")
        db_session.add(status_list)
        db_session.flush()
    received = (
        db_session.query(ListEntry)
        .filter(ListEntry.list_id == status_list.id, ListEntry.name == "Received")
        .first()
    )
    if not received:
        received = ListEntry(list_id=status_list.id, name="Received")
        db_session.add(received)
        db_session.flush()
    available = (
        db_session.query(ListEntry)
        .filter(
            ListEntry.list_id == status_list.id,
            ListEntry.name == "Available for Testing",
        )
        .first()
    )
    if not available:
        available = ListEntry(list_id=status_list.id, name="Available for Testing")
        db_session.add(available)
        db_session.flush()
    sample_type = ListEntry(list_id=status_list.id, name=f"Blood_{uuid4().hex[:4]}")
    matrix = ListEntry(list_id=status_list.id, name=f"Serum_{uuid4().hex[:4]}")
    db_session.add_all([sample_type, matrix])
    db_session.flush()
    test_status_list = (
        db_session.query(List).filter(List.name.in_(("test_status", "Test Status"))).first()
    )
    if not test_status_list:
        test_status_list = List(name="test_status", description="E-6 tests")
        db_session.add(test_status_list)
        db_session.flush()
    in_process = (
        db_session.query(ListEntry)
        .filter(ListEntry.list_id == test_status_list.id, ListEntry.name == "In Process")
        .first()
    )
    if not in_process:
        in_process = ListEntry(list_id=test_status_list.id, name="In Process")
        db_session.add(in_process)
        db_session.flush()
    project = Project(
        name=f"E6 {uuid4().hex[:8]}",
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
    db_session.commit()
    return {
        "available": available,
        "received": received,
        "sample_type": sample_type,
        "matrix": matrix,
        "project": project,
        "client": test_org,
        "container_type": ctype,
    }


class TestE6IntakeStatus:
    def test_accession_writes_available_for_testing(
        self, client: TestClient, headers, intake_seed, db_session: Session
    ):
        r = client.post(
            "/samples/accession",
            json={
                "name": f"E6-ACC-{uuid4().hex[:6]}",
                "due_date": "2026-01-15T00:00:00",
                "received_date": "2026-01-01T00:00:00",
                "sample_type": str(intake_seed["sample_type"].id),
                "matrix": str(intake_seed["matrix"].id),
                "client_id": str(intake_seed["client"].id),
                "project_id": str(intake_seed["project"].id),
                "assigned_tests": [],
            },
            headers=headers,
        )
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["status"] == str(intake_seed["available"].id)
        assert body["status"] != str(intake_seed["received"].id)
        db_session.expire_all()
        sample = db_session.query(Sample).filter(Sample.id == body["id"]).first()
        assert sample is not None
        assert sample.status == intake_seed["available"].id

    def test_bulk_accession_writes_available_for_testing(
        self, client: TestClient, headers, intake_seed
    ):
        r = client.post(
            "/samples/bulk-accession",
            json={
                "due_date": "2026-01-15T00:00:00",
                "received_date": "2026-01-01T00:00:00",
                "sample_type": str(intake_seed["sample_type"].id),
                "matrix": str(intake_seed["matrix"].id),
                "client_id": str(intake_seed["client"].id),
                "project_id": str(intake_seed["project"].id),
                "container_type_id": str(intake_seed["container_type"].id),
                "uniques": [
                    {
                        "name": f"E6-B-{uuid4().hex[:6]}",
                        "container_name": f"E6-C-{uuid4().hex[:6]}",
                    }
                ],
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0]["status"] == str(intake_seed["available"].id)
