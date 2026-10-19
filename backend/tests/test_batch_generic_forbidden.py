"""Legacy batch denials use the same generic 403 body as F10.

The visibility probe returns 403 before this code when the batch is hidden.
These tests make the batch visible to a lab technician (a project_users row)
whose client is not the project's client, so the older client check runs.
The compatibility helper is the same rule: the message has no project id.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.core.security import create_access_token, get_password_hash
from models.batch import Batch, BatchContainer
from models.client import Client
from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.sample import Sample
from models.user import Permission, Role, User
from tests.conftest import _get_or_create, _grant


def _token(user: User) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "permissions": ["batch:update", "batch:manage"],
            "pwd_epoch": 0,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _world(db_session, *, assign: bool):
    suffix = uuid4().hex[:8]
    tech_org = Client(name=f"Tech Org {suffix}")
    project_org = Client(name=f"Project Org {suffix}")
    db_session.add_all([tech_org, project_org])
    db_session.flush()

    role = _get_or_create(db_session, Role, "Lab Technician", "Laboratory technician")
    perms = [
        _get_or_create(db_session, Permission, "batch:update", "Update batches"),
        _get_or_create(db_session, Permission, "batch:manage", "Manage batches"),
    ]
    _grant(db_session, role, perms)
    user = User(
        name=f"Tech {suffix}",
        username=f"tech-{suffix}",
        email=f"tech-{suffix}@example.com",
        password_hash=get_password_hash("tech-password-1"),
        role_id=role.id,
        client_id=tech_org.id,
        must_change_password=False,
        password_epoch=0,
    )
    db_session.add(user)
    db_session.flush()

    catalog = List(name=f"batch-generic-{suffix}", created_by=user.id, modified_by=user.id)
    db_session.add(catalog)
    db_session.flush()
    entry = ListEntry(
        name=f"Active {suffix}",
        list_id=catalog.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(entry)
    db_session.flush()

    project = Project(
        name=f"Hidden project {suffix}",
        client_id=project_org.id,
        status=entry.id,
        start_date=date(2026, 10, 19),
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(project)
    db_session.flush()

    containers = []
    ctype = ContainerType(
        name=f"Vial {suffix}",
        rows=1,
        columns=1,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(ctype)
    db_session.flush()
    for index in (1, 2):
        sample = Sample(
            name=f"Sample {suffix}-{index}",
            sample_type=entry.id,
            status=entry.id,
            project_id=project.id,
            created_by=user.id,
            modified_by=user.id,
        )
        container = Container(
            name=f"Container {suffix}-{index}",
            row=1,
            column=1,
            type_id=ctype.id,
            created_by=user.id,
            modified_by=user.id,
        )
        db_session.add_all([sample, container])
        db_session.flush()
        db_session.add(Contents(container_id=container.id, sample_id=sample.id))
        containers.append(container)

    batch = Batch(
        name=f"Batch {suffix}",
        status=entry.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(batch)
    db_session.flush()
    db_session.add(BatchContainer(batch_id=batch.id, container_id=containers[0].id))
    if assign:
        db_session.add(
            ProjectUser(project_id=project.id, user_id=user.id, granted_by=user.id)
        )
    db_session.commit()
    return user, project, batch, containers


def test_patch_legacy_client_check_is_generic_403(client, db_session):
    user, project, batch, _containers = _world(db_session, assign=True)
    response = client.patch(
        f"/batches/{batch.id}",
        headers=_token(user),
        json={"description": "renamed"},
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["detail"] == {"code": "batch_forbidden", "message": "Access denied"}
    assert str(project.id) not in response.text
    assert str(project.client_id) not in response.text
    assert "insufficient client" not in response.text


def test_compat_helper_error_has_no_project_id(client, db_session):
    user, project, _batch, containers = _world(db_session, assign=False)
    response = client.post(
        "/batches/validate-compatibility",
        headers=_token(user),
        json={"container_ids": [str(containers[0].id), str(containers[1].id)]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["compatible"] is False
    assert body["error"] == "Access denied"
    assert str(project.id) not in response.text
    assert str(project.client_id) not in response.text
