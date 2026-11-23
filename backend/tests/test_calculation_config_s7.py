"""Calculations S7: the builder's rules (CALC-REQ-22, 23, 28, 40, 48, 50). Pure tests.

No database. The configurations are written out in full so each refusal can be
read next to the input that causes it.
"""
from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from app.services.calculation_catalog import CLOSED_CATALOG_NAMES, closed_catalog
from app.services.calculation_config import (
    ABOVE_LIST,
    CONTRACT_GROUP,
    CONTRACT_NONE,
    CONTRACT_ONE,
    CONTRACT_PERCENT,
    FAILURE_STOPS,
    REQUIRED_INPUTS,
    STAGE_STOP_CODES,
    ConfigContext,
    ConfigRefusal,
    UnitInfo,
    assign_ad_hoc_versions,
    catalog_entries,
    formula_stages_changed,
    parse_config,
    referenced_analytes,
    unit_contract,
)

SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"

ME = str(uuid.uuid4())
EARLIER = str(uuid.uuid4())
LATER = str(uuid.uuid4())
MG_ML = UnitInfo(str(uuid.uuid4()), "mg/mL", "concentration")
G_L = UnitInfo(str(uuid.uuid4()), "g/L", "concentration")
OD = UnitInfo(str(uuid.uuid4()), "OD", "absorbance")
ONE = UnitInfo(str(uuid.uuid4()), "1", "dimensionless")
PERCENT = UnitInfo(str(uuid.uuid4()), "%", "ratio")
UNITS = {u.id: u for u in (MG_ML, G_L, OD, ONE, PERCENT)}


def context(order: int = 3, formulas: Optional[Dict[Any, str]] = None) -> ConfigContext:
    return ConfigContext(
        analyte_id=ME,
        calculation_order=order,
        analyte_orders={EARLIER: 1, LATER: 5},
        units=UNITS,
        saved_formulas=formulas or {},
    )


def field(name: str, **extra: Any) -> Dict[str, Any]:
    return {"kind": "run_field", "entry_type": "experiment_sample_data", "field_name": name, **extra}


def declare(**overrides: Any) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "outcome": "run_failed",
        "flag": None,
        "gates": [],
        "precedence_place": 1,
    }
    body.update(overrides)
    return body


def stage_copy(stage_id: str = "copy", **on_fail: Any) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "kind": "catalog_function",
        "function": "copy_raw",
        "function_version": 1,
        "bindings": {"value": field("OD 450")},
        "on_fail": declare(**on_fail),
    }


def stage_cv(stage_id: str = "cv", unit: Optional[UnitInfo] = None, **on_fail: Any) -> Dict[str, Any]:
    replicates = field("Replicates", **({"unit_id": unit.id} if unit else {}))
    return {
        "id": stage_id,
        "kind": "catalog_function",
        "function": "replicate_mean_cv",
        "function_version": 1,
        "bindings": {"replicates": replicates},
        "on_fail": declare(**on_fail),
    }


def stage_limit(
    stage_id: str = "limit",
    value: Optional[Dict[str, Any]] = None,
    limit: Optional[Dict[str, Any]] = None,
    **on_fail: Any,
) -> Dict[str, Any]:
    declaration = {
        "outcome": "flag",
        "flag": "above_limit",
        "missing_limit_flag": "limit_missing",
        "gates": [],
        "precedence_place": 2,
    }
    declaration.update(on_fail)
    return {
        "id": stage_id,
        "kind": "catalog_function",
        "function": "limit_compare",
        "function_version": 1,
        "bindings": {
            "comparison": {"kind": "direct", "value": "at_most"},
            "value": value or field("Mean"),
            "limit": limit or {"kind": "direct", "value": "5.00"},
        },
        "on_fail": declaration,
    }


def config(*stages: Dict[str, Any], result: Optional[Dict[str, str]] = None, name: str = "cfg") -> Dict[str, Any]:
    return {
        "name": name,
        "stages": list(stages),
        "result": result or {"stage": stages[0]["id"], "output": _first_output(stages[0])},
    }


def _first_output(stage: Dict[str, Any]) -> str:
    if stage["kind"] != "catalog_function":
        return "result"
    match = next((v for v in closed_catalog() if v.name == stage["function"]), None)
    return next(iter(match.outputs)) if match else "calculated"


def refused(raw: Any, ctx: Optional[ConfigContext] = None) -> ConfigRefusal:
    with pytest.raises(ConfigRefusal) as raised:
        parse_config(raw, ctx or context())
    return raised.value


# ---- the catalog is closed and read here only (CALC-REQ-22) ------------------


def test_the_catalog_is_still_the_eleven() -> None:
    assert len(closed_catalog()) == 11
    assert tuple(v.name for v in closed_catalog()) == CLOSED_CATALOG_NAMES
    assert [e["name"] for e in catalog_entries()] == list(CLOSED_CATALOG_NAMES)
    assert not any(name.startswith(("elisa_", "lal_")) for name in CLOSED_CATALOG_NAMES)


def test_every_declared_unit_in_the_catalog_has_a_contract() -> None:
    for version in closed_catalog():
        for declared in (*version.inputs.values(), *version.outputs.values()):
            unit_contract(declared)


def test_a_new_kind_of_unit_declaration_is_not_skipped() -> None:
    with pytest.raises(ValueError):
        unit_contract("furlongs per fortnight")


def test_unit_contract_reading() -> None:
    assert unit_contract("1").kind == CONTRACT_ONE
    assert unit_contract("1 (label log10(<y unit>))").kind == CONTRACT_ONE
    assert unit_contract("%").kind == CONTRACT_PERCENT
    for none in ("count", "identity", "token", ""):
        assert unit_contract(none).kind == CONTRACT_NONE
    assert unit_contract("shared unit") == (unit_contract("shared unit"))
    assert unit_contract("shared unit").kind == CONTRACT_GROUP
    assert unit_contract("shared unit").group == "shared"


def test_required_inputs_and_failure_stops_name_real_things() -> None:
    by_name = {v.name: v for v in closed_catalog()}
    assert set(REQUIRED_INPUTS) == set(by_name)
    for name, required in REQUIRED_INPUTS.items():
        assert set(required) <= set(by_name[name].inputs), name
    assert set(FAILURE_STOPS) <= set(by_name)
    for name, stops in FAILURE_STOPS.items():
        assert str(getattr(by_name[name].side, "value", by_name[name].side)) == "r"
        assert set(stops) <= set(STAGE_STOP_CODES)
    assert "on_fail_undeclared" not in STAGE_STOP_CODES


def test_the_builder_offers_only_catalog_functions() -> None:
    for name in ("elisa_4pl", "lal_endotoxin", "fit_5pl", "run_r", "Fit_4PL"):
        stage = stage_copy()
        stage["function"] = name
        assert refused(config(stage)).code == "catalog_function_unknown", name
    stage = stage_copy()
    stage["function_version"] = 2
    assert refused(config(stage)).code == "catalog_function_unknown"
    stage["function_version"] = True
    assert refused(config(stage)).code == "catalog_function_unknown"


# ---- a valid configuration and what it stores --------------------------------


def test_a_catalog_only_configuration_is_accepted_and_normalised() -> None:
    parsed = parse_config(config(stage_cv(), stage_copy("copy2")), context())
    stored = parsed.to_json()
    assert stored["name"] == "cfg"
    assert [s["id"] for s in stored["stages"]] == ["cv", "copy2"]
    first = stored["stages"][0]
    assert first["function"] == "replicate_mean_cv" and first["function_version"] == 1
    assert first["on_fail"] == {
        "outcome": "run_failed",
        "verdict": None,
        "flag": None,
        "missing_limit_flag": None,
        "gates": [],
        "precedence_place": 1,
    }
    assert stored["result"] == {"stage": "cv", "output": "mean"}


def test_a_stored_configuration_has_no_formula_text_for_a_catalog_stage_and_no_unit_for_a_formula() -> None:
    stored = parse_config(config(stage_copy()), context()).to_json()
    assert "formula_text" not in stored["stages"][0]
    assert "formula_name" not in stored["stages"][0]


def test_parsing_is_idempotent_on_the_stored_form() -> None:
    first = parse_config(config(stage_cv(), stage_copy("copy2")), context()).to_json()
    second = parse_config(copy.deepcopy(first), context()).to_json()
    assert first == second


# ---- direct binding (CALC-REQ-23) -------------------------------------------


def test_a_value_bound_directly_saves_and_is_stored_unchanged() -> None:
    cfg = config(
        stage_cv(),
        stage_limit(value={"kind": "stage_output", "stage": "cv", "output": "mean"}, limit={"kind": "direct", "value": "5.00"}),
        result={"stage": "limit", "output": "verdict"},
    )
    stored = parse_config(cfg, context()).to_json()
    assert stored["stages"][1]["bindings"]["limit"] == {"kind": "direct", "value": "5.00"}


def test_the_compared_bound_is_the_configured_value_not_a_built_in_one() -> None:
    for value in ("0.5", "5.00", "1E3", "-0.000001", "123456789.123456789"):
        cfg = config(stage_limit(limit={"kind": "direct", "value": value}), result={"stage": "limit", "output": "verdict"})
        stored = parse_config(cfg, context()).to_json()
        assert stored["stages"][0]["bindings"]["limit"]["value"] == value


@pytest.mark.parametrize("value", [5, 5.5, True, None, ["5"], {"v": "5"}, "", " 5", "5 ", "abc", "5,5", "NaN", "Infinity"])
def test_a_direct_value_is_a_decimal_string(value: Any) -> None:
    cfg = config(stage_limit(limit={"kind": "direct", "value": value}), result={"stage": "limit", "output": "verdict"})
    assert refused(cfg).code == "direct_value_invalid"


def test_comparison_is_a_direct_token_from_the_catalog() -> None:
    for token in ("at_most", "at_least", "within"):
        stage = stage_limit()
        stage["bindings"]["comparison"] = {"kind": "direct", "value": token}
        if token == "within":
            stage["bindings"].pop("limit")
            stage["bindings"]["low"] = {"kind": "direct", "value": "1"}
            stage["bindings"]["high"] = {"kind": "direct", "value": "2"}
        parse_config(config(stage, result={"stage": "limit", "output": "verdict"}), context())
    stage = stage_limit()
    stage["bindings"]["comparison"] = {"kind": "direct", "value": "greater_than"}
    assert refused(config(stage)).code == "binding_invalid"
    stage = stage_limit()
    stage["bindings"]["comparison"] = field("Comparison")
    assert refused(config(stage)).code == "binding_invalid"


def test_limit_compare_needs_the_bounds_its_form_uses() -> None:
    stage = stage_limit()
    stage["bindings"].pop("limit")
    assert refused(config(stage)).code == "binding_missing"
    stage = stage_limit()
    stage["bindings"]["comparison"] = {"kind": "direct", "value": "within"}
    assert refused(config(stage)).code == "binding_missing"
    stage = stage_limit()
    stage["bindings"]["high"] = {"kind": "direct", "value": "9"}
    assert refused(config(stage)).code == "binding_unknown_input"


def test_there_is_no_constants_binding_and_no_constants_field() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "constant", "name": "endotoxin_limit"}
    assert refused(config(stage)).code == "binding_kind_unknown"
    cfg = config(stage_copy())
    cfg["constants"] = {"x": "1"}
    assert refused(cfg).code == "unknown_field"
    stage = stage_copy()
    stage["constants"] = {}
    assert refused(config(stage)).code == "unknown_field"


# ---- on-fail declarations (CALC-REQ-48) -------------------------------------


def test_a_stage_with_no_declaration_is_refused_and_named() -> None:
    stage = stage_copy("needs_decl")
    del stage["on_fail"]
    exc = refused(config(stage))
    assert exc.code == "on_fail_declaration_missing"
    assert exc.stage == "needs_decl" and "needs_decl" in exc.message
    assert exc.detail()["stage"] == "needs_decl"


@pytest.mark.parametrize("missing", ["outcome", "flag", "gates", "precedence_place"])
def test_every_one_of_the_four_declarations_is_required(missing: str) -> None:
    stage = stage_copy("s")
    del stage["on_fail"][missing]
    exc = refused(config(stage))
    assert exc.code == "on_fail_declaration_missing" and exc.stage == "s" and missing in exc.message


def test_pass_is_refused_at_save() -> None:
    exc = refused(config(stage_copy(outcome="pass")))
    assert exc.code == "on_fail_pass_refused"
    exc = refused(config(stage_copy(outcome="flag", flag="pass")))
    assert exc.code == "on_fail_pass_refused"
    stage = stage_copy(outcome="sample_verdict", verdict="pass")
    assert refused(config(stage)).code == "on_fail_pass_refused"


def test_an_outcome_that_is_not_declarable_is_refused() -> None:
    for outcome in ("fail_open", "skip", "continue", "", None, 3, "on_fail_undeclared", "RUN_FAILED"):
        exc = refused(config(stage_copy(outcome=outcome)))
        assert exc.code in ("on_fail_outcome_unknown", "on_fail_declaration_missing"), outcome


def test_the_four_outcomes_and_their_required_fields() -> None:
    parse_config(config(stage_copy(outcome="run_failed")), context())
    parse_config(config(stage_copy(outcome="dilution_invalid")), context())
    parse_config(config(stage_copy(outcome="sample_verdict", verdict="no_verdict")), context())
    parse_config(config(stage_copy(outcome="flag", flag="needs_review")), context())
    assert refused(config(stage_copy(outcome="sample_verdict"))).code == "on_fail_declaration_missing"
    assert refused(config(stage_copy(outcome="flag"))).code == "on_fail_declaration_missing"
    assert refused(config(stage_copy(outcome="run_failed", verdict="x"))).code == "on_fail_invalid"


def test_fit_4pl_declaring_run_failed_for_curve_not_fitted_is_refused() -> None:
    fit = {
        "id": "fit",
        "kind": "catalog_function",
        "function": "fit_4pl",
        "function_version": 1,
        "bindings": {"concentration": field("Dose"), "response": field("OD")},
        "on_fail": declare(outcome="run_failed"),
    }
    exc = refused(config(fit))
    assert exc.code == "on_fail_stage_stop_required" and exc.stage == "fit"
    assert "curve_not_fitted" in exc.message
    fit["on_fail"] = declare(outcome="curve_not_fitted", precedence_place=ABOVE_LIST)
    parse_config(config(fit), context())
    fit["on_fail"] = declare(outcome="reference_missing", precedence_place=ABOVE_LIST)
    assert refused(config(fit)).code == "on_fail_stage_stop_required"


def test_a_backend_stage_cannot_declare_a_stage_stop_it_does_not_have() -> None:
    exc = refused(config(stage_copy(outcome="curve_not_fitted", precedence_place=ABOVE_LIST)))
    assert exc.code == "on_fail_stage_stop_not_applicable"


def test_the_two_stage_stop_spellings_that_are_not_declarations() -> None:
    assert "on_fail_undeclared" not in STAGE_STOP_CODES
    assert all(isinstance(code, str) for code in STAGE_STOP_CODES)


def test_a_stage_that_reads_a_limit_declares_the_missing_limit_flag() -> None:
    stage = stage_limit()
    del stage["on_fail"]["missing_limit_flag"]
    exc = refused(config(stage))
    assert exc.code == "missing_limit_flag_required" and exc.stage == "limit"
    stage = stage_limit()
    stage["on_fail"]["missing_limit_flag"] = None
    assert refused(config(stage)).code == "missing_limit_flag_required"
    parse_config(config(stage_limit(), result={"stage": "limit", "output": "verdict"}), context())
    stage = stage_copy(missing_limit_flag="x")
    assert refused(config(stage)).code == "missing_limit_flag_not_applicable"


def test_the_flag_a_stage_declares_is_stored() -> None:
    parsed = parse_config(config(stage_limit(), result={"stage": "limit", "output": "verdict"}), context())
    on_fail = parsed.to_json()["stages"][0]["on_fail"]
    assert on_fail["flag"] == "above_limit" and on_fail["missing_limit_flag"] == "limit_missing"


def test_no_built_in_flag_is_added() -> None:
    parsed = parse_config(config(stage_limit(), result={"stage": "limit", "output": "verdict"}), context())
    assert "limit_below_el" not in str(parsed.to_json())
    for name in ("calculation_config.py", "calculation_config_service.py"):
        assert "limit_below_el" not in (SERVICES / name).read_text(encoding="utf-8")


def test_two_stages_claiming_place_1_for_different_flags_are_refused() -> None:
    a = stage_copy("a", outcome="flag", flag="flag_one", precedence_place=1)
    b = stage_copy("b", outcome="flag", flag="flag_two", precedence_place=1)
    exc = refused(config(a, b))
    assert exc.code == "precedence_place_conflict" and exc.stage == "b"
    b["on_fail"]["flag"] = "flag_one"
    parse_config(config(a, b), context())
    b["on_fail"]["precedence_place"] = 2
    b["on_fail"]["flag"] = "flag_two"
    parse_config(config(a, b), context())


def test_a_place_claimed_by_a_verdict_and_a_flag_conflicts() -> None:
    a = stage_copy("a", outcome="flag", flag="needs_review", precedence_place=1)
    b = stage_copy("b", outcome="sample_verdict", verdict="no_verdict", precedence_place=1)
    assert refused(config(a, b)).code == "precedence_place_conflict"


def test_precedence_place_values() -> None:
    for place in (0, -1, 1.5, "1", None, True, 1001, "above"):
        assert refused(config(stage_copy(precedence_place=place))).code == "precedence_place_invalid", place
    assert refused(config(stage_copy(precedence_place=ABOVE_LIST))).code == "precedence_place_invalid"


def test_gates_name_later_stages_only() -> None:
    a = stage_copy("a", gates=["b"])
    b = stage_copy("b", precedence_place=2)
    parse_config(config(a, b), context())
    assert refused(config(stage_copy("a", gates=["zzz"]), b)).code == "gate_unknown_stage"
    assert refused(config(stage_copy("a", gates=["a"]), b)).code == "gate_not_later"
    b2 = stage_copy("b", gates=["a"], precedence_place=2)
    assert refused(config(stage_copy("a"), b2)).code == "gate_not_later"
    assert refused(config(stage_copy("a", gates=["b", "b"]), b)).code == "on_fail_invalid"
    assert refused(config(stage_copy("a", gates="b"), b)).code == "on_fail_invalid"


def test_unknown_fields_in_a_declaration_are_refused() -> None:
    stage = stage_copy()
    stage["on_fail"]["fail_open"] = True
    assert refused(config(stage)).code == "unknown_field"


# ---- bindings (CALC-REQ-23, 50) ---------------------------------------------


def test_a_binding_has_one_of_four_kinds() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "sql", "query": "select 1"}
    assert refused(config(stage)).code == "binding_kind_unknown"
    stage["bindings"]["value"] = {"entry_type": "experiment_data"}
    assert refused(config(stage)).code == "binding_kind_unknown"
    stage["bindings"]["value"] = "OD 450"
    assert refused(config(stage)).code == "config_invalid"


def test_a_run_field_binding_names_the_entry_type_and_the_field() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = field("OD 450", match_field="Sample ID")
    parsed = parse_config(config(stage), context()).to_json()
    assert parsed["stages"][0]["bindings"]["value"]["match_field"] == "Sample ID"
    for bad in (
        {"kind": "run_field", "entry_type": "experiment", "field_name": "x"},
        {"kind": "run_field", "entry_type": "experiment_data"},
        {"kind": "run_field", "entry_type": "experiment_data", "field_name": ""},
        {"kind": "run_field", "entry_type": "experiment_data", "field_name": "x", "lims_run_id": "other-run"},
    ):
        stage["bindings"]["value"] = bad
        assert refused(config(stage)).code in ("binding_invalid", "unknown_field")


def test_a_stage_output_binding_reads_an_earlier_stage_and_a_real_output() -> None:
    use = stage_copy("use")
    use["bindings"]["value"] = {"kind": "stage_output", "stage": "cv", "output": "mean"}
    parse_config(config(stage_cv(), use, result={"stage": "use", "output": "calculated"}), context())
    use["bindings"]["value"] = {"kind": "stage_output", "stage": "cv", "output": "nope"}
    assert refused(config(stage_cv(), use)).code == "binding_invalid"
    use["bindings"]["value"] = {"kind": "stage_output", "stage": "use", "output": "calculated"}
    assert refused(config(stage_cv(), use)).code == "stage_order_violation"
    first = stage_copy("first")
    first["bindings"]["value"] = {"kind": "stage_output", "stage": "cv", "output": "mean"}
    assert refused(config(first, stage_cv())).code == "stage_order_violation"


def test_a_reference_reads_an_earlier_analyte_in_calculation_order() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": EARLIER, "value": "calculated"}
    parse_config(config(stage), context(order=3))
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": EARLIER, "value": "reported"}
    parse_config(config(stage), context(order=2))


def test_a_reference_to_a_later_equal_or_own_analyte_is_refused() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": LATER, "value": "calculated"}
    assert refused(config(stage), context(order=3)).code == "calculation_order_violation"
    assert refused(config(stage), context(order=5)).code == "calculation_order_violation"
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": EARLIER, "value": "calculated"}
    assert refused(config(stage), context(order=1)).code == "calculation_order_violation"
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": ME, "value": "calculated"}
    assert refused(config(stage)).code == "calculation_order_violation"


def test_a_reference_to_an_analyte_with_no_calculation_or_not_in_the_analysis() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": str(uuid.uuid4()), "value": "calculated"}
    assert refused(config(stage)).code == "reference_analyte_unknown"
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": "not-a-uuid", "value": "calculated"}
    assert refused(config(stage)).code == "binding_invalid"
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": EARLIER, "value": "raw"}
    assert refused(config(stage)).code == "binding_invalid"


def test_referenced_analytes_lists_the_reference_bindings() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "reference", "analyte_id": EARLIER, "value": "calculated"}
    stored = parse_config(config(stage), context()).to_json()
    assert referenced_analytes(stored) == {EARLIER}
    assert referenced_analytes(parse_config(config(stage_copy()), context()).to_json()) == set()


def test_an_input_the_function_does_not_have_is_refused() -> None:
    stage = stage_copy()
    stage["bindings"]["extra"] = field("x")
    assert refused(config(stage)).code == "binding_unknown_input"


def test_a_required_input_must_be_bound() -> None:
    stage = stage_copy()
    stage["bindings"] = {}
    exc = refused(config(stage))
    assert exc.code == "binding_missing" and "value" in exc.message


def test_an_identity_input_is_bound_to_a_field() -> None:
    fit = {
        "id": "fit",
        "kind": "catalog_function",
        "function": "fit_4pl",
        "function_version": 1,
        "bindings": {
            "concentration": field("Dose"),
            "response": field("OD"),
            "replicate": {"kind": "direct", "value": "1"},
        },
        "on_fail": declare(outcome="curve_not_fitted", precedence_place=ABOVE_LIST),
    }
    assert refused(config(fit)).code == "binding_invalid"
    fit["bindings"]["replicate"] = field("Replicate")
    parse_config(config(fit), context())


# ---- units (CALC-REQ-28) ----------------------------------------------------


def test_a_binding_of_another_unit_type_than_declared_is_refused() -> None:
    cv_ok = stage_cv(unit=MG_ML)
    limit = stage_limit(
        value={"kind": "stage_output", "stage": "cv", "output": "mean"},
        limit={"kind": "direct", "value": "5", "unit_id": G_L.id},
    )
    exc = refused(config(cv_ok, limit, result={"stage": "limit", "output": "verdict"}))
    assert exc.code == "unit_binding_mismatch" and exc.stage == "limit"
    limit["bindings"]["limit"]["unit_id"] = MG_ML.id
    parse_config(config(cv_ok, limit, result={"stage": "limit", "output": "verdict"}), context())


def test_a_unit_on_a_dimensionless_input_must_be_dimensionless() -> None:
    stage = stage_limit()
    stage["bindings"]["absolute"] = {"kind": "direct", "value": "1", "unit_id": MG_ML.id}
    assert refused(config(stage)).code == "unit_binding_mismatch"
    stage["bindings"]["absolute"] = {"kind": "direct", "value": "1", "unit_id": ONE.id}
    parse_config(config(stage, result={"stage": "limit", "output": "verdict"}), context())
    stage["bindings"]["absolute"] = {"kind": "direct", "value": "1", "unit_id": PERCENT.id}
    assert refused(config(stage)).code == "unit_binding_mismatch"


def test_dilution_factor_takes_a_dimensionless_value_not_a_percentage_output() -> None:
    cv = stage_cv()
    dilute = {
        "id": "dilute",
        "kind": "catalog_function",
        "function": "apply_dilution",
        "function_version": 1,
        "bindings": {
            "value": field("Conc"),
            "dilution_factor": {"kind": "stage_output", "stage": "cv", "output": "percent_cv"},
        },
        "on_fail": declare(outcome="dilution_invalid", precedence_place=2),
    }
    exc = refused(config(cv, dilute, result={"stage": "dilute", "output": "value"}))
    assert exc.code == "unit_binding_mismatch" and exc.stage == "dilute"
    assert "dimensionless" in exc.message
    dilute["bindings"]["dilution_factor"] = {"kind": "direct", "value": "10"}
    parse_config(config(cv, dilute, result={"stage": "dilute", "output": "value"}), context())


def test_inputs_that_share_a_declared_unit_share_one_unit() -> None:
    sub = {
        "id": "sub",
        "kind": "catalog_function",
        "function": "subtract",
        "function_version": 1,
        "bindings": {
            "minuend": field("Sample", unit_id=MG_ML.id),
            "subtrahend": field("Blank", unit_id=G_L.id),
        },
        "on_fail": declare(),
    }
    exc = refused(config(sub, result={"stage": "sub", "output": "difference"}))
    assert exc.code == "unit_binding_mismatch" and "share one declared unit" in exc.message
    sub["bindings"]["subtrahend"]["unit_id"] = MG_ML.id
    parse_config(config(sub, result={"stage": "sub", "output": "difference"}), context())
    del sub["bindings"]["subtrahend"]["unit_id"]
    parse_config(config(sub, result={"stage": "sub", "output": "difference"}), context())


def test_an_output_carries_its_group_unit_to_the_next_stage() -> None:
    sub = {
        "id": "sub",
        "kind": "catalog_function",
        "function": "subtract",
        "function_version": 1,
        "bindings": {
            "minuend": field("Sample", unit_id=MG_ML.id),
            "subtrahend": field("Blank", unit_id=MG_ML.id),
        },
        "on_fail": declare(),
    }
    nxt = {
        "id": "nxt",
        "kind": "catalog_function",
        "function": "subtract",
        "function_version": 1,
        "bindings": {
            "minuend": {"kind": "stage_output", "stage": "sub", "output": "difference"},
            "subtrahend": field("Other", unit_id=G_L.id),
        },
        "on_fail": declare(precedence_place=2),
    }
    exc = refused(config(sub, nxt, result={"stage": "nxt", "output": "difference"}))
    assert exc.code == "unit_binding_mismatch" and exc.stage == "nxt"
    nxt["bindings"]["subtrahend"]["unit_id"] = MG_ML.id
    parse_config(config(sub, nxt, result={"stage": "nxt", "output": "difference"}), context())


def test_a_unit_that_does_not_exist_or_is_not_active_is_refused() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = field("x", unit_id=str(uuid.uuid4()))
    assert refused(config(stage)).code == "unit_not_found"
    stage["bindings"]["value"] = field("x", unit_id="nope")
    assert refused(config(stage)).code == "unit_not_found"


def test_a_token_or_identity_input_has_no_unit() -> None:
    stage = stage_limit()
    stage["bindings"]["comparison"] = {"kind": "direct", "value": "at_most", "unit_id": ONE.id}
    assert refused(config(stage)).code == "unit_binding_mismatch"


def test_no_unit_is_stored_for_the_result() -> None:
    stored = parse_config(config(stage_copy()), context()).to_json()
    assert "unit" not in str(stored["result"]) and "units" not in stored


# ---- formulas (CALC-REQ-23) --------------------------------------------------


def ad_hoc(stage_id: str = "calc", text: str = "ROUND(od - blank, 3)", **bindings: Any) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "kind": "ad_hoc_formula",
        "formula_text": text,
        "bindings": bindings or {"od": field("OD 450"), "blank": {"kind": "direct", "value": "0.05"}},
        "on_fail": declare(),
    }


def test_an_ad_hoc_formula_stage_is_accepted_with_every_term_bound() -> None:
    parsed = parse_config(config(ad_hoc(), result={"stage": "calc", "output": "result"}), context())
    stage = parsed.to_json()["stages"][0]
    assert stage["kind"] == "ad_hoc_formula" and stage["formula_text"] == "ROUND(od - blank, 3)"
    assert stage["bindings"]["blank"] == {"kind": "direct", "value": "0.05"}


def test_a_formula_term_that_is_not_bound_is_refused() -> None:
    stage = ad_hoc(od=field("OD 450"))
    exc = refused(config(stage, result={"stage": "calc", "output": "result"}))
    assert exc.code == "formula_term_unbound" and "blank" in exc.message and exc.stage == "calc"


def test_a_binding_for_a_name_the_formula_does_not_use_is_refused() -> None:
    stage = ad_hoc(od=field("a"), blank=field("b"), extra=field("c"))
    assert refused(config(stage, result={"stage": "calc", "output": "result"})).code == "binding_unknown_input"


@pytest.mark.parametrize(
    "text, code",
    [
        ("SUM(A1:A3)", "formula_range_not_supported"),
        ("FOO(od)", "formula_unknown_function"),
        ("od +", "formula_syntax"),
        ("'x'", "formula_token_not_allowed"),
        ("LINEST({1,2},{1,2})", "formula_result_not_scalar"),
        ("TREND({1,2},{1,2})", "formula_result_not_scalar"),
        ("", "formula_empty"),
        ("od.x", "formula_unknown_name"),
    ],
)
def test_a_formula_outside_the_grammar_is_refused_at_save(text: str, code: str) -> None:
    exc = refused(config(ad_hoc(text=text, od=field("a")), result={"stage": "calc", "output": "result"}))
    assert exc.code == code and exc.stage == "calc"


def test_a_formula_stage_stores_no_unit_and_a_term_binding_cannot_carry_one() -> None:
    stage = ad_hoc(od=field("OD 450", unit_id=MG_ML.id), blank={"kind": "direct", "value": "0.05"})
    exc = refused(config(stage, result={"stage": "calc", "output": "result"}))
    assert exc.code == "formula_term_unit_not_allowed"
    stage = ad_hoc()
    stage["unit"] = "mg/mL"
    assert refused(config(stage, result={"stage": "calc", "output": "result"})).code == "unknown_field"


def test_the_formula_layer_does_not_refuse_terms_with_different_origins() -> None:
    cv = stage_cv(unit=MG_ML)
    stage = ad_hoc(
        text="mean_value - other",
        mean_value={"kind": "stage_output", "stage": "cv", "output": "mean"},
        other=field("Other"),
    )
    parse_config(config(cv, stage, result={"stage": "calc", "output": "result"}), context())


def test_a_formula_can_read_an_earlier_analyte_and_not_a_later_one() -> None:
    stage = ad_hoc(text="a + b", a={"kind": "reference", "analyte_id": EARLIER, "value": "reported"}, b=field("x"))
    parse_config(config(stage, result={"stage": "calc", "output": "result"}), context(order=3))
    stage = ad_hoc(text="a + b", a={"kind": "reference", "analyte_id": LATER, "value": "reported"}, b=field("x"))
    assert refused(config(stage, result={"stage": "calc", "output": "result"}), context(order=3)).code == "calculation_order_violation"


def test_a_direct_formula_term_is_a_decimal_string() -> None:
    stage = ad_hoc(od=field("a"), blank={"kind": "direct", "value": "abc"})
    assert refused(config(stage, result={"stage": "calc", "output": "result"})).code == "direct_value_invalid"
    stage = ad_hoc(od=field("a"), blank={"kind": "direct", "value": 0.05})
    assert refused(config(stage, result={"stage": "calc", "output": "result"})).code == "direct_value_invalid"


def test_a_saved_formula_is_pinned_by_name_and_version() -> None:
    formulas = {("blank correct", 2): "od - blank"}
    stage = {
        "id": "calc",
        "kind": "saved_formula",
        "formula_name": "Blank Correct",
        "formula_version": 2,
        "bindings": {"od": field("OD 450"), "blank": {"kind": "direct", "value": "0.05"}},
        "on_fail": declare(),
    }
    stored = parse_config(config(stage, result={"stage": "calc", "output": "result"}), context(formulas=formulas)).to_json()
    saved = stored["stages"][0]
    assert saved["formula_name"] == "Blank Correct" and saved["formula_version"] == 2
    assert "formula_text" not in saved
    stage["formula_version"] = 3
    assert refused(config(stage, result={"stage": "calc", "output": "result"}), context(formulas=formulas)).code == "saved_formula_unknown"
    stage["formula_version"] = 2
    stage["formula_name"] = "nope"
    assert refused(config(stage, result={"stage": "calc", "output": "result"}), context(formulas=formulas)).code == "saved_formula_unknown"


def test_a_saved_formula_with_an_unbound_term_is_refused() -> None:
    formulas = {("f", 1): "a + b"}
    stage = {
        "id": "calc",
        "kind": "saved_formula",
        "formula_name": "f",
        "formula_version": 1,
        "bindings": {"a": field("x")},
        "on_fail": declare(),
    }
    assert refused(config(stage, result={"stage": "calc", "output": "result"}), context(formulas=formulas)).code == "formula_term_unbound"


def test_an_ad_hoc_formula_version_is_one_then_counts_changes() -> None:
    first = assign_ad_hoc_versions(parse_config(config(ad_hoc(), result={"stage": "calc", "output": "result"}), context()), None)
    stored_1 = first.to_json()
    assert stored_1["stages"][0]["formula_version"] == 1
    same = assign_ad_hoc_versions(parse_config(config(ad_hoc(), result={"stage": "calc", "output": "result"}), context()), stored_1)
    assert same.to_json()["stages"][0]["formula_version"] == 1
    changed = assign_ad_hoc_versions(
        parse_config(config(ad_hoc(text="ROUND(od - blank, 4)"), result={"stage": "calc", "output": "result"}), context()),
        stored_1,
    )
    assert changed.to_json()["stages"][0]["formula_version"] == 2
    again = assign_ad_hoc_versions(
        parse_config(config(ad_hoc(text="ROUND(od - blank, 4)"), result={"stage": "calc", "output": "result"}), context()),
        changed.to_json(),
    )
    assert again.to_json()["stages"][0]["formula_version"] == 2


def test_the_client_cannot_set_the_ad_hoc_formula_version() -> None:
    stage = ad_hoc()
    stage["formula_version"] = 9
    assert refused(config(stage, result={"stage": "calc", "output": "result"})).code == "unknown_field"


def test_formula_stages_changed_finds_new_and_edited_formula_stages_only() -> None:
    base = parse_config(config(stage_copy(), ad_hoc(stage_id="calc"), result={"stage": "copy", "output": "calculated"}), context())
    stored = assign_ad_hoc_versions(base, None).to_json()
    assert formula_stages_changed(stored, stored) == []
    edited = copy.deepcopy(stored)
    edited["stages"][1]["formula_text"] = "od + blank"
    assert formula_stages_changed(edited, stored) == ["calc"]
    edited = copy.deepcopy(stored)
    edited["stages"][1]["bindings"]["blank"]["value"] = "0.06"
    assert formula_stages_changed(edited, stored) == ["calc"]
    edited = copy.deepcopy(stored)
    edited["stages"][0]["bindings"]["value"]["field_name"] = "OD 600"
    assert formula_stages_changed(edited, stored) == []
    assert formula_stages_changed(stored, None) == ["calc"]


# ---- shape of the whole configuration ---------------------------------------


@pytest.mark.parametrize(
    "raw",
    [None, [], "x", 1, {}, {"name": "x"}, {"name": "x", "stages": []}, {"name": "x", "stages": "s"}],
)
def test_a_configuration_must_be_an_object_with_a_name_and_stages(raw: Any) -> None:
    refused(raw)


def test_names_ids_and_limits() -> None:
    cfg = config(stage_copy())
    cfg["name"] = ""
    assert refused(cfg).code == "config_invalid"
    cfg["name"] = "x" * 101
    assert refused(cfg).code == "config_invalid"
    cfg["name"] = " padded"
    assert refused(cfg).code == "config_invalid"
    for bad in ("", "A", "1a", "a-b", "a b", "x" * 41, None, 5):
        stage = stage_copy()
        stage["id"] = bad
        assert refused(config(stage)).code == "stage_id_invalid", bad
    assert refused(config(stage_copy("same"), stage_copy("same", precedence_place=2))).code == "stage_id_duplicate"
    many = [stage_copy(f"s{i}", precedence_place=i + 1) for i in range(51)]
    assert refused(config(*many)).code == "config_invalid"


def test_the_result_names_a_real_output() -> None:
    assert refused(config(stage_copy(), result={"stage": "nope", "output": "calculated"})).code == "result_invalid"
    assert refused(config(stage_copy(), result={"stage": "copy", "output": "nope"})).code == "result_invalid"
    cfg = config(stage_copy())
    del cfg["result"]
    assert refused(cfg).code == "config_invalid"
    cfg = config(stage_copy())
    cfg["result"]["unit"] = "mg"
    assert refused(cfg).code == "unknown_field"


def test_unknown_stage_kind_and_unknown_stage_fields_are_refused() -> None:
    stage = stage_copy()
    stage["kind"] = "r_script"
    assert refused(config(stage)).code == "stage_kind_unknown"
    stage = stage_copy()
    stage["r_code"] = "print(1)"
    assert refused(config(stage)).code == "unknown_field"
    stage = stage_copy()
    stage["formula_text"] = "1+1"
    assert refused(config(stage)).code == "unknown_field"


def test_there_is_no_route_to_run_r_or_name_a_model_in_a_configuration() -> None:
    stage = stage_copy()
    stage["bindings"]["value"] = {"kind": "r", "code": "x"}
    assert refused(config(stage)).code == "binding_kind_unknown"
    stage = stage_copy()
    stage["function"] = "LL.4"
    assert refused(config(stage)).code == "catalog_function_unknown"


# ---- wording and the parked constants (CALC-REQ-46, #258) ---------------------

S7_FILES = (
    SERVICES / "calculation_formula.py",
    SERVICES / "calculation_config.py",
    SERVICES / "calculation_config_service.py",
    SERVICES.parent / "routers" / "calculation_config.py",
    SERVICES.parent / "schemas" / "calculation_config.py",
)

# The constants parked toward #258 are not a menu and not built in. nominal_spike
# is also a real input name of spike_recovery, so it is checked separately.
PARKED_CONSTANT_IDENTIFIERS = (
    "abs_correlation_min",
    "percent_cv_max",
    "percent_range",
    "min_point_count",
    "endotoxin_limit",
    "max_valid_dilution",
    "onset_cutoff",
    "replicate_count",
    "min_in_range",
    "max_remaining_span",
)


def test_the_parked_constant_identifiers_are_not_in_the_s7_code() -> None:
    for path in S7_FILES:
        source = path.read_text(encoding="utf-8")
        for identifier in PARKED_CONSTANT_IDENTIFIERS:
            assert identifier not in source, (path.name, identifier)
    config_source = (SERVICES / "calculation_config.py").read_text(encoding="utf-8")
    assert config_source.count("nominal_spike") == 1


def test_the_word_validated_appears_only_in_validated_catalog_function() -> None:
    migration = SERVICES.parents[1] / "db" / "migrations" / "versions" / "0124_calculation_configuration.py"
    root = SERVICES.parents[2]
    docs = (
        root / "manuals" / "calculation-configuration-s7.md",
        root / "UAT_Scripts" / "uat-calculations-s7.md",
    )
    for path in (*S7_FILES, migration, *docs):
        for line in path.read_text(encoding="utf-8").splitlines():
            for match in re.finditer(r"validated", line, re.IGNORECASE):
                assert re.match(r"validated catalog functions?", line[match.start():], re.IGNORECASE), (path.name, line)


def test_no_threshold_number_is_built_in() -> None:
    import ast

    for path in S7_FILES[:3]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                pytest.fail(f"{path.name} has the float literal {node.value}")
