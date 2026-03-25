"""
Pytest tests for ExperimentProcess and ProcessStep:
  - Process CRUD (create with/without steps, list, get, delete)
  - Step CRUD (create, list, get)
  - State machine: queued → in_process → complete | failed
  - Invalid transitions return 400
  - Terminal states (complete, failed) reject all transitions
  - Timestamps set on transition (started_at, completed_at, failed_at)
  - Notes update allowed at any status
  - Regression: cross-client runs may share the same name
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from models.user import User, Role, Permission  # noqa: F401 (ensure models loaded)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ──────────────────────────────────────────────────────────────────────────────

VALID_TEMPLATE_DEF = {
    "experiment_name": "Process Test",
    "description": "test",
    "protocol_steps": ["step 1"],
    "plate_layout": {
        "plate_type": "96",
        "wells": {"A1": {"condition": "sample", "role": "unknown"}},
    },
    "transfer_steps": [],
    "result_columns": [],
    "acceptance_criteria": "",
    "mandatory_review_count": 0,
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    """Login and return bearer auth headers."""
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def experiment_template(client: TestClient, auth_headers):
    """Create a minimal ExperimentTemplate and return its id."""
    payload = {
        "name": f"Template {uuid4().hex[:8]}",
        "description": "process test template",
        "template_definition": VALID_TEMPLATE_DEF,
    }
    r = client.post("/v1/experiment-templates", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def draft_run(client: TestClient, auth_headers, experiment_template):
    """Create a run in draft status."""
    payload = {
        "name": f"Run {uuid4().hex[:8]}",
        "experiment_template_id": experiment_template,
        "description": "process test run",
    }
    r = client.post("/v1/experiment-runs", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def process(client: TestClient, auth_headers, draft_run):
    """Create a minimal process on the draft run."""
    run_id = draft_run["id"]
    r = client.post(
        f"/v1/experiment-runs/{run_id}/processes",
        json={"name": "Prep Process", "description": "test process", "sort_order": 0},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def step(client: TestClient, auth_headers, process):
    """Create a step on the process."""
    process_id = process["id"]
    r = client.post(
        f"/v1/processes/{process_id}/steps",
        json={"name": "Centrifuge", "description": "spin down", "sort_order": 0},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ──────────────────────────────────────────────────────────────────────────────
# Regression test
# ──────────────────────────────────────────────────────────────────────────────

class TestRunNameRegression:
    """Cross-client name uniqueness — two clients can use the same run name."""

    def test_create_run_cross_client_same_name_allowed(
        self, client: TestClient, auth_headers, experiment_template, db_session
    ):
        """
        Run names are unique per-client, not globally. Two separate clients
        must be able to create runs with identical names without a 409.
        """
        from app.core.security import get_password_hash
        from models.user import User, Role
        from models.client import Client

        shared_name = f"SharedRun {uuid4().hex[:8]}"

        # Create a second client and a user belonging to it
        client2 = Client(name=f"Client {uuid4().hex[:8]}", created_by=None, modified_by=None)
        db_session.add(client2)
        db_session.flush()

        role2 = Role(
            name=f"admin_{uuid4().hex[:4]}",
            description="Test role for client2",
            created_by=None,
            modified_by=None,
        )
        db_session.add(role2)
        db_session.flush()

        # Grant experiment:manage to role2
        perm = db_session.query(
            __import__("models.user", fromlist=["Permission"]).Permission
        ).filter_by(name="experiment:manage").first()
        if perm:
            role2.permissions.append(perm)

        user2_username = f"user2_{uuid4().hex[:6]}"
        user2_email = f"user2_{uuid4().hex[:6]}@test.com"
        user2 = User(
            name=user2_username,
            username=user2_username,
            email=user2_email,
            password_hash=get_password_hash("password2"),
            client_id=client2.id,
            role_id=role2.id,
            created_by=None,
            modified_by=None,
        )
        db_session.add(user2)
        db_session.flush()

        # Login as user2
        r2 = client.post(
            "/auth/login",
            json={"username": user2.username, "password": "password2"},
        )
        assert r2.status_code == 200, r2.text
        headers2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        # user2 needs their own template
        tmpl_payload = {
            "name": f"Template2 {uuid4().hex[:8]}",
            "description": "cross-client template",
            "template_definition": VALID_TEMPLATE_DEF,
        }
        r_tmpl = client.post("/v1/experiment-templates", json=tmpl_payload, headers=headers2)
        assert r_tmpl.status_code == 201, r_tmpl.text
        template2_id = r_tmpl.json()["id"]

        # Client 1 creates run with shared_name
        r1 = client.post(
            "/v1/experiment-runs",
            json={
                "name": shared_name,
                "experiment_template_id": experiment_template,
            },
            headers=auth_headers,
        )
        assert r1.status_code == 201, r1.text

        # Client 2 creates run with the same shared_name — must succeed
        r2_run = client.post(
            "/v1/experiment-runs",
            json={
                "name": shared_name,
                "experiment_template_id": template2_id,
            },
            headers=headers2,
        )
        assert r2_run.status_code == 201, (
            f"Expected 201 for cross-client duplicate name, got {r2_run.status_code}: {r2_run.text}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# ExperimentProcess CRUD
# ──────────────────────────────────────────────────────────────────────────────

class TestExperimentProcess:
    def test_create_process_no_steps(self, client, auth_headers, draft_run):
        run_id = draft_run["id"]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/processes",
            json={"name": "Empty Process", "sort_order": 1},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Empty Process"
        assert body["sort_order"] == 1
        assert body["steps"] == []
        assert body["experiment_run_id"] == run_id

    def test_create_process_with_inline_steps(self, client, auth_headers, draft_run):
        run_id = draft_run["id"]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/processes",
            json={
                "name": "Process With Steps",
                "sort_order": 0,
                "steps": [
                    {"name": "Step A", "sort_order": 0},
                    {"name": "Step B", "sort_order": 1},
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Process With Steps"
        assert len(body["steps"]) == 2
        step_names = {s["name"] for s in body["steps"]}
        assert step_names == {"Step A", "Step B"}
        # All inline steps start as queued
        for s in body["steps"]:
            assert s["status"] == "queued"

    def test_list_processes_for_run(self, client, auth_headers, draft_run):
        run_id = draft_run["id"]
        # Create two processes
        for i in range(2):
            client.post(
                f"/v1/experiment-runs/{run_id}/processes",
                json={"name": f"Process {i}", "sort_order": i},
                headers=auth_headers,
            )
        r = client.get(f"/v1/experiment-runs/{run_id}/processes", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert len(r.json()) >= 2

    def test_get_process_by_id(self, client, auth_headers, process):
        process_id = process["id"]
        r = client.get(f"/v1/processes/{process_id}", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == process_id

    def test_get_process_unknown_id_returns_404(self, client, auth_headers):
        r = client.get(f"/v1/processes/{uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    def test_delete_process(self, client, auth_headers, process):
        process_id = process["id"]
        r = client.delete(f"/v1/processes/{process_id}", headers=auth_headers)
        assert r.status_code == 204

        # Confirm gone
        r2 = client.get(f"/v1/processes/{process_id}", headers=auth_headers)
        assert r2.status_code == 404

    def test_create_process_unknown_run_returns_404(self, client, auth_headers):
        r = client.post(
            f"/v1/experiment-runs/{uuid4()}/processes",
            json={"name": "Ghost Process", "sort_order": 0},
            headers=auth_headers,
        )
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# ProcessStep CRUD
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessStep:
    def test_create_step(self, client, auth_headers, process):
        process_id = process["id"]
        r = client.post(
            f"/v1/processes/{process_id}/steps",
            json={"name": "Vortex", "description": "mix well", "sort_order": 0},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Vortex"
        assert body["status"] == "queued"
        assert body["started_at"] is None
        assert body["completed_at"] is None
        assert body["failed_at"] is None

    def test_list_steps_for_process(self, client, auth_headers, process):
        process_id = process["id"]
        for i in range(3):
            client.post(
                f"/v1/processes/{process_id}/steps",
                json={"name": f"Step {i}", "sort_order": i},
                headers=auth_headers,
            )
        r = client.get(f"/v1/processes/{process_id}/steps", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert len(r.json()) >= 3

    def test_get_step_by_id(self, client, auth_headers, step):
        step_id = step["id"]
        r = client.get(f"/v1/process-steps/{step_id}", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == step_id

    def test_get_step_unknown_id_returns_404(self, client, auth_headers):
        r = client.get(f"/v1/process-steps/{uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    def test_create_step_unknown_process_returns_404(self, client, auth_headers):
        r = client.post(
            f"/v1/processes/{uuid4()}/steps",
            json={"name": "Ghost Step", "sort_order": 0},
            headers=auth_headers,
        )
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# ProcessStep state machine
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessStepTransitions:
    """
    State machine:
        queued ──► in_process ──► complete  (terminal)
           └──────────────────► failed     (terminal)
    """

    def test_full_happy_path_queued_to_complete(self, client, auth_headers, step):
        step_id = step["id"]

        # queued → in_process
        r = client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "in_process"
        assert body["started_at"] is not None
        assert body["completed_at"] is None
        assert body["failed_at"] is None

        # in_process → complete
        r = client.post(f"/v1/process-steps/{step_id}/complete", headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "complete"
        assert body["started_at"] is not None
        assert body["completed_at"] is not None
        assert body["failed_at"] is None

    def test_queued_to_failed_direct(self, client, auth_headers, step):
        """queued → failed is a valid direct transition."""
        step_id = step["id"]
        r = client.post(f"/v1/process-steps/{step_id}/fail", headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "failed"
        assert body["failed_at"] is not None
        assert body["started_at"] is None
        assert body["completed_at"] is None

    def test_in_process_to_failed(self, client, auth_headers, step):
        """in_process → failed is valid."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        r = client.post(f"/v1/process-steps/{step_id}/fail", headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "failed"
        assert body["started_at"] is not None
        assert body["failed_at"] is not None

    def test_invalid_transition_queued_to_complete_returns_400(self, client, auth_headers, step):
        """Cannot skip in_process — queued → complete is invalid."""
        step_id = step["id"]
        r = client.post(f"/v1/process-steps/{step_id}/complete", headers=auth_headers)
        assert r.status_code == 400, r.text
        assert "queued" in r.json()["detail"].lower()

    def test_complete_is_terminal_no_further_transitions(self, client, auth_headers, step):
        """complete → anything must return 400."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        client.post(f"/v1/process-steps/{step_id}/complete", headers=auth_headers)

        r = client.post(f"/v1/process-steps/{step_id}/fail", headers=auth_headers)
        assert r.status_code == 400, r.text
        assert "complete" in r.json()["detail"].lower()

    def test_failed_is_terminal_no_further_transitions(self, client, auth_headers, step):
        """failed → anything must return 400."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/fail", headers=auth_headers)

        r = client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        assert r.status_code == 400, r.text
        assert "failed" in r.json()["detail"].lower()

    def test_in_process_cannot_restart(self, client, auth_headers, step):
        """in_process → in_process is invalid (not in transition map)."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        r = client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        assert r.status_code == 400, r.text

    def test_started_at_only_set_on_in_process_transition(self, client, auth_headers, process):
        """started_at is None until step reaches in_process."""
        process_id = process["id"]
        r = client.post(
            f"/v1/processes/{process_id}/steps",
            json={"name": "Timestamp Step", "sort_order": 0},
            headers=auth_headers,
        )
        step_id = r.json()["id"]

        # Initially null
        r = client.get(f"/v1/process-steps/{step_id}", headers=auth_headers)
        assert r.json()["started_at"] is None

        # After start
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        r = client.get(f"/v1/process-steps/{step_id}", headers=auth_headers)
        body = r.json()
        assert body["started_at"] is not None
        assert body["completed_at"] is None
        assert body["failed_at"] is None


# ──────────────────────────────────────────────────────────────────────────────
# ProcessStep notes
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessStepNotes:
    def test_update_notes_on_queued_step(self, client, auth_headers, step):
        step_id = step["id"]
        r = client.patch(
            f"/v1/process-steps/{step_id}/notes",
            json={"notes": "Sample was cloudy, noted for review."},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["notes"] == "Sample was cloudy, noted for review."

    def test_update_notes_on_in_process_step(self, client, auth_headers, step):
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        r = client.patch(
            f"/v1/process-steps/{step_id}/notes",
            json={"notes": "Mid-process observation."},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["notes"] == "Mid-process observation."

    def test_update_notes_on_complete_step(self, client, auth_headers, step):
        """Notes must be updatable even after step is complete (terminal)."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/start", headers=auth_headers)
        client.post(f"/v1/process-steps/{step_id}/complete", headers=auth_headers)
        r = client.patch(
            f"/v1/process-steps/{step_id}/notes",
            json={"notes": "All good, completed cleanly."},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["notes"] == "All good, completed cleanly."

    def test_update_notes_on_failed_step(self, client, auth_headers, step):
        """Notes must be updatable even after step fails (terminal)."""
        step_id = step["id"]
        client.post(f"/v1/process-steps/{step_id}/fail", headers=auth_headers)
        r = client.patch(
            f"/v1/process-steps/{step_id}/notes",
            json={"notes": "Equipment failure. Restart required."},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["notes"] == "Equipment failure. Restart required."

    def test_notes_unknown_step_returns_404(self, client, auth_headers):
        r = client.patch(
            f"/v1/process-steps/{uuid4()}/notes",
            json={"notes": "ghost note"},
            headers=auth_headers,
        )
        assert r.status_code == 404
