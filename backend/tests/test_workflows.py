"""
Pytest tests for workflow templates CRUD, execute (valid/invalid steps),
transaction rollback on failure, and RBAC.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.security import get_password_hash, create_access_token
from models.user import User, Role, Permission, RolePermission
from models.workflow import WorkflowTemplate, WorkflowInstance


# ---------- Fixtures ----------


@pytest.fixture
def workflow_template_payload():
    """Valid payload for creating a workflow template."""
    return {
        "name": f"Test Template {uuid4().hex[:8]}",
        "description": "Test workflow",
        "active": True,
        "template_definition": {
            "steps": [
                {"action": "update_status", "params": {}},
                {"action": "validate_custom", "params": {}},
            ],
        },
    }


@pytest.fixture
def auth_headers_admin(client: TestClient):
    """Auth headers for admin user (config:edit + workflow:execute)."""
    login = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_config_edit_only(db_session: Session):
    """User with config:edit only (no workflow:execute)."""
    role = Role(name=f"ConfigOnly_{uuid4().hex[:6]}", description="Config edit only")
    db_session.add(role)
    db_session.flush()
    perm = db_session.query(Permission).filter(Permission.name == "config:edit").first()
    if not perm:
        perm = Permission(name="config:edit", description="Edit config")
        db_session.add(perm)
        db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = User(
        name="Config User",
        username=f"configuser_{uuid4().hex[:6]}",
        email="config@test.com",
        password_hash=get_password_hash("pass"),
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_execute_only(db_session: Session):
    """User with workflow:execute only (no config:edit)."""
    role = Role(name=f"ExecuteOnly_{uuid4().hex[:6]}", description="Execute only")
    db_session.add(role)
    db_session.flush()
    perm = db_session.query(Permission).filter(Permission.name == "workflow:execute").first()
    if not perm:
        perm = Permission(name="workflow:execute", description="Execute workflows")
        db_session.add(perm)
        db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = User(
        name="Execute User",
        username=f"executeuser_{uuid4().hex[:6]}",
        email="execute@test.com",
        password_hash=get_password_hash("pass"),
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_no_workflow_perms(db_session: Session):
    """User with no config:edit and no workflow:execute."""
    role = Role(name=f"NoWorkflow_{uuid4().hex[:6]}", description="No workflow perms")
    db_session.add(role)
    db_session.flush()
    perm = db_session.query(Permission).filter(Permission.name == "sample:read").first()
    if not perm:
        perm = Permission(name="sample:read", description="Read samples")
        db_session.add(perm)
        db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = User(
        name="No Perm User",
        username=f"noperm_{uuid4().hex[:6]}",
        email="noperm@test.com",
        password_hash=get_password_hash("pass"),
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _token_for_user(user: User, db_session: Session) -> str:
    """Build JWT for a user (permissions from role)."""
    perms = (
        db_session.query(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .filter(RolePermission.role_id == user.role_id)
        .all()
    )
    perm_names = [p.name for p in perms]
    return create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.name,
        "permissions": perm_names,
    })


# ---------- Template CRUD ----------


class TestWorkflowTemplateCRUD:
    """Workflow template list, create, get, update, delete."""

    def test_list_templates_empty(self, client: TestClient, auth_headers_admin):
        r = client.get("/admin/workflow-templates", headers=auth_headers_admin)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_templates_filter_active(self, client: TestClient, auth_headers_admin, db_session: Session):
        # Create one active, one inactive
        t1 = WorkflowTemplate(
            name=f"Active_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        t2 = WorkflowTemplate(
            name=f"Inactive_{uuid4().hex[:8]}",
            description="",
            active=False,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add_all([t1, t2])
        db_session.commit()
        r_all = client.get("/admin/workflow-templates", headers=auth_headers_admin)
        assert r_all.status_code == 200
        assert len(r_all.json()) >= 2
        r_active = client.get("/admin/workflow-templates?active=true", headers=auth_headers_admin)
        assert r_active.status_code == 200
        names_active = [x["name"] for x in r_active.json()]
        assert t1.name in names_active
        assert t2.name not in names_active
        r_inactive = client.get("/admin/workflow-templates?active=false", headers=auth_headers_admin)
        assert r_inactive.status_code == 200
        names_inactive = [x["name"] for x in r_inactive.json()]
        assert t2.name in names_inactive

    def test_create_template_success(self, client: TestClient, auth_headers_admin, workflow_template_payload):
        r = client.post(
            "/admin/workflow-templates",
            json=workflow_template_payload,
            headers=auth_headers_admin,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == workflow_template_payload["name"]
        assert data["description"] == workflow_template_payload["description"]
        assert data["active"] is True
        assert data["template_definition"]["steps"] == workflow_template_payload["template_definition"]["steps"]
        assert "id" in data
        assert "created_at" in data

    def test_create_template_duplicate_name(self, client: TestClient, auth_headers_admin, workflow_template_payload):
        r1 = client.post(
            "/admin/workflow-templates",
            json=workflow_template_payload,
            headers=auth_headers_admin,
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/admin/workflow-templates",
            json=workflow_template_payload,
            headers=auth_headers_admin,
        )
        assert r2.status_code == 400
        assert "already exists" in (r2.json().get("detail") or "")

    def test_create_template_invalid_definition(self, client: TestClient, auth_headers_admin, workflow_template_payload):
        workflow_template_payload["template_definition"] = {"steps": [{"action": "invalid_action", "params": {}}]}
        r = client.post(
            "/admin/workflow-templates",
            json=workflow_template_payload,
            headers=auth_headers_admin,
        )
        assert r.status_code == 422  # validation error

    def test_get_template_success(self, client: TestClient, auth_headers_admin, db_session: Session):
        t = WorkflowTemplate(
            name=f"GetMe_{uuid4().hex[:8]}",
            description="Get test",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.get(f"/admin/workflow-templates/{t.id}", headers=auth_headers_admin)
        assert r.status_code == 200
        assert r.json()["id"] == str(t.id)
        assert r.json()["name"] == t.name

    def test_get_template_not_found(self, client: TestClient, auth_headers_admin):
        r = client.get(f"/admin/workflow-templates/{uuid4()}", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_update_template_success(self, client: TestClient, auth_headers_admin, db_session: Session):
        t = WorkflowTemplate(
            name=f"UpdateMe_{uuid4().hex[:8]}",
            description="Original",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.patch(
            f"/admin/workflow-templates/{t.id}",
            json={"description": "Updated desc", "active": False},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        assert r.json()["description"] == "Updated desc"
        assert r.json()["active"] is False

    def test_delete_template_soft_deactivate(self, client: TestClient, auth_headers_admin, db_session: Session):
        t = WorkflowTemplate(
            name=f"DeleteMe_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.delete(f"/admin/workflow-templates/{t.id}", headers=auth_headers_admin)
        assert r.status_code == 204
        db_session.refresh(t)
        assert t.active is False


# ---------- Execute: valid / invalid steps ----------


class TestWorkflowExecute:
    """Execute workflow: valid steps, invalid action, and rollback."""

    def test_execute_valid_steps(self, client: TestClient, auth_headers_admin, db_session: Session):
        t = WorkflowTemplate(
            name=f"ExecOK_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={
                "steps": [
                    {"action": "update_status", "params": {}},
                    {"action": "validate_custom", "params": {}},
                ],
            },
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.post(
            f"/workflows/execute/{t.id}",
            json={"context": {"batch_id": "00000000-0000-0000-0000-000000000001"}},
            headers=auth_headers_admin,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["workflow_template_id"] == str(t.id)
        assert data["runtime_state"]["completed"] is True
        assert len(data["runtime_state"]["steps_run"]) == 2
        assert data["runtime_state"]["steps_run"][0]["action"] == "update_status"
        assert data["runtime_state"]["steps_run"][0]["status"] == "ok"

    def test_execute_invalid_action_returns_400(self, client: TestClient, auth_headers_admin, db_session: Session):
        # Template must be created with valid steps (API validates on create).
        # So we create a valid template, then we need to test invalid action at execute time.
        # The execute endpoint reads steps from the template; we cannot pass invalid steps in the body.
        # So invalid action only happens if the template was created with invalid action - but create
        # validates and returns 422. So we test: template with valid steps -> execute returns 201.
        # For "invalid step" we can only get that if the schema allowed it - it doesn't on create.
        # So we test execute with template that has empty steps (valid) and then test that a template
        # with one invalid step cannot be created (already in test_create_template_invalid_definition).
        # Alternatively, we could add a template directly in DB with invalid action and call execute.
        t = WorkflowTemplate(
            name=f"InvalidStep_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={"steps": [{"action": "not_valid_action", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.post(
            f"/workflows/execute/{t.id}",
            json={"context": {}},
            headers=auth_headers_admin,
        )
        assert r.status_code == 400
        assert "Invalid action" in (r.json().get("detail") or "")

    def test_execute_inactive_template_returns_404(self, client: TestClient, auth_headers_admin, db_session: Session):
        t = WorkflowTemplate(
            name=f"Inactive_{uuid4().hex[:8]}",
            description="",
            active=False,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.post(
            f"/workflows/execute/{t.id}",
            json={"context": {}},
            headers=auth_headers_admin,
        )
        assert r.status_code == 404
        assert "not found or inactive" in (r.json().get("detail") or "").lower()

    def test_execute_template_not_found(self, client: TestClient, auth_headers_admin):
        r = client.post(
            f"/workflows/execute/{uuid4()}",
            json={"context": {}},
            headers=auth_headers_admin,
        )
        assert r.status_code == 404

    def test_transaction_rollback_on_step_failure(
        self, client: TestClient, auth_headers_admin, db_session: Session, monkeypatch
    ):
        """When a step raises, no WorkflowInstance should be created (transaction rollback)."""
        from app.routers import workflows as workflow_router

        t = WorkflowTemplate(
            name=f"Rollback_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={
                "steps": [
                    {"action": "update_status", "params": {}},
                    {"action": "validate_custom", "params": {}},
                ],
            },
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        count_before = db_session.query(WorkflowInstance).filter(
            WorkflowInstance.workflow_template_id == t.id
        ).count()

        def _run_action_fail(*args, **kwargs):
            raise RuntimeError("Simulated step failure")

        monkeypatch.setattr(workflow_router, "_run_action", _run_action_fail)
        r = client.post(
            f"/workflows/execute/{t.id}",
            json={"context": {}},
            headers=auth_headers_admin,
        )
        assert r.status_code == 500
        count_after = db_session.query(WorkflowInstance).filter(
            WorkflowInstance.workflow_template_id == t.id
        ).count()
        assert count_after == count_before, "WorkflowInstance must not be created on step failure"


# ---------- RBAC ----------


class TestWorkflowRBAC:
    """Template CRUD requires config:edit; execute requires workflow:execute."""

    def test_list_templates_requires_config_edit(
        self, client: TestClient, user_no_workflow_perms, db_session: Session
    ):
        token = _token_for_user(user_no_workflow_perms, db_session)
        r = client.get("/admin/workflow-templates", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
        assert "config:edit" in (r.json().get("detail") or "").lower() or "permission" in (r.json().get("detail") or "").lower()

    def test_create_template_requires_config_edit(
        self, client: TestClient, user_execute_only, db_session: Session, workflow_template_payload
    ):
        """User with workflow:execute but no config:edit cannot create templates."""
        token = _token_for_user(user_execute_only, db_session)
        r = client.post(
            "/admin/workflow-templates",
            json=workflow_template_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    def test_execute_requires_workflow_execute(
        self, client: TestClient, user_config_edit_only, db_session: Session
    ):
        """User with config:edit but no workflow:execute cannot execute."""
        t = WorkflowTemplate(
            name=f"RBAC_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        token = _token_for_user(user_config_edit_only, db_session)
        r = client.post(
            f"/workflows/execute/{t.id}",
            json={"context": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
        assert "workflow" in (r.json().get("detail") or "").lower() or "permission" in (r.json().get("detail") or "").lower()

    def test_unauthenticated_template_list(self, client: TestClient):
        r = client.get("/admin/workflow-templates")
        assert r.status_code == 403  # no auth

    def test_unauthenticated_execute(self, client: TestClient, db_session: Session):
        t = WorkflowTemplate(
            name=f"Unauth_{uuid4().hex[:8]}",
            description="",
            active=True,
            template_definition={"steps": [{"action": "update_status", "params": {}}]},
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        r = client.post(f"/workflows/execute/{t.id}", json={"context": {}})
        assert r.status_code == 403
