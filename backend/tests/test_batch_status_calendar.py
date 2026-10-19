"""PATCH /batches/{id}/status writes a lab-day midnight from the status name."""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from sqlalchemy import text

from app.routers.batches import calendar_stamp_for_batch_status
from models.batch import Batch
from models.lab_setting import LAB_SETTINGS_ID, LabSetting
from models.list import List, ListEntry
from tests._fk_helpers import scratch_entry_id


@pytest.fixture
def auth_headers(client, test_admin_user):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _save_zone(db_session, name):
    row = db_session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        row = LabSetting(id=LAB_SETTINGS_ID, timezone=name)
        db_session.add(row)
    else:
        row.timezone = name
    db_session.commit()


def _entry(db_session, list_name, entry_name, user_id):
    parent = db_session.query(List).filter(List.name == list_name).first()
    if parent is None:
        parent = List(
            name=list_name,
            description=list_name,
            created_by=user_id,
            modified_by=user_id,
        )
        db_session.add(parent)
        db_session.flush()
    entry = ListEntry(
        name=entry_name,
        description=entry_name,
        list_id=parent.id,
        created_by=user_id,
        modified_by=user_id,
    )
    db_session.add(entry)
    db_session.flush()
    return entry


def _batch(db_session, user_id):
    batch = Batch(
        name=f"status-batch-{uuid4().hex[:8]}",
        description="status calendar",
        status=scratch_entry_id(db_session),
        created_by=user_id,
        modified_by=user_id,
    )
    db_session.add(batch)
    db_session.commit()
    return batch


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        # 03:30 UTC is 23:30 the previous evening in America/New_York.
        return datetime(2026, 10, 19, 3, 30, tzinfo=timezone.utc)

    @classmethod
    def utcnow(cls):
        return datetime(2026, 10, 19, 3, 30)


def test_status_name_writes_lab_day_midnight(
    client, db_session, test_admin_user, auth_headers, monkeypatch
):
    monkeypatch.setattr("app.routers.batches.datetime", _FrozenClock)
    # create_all copies BaseModel's unique name. Migration 0005's real rule
    # is unique per list, so In Process can exist on more than one list.
    db_session.execute(text("ALTER TABLE list_entries DROP CONSTRAINT IF EXISTS list_entries_name_key"))
    db_session.commit()
    _save_zone(db_session, "America/New_York")
    user_id = test_admin_user.id
    in_process = _entry(db_session, "batch_status", "In Process", user_id)
    completed = _entry(db_session, "batch_status", "Completed", user_id)
    created = _entry(db_session, "batch_status", "Created", user_id)
    decoy = _entry(db_session, "not_batch_status", "In Process", user_id)
    batch = _batch(db_session, user_id)

    assert calendar_stamp_for_batch_status(db_session, in_process) == "start"
    assert calendar_stamp_for_batch_status(db_session, completed) == "end"
    assert calendar_stamp_for_batch_status(db_session, created) is None
    assert calendar_stamp_for_batch_status(db_session, decoy) is None

    started = client.patch(
        f"/batches/{batch.id}/status",
        params={"status_id": str(in_process.id)},
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text
    db_session.refresh(batch)
    assert batch.start_date == date(2026, 10, 18)
    assert batch.end_date is None
    assert batch.status == in_process.id

    finished = client.patch(
        f"/batches/{batch.id}/status",
        params={"status_id": str(completed.id)},
        headers=auth_headers,
    )
    assert finished.status_code == 200, finished.text
    db_session.refresh(batch)
    assert batch.end_date == date(2026, 10, 18)
    assert batch.start_date == date(2026, 10, 18)

    other = _batch(db_session, user_id)
    decoy_response = client.patch(
        f"/batches/{other.id}/status",
        params={"status_id": str(decoy.id)},
        headers=auth_headers,
    )
    assert decoy_response.status_code == 200, decoy_response.text
    db_session.refresh(other)
    assert other.start_date is None
    assert other.end_date is None

    held = _batch(db_session, user_id)
    created_response = client.patch(
        f"/batches/{held.id}/status",
        params={"status_id": str(created.id)},
        headers=auth_headers,
    )
    assert created_response.status_code == 200, created_response.text
    db_session.refresh(held)
    assert held.start_date is None
    assert held.end_date is None
