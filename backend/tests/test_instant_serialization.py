"""Instant fields leave the API with a UTC offset. Calendar dates do not."""
import re
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.schemas.flexible_experiment import LimsRunRead
from app.schemas.sample import SampleResponse
from models.flexible_experiment import LimsRunStatus

_OFFSET = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")
_WHEN = datetime(2026, 10, 18, 23, 23, 0)


def _lims_run(created_at: datetime) -> LimsRunRead:
    return LimsRunRead.model_construct(
        id=uuid4(),
        name="R-1",
        description=None,
        experiment_template_id=None,
        analysis_id=None,
        status=LimsRunStatus.draft,
        cohort={"sample_ids": [], "locked_at": "2026-10-18T23:23:00+00:00"},
        started_at=None,
        completed_at=None,
        published_at=None,
        canceled_at=None,
        created_at=created_at,
        created_by=None,
        modified_at=created_at,
        lifecycle_type=None,
    )


def test_lims_run_json_stamps_naive_utc_and_keeps_python_datetimes():
    run = _lims_run(_WHEN)
    data = run.model_dump(mode="json")
    assert data["created_at"] == "2026-10-18T23:23:00Z"
    assert data["modified_at"] == "2026-10-18T23:23:00Z"
    assert data["started_at"] is None
    assert data["completed_at"] is None
    assert data["published_at"] is None
    assert data["canceled_at"] is None
    assert data["cohort"]["locked_at"] == "2026-10-18T23:23:00Z"
    python_value = run.model_dump()
    assert isinstance(python_value["created_at"], datetime)
    assert python_value["created_at"] == _WHEN


def test_aware_instant_serializes_as_utc_z():
    aware = datetime(2026, 10, 18, 23, 23, tzinfo=timezone.utc)
    data = _lims_run(aware).model_dump(mode="json")
    assert data["created_at"] == "2026-10-18T23:23:00Z"


def test_sample_calendar_dates_do_not_gain_an_offset():
    uid = uuid4()
    sample = SampleResponse.model_construct(
        name="S-1",
        description=None,
        received_date=date(2026, 10, 18),
        report_date=None,
        due_date=date(2026, 10, 25),
        date_sampled=None,
        sample_type=uid,
        status=uid,
        matrix=None,
        temperature=None,
        parent_sample_id=None,
        client_id=None,
        client_project_id=None,
        project_id=None,
        qc_type=None,
        client_sample_id=None,
        custom_attributes={"created_at": "2026-10-18T00:00:00"},
        id=uid,
        active=True,
        created_at=_WHEN,
        created_by=uid,
        modified_at=_WHEN,
        modified_by=uid,
        extra_fields={"modified_at": "2026-10-18T00:00:00"},
    )
    data = sample.model_dump(mode="json")
    assert data["created_at"] == "2026-10-18T23:23:00Z"
    assert data["modified_at"] == "2026-10-18T23:23:00Z"
    assert data["received_date"] == "2026-10-18"
    assert data["due_date"] == "2026-10-25"
    assert data["report_date"] is None
    assert _OFFSET.search(data["received_date"]) is None
    assert _OFFSET.search(data["due_date"]) is None
    assert data["custom_attributes"]["created_at"] == "2026-10-18T00:00:00"
    assert data["extra_fields"]["modified_at"] == "2026-10-18T00:00:00"


def test_users_api_emits_offset_aware_timestamps(client: TestClient, test_admin_user):
    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "adminpassword"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) >= 1
    saw_created = False
    for row in rows:
        created_at = row["created_at"]
        modified_at = row["modified_at"]
        assert isinstance(created_at, str)
        assert isinstance(modified_at, str)
        assert _OFFSET.search(created_at) is not None
        assert _OFFSET.search(modified_at) is not None
        saw_created = True
        if row["last_login"] is not None:
            assert _OFFSET.search(row["last_login"]) is not None
        role = row["role"]
        if role is not None:
            assert _OFFSET.search(role["created_at"]) is not None
            assert _OFFSET.search(role["modified_at"]) is not None
    assert saw_created is True
