"""Date-only inputs and stored midnights are lab calendar days.

``YYYY-MM-DD`` becomes a naive datetime at 00:00. That value, and a row saved
the same way, is that calendar date. It is not read as UTC midnight, so the
lab zone does not move it to the previous evening. A datetime that carries an
offset still converts into the lab zone.

The nine write paths are sample PATCH received, sample PATCH report, accession
received, test PATCH test_date, test PATCH review_date, PATCH /tests/{id}/review,
result POST entry_date, result PATCH entry_date, and POST /results/batch.
"""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.core import lab_time
from app.schemas._dates import is_future
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
