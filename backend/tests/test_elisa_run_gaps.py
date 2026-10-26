"""ELISA run gaps: import from a Gen5 file, link rows, publish, reject, rerun, receipt.

The Gen5 export and parser config are the IL-6 pack (read-only reference copied
into tests/fixtures/elisa). Plate math (4PL, QC ranges, LLOQ/ULOQ) is not in
this slice.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "elisa"
GEN5 = FIXTURE_DIR / "IL6-PLT-0001_Gen5.csv"
PARSER = json.loads((FIXTURE_DIR / "parser_config.json").read_text())


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _ensure_test_status(db_session) -> None:
    from models.list import List, ListEntry

    lst = db_session.query(List).filter(List.name.in_(("Test Status", "test_status"))).first()
    if not lst:
        lst = List(name="test_status", description="Test status")
        db_session.add(lst)
        db_session.flush()
    names = {
        row.name
        for row in db_session.query(ListEntry).filter(ListEntry.list_id == lst.id).all()
    }
    if not names.intersection({"Assigned/Pending", "In Process", "Pending"}):
        db_session.add(ListEntry(list_id=lst.id, name="In Process"))
        db_session.flush()


def _sample(db_session, test_admin_user, test_org, client_sample_id: str):
    from models.list import List, ListEntry
    from models.project import Project
    from models.sample import Sample

    lst = List(name=f"elisa_list_{uuid.uuid4().hex[:6]}", description="t")
    db_session.add(lst)
    db_session.flush()
    sample_type = ListEntry(list_id=lst.id, name=f"Serum-{uuid.uuid4().hex[:6]}")
    status = ListEntry(list_id=lst.id, name=f"Status-{uuid.uuid4().hex[:6]}")
    matrix = ListEntry(list_id=lst.id, name=f"Matrix-{uuid.uuid4().hex[:6]}")
    db_session.add_all([sample_type, status, matrix])
    db_session.flush()
    project = Project(
        name=f"P {uuid.uuid4().hex[:6]}",
        client_id=test_org.id,
        status=status.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"S {uuid.uuid4().hex[:6]}",
        sample_type=sample_type.id,
        status=status.id,
        matrix=matrix.id,
        project_id=project.id,
        client_sample_id=client_sample_id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(sample)
    db_session.commit()
    return sample


def _analysis(db_session, test_admin_user):
    from models.analysis import Analyte, AnalyteAlias, Analysis, AnalysisAnalyte

    _ensure_test_status(db_session)
    analysis = Analysis(
        name=f"IL6 {uuid.uuid4().hex[:6]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    analyte = Analyte(
        name=f"IL6_{uuid.uuid4().hex[:4]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([analysis, analyte])
    db_session.flush()
    db_session.add(AnalyteAlias(analyte_id=analyte.id, alias="corr", created_by=test_admin_user.id))
    db_session.add(AnalysisAnalyte(analysis_id=analysis.id, analyte_id=analyte.id))
    db_session.commit()
    return analysis, analyte


def _template(client, auth_headers) -> str:
    response = client.post(
        "/v1/experiment-templates",
        json={
            "name": f"Tpl {uuid.uuid4().hex[:8]}",
            "template_definition": {
                "experiment_name": "ELISA",
                "protocol_steps": ["read"],
                "transfer_steps": [],
                "result_columns": [],
                "mandatory_review_count": 0,
                "entries": __import__(
                    "tests.test_flexible_experiment", fromlist=["VALID_TEMPLATE_DEF"]
                ).VALID_TEMPLATE_DEF["entries"],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _parser(client, auth_headers, db_session, analysis) -> tuple[str, str]:
    from tests.test_flexible_experiment import PLATE_READER_TYPE_ID

    instrument = client.post(
        "/v1/instruments",
        headers=auth_headers,
        json={
            "name": f"I-{uuid.uuid4().hex[:6]}",
            "instrument_type_id": PLATE_READER_TYPE_ID,
        },
    )
    assert instrument.status_code == 201, instrument.text
    created = client.post(
        "/v1/data-parsers",
        headers=auth_headers,
        json={
            "name": f"Gen5-{uuid.uuid4().hex[:6]}",
            "instrument_id": instrument.json()["id"],
            "parser_config": PARSER,
            "analyses": [{"analysis_id": str(analysis.id), "is_default": True}],
            "activate": True,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"], instrument.json()["id"]


def _run(client, auth_headers, template_id: str, analysis_id: str, sample_id: str) -> str:
    created = client.post(
        "/v1/lims-runs",
        json={
            "name": f"Plate {uuid.uuid4().hex[:8]}",
            "experiment_template_id": template_id,
            "analysis_id": analysis_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    started = client.patch(
        f"/v1/lims-runs/{run_id}/start",
        json={"sample_ids": [sample_id]},
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text
    return run_id


def _publish(client, auth_headers, run_id: str):
    reviewed = client.patch(f"/v1/lims-runs/{run_id}/review", headers=auth_headers)
    assert reviewed.status_code == 200, reviewed.text
    published = client.patch(f"/v1/lims-runs/{run_id}/complete", headers=auth_headers)
    return published


class TestElisaRunGaps:
    def test_gen5_import_links_sample_and_publish_creates_results(
        self,
        client: TestClient,
        auth_headers,
        db_session,
        test_admin_user,
        test_org,
    ):
        sample = _sample(db_session, test_admin_user, test_org, "IL6-SER-0001")
        analysis, analyte = _analysis(db_session, test_admin_user)
        template_id = _template(client, auth_headers)
        parser_id, instrument_id = _parser(client, auth_headers, db_session, analysis)
        run_id = _run(client, auth_headers, template_id, str(analysis.id), str(sample.id))

        with GEN5.open("rb") as handle:
            imported = client.post(
                f"/v1/lims-runs/{run_id}/import-file",
                headers=auth_headers,
                data={"parser_id": parser_id, "instrument_id": instrument_id},
                files={"file": ("IL6-PLT-0001_Gen5.csv", handle, "text/csv")},
            )
        assert imported.status_code == 200, imported.text
        body = imported.json()
        assert body["imported"] == 96
        assert body["linked"] == 2
        assert body["unmatched_count"] == 94
        standard = next(row for row in body["unmatched"] if row["sample_key"] == "STD-S1")
        assert standard["reason"] == "No sample matches STD-S1"
        assert standard["well_position"] == "A1"
        blank = next(row for row in body["unmatched"] if row["sample_key"] == "BLANK")
        assert "No sample matches BLANK" == blank["reason"]

        listed = client.get(
            f"/v1/lims-runs/{run_id}/data",
            headers=auth_headers,
            params={"page": 1, "size": 200},
        )
        assert listed.status_code == 200, listed.text
        rows = listed.json()["rows"]
        assert listed.json()["total"] == 96
        linked = [row for row in rows if row["sample_id"] == str(sample.id)]
        assert len(linked) == 2
        assert {row["well_position"] for row in linked} == {"D3", "D4"}
        assert all(row["sample_key"] == "IL6-SER-0001" for row in linked)
        unmatched = [row for row in rows if row["sample_id"] is None]
        assert len(unmatched) == 94
        assert all(row["link_note"] for row in unmatched)

        preview = client.get(
            f"/v1/lims-runs/{run_id}/promotion/preview", headers=auth_headers
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["create_count"] == 2
        assert preview.json()["conflict_count"] == 0

        published = _publish(client, auth_headers, run_id)
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "published"

        results = client.get(
            "/results/",
            headers=auth_headers,
            params={"analyte_id": str(analyte.id), "page": 1, "size": 100},
        )
        assert results.status_code == 200, results.text
        ours = [
            row
            for row in results.json().get("results") or []
            if str(row.get("lims_run_id")) == run_id
        ]
        assert len(ours) == 2
        assert {int(row["replicate"]) for row in ours} == {1, 2}
        for row in ours:
            assert abs(float(row["raw_result"]) - 0.063) < 1e-6

    def test_reject_keeps_rows(
        self,
        client: TestClient,
        auth_headers,
        db_session,
        test_admin_user,
        test_org,
    ):
        sample = _sample(db_session, test_admin_user, test_org, f"IL6-{uuid.uuid4().hex[:6]}")
        analysis, _analyte = _analysis(db_session, test_admin_user)
        template_id = _template(client, auth_headers)
        run_id = _run(client, auth_headers, template_id, str(analysis.id), str(sample.id))
        imported = client.post(
            f"/v1/lims-runs/{run_id}/import",
            json={
                "rows": [
                    {
                        "sample_id": str(sample.id),
                        "sample_key": sample.client_sample_id,
                        "well_position": "D3",
                        "row_data": {"corr": "0.063", "replicate": 1},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert imported.status_code == 200, imported.text

        missing = client.post(
            f"/v1/lims-runs/{run_id}/reject",
            json={"reason": "   "},
            headers=auth_headers,
        )
        assert missing.status_code == 422, missing.text

        rejected = client.post(
            f"/v1/lims-runs/{run_id}/reject",
            json={"reason": "QC-H out of range"},
            headers=auth_headers,
        )
        assert rejected.status_code == 200, rejected.text
        assert rejected.json()["status"] == "failed"
        assert rejected.json()["status_reason"] == "QC-H out of range"
        assert rejected.json()["rejected_at"]

        listed = client.get(
            f"/v1/lims-runs/{run_id}/data", headers=auth_headers, params={"size": 20}
        )
        assert listed.json()["total"] == 1
        assert listed.json()["rows"][0]["sample_id"] == str(sample.id)

    def test_rerun_publish_is_held_and_reviewer_picks(
        self,
        client: TestClient,
        auth_headers,
        db_session,
        test_admin_user,
        test_org,
    ):
        from models.result import Result
        from models.result_acceptance import ResultAcceptance

        sample = _sample(db_session, test_admin_user, test_org, f"IL6-{uuid.uuid4().hex[:6]}")
        analysis, analyte = _analysis(db_session, test_admin_user)
        template_id = _template(client, auth_headers)
        run_id = _run(client, auth_headers, template_id, str(analysis.id), str(sample.id))
        first = client.post(
            f"/v1/lims-runs/{run_id}/import",
            json={
                "rows": [
                    {
                        "sample_id": str(sample.id),
                        "well_position": "D3",
                        "row_data": {"corr": "1.10", "replicate": 1},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert first.status_code == 200, first.text
        published = _publish(client, auth_headers, run_id)
        assert published.status_code == 200, published.text

        rerun = client.post(f"/v1/lims-runs/{run_id}/rerun", json={}, headers=auth_headers)
        assert rerun.status_code == 201, rerun.text
        rerun_id = rerun.json()["id"]
        assert rerun.json()["replaces_run_id"] == run_id
        assert rerun.json()["status"] == "draft"
        assert str(sample.id) in [str(sid) for sid in rerun.json()["cohort"]["sample_ids"]]

        started = client.patch(
            f"/v1/lims-runs/{rerun_id}/start",
            json={"sample_ids": [str(sample.id)]},
            headers=auth_headers,
        )
        assert started.status_code == 200, started.text
        second = client.post(
            f"/v1/lims-runs/{rerun_id}/import",
            json={
                "rows": [
                    {
                        "sample_id": str(sample.id),
                        "well_position": "D3",
                        "row_data": {"corr": "2.20", "replicate": 1},
                    }
                ]
            },
            headers=auth_headers,
        )
        assert second.status_code == 200, second.text
        preview = client.get(
            f"/v1/lims-runs/{rerun_id}/promotion/preview", headers=auth_headers
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["held_count"] == 1
        assert preview.json()["conflict_count"] == 0
        republished = _publish(client, auth_headers, rerun_id)
        assert republished.status_code == 200, republished.text

        db_session.expire_all()
        stored = (
            db_session.query(Result)
            .filter(Result.analyte_id == analyte.id, Result.active == True)  # noqa: E712
            .one()
        )
        assert stored.raw_result == "1.10"
        assert str(stored.lims_run_id) == run_id

        choices = client.get(f"/v1/lims-runs/{rerun_id}/value-choices", headers=auth_headers)
        assert choices.status_code == 200, choices.text
        choice = choices.json()[0]
        assert {opt["raw_result"] for opt in choice["options"]} == {"1.10", "2.20"}

        accepted = client.post(
            f"/v1/lims-runs/{rerun_id}/value-choices",
            json={
                "sample_id": str(sample.id),
                "analyte_id": str(analyte.id),
                "replicate": 1,
                "accepted_lims_run_id": rerun_id,
                "reason": "Rerun is the value to report",
            },
            headers=auth_headers,
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["accepted_value"] == "2.20"

        db_session.expire_all()
        stored = (
            db_session.query(Result)
            .filter(Result.analyte_id == analyte.id, Result.active == True)  # noqa: E712
            .one()
        )
        assert stored.raw_result == "2.20"
        assert str(stored.lims_run_id) == rerun_id
        pick = (
            db_session.query(ResultAcceptance)
            .filter(
                ResultAcceptance.sample_id == sample.id,
                ResultAcceptance.active == True,  # noqa: E712
            )
            .one()
        )
        assert pick.accepted_value == "2.20"
        assert pick.previous_value == "1.10"
        assert pick.other_value == "1.10"

    def test_receive_stores_manifest_fields(
        self,
        client: TestClient,
        auth_headers,
        db_session,
        test_admin_user,
    ):
        from models.container import ContainerType
        from models.list import List, ListEntry
        from models.project import Project, ProjectUser
        from models.sample import Sample

        status_list = List(name="Sample Status", description="Sample statuses")
        type_list = List(name="Sample Type", description="Sample types")
        project_status_list = List(name="Project Status", description="Project statuses")
        db_session.add_all([status_list, type_list, project_status_list])
        db_session.flush()
        available = ListEntry(list_id=status_list.id, name="Available for Testing")
        sample_type = ListEntry(list_id=type_list.id, name="Serum")
        project_active = ListEntry(list_id=project_status_list.id, name="Active")
        db_session.add_all([available, sample_type, project_active])
        tube = ContainerType(name="Tube", capacity=5, material="plastic", rows=1, columns=1)
        db_session.add(tube)
        db_session.flush()
        project = Project(
            name=f"AR-{uuid.uuid4().hex[:8]}",
            start_date=datetime.utcnow(),
            client_id=test_admin_user.client_id,
            status=project_active.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(project)
        db_session.flush()
        db_session.add(ProjectUser(project_id=project.id, user_id=test_admin_user.id))
        db_session.commit()

        payload = {
            "container_barcode": f"NBIO-{uuid.uuid4().hex[:8]}",
            "sample_type": str(sample_type.id),
            "project_id": str(project.id),
            "container_type_id": str(tube.id),
            "client_sample_id": f"IL6-{uuid.uuid4().hex[:6]}",
            "date_sampled": "2026-10-20",
            "volume_ul": 500,
            "receipt_condition": "Frozen",
            "thaw_count": 1,
        }
        received = client.post("/samples/receive", json=payload, headers=auth_headers)
        assert received.status_code == 201, received.text
        body = received.json()
        assert body["date_sampled"] == "2026-10-20"
        assert body["volume_ul"] == 500
        assert body["receipt_condition"] == "Frozen"
        assert body["thaw_count"] == 1
        db_session.expire_all()
        stored = db_session.query(Sample).filter(Sample.id == body["sample_id"]).one()
        assert str(stored.date_sampled) == "2026-10-20"
        assert float(stored.volume_ul) == 500
        assert stored.receipt_condition == "Frozen"
        assert stored.thaw_count == 1

        future = dict(payload, container_barcode=f"NBIO-{uuid.uuid4().hex[:8]}", date_sampled="2099-01-01")
        assert client.post("/samples/receive", json=future, headers=auth_headers).status_code == 422
        negative = dict(
            payload,
            container_barcode=f"NBIO-{uuid.uuid4().hex[:8]}",
            client_sample_id=f"IL6-{uuid.uuid4().hex[:6]}",
            volume_ul=-1,
            date_sampled="2026-10-20",
        )
        assert client.post("/samples/receive", json=negative, headers=auth_headers).status_code == 422
        thaw = dict(
            payload,
            container_barcode=f"NBIO-{uuid.uuid4().hex[:8]}",
            client_sample_id=f"IL6-{uuid.uuid4().hex[:6]}",
            thaw_count=-1,
        )
        assert client.post("/samples/receive", json=thaw, headers=auth_headers).status_code == 422


def test_result_acceptances_are_registered_and_forced_rls(migrated_engine):
    with migrated_engine.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                text("SELECT physical_name FROM schema_tables")
            ).all()
        }
        assert "result_acceptances" in names
        forced = conn.execute(
            text(
                "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'result_acceptances'"
            )
        ).scalar()
        assert forced is True
        sample_cols = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT c.physical_name
                    FROM schema_columns c
                    JOIN schema_tables t ON t.id = c.table_id
                    WHERE t.physical_name = 'samples'
                    """
                )
            ).all()
        }
        assert {"volume_ul", "receipt_condition", "thaw_count"} <= sample_cols
        run_cols = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT c.physical_name
                    FROM schema_columns c
                    JOIN schema_tables t ON t.id = c.table_id
                    WHERE t.physical_name = 'lims_runs'
                    """
                )
            ).all()
        }
        assert {"status_reason", "replaces_run_id", "rejected_at"} <= run_cols
