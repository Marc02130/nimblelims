"""KAT harness test fixtures (calculations S2). Not catalog KATs.

Every function here is named ``harness_fixture_*``. None is one of the eleven
catalog functions (CALC-REQ-22), none is released, and none ships: the
backend image excludes ``tests/``. They exist only to prove the KAT runner,
the run log, and the release check. No value here comes from an SOP.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import httpx

from app.services.calculation_kat import FunctionVersion, KatCase, Quantity, Tolerance

HARNESS_CITATION = (
    "KAT harness test fixture, calculations S2 (not a catalog KAT, not an SOP): "
    "expected value is exact decimal arithmetic worked by hand and recorded with this case"
)
HARNESS_R_CITATION = (
    "KAT harness test fixture, calculations S2 (not a catalog KAT, not an SOP): "
    "expected string is Python 3 repr() of the same IEEE double, computed outside the R service"
)
HARNESS_FAILING_CITATION = (
    "KAT harness test fixture, calculations S2 (not a catalog KAT, not an SOP): "
    "expected value is deliberately wrong so the harness must report this case as failed"
)

UNITLESS = "1"


def _q(value: str, unit: str = UNITLESS) -> Quantity:
    return Quantity(value=value, unit=unit)


def _exact(unit: str = UNITLESS) -> Tolerance:
    return Tolerance(kind="absolute", value="0", unit=unit)


def harness_sum(inputs: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
    return {"total": inputs["a"] + inputs["b"]}


def harness_sum_calls_r(inputs: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
    httpx.get("http://r-calculator:8000/health", timeout=1.0)
    return {"total": inputs["a"] + inputs["b"]}


def sum_case(
    case_id: str = "hf-sum-exact",
    a: str = "2.522",
    b: str = "0.050",
    total: str = "2.572",
    citation: str = HARNESS_CITATION,
    tolerance: Tolerance | None = None,
    unit: str = UNITLESS,
) -> KatCase:
    return KatCase(
        case_id=case_id,
        inputs={"a": _q(a, unit), "b": _q(b, unit)},
        expected={"total": _q(total, unit)},
        tolerance={"total": tolerance if tolerance is not None else _exact(unit)},
        citation=citation,
    )


def backend_sum(
    version: int = 1,
    *,
    name: str = "harness_fixture_backend_sum",
    kats: tuple[KatCase, ...] | None = None,
    description: str = "total = a + b, in decimal",
    unit: str = UNITLESS,
    stop_rule: str = "none",
    missing_data_rule: str = "a missing a or b gives no total",
    defaults: Mapping[str, str] | None = None,
    compute=harness_sum,
) -> FunctionVersion:
    """A backend harness fixture version. Its KATs pass unless ``kats`` says otherwise."""
    return FunctionVersion(
        name=name,
        version=version,
        side="backend",
        description=description,
        inputs={"a": unit, "b": unit},
        outputs={"total": unit},
        stop_rule=stop_rule,
        missing_data_rule=missing_data_rule,
        kats=kats if kats is not None else (sum_case(unit=unit),),
        defaults=dict(defaults or {}),
        compute=compute,
    )


def failing_sum_case() -> KatCase:
    return sum_case(
        case_id="hf-sum-deliberately-wrong",
        total="2.573",
        citation=HARNESS_FAILING_CITATION,
    )


R_ROUND_TRIP_ROUTE = "/kat-harness/round-trip"

# Spec CALC-REQ-5 example strings. Each expected value is Python repr() of
# float(input); the input string already is that shortest form.
R_ROUND_TRIP_PASSING = (
    ("hf-r-0.026", "0.026", "0.026"),
    ("hf-r-neg-0.98", "-0.98", "-0.98"),
    ("hf-r-sum-0.1-0.2", "0.30000000000000004", "0.30000000000000004"),
    ("hf-r-one-third", "0.3333333333333333", "0.3333333333333333"),
)


def r_round_trip_case(case_id: str, value: str, expected: str, citation: str) -> KatCase:
    return KatCase(
        case_id=case_id,
        inputs={"value": _q(value)},
        expected={"value": _q(expected)},
        tolerance={"value": _exact()},
        citation=citation,
    )


# Synthetic array fixture. Not a catalog case and not a release. The three
# values are the known parameter 1.25 repeated, so the total is exact in decimal.
ARRAY_LEVEL = "1.25"
ARRAY_CITATION = (
    "Harness unit-test fixture (not a catalog case): synthetic values generated "
    "from the known parameter 1.25; the expected total is their exact decimal sum"
)
# x and y are the exact line y = 0.5 + 2x. Replicates are two copies of each y.
VECTOR_SLOPE = "2"
VECTOR_INTERCEPT = "0.5"
VECTOR_X = ("1", "2", "4", "8")
VECTOR_CITATION = (
    "Harness unit-test fixture (not a catalog case): synthetic x and y generated "
    "from slope 2 and intercept 0.5; replicates are two copies of each y"
)


def harness_array_sum(inputs: Mapping[str, Any]) -> Mapping[str, Decimal]:
    total = Decimal(0)
    for value in inputs["values"]:
        total += value
    return {"total": total}


def array_sum_case() -> KatCase:
    level = Decimal(ARRAY_LEVEL)
    values = tuple(ARRAY_LEVEL for _ in range(3))
    return KatCase(
        case_id="hf-array-sum-synthetic",
        inputs={"values": Quantity(value=values, unit=UNITLESS)},
        expected={"total": _q(str(level * len(values)))},
        tolerance={"total": _exact()},
        citation=ARRAY_CITATION,
    )


def backend_array_sum() -> FunctionVersion:
    """Backend harness fixture whose only input is an array of decimal strings."""
    return FunctionVersion(
        name="harness_fixture_array_sum",
        version=1,
        side="backend",
        description="total = the exact decimal sum of an array of values",
        inputs={"values": UNITLESS},
        outputs={"total": UNITLESS},
        stop_rule="none",
        missing_data_rule="an empty array sums to 0",
        kats=(array_sum_case(),),
        compute=harness_array_sum,
    )


def vector_case() -> KatCase:
    """Concentration, response, and replicate arrays a fit case would send.

    The expected echo is 1. This case checks that the harness posts the arrays.
    It does not check a fit.
    """
    slope = Decimal(VECTOR_SLOPE)
    intercept = Decimal(VECTOR_INTERCEPT)
    ys = tuple(str(intercept + slope * Decimal(x)) for x in VECTOR_X)
    replicates = tuple((y, y) for y in ys)
    return KatCase(
        case_id="hf-array-vectors-synthetic",
        inputs={
            "concentration": Quantity(value=VECTOR_X, unit=UNITLESS),
            "response": Quantity(value=ys, unit=UNITLESS),
            "replicates": Quantity(value=replicates, unit=UNITLESS),
        },
        expected={"echo": _q("1")},
        tolerance={"echo": _exact()},
        citation=VECTOR_CITATION,
    )


def r_vectors() -> FunctionVersion:
    """R-side harness fixture that posts array inputs. The route is a test double."""
    return FunctionVersion(
        name="harness_fixture_array_vectors",
        version=1,
        side="r",
        description="posts concentration, response, and replicate arrays unchanged",
        inputs={"concentration": UNITLESS, "response": UNITLESS, "replicates": UNITLESS},
        outputs={"echo": UNITLESS},
        stop_rule="none",
        missing_data_rule="none",
        kats=(vector_case(),),
        route="/kat-harness/array-vectors",
    )


def r_round_trip(version: int = 1, *, with_failing_case: bool = False) -> FunctionVersion:
    """R-side harness fixture against the pinned image's harness route."""
    kats = [r_round_trip_case(cid, v, e, HARNESS_R_CITATION) for cid, v, e in R_ROUND_TRIP_PASSING]
    if with_failing_case:
        kats.append(
            r_round_trip_case(
                "hf-r-deliberately-wrong",
                "0.1",
                "0.2",
                HARNESS_FAILING_CITATION,
            )
        )
    return FunctionVersion(
        name="harness_fixture_r_round_trip",
        version=version,
        side="r",
        description="R parses one decimal string as a double and returns its shortest round-trip string",
        inputs={"value": UNITLESS},
        outputs={"value": UNITLESS},
        stop_rule="a value that is not one finite decimal string is refused",
        missing_data_rule="a missing value is refused",
        kats=tuple(kats),
        route=R_ROUND_TRIP_ROUTE,
        r_sources=("R/serialise.R",),
    )
