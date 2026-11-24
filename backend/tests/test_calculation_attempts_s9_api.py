"""Calculations S9: calculate a result-entry row, record the attempt, run test
cases and dry runs (API and service level).

Runs on the ``create_all`` schema, so the database triggers of 0127 are not
present; the services' own checks are what these tests exercise. The R client
is a stub behind the ``calculation_r_client`` dependency: ``/health`` reports
the lock hash recomputed from this commit, so the gate accepts the call unless
a test changes the body. The triggers, privileges, row-level security, and
downgrade are in ``test_calculation_attempts_s9_db.py``.

CALC-REQ-49 AC: ``copy_raw`` writes ``0.026`` to both; a first calculation
that stops with ``r_timeout`` clears both. CALC-REQ-30 AC: the attempt shows
versions, lock hash, digest, values, and knockouts; the lock hash matches
``/health``. CALC-REQ-25: a refusal before acceptance is HTTP 400 and writes no
attempt; a stage stop is HTTP 200.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.services.calculation_attempt_service import calculation_r_client
from app.services.calculation_runtime import CalculationCallRefused
from app.services.configuring_agent_allow import classify_call
from tests.test_calculation_activation_s8_api import _activate, _issue, _review
from tests.test_calculation_catalog_decimal_s4 import DIGEST, _health
from tests.test_calculation_config_s7 import declare, field
from tests.test_calculation_config_s7_api import (  # noqa: F401  (fixtures)
    _body,
    _code,
    _url,
    manager_headers,
    plain_headers,
)
from tests.test_calculation_result_entry_s6 import _db_row, _row_for, _rows, _started_run
from tests.test_result_promotion import (  # noqa: F401  (fixtures)
    analysis_and_analyte,
    auth_headers,
    sample_id,
    template_id,
)

RAW = {"kind": "run_field", "entry_type": "experiment_sample_data", "field_name": "raw_result"}


class StubClient:
    """Stands in for ``RCalculatorClient``: a ``/health`` body and recorded R calls."""

    def __init__(self, health: Optional[Dict[str, Any]] = None, reply: Optional[Callable[[str, dict], Any]] = None) -> None:
        self.health = health if health is not None else _health()
        self.reply = reply
        self.calls: list = []
        self.health_reads = 0

    def fetch_health_body(self) -> Dict[str, Any]:
        self.health_reads += 1
        return self.health

    def execute_calculation_request(self, path: str, payload: dict) -> Any:
        self.calls.append((path, payload))
        if self.reply is None:
            pytest.fail(f"unexpected R call {path}")
        return self.reply(path, payload)


@pytest.fixture
def r_stub():
    stub = StubClient()
    app.dependency_overrides[calculation_r_client] = lambda: stub
    yield stub
    app.dependency_overrides.pop(calculation_r_client, None)


def _copy_raw(stage_id: str = "copy", **on_fail: Any) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "kind": "catalog_function",
        "function": "copy_raw",
        "function_version": 1,
        "bindings": {"value": dict(RAW)},
        "on_fail": declare(**on_fail),
    }


def _cfg(*stages: Dict[str, Any], result: Dict[str, str], name: str = "cfg") -> Dict[str, Any]:
    return {"name": name, "stages": list(stages), "result": result}


COPY_RAW_CFG = _cfg(_copy_raw(), result={"stage": "copy", "output": "calculated"}, name="Lead copy")


def _inverse_then_copy() -> Dict[str, Any]:
    inverse = {
        "id": "inv",
        "kind": "catalog_function",
        "function": "inverse_4pl",
        "function_version": 1,
        "bindings": {
            "bottom": {"kind": "direct", "value": "0.05"},
            "top": {"kind": "direct", "value": "2.5"},
            "slope": {"kind": "direct", "value": "1.5"},
            "inflection": {"kind": "direct", "value": "40"},
            "response": dict(RAW),
            "low_calibrator_mean_response": {"kind": "direct", "value": "0.1"},
            "high_calibrator_mean_response": {"kind": "direct", "value": "2.4"},
        },
        "on_fail": declare(outcome="r_timeout", precedence_place="above_list"),
    }
    after = {
        "id": "after",
        "kind": "catalog_function",
        "function": "copy_raw",
        "function_version": 1,
        "bindings": {"value": {"kind": "stage_output", "stage": "inv", "output": "concentration"}},
        "on_fail": declare(),
    }
    return _cfg(inverse, after, result={"stage": "after", "output": "calculated"}, name="Lead 4PL")


def _put(client, headers, ids, configuration, order=1, analyte="lead_id"):
    r = client.put(_url(ids, analyte), headers=headers, json=_body(configuration, order))
    assert r.status_code == 200, r.text
    return r.json()


def _activated(client, headers, ids, configuration, order=1, analyte="lead_id"):
    _put(client, headers, ids, configuration, order, analyte)
    token = _issue(client, headers, ids, analyte)
    r = _activate(client, headers, ids, token, analyte)
    assert r.status_code == 200, r.text


def _run_with_raw(client, headers, ids, template, sample, raw: Optional[Dict[str, str]] = None) -> tuple[str, Dict[str, Any]]:
    run_id = _started_run(client, headers, ids, template, sample)
    rows = _rows(client, headers, run_id)
    found = {key: _row_for(rows, ids[key]) for key in ("lead_id", "arsenic_id")}
    for key, value in (raw or {}).items():
        r = client.patch(
            f"/v1/lims-runs/{run_id}/result-entries/{found[key]['id']}",
            headers=headers,
            json={"raw_result": value},
        )
        assert r.status_code == 200, r.text
    return run_id, found


def _calculate(client, headers, run_id, row_id):
    return client.post(f"/v1/lims-runs/{run_id}/result-entries/{row_id}/calculate", headers=headers)


def _counts(db_session) -> Dict[str, int]:
    return {
        table: db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in ("calculation_attempts", "calculation_test_case_results", "calculation_dry_runs", "results")
    }


# ---- CALC-REQ-49 / 53: the first calculation write ----------------------------------------------


def test_copy_raw_writes_0_026_to_calculated_and_reported_and_links_the_attempt(
    client: TestClient, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    lead = rows["lead_id"]

    r = _calculate(client, auth_headers, run_id, lead["id"])
    assert r.status_code == 200, r.text
    body = r.json()
    attempt, row = body["attempt"], body["result_entry"]
    assert (row["calculated_result"], row["reported_result"]) == ("0.026", "0.026")
    assert row["raw_result"] == "0.026"
    assert row["calculation_attempt_id"] == attempt["id"]
    assert attempt["status"] == "completed"
    assert (attempt["calculated_result"], attempt["reported_result"]) == ("0.026", "0.026")
    assert attempt["run_summary"] == "pass" and attempt["summary_check"] is None

    # CALC-REQ-30: the attempt's provenance.
    assert attempt["lock_hash"] == r_stub.health["lock_hash"]
    assert attempt["built_image_digest"] == DIGEST == r_stub.health["R_IMAGE_DIGEST"]
    assert attempt["configuration_name"] == "Lead copy"
    assert attempt["configuration_version"] >= 1
    assert attempt["analysis_version"] >= 1
    assert attempt["function_versions"] == [{"stage": "copy", "function": "copy_raw", "version": 1}]
    assert attempt["inputs_read"] == [
        {
            "stage": "copy",
            "input": "value",
            "kind": "run_field",
            "entry_id": lead["entry_id"],
            "record_id": lead["id"],
            "field": "raw_result",
            "value": "0.026",
            "units": None,
        }
    ]
    assert attempt["values_used"] == [{"stage": "copy", "input": "value", "kind": "run_field", "value": "0.026"}]
    assert attempt["knocked_out_points"] == []
    assert (attempt["test_id"], attempt["analyte_id"], attempt["lims_run_id"]) == (lead["test_id"], ids["lead_id"], run_id)
    assert attempt["analysis_id"] == ids["analysis_id"]
    assert r_stub.health_reads == 1 and r_stub.calls == []

    stored = _db_row(db_session, lead["id"])
    assert stored.calculated_result == "0.026" and str(stored.calculation_attempt_id) == attempt["id"]
    assert _counts(db_session)["results"] == 0, "a calculation writes no official result"

    listed = client.get(f"/v1/lims-runs/{run_id}/result-entries/{lead['id']}/calculation-attempts", headers=auth_headers)
    assert listed.status_code == 200
    assert [a["id"] for a in listed.json()] == [attempt["id"]]
    assert _row_for(_rows(client, auth_headers, run_id), ids["lead_id"])["calculation_attempt_id"] == attempt["id"]


def test_reported_can_be_overwritten_after_the_calculation_wrote_it(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    assert _calculate(client, auth_headers, run_id, rows["lead_id"]["id"]).status_code == 200
    r = client.patch(
        f"/v1/lims-runs/{run_id}/result-entries/{rows['lead_id']['id']}",
        headers=auth_headers,
        json={"reported_result": "0.03"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["calculated_result"] == "0.026" and r.json()["reported_result"] == "0.03"


def test_a_first_calculation_that_stops_with_r_timeout_clears_both_and_is_200(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte

    def timeout(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused("r_timeout", "R stopped the request after 50 s")

    r_stub.reply = timeout
    _activated(client, auth_headers, ids, _inverse_then_copy())
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "1.0"})

    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200, r.text
    attempt, row = r.json()["attempt"], r.json()["result_entry"]
    assert attempt["status"] == "stopped"
    assert (attempt["stop_code"], attempt["stop_stage"]) == ("r_timeout", "inv")
    assert (attempt["run_summary"], attempt["summary_check"], attempt["summary_code"]) == ("stopped", "inv", "r_timeout")
    assert row["calculated_result"] is None and row["reported_result"] is None
    assert row["calculation_attempt_id"] == attempt["id"]
    assert [s["status"] for s in attempt["stages"]] == ["stopped", "not_reached"]
    assert [path for path, _ in r_stub.calls] == ["/catalog/inverse_4pl/v1"]
    assert attempt["function_versions"][0]["route"] == "/catalog/inverse_4pl/v1"
    assert {"stage": "inv", "input": "slope", "kind": "direct", "value": "1.5"} in attempt["values_used"]
    assert _counts(db_session)["calculation_attempts"] == 1


def test_a_backend_timeout_is_also_a_recorded_stop(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte

    def timeout(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused("backend_timeout", "backend stopped waiting after 60 s")

    r_stub.reply = timeout
    _activated(client, auth_headers, ids, _inverse_then_copy())
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "1.0"})
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200
    assert r.json()["attempt"]["stop_code"] == "backend_timeout"


def test_an_r_value_feeds_the_next_stage_and_is_written(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte
    r_stub.reply = lambda _path, _payload: {"concentration": "12.5"}
    _activated(client, auth_headers, ids, _inverse_then_copy())
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "1.0"})
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200, r.text
    assert r.json()["result_entry"]["calculated_result"] == "12.5"
    assert r_stub.calls[0][1]["response"] == "1.0"


# ---- refusals before acceptance: HTTP 400, nothing written ---------------------------------------


def _refused_nothing_written(r, code: str, db_session, before: Dict[str, int], row_id: str) -> None:
    assert r.status_code == 400, r.text
    assert _code(r) == code
    assert _counts(db_session) == before
    row = _db_row(db_session, row_id)
    assert row.calculation_attempt_id is None and row.calculated_result is None


def test_a_draft_configuration_is_not_run(client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    _refused_nothing_written(r, "configuration_not_active", db_session, before, rows["lead_id"]["id"])
    assert r_stub.health_reads == 0


def test_an_analyte_with_no_configuration_is_refused(client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub):
    ids = analysis_and_analyte
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"arsenic_id": "1"})
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["arsenic_id"]["id"])
    _refused_nothing_written(r, "configuration_not_active", db_session, before, rows["arsenic_id"]["id"])


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda h: h.update(lock_hash="0" * 64), "lock_mismatch"),
        (lambda h: h.pop("lock_hash"), "lock_hash"),
        (lambda h: h.update(R_IMAGE_DIGEST=""), "missing_digest"),
        (lambda h: h["sandbox"].update(egress_blocked=False), "sandbox"),
    ],
)
def test_a_lock_or_sandbox_refusal_writes_no_attempt(
    change, code, client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    change(r_stub.health)
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    _refused_nothing_written(r, code, db_session, before, rows["lead_id"]["id"])


def test_an_r_refusal_mid_run_that_is_not_a_timeout_writes_nothing(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte

    def refused(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused("r_service", "calculation call refused: R service error (500)")

    r_stub.reply = refused
    _activated(client, auth_headers, ids, _inverse_then_copy())
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "1.0"})
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    _refused_nothing_written(r, "r_service", db_session, before, rows["lead_id"]["id"])


def test_a_row_is_calculated_once_in_s9(client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    assert _calculate(client, auth_headers, run_id, rows["lead_id"]["id"]).status_code == 200
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 400 and _code(r) == "already_calculated"
    assert _counts(db_session) == before


def test_a_knocked_out_row_is_not_calculated(client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub, test_admin_user):
    from datetime import datetime, timezone

    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    row = _db_row(db_session, rows["lead_id"]["id"])
    row.knocked_out = True
    row.knocked_out_by = test_admin_user.id
    row.knocked_out_at = datetime.now(timezone.utc)
    db_session.commit()
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 400 and _code(r) == "row_knocked_out"
    assert _counts(db_session) == before


def test_a_published_run_is_not_calculated(client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub):
    from models.flexible_experiment import LimsRun, LimsRunStatus

    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    run = db_session.get(LimsRun, UUID(run_id))
    run.status = LimsRunStatus.published
    db_session.commit()
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 400 and _code(r) == "run_published"
    assert _counts(db_session) == before


def test_a_run_field_s9_cannot_read_is_refused_before_the_call(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte
    other = _cfg(
        {**_copy_raw(), "bindings": {"value": field("OD 450")}},
        result={"stage": "copy", "output": "calculated"},
    )
    _activated(client, auth_headers, ids, other)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    _refused_nothing_written(r, "binding_not_readable", db_session, before, rows["lead_id"]["id"])
    assert r.json()["detail"]["stage"] == "copy"
    assert r_stub.health_reads == 0


def test_raw_units_that_differ_from_the_pairing_unit_are_refused_for_copy_raw(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "26"})
    r = client.patch(
        f"/v1/lims-runs/{run_id}/result-entries/{rows['lead_id']['id']}",
        headers=auth_headers,
        json={"raw_units": "ug/mL"},
    )
    assert r.status_code == 200, r.text
    before = _counts(db_session)
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    _refused_nothing_written(r, "raw_units_differ", db_session, before, rows["lead_id"]["id"])
    assert "OQ-CALC-39" in r.json()["detail"]["message"]


def test_calculating_needs_result_enter_not_configuration_rights(
    client, auth_headers, plain_headers, manager_headers, analysis_and_analyte, sample_id, template_id, db_session, r_stub
):
    ids = analysis_and_analyte
    _activated(client, auth_headers, ids, COPY_RAW_CFG)
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "0.026"})
    r = _calculate(client, manager_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 403
    assert _counts(db_session)["calculation_attempts"] == 0
    r = _calculate(client, plain_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200, r.text
    assert r.json()["attempt"]["created_by"] is not None


# ---- references (CALC-REQ-58: a metadata analyte is read as an analyte) ----------------------------


def _subtract_reference(ids) -> Dict[str, Any]:
    stage = {
        "id": "net",
        "kind": "catalog_function",
        "function": "subtract",
        "function_version": 1,
        "bindings": {
            "minuend": dict(RAW),
            "subtrahend": {"kind": "reference", "analyte_id": ids["arsenic_id"], "value": "calculated"},
        },
        "on_fail": declare(),
    }
    return _cfg(stage, result={"stage": "net", "output": "difference"}, name="Lead net")


def _two_analytes(client, headers, ids, arsenic_cfg: Dict[str, Any]) -> None:
    _activated(client, headers, ids, arsenic_cfg, order=1, analyte="arsenic_id")
    _activated(client, headers, ids, _subtract_reference(ids), order=2, analyte="lead_id")


def test_a_reference_to_an_analyte_on_the_same_test_is_read_and_recorded(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte
    _two_analytes(client, auth_headers, ids, _cfg(_copy_raw(), result={"stage": "copy", "output": "calculated"}))
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "5", "arsenic_id": "1.5"})
    first = _calculate(client, auth_headers, run_id, rows["arsenic_id"]["id"])
    assert first.status_code == 200, first.text
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200, r.text
    attempt = r.json()["attempt"]
    assert r.json()["result_entry"]["calculated_result"] == "3.5"
    reference = next(item for item in attempt["inputs_read"] if item["kind"] == "reference")
    assert reference["record_id"] == rows["arsenic_id"]["id"]
    assert reference["analyte_id"] == ids["arsenic_id"]
    assert reference["value"] == "1.5"
    assert reference["attempt_id"] == first.json()["attempt"]["id"]


def test_a_reference_not_calculated_yet_stops_reference_missing(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte
    _two_analytes(client, auth_headers, ids, _cfg(_copy_raw(), result={"stage": "copy", "output": "calculated"}))
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "5", "arsenic_id": "1.5"})
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.status_code == 200, r.text
    attempt = r.json()["attempt"]
    assert (attempt["status"], attempt["stop_code"], attempt["stop_stage"]) == ("stopped", "reference_missing", "net")
    assert r.json()["result_entry"]["calculated_result"] is None


def test_a_reference_whose_calculation_stopped_stops_reference_stopped(
    client, auth_headers, analysis_and_analyte, sample_id, template_id, r_stub
):
    ids = analysis_and_analyte
    divide = {
        "id": "calc",
        "kind": "ad_hoc_formula",
        "formula_text": "x / y",
        "bindings": {"x": dict(RAW), "y": {"kind": "direct", "value": "0"}},
        "on_fail": declare(),
    }
    _two_analytes(client, auth_headers, ids, _cfg(divide, result={"stage": "calc", "output": "result"}))
    run_id, rows = _run_with_raw(client, auth_headers, ids, template_id, sample_id, {"lead_id": "5", "arsenic_id": "1.5"})
    first = _calculate(client, auth_headers, run_id, rows["arsenic_id"]["id"])
    assert first.status_code == 200
    assert (first.json()["attempt"]["formula_error"], first.json()["attempt"]["stop_code"]) == ("#DIV/0!", None)
    assert first.json()["attempt"]["summary_code"] == "#DIV/0!"
    r = _calculate(client, auth_headers, run_id, rows["lead_id"]["id"])
    assert r.json()["attempt"]["stop_code"] == "reference_stopped"


# ---- test cases and dry runs (S8 tables, S9 runner) --------------------------------------------


def _case(client, headers, ids, name: str, inputs: Dict[str, Any], expected: Dict[str, Any], analyte: str = "lead_id"):
    r = client.post(
        _url(ids, analyte, "calculation-config/test-cases"),
        headers=headers,
        json={"name": name, "inputs": inputs, "expected": expected, "expected_source": "independent"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _run_cases(client, headers, ids, analyte: str = "lead_id"):
    return client.post(_url(ids, analyte, "calculation-config/test-cases/run"), headers=headers)


def test_running_test_cases_records_outcomes_and_the_review_reads_them(
    client, auth_headers, analysis_and_analyte, db_session, r_stub
):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    good = _case(client, auth_headers, ids, "copies", {"raw_result": "0.026"}, {"calculated": "0.026", "reported": "0.026"})
    tolerant = _case(client, auth_headers, ids, "within", {"raw_result": "0.0261"}, {"calculated": "0.026", "tolerance": "0.0002"})
    bad = _case(client, auth_headers, ids, "wrong", {"raw_result": "0.5"}, {"calculated": "0.6"})
    unread = _case(client, auth_headers, ids, "unreadable", {"raw_result": "1"}, {"answer": "1"})

    r = _run_cases(client, auth_headers, ids)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["total"], body["run"], body["passed"]) == (4, 3, 2)
    assert body["lock_hash"] == r_stub.health["lock_hash"] and body["built_image_digest"] == DIGEST
    states = {case["name"]: case["state"] for case in body["cases"]}
    assert states == {"copies": "passed", "within": "passed", "wrong": "failed", "unreadable": "not_run"}
    assert body["live_refusal"] is None

    from models.calculation import CalculationTestCaseResult

    db_session.expire_all()
    recorded = {str(row.test_case_id): row for row in db_session.query(CalculationTestCaseResult).all()}
    assert set(recorded) == {good["id"], tolerant["id"], bad["id"]}
    assert unread["id"] not in recorded
    assert recorded[good["id"]].passed is True and recorded[bad["id"]].passed is False
    assert recorded[good["id"]].lock_hash == r_stub.health["lock_hash"]
    assert recorded[good["id"]].built_image_digest == DIGEST
    assert recorded[bad["id"]].outcome["checks"][0] == {"check": "calculated", "expected": "0.6", "actual": "0.5", "passed": False}

    review = _review(client, auth_headers, ids)["document"]
    assert review["validation_state"] == "tests_some_passed"
    assert review["test_cases"]["passed_on_current_lock"] == 2
    assert _counts(db_session)["calculation_attempts"] == 0, "a test case writes no attempt"


def test_test_cases_check_stops_and_flags(client, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    divide = {
        "id": "calc",
        "kind": "ad_hoc_formula",
        "formula_text": "x / y",
        "bindings": {"x": field("OD 450"), "y": field("Blank")},
        "on_fail": declare(),
    }
    _put(client, auth_headers, ids, _cfg(divide, result={"stage": "calc", "output": "result"}))
    _case(client, auth_headers, ids, "div0", {"OD 450": "1", "Blank": "0"}, {"status": "stopped", "formula_error": "#DIV/0!", "calculated": None})
    _case(client, auth_headers, ids, "missing", {"OD 450": "1"}, {"formula_error": "#N/A", "run_summary": "stopped"})
    _case(client, auth_headers, ids, "knocked", {"OD 450": {"value": "1", "knocked_out": True}, "Blank": "2"}, {"formula_error": "#N/A"})
    _case(client, auth_headers, ids, "ok", {"OD 450": "1", "Blank": "4"}, {"calculated": "0.25", "flags": []})
    body = _run_cases(client, auth_headers, ids).json()
    assert {case["name"]: case["state"] for case in body["cases"]} == {
        "div0": "passed",
        "missing": "passed",
        "knocked": "passed",
        "ok": "passed",
    }
    assert body["live_refusal"]["code"] == "binding_not_readable"


def test_all_test_cases_passing_reaches_all_passed(client, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    _case(client, auth_headers, ids, "copies", {"raw_result": "0.026"}, {"calculated": "0.026"})
    assert _run_cases(client, auth_headers, ids).json()["passed"] == 1
    review = _review(client, auth_headers, ids)["document"]
    assert review["validation_state"] == "tests_all_passed"


def test_a_gate_refusal_records_no_test_case_outcome(client, auth_headers, analysis_and_analyte, db_session, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    _case(client, auth_headers, ids, "copies", {"raw_result": "0.026"}, {"calculated": "0.026"})
    r_stub.health["lock_hash"] = "f" * 64
    r = _run_cases(client, auth_headers, ids)
    assert r.status_code == 400 and _code(r) == "lock_mismatch"
    assert _counts(db_session)["calculation_test_case_results"] == 0


def test_running_test_cases_needs_configuration_permission(client, plain_headers, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    assert _run_cases(client, plain_headers, ids).status_code == 403
    r = client.post(_url(ids, "lead_id", "calculation-config/dry-run"), headers=plain_headers, json={"input": {}})
    assert r.status_code == 403


def test_a_manager_with_config_edit_may_run_test_cases(client, manager_headers, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    assert _run_cases(client, manager_headers, ids).status_code == 200


def test_a_dry_run_is_recorded_and_the_review_shows_it(client, auth_headers, analysis_and_analyte, db_session, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    assert _review(client, auth_headers, ids)["document"]["dry_run"]["done"] is False
    r = client.post(_url(ids, "lead_id", "calculation-config/dry-run"), headers=auth_headers, json={"input": {"raw_result": "0.026"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"]["calculated"] == "0.026" and body["outcome"]["status"] == "completed"
    assert body["lock_hash"] == r_stub.health["lock_hash"] and body["built_image_digest"] == DIGEST
    dry = _review(client, auth_headers, ids)["document"]["dry_run"]
    assert dry["done"] is True and dry["input"] == {"raw_result": "0.026"}
    counts = _counts(db_session)
    assert counts["calculation_dry_runs"] == 1 and counts["calculation_attempts"] == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"input": []},
        {"input": {"raw_result": 0.5}},
        {"input": {"raw_result": True}},
        {"input": {}, "extra": 1},
    ],
)
def test_an_unreadable_dry_run_is_refused_and_records_nothing(body, client, auth_headers, analysis_and_analyte, db_session, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, COPY_RAW_CFG)
    r = client.post(_url(ids, "lead_id", "calculation-config/dry-run"), headers=auth_headers, json=body)
    assert r.status_code == 400 and _code(r) == "dry_run_invalid"
    assert _counts(db_session)["calculation_dry_runs"] == 0


def test_a_dry_run_on_an_analyte_with_no_configuration_is_refused(client, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    r = client.post(_url(ids, "lead_id", "calculation-config/dry-run"), headers=auth_headers, json={"input": {}})
    assert r.status_code == 400 and _code(r) == "configuration_missing"


def test_a_dry_run_of_a_reference_reads_the_inputs_references(client, auth_headers, analysis_and_analyte, r_stub):
    ids = analysis_and_analyte
    _put(client, auth_headers, ids, _cfg(_copy_raw(), result={"stage": "copy", "output": "calculated"}), order=1, analyte="arsenic_id")
    _put(client, auth_headers, ids, _subtract_reference(ids), order=2)
    url = _url(ids, "lead_id", "calculation-config/dry-run")
    ok = client.post(url, headers=auth_headers, json={"input": {"raw_result": "5", "references": {ids["arsenic_id"]: {"calculated": "2"}}}})
    assert ok.json()["outcome"]["calculated"] == "3"
    missing = client.post(url, headers=auth_headers, json={"input": {"raw_result": "5"}})
    assert missing.json()["outcome"]["stop_code"] == "reference_missing"
    stopped = client.post(url, headers=auth_headers, json={"input": {"raw_result": "5", "references": {ids["arsenic_id"]: {"stopped": True}}}})
    assert stopped.json()["outcome"]["stop_code"] == "reference_stopped"


# ---- the configuring agent cannot run anything --------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/v1/lims-runs/r/result-entries/x/calculate",
        "/v1/lims-runs/r/result-entries/x/calculation-attempts",
        "/v1/analyses/a/analytes/b/calculation-config/test-cases/run",
        "/v1/analyses/a/analytes/b/calculation-config/dry-run",
    ],
)
def test_no_s9_route_is_on_the_agent_allow_list(path: str) -> None:
    for method in ("POST", "GET"):
        assert classify_call(method, path, {}).ok is False, (method, path)
