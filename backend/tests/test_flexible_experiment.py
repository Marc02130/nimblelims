"""
Pytest tests for the Flexible Experiment Engine:
  - ExperimentRun lifecycle (draft → running → complete → published)
  - Status transition guards (invalid transitions → 400)
  - Instrument data import (happy path + error paths)
  - Robot worklist export
  - SOP parse job creation and background task (mocked Anthropic API)
"""
import io
import json
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import anthropic
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from models.flexible_experiment import (
    ExperimentRun,
    ExperimentRunStatus,
    InstrumentParser,
    RobotWorklistConfig,
)
from models.user import User, Role, Permission, RolePermission


# ──────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ──────────────────────────────────────────────────────────────────────────────

VALID_TEMPLATE_DEF = {
    "experiment_name": "Cell Viability",
    "description": "Live/dead cell count",
    "protocol_steps": ["seed plates", "add reagent", "read plate"],
    "plate_layout": {
        "plate_type": "96",
        "wells": {"A1": {"condition": "sample", "role": "unknown"}},
    },
    "transfer_steps": [
        {
            "step": 1,
            "source_plate": "stock",
            "source_well": "A1",
            "dest_plate": "assay",
            "dest_well": "A1",
            "volume_ul": 10.0,
            "mandatory_review": True,
        }
    ],
    "result_columns": [
        {"name": "viability_pct", "data_type": "float", "unit": "%"}
    ],
    "acceptance_criteria": "viability > 80%",
    "mandatory_review_count": 0,
}

VALID_PARSER_CONFIG = {
    "columns": [
        {"source_col": "Viability", "field_name": "viability_pct", "data_type": "float", "unit": "%"},
        {"source_col": "Well", "field_name": "well", "data_type": "string", "unit": None},
    ],
    "well_col": "Well",
    "skip_rows": 0,
}

VALID_WORKLIST_CONFIG = {
    "steps": [
        {
            "step": 1,
            "source_plate": "stock",
            "source_well_col": "source_well",
            "dest_plate": "assay",
            "dest_well_col": "dest_well",
            "volume_col": "volume",
            "mandatory_review": True,
        }
    ]
}

INSTRUMENT_CSV = (
    "Well,Viability\n"
    "A1,92.3\n"
    "A2,85.1\n"
    "A3,78.4\n"
)

MOCK_EXTRACTION_RESULT = {
    "template_definition": VALID_TEMPLATE_DEF,
    "parser_config": VALID_PARSER_CONFIG,
    "worklist_config": VALID_WORKLIST_CONFIG,
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    """Login as the seeded admin user and return bearer headers."""
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def experiment_template(client: TestClient, auth_headers):
    """Create a minimal ExperimentTemplate and return its id."""
    payload = {
        "name": f"Template {uuid4().hex[:8]}",
        "description": "test template",
        "template_definition": VALID_TEMPLATE_DEF,
    }
    r = client.post("/v1/experiment-templates", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def draft_run(client: TestClient, auth_headers, experiment_template):
    """Create a run in draft status and return its full JSON."""
    payload = {
        "name": f"Run {uuid4().hex[:8]}",
        "experiment_template_id": experiment_template,
        "description": "test run",
    }
    r = client.post("/v1/experiment-runs", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def running_run(client: TestClient, auth_headers, draft_run):
    """Advance a draft run to running status."""
    run_id = draft_run["id"]
    r = client.patch(f"/v1/experiment-runs/{run_id}/start", headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def template_with_parser(db_session: Session, experiment_template, auth_headers, client):
    """Attach an InstrumentParser to the template and return the template id."""
    from models.flexible_experiment import InstrumentParser as IP
    parser = IP(
        experiment_template_id=experiment_template,
        name="Plate Reader Parser",
        parser_config=VALID_PARSER_CONFIG,
        created_by=None,
        modified_by=None,
    )
    db_session.add(parser)
    db_session.flush()
    return experiment_template


@pytest.fixture
def template_with_parser_and_worklist(db_session: Session, template_with_parser):
    """Attach both parser and worklist config to the template."""
    from models.flexible_experiment import RobotWorklistConfig as RWC
    wl = RWC(
        experiment_template_id=template_with_parser,
        name="Robot Worklist",
        worklist_config=VALID_WORKLIST_CONFIG,
        created_by=None,
        modified_by=None,
    )
    db_session.add(wl)
    db_session.flush()
    return template_with_parser


# ──────────────────────────────────────────────────────────────────────────────
# 1. ExperimentRun CRUD
# ──────────────────────────────────────────────────────────────────────────────

class TestExperimentRunCreate:
    def test_create_run_returns_draft(self, client, auth_headers, experiment_template):
        payload = {
            "name": f"Run {uuid4().hex[:8]}",
            "experiment_template_id": experiment_template,
        }
        r = client.post("/v1/experiment-runs", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "draft"
        assert data["started_at"] is None

    def test_create_run_duplicate_name_returns_400(self, client, auth_headers, draft_run):
        payload = {
            "name": draft_run["name"],
            "experiment_template_id": draft_run["experiment_template_id"],
        }
        r = client.post("/v1/experiment-runs", json=payload, headers=auth_headers)
        assert r.status_code == 400
        assert "already exists" in r.json()["detail"]

    def test_list_runs_returns_created(self, client, auth_headers, draft_run):
        r = client.get("/v1/experiment-runs", headers=auth_headers)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()["runs"]]
        assert draft_run["id"] in ids

    def test_list_runs_filter_by_status(self, client, auth_headers, draft_run):
        r = client.get("/v1/experiment-runs?status=draft", headers=auth_headers)
        assert r.status_code == 200
        for run in r.json()["runs"]:
            assert run["status"] == "draft"

    def test_get_run_by_id(self, client, auth_headers, draft_run):
        r = client.get(f"/v1/experiment-runs/{draft_run['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == draft_run["id"]

    def test_get_run_not_found(self, client, auth_headers):
        r = client.get(f"/v1/experiment-runs/{uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    def test_unauthenticated_request_rejected(self, client, experiment_template):
        r = client.post(
            "/v1/experiment-runs",
            json={"name": "X", "experiment_template_id": experiment_template},
        )
        assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# 2. Status transitions
# ──────────────────────────────────────────────────────────────────────────────

class TestStatusTransitions:
    def test_draft_to_running_sets_started_at(self, client, auth_headers, draft_run):
        r = client.patch(f"/v1/experiment-runs/{draft_run['id']}/start", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None

    def test_running_to_complete_via_review(self, client, auth_headers, running_run):
        r = client.patch(f"/v1/experiment-runs/{running_run['id']}/review", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "complete"

    def test_complete_to_published(self, client, auth_headers, running_run):
        run_id = running_run["id"]
        r = client.patch(f"/v1/experiment-runs/{run_id}/review", headers=auth_headers)
        assert r.status_code == 200
        r = client.patch(f"/v1/experiment-runs/{run_id}/complete", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    def test_invalid_transition_draft_to_complete(self, client, auth_headers, draft_run):
        """draft → complete is not a valid transition; must go through running."""
        r = client.patch(f"/v1/experiment-runs/{draft_run['id']}/review", headers=auth_headers)
        assert r.status_code == 400
        assert "Cannot transition" in r.json()["detail"]

    def test_invalid_transition_running_to_published(self, client, auth_headers, running_run):
        """running → published skips the required 'complete' state."""
        r = client.patch(f"/v1/experiment-runs/{running_run['id']}/complete", headers=auth_headers)
        assert r.status_code == 400

    def test_invalid_transition_complete_to_running(self, client, auth_headers, running_run):
        """complete → running (restart) is not allowed."""
        run_id = running_run["id"]
        r = client.patch(f"/v1/experiment-runs/{run_id}/review", headers=auth_headers)
        assert r.status_code == 200
        r = client.patch(f"/v1/experiment-runs/{run_id}/start", headers=auth_headers)
        assert r.status_code == 400


# ──────────────────────────────────────────────────────────────────────────────
# 3. Instrument data import
# ──────────────────────────────────────────────────────────────────────────────

class TestInstrumentImport:
    def test_import_happy_path(self, client, auth_headers, running_run,
                                template_with_parser, db_session):
        """Import valid rows to a running run → rows persisted, counts returned."""
        run_id = running_run["id"]
        rows = [
            {"well_position": "A1", "row_data": {"viability_pct": 92.3, "well": "A1"}},
            {"well_position": "A2", "row_data": {"viability_pct": 85.1, "well": "A2"}},
        ]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0
        assert len(data["rows"]) == 2

    def test_import_to_draft_run_returns_400(self, client, auth_headers, draft_run,
                                               template_with_parser):
        """Import to a draft run is rejected."""
        run_id = draft_run["id"]
        rows = [{"well_position": "A1", "row_data": {"viability_pct": 90.0, "well": "A1"}}]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "running" in r.json()["detail"]

    def test_import_without_parser_config_returns_400(self, client, auth_headers, running_run):
        """Template with no InstrumentParser → import is rejected."""
        run_id = running_run["id"]
        rows = [{"well_position": "A1", "row_data": {"foo": "bar"}}]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "no instrument parser" in r.json()["detail"].lower()

    def test_import_missing_expected_columns_returns_422(self, client, auth_headers,
                                                          running_run, template_with_parser):
        """Row data missing a parser_config field_name → 422."""
        run_id = running_run["id"]
        rows = [{"well_position": "A1", "row_data": {"wrong_field": 1.0}}]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_get_data_rows_after_import(self, client, auth_headers, running_run,
                                         template_with_parser):
        """GET /data returns imported rows."""
        run_id = running_run["id"]
        rows = [{"well_position": "A1", "row_data": {"viability_pct": 88.0, "well": "A1"}}]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 200

        r = client.get(f"/v1/experiment-runs/{run_id}/data", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["row_data"]["viability_pct"] == 88.0


# ──────────────────────────────────────────────────────────────────────────────
# 4. Worklist export
# ──────────────────────────────────────────────────────────────────────────────

class TestWorklistExport:
    def _import_rows(self, client, auth_headers, run_id):
        rows = [
            {"well_position": "A1", "row_data": {
                "viability_pct": 92.3, "well": "A1",
                "source_well": "A1", "dest_well": "B1", "volume": 10,
            }},
        ]
        r = client.post(
            f"/v1/experiment-runs/{run_id}/import",
            json={"rows": rows},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_worklist_csv_columns(self, client, auth_headers, running_run,
                                   template_with_parser_and_worklist, db_session):
        run_id = running_run["id"]
        self._import_rows(client, auth_headers, run_id)
        r = client.get(f"/v1/experiment-runs/{run_id}/worklist", headers=auth_headers)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        lines = r.text.strip().splitlines()
        assert lines[0] == "source_well,dest_well,volume"
        assert len(lines) == 2  # header + 1 data row

    def test_worklist_no_config_returns_400(self, client, auth_headers, running_run,
                                             template_with_parser):
        """Template with no worklist config → 400."""
        run_id = running_run["id"]
        r = client.get(f"/v1/experiment-runs/{run_id}/worklist", headers=auth_headers)
        assert r.status_code == 400
        assert "no robot worklist config" in r.json()["detail"].lower()

    def test_worklist_empty_run_returns_header_only(self, client, auth_headers, running_run,
                                                      template_with_parser_and_worklist):
        """Running run with no imported data → CSV with headers only, not 500."""
        run_id = running_run["id"]
        r = client.get(f"/v1/experiment-runs/{run_id}/worklist", headers=auth_headers)
        assert r.status_code == 200
        assert r.text.strip() == "source_well,dest_well,volume"

    def test_worklist_blocked_by_mandatory_review(self, client, auth_headers,
                                                   running_run, db_session,
                                                   template_with_parser_and_worklist):
        """mandatory_review_count > 0 on template → worklist export blocked with 400."""
        from models.experiment import ExperimentTemplate

        tmpl = db_session.query(ExperimentTemplate).filter(
            ExperimentTemplate.id == template_with_parser_and_worklist
        ).first()
        assert tmpl is not None, "Template not found"

        tmpl.template_definition = {**VALID_TEMPLATE_DEF, "mandatory_review_count": 1}
        db_session.flush()

        run_id = running_run["id"]
        r = client.get(f"/v1/experiment-runs/{run_id}/worklist", headers=auth_headers)
        assert r.status_code == 400
        assert "mandatory" in r.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# 5. SOP Parse Jobs
# ──────────────────────────────────────────────────────────────────────────────

MOCK_SOP_TEXT = "Standard Operating Procedure: Cell Viability Assay..."
MOCK_INSTRUMENT_TEXT = "Well,Viability\nA1,92.3\n"


def _make_mock_anthropic_response(result_dict: dict):
    """Return a mock anthropic Message with the given dict as JSON text."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps(result_dict)
    return mock_msg


class TestSopParseJobs:
    def _upload(self, client, auth_headers, sop_text=MOCK_SOP_TEXT,
                instrument_text=MOCK_INSTRUMENT_TEXT):
        sop_bytes = sop_text.encode()
        instrument_bytes = instrument_text.encode()
        r = client.post(
            "/v1/sop-parse",
            files={
                "sop_file": ("sop.txt", io.BytesIO(sop_bytes), "text/plain"),
                "instrument_file": ("instrument.csv", io.BytesIO(instrument_bytes), "text/csv"),
            },
            headers=auth_headers,
        )
        return r

    def test_create_job_returns_202_pending(self, client, auth_headers):
        r = self._upload(client, auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "pending"
        assert "id" in data

    def test_get_job_by_id(self, client, auth_headers):
        r = self._upload(client, auth_headers)
        assert r.status_code == 202
        job_id = r.json()["id"]

        r2 = client.get(f"/v1/sop-parse/{job_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == job_id

    def test_get_job_not_found(self, client, auth_headers):
        r = client.get(f"/v1/sop-parse/{uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    def _make_session_factory(self, db_engine):
        """Return a SessionLocal-compatible callable backed by the test engine."""
        from sqlalchemy.orm import sessionmaker
        return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _seed_job(self, db_engine):
        """Create and commit a SopParseJob; return its id."""
        from app.repositories.flexible_experiment_repository import SopParseJobRepository

        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            repo = SopParseJobRepository(db)
            job = repo.create(
                sop_filename="sop.txt",
                instrument_filename="instrument.csv",
                created_by=None,
            )
            db.flush()
            db.refresh(job)
            job_id = job.id
            db.commit()
        finally:
            db.close()
        return job_id

    def test_background_task_happy_path(self, db_engine):
        """Background extraction succeeds → job status=complete with result."""
        from app.services.sop_parse_service import SOPParseService

        mock_response = _make_mock_anthropic_response(MOCK_EXTRACTION_RESULT)
        job_id = self._seed_job(db_engine)
        SessionFactory = self._make_session_factory(db_engine)

        with patch("app.database.SessionLocal", SessionFactory), \
             patch("anthropic.Anthropic") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.messages.create.return_value = mock_response
            mock_cls.return_value = mock_instance

            SOPParseService.run_extraction_background(
                job_id=job_id,
                sop_text=MOCK_SOP_TEXT,
                instrument_text=MOCK_INSTRUMENT_TEXT,
            )

        # Re-read from DB after task completion
        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            from app.repositories.flexible_experiment_repository import SopParseJobRepository
            completed = SopParseJobRepository(db).get_by_id(job_id)
            assert completed.status.value == "complete"
            assert completed.result is not None
            assert "template_definition" in completed.result
        finally:
            db.close()

    def test_background_task_anthropic_api_error(self, db_engine):
        """Anthropic APIError → job status=failed with error_message."""
        from app.services.sop_parse_service import SOPParseService

        job_id = self._seed_job(db_engine)
        SessionFactory = self._make_session_factory(db_engine)

        # Construct an APIError via its documented subclass interface
        class _FakeAPIError(anthropic.APIError):
            def __init__(self):
                pass  # skip super().__init__ to avoid complex constructor
            message = "rate limit exceeded"

        with patch("app.database.SessionLocal", SessionFactory), \
             patch("anthropic.Anthropic") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.messages.create.side_effect = _FakeAPIError()
            mock_cls.return_value = mock_instance

            SOPParseService.run_extraction_background(
                job_id=job_id,
                sop_text=MOCK_SOP_TEXT,
                instrument_text=MOCK_INSTRUMENT_TEXT,
            )

        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            from app.repositories.flexible_experiment_repository import SopParseJobRepository
            failed = SopParseJobRepository(db).get_by_id(job_id)
            assert failed.status.value == "failed"
            assert failed.error_message is not None
            assert "Anthropic API error" in failed.error_message
        finally:
            db.close()

    def test_background_task_malformed_json(self, db_engine):
        """Claude returns malformed JSON → job status=failed."""
        from app.services.sop_parse_service import SOPParseService

        job_id = self._seed_job(db_engine)
        SessionFactory = self._make_session_factory(db_engine)

        bad_response = MagicMock()
        bad_response.content = [MagicMock()]
        bad_response.content[0].text = "This is definitely not JSON }{{"

        with patch("app.database.SessionLocal", SessionFactory), \
             patch("anthropic.Anthropic") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.messages.create.return_value = bad_response
            mock_cls.return_value = mock_instance

            SOPParseService.run_extraction_background(
                job_id=job_id,
                sop_text=MOCK_SOP_TEXT,
                instrument_text=MOCK_INSTRUMENT_TEXT,
            )

        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            from app.repositories.flexible_experiment_repository import SopParseJobRepository
            failed = SopParseJobRepository(db).get_by_id(job_id)
            assert failed.status.value == "failed"
            assert "malformed JSON" in failed.error_message
        finally:
            db.close()


# ──────────────────────────────────────────────────────────────────────────────
# 6. SOP Parse Apply
# ──────────────────────────────────────────────────────────────────────────────

class TestSopApplyJob:
    """Tests for POST /v1/sop-parse/{id}/apply."""

    def _make_session_factory(self, db_engine):
        from sqlalchemy.orm import sessionmaker
        return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _seed_complete_job(self, db_engine, result: dict = None) -> "uuid.UUID":
        """Seed a complete SopParseJob with a given result dict."""
        from app.repositories.flexible_experiment_repository import SopParseJobRepository
        from models.flexible_experiment import SopParseJobStatus

        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            repo = SopParseJobRepository(db)
            job = repo.create(
                sop_filename="sop.txt",
                instrument_filename="instrument.csv",
                created_by=None,
            )
            db.flush()
            result = result if result is not None else MOCK_EXTRACTION_RESULT
            repo.mark_complete(job, result)
            db.flush()
            db.refresh(job)
            job_id = job.id
            db.commit()
        finally:
            db.close()
        return job_id

    def test_apply_creates_template_parser_worklist(self, client, auth_headers, db_engine):
        """Happy path: complete job → 201, creates template + parser + worklist."""
        job_id = self._seed_complete_job(db_engine)

        r = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r.status_code == 201, r.text
        data = r.json()

        assert data["job_id"] == str(job_id)
        assert data["experiment_template_id"] is not None
        assert data["instrument_parser_id"] is not None
        assert data["robot_worklist_config_id"] is not None

    def test_apply_no_worklist_steps_skips_worklist_record(self, client, auth_headers, db_engine):
        """When worklist_config has no steps, robot_worklist_config_id is null."""
        result_no_worklist = {
            "template_definition": VALID_TEMPLATE_DEF,
            "parser_config": VALID_PARSER_CONFIG,
            "worklist_config": {"steps": []},
        }
        job_id = self._seed_complete_job(db_engine, result=result_no_worklist)

        r = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r.status_code == 201, r.text
        assert r.json()["robot_worklist_config_id"] is None

    def test_apply_links_job_to_template(self, client, auth_headers, db_engine):
        """After apply, the job's experiment_template_id FK is set."""
        job_id = self._seed_complete_job(db_engine)
        r = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r.status_code == 201
        template_id = r.json()["experiment_template_id"]

        # Verify via GET that job now references the template
        r2 = client.get(f"/v1/sop-parse/{job_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["experiment_template_id"] == template_id

    def test_apply_idempotency_returns_409(self, client, auth_headers, db_engine):
        """Applying same job twice → 409 Conflict on second call."""
        job_id = self._seed_complete_job(db_engine)
        r1 = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r1.status_code == 201

        r2 = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r2.status_code == 409
        assert "already been applied" in r2.json()["detail"].lower()

    def test_apply_pending_job_returns_422(self, client, auth_headers, db_engine):
        """Applying a job that's still pending → 422."""
        from app.repositories.flexible_experiment_repository import SopParseJobRepository
        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            repo = SopParseJobRepository(db)
            job = repo.create(sop_filename="x.txt", instrument_filename="y.csv", created_by=None)
            db.flush()
            db.refresh(job)
            job_id = job.id
            db.commit()
        finally:
            db.close()

        r = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r.status_code == 422
        assert "complete" in r.json()["detail"].lower()

    def test_apply_failed_job_returns_422(self, client, auth_headers, db_engine):
        """Applying a failed job → 422."""
        from app.repositories.flexible_experiment_repository import SopParseJobRepository
        Session = self._make_session_factory(db_engine)
        db = Session()
        try:
            repo = SopParseJobRepository(db)
            job = repo.create(sop_filename="x.txt", instrument_filename="y.csv", created_by=None)
            db.flush()
            repo.mark_failed(job, "extraction failed")
            db.flush()
            db.refresh(job)
            job_id = job.id
            db.commit()
        finally:
            db.close()

        r = client.post(f"/v1/sop-parse/{job_id}/apply", headers=auth_headers)
        assert r.status_code == 422

    def test_apply_not_found_returns_404(self, client, auth_headers):
        """Applying a non-existent job → 404."""
        r = client.post(f"/v1/sop-parse/{uuid4()}/apply", headers=auth_headers)
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# 7. InstrumentDataService unit tests
# ──────────────────────────────────────────────────────────────────────────────

class TestInstrumentDataService:
    def _make_service(self):
        from app.services.instrument_data_service import InstrumentDataService
        return InstrumentDataService(VALID_PARSER_CONFIG)

    def test_parse_happy_path(self):
        svc = self._make_service()
        csv_bytes = INSTRUMENT_CSV.encode()
        rows, warnings = svc.parse(csv_bytes)
        assert len(rows) == 3
        assert rows[0].row_data["viability_pct"] == 92.3
        assert rows[0].well_position == "A1"
        assert warnings == []

    def test_parse_with_max_rows(self):
        svc = self._make_service()
        rows, _ = svc.parse(INSTRUMENT_CSV.encode(), max_rows=1)
        assert len(rows) == 1

    def test_parse_missing_column_raises_422(self):
        from fastapi import HTTPException
        bad_csv = "OtherCol\nfoo\n"
        svc = self._make_service()
        with pytest.raises(HTTPException) as exc:
            svc.parse(bad_csv.encode())
        assert exc.value.status_code == 422
        assert "missing expected columns" in exc.value.detail.lower()

    def test_parse_empty_after_skip_raises_422(self):
        from fastapi import HTTPException
        svc = self._make_service()
        with pytest.raises(HTTPException) as exc:
            svc.parse(b"")
        assert exc.value.status_code == 422

    def test_parse_coercion_warning_on_bad_float(self):
        svc = self._make_service()
        bad_csv = "Well,Viability\nA1,not_a_number\n"
        rows, warnings = svc.parse(bad_csv.encode())
        assert len(rows) == 1
        assert rows[0].row_data["viability_pct"] == "not_a_number"
        assert len(warnings) == 1
        assert "not_a_number" in warnings[0]

    def test_parse_skips_blank_rows(self):
        svc = self._make_service()
        csv_with_blanks = "Well,Viability\nA1,90.0\n\n\nA2,80.0\n"
        rows, _ = svc.parse(csv_with_blanks.encode())
        assert len(rows) == 2

    def test_parse_utf8_bom(self):
        """UTF-8 BOM prefix should be silently stripped."""
        svc = self._make_service()
        bom_csv = "\xef\xbb\xbfWell,Viability\nA1,92.3\n"
        rows, _ = svc.parse(bom_csv.encode("utf-8"))
        assert rows[0].well_position == "A1"
