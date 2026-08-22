"""P0c S6: entry upsert / write-back only for experiment cohort samples."""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


VALID_TEMPLATE_DEF = {
    "experiment_name": "Cohort Write",
    "protocol_steps": [],
    "transfer_steps": [],
    "result_columns": [],
    "mandatory_review_count": 0,
    "entries": [
        {
            "predefined_entry_key": "samples",
            "name": "Samples",
            "sort_order": 0,
        },
    ],
}


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def experiment(client: TestClient, auth_headers):
    r = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl S6 {uuid4().hex[:8]}",
            "template_definition": VALID_TEMPLATE_DEF,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    tpl = r.json()
    r = client.post(
        "/v1/experiments",
        json={
            "name": f"Exp S6 {uuid4().hex[:8]}",
            "experiment_template_id": tpl["id"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _make_sample(db_session, test_admin_user, test_org):
    from models.sample import Sample
    from models.list import List, ListEntry
    from models.project import Project

    avail = (
        db_session.query(ListEntry)
        .filter(ListEntry.name == "Available for Testing")
        .first()
    )
    if not avail:
        status_list = db_session.query(List).filter(List.name == "sample_status").first()
        if not status_list:
            status_list = List(name="sample_status")
            db_session.add(status_list)
            db_session.flush()
        avail = ListEntry(list_id=status_list.id, name="Available for Testing")
        db_session.add(avail)
        db_session.flush()

    lst = List(name=f"s6_{uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.flush()
    sample_type = ListEntry(list_id=lst.id, name=f"t_{uuid4().hex[:6]}")
    matrix = ListEntry(list_id=lst.id, name=f"m_{uuid4().hex[:6]}")
    db_session.add_all([sample_type, matrix])
    db_session.flush()

    project = Project(
        name=f"S6 {uuid4().hex[:8]}",
        client_id=test_org.id,
        status=avail.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"S6S {uuid4().hex[:6]}",
        sample_type=sample_type.id,
        status=avail.id,
        matrix=matrix.id,
        project_id=project.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(sample)
    db_session.commit()
    return sample


class TestCohortUpsertS6:
    def test_foreign_sample_id_rejected_on_upsert(
        self,
        client: TestClient,
        auth_headers,
        experiment,
        db_session,
        test_admin_user,
        test_org,
    ):
        from models.field_definition import FieldDefinition

        foreign = _make_sample(db_session, test_admin_user, test_org)

        fd = FieldDefinition(
            name=f"note_{uuid4().hex[:6]}",
            entity_type="experiment_sample_data",
            data_type="text",
            display_name="Note",
            is_materialized_column=False,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(fd)
        db_session.commit()

        r = client.post(
            f"/v1/experiments/{experiment['id']}/entries",
            json={
                "experiment_id": experiment["id"],
                "entry_type": "experiment_sample_data",
                "name": "Sample notes",
                "fields": [{"field_definition_id": str(fd.id), "sort_order": 0}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        entry = r.json()

        r = client.put(
            f"/v1/entries/{entry['id']}/values",
            json={
                "values": [
                    {
                        "field_definition_id": str(fd.id),
                        "sample_id": str(foreign.id),
                        "value_text": "should fail",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "sample_not_in_cohort"

    def test_cohort_sample_upsert_ok(
        self,
        client: TestClient,
        auth_headers,
        experiment,
        db_session,
        test_admin_user,
        test_org,
    ):
        from models.field_definition import FieldDefinition
        from models.experiment import ExperimentSampleExecution

        on_cohort = _make_sample(db_session, test_admin_user, test_org)
        db_session.add(
            ExperimentSampleExecution(
                experiment_id=experiment["id"],
                sample_id=on_cohort.id,
                created_by=test_admin_user.id,
                modified_by=test_admin_user.id,
            )
        )
        db_session.commit()

        fd = FieldDefinition(
            name=f"ok_{uuid4().hex[:6]}",
            entity_type="experiment_sample_data",
            data_type="text",
            display_name="OK Note",
            is_materialized_column=False,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(fd)
        db_session.commit()

        r = client.post(
            f"/v1/experiments/{experiment['id']}/entries",
            json={
                "experiment_id": experiment["id"],
                "entry_type": "experiment_sample_data",
                "name": "OK notes",
                "fields": [{"field_definition_id": str(fd.id), "sort_order": 0}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        entry = r.json()

        r = client.put(
            f"/v1/entries/{entry['id']}/values",
            json={
                "values": [
                    {
                        "field_definition_id": str(fd.id),
                        "sample_id": str(on_cohort.id),
                        "value_text": "allowed",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()[0]["value_text"] == "allowed"
