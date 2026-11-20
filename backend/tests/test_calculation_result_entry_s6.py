"""Calculations S6: run and result-entry data model (API and service level).

Database-level guards, the 0123 backfill, and downgrade are in
``test_calculation_result_entry_s6_db.py``.
"""
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.calculation_catalog_decimal import COPY_RAW_V1, copy_raw
from app.services.calculation_kat import run_kats
from app.services.result_entry_service import (
    RESULTS_ENTRY_KEY,
    RESULTS_ENTRY_TYPE,
    ResultEntryService,
)
from tests._fk_helpers import scratch_entry_id
from tests.test_calculation_catalog_decimal_s4 import _health
from tests.test_result_promotion import (  # noqa: F401  (fixtures)
    analysis_and_analyte,
    auth_headers,
    sample_id,
    template_id,
)


def _unit(db_session, user_id) -> UUID:
    from models.unit import Unit

    unit = Unit(
        name=f"ug/L-{uuid4().hex[:6]}",
        multiplier=1,
        type=scratch_entry_id(db_session),
        created_by=user_id,
        modified_by=user_id,
    )
    db_session.add(unit)
    db_session.flush()
    return unit.id


def _configure(db_session, ids: Dict[str, str], user_id) -> Dict[str, Any]:
    """Lead: pairing unit set, display order 2. Arsenic: display order 1."""
    from models.analysis import AnalysisAnalyte

    unit_id = _unit(db_session, user_id)
    lead = (
        db_session.query(AnalysisAnalyte)
        .filter_by(analysis_id=UUID(ids["analysis_id"]), analyte_id=UUID(ids["lead_id"]))
        .one()
    )
    lead.pairing_unit_id = unit_id
    lead.display_order = 2
    arsenic = (
        db_session.query(AnalysisAnalyte)
        .filter_by(analysis_id=UUID(ids["analysis_id"]), analyte_id=UUID(ids["arsenic_id"]))
        .one()
    )
    arsenic.display_order = 1
    db_session.commit()
    return {"unit_id": unit_id}


def _started_run(client, headers, ids, template, sample) -> str:
    r = client.post(
        "/v1/lims-runs",
        json={
            "name": f"S6 {uuid4().hex[:8]}",
            "experiment_template_id": template,
            "analysis_id": ids["analysis_id"],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    run_id = r.json()["id"]
    r = client.patch(
        f"/v1/lims-runs/{run_id}/start", json={"sample_ids": [sample]}, headers=headers
    )
    assert r.status_code == 200, r.text
    return run_id


def _rows(client, headers, run_id):
    r = client.get(f"/v1/lims-runs/{run_id}/result-entries", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _row_for(rows, analyte_id, replicate=1):
    return next(
        row for row in rows["result_entries"]
        if row["analyte_id"] == analyte_id and row["replicate"] == replicate
    )


def _service(db_session, user):
    return ResultEntryService(db_session, user.id)


def _db_row(db_session, row_id):
    from models.entry import ResultEntry

    db_session.expire_all()
    return db_session.get(ResultEntry, UUID(row_id))


# ---- CALC-REQ-49 / 54: start creates the run's Test and result-entry rows ----


class TestStartCreatesRows:
    def test_start_puts_test_on_run_and_creates_one_row_per_analyte(
        self, client: TestClient, auth_headers, analysis_and_analyte, sample_id,
        template_id, db_session, test_admin_user,
    ):
        from models.entry import Entry
        from models.test import Test

        cfg = _configure(db_session, analysis_and_analyte, test_admin_user.id)
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)

        tests = db_session.query(Test).filter(Test.sample_id == UUID(sample_id)).all()
        assert [str(t.lims_run_id) for t in tests] == [run_id]

        entry = db_session.query(Entry).filter(Entry.lims_run_id == UUID(run_id)).one()
        assert entry.experiment_id is None
        assert entry.entry_type == RESULTS_ENTRY_TYPE == "experiment_sample_data"
        assert entry.predefined_entry_key == RESULTS_ENTRY_KEY
        assert entry.name == "Results"

        body = _rows(client, auth_headers, run_id)
        assert body["total"] == 2
        lead = analysis_and_analyte["lead_id"]
        arsenic = analysis_and_analyte["arsenic_id"]
        keyed = {(r["analyte_id"], r["replicate"]): r for r in body["result_entries"]}
        assert set(keyed) == {(lead, 1), (arsenic, 1)}
        # Ordered by display order: arsenic (1) before lead (2).
        assert [r["analyte_id"] for r in body["result_entries"]] == [arsenic, lead]
        for row in body["result_entries"]:
            assert row["lims_run_id"] == run_id
            assert row["test_id"] == str(tests[0].id)
            assert row["entry_id"] == str(entry.id)
            assert row["raw_result"] is None and row["raw_origin"] is None
            assert row["calculated_result"] is None and row["reported_result"] is None
            assert row["knocked_out"] is False and row["knocked_out_at"] is None
        assert keyed[(lead, 1)]["final_units_id"] == str(cfg["unit_id"])
        assert keyed[(lead, 1)]["display_order"] == 2
        assert keyed[(arsenic, 1)]["final_units_id"] is None

    def test_rows_are_created_once(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        from models.flexible_experiment import LimsRun

        _configure(db_session, analysis_and_analyte, test_admin_user.id)
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        run = db_session.get(LimsRun, UUID(run_id))
        assert _service(db_session, test_admin_user).ensure_rows(run) == 0
        assert _rows(client, auth_headers, run_id)["total"] == 2

    def test_replicate_count_comes_from_the_caller_not_a_column(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        from fastapi import HTTPException

        from models.analysis import AnalysisAnalyte
        from models.flexible_experiment import LimsRun

        assert not hasattr(AnalysisAnalyte, "replicates")
        _configure(db_session, analysis_and_analyte, test_admin_user.id)
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        run = db_session.get(LimsRun, UUID(run_id))
        lead = analysis_and_analyte["lead_id"]
        service = _service(db_session, test_admin_user)
        assert service.ensure_rows(run, {UUID(lead): 3}) == 2
        db_session.commit()
        body = _rows(client, auth_headers, run_id)
        assert sorted(
            r["replicate"] for r in body["result_entries"] if r["analyte_id"] == lead
        ) == [1, 2, 3]
        assert service.ensure_rows(run, {UUID(lead): 3}) == 0
        for bad in (0, -1, True, "2"):
            with pytest.raises(HTTPException) as err:
                service.ensure_rows(run, {UUID(lead): bad})
            assert err.value.status_code == 400
            assert err.value.detail["code"] == "invalid_input"

    def test_unclaimed_test_without_results_is_claimed(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        from models.test import Test

        accessioned = Test(
            name=f"Acc_{uuid4().hex[:8]}",
            sample_id=UUID(sample_id),
            analysis_id=UUID(analysis_and_analyte["analysis_id"]),
            status=scratch_entry_id(db_session),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(accessioned)
        db_session.commit()
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        db_session.expire_all()
        tests = db_session.query(Test).filter(Test.sample_id == UUID(sample_id)).all()
        assert [t.id for t in tests] == [accessioned.id]
        assert str(tests[0].lims_run_id) == run_id

    def test_unclaimed_test_with_results_is_left_and_a_new_test_is_minted(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        from datetime import datetime

        from models.result import Result
        from models.test import Test

        legacy = Test(
            name=f"Legacy_{uuid4().hex[:8]}",
            sample_id=UUID(sample_id),
            analysis_id=UUID(analysis_and_analyte["analysis_id"]),
            status=scratch_entry_id(db_session),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(legacy)
        db_session.flush()
        db_session.add(
            Result(
                test_id=legacy.id,
                analyte_id=UUID(analysis_and_analyte["lead_id"]),
                raw_result="5",
                entry_date=datetime.now(),
                entered_by=test_admin_user.id,
            )
        )
        db_session.commit()
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        db_session.expire_all()
        tests = db_session.query(Test).filter(Test.sample_id == UUID(sample_id)).all()
        assert len(tests) == 2
        by_run = {t.lims_run_id: t for t in tests}
        assert by_run[None].id == legacy.id
        assert by_run[UUID(run_id)].id != legacy.id

    def test_rerun_gets_its_own_test(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        from models.test import Test

        first = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        rerun = client.post(f"/v1/lims-runs/{first}/rerun", headers=auth_headers)
        assert rerun.status_code == 201, rerun.text
        rerun_id = rerun.json()["id"]
        r = client.patch(
            f"/v1/lims-runs/{rerun_id}/start", json={"sample_ids": [sample_id]}, headers=auth_headers
        )
        assert r.status_code == 200, r.text
        tests = db_session.query(Test).filter(Test.sample_id == UUID(sample_id)).all()
        assert sorted(str(t.lims_run_id) for t in tests) == sorted([first, rerun_id])
        first_rows = _rows(client, auth_headers, first)["result_entries"]
        rerun_rows = _rows(client, auth_headers, rerun_id)["result_entries"]
        assert {r["test_id"] for r in first_rows}.isdisjoint({r["test_id"] for r in rerun_rows})

    def test_list_pages(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id,
        db_session, test_admin_user,
    ):
        _configure(db_session, analysis_and_analyte, test_admin_user.id)
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        r = client.get(
            f"/v1/lims-runs/{run_id}/result-entries",
            params={"page": 2, "size": 1},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert (body["total"], body["page"], body["size"], body["pages"]) == (2, 2, 1, 2)
        assert len(body["result_entries"]) == 1
        missing = client.get(f"/v1/lims-runs/{uuid4()}/result-entries", headers=auth_headers)
        assert missing.status_code == 404


# ---- CALC-REQ-49: raw, calculated, reported rules on PATCH ----


class TestResultEntryEdits:
    @pytest.fixture
    def run_row(self, client, auth_headers, analysis_and_analyte, sample_id, template_id):
        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        row = _row_for(_rows(client, auth_headers, run_id), analysis_and_analyte["lead_id"])
        return run_id, row["id"]

    def _patch(self, client, headers, run_id, row_id, body):
        return client.patch(
            f"/v1/lims-runs/{run_id}/result-entries/{row_id}", json=body, headers=headers
        )

    def test_typed_raw_is_stored_with_origin_and_units(self, client, auth_headers, run_row):
        run_id, row_id = run_row
        r = self._patch(client, auth_headers, run_id, row_id, {"raw_result": "12.30", "raw_units": "ug/L"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert (body["raw_result"], body["raw_units"], body["raw_origin"]) == ("12.30", "ug/L", "typed")
        assert body["calculated_result"] is None

        corrected = self._patch(client, auth_headers, run_id, row_id, {"raw_result": "12.4"})
        assert corrected.status_code == 200, corrected.text
        assert (corrected.json()["raw_result"], corrected.json()["raw_units"]) == ("12.4", "ug/L")

        cleared = self._patch(client, auth_headers, run_id, row_id, {"raw_result": "  "})
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["raw_result"] is None
        assert cleared.json()["raw_units"] is None
        assert cleared.json()["raw_origin"] is None

    def test_blank_raw_units_is_stored_as_null(self, client, auth_headers, run_row):
        run_id, row_id = run_row
        r = self._patch(client, auth_headers, run_id, row_id, {"raw_result": "1", "raw_units": ""})
        assert r.status_code == 200, r.text
        assert r.json()["raw_units"] is None

    @pytest.mark.parametrize(
        "body, code",
        [
            ({"calculated_result": "1"}, "calculated_locked"),
            ({"calculated_result": None}, "calculated_locked"),
            ({"raw_result": "1", "calculated_result": "1"}, "calculated_locked"),
            ({"knocked_out": True}, "invalid_input"),
            ({"final_units_id": str(uuid4())}, "invalid_input"),
            ({"raw_result": "1", "extra": 1}, "invalid_input"),
            ({}, "invalid_input"),
            ({"raw_result": 12.3}, "invalid_input"),
            ({"raw_result": "x" * 256}, "invalid_input"),
            ({"raw_units": "ug/L"}, "invalid_input"),
            ({"reported_result": "5"}, "reported_before_calculation"),
            ({"reported_result": None}, "invalid_input"),
            ({"reported_result": " "}, "invalid_input"),
        ],
    )
    def test_refusals_are_400_with_a_code(self, client, auth_headers, run_row, body, code, db_session):
        run_id, row_id = run_row
        r = self._patch(client, auth_headers, run_id, row_id, body)
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == code
        row = _db_row(db_session, row_id)
        assert row.raw_result is None and row.calculated_result is None and row.reported_result is None

    def test_uploaded_raw_cannot_be_edited(self, client, auth_headers, run_row, db_session, test_admin_user):
        run_id, row_id = run_row
        service = _service(db_session, test_admin_user)
        service.record_uploaded_raw(_db_row(db_session, row_id), "7.5", "ng/mL")
        db_session.commit()
        for body in ({"raw_result": "8"}, {"raw_units": "ug/L"}, {"raw_result": None}):
            r = self._patch(client, auth_headers, run_id, row_id, body)
            assert r.status_code == 400, r.text
            assert r.json()["detail"]["code"] == "raw_uploaded"
        row = _db_row(db_session, row_id)
        assert (row.raw_result, row.raw_units, row.raw_origin) == ("7.5", "ng/mL", "upload")

    def test_reported_override_after_calculation_keeps_calculated(
        self, client, auth_headers, run_row, db_session, test_admin_user
    ):
        run_id, row_id = run_row
        assert self._patch(client, auth_headers, run_id, row_id, {"raw_result": "12.30"}).status_code == 200
        service = _service(db_session, test_admin_user)
        row = _db_row(db_session, row_id)
        stage = copy_raw(row.raw_result)
        service.write_calculation(row, stage.outputs["calculated"], stage.outputs["reported"])
        db_session.commit()

        r = self._patch(client, auth_headers, run_id, row_id, {"reported_result": "12"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert (body["raw_result"], body["calculated_result"], body["reported_result"]) == ("12.30", "12.30", "12")

        refused = self._patch(client, auth_headers, run_id, row_id, {"calculated_result": "13"})
        assert refused.status_code == 400
        assert _db_row(db_session, row_id).calculated_result == "12.30"

    def test_published_run_refuses_edits(self, client, auth_headers, run_row, db_session):
        from models.flexible_experiment import LimsRun, LimsRunStatus

        run_id, row_id = run_row
        run = db_session.get(LimsRun, UUID(run_id))
        run.status = LimsRunStatus.published
        db_session.commit()
        r = self._patch(client, auth_headers, run_id, row_id, {"raw_result": "1"})
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "run_published"

    def test_row_on_another_run_is_404(
        self, client, auth_headers, run_row, analysis_and_analyte, template_id, db_session, test_admin_user
    ):
        from models.project import Project
        from models.sample import Sample

        run_id, row_id = run_row
        sample = db_session.query(Sample).join(Project).first()
        other_sample = Sample(
            name=f"S6-other {uuid4().hex[:6]}",
            sample_type=sample.sample_type,
            status=sample.status,
            matrix=sample.matrix,
            project_id=sample.project_id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(other_sample)
        db_session.commit()
        other_run = _started_run(
            client, auth_headers, analysis_and_analyte, template_id, str(other_sample.id)
        )
        r = self._patch(client, auth_headers, other_run, row_id, {"raw_result": "1"})
        assert r.status_code == 404

    def test_list_needs_result_read(self, client, run_row, test_user):
        run_id, _ = run_row
        login = client.post("/auth/login", json={"username": test_user.username, "password": "testpassword"})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = client.get(f"/v1/lims-runs/{run_id}/result-entries", headers=headers)
        assert r.status_code == 403


# ---- copy_raw through the KAT harness, then into storage ----


def test_copy_raw_kats_pass_and_its_outputs_store_exactly(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, test_admin_user
):
    log = run_kats([COPY_RAW_V1], health=_health())
    assert log.cases and all(case.passed for case in log.cases), log.to_dict()

    run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
    row_id = _row_for(_rows(client, auth_headers, run_id), analysis_and_analyte["lead_id"])["id"]
    service = _service(db_session, test_admin_user)
    for raw in ("0.000123", "12.30", "-4", "1E+3"):
        row = _db_row(db_session, row_id)
        service.record_uploaded_raw(row, raw, None)
        stage = copy_raw(row.raw_result)
        assert stage.outputs == {"calculated": raw, "reported": raw}
        service.write_calculation(row, stage.outputs["calculated"], stage.outputs["reported"])
        db_session.commit()
        stored = _row_for(_rows(client, auth_headers, run_id), analysis_and_analyte["lead_id"])
        assert (stored["raw_result"], stored["calculated_result"], stored["reported_result"]) == (raw, raw, raw)


def test_copy_raw_missing_input_leaves_outputs_empty():
    stage = copy_raw(None)
    assert stage.outputs == {}
    assert "missing_input" in stage.flags


# ---- results API: calculated is never accepted; results need a run Test ----


class TestResultsApi:
    @pytest.fixture
    def run_test(self, client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session):
        from models.test import Test

        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        test = db_session.query(Test).filter(Test.lims_run_id == UUID(run_id)).one()
        return run_id, test

    def _body(self, test, analyte_id, user, **extra):
        body = {
            "test_id": str(test.id),
            "analyte_id": analyte_id,
            "raw_result": "1.5",
            "entry_date": "2024-01-01T00:00:00Z",
            "entered_by": str(user.id),
        }
        body.update(extra)
        return body

    def test_create_on_run_test_reports_the_run(self, client, auth_headers, run_test, analysis_and_analyte, test_admin_user):
        run_id, test = run_test
        r = client.post("/results/", json=self._body(test, analysis_and_analyte["lead_id"], test_admin_user), headers=auth_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["lims_run_id"] == run_id
        assert body["calculated_result"] is None
        assert body["knocked_out"] is False
        assert body["raw_units"] is None and body["final_units_id"] is None

    def test_create_with_calculated_is_refused(self, client, auth_headers, run_test, analysis_and_analyte, test_admin_user):
        _, test = run_test
        r = client.post(
            "/results/",
            json=self._body(test, analysis_and_analyte["lead_id"], test_admin_user, calculated_result="2"),
            headers=auth_headers,
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "calculated_locked"

    def test_patch_calculated_is_refused(self, client, auth_headers, run_test, analysis_and_analyte, test_admin_user):
        _, test = run_test
        created = client.post("/results/", json=self._body(test, analysis_and_analyte["lead_id"], test_admin_user), headers=auth_headers)
        result_id = created.json()["id"]
        for value in ("2", None):
            r = client.patch(f"/results/{result_id}", json={"calculated_result": value}, headers=auth_headers)
            assert r.status_code == 400, r.text
            assert r.json()["detail"]["code"] == "calculated_locked"
        ok = client.patch(f"/results/{result_id}", json={"raw_result": "1.6"}, headers=auth_headers)
        assert ok.status_code == 200, ok.text
        assert ok.json()["raw_result"] == "1.6"

    def test_run_less_test_is_refused(self, client, auth_headers, analysis_and_analyte, sample_id, db_session, test_admin_user):
        from models.test import Test

        test = Test(
            name=f"NoRun_{uuid4().hex[:8]}",
            sample_id=UUID(sample_id),
            analysis_id=UUID(analysis_and_analyte["analysis_id"]),
            status=scratch_entry_id(db_session),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
        )
        db_session.add(test)
        db_session.commit()
        r = client.post("/results/", json=self._body(test, analysis_and_analyte["lead_id"], test_admin_user), headers=auth_headers)
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "result_test_has_no_run"

    def test_test_response_carries_the_run(self, client, auth_headers, run_test):
        run_id, test = run_test
        r = client.get(f"/tests/{test.id}", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["lims_run_id"] == run_id

    def test_publish_writes_results_on_the_run_test(
        self, client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session
    ):
        from models.result import Result
        from models.test import Test

        run_id = _started_run(client, auth_headers, analysis_and_analyte, template_id, sample_id)
        r = client.post(
            f"/v1/lims-runs/{run_id}/import",
            json={"rows": [{"sample_id": sample_id, "well_position": "A1", "row_data": {"Pb_ug_L": "3.3"}}]},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert client.patch(f"/v1/lims-runs/{run_id}/review", headers=auth_headers).status_code == 200
        r = client.patch(f"/v1/lims-runs/{run_id}/complete", headers=auth_headers)
        assert r.status_code == 200, r.text
        db_session.expire_all()
        test = db_session.query(Test).filter(Test.lims_run_id == UUID(run_id)).one()
        results = db_session.query(Result).filter(Result.test_id == test.id).all()
        assert [(res.raw_result, res.lims_run_id) for res in results] == [("3.3", UUID(run_id))]


# ---- OQ-36 / CALC-REQ-28: pairing unit on the analysis analyte ----


class TestAnalyteRules:
    def _analysis(self, db_session, user_id, unit_id=None):
        from models.analysis import Analysis, Analyte

        analysis = Analysis(name=f"S6A {uuid4().hex[:6]}", created_by=user_id, modified_by=user_id)
        analyte = Analyte(
            name=f"S6An {uuid4().hex[:6]}", units_default=unit_id, created_by=user_id, modified_by=user_id
        )
        db_session.add_all([analysis, analyte])
        db_session.commit()
        return analysis, analyte

    def test_rule_create_defaults_pairing_unit_to_the_analyte_default(
        self, client, auth_headers, db_session, test_admin_user
    ):
        unit_id = _unit(db_session, test_admin_user.id)
        analysis, analyte = self._analysis(db_session, test_admin_user.id, unit_id)
        r = client.post(
            f"/analyses/{analysis.id}/analyte-rules",
            json={"analyte_id": str(analyte.id)},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["pairing_unit_id"] == str(unit_id)
        assert "replicates" not in r.json()

    def test_rule_create_takes_explicit_pairing_unit(
        self, client, auth_headers, db_session, test_admin_user
    ):
        default_unit = _unit(db_session, test_admin_user.id)
        chosen = _unit(db_session, test_admin_user.id)
        analysis, analyte = self._analysis(db_session, test_admin_user.id, default_unit)
        r = client.post(
            f"/analyses/{analysis.id}/analyte-rules",
            json={"analyte_id": str(analyte.id), "pairing_unit_id": str(chosen)},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["pairing_unit_id"] == str(chosen)

    def test_link_defaults_pairing_unit(self, client, auth_headers, db_session, test_admin_user):
        from models.analysis import AnalysisAnalyte

        unit_id = _unit(db_session, test_admin_user.id)
        analysis, analyte = self._analysis(db_session, test_admin_user.id, unit_id)
        r = client.post(
            f"/analyses/{analysis.id}/analytes",
            json={"analyte_ids": [str(analyte.id)]},
            headers=auth_headers,
        )
        assert r.status_code in (200, 201), r.text
        db_session.expire_all()
        link = db_session.query(AnalysisAnalyte).filter_by(analysis_id=analysis.id, analyte_id=analyte.id).one()
        assert link.pairing_unit_id == unit_id

    def test_patch_pairing_unit(self, client, auth_headers, db_session, test_admin_user):
        analysis, analyte = self._analysis(db_session, test_admin_user.id)
        assert client.post(
            f"/analyses/{analysis.id}/analyte-rules", json={"analyte_id": str(analyte.id)}, headers=auth_headers
        ).status_code == 201
        unit_id = _unit(db_session, test_admin_user.id)
        db_session.commit()
        url = f"/analyses/{analysis.id}/analyte-rules/{analyte.id}"
        r = client.patch(url, json={"pairing_unit_id": str(unit_id)}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["pairing_unit_id"] == str(unit_id)
        bad = client.patch(url, json={"pairing_unit_id": str(uuid4())}, headers=auth_headers)
        assert bad.status_code == 400, bad.text
        cleared = client.patch(url, json={"pairing_unit_id": None}, headers=auth_headers)
        assert cleared.status_code == 200 and cleared.json()["pairing_unit_id"] is None
