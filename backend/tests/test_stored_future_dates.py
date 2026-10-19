"""A stored future date must not 500 a read.

Validators stay on create and update. Response models do not re-run them,
so a row written under another zone still lists and opens.
"""
from datetime import datetime, timedelta
from uuid import uuid4

from models.analysis import Analyte, Analysis
from models.list import List, ListEntry
from models.project import Project
from models.result import Result
from models.sample import Sample
from models.test import Test

FUTURE = datetime(2099, 6, 1, 15, 0)


def _login(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed(db_session, user, org):
    suffix = uuid4().hex[:8]
    lst = List(name=f"future-{suffix}")
    db_session.add(lst)
    db_session.flush()
    status = ListEntry(list_id=lst.id, name=f"Available {suffix}")
    sample_type = ListEntry(list_id=lst.id, name=f"type {suffix}")
    db_session.add_all([status, sample_type])
    db_session.flush()
    project = Project(
        name=f"P {suffix}",
        client_id=org.id,
        status=status.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=2),
    )
    analysis = Analysis(name=f"A {suffix}", created_by=user.id, modified_by=user.id)
    analyte = Analyte(name=f"N {suffix}", created_by=user.id, modified_by=user.id)
    db_session.add_all([project, analysis, analyte])
    db_session.flush()
    sample = Sample(
        name=f"S {suffix}",
        sample_type=sample_type.id,
        status=status.id,
        project_id=project.id,
        received_date=FUTURE,
        report_date=FUTURE,
        temperature=25,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(sample)
    db_session.flush()
    test = Test(
        name=f"T {suffix}",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=status.id,
        test_date=FUTURE,
        review_date=FUTURE,
        custom_attributes={},
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(test)
    db_session.flush()
    result = Result(
        test_id=test.id,
        analyte_id=analyte.id,
        entry_date=FUTURE,
        entered_by=user.id,
        raw_result="1",
        custom_attributes={},
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(result)
    db_session.commit()
    return sample, test, result, sample_type, status, project, analyte


def test_stored_future_dates_read_as_200(client, db_session, test_admin_user, test_org):
    sample, test, result, sample_type, status, project, analyte = _seed(
        db_session, test_admin_user, test_org
    )
    headers = _login(client)

    samples = client.get("/samples", headers=headers, params={"size": 100})
    assert samples.status_code == 200, samples.text
    assert any(row["id"] == str(sample.id) for row in samples.json()["samples"])

    one_sample = client.get(f"/samples/{sample.id}", headers=headers)
    assert one_sample.status_code == 200, one_sample.text
    assert one_sample.json()["received_date"].startswith("2099-06-01")

    tests = client.get("/tests", headers=headers, params={"sample_id": str(sample.id), "size": 100})
    assert tests.status_code == 200, tests.text
    assert any(row["id"] == str(test.id) for row in tests.json()["tests"])

    one_test = client.get(f"/tests/{test.id}", headers=headers)
    assert one_test.status_code == 200, one_test.text
    assert one_test.json()["test_date"].startswith("2099-06-01")

    results = client.get("/results/", headers=headers, params={"test_id": str(test.id), "size": 100})
    assert results.status_code == 200, results.text
    assert any(row["id"] == str(result.id) for row in results.json()["results"])

    one_result = client.get(f"/results/{result.id}", headers=headers)
    assert one_result.status_code == 200, one_result.text
    assert one_result.json()["entry_date"].startswith("2099-06-01")

    refused_sample = client.post(
        "/samples/",
        headers=headers,
        json={
            "name": f"nope-{uuid4().hex[:6]}",
            "sample_type": str(sample_type.id),
            "status": str(status.id),
            "project_id": str(project.id),
            "received_date": "2099-06-02T12:00:00",
        },
    )
    assert refused_sample.status_code == 422, refused_sample.text
    assert "future" in refused_sample.text.lower()

    refused_test = client.patch(
        f"/tests/{test.id}",
        headers=headers,
        json={"test_date": "2099-06-02T12:00:00"},
    )
    assert refused_test.status_code == 422, refused_test.text
    assert "future" in refused_test.text.lower()

    refused_result = client.post(
        "/results/",
        headers=headers,
        json={
            "test_id": str(test.id),
            "analyte_id": str(analyte.id),
            "entered_by": str(test_admin_user.id),
            "entry_date": "2099-06-02T12:00:00",
            "raw_result": "2",
        },
    )
    assert refused_result.status_code == 422, refused_result.text
    assert "future" in refused_result.text.lower()
