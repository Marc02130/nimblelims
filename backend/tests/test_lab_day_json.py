"""Lab-day API values are YYYY-MM-DD, and project create keeps due_date."""
from __future__ import annotations

import re
from datetime import date
from uuid import uuid4

from models.analysis import Analyte, Analysis
from models.batch import Batch
from models.lab_setting import LAB_SETTINGS_ID, LabSetting
from models.list import List, ListEntry
from models.project import Project
from models.result import Result
from models.sample import Sample
from models.test import Test

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
START = "2026-10-19"
DUE = "2026-11-02"
RECEIVED = "2026-10-18"
REPORT = "2026-10-20"
SAMPLED = "2026-10-17"
TEST_DAY = "2026-10-21"
REVIEW = "2026-10-22"
ENTRY = "2026-10-23"
END = "2026-10-24"


def _listed(client, path: str, key: str, row_id, headers: dict) -> dict:
    response = client.get(path, headers=headers, params={"size": 100})
    assert response.status_code == 200, response.text
    return next(item for item in response.json()[key] if item["id"] == str(row_id))


def _assert_day(value: str, expected: str) -> None:
    assert value == expected
    assert _DAY.fullmatch(value) is not None
    assert "T" not in value


def _entry(db_session, list_id, label: str) -> ListEntry:
    row = ListEntry(list_id=list_id, name=f"{label}-{uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _seed(db_session, admin, org):
    db_session.add(
        LabSetting(id=LAB_SETTINGS_ID, timezone="America/New_York", modified_by=admin.id)
    )
    catalog = List(name=f"lab-day-{uuid4().hex[:8]}")
    db_session.add(catalog)
    db_session.flush()
    status = _entry(db_session, catalog.id, "status")
    sample_type = _entry(db_session, catalog.id, "type")
    matrix = _entry(db_session, catalog.id, "matrix")
    project = Project(
        name=f"Lab day {uuid4().hex[:8]}",
        client_id=org.id,
        status=status.id,
        start_date=date(2026, 10, 19),
        due_date=date(2026, 11, 2),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"Lab day sample {uuid4().hex[:8]}",
        sample_type=sample_type.id,
        status=status.id,
        matrix=matrix.id,
        project_id=project.id,
        due_date=date(2026, 11, 2),
        received_date=date(2026, 10, 18),
        report_date=date(2026, 10, 20),
        date_sampled=date(2026, 10, 17),
        created_by=admin.id,
        modified_by=admin.id,
    )
    analysis = Analysis(
        name=f"Lab day analysis {uuid4().hex[:8]}",
        created_by=admin.id,
        modified_by=admin.id,
    )
    analyte = Analyte(
        name=f"Lab day analyte {uuid4().hex[:8]}",
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add_all([sample, analysis, analyte])
    db_session.flush()
    test = Test(
        name=f"Lab day test {uuid4().hex[:8]}",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=status.id,
        test_date=date(2026, 10, 21),
        review_date=date(2026, 10, 22),
        created_by=admin.id,
        modified_by=admin.id,
    )
    batch = Batch(
        name=f"Lab day batch {uuid4().hex[:8]}",
        status=status.id,
        start_date=date(2026, 10, 19),
        end_date=date(2026, 10, 24),
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add_all([test, batch])
    db_session.flush()
    result = Result(
        test_id=test.id,
        analyte_id=analyte.id,
        entry_date=date(2026, 10, 23),
        entered_by=admin.id,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db_session.add(result)
    db_session.commit()
    return {
        "project": project,
        "sample": sample,
        "test": test,
        "result": result,
        "batch": batch,
        "status": status,
    }


def test_lab_day_responses_are_date_only(client, db_session, test_admin_user, test_org, admin_token):
    rows = _seed(db_session, test_admin_user, test_org)
    headers = {"Authorization": f"Bearer {admin_token}"}

    project = client.get(f"/projects/{rows['project'].id}", headers=headers)
    assert project.status_code == 200, project.text
    body = project.json()
    _assert_day(body["start_date"], START)
    _assert_day(body["due_date"], DUE)
    listed = _listed(client, "/projects", "projects", rows["project"].id, headers)
    _assert_day(listed["start_date"], START)
    _assert_day(listed["due_date"], DUE)

    sample = client.get(f"/samples/{rows['sample'].id}", headers=headers)
    assert sample.status_code == 200, sample.text
    body = sample.json()
    _assert_day(body["due_date"], DUE)
    _assert_day(body["received_date"], RECEIVED)
    _assert_day(body["report_date"], REPORT)
    _assert_day(body["date_sampled"], SAMPLED)
    listed = _listed(client, "/samples", "samples", rows["sample"].id, headers)
    _assert_day(listed["due_date"], DUE)
    _assert_day(listed["received_date"], RECEIVED)
    _assert_day(listed["report_date"], REPORT)
    _assert_day(listed["date_sampled"], SAMPLED)

    test_row = client.get(f"/tests/{rows['test'].id}", headers=headers)
    assert test_row.status_code == 200, test_row.text
    body = test_row.json()
    _assert_day(body["test_date"], TEST_DAY)
    _assert_day(body["review_date"], REVIEW)
    listed = _listed(client, "/tests", "tests", rows["test"].id, headers)
    _assert_day(listed["test_date"], TEST_DAY)
    _assert_day(listed["review_date"], REVIEW)

    result = client.get(f"/results/{rows['result'].id}", headers=headers)
    assert result.status_code == 200, result.text
    _assert_day(result.json()["entry_date"], ENTRY)
    listed = _listed(client, "/results/", "results", rows["result"].id, headers)
    _assert_day(listed["entry_date"], ENTRY)

    batch = client.get(f"/batches/{rows['batch'].id}", headers=headers)
    assert batch.status_code == 200, batch.text
    body = batch.json()
    _assert_day(body["start_date"], START)
    _assert_day(body["end_date"], END)
    listed = _listed(client, "/batches", "batches", rows["batch"].id, headers)
    _assert_day(listed["start_date"], START)
    _assert_day(listed["end_date"], END)

    eligible = client.get(
        "/samples/eligible",
        params={"project_id": str(rows["project"].id)},
        headers=headers,
    )
    assert eligible.status_code == 200, eligible.text
    match = next(item for item in eligible.json()["samples"] if item["id"] == str(rows["sample"].id))
    _assert_day(match["due_date"], DUE)
    _assert_day(match["received_date"], RECEIVED)
    _assert_day(match["date_sampled"], SAMPLED)
    _assert_day(match["project_due_date"], DUE)
    _assert_day(match["effective_due_date"], DUE)


def test_post_project_persists_due_date(client, db_session, test_admin_user, test_org, admin_token):
    db_session.add(
        LabSetting(id=LAB_SETTINGS_ID, timezone="America/New_York", modified_by=test_admin_user.id)
    )
    catalog = List(name=f"project-due-{uuid4().hex[:8]}")
    db_session.add(catalog)
    db_session.flush()
    status = _entry(db_session, catalog.id, "status")
    db_session.commit()
    headers = {"Authorization": f"Bearer {admin_token}"}

    date_only = client.post(
        "/projects",
        headers=headers,
        json={
            "name": f"Due date only {uuid4().hex[:8]}",
            "start_date": "2026-10-19",
            "due_date": "2026-11-02",
            "client_id": str(test_org.id),
            "status": str(status.id),
        },
    )
    assert date_only.status_code == 201, date_only.text
    created = date_only.json()
    _assert_day(created["start_date"], START)
    _assert_day(created["due_date"], DUE)
    fetched = client.get(f"/projects/{created['id']}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    _assert_day(fetched.json()["due_date"], DUE)

    offset = client.post(
        "/projects",
        headers=headers,
        json={
            "name": f"Due date offset {uuid4().hex[:8]}",
            "start_date": "2026-10-19T03:30:00+00:00",
            "due_date": "2026-10-19T03:30:00+00:00",
            "client_id": str(test_org.id),
            "status": str(status.id),
        },
    )
    assert offset.status_code == 201, offset.text
    body = offset.json()
    # 03:30 UTC is still 2026-10-18 in America/New_York.
    _assert_day(body["start_date"], "2026-10-18")
    _assert_day(body["due_date"], "2026-10-18")
    stored = db_session.get(Project, body["id"])
    assert stored is not None
    assert stored.due_date == date(2026, 10, 18)
    assert stored.start_date == date(2026, 10, 18)
