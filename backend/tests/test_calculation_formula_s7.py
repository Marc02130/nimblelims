"""Calculations S7: the lab-written formula language (CALC-REQ-23, 26, 27).

Pure tests: no database, no R. Expected values are worked out by hand or with
Python's ``statistics`` and ``fractions``, never by calling the code under test.
"""
from __future__ import annotations

import ast
import statistics
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from app.services.calculation_formula import (
    DIV_ZERO,
    KNOCKED_OUT,
    MAX_DEPTH,
    MAX_FORMULA_LENGTH,
    NOT_AVAILABLE,
    NUM_ERROR,
    RUN_TIME_ERRORS,
    VALUE_ERROR,
    FormulaSyntaxError,
    check_names,
    format_value,
    parse_formula,
    render_term,
    run_formula,
    term_name_error,
)

SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"


def run(text: str, **terms: Any) -> str:
    outcome = run_formula(parse_formula(text), terms)
    return outcome.error if outcome.stopped else format_value(outcome.value)


def refused(text: str) -> str:
    with pytest.raises(FormulaSyntaxError) as raised:
        parse_formula(text)
    return raised.value.code


# ---- ROUND is half-to-even (CALC-REQ-23) ------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ROUND(2.5, 0)", "2"),
        ("ROUND(3.5, 0)", "4"),
        ("ROUND(-2.5, 0)", "-2"),
        ("ROUND(-3.5, 0)", "-4"),
        ("ROUND(0.125, 2)", "0.12"),
        ("ROUND(0.135, 2)", "0.14"),
        ("ROUND(0.5, 0)", "0"),
        ("ROUND(1.5, 0)", "2"),
        ("ROUND(1250, -2)", "1200"),
        ("ROUND(1350, -2)", "1400"),
        ("ROUND(2.4999999, 0)", "2"),
    ],
)
def test_round_uses_half_to_even_on_an_exact_tie(text: str, expected: str) -> None:
    assert run(text) == expected


def test_round_of_2_5_is_never_3() -> None:
    assert run("ROUND(2.5, 0)") != "3"


def test_round_digits_out_of_range_is_num_error() -> None:
    assert run("ROUND(1.5, 1000)") == NUM_ERROR


# ---- STDEV divides by n-1, STDEV.P by n -------------------------------------

DATA = (2, 4, 4, 4, 5, 5, 7, 9)


def test_stdev_divides_by_n_minus_1_and_stdev_p_by_n() -> None:
    terms = {f"x{i}": str(v) for i, v in enumerate(DATA)}
    listing = ", ".join(terms)
    sample = Decimal(run(f"STDEV({listing})", **terms))
    population = Decimal(run(f"STDEV.P({listing})", **terms))
    assert population == Decimal(2)
    assert abs(float(sample) - statistics.stdev(DATA)) < 1e-12
    assert abs(float(population) - statistics.pstdev(DATA)) < 1e-12
    assert sample != population


def test_stdev_p_of_one_value_is_zero_and_stdev_of_one_value_is_div_zero() -> None:
    assert run("STDEV.P(a)", a="5") == "0"
    assert run("STDEV(a)", a="5") == DIV_ZERO


def test_stdev_over_a_braced_list_of_result_names() -> None:
    text = "STDEV({[Replicate 1], [Replicate 2], [Replicate 3]})"
    terms = {"Replicate 1": "1", "Replicate 2": "2", "Replicate 3": "3"}
    assert run(text, **terms) == "1"


# ---- errors: the four Excel messages (CALC-REQ-23, 26, 27) ------------------


def test_the_four_excel_error_texts() -> None:
    assert RUN_TIME_ERRORS == ("#DIV/0!", "#VALUE!", "#N/A", "#NUM!")


def test_division_by_zero_is_div_zero_and_never_a_number() -> None:
    assert run("1/0") == "#DIV/0!"
    assert run("a/b", a="4", b="0") == "#DIV/0!"
    assert run("1/(2-2)") == "#DIV/0!"


def test_missing_or_blank_input_is_n_a_and_never_zero() -> None:
    assert run("a+1", a=None) == NOT_AVAILABLE
    assert run("a+1", a="") == NOT_AVAILABLE
    assert run("a+1", a="   ") == NOT_AVAILABLE
    assert run("a+1") == NOT_AVAILABLE
    assert run("a*0", a=None) == NOT_AVAILABLE
    assert run("SUM(a, b)", a="1", b=None) == NOT_AVAILABLE


def test_knocked_out_result_is_n_a_and_never_zero() -> None:
    assert run("a+1", a=KNOCKED_OUT) == NOT_AVAILABLE
    assert run("a*0", a=KNOCKED_OUT) == NOT_AVAILABLE
    assert run("AVERAGE(a, b)", a="1", b=KNOCKED_OUT) == NOT_AVAILABLE


def test_text_that_is_not_a_number_is_value_error() -> None:
    assert run("a+1", a="abc") == VALUE_ERROR
    assert run("a+1", a="1,5") == VALUE_ERROR


@pytest.mark.parametrize(
    "text",
    ["SQRT(0-1)", "LN(0)", "LN(0-1)", "LOG10(0)", "LOG10(0-5)", "0^0", "(0-8)^0.5", "EXP(100000)", "2^1001"],
)
def test_num_errors(text: str) -> None:
    assert run(text) == NUM_ERROR


def test_boolean_in_arithmetic_is_value_error() -> None:
    assert run("TRUE+1") == VALUE_ERROR
    assert run("1=TRUE") == VALUE_ERROR
    assert run("IF(1, 2, 3)") == VALUE_ERROR


def test_a_formula_error_stops_only_that_formula() -> None:
    erroring = parse_formula("a/b")
    fine = parse_formula("a+b")
    terms = {"a": "6", "b": "0"}
    first = run_formula(erroring, terms)
    second = run_formula(fine, terms)
    assert first.stopped and first.error == DIV_ZERO and first.value is None
    assert not second.stopped and format_value(second.value) == "6"


def test_if_evaluates_only_the_branch_it_takes() -> None:
    assert run("IF(TRUE, 1, 1/0)") == "1"
    assert run("IF(FALSE, 1/0, 2)") == "2"
    assert run("IF(1<0, 1, 1/0)") == DIV_ZERO


# ---- arithmetic -------------------------------------------------------------


def test_decimal_arithmetic_is_exact_not_binary_float() -> None:
    assert run("0.1+0.2") == "0.3"
    assert run("0.1*3") == "0.3"
    assert run("1-0.9") == "0.1"
    assert run("a+b", a="0.1", b="0.2") == "0.3"


def test_precedence_follows_excel() -> None:
    assert run("2+3*4") == "14"
    assert run("(2+3)*4") == "20"
    assert run("-2^2") == "4"
    assert run("2^3^2") == "64"
    assert run("2^-1") == "0.5"
    assert run("10-4-3") == "3"
    assert run("100/10/5") == "2"


def test_division_keeps_fifty_digits_and_matches_fraction() -> None:
    value = Decimal(run("1/7"))
    assert value.as_tuple().exponent == -49 or len(value.as_tuple().digits) == 50
    assert abs(Fraction(value) - Fraction(1, 7)) < Fraction(1, 10**48)


def test_power_sqrt_and_logs() -> None:
    assert run("POWER(2, 10)") == "1024"
    assert run("SQRT(16)") == "4"
    assert run("LOG10(1000)") == "3"
    assert run("ABS(0-3.25)") == "3.25"
    assert abs(float(run("LN(10)")) - 2.302585092994046) < 1e-12
    assert abs(float(run("EXP(1)")) - 2.718281828459045) < 1e-12


def test_aggregates_and_count() -> None:
    assert run("SUM(1, 2, 3.5)") == "6.5"
    assert run("AVERAGE(1, 2, 4)").startswith("2.3333333333")
    assert run("MIN(3, 1, 2)") == "1"
    assert run("MAX(3, 1, 2)") == "3"
    assert run("COUNT(1, 2, 3)") == "3"
    assert run("SUM({1, 2, 3})") == "6"


def test_comparisons_and_logic() -> None:
    assert run("1<2") == "TRUE"
    assert run("2<=2") == "TRUE"
    assert run("3<>3") == "FALSE"
    assert run("AND(1<2, 2<3)") == "TRUE"
    assert run("OR(1>2, 2>3)") == "FALSE"
    assert run("NOT(1>2)") == "TRUE"
    assert run("IF(a>=b, 10, 20)", a="2", b="2") == "10"


def test_linest_forecast_trend_lookup() -> None:
    assert run("FORECAST(3, {1,3,5}, {0,1,2})") == "7"
    assert run("TREND({1,3,5}, {0,1,2}, {3,4})") == "{7, 9}"
    assert run("LOOKUP(5, {0, 10}, {1, 2})") == "1"
    assert run("LOOKUP(10, {0, 10}, {1, 2})") == "2"
    assert run("LOOKUP(0-1, {0, 10}, {1, 2})") == NOT_AVAILABLE
    assert run("FORECAST(1, {1,1}, {2,2})") == DIV_ZERO
    assert run("FORECAST(1, {1}, {2})") == NUM_ERROR


# ---- the grammar refuses what it must (CALC-REQ-23) -------------------------


def test_a_range_is_refused() -> None:
    assert refused("SUM(A1:A3)") == "formula_range_not_supported"
    assert refused("AVERAGE([Rep 1]:[Rep 3])") == "formula_range_not_supported"


@pytest.mark.parametrize(
    "text, code",
    [
        ("", "formula_empty"),
        ("   ", "formula_empty"),
        ("1+", "formula_syntax"),
        ("(1+2", "formula_syntax"),
        ("1+2)", "formula_syntax"),
        ("SUM(1,)", "formula_syntax"),
        ("1 2", "formula_syntax"),
        ("[open", "formula_syntax"),
        ("[]", "formula_syntax"),
        ("FOO(1)", "formula_unknown_function"),
        ("INDIRECT(1)", "formula_unknown_function"),
        ("ROUND(1)", "formula_arity"),
        ("ABS(1,2)", "formula_arity"),
        ("IF(1,2)", "formula_arity"),
        ("\"text\"", "formula_token_not_allowed"),
        ("'Sheet'!A1", "formula_token_not_allowed"),
        ("A1&B1", "formula_token_not_allowed"),
        ("5%", "formula_token_not_allowed"),
        ("$A$1", "formula_token_not_allowed"),
        ("a;b", "formula_token_not_allowed"),
        ("a\x00b", "formula_token_not_allowed"),
        ("{1,2}", "formula_list_misplaced"),
        ("{1,2}+1", "formula_list_misplaced"),
        ("LINEST({1,2},{1,2})+1", "formula_list_misplaced"),
        ("ROUND({1,2}, 0)", "formula_list_misplaced"),
        ("LOOKUP(1, 2, 3)", "formula_list_expected"),
        ("a.b", "formula_unknown_name"),
    ],
)
def test_outside_the_grammar_is_refused_at_save(text: str, code: str) -> None:
    assert refused(text) == code


def test_function_names_are_case_insensitive() -> None:
    assert run("round(2.5, 0)") == "2"
    assert run("Stdev.P(a)", a="5") == "0"


def test_unknown_name_is_refused_at_save_by_check_names() -> None:
    parsed = parse_formula("raw_od - blank_od")
    check_names(parsed, {"raw_od", "blank_od"})
    with pytest.raises(FormulaSyntaxError) as raised:
        check_names(parsed, {"raw_od"})
    assert raised.value.code == "formula_unknown_name"
    assert "blank_od" in raised.value.message


def test_a_result_name_is_a_term_and_has_no_unit() -> None:
    parsed = parse_formula("[Mean OD] - blank_od")
    assert parsed.names == {"Mean OD", "blank_od"}
    assert render_term("Mean OD") == "[Mean OD]"
    assert render_term("blank_od") == "blank_od"


def test_term_names() -> None:
    assert term_name_error("Mean OD") is None
    assert term_name_error("blank_od") is None
    assert term_name_error("") is not None
    assert term_name_error(" x") is not None
    assert term_name_error("a[b") is not None
    assert term_name_error("TRUE") is not None
    assert term_name_error("SUM") is not None
    assert term_name_error("x" * 101) is not None
    assert term_name_error(None) is not None


def test_limits_bound_the_evaluator() -> None:
    assert refused("1+" * (MAX_FORMULA_LENGTH // 2) + "1") == "formula_too_long"
    assert refused("(" * (MAX_DEPTH + 5) + "1" + ")" * (MAX_DEPTH + 5)) == "formula_too_deep"
    assert refused("-" * (MAX_DEPTH + 5) + "1") == "formula_too_deep"
    assert refused("+".join(["1"] * 600)) == "formula_too_complex"
    assert refused("SUM({" + ",".join(["1"] * 101) + "})") == "formula_too_complex"


def test_an_exponent_past_the_bound_stops_instead_of_running_long() -> None:
    assert run("10^100000") == NUM_ERROR
    assert run("2^0.5").startswith("1.41421356237309504880168872420969807856967187537")


# ---- no formula text is ever executed as code (CALC-REQ-23) ------------------


def _calls(path: Path) -> set[str]:
    """Bare calls such as ``eval(...)`` and dotted calls such as ``os.system(...)``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                names.add(f"{func.value.id}.{func.attr}")
    return names


@pytest.mark.parametrize(
    "module",
    [
        "calculation_formula.py",
        "calculation_config.py",
        "calculation_config_service.py",
    ],
)
def test_no_module_executes_text_as_code(module: str) -> None:
    called = _calls(SERVICES / module)
    assert not called & {
        "eval", "exec", "compile", "__import__", "os.system", "os.popen", "subprocess.run", "subprocess.Popen",
    }
    source = (SERVICES / module).read_text(encoding="utf-8")
    assert "import subprocess" not in source and "import os" not in source


def test_formula_text_that_looks_like_code_is_just_refused() -> None:
    for hostile in (
        "__import__('os').system('id')",
        "exec('1')",
        "a.__class__",
        "1; DROP TABLE analyses",
        "SUM(1) /* comment */",
    ):
        with pytest.raises(FormulaSyntaxError):
            parse_formula(hostile)
