"""Sample, test, and result future-date checks use the lab's calendar day.

Between 20:00 and 23:59 America/New_York the UTC date is already tomorrow.
A value on the lab's today is accepted. A value on the lab's tomorrow is refused.
At midnight in that zone the boundary moves.
"""
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.core import lab_time
from app.schemas.result import ResultCreate, ResultResponse, ResultUpdate
from app.schemas.sample import (
    BulkSampleAccessioningRequest,
    SampleAccessioningRequest,
    SampleCreate,
    SampleResponse,
    SampleUpdate,
)
from app.schemas.test import (
    TestAssignmentRequest,
    TestCreate,
    TestResponse,
    TestReviewRequest,
    TestStatusUpdateRequest,
    TestUpdate,
)
from app.schemas._dates import is_future
from models.lab_setting import LAB_SETTINGS_ID, LabSetting

UID = uuid4()


def _noon_utc(day: date) -> datetime:
    """Noon in America/New_York on ``day``, stored the way the API stores times."""
    local = datetime(day.year, day.month, day.day, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def _sample_create(when):
    return {"sample_type": UID, "status": UID, "received_date": when, "report_date": when}


def _sample_update(when):
    return {"received_date": when, "report_date": when}


def _sample_response(when):
    return {
        "id": UID,
        "active": True,
        "created_at": when,
        "created_by": UID,
        "modified_at": when,
        "modified_by": UID,
        **_sample_create(when),
    }


def _accession(when):
    return {
        "due_date": when,
        "received_date": when,
        "sample_type": UID,
        "matrix": UID,
        "client_id": UID,
    }


def _bulk(when):
    return {
        **_accession(when),
        "container_type_id": UID,
        "uniques": [{"container_name": "C-1", "name": "S-1"}],
    }


def _test_create(when):
    return {
        "name": "Assay",
        "sample_id": UID,
        "analysis_id": UID,
        "status": UID,
        "review_date": when,
        "test_date": when,
    }


def _test_response(when):
    return {
        "id": UID,
        "active": True,
        "created_at": when,
        "created_by": UID,
        "modified_at": when,
        "modified_by": UID,
        **_test_create(when),
    }


def _test_update(when):
    return {"review_date": when, "test_date": when}


def _assign(when):
    return {"sample_id": UID, "analysis_id": UID, "test_date": when}


def _status(when):
    return {"status": UID, "review_date": when, "test_date": when}


def _review(when):
    return {"review_date": when}


def _result(when):
    return {"test_id": UID, "analyte_id": UID, "entered_by": UID, "entry_date": when}


def _result_response(when):
    return {
        "id": UID,
        "active": True,
        "created_at": when,
        "modified_at": when,
        **_result(when),
    }


# Each class that checks a date, including response models that inherit the check.
_CASES = [
    (SampleCreate, _sample_create),
    (SampleUpdate, _sample_update),
    (SampleResponse, _sample_response),
    (SampleAccessioningRequest, _accession),
    (BulkSampleAccessioningRequest, _bulk),
    (TestCreate, _test_create),
    (TestUpdate, _test_update),
    (TestResponse, _test_response),
    (TestAssignmentRequest, _assign),
    (TestStatusUpdateRequest, _status),
    (TestReviewRequest, _review),
    (ResultCreate, _result),
    (ResultUpdate, _result),
    (ResultResponse, _result_response),
]


@pytest.mark.parametrize(
    "utc_moment, lab_day",
    [
        (datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), date(2026, 10, 18)),  # 20:00 ET
        (datetime(2026, 10, 19, 3, 59, tzinfo=timezone.utc), date(2026, 10, 18)),  # 23:59 ET
        (datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc), date(2026, 10, 19)),  # midnight ET
    ],
)
def test_each_validator_accepts_the_lab_today_and_refuses_tomorrow(utc_moment, lab_day, monkeypatch):
    monkeypatch.setattr(lab_time, "_utcnow", lambda: utc_moment)
    lab_time.remember_lab_zone("America/New_York")
    today = _noon_utc(lab_day)
    tomorrow = _noon_utc(lab_day + timedelta(days=1))
    # 22:00 ET on the lab's today is already the next UTC date during the evening window.
    same_evening = datetime(2026, 10, 19, 2, 0) if lab_day == date(2026, 10, 18) else today
    for model, build in _CASES:
        model(**build(today))
        model(**build(same_evening))
        with pytest.raises(ValidationError) as caught:
            model(**build(tomorrow))
        assert "future" in str(caught.value).lower(), model.__name__


def test_days_from_today_follows_the_lab_calendar(monkeypatch):
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 0, 30, tzinfo=timezone.utc)
    )
    # 22:00 ET on Oct 18, which is already Oct 19 in UTC. Still the lab's today.
    assert lab_time.days_from_today(datetime(2026, 10, 19, 2, 0), "America/New_York") == 0
    assert lab_time.days_from_today(datetime(2026, 10, 19, 16, 0), "America/New_York") == 1
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)
    )
    assert lab_time.days_from_today(datetime(2026, 10, 19, 16, 0), "America/New_York") == 0
    assert lab_time.days_from_today(datetime(2026, 10, 20, 16, 0), "America/New_York") == 1


def _login(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_a_request_publishes_the_saved_zone(client, test_admin_user, monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "UTC")
    headers = _login(client)
    saved = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "America/New_York"})
    assert saved.status_code == 200, saved.text
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 1, 0, tzinfo=timezone.utc)
    )
    again = client.get("/v1/lab-settings", headers=headers)
    assert again.status_code == 200, again.text
    assert is_future(date(2026, 10, 18)) is False
    assert is_future(date(2026, 10, 19)) is True
    SampleCreate(sample_type=UID, status=UID, received_date=datetime(2026, 10, 18, 22, 0))
    with pytest.raises(ValidationError):
        SampleCreate(sample_type=UID, status=UID, received_date=datetime(2026, 10, 19, 16, 0))


def test_corrupt_zone_reaches_validators_and_patch_repairs_it(client, db_session, test_admin_user, monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    db_session.add(LabSetting(id=LAB_SETTINGS_ID, timezone="Not/AZone"))
    db_session.flush()
    headers = _login(client)
    got = client.get("/v1/lab-settings", headers=headers)
    assert got.status_code == 503, got.text
    with pytest.raises(lab_time.LabTimezoneInvalid):
        is_future(date(2026, 10, 18))
    repaired = client.patch("/v1/lab-settings", headers=headers, json={"timezone": "America/Chicago"})
    assert repaired.status_code == 200, repaired.text
    assert is_future(date(2099, 1, 1)) is True
    assert is_future(date(2000, 1, 1)) is False
    assert is_future(None) is False
