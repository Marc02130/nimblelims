"""P1 asked-for lake: create / unique / params / AuthZ / zero Tests / receive freeze."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from models.analysis import Analysis
from models.container import ContainerType
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.asked_for import AskedFor
from models.sample import Sample
from models.test import Test
from models.user import Permission, Role, User, role_permissions


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
    discarded = ListEntry(
        list_id=status_list.id, name="Discarded", description="Discarded"
    )
    sample_type = ListEntry(list_id=type_list.id, name="Plasma", description="Plasma")
    matrix = ListEntry(list_id=matrix_list.id, name="Serum", description="Serum")
    project_active = ListEntry(
        list_id=project_status_list.id, name="Active", description="Active"
    )
    db_session.add_all([available, discarded, sample_type, matrix, project_active])

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
        name=f"ELISA-{uuid4().hex[:6]}",
        description="Asked-for A",
        turnaround_time=5,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(analysis_a)
    db_session.flush()

    project = Project(
        name=f"AF-P1-{uuid4().hex[:8]}",
        description="Asked-for P1 project",
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
        "discarded": discarded,
        "sample_type": sample_type,
        "matrix": matrix,
        "tube": tube,
        "project": project,
        "project_active": project_active,
        "analysis_a": analysis_a,
    }


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _receive_body(receive_seed, *, barcode: str):
    return {
        "container_barcode": barcode,
        "additional_container_barcodes": [],
        "sample_type": str(receive_seed["sample_type"].id),
        "project_id": str(receive_seed["project"].id),
        "container_type_id": str(receive_seed["tube"].id),
        "analysis_ids": [],
    }


def _receive_sample(client: TestClient, admin_token: str, receive_seed, barcode: str) -> str:
    r = client.post(
        "/samples/receive",
        json=_receive_body(receive_seed, barcode=barcode),
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["sample_id"]


def _user_with_perms(
    db_session: Session,
    test_admin_user: User,
    *,
    role_name: str,
    username: str,
    perm_names: list[str],
):
    role = Role(name=role_name, description=role_name)
    db_session.add(role)
    db_session.flush()
    perms = (
        db_session.query(Permission).filter(Permission.name.in_(perm_names)).all()
    )
    for p in perms:
        db_session.execute(
            role_permissions.insert().values(role_id=role.id, permission_id=p.id)
        )
    user = User(
        name=username,
        username=username,
        email=f"{username}-{uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("Labtech1234!"),
        role_id=role.id,
        client_id=test_admin_user.client_id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": role_name,
            "permissions": perm_names,
        }
    )
    return user, token


def _asked_for_body(sample_ids, analysis_id, tat_days=5, params=None, **extra):
    body = {
        "sample_ids": [str(s) for s in sample_ids],
        "analysis_id": str(analysis_id),
        "tat_days": tat_days,
        "params": params if params is not None else {},
    }
    body.update(extra)
    return body


class TestAskedForP1:
    def test_create_empty_params_zero_tests(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        user, token = _user_with_perms(
            db_session,
            test_admin_user,
            role_name="Lab Technician",
            username="af-tech",
            perm_names=["test:assign", "sample:read"],
        )
        db_session.add(ProjectUser(project_id=receive_seed["project"].id, user_id=user.id))
        db_session.commit()

        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-0001")
        before = db_session.query(Test).count()
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], receive_seed["analysis_a"].id),
            headers=_auth(token),
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["count"] == 1
        assert data["items"][0]["status"] == "requested"
        assert data["items"][0]["params"] == {}
        assert data["items"][0]["tat_days"] == 5
        assert db_session.query(Test).count() == before

    def test_duplicate_open_409(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-DUP")
        body = _asked_for_body([sample_id], receive_seed["analysis_a"].id)
        first = client.post("/v1/asked-for", json=body, headers=_auth(admin_token))
        assert first.status_code == 201, first.text
        second = client.post("/v1/asked-for", json=body, headers=_auth(admin_token))
        assert second.status_code == 409, second.text

    def test_cancel_then_recreate(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-CAN")
        body = _asked_for_body([sample_id], receive_seed["analysis_a"].id)
        first = client.post("/v1/asked-for", json=body, headers=_auth(admin_token))
        assert first.status_code == 201, first.text
        af_id = first.json()["items"][0]["id"]
        cancel = client.post(
            f"/v1/asked-for/{af_id}/cancel",
            headers=_auth(admin_token),
        )
        assert cancel.status_code == 200, cancel.text
        assert cancel.json()["status"] == "cancelled"
        second = client.post("/v1/asked-for", json=body, headers=_auth(admin_token))
        assert second.status_code == 201, second.text

    def test_unknown_param_key_422(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        analysis_id = receive_seed["analysis_a"].id
        put = client.put(
            f"/analyses/{analysis_id}/param-defs",
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
        assert put.status_code == 200, put.text
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-PARAM")
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body(
                [sample_id],
                analysis_id,
                params={"cell_line": "A549", "nope": 1},
            ),
            headers=_auth(admin_token),
        )
        assert r.status_code == 422, r.text
        assert "Unknown param key" in r.text

    def test_empty_defs_empty_params_ok(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-EMPTY")
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], receive_seed["analysis_a"].id, params={}),
            headers=_auth(admin_token),
        )
        assert r.status_code == 201, r.text

    def test_tat_days_zero_422(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-TAT")
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body(
                [sample_id], receive_seed["analysis_a"].id, tat_days=0
            ),
            headers=_auth(admin_token),
        )
        assert r.status_code == 422, r.text

    def test_hidden_sample_403_not_404(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        tech, token = _user_with_perms(
            db_session,
            test_admin_user,
            role_name="Lab Technician",
            username="af-no-project",
            perm_names=["test:assign", "sample:read"],
        )
        other = Project(
            name=f"AF-OTHER-{uuid4().hex[:8]}",
            description="Other project",
            start_date=datetime.utcnow(),
            client_id=test_admin_user.client_id,
            status=receive_seed["project_active"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(other)
        db_session.flush()
        db_session.add(ProjectUser(project_id=other.id, user_id=test_admin_user.id))
        db_session.commit()

        body = _receive_body(receive_seed, barcode="NBIO-AF-HIDDEN")
        body["project_id"] = str(other.id)
        rec = client.post("/samples/receive", json=body, headers=_auth(admin_token))
        assert rec.status_code == 201, rec.text
        sample_id = rec.json()["sample_id"]

        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], receive_seed["analysis_a"].id),
            headers=_auth(token),
        )
        assert r.status_code == 403, r.text
        assert r.status_code != 404
        assert "insufficient project permissions" in r.text

    def test_client_with_test_assign_still_403(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        _user, token = _user_with_perms(
            db_session,
            test_admin_user,
            role_name="Client",
            username="af-client-assign",
            perm_names=["test:assign", "sample:read"],
        )
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-CLI2")
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], receive_seed["analysis_a"].id),
            headers=_auth(token),
        )
        assert r.status_code == 403, r.text
        assert "Client role" in r.text

    def test_missing_test_assign_403(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        _user, token = _user_with_perms(
            db_session,
            test_admin_user,
            role_name="Lab Technician",
            username="af-noread",
            perm_names=["sample:read"],
        )
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-PERM")
        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([sample_id], receive_seed["analysis_a"].id),
            headers=_auth(token),
        )
        assert r.status_code == 403, r.text

    def test_receive_analysis_ids_still_422(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        before = db_session.query(Sample).count()
        body = _receive_body(receive_seed, barcode="NBIO-AF-RECV")
        body["analysis_ids"] = [str(receive_seed["analysis_a"].id)]
        r = client.post("/samples/receive", json=body, headers=_auth(admin_token))
        assert r.status_code == 422, r.text
        assert "analysis_ids must be empty" in r.text
        assert db_session.query(Sample).count() == before

    def test_multi_sample_one_duplicate_rolls_back(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        s1 = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-M1")
        s2 = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-M2")
        first = client.post(
            "/v1/asked-for",
            json=_asked_for_body([s1], receive_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        assert first.status_code == 201, first.text
        count_before = db_session.query(AskedFor).count()

        r = client.post(
            "/v1/asked-for",
            json=_asked_for_body([s2, s1], receive_seed["analysis_a"].id),
            headers=_auth(admin_token),
        )
        assert r.status_code == 409, r.text
        # IntegrityError rollback() ends the test transaction; count via a
        # nested query on the same session after expire.
        db_session.expire_all()
        leftover = (
            db_session.query(AskedFor)
            .filter(AskedFor.sample_id == s2)
            .count()
        )
        assert leftover == 0
        assert db_session.query(AskedFor).count() == count_before

    def test_sample_id_alias(
        self,
        client: TestClient,
        admin_token: str,
        receive_seed,
        db_session: Session,
        test_admin_user: User,
    ):
        sample_id = _receive_sample(client, admin_token, receive_seed, "NBIO-AF-ALIAS")
        r = client.post(
            "/v1/asked-for",
            json={
                "sample_id": sample_id,
                "analysis_id": str(receive_seed["analysis_a"].id),
                "tat_days": 3,
                "params": {},
            },
            headers=_auth(admin_token),
        )
        assert r.status_code == 201, r.text
        assert r.json()["count"] == 1
