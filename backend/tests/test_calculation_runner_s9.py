"""Calculations S9: the stage runner, on its own (no database).

CALC-REQ-25 (stop rules: each function's stop case leaves dependents not run
and both values cleared), 26 (missing data), 21 (run summary), 48 (on-fail at
run time, gates, precedence), 53 (``copy_raw``), 37 (decimal strings; R only on
its named route), 4a (timeouts are stage stops; other refusals write nothing).
"""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pytest

from app.services.calculation_catalog_decimal import UnitFactor
from app.services.calculation_config import ConfigContext, UnitInfo, parse_config
from app.services.calculation_runner import (
    ATTEMPT_COMPLETED,
    ATTEMPT_STOPPED,
    STAGE_FAILED,
    STAGE_FLAGGED,
    STAGE_GATED,
    STAGE_NOT_REACHED,
    STAGE_QUALIFIED,
    STAGE_SKIPPED,
    SUMMARY_FAIL,
    SUMMARY_PASS,
    SUMMARY_STOPPED,
    UNIT_TYPE_MISMATCH,
    InputRead,
    Knocked,
    PlanRefused,
    ReadStop,
    RunContext,
    RunOutcome,
    prepare_plan,
    run_plan,
)
from app.services.calculation_runtime import CalculationCallRefused
from tests.test_calculation_catalog_r_s3 import FIT_OUT, StubR

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SERVICES = BACKEND / "app" / "services"

S9_FILES = (
    SERVICES / "calculation_runner.py",
    SERVICES / "calculation_attempt_service.py",
    SERVICES / "calculation_test_run_service.py",
)
S9_DOCS = (
    ROOT / "manuals" / "calculation-configuration-s9.md",
    ROOT / "UAT_Scripts" / "uat-calculations-s9.md",
)

ME = "33333333-3333-4333-8333-333333333333"
EARLIER = "44444444-4444-4444-8444-444444444444"
MG_ML = UnitInfo("55555555-5555-4555-8555-555555555555", "mg/mL", "concentration")
G_L = UnitInfo("66666666-6666-4666-8666-666666666666", "g/L", "concentration")
OD = UnitInfo("77777777-7777-4777-8777-777777777777", "OD", "absorbance")
UNITS = {u.id: u for u in (MG_ML, G_L, OD)}
FACTORS = {
    "mg/mL": UnitFactor("mg/mL", "concentration", Decimal("1")),
    "g/L": UnitFactor("g/L", "concentration", Decimal("1")),
    "ug/mL": UnitFactor("ug/mL", "concentration", Decimal("0.001")),
    "OD": UnitFactor("OD", "absorbance", Decimal("1")),
}


# ---- helpers ------------------------------------------------------------------


def field(name: str, **extra: Any) -> Dict[str, Any]:
    return {"kind": "run_field", "entry_type": "experiment_sample_data", "field_name": name, **extra}


def direct(value: str) -> Dict[str, Any]:
    return {"kind": "direct", "value": value}


def out(stage: str, output: str) -> Dict[str, Any]:
    return {"kind": "stage_output", "stage": stage, "output": output}


def declare(outcome: str = "run_failed", place: int = 1, gates: Optional[list] = None, **extra: Any) -> Dict[str, Any]:
    body = {"outcome": outcome, "flag": None, "gates": gates or [], "precedence_place": place}
    body.update(extra)
    return body


def catalog(stage_id: str, function: str, bindings: Dict[str, Any], on_fail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "kind": "catalog_function",
        "function": function,
        "function_version": 1,
        "bindings": bindings,
        "on_fail": on_fail or declare(),
    }


def ad_hoc(stage_id: str, text: str, bindings: Dict[str, Any], on_fail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "kind": "ad_hoc_formula",
        "formula_text": text,
        "bindings": bindings,
        "on_fail": on_fail or declare(),
    }


def stored(*stages: Dict[str, Any], result: Optional[Dict[str, str]] = None, validate: bool = True) -> Dict[str, Any]:
    raw = {"name": "cfg", "stages": list(stages), "result": result or {"stage": stages[-1]["id"], "output": "result"}}
    if not validate:
        return raw
    ctx = ConfigContext(
        analyte_id=ME,
        calculation_order=3,
        analyte_orders={EARLIER: 1},
        units=UNITS,
        saved_formulas={},
    )
    return parse_config(raw, ctx).to_json()


class Reader:
    def __init__(self, fields: Optional[Mapping[str, Any]] = None, refs: Optional[Mapping[str, Any]] = None, units: Optional[Mapping[str, str]] = None) -> None:
        self.fields = dict(fields or {})
        self.refs = dict(refs or {})
        self.units = dict(units or {})

    def read(self, binding: Mapping[str, Any]) -> InputRead:
        if binding["kind"] == "run_field":
            name = binding["field_name"]
            return InputRead(
                self.fields.get(name),
                unit=self.units.get(name),
                sources=({"kind": "run_field", "field": name, "value": self.fields.get(name)},),
            )
        ref = self.refs.get(binding["analyte_id"])
        if isinstance(ref, ReadStop):
            raise ref
        if ref is None:
            raise ReadStop("reference_missing", "no row")
        return InputRead(ref, sources=({"kind": "reference", "analyte_id": binding["analyte_id"], "value": ref},))


def run(config: Dict[str, Any], reader: Optional[Reader] = None, r: Any = None, pairing: Optional[str] = "mg/mL", formulas: Optional[Dict] = None) -> RunOutcome:
    plan = prepare_plan(config, formulas or {})
    ctx = RunContext(
        reader=reader or Reader(),
        r_client=r if r is not None else StubR(),
        unit_lookup=lambda name: FACTORS.get(name),
        pairing_unit=pairing,
        unit_names={u.id: u.name for u in UNITS.values()},
    )
    return run_plan(plan, ctx)


def status_of(outcome: RunOutcome, stage: str) -> str:
    return next(s["status"] for s in outcome.stages if s["stage"] == stage)


def assert_stopped(outcome: RunOutcome, stage: str, code: Optional[str], excel: Optional[str] = None) -> None:
    assert outcome.status == ATTEMPT_STOPPED
    assert outcome.stop_stage == stage
    assert outcome.stop_code == code
    assert outcome.formula_error == excel
    assert outcome.calculated is None and outcome.reported is None
    assert outcome.run_summary == SUMMARY_STOPPED
    assert outcome.summary_check == stage
    assert outcome.summary_code == (code or excel)


def copy_then(stage: Dict[str, Any]) -> Dict[str, Any]:
    """A stage, then a copy_raw that depends on it, pointed at the copy."""
    first_output = {
        "fit_4pl": "bottom",
        "fit_loglog_linear": "slope",
        "convert_units": "value",
        "inverse_4pl": "concentration",
        "inverse_loglog_linear": "x",
    }.get(stage["function"], "value")
    return stored(
        stage,
        catalog("after", "copy_raw", {"value": out(stage["id"], first_output)}),
        result={"stage": "after", "output": "calculated"},
        validate=False,
    )


# ---- copy_raw and the write (CALC-REQ-53, 49) ---------------------------------


def test_copy_raw_writes_the_raw_string_to_calculated_and_reported() -> None:
    cfg = stored(catalog("copy", "copy_raw", {"value": field("raw_result")}), result={"stage": "copy", "output": "calculated"})
    outcome = run(cfg, Reader({"raw_result": "0.026"}))
    assert outcome.status == ATTEMPT_COMPLETED
    assert (outcome.calculated, outcome.reported) == ("0.026", "0.026")
    assert outcome.run_summary == SUMMARY_PASS and outcome.summary_check is None and outcome.summary_code is None
    assert outcome.function_versions == [{"stage": "copy", "function": "copy_raw", "version": 1}]
    assert outcome.inputs_read == [{"stage": "copy", "input": "value", "kind": "run_field", "field": "raw_result", "value": "0.026"}]
    assert outcome.values_used == [{"stage": "copy", "input": "value", "kind": "run_field", "value": "0.026"}]


def test_copy_raw_keeps_trailing_zeros_and_never_converts() -> None:
    cfg = stored(catalog("copy", "copy_raw", {"value": field("raw_result")}), result={"stage": "copy", "output": "calculated"})
    outcome = run(cfg, Reader({"raw_result": "0.0260"}, units={"raw_result": "ug/mL"}))
    assert (outcome.calculated, outcome.reported) == ("0.0260", "0.0260")


def test_copy_raw_with_no_raw_is_missing_input_and_leaves_both_empty() -> None:
    cfg = stored(
        catalog("copy", "copy_raw", {"value": field("raw_result")}, declare("flag", flag="no_raw")),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({}))
    assert outcome.status == ATTEMPT_COMPLETED
    assert outcome.calculated is None and outcome.reported is None
    assert status_of(outcome, "copy") == STAGE_FAILED
    assert outcome.flags[0]["flag"] == "no_raw"
    assert outcome.flags[0]["function_flags"] == ["missing_input"]
    assert outcome.result_note["code"] == "result_not_produced"


def test_a_formula_result_is_written_to_both() -> None:
    cfg = stored(ad_hoc("calc", "OD * 2", {"OD": field("raw_result")}))
    outcome = run(cfg, Reader({"raw_result": "0.013"}))
    assert (outcome.calculated, outcome.reported) == ("0.026", "0.026")
    assert outcome.formula_versions[0]["kind"] == "ad_hoc_formula"
    assert "formula_text" not in outcome.formula_versions[0]


def test_a_saved_formula_is_run_from_its_pinned_text() -> None:
    cfg = stored(
        {
            "id": "calc",
            "kind": "saved_formula",
            "formula_name": "Double",
            "formula_version": 2,
            "bindings": {"x": field("raw_result")},
            "on_fail": declare(),
        },
        validate=False,
    )
    outcome = run(cfg, Reader({"raw_result": "4"}), formulas={("double", 2): "x * 2"})
    assert outcome.calculated == "8"
    assert outcome.formula_versions == [{"stage": "calc", "kind": "saved_formula", "name": "Double", "version": 2}]


def test_a_boolean_formula_is_written_as_true_or_false() -> None:
    outcome = run(stored(ad_hoc("calc", "x > 1", {"x": field("raw_result")})), Reader({"raw_result": "4"}))
    assert outcome.calculated == "TRUE"


# ---- the plan refuses before any call --------------------------------------------


def test_an_unknown_catalog_function_is_refused_before_any_call() -> None:
    cfg = stored(catalog("x", "copy_raw", {"value": field("raw_result")}), validate=False)
    cfg["stages"][0]["function_version"] = 9
    with pytest.raises(PlanRefused) as exc:
        prepare_plan(cfg, {})
    assert exc.value.code == "catalog_function_unknown"


def test_a_saved_formula_that_is_not_stored_is_refused() -> None:
    cfg = stored(
        {"id": "calc", "kind": "saved_formula", "formula_name": "Gone", "formula_version": 1, "bindings": {}, "on_fail": declare()},
        validate=False,
    )
    with pytest.raises(PlanRefused) as exc:
        prepare_plan(cfg, {})
    assert exc.value.code == "saved_formula_unknown"


@pytest.mark.parametrize("bad", [None, [], {"stages": []}, {"stages": [{"id": "a", "kind": "x"}], "result": {}}])
def test_an_unreadable_configuration_is_refused(bad: Any) -> None:
    with pytest.raises(PlanRefused):
        prepare_plan(bad, {})


# ---- CALC-REQ-25: each stop clears both and nothing further runs --------------------------


def _fit_points(levels: int) -> Dict[str, Any]:
    concs = [str(5 * 2 ** i) for i in range(levels)]
    return {"conc": concs, "resp": ["1.0"] * levels}


def _fit_stage() -> Dict[str, Any]:
    return catalog(
        "fit",
        "fit_4pl",
        {"concentration": field("conc"), "response": field("resp")},
        declare("curve_not_fitted"),
    )


def test_fit_4pl_curve_not_fitted_stops_and_dependents_do_not_run() -> None:
    stub = StubR()
    outcome = run(copy_then(_fit_stage()), Reader(_fit_points(3)), r=stub)
    assert_stopped(outcome, "fit", "curve_not_fitted")
    assert status_of(outcome, "after") == STAGE_NOT_REACHED
    assert stub.calls == []


@pytest.mark.parametrize("code", ["r_timeout", "backend_timeout"])
def test_a_timeout_is_a_stage_stop_recorded_on_the_attempt(code: str) -> None:
    def reply(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused(code, "stopped waiting")

    outcome = run(copy_then(_fit_stage()), Reader(_fit_points(5)), r=StubR(reply))
    assert_stopped(outcome, "fit", code)
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


def test_r_non_finite_stops() -> None:
    stub = StubR(lambda _p, _b: {**FIT_OUT, "slope": "NaN"})
    outcome = run(copy_then(_fit_stage()), Reader(_fit_points(5)), r=stub)
    assert_stopped(outcome, "fit", "r_non_finite")


@pytest.mark.parametrize("code", ["lock_mismatch", "sandbox", "r_service", "route"])
def test_a_refusal_that_is_not_a_timeout_is_raised_and_nothing_is_recorded(code: str) -> None:
    def reply(_path: str, _payload: dict) -> Any:
        raise CalculationCallRefused(code, "refused")

    with pytest.raises(CalculationCallRefused) as exc:
        run(copy_then(_fit_stage()), Reader(_fit_points(5)), r=StubR(reply))
    assert exc.value.code == code


def test_fit_4pl_success_feeds_the_next_stage_and_calls_only_its_route() -> None:
    stub = StubR(lambda _p, _b: dict(FIT_OUT))
    outcome = run(copy_then(_fit_stage()), Reader(_fit_points(5)), r=stub)
    assert outcome.status == ATTEMPT_COMPLETED
    assert outcome.calculated == FIT_OUT["bottom"]
    assert [path for path, _ in stub.calls] == ["/catalog/fit_4pl/v1"]
    fit = next(s for s in outcome.stages if s["stage"] == "fit")
    assert fit["outputs"]["inflection"] == "40" and fit["r_called"] is True
    assert outcome.function_versions[0] == {"stage": "fit", "function": "fit_4pl", "version": 1, "route": "/catalog/fit_4pl/v1"}


def test_fit_loglog_linear_non_positive_log_input_stops() -> None:
    stage = catalog(
        "loglog",
        "fit_loglog_linear",
        {"x": field("x"), "y": field("y")},
        declare("non_positive_log_input"),
    )
    reader = Reader({"x": ["0", "1", "2", "4"], "y": ["1", "2", "3", "4"]})
    outcome = run(copy_then(stage), reader)
    assert_stopped(outcome, "loglog", "non_positive_log_input")
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


def test_inverse_loglog_linear_non_positive_endpoint_stops() -> None:
    stage = catalog(
        "inv",
        "inverse_loglog_linear",
        {
            "slope": direct("1"),
            "intercept": direct("0"),
            "y": field("y"),
            "lowest_x_mean_y": direct("0"),
            "highest_x_mean_y": direct("10"),
        },
        declare("non_positive_log_input"),
    )
    outcome = run(copy_then(stage), Reader({"y": "5"}))
    assert_stopped(outcome, "inv", "non_positive_log_input")


def test_inverse_4pl_r_non_finite_stops() -> None:
    stage = catalog(
        "inv",
        "inverse_4pl",
        {
            "bottom": direct("0.05"),
            "top": direct("2.5"),
            "slope": direct("1.5"),
            "inflection": direct("40"),
            "response": field("resp"),
            "low_calibrator_mean_response": direct("0.1"),
            "high_calibrator_mean_response": direct("2.4"),
        },
        declare("r_non_finite"),
    )
    outcome = run(copy_then(stage), Reader({"resp": "1.0"}), r=StubR(lambda _p, _b: {"concentration": "Inf"}))
    assert_stopped(outcome, "inv", "r_non_finite")


def test_convert_units_unit_not_found_stops() -> None:
    stage = catalog("conv", "convert_units", {"value": field("raw_result")}, declare("run_failed"))
    outcome = run(copy_then(stage), Reader({"raw_result": "5"}, units={"raw_result": "furlongs"}))
    assert_stopped(outcome, "conv", "unit_not_found")
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


def test_convert_units_across_unit_types_stops_with_the_type_mismatch_code() -> None:
    stage = catalog("conv", "convert_units", {"value": field("raw_result")}, declare("run_failed"))
    outcome = run(copy_then(stage), Reader({"raw_result": "5"}, units={"raw_result": "OD"}))
    assert_stopped(outcome, "conv", UNIT_TYPE_MISMATCH)


def test_convert_units_converts_the_raw_unit_to_the_pairing_unit() -> None:
    stage = catalog("conv", "convert_units", {"value": field("raw_result")}, declare("run_failed"))
    outcome = run(copy_then(stage), Reader({"raw_result": "26"}, units={"raw_result": "ug/mL"}))
    assert outcome.calculated == "0.026"


def test_convert_units_with_no_raw_unit_reads_the_pairing_unit() -> None:
    stage = catalog("conv", "convert_units", {"value": field("raw_result")}, declare("run_failed"))
    outcome = run(copy_then(stage), Reader({"raw_result": "26"}))
    assert outcome.calculated == "26"


def test_convert_units_per_amount_divides() -> None:
    stage = catalog("conv", "convert_units", {"value": field("raw_result"), "amount": direct("4")})
    outcome = run(copy_then(stage), Reader({"raw_result": "26"}))
    assert outcome.calculated == "6.5"


@pytest.mark.parametrize("code", ["reference_missing", "reference_ambiguous", "reference_stopped"])
def test_a_reference_that_cannot_be_read_stops(code: str) -> None:
    stage = catalog(
        "diff",
        "subtract",
        {"minuend": field("raw_result"), "subtrahend": {"kind": "reference", "analyte_id": EARLIER, "value": "calculated"}},
    )
    reader = Reader({"raw_result": "5"}, refs={EARLIER: ReadStop(code, "cannot read")})
    outcome = run(copy_then(stage), reader)
    assert_stopped(outcome, "diff", code)
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


def test_a_reference_is_read_as_an_analyte_and_recorded() -> None:
    stage = catalog(
        "diff",
        "subtract",
        {"minuend": field("raw_result"), "subtrahend": {"kind": "reference", "analyte_id": EARLIER, "value": "calculated"}},
    )
    cfg = stored(stage, result={"stage": "diff", "output": "difference"})
    outcome = run(cfg, Reader({"raw_result": "5"}, refs={EARLIER: "1.5"}))
    assert outcome.calculated == "3.5"
    assert {"stage": "diff", "input": "subtrahend", "kind": "reference", "analyte_id": EARLIER, "value": "1.5"} in outcome.inputs_read


def test_a_stage_with_no_on_fail_declaration_stops_on_fail_undeclared() -> None:
    cfg = stored(
        catalog("copy", "copy_raw", {"value": field("raw_result")}),
        catalog("after", "copy_raw", {"value": out("copy", "calculated")}),
        result={"stage": "after", "output": "calculated"},
        validate=False,
    )
    del cfg["stages"][0]["on_fail"]
    outcome = run(cfg, Reader({"raw_result": "5"}))
    assert_stopped(outcome, "copy", "on_fail_undeclared")
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


@pytest.mark.parametrize(
    "on_fail",
    [{"outcome": "pass", "flag": None, "gates": [], "precedence_place": 1}, {"outcome": "carry_on", "flag": None, "gates": [], "precedence_place": 1}, {"outcome": "flag"}],
)
def test_an_unusable_declaration_fails_closed(on_fail: Dict[str, Any]) -> None:
    cfg = stored(catalog("copy", "copy_raw", {"value": field("raw_result")}), result={"stage": "copy", "output": "calculated"}, validate=False)
    cfg["stages"][0]["on_fail"] = on_fail
    outcome = run(cfg, Reader({"raw_result": "5"}))
    assert_stopped(outcome, "copy", "on_fail_undeclared")


# ---- formula errors (CALC-REQ-26, 23) -------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "fields", "excel"),
    [
        ("x / y", {"x": "1", "y": "0"}, "#DIV/0!"),
        ("x * 2", {}, "#N/A"),
        ("SQRT(x)", {"x": "-1"}, "#NUM!"),
    ],
)
def test_a_formula_error_stops_with_its_excel_text_and_no_stop_code(text: str, fields: Dict[str, str], excel: str) -> None:
    names = sorted(set(re.findall(r"\b[a-z]\b", text)))
    stage = ad_hoc("calc", text, {name: field(name) for name in names})
    cfg = stored(stage, catalog("after", "copy_raw", {"value": out("calc", "result")}), result={"stage": "after", "output": "calculated"})
    outcome = run(cfg, Reader(fields))
    assert_stopped(outcome, "calc", None, excel)
    assert status_of(outcome, "after") == STAGE_NOT_REACHED


def test_a_knocked_out_value_in_a_formula_is_na_and_is_recorded() -> None:
    cfg = stored(ad_hoc("calc", "x * 2", {"x": field("raw_result")}))
    outcome = run(cfg, Reader({"raw_result": Knocked("4")}))
    assert_stopped(outcome, "calc", None, "#N/A")
    assert outcome.knocked_out_points == [{"stage": "calc", "input": "x", "value": "4"}]


# ---- missing data in catalog functions, flags, knockouts ------------------------------------


def test_a_knocked_out_replicate_is_left_out_of_the_mean_and_recorded() -> None:
    stage = catalog("cv", "replicate_mean_cv", {"replicates": field("reps")}, declare("flag", flag="cv_missing"))
    cfg = stored(stage, result={"stage": "cv", "output": "mean"})
    outcome = run(cfg, Reader({"reps": ["1.0", Knocked("9.0"), "3.0"]}))
    assert outcome.calculated == "2"
    assert outcome.knocked_out_points == [{"stage": "cv", "input": "replicates", "value": "9.0"}]
    assert outcome.values_used[0]["value"] == ["1.0", {"knocked_out": True, "value": "9.0"}, "3.0"]


def test_a_flag_raised_with_outputs_is_carried_not_failed() -> None:
    stage = catalog("cv", "replicate_mean_cv", {"replicates": field("reps")}, declare("run_failed"))
    cfg = stored(stage, result={"stage": "cv", "output": "mean"})
    outcome = run(cfg, Reader({"reps": ["2.0"]}))
    assert status_of(outcome, "cv") == STAGE_FLAGGED
    assert outcome.run_summary == SUMMARY_PASS
    assert outcome.calculated == "2"
    assert outcome.flags == [
        {"stage": "cv", "place": None, "outcome": None, "flag": None, "verdict": None, "function_flags": ["replicate_missing"]}
    ]


def test_every_replicate_knocked_out_is_missing_input_with_no_fabricated_mean() -> None:
    stage = catalog("cv", "replicate_mean_cv", {"replicates": field("reps")}, declare("flag", flag="all_out"))
    cfg = stored(stage, result={"stage": "cv", "output": "mean"})
    outcome = run(cfg, Reader({"reps": [Knocked("1"), Knocked("2")]}))
    assert outcome.calculated is None and outcome.reported is None
    assert outcome.flags[0]["function_flags"] == ["missing_input"]
    assert outcome.status == ATTEMPT_COMPLETED


# ---- CALC-REQ-48 at run time and CALC-REQ-21 ------------------------------------------------


def _limit(stage_id: str, value: Dict[str, Any], limit: Optional[str], on_fail: Dict[str, Any]) -> Dict[str, Any]:
    on_fail.setdefault("missing_limit_flag", "limit_missing")
    bindings = {"comparison": direct("at_most"), "value": value}
    if limit is not None:
        bindings["limit"] = direct(limit)
    return catalog(stage_id, "limit_compare", bindings, on_fail)


def test_a_failed_check_with_run_failed_names_the_check_in_the_summary() -> None:
    cfg = stored(
        _limit("blank", field("blank"), "0.1", declare("run_failed", place=1)),
        catalog("copy", "copy_raw", {"value": field("raw_result")}),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"blank": "0.5", "raw_result": "1.2"}))
    assert outcome.status == ATTEMPT_COMPLETED
    assert outcome.run_summary == SUMMARY_FAIL
    assert (outcome.summary_check, outcome.summary_code) == ("blank", "run_failed")
    assert outcome.calculated == "1.2"


def test_a_failed_check_gates_the_stages_it_names() -> None:
    cfg = stored(
        _limit("blank", field("blank"), "0.1", declare("run_failed", place=1, gates=["copy"])),
        catalog("copy", "copy_raw", {"value": field("raw_result")}),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"blank": "0.5", "raw_result": "1.2"}))
    assert status_of(outcome, "copy") == STAGE_GATED
    assert outcome.calculated is None and outcome.reported is None
    assert outcome.run_summary == SUMMARY_FAIL


def test_a_passing_check_does_not_gate() -> None:
    cfg = stored(
        _limit("blank", field("blank"), "0.1", declare("run_failed", place=1, gates=["copy"])),
        catalog("copy", "copy_raw", {"value": field("raw_result")}),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"blank": "0.05", "raw_result": "1.2"}))
    assert outcome.run_summary == SUMMARY_PASS
    assert outcome.calculated == "1.2"


def test_a_fail_verdict_at_the_pointer_writes_fail() -> None:
    cfg = stored(
        _limit("check", field("raw_result"), "5", declare("sample_verdict", verdict="fail")),
        result={"stage": "check", "output": "verdict"},
    )
    outcome = run(cfg, Reader({"raw_result": "7"}))
    assert (outcome.calculated, outcome.reported) == ("fail", "fail")
    assert outcome.flags[0]["outcome"] == "sample_verdict"
    passed = run(cfg, Reader({"raw_result": "3"}))
    assert passed.calculated == "pass"


def test_a_missing_limit_raises_the_missing_limit_flag() -> None:
    cfg = stored(
        _limit("check", field("raw_result"), None, declare("flag", flag="above", missing_limit_flag="no_limit")),
        result={"stage": "check", "output": "verdict"},
        validate=False,
    )
    outcome = run(cfg, Reader({"raw_result": "7"}))
    assert status_of(outcome, "check") == STAGE_FAILED
    assert outcome.flags[0]["flag"] == "no_limit"


def test_flags_are_in_precedence_order_not_stage_order() -> None:
    cfg = stored(
        _limit("first", field("a"), "1", declare("flag", place=3, flag="third")),
        _limit("second", field("b"), "1", declare("flag", place=1, flag="first")),
        catalog("copy", "copy_raw", {"value": field("raw_result")}, declare(place=4)),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"a": "5", "b": "5", "raw_result": "1"}))
    assert [f["flag"] for f in outcome.flags] == ["first", "third"]


def test_the_first_run_failed_by_precedence_is_named() -> None:
    cfg = stored(
        _limit("late", field("a"), "1", declare("run_failed", place=2)),
        _limit("early", field("b"), "1", declare("run_failed", place=1)),
        catalog("copy", "copy_raw", {"value": field("raw_result")}),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"a": "5", "b": "5", "raw_result": "1"}))
    assert outcome.summary_check == "early"


def test_a_dilution_below_one_is_dilution_invalid_and_gates() -> None:
    cfg = stored(
        catalog("dil", "apply_dilution", {"value": field("raw_result"), "dilution_factor": field("df")}, declare("dilution_invalid", gates=["copy"])),
        catalog("copy", "copy_raw", {"value": out("dil", "value")}, declare(place=2)),
        result={"stage": "copy", "output": "calculated"},
    )
    outcome = run(cfg, Reader({"raw_result": "2", "df": "0.5"}))
    assert status_of(outcome, "dil") == STAGE_FAILED
    assert status_of(outcome, "copy") == STAGE_GATED
    assert outcome.flags[0]["outcome"] == "dilution_invalid"
    assert outcome.calculated is None


def test_a_dilution_is_applied_in_decimal() -> None:
    cfg = stored(
        catalog("dil", "apply_dilution", {"value": field("raw_result"), "dilution_factor": field("df")}, declare("dilution_invalid")),
        result={"stage": "dil", "output": "value"},
    )
    outcome = run(cfg, Reader({"raw_result": "0.1", "df": "3"}))
    assert outcome.calculated == "0.3"


def test_a_failure_that_is_not_a_stop_at_an_r_stage_is_a_flag() -> None:
    stage = catalog(
        "inv",
        "inverse_4pl",
        {
            "bottom": direct("0.05"),
            "top": direct("2.5"),
            "slope": direct("0"),
            "inflection": direct("40"),
            "response": field("resp"),
            "low_calibrator_mean_response": direct("0.1"),
            "high_calibrator_mean_response": direct("2.4"),
        },
        declare("r_non_finite", flag="inverse_inactive"),
    )
    cfg = stored(stage, result={"stage": "inv", "output": "concentration"}, validate=False)
    outcome = run(cfg, Reader({"resp": "1.0"}))
    assert outcome.status == ATTEMPT_COMPLETED
    assert outcome.flags[0]["outcome"] == "flag"
    assert outcome.flags[0]["function_flags"] == ["inactive"]
    assert outcome.calculated is None


def test_a_qualified_inverse_is_not_a_stop_and_its_dependents_are_skipped() -> None:
    stage = catalog(
        "inv",
        "inverse_4pl",
        {
            "bottom": direct("0.05"),
            "top": direct("2.5"),
            "slope": direct("1.5"),
            "inflection": direct("40"),
            "response": field("resp"),
            "low_calibrator_mean_response": direct("0.1"),
            "high_calibrator_mean_response": direct("2.4"),
        },
        declare("r_non_finite"),
    )
    cfg = stored(
        stage,
        catalog("after", "copy_raw", {"value": out("inv", "concentration")}),
        result={"stage": "inv", "output": "concentration"},
        validate=False,
    )
    stub = StubR()
    outcome = run(cfg, Reader({"resp": "0.01"}), r=stub)
    assert outcome.status == ATTEMPT_COMPLETED
    assert status_of(outcome, "inv") == STAGE_QUALIFIED
    assert status_of(outcome, "after") == STAGE_SKIPPED
    assert outcome.calculated is None and outcome.reported is None
    assert outcome.result_note["code"] == "result_qualified" and outcome.result_note["qualifier"] == "<"
    assert stub.calls == []


def test_direct_values_are_recorded_in_values_used() -> None:
    cfg = stored(
        catalog("dil", "apply_dilution", {"value": field("raw_result"), "dilution_factor": direct("10")}, declare("dilution_invalid")),
        result={"stage": "dil", "output": "value"},
    )
    outcome = run(cfg, Reader({"raw_result": "0.5"}))
    assert {"stage": "dil", "input": "dilution_factor", "kind": "direct", "value": "10"} in outcome.values_used


def test_the_outcome_is_json_safe() -> None:
    import json

    cfg = stored(catalog("cv", "replicate_mean_cv", {"replicates": field("reps")}, declare("flag", flag="x")), result={"stage": "cv", "output": "mean"})
    outcome = run(cfg, Reader({"reps": ["1", Knocked("2"), "3"]}))
    json.dumps(outcome.to_json())


# ---- wording (Marc, 2026-11-22) -----------------------------------------------------------


def test_the_s9_files_use_validated_only_for_catalog_functions() -> None:
    migration = BACKEND / "db" / "migrations" / "versions" / "0127_calculation_attempts.py"
    for path in (*S9_FILES, migration, *S9_DOCS):
        assert path.exists(), path
        for line in path.read_text(encoding="utf-8").splitlines():
            for match in re.finditer(r"validated", line, re.IGNORECASE):
                assert re.match(r"validated catalog functions?", line[match.start():], re.IGNORECASE), (path.name, line)


def test_s9_does_not_call_a_stage_output_a_result() -> None:
    for path in (*S9_FILES, *S9_DOCS):
        for line in path.read_text(encoding="utf-8").splitlines():
            lowered = line.lower()
            assert "stage output is a result" not in lowered, (path.name, line)
            assert "stage result" not in lowered, (path.name, line)


def test_s9_code_writes_no_official_result() -> None:
    for path in S9_FILES:
        source = path.read_text(encoding="utf-8")
        assert re.search(r"(?<![A-Za-z_])Result\(", source) is None, path.name
        for model in ("from models.result import", "models.result.", "result_promotion"):
            assert model not in source, (path.name, model)


def test_s9_holds_no_parked_constant() -> None:
    from tests.test_calculation_config_s7 import PARKED_CONSTANT_IDENTIFIERS

    for path in S9_FILES:
        source = path.read_text(encoding="utf-8")
        for identifier in PARKED_CONSTANT_IDENTIFIERS:
            assert identifier not in source, (path.name, identifier)
