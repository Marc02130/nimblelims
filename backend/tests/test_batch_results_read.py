"""Enter Results reads containers and tests for a batch.

GET /batches/{id}/containers used to hit POST and return 405.
GET /batches/{id}/tests did not exist (404).
"""
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.security import get_password_hash
from models.analysis import Analysis
from models.batch import Batch, BatchContainer
from models.client import Client
from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project
from models.sample import Sample
from models.test import Test
from models.user import Permission, Role, User
from tests.conftest import _get_or_create, _grant


def _login(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_batch(db_session, user, org):
    suffix = uuid4().hex[:8]
    lst = List(name=f"batch-read-{suffix}")
    db_session.add(lst)
    db_session.flush()
    status = ListEntry(list_id=lst.id, name=f"In Process {suffix}")
    sample_type = ListEntry(list_id=lst.id, name=f"type {suffix}")
    db_session.add_all([status, sample_type])
    db_session.flush()

    project = Project(
        name=f"P {suffix}",
        client_id=org.id,
        status=status.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=3),
    )
    db_session.add(project)
    db_session.flush()

    sample = Sample(
        name=f"S {suffix}",
        sample_type=sample_type.id,
        status=status.id,
        project_id=project.id,
        qc_type=status.id,
        created_by=user.id,
        modified_by=user.id,
    )
    container_type = ContainerType(
        name=f"Tube {suffix}",
        rows=1,
        columns=1,
        created_by=user.id,
        modified_by=user.id,
    )
    analysis = Analysis(
        name=f"Assay {suffix}",
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add_all([sample, container_type, analysis])
    db_session.flush()

    container = Container(
        name=f"C {suffix}",
        row=2,
        column=3,
        type_id=container_type.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(container)
    db_session.flush()
    db_session.add(Contents(container_id=container.id, sample_id=sample.id))

    batch = Batch(
        name=f"B {suffix}",
        description="results entry",
        status=status.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(batch)
    db_session.flush()
    db_session.add(BatchContainer(batch_id=batch.id, container_id=container.id))

    test = Test(
        name=f"T {suffix}",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=status.id,
        custom_attributes={},
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(test)
    db_session.commit()
    return batch, sample, container, test


def test_batch_containers_and_tests_for_enter_results(client, db_session, test_admin_user, test_org):
    batch, sample, container, test = _seed_batch(db_session, test_admin_user, test_org)
    headers = _login(client, "admin", "adminpassword")

    containers = client.get(f"/batches/{batch.id}/containers", headers=headers)
    assert containers.status_code == 200, containers.text
    body = containers.json()
    assert len(body) == 1
    assert body[0]["id"] == str(container.id)
    assert body[0]["row"] == 2
    assert body[0]["column"] == 3
    assert body[0]["contents"][0]["sample_id"] == str(sample.id)
    assert body[0]["contents"][0]["sample_name"] == sample.name
    assert body[0]["contents"][0]["qc_type"] == str(sample.qc_type)
    assert body[0]["contents"][0]["sample"]["qc_type"] == str(sample.qc_type)

    tests = client.get(f"/batches/{batch.id}/tests", headers=headers)
    assert tests.status_code == 200, tests.text
    rows = tests.json()
    assert len(rows) == 1
    assert rows[0]["id"] == str(test.id)
    assert rows[0]["name"] == test.name
    assert rows[0]["analysis_id"] == str(test.analysis_id)
    assert rows[0]["sample_id"] == str(sample.id)


def test_empty_batch_returns_empty_lists(client, db_session, test_admin_user):
    suffix = uuid4().hex[:8]
    lst = List(name=f"empty-batch-{suffix}")
    db_session.add(lst)
    db_session.flush()
    status = ListEntry(list_id=lst.id, name=f"Created {suffix}")
    db_session.add(status)
    db_session.flush()
    batch = Batch(
        name=f"Empty {suffix}",
        status=status.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(batch)
    db_session.commit()
    headers = _login(client, "admin", "adminpassword")

    containers = client.get(f"/batches/{batch.id}/containers", headers=headers)
    tests = client.get(f"/batches/{batch.id}/tests", headers=headers)
    assert containers.status_code == 200, containers.text
    assert tests.status_code == 200, tests.text
    assert containers.json() == []
    assert tests.json() == []


def test_missing_batch_is_404(client, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    missing = uuid4()
    assert client.get(f"/batches/{missing}/containers", headers=headers).status_code == 404
    assert client.get(f"/batches/{missing}/tests", headers=headers).status_code == 404


def test_batch_read_permission_is_required(client, db_session, test_admin_user, test_org, test_user):
    batch, _, _, _ = _seed_batch(db_session, test_admin_user, test_org)
    headers = _login(client, "testuser", "testpassword")
    containers = client.get(f"/batches/{batch.id}/containers", headers=headers)
    tests = client.get(f"/batches/{batch.id}/tests", headers=headers)
    assert containers.status_code == 403, containers.text
    assert tests.status_code == 403, tests.text


def test_other_client_cannot_read_the_batch(client, db_session, test_admin_user, test_org):
    batch, _, _, _ = _seed_batch(db_session, test_admin_user, test_org)
    other = Client(name=f"Other {uuid4().hex[:6]}")
    db_session.add(other)
    db_session.flush()
    role = _get_or_create(db_session, Role, "batch_reader", "Reads batches")
    perm = _get_or_create(db_session, Permission, "batch:read", "Read batches")
    _grant(db_session, role, [perm])
    outsider = User(
        name="Outsider",
        username=f"outsider-{uuid4().hex[:6]}",
        email=f"outsider-{uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("outsiderpass"),
        role_id=role.id,
        client_id=other.id,
        must_change_password=False,
    )
    db_session.add(outsider)
    db_session.commit()
    headers = _login(client, outsider.username, "outsiderpass")
    containers = client.get(f"/batches/{batch.id}/containers", headers=headers)
    tests = client.get(f"/batches/{batch.id}/tests", headers=headers)
    assert containers.status_code == 403, containers.text
    assert tests.status_code == 403, tests.text
