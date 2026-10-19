"""Date-only inputs and stored midnights are lab calendar days.

``YYYY-MM-DD`` becomes a naive datetime at 00:00. That value, and a row saved
the same way, is that calendar date. It is not read as UTC midnight, so the
lab zone does not move it to the previous evening. A datetime that carries an
offset is converted to the lab-zone calendar day and stored as that day's
naive midnight.

The nine write paths are sample PATCH received, sample PATCH report, accession
received, test PATCH test_date, test PATCH review_date, PATCH /tests/{id}/review,
result POST entry_date, result PATCH entry_date, and POST /results/batch.
Batch start and end dates use the same storage rule and may be a later lab day.
"""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.core import lab_time
from app.schemas._dates import is_future, store_calendar_day
from models.analysis import Analysis, Analyte, AnalysisAnalyte
from models.batch import Batch, BatchContainer
from models.client import Client
from models.container import Container, ContainerType, Contents
from models.lab_setting import LAB_SETTINGS_ID, LabSetting
from models.name_template import NameTemplate
from models.project import Project
from models.result import Result
from models.sample import Sample
from models.test import Test
from tests._fk_helpers import get_or_create_list_entry, scratch_entry_id


def _login(client):
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


def _world(db_session, admin):
    """One sample, test, result, and batch for the nine date paths."""
    suffix = uuid4().hex[:8]
    org = Client(
        name=f"Date Lab {suffix}",
        description="Date-only lab day",
        billing_info={},
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(org)
    db_session.flush()
    project = Project(
        name=f"Date Project {suffix}",
        description="Date-only lab day",
        start_date=datetime(2026, 1, 1, 15, 0),
        client_id=org.id,
        status=scratch_entry_id(db_session),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(project)
    db_session.flush()
    sample_type = scratch_entry_id(db_session)
    matrix = scratch_entry_id(db_session)
    status = scratch_entry_id(db_session)
    get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
    get_or_create_list_entry(db_session, "test_status", "In Process")
    get_or_create_list_entry(db_session, "test_status", "Complete")
    get_or_create_list_entry(db_session, "project_status", "Active")
    sample = Sample(
        name=f"DATE-SAMPLE-{suffix}",
        description="Date-only lab day",
        due_date=datetime(2026, 11, 1, 0, 0),
        received_date=datetime(2026, 10, 1, 0, 0),
        sample_type=sample_type,
        status=status,
        matrix=matrix,
        project_id=project.id,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(sample)
    db_session.flush()
    analysis = Analysis(
        name=f"Date Analysis {suffix}",
        description="Date-only lab day",
        method="calendar",
        turnaround_time=1,
        cost=1.0,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(analysis)
    db_session.flush()
    analyte = Analyte(
        name=f"Date Analyte {suffix}",
        description="Date-only lab day",
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(analyte)
    db_session.flush()
    db_session.add(
        AnalysisAnalyte(analysis_id=analysis.id, analyte_id=analyte.id, data_type="numeric")
    )
    test = Test(
        name=f"DATE-TEST-{suffix}",
        description="Date-only lab day",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=get_or_create_list_entry(db_session, "test_status", "In Process").id,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(test)
    db_session.flush()
    result = Result(
        test_id=test.id,
        analyte_id=analyte.id,
        raw_result="1.0",
        entry_date=datetime(2026, 10, 1, 0, 0),
        entered_by=admin.id,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(result)
    db_session.flush()
    batch = Batch(
        name=f"DATE-BATCH-{suffix}",
        description="Date-only lab day",
        status=scratch_entry_id(db_session),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(batch)
    db_session.flush()
    tube_type = ContainerType(name=f"date-tube-{suffix}")
    db_session.add(tube_type)
    db_session.flush()
    tube = Container(name=f"DATE-TUBE-{suffix}", type_id=tube_type.id)
    db_session.add(tube)
    db_session.flush()
    db_session.add(Contents(container_id=tube.id, sample_id=sample.id))
    db_session.add(BatchContainer(batch_id=batch.id, container_id=tube.id))
    db_session.commit()
    return {
        "client_id": org.id,
        "project_id": project.id,
        "sample_type": sample_type,
        "matrix": matrix,
        "sample": sample,
        "test": test,
        "result": result,
        "batch": batch,
        "analyte": analyte,
        "admin_id": admin.id,
    }


def _call(client, headers, world, path, day):
    sample_id = str(world["sample"].id)
    test_id = str(world["test"].id)
    if path == "sample_received":
        return client.patch(
            f"/samples/{sample_id}",
            json={"received_date": day},
            headers=headers,
        )
    if path == "sample_report":
        return client.patch(
            f"/samples/{sample_id}",
            json={"report_date": day},
            headers=headers,
        )
    if path == "accession_received":
        return client.post(
            "/samples/accession",
            json={
                "name": f"ACC-{day}-{uuid4().hex[:8]}",
                "due_date": "2026-11-01",
                "received_date": day,
                "sample_type": str(world["sample_type"]),
                "matrix": str(world["matrix"]),
                "client_id": str(world["client_id"]),
                "project_id": str(world["project_id"]),
                "assigned_tests": [],
            },
            headers=headers,
        )
    if path == "test_test_date":
        return client.patch(
            f"/tests/{test_id}",
            json={"test_date": day},
            headers=headers,
        )
    if path == "test_review_date":
        return client.patch(
            f"/tests/{test_id}",
            json={"review_date": day},
            headers=headers,
        )
    if path == "test_review":
        return client.patch(
            f"/tests/{test_id}/review",
            json={"review_date": day},
            headers=headers,
        )
    if path == "result_post":
        return client.post(
            "/results/",
            json={
                "test_id": test_id,
                "analyte_id": str(world["analyte"].id),
                "entered_by": str(world["admin_id"]),
                "entry_date": day,
                "raw_result": "1.0",
            },
            headers=headers,
        )
    if path == "result_patch":
        return client.patch(
            f"/results/{world['result'].id}",
            json={"entry_date": day},
            headers=headers,
        )
    if path == "results_batch":
        return client.post(
            "/results/batch",
            json={
                "batch_id": str(world["batch"].id),
                "results": [
                    {
                        "test_id": test_id,
                        "entry_date": day,
                        "analyte_results": [
                            {
                                "analyte_id": str(world["analyte"].id),
                                "raw_result": "1.0",
                            }
                        ],
                    }
                ],
            },
            headers=headers,
        )
    raise AssertionError(path)


PATHS = (
    "sample_received",
    "sample_report",
    "accession_received",
    "test_test_date",
    "test_review_date",
    "test_review",
    "result_post",
    "result_patch",
    "results_batch",
)


@pytest.mark.parametrize(
    "utc_moment, accept_day, refuse_day",
    [
        (datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), "2026-10-18", "2026-10-19"),
        (datetime(2026, 10, 19, 1, 30, tzinfo=timezone.utc), "2026-10-18", "2026-10-19"),
        (datetime(2026, 10, 19, 3, 59, tzinfo=timezone.utc), "2026-10-18", "2026-10-19"),
        (datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc), "2026-10-19", "2026-10-20"),
        (datetime(2026, 10, 18, 14, 0, tzinfo=timezone.utc), "2026-10-18", "2026-10-19"),
    ],
)
def test_date_only_on_every_path(
    utc_moment, accept_day, refuse_day, client, db_session, test_admin_user, monkeypatch
):
    monkeypatch.setattr(lab_time, "_utcnow", lambda: utc_moment)
    _save_zone(db_session, "America/New_York")
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    for path in PATHS:
        refused = _call(client, headers, world, path, refuse_day)
        assert refused.status_code == 422, f"{path} {refuse_day} {refused.text}"
        assert "future" in refused.text.lower(), path
        accepted = _call(client, headers, world, path, accept_day)
        assert accepted.status_code == 200, f"{path} {accept_day} {accepted.text}"


def test_offset_bearing_values_still_convert(monkeypatch):
    """An offset is a real instant. A naive midnight is the calendar date."""
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 0, 30, tzinfo=timezone.utc)
    )
    lab_time.remember_lab_zone("America/New_York")
    # 2026-10-19 00:00 UTC is 20:00 EDT on 2026-10-18.
    aware_midnight = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
    assert lab_time.as_calendar_day(aware_midnight, "America/New_York") == date(2026, 10, 18)
    assert is_future(aware_midnight) is False
    # Noon UTC on the 19th is 08:00 EDT, the lab's tomorrow from the evening of the 18th.
    aware_tomorrow = datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)
    assert lab_time.as_calendar_day(aware_tomorrow, "America/New_York") == date(2026, 10, 19)
    assert is_future(aware_tomorrow) is True
    # A non-midnight naive value is still UTC wall time.
    naive_evening = datetime(2026, 10, 19, 2, 0)
    assert lab_time.as_calendar_day(naive_evening, "America/New_York") == date(2026, 10, 18)
    assert is_future(naive_evening) is False
    stored_midnight = datetime(2026, 10, 19, 0, 0)
    assert lab_time.as_calendar_day(stored_midnight, "America/New_York") == date(2026, 10, 19)
    assert lab_time.days_from_today(stored_midnight, "America/New_York") == 1
    assert is_future(stored_midnight) is True
    assert is_future(None) is False


def _count_pair(db_session, admin):
    """Two samples whose due date and expiry are the calendar day 2026-10-19 at 00:00."""
    suffix = uuid4().hex[:8]
    org = Client(
        name=f"Count Lab {suffix}",
        billing_info={},
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(org)
    db_session.flush()
    project = Project(
        name=f"Count Project {suffix}",
        start_date=datetime(2026, 1, 1, 15, 0),
        due_date=datetime(2026, 12, 1, 0, 0),
        client_id=org.id,
        status=scratch_entry_id(db_session),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(project)
    db_session.flush()
    analysis = Analysis(
        name=f"Count Analysis {suffix}",
        method="calendar",
        turnaround_time=1,
        cost=1.0,
        shelf_life=1,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(analysis)
    db_session.flush()
    status = scratch_entry_id(db_session)
    sample_type = scratch_entry_id(db_session)
    matrix = scratch_entry_id(db_session)
    tube_type = ContainerType(name=f"count-tube-{suffix}")
    db_session.add(tube_type)
    db_session.flush()
    samples = []
    containers = []
    for index in (1, 2):
        sample = Sample(
            name=f"COUNT-{suffix}-{index}",
            due_date=datetime(2026, 10, 19, 0, 0),
            date_sampled=datetime(2026, 10, 18, 0, 0),
            received_date=datetime(2026, 10, 1, 0, 0),
            sample_type=sample_type,
            status=status,
            matrix=matrix,
            project_id=project.id,
            created_by=admin.id,
            modified_by=admin.id,
        )
        db_session.add(sample)
        db_session.flush()
        test = Test(
            name=f"COUNT-TEST-{suffix}-{index}",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=status,
            created_by=admin.id,
            modified_by=admin.id,
        )
        db_session.add(test)
        tube = Container(name=f"COUNT-TUBE-{suffix}-{index}", type_id=tube_type.id)
        db_session.add(tube)
        db_session.flush()
        db_session.add(Contents(container_id=tube.id, sample_id=sample.id))
        samples.append(sample)
        containers.append(tube)
    db_session.commit()
    return project, samples, containers


def _assert_counts(client, headers, project, samples, containers, days):
    eligible = client.get(
        "/samples/eligible",
        params={"project_id": str(project.id), "size": 100},
        headers=headers,
    )
    assert eligible.status_code == 200, eligible.text
    rows = {row["id"]: row for row in eligible.json()["samples"]}
    for sample in samples:
        row = rows[str(sample.id)]
        assert row["days_until_due"] == days, row
        assert row["is_overdue"] is False, row
        assert row["days_until_expiration"] == days, row
        assert row["is_expired"] is False, row
    compat = client.post(
        "/batches/validate-compatibility",
        json={"container_ids": [str(tube.id) for tube in containers]},
        headers=headers,
    )
    assert compat.status_code == 200, compat.text
    body = compat.json()
    assert body.get("compatible") is True, body
    warnings = body.get("warnings") or []
    expired = next((item for item in warnings if item.get("type") == "expired_samples"), None)
    expired_ids = [] if expired is None else [item["sample_id"] for item in expired["samples"]]
    for sample in samples:
        assert str(sample.id) not in expired_ids


def test_midnight_stored_dates_count_as_calendar_days(
    client, db_session, test_admin_user, monkeypatch
):
    _save_zone(db_session, "America/New_York")
    project, samples, containers = _count_pair(db_session, test_admin_user)
    headers = _login(client)
    evening = [
        datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),  # 20:00 EDT on 10-18
        datetime(2026, 10, 19, 1, 30, tzinfo=timezone.utc),  # 21:30 EDT
        datetime(2026, 10, 19, 3, 59, tzinfo=timezone.utc),  # 23:59 EDT
    ]
    for moment in evening:
        monkeypatch.setattr(lab_time, "_utcnow", lambda moment=moment: moment)
        _assert_counts(client, headers, project, samples, containers, 1)
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)
    )
    _assert_counts(client, headers, project, samples, containers, 0)


# 20:00 EDT on 2026-10-19. UTC has already rolled to 2026-10-20.
_EVENING = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
_LAB_DAY = datetime(2026, 10, 19, 0, 0)


def _evening(monkeypatch, db_session):
    monkeypatch.setattr(lab_time, "_utcnow", lambda: _EVENING)
    _save_zone(db_session, "America/New_York")


def _stored_and_get(client, headers, db_session, world, path, response):
    """The column written by ``path``, and a GET of the row that holds it."""
    body = response.json()
    db_session.expire_all()
    if path == "sample_received":
        row = db_session.query(Sample).filter(Sample.id == world["sample"].id).one()
        field = "received_date"
        get_path = f"/samples/{row.id}"
    elif path == "sample_report":
        row = db_session.query(Sample).filter(Sample.id == world["sample"].id).one()
        field = "report_date"
        get_path = f"/samples/{row.id}"
    elif path == "accession_received":
        row = db_session.query(Sample).filter(Sample.id == body["id"]).one()
        field = "received_date"
        get_path = f"/samples/{row.id}"
    elif path == "test_test_date":
        row = db_session.query(Test).filter(Test.id == world["test"].id).one()
        field = "test_date"
        get_path = f"/tests/{row.id}"
    elif path in ("test_review_date", "test_review"):
        row = db_session.query(Test).filter(Test.id == world["test"].id).one()
        field = "review_date"
        get_path = f"/tests/{row.id}"
    elif path == "result_post":
        row = db_session.query(Result).filter(Result.id == body["id"]).one()
        field = "entry_date"
        get_path = f"/results/{row.id}"
    elif path in ("result_patch", "results_batch"):
        row = db_session.query(Result).filter(Result.id == world["result"].id).one()
        field = "entry_date"
        get_path = f"/results/{row.id}"
    else:
        raise AssertionError(path)
    fetched = client.get(get_path, headers=headers)
    return getattr(row, field), fetched, field


def _assert_lab_midnight(stored, fetched, field):
    assert stored == _LAB_DAY, stored
    assert stored.tzinfo is None
    assert lab_time.days_from_today(stored, "America/New_York") == 0
    assert fetched.status_code == 200, fetched.text
    text = fetched.json()[field]
    assert text.startswith("2026-10-19T00:00:00"), text
    assert "Z" not in text
    assert "+" not in text


@pytest.mark.parametrize("path", PATHS)
def test_utc_midnight_stores_the_lab_day(path, client, db_session, test_admin_user, monkeypatch):
    """'2026-10-20T00:00:00Z' at 20:00 EDT is lab today, stored as 10-19 00:00."""
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    written = _call(client, headers, world, path, "2026-10-20T00:00:00Z")
    assert written.status_code == 200, f"{path} {written.text}"
    stored, fetched, field = _stored_and_get(client, headers, db_session, world, path, written)
    _assert_lab_midnight(stored, fetched, field)


@pytest.mark.parametrize("path", PATHS)
def test_other_offset_stores_the_lab_day(path, client, db_session, test_admin_user, monkeypatch):
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    written = _call(client, headers, world, path, "2026-10-19T23:30:00-04:00")
    assert written.status_code == 200, f"{path} {written.text}"
    stored, fetched, field = _stored_and_get(client, headers, db_session, world, path, written)
    _assert_lab_midnight(stored, fetched, field)


@pytest.mark.parametrize(
    "path, day",
    [(path, day) for path in PATHS for day in ("2026-10-21T00:00:00Z", "2026-10-20T04:00:00Z")],
)
def test_offset_lab_tomorrow_is_refused(path, day, client, db_session, test_admin_user, monkeypatch):
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    refused = _call(client, headers, world, path, day)
    assert refused.status_code == 422, f"{path} {day} {refused.text}"
    assert "future" in refused.text.lower(), path


@pytest.mark.parametrize(
    "path, day",
    [(path, day) for path in PATHS for day in ("2026-10-19", "2026-10-19T00:00:00")],
)
def test_date_only_input_is_stored_unchanged(path, day, client, db_session, test_admin_user, monkeypatch):
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    written = _call(client, headers, world, path, day)
    assert written.status_code == 200, f"{path} {day} {written.text}"
    stored, fetched, field = _stored_and_get(client, headers, db_session, world, path, written)
    _assert_lab_midnight(stored, fetched, field)


def test_due_and_sampled_offsets_count_as_the_lab_day(
    client, db_session, test_admin_user, monkeypatch
):
    """due_date and date_sampled are calendar days and are not future-capped."""
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    analysis = db_session.query(Analysis).filter(Analysis.id == world["test"].analysis_id).one()
    analysis.shelf_life = 1
    db_session.commit()
    headers = _login(client)
    written = client.patch(
        f"/samples/{world['sample'].id}",
        json={
            "due_date": "2026-10-20T00:00:00Z",
            "date_sampled": "2026-10-19T23:30:00-04:00",
        },
        headers=headers,
    )
    assert written.status_code == 200, written.text
    db_session.expire_all()
    sample = db_session.query(Sample).filter(Sample.id == world["sample"].id).one()
    assert sample.due_date == _LAB_DAY
    assert sample.due_date.tzinfo is None
    assert sample.date_sampled == _LAB_DAY
    assert sample.date_sampled.tzinfo is None
    assert lab_time.days_from_today(sample.due_date, "America/New_York") == 0
    eligible = client.get(
        "/samples/eligible",
        params={"project_id": str(world["project_id"]), "size": 100},
        headers=headers,
    )
    assert eligible.status_code == 200, eligible.text
    rows = {row["id"]: row for row in eligible.json()["samples"]}
    row = rows[str(sample.id)]
    assert row["days_until_due"] == 0, row
    assert row["is_overdue"] is False
    assert row["days_until_expiration"] == 1, row
    detail = client.get(f"/samples/{sample.id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["due_date"].startswith("2026-10-19T00:00:00")


def test_batch_dates_store_the_lab_day_and_allow_a_later_day(
    client, db_session, test_admin_user, monkeypatch
):
    _evening(monkeypatch, db_session)
    world = _world(db_session, test_admin_user)
    headers = _login(client)
    batch_id = world["batch"].id
    today = client.patch(
        f"/batches/{batch_id}",
        json={"start_date": "2026-10-20T00:00:00Z", "end_date": "2026-10-19T23:30:00-04:00"},
        headers=headers,
    )
    assert today.status_code == 200, today.text
    db_session.expire_all()
    batch = db_session.query(Batch).filter(Batch.id == batch_id).one()
    assert batch.start_date == _LAB_DAY
    assert batch.start_date.tzinfo is None
    assert batch.end_date == _LAB_DAY
    assert batch.end_date.tzinfo is None
    assert lab_time.days_from_today(batch.start_date, "America/New_York") == 0
    detail = client.get(f"/batches/{batch_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["start_date"].startswith("2026-10-19T00:00:00")
    assert detail.json()["end_date"].startswith("2026-10-19T00:00:00")
    later = client.patch(
        f"/batches/{batch_id}",
        json={"start_date": "2026-10-21T00:00:00Z", "end_date": "2026-11-01"},
        headers=headers,
    )
    assert later.status_code == 200, later.text
    db_session.expire_all()
    batch = db_session.query(Batch).filter(Batch.id == batch_id).one()
    assert batch.start_date == datetime(2026, 10, 20, 0, 0)
    assert batch.start_date.tzinfo is None
    assert batch.end_date == datetime(2026, 11, 1, 0, 0)
    assert batch.end_date.tzinfo is None
    unchanged = client.patch(
        f"/batches/{batch_id}",
        json={"start_date": "2026-11-01T00:00:00"},
        headers=headers,
    )
    assert unchanged.status_code == 200, unchanged.text
    db_session.expire_all()
    batch = db_session.query(Batch).filter(Batch.id == batch_id).one()
    assert batch.start_date == datetime(2026, 11, 1, 0, 0)


def test_store_calendar_day_leaves_naive_and_none(monkeypatch):
    monkeypatch.setattr(lab_time, "_utcnow", lambda: _EVENING)
    lab_time.remember_lab_zone("America/New_York")
    assert store_calendar_day(None) is None
    naive_midnight = datetime(2026, 10, 19, 0, 0)
    assert store_calendar_day(naive_midnight) is naive_midnight
    naive_noon = datetime(2026, 10, 19, 12, 0)
    assert store_calendar_day(naive_noon) is naive_noon
    plain = date(2026, 10, 19)
    assert store_calendar_day(plain) is plain
    aware = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
    stored = store_calendar_day(aware)
    assert stored == _LAB_DAY
    assert stored.tzinfo is None
    offset = datetime.fromisoformat("2026-10-19T23:30:00-04:00")
    assert store_calendar_day(offset) == _LAB_DAY
    assert store_calendar_day(offset).tzinfo is None


def test_name_preview_corrupt_zone_is_503(client, db_session, test_admin_user):
    db_session.query(NameTemplate).filter(NameTemplate.entity_type == "project").update(
        {"active": False}, synchronize_session=False
    )
    db_session.add(
        NameTemplate(
            id=uuid4(),
            entity_type="project",
            template="P-{YYYY}{MM}{DD}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
    )
    _save_zone(db_session, "Not/AZone")
    headers = _login(client)
    preview = client.get(
        "/admin/name-templates/preview",
        params={"entity_type": "project"},
        headers=headers,
    )
    assert preview.status_code == 503, preview.text
    body = preview.json()
    assert body["detail"]["code"] == "lab_timezone_invalid"
    assert "Not/AZone" in body["detail"]["message"]
    assert "Error generating preview" not in preview.text
