"""Calculations S8: the pieces that need no database (CALC-REQ-34, 35, 45, 46, 47).

RFC 8785 canonical JSON, the review diff, the validation-state rule, the
configuring agent's allow-list, and the wording rules for the S8 files.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from app.core.agent_context import agent_run_context, in_agent_context, refuse_in_agent_context
from app.services import jcs
from app.services.calculation_review import (
    CONFIRM_LABEL,
    CONFIRM_LABEL_NO_TESTS,
    VALIDATION_STATES,
    binding_text,
    classify_state,
    diff_configurations,
)
from app.services.configuring_agent_allow import ACTIVATION_GAP, CATALOG_GAP, classify_call
from app.services.configuring_agent_catalog import route_formats, route_formats_text
from tests.test_calculation_config_s7 import PARKED_CONSTANT_IDENTIFIERS, config, field, stage_copy, stage_cv

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SERVICES = BACKEND / "app" / "services"

S8_FILES = (
    SERVICES / "calculation_activation.py",
    SERVICES / "calculation_review.py",
    SERVICES / "jcs.py",
    BACKEND / "app" / "core" / "agent_context.py",
)
S8_DOCS = (
    ROOT / "manuals" / "calculation-configuration-s8.md",
    ROOT / "UAT_Scripts" / "uat-calculations-s8.md",
)

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"


# ---- RFC 8785 ------------------------------------------------------------------


def test_the_rfc_8785_sorting_example_orders_names_by_utf16_code_units() -> None:
    value = {
        "\u20ac": "Euro Sign",
        "\r": "Carriage Return",
        "\ufb33": "Hebrew Letter Dalet With Dagesh",
        "1": "One",
        "\U0001f600": "Emoji: Grinning Face",
        "\u0080": "Control",
        "\u00f6": "Latin Small Letter O With Diaeresis",
    }
    text = jcs.canonical_json(value)
    names = re.findall(r'"((?:[^"\\]|\\.)*)":"', text)
    assert names == ["\\r", "1", "\u0080", "\u00f6", "\u20ac", "\U0001f600", "\ufb33"]


def test_the_rfc_8785_string_example() -> None:
    value = "\u20ac$\u000f\u000aA'\u0042\u0022\u005c\\\"/"
    assert jcs.canonical_json(value) == '"\u20ac$\\u000f\\nA\'B\\"\\\\\\\\\\"/"'


def test_scalars_containers_and_whitespace() -> None:
    assert jcs.canonical_json(None) == "null"
    assert jcs.canonical_json(True) == "true"
    assert jcs.canonical_json(False) == "false"
    assert jcs.canonical_json(0) == "0"
    assert jcs.canonical_json(-7) == "-7"
    assert jcs.canonical_json({}) == "{}"
    assert jcs.canonical_json([]) == "[]"
    assert jcs.canonical_json({"b": [1, {"d": None, "c": True}], "a": "x"}) == (
        '{"a":"x","b":[1,{"c":true,"d":null}]}'
    )
    assert jcs.canonical_json("\u0000\u0008\u0009\u000a\u000c\u000d\u001f\u007f") == (
        '"\\u0000\\b\\t\\n\\f\\r\\u001f\u007f"'
    )


def test_canonical_form_does_not_depend_on_insertion_order() -> None:
    first = {"z": 1, "a": {"y": [1, 2], "b": "text"}, "m": None}
    second = {"m": None, "a": {"b": "text", "y": [1, 2]}, "z": 1}
    assert jcs.canonical_bytes(first) == jcs.canonical_bytes(second)
    assert jcs.canonical_sha256(first) == jcs.canonical_sha256(second)
    assert jcs.canonical_sha256(first) == hashlib.sha256(jcs.canonical_bytes(first)).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", jcs.canonical_sha256(first))


def test_a_changed_value_changes_the_hash() -> None:
    assert jcs.canonical_sha256({"a": 1}) != jcs.canonical_sha256({"a": 2})
    assert jcs.canonical_sha256({"a": [1, 2]}) != jcs.canonical_sha256({"a": [2, 1]})


def test_numbers_that_have_no_canonical_form_here_are_refused() -> None:
    for bad in (1.5, 0.1, float("nan"), float("inf"), 2**53, -(2**53), object(), b"x", {1: "a"}, "\ud800"):
        with pytest.raises(jcs.CanonicalizationError):
            jcs.canonical_json(bad)
    assert jcs.canonical_json(2**53 - 1) == str(2**53 - 1)


# ---- the validation state (OQ-CALC-12) -----------------------------------------


def test_validation_state_is_a_closed_list_derived_from_the_counts() -> None:
    assert VALIDATION_STATES == ("no_test_cases", "tests_none_passed", "tests_some_passed", "tests_all_passed")
    assert classify_state(0, 0) == "no_test_cases"
    assert classify_state(3, 0) == "tests_none_passed"
    assert classify_state(3, 2) == "tests_some_passed"
    assert classify_state(3, 3) == "tests_all_passed"
    assert classify_state(1, 1) == "tests_all_passed"
    assert not any("valid" in state for state in VALIDATION_STATES)


def test_the_confirm_control_names_the_no_test_case_choice() -> None:
    assert CONFIRM_LABEL == "Activate"
    assert CONFIRM_LABEL_NO_TESTS == "Activate with no test cases recorded"


# ---- the diff (CALC-REQ-45 item 6) --------------------------------------------


def _diff(old: Optional[Dict[str, Any]], new: Dict[str, Any], **extra: Any):
    return diff_configurations(
        old,
        new,
        old_order=extra.pop("old_order", 1),
        new_order=extra.pop("new_order", 1),
        old_saved_texts=extra.pop("old_saved_texts", {}),
        new_saved_texts=extra.pop("new_saved_texts", {}),
        units={},
        analytes={},
    )


def test_a_first_version_has_no_changes_to_list() -> None:
    assert _diff(None, config(stage_copy())) == []


def test_an_identical_configuration_has_no_changes() -> None:
    assert _diff(config(stage_copy()), config(stage_copy())) == []


def test_a_changed_binding_lists_the_old_and_new_binding() -> None:
    old = config(stage_copy())
    new = config(stage_copy())
    new["stages"][0]["bindings"]["value"] = field("OD 620")
    changes = _diff(old, new)
    assert len(changes) == 1
    change = changes[0]
    assert change["stage"] == "copy" and change["category"] == "binding" and change["field"] == "value"
    assert "OD 450" in change["old"] and "OD 620" in change["new"]


def test_a_changed_on_fail_declaration_lists_each_field() -> None:
    old = config(stage_copy())
    new = config(stage_copy(outcome="flag", flag="odd", precedence_place=3))
    changes = {(c["field"], c["old"], c["new"]) for c in _diff(old, new) if c["category"] == "on_fail"}
    assert ("outcome", "run_failed", "flag") in changes
    assert ("flag", None, "odd") in changes
    assert ("precedence_place", "1", "3") in changes


def test_a_changed_function_version_is_listed() -> None:
    old = config(stage_copy())
    new = config(stage_copy())
    new["stages"][0]["function_version"] = 2
    change = next(c for c in _diff(old, new) if c["category"] == "function_version")
    assert change["old"] == "copy_raw version 1" and change["new"] == "copy_raw version 2"


def _ad_hoc(text: str, version: int) -> Dict[str, Any]:
    return {
        "id": "calc",
        "kind": "ad_hoc_formula",
        "formula_text": text,
        "formula_version": version,
        "bindings": {"od": field("OD 450")},
        "on_fail": {"outcome": "run_failed", "flag": None, "gates": [], "precedence_place": 1},
    }


def _saved(name: str, version: int) -> Dict[str, Any]:
    return {
        "id": "calc",
        "kind": "saved_formula",
        "formula_name": name,
        "formula_version": version,
        "bindings": {"od": field("OD 450")},
        "on_fail": {"outcome": "run_failed", "flag": None, "gates": [], "precedence_place": 1},
    }


def test_a_changed_ad_hoc_formula_lists_old_and_new_text_and_version() -> None:
    old = config(_ad_hoc("od - 1", 1), result={"stage": "calc", "output": "result"})
    new = config(_ad_hoc("od - 2", 2), result={"stage": "calc", "output": "result"})
    changes = [c for c in _diff(old, new) if c["category"] == "formula_text"]
    assert len(changes) == 1
    assert changes[0]["old"] == "ad hoc formula version 1: od - 1"
    assert changes[0]["new"] == "ad hoc formula version 2: od - 2"


def test_a_changed_saved_formula_lists_old_and_new_name_version_and_text() -> None:
    old = config(_saved("blank_correct", 1), result={"stage": "calc", "output": "result"})
    new = config(_saved("blank_correct", 2), result={"stage": "calc", "output": "result"})
    changes = [
        c
        for c in _diff(
            old,
            new,
            old_saved_texts={("blank_correct", 1): "od - 1", ("blank_correct", 2): "od - 2"},
            new_saved_texts={("blank_correct", 1): "od - 1", ("blank_correct", 2): "od - 2"},
        )
        if c["category"] == "formula_text"
    ]
    assert len(changes) == 1
    assert changes[0]["old"] == "saved formula blank_correct version 1: od - 1"
    assert changes[0]["new"] == "saved formula blank_correct version 2: od - 2"


def test_an_unchanged_saved_formula_is_not_a_change() -> None:
    same = config(_saved("blank_correct", 1), result={"stage": "calc", "output": "result"})
    assert _diff(same, same, old_saved_texts={("blank_correct", 1): "od"}, new_saved_texts={("blank_correct", 1): "od"}) == []


def test_added_and_removed_stages_name_what_they_are() -> None:
    old = config(stage_copy("a"), stage_cv("b"))
    new = config(stage_copy("a"), stage_copy("c"), result={"stage": "a", "output": "calculated"})
    changes = {(c["stage"], c["field"]) for c in _diff(old, new) if c["category"] == "stage"}
    assert ("b", "removed") in changes and ("c", "added") in changes


def test_name_order_and_result_pointer_changes_are_listed() -> None:
    old = config(stage_copy(), name="one")
    new = config(stage_copy(), name="two", result={"stage": "copy", "output": "other"})
    fields = {c["field"] for c in _diff(old, new, new_order=2)}
    assert {"name", "calculation_order", "result_pointer"} <= fields
    pointer = next(c for c in _diff(old, new) if c["field"] == "result_pointer")
    assert pointer["old"].startswith("stage copy output") and pointer["new"] == "stage copy output other"


def test_binding_text_reads_each_kind_and_marks_a_direct_value_as_lab_bound() -> None:
    assert "field OD 450 of the experiment sample data entry" in binding_text(field("OD 450"), {}, {})
    assert "output mean of stage cv" in binding_text({"kind": "stage_output", "stage": "cv", "output": "mean"}, {}, {})
    reference = {"kind": "reference", "analyte_id": A, "value": "calculated"}
    assert binding_text(reference, {}, {A: "Protein"}) == "the calculated value of analyte Protein in the same run"
    assert "bound directly in the configuration" in binding_text({"kind": "direct", "value": "5.00"}, {}, {})
    assert binding_text(None, {}, {}) is None
    unit = binding_text({**field("x"), "unit_id": B}, {B: "mg/mL"}, {})
    assert unit.endswith("in unit mg/mL")


# ---- the agent: it proposes, it never activates (CALC-REQ-34, 47) --------------

CONFIG_PATH = f"/v1/analyses/{A}/analytes/{B}/calculation-config"


def test_the_agent_may_save_a_draft_and_record_test_cases() -> None:
    put = classify_call("PUT", CONFIG_PATH, {})
    assert put.ok and put.permission == "config:edit" and put.kind == "calculation_config"
    post = classify_call("POST", CONFIG_PATH + "/test-cases", {})
    assert post.ok and post.permission == "config:edit" and post.kind == "calculation_test_case"


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("POST", "/activate"),
        ("POST", "/activation-token"),
        ("GET", "/activation-review"),
        ("GET", "/activation-review/export"),
        ("GET", "/activations"),
        ("PUT", "/activate"),
        ("PATCH", "/activate"),
    ],
)
def test_no_activation_route_is_on_the_agent_allow_list(method: str, suffix: str) -> None:
    result = classify_call(method, CONFIG_PATH + suffix, {})
    assert result.ok is False
    assert result.gap == ACTIVATION_GAP


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_the_agent_cannot_change_the_catalog(method: str) -> None:
    for path in ("/v1/calculation-catalog", "/v1/calculation-catalog/fit_4pl"):
        result = classify_call(method, path, {"name": "elisa_4pl"})
        assert result.ok is False
        assert result.gap in (CATALOG_GAP, "Drop and delete are never applied by the configuring agent. "
                              "Retire a record with its status flag (Set inactive), or a container with Amount \u2192 0.")


def test_the_agent_cannot_delete_a_configuration_or_run_one() -> None:
    assert classify_call("DELETE", CONFIG_PATH).ok is False
    assert classify_call("PATCH", f"/v1/analyses/{A}/analytes/{B}/calculation-order", {}).ok is False
    assert classify_call("POST", f"/v1/analyses/{A}/new-version", {}).ok is False
    assert classify_call("POST", "/v1/calculation-formulas", {}).ok is False
    assert classify_call("POST", "/v1/lims-runs", {}).ok is False


def test_the_agent_route_formats_list_the_two_routes_and_say_a_proposal_is_inactive() -> None:
    rows = {f"{r['method']} {r['path']}": r for r in route_formats()}
    config_row = rows[f"PUT /v1/analyses/{{analysis_id}}/analytes/{{analyte_id}}/calculation-config"]
    assert "never active" in config_row["body"] and "Admin" in config_row["body"]
    assert f"POST /v1/analyses/{{analysis_id}}/analytes/{{analyte_id}}/calculation-config/test-cases" in rows
    text = route_formats_text()
    assert "activate" not in text.lower().replace("never active, and only an admin activates it", "")


def test_the_agent_context_is_set_by_the_executor_only() -> None:
    assert in_agent_context() is False
    refuse_in_agent_context("Activation")
    with agent_run_context():
        assert in_agent_context() is True
        with pytest.raises(Exception) as refused:
            refuse_in_agent_context("Activation")
        assert refused.value.status_code == 403
        assert refused.value.detail["code"] == "agent_context_refused"
    assert in_agent_context() is False


def test_the_agent_context_resets_after_an_error() -> None:
    with pytest.raises(RuntimeError):
        with agent_run_context():
            raise RuntimeError("boom")
    assert in_agent_context() is False


def test_no_header_or_field_sets_the_agent_context() -> None:
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (BACKEND / "app" / "routers").glob("*.py"))
    assert "agent_run_context" not in sources
    assert "_AGENT_RUN" not in sources
    users = [p for p in (BACKEND / "app").rglob("*.py") if "agent_run_context" in p.read_text(encoding="utf-8")]
    assert {p.name for p in users} == {"agent_context.py", "configuring_agent_apply.py"}


# ---- wording and parked constants (CALC-REQ-46, #258) --------------------------


def test_the_s8_files_use_validated_only_for_catalog_functions() -> None:
    migration = BACKEND / "db" / "migrations" / "versions" / "0126_calculation_activation.py"
    for path in (*S8_FILES, migration, *(p for p in S8_DOCS if p.exists())):
        for line in path.read_text(encoding="utf-8").splitlines():
            for match in re.finditer(r"validated", line, re.IGNORECASE):
                assert re.match(r"validated catalog functions?", line[match.start():], re.IGNORECASE), (path.name, line)


def test_the_s8_files_hold_no_parked_constant() -> None:
    for path in S8_FILES:
        source = path.read_text(encoding="utf-8")
        for identifier in PARKED_CONSTANT_IDENTIFIERS:
            assert identifier not in source, (path.name, identifier)


def test_s8_code_does_not_call_a_stage_output_a_result() -> None:
    source = (SERVICES / "calculation_review.py").read_text(encoding="utf-8")
    assert "published as the" in source
    for path in S8_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            assert "becomes the analyte's calculated value" not in line
            assert "stage output is a result" not in line.lower()


def test_s8_code_writes_nothing_to_result_tables() -> None:
    for path in S8_FILES:
        source = path.read_text(encoding="utf-8")
        for model in ("Result(", "ResultEntry", "models.result", "CalculationAttempt"):
            assert model not in source, (path.name, model)
