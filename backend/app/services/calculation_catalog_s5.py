"""Backend decimal catalog functions v1 for S5 (CALC-REQ-14, 18, 19, 37, 22).

``replicate_mean_cv``, ``spike_recovery``, and ``limit_compare``.
Arithmetic uses Python ``decimal`` at precision 50 with ``ROUND_HALF_EVEN``.
``sqrt`` uses that context. None of these functions calls R, and none has an
R route (CALC-REQ-24).

Decisions Marc stated for this slice, implemented here. The Spec text is
unchanged.

- OQ-CALC-5: %CV uses the sample standard deviation, dividing by n−1, the
  same quantity as Excel STDEV. The function stays generic. It does not
  choose onset time or concentration. A configuration binds whichever
  numeric replicates it wants. Which of those the LAL configuration binds
  is still open.
- OQ-CALC-6: recovery % = (spiked − unspiked) × 100 ÷ nominal spike.
- OQ-51, clarified: ``limit_compare`` compares the one value it is given.
  The formula chooses that value (the numeric calculated result, or the
  qualified reported result such as ``>100``). This function does not
  choose between those fields and does not format a reported result.
  Qualified ``<`` and ``>`` values against an at-most limit follow
  CALC-REQ-19. No conflict with that rule was found: the rule judges a
  qualified value when that is the value passed in. It does not decide
  which field is passed in, and it does not say this function writes the
  reported text.

Nothing here writes an attempt or a result (S9). The versions below are
declared with KATs and are not released: S5 does not write a release record.
"""
from __future__ import annotations

import decimal
import re
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.calculation_catalog_decimal import (
    _context,
    _http_refusal,
    _http_result,
    _json_object,
    _optional_input,
    _reject_unknown,
    format_decimal,
)
from app.services.calculation_catalog_r import (
    MISSING_INPUT,
    CatalogInputRefused,
    StageResult,
    is_decimal_string,
)
from app.services.calculation_kat import (
    NO_UNIT,
    TOKEN_UNIT,
    FunctionVersion,
    KatCase,
    Quantity,
    Tolerance,
)

REPLICATE_MISSING = "replicate_missing"
MEAN_ZERO = "mean_zero"
LIMIT_ABOVE_EL = "limit_above_el"
LIMIT_BELOW_EL = "limit_below_el"

AT_MOST = "at_most"
AT_LEAST = "at_least"
WITHIN = "within"
COMPARISONS = (AT_MOST, AT_LEAST, WITHIN)

# Not review flags. ``missing_limit`` means the stage's own flag is not
# chosen here. ``unspecified`` means CALC-REQ-19 states no qualified rule
# for that form.
MISSING_LIMIT = "missing_limit"
UNSPECIFIED = "unspecified"

REPLICATE_UNIT = "the replicate unit"
SHARED_UNIT = "shared unit"
PERCENT = "%"
ABSOLUTE_UNIT = "1"

_DECIMAL_BODY = r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
QUALIFIED_RE = re.compile(rf"^([<>])({_DECIMAL_BODY})$")

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HUNDRED = Decimal(100)


def _quantity(value: str, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit)


def _exact(unit: str) -> Tolerance:
    return Tolerance(kind="absolute", value="0", unit=unit)


def _mean_decimal(values: tuple[Decimal, ...]) -> Decimal:
    with decimal.localcontext(_context()):
        return sum(values, _ZERO) / Decimal(len(values))


def replicate_mean_cv_compute(inputs: Mapping[str, Any]) -> Mapping[str, str]:
    """Mean and sample %CV. Divides by n−1. Needs two or more values and a non-zero mean."""
    raw = inputs["replicates"]
    if isinstance(raw, list):
        values = tuple(raw)
    elif isinstance(raw, tuple):
        values = raw
    else:
        raise CatalogInputRefused("replicates must be an array")
    if len(values) < 2:
        raise CatalogInputRefused("percent cv needs at least two replicates")
    with decimal.localcontext(_context()):
        mean = sum(values, _ZERO) / Decimal(len(values))
        if mean == 0:
            raise CatalogInputRefused("percent cv is not defined when the mean is 0")
        sum_sq = sum(((value - mean) * (value - mean) for value in values), _ZERO)
        variance = sum_sq / Decimal(len(values) - 1)
        standard_deviation = variance.sqrt()
        percent_cv = (standard_deviation * _HUNDRED) / mean
        return {
            "mean": format_decimal(mean),
            "percent_cv": format_decimal(percent_cv),
        }


def spike_recovery_compute(inputs: Mapping[str, Decimal]) -> Mapping[str, str]:
    """(spiked − unspiked) × 100 ÷ nominal spike. One division, last."""
    nominal = inputs["nominal_spike"]
    if nominal <= 0:
        raise CatalogInputRefused("nominal spike is not greater than 0")
    with decimal.localcontext(_context()):
        recovery = ((inputs["spiked"] - inputs["unspiked"]) * _HUNDRED) / nominal
        return {"recovery": format_decimal(recovery)}


def numeric_verdict(
    value: Decimal,
    comparison: str,
    *,
    limit: Optional[Decimal] = None,
    low: Optional[Decimal] = None,
    high: Optional[Decimal] = None,
    absolute: bool = False,
) -> str:
    """Inclusive numeric comparison. Does not round the value or the bound."""
    if comparison not in COMPARISONS:
        raise CatalogInputRefused("comparison must be at_most, at_least, or within")
    compared = abs(value) if absolute else value
    with decimal.localcontext(_context()):
        if comparison == AT_MOST:
            if limit is None:
                raise CatalogInputRefused("at_most needs a limit")
            return "pass" if compared <= limit else "fail"
        if comparison == AT_LEAST:
            if limit is None:
                raise CatalogInputRefused("at_least needs a limit")
            return "pass" if compared >= limit else "fail"
        if low is None or high is None:
            raise CatalogInputRefused("within needs a low and a high")
        if low > high:
            raise CatalogInputRefused("the low bound is above the high bound")
        return "pass" if low <= compared <= high else "fail"


def limit_compare_compute(inputs: Mapping[str, Any]) -> Mapping[str, str]:
    """KAT path: numeric value only. ``comparison`` is a token. ``absolute`` is 0 or 1."""
    absolute = inputs["absolute"]
    if not isinstance(absolute, Decimal) or absolute not in (_ZERO, _ONE):
        raise CatalogInputRefused("absolute must be 0 or 1")
    comparison = inputs["comparison"]
    if not isinstance(comparison, str):
        raise CatalogInputRefused("comparison must be a token")
    verdict = numeric_verdict(
        inputs["value"],
        comparison,
        limit=inputs["limit"],
        low=inputs["low"],
        high=inputs["high"],
        absolute=absolute == _ONE,
    )
    return {"verdict": verdict}


# ---- KATs ------------------------------------------------------------------

_MEAN_CITATION = (
    "CALC-REQ-14 acceptance criterion, worked by hand outside this function "
    "and recorded with this case: the mean of 1400.1 and 1400.3 is 1400.2. "
    "The %CV is the sample standard deviation (divide by n-1; Marc, "
    "2026-11-17, Excel STDEV) over that mean, times 100, from Python decimal "
    "precision 50 and ROUND_HALF_EVEN, computed outside this function. "
    "The function does not read a unit. These two numbers are also valid "
    "onset times in s. Not an SOP and not a configuration constant."
)
_TIME_CITATION = (
    "Onset times 100 s and 110 s, and the CALC-REQ-14 acceptance criterion "
    "for replicates 100 and 110. Sample standard deviation divides by n-1 "
    "(Marc, 2026-11-17, Excel STDEV). The mean 105 is exact. The %CV was "
    "computed outside this function with Python decimal precision 50 and "
    "ROUND_HALF_EVEN. The function does not read the unit s. A configuration "
    "may bind onset times or concentrations. Which one the LAL configuration "
    "binds is still open. Not an SOP and not a configuration constant."
)
_CONCENTRATION_CITATION = (
    "Concentrations 0.01, 0.02, and 0.03, worked by hand outside this "
    "function: the mean is 0.02. Squared deviations sum to 0.0002. The "
    "sample variance divides by n-1 = 2, so the variance is 0.0001, the "
    "standard deviation is 0.01, and the %CV is 50. Dividing by n would not "
    "give 50 (Marc, 2026-11-17, Excel STDEV). The function does not read a "
    "concentration unit. Not an SOP and not a configuration constant."
)
_SPIKE_100_CITATION = (
    "CALC-REQ-18 example, worked by hand outside this function and recorded "
    "with this case: (0.06 - 0.01) x 100 / 0.05 = 100. The numbers are not "
    "a required spike. Not an SOP and not a configuration constant."
)
_SPIKE_50_CITATION = (
    "CALC-REQ-18 and CALC-REQ-37 example, worked by hand outside this "
    "function: (0.026 - 0.001) x 100 / 0.05 = 50 exactly in decimal. "
    "Not an SOP and not a configuration constant."
)
_SPIKE_200_CITATION = (
    "CALC-REQ-18 and CALC-REQ-37 example, worked by hand outside this "
    "function: (0.171 - 0.071) x 100 / 0.05 = 200 exactly in decimal. "
    "The same subtraction in binary floating point is not 200. Not an SOP "
    "and not a configuration constant."
)
_LIMIT_CITATION = (
    "CALC-REQ-19 acceptance criterion, worked by hand outside this function. "
    "Bounds are inclusive. The value is not rounded before the compare. "
    "The numbers are not assay rules. Not an SOP and not a configuration constant."
)


def _replicate_case(
    case_id: str,
    replicates: tuple[str, ...],
    mean: str,
    percent_cv: str,
    citation: str,
) -> KatCase:
    return KatCase(
        case_id=case_id,
        inputs={"replicates": Quantity(value=replicates, unit=REPLICATE_UNIT)},
        expected={
            "mean": _quantity(mean, REPLICATE_UNIT),
            "percent_cv": _quantity(percent_cv, PERCENT),
        },
        tolerance={
            "mean": _exact(REPLICATE_UNIT),
            "percent_cv": _exact(PERCENT),
        },
        citation=citation,
    )


def _spike_case(
    case_id: str, spiked: str, unspiked: str, nominal: str, recovery: str, citation: str
) -> KatCase:
    return KatCase(
        case_id=case_id,
        inputs={
            "spiked": _quantity(spiked, SHARED_UNIT),
            "unspiked": _quantity(unspiked, SHARED_UNIT),
            "nominal_spike": _quantity(nominal, SHARED_UNIT),
        },
        expected={"recovery": _quantity(recovery, PERCENT)},
        tolerance={"recovery": _exact(PERCENT)},
        citation=citation,
    )


def _limit_case(
    case_id: str,
    comparison: str,
    value: str,
    limit: str,
    low: str,
    high: str,
    absolute: str,
    verdict: str,
) -> KatCase:
    return KatCase(
        case_id=case_id,
        inputs={
            "comparison": Quantity(value=comparison, unit=TOKEN_UNIT),
            "value": _quantity(value, SHARED_UNIT),
            "limit": _quantity(limit, SHARED_UNIT),
            "low": _quantity(low, SHARED_UNIT),
            "high": _quantity(high, SHARED_UNIT),
            "absolute": _quantity(absolute, ABSOLUTE_UNIT),
        },
        expected={"verdict": Quantity(value=verdict, unit=NO_UNIT)},
        tolerance={"verdict": _exact(NO_UNIT)},
        citation=_LIMIT_CITATION,
    )


# ---- declarations ----------------------------------------------------------

REPLICATE_MEAN_CV_V1 = FunctionVersion(
    name="replicate_mean_cv",
    version=1,
    side="backend",
    description=(
        "Arithmetic mean of the numeric replicates, and percent CV = sample "
        "standard deviation / mean x 100. The sample standard deviation divides "
        "the sum of squared deviations by n-1, matching Excel STDEV (Marc, "
        "2026-11-17). sqrt runs in the precision-50 decimal context. The "
        "function does not read a unit and does not choose onset time or "
        "concentration. A configuration binds the replicates."
    ),
    inputs={"replicates": REPLICATE_UNIT},
    outputs={"mean": REPLICATE_UNIT, "percent_cv": PERCENT},
    stop_rule=(
        "A mean of 0 gives that mean, no percent CV, and the flag mean_zero. "
        "It is not a stage stop. The Spec names a flag and does not name this spelling."
    ),
    missing_data_rule=(
        "No numeric replicate gives no mean and missing_input. Fewer than two "
        "numeric replicates gives the mean, no percent CV, and replicate_missing. "
        "A non-numeric replicate is left out and is never treated as zero."
    ),
    kats=(
        _replicate_case(
            "replicate-mean-1400.1-1400.3",
            ("1400.1", "1400.3"),
            "1400.2",
            "0.010100082576582595692056054308025268380014796995978",
            _MEAN_CITATION,
        ),
        _replicate_case(
            "replicate-onset-time-100s-110s",
            ("100", "110"),
            "105",
            "6.7343502970147383276270891629033241836651041684616",
            _TIME_CITATION,
        ),
        _replicate_case(
            "replicate-concentration-0.01-0.02-0.03",
            ("0.01", "0.02", "0.03"),
            "0.02",
            "50",
            _CONCENTRATION_CITATION,
        ),
    ),
    compute=replicate_mean_cv_compute,
)

SPIKE_RECOVERY_V1 = FunctionVersion(
    name="spike_recovery",
    version=1,
    side="backend",
    description=(
        "recovery = (spiked - unspiked) x 100 / nominal spike. The difference "
        "is multiplied by 100, and that product is divided once by the nominal "
        "spike. The nominal spike is an input. It is not a number in this function."
    ),
    inputs={
        "spiked": SHARED_UNIT,
        "unspiked": SHARED_UNIT,
        "nominal_spike": SHARED_UNIT,
    },
    outputs={"recovery": PERCENT},
    stop_rule=(
        "No stage stop. A nominal spike that is not greater than 0 is refused. "
        "The refusal is not a stage stop."
    ),
    missing_data_rule=(
        "No spiked value, no unspiked value, or no nominal spike gives no "
        "recovery and missing_input. A qualified string is not numeric, so it "
        "is missing here. How a configuration supplies a qualified unspiked "
        "value is open (OQ-CALC-7). A missing input is never replaced with zero."
    ),
    kats=(
        _spike_case("spike-0.06-0.01-0.05-is-100", "0.06", "0.01", "0.05", "100", _SPIKE_100_CITATION),
        _spike_case(
            "spike-0.026-0.001-0.05-is-50", "0.026", "0.001", "0.05", "50", _SPIKE_50_CITATION
        ),
        _spike_case(
            "spike-0.171-0.071-0.05-is-200", "0.171", "0.071", "0.05", "200", _SPIKE_200_CITATION
        ),
    ),
    compute=spike_recovery_compute,
)

LIMIT_COMPARE_V1 = FunctionVersion(
    name="limit_compare",
    version=1,
    side="backend",
    description=(
        "Compares the one value it is given. The calculation formula chooses "
        "that value, either the numeric calculated result or the qualified "
        "reported result. This function does not choose between those fields "
        "and does not format a reported result. A numeric comparison is "
        "at_most (value <= limit), at_least (value >= limit), or within "
        "(low <= value <= high). Every bound is inclusive. The absolute "
        "switch compares the absolute value and does not round first. A "
        "qualified value stored < or > is judged only for at_most, using the "
        "limit written after the symbol. For <, a stored limit at or under "
        "the bound passes, and a stored limit above the bound gives no "
        "verdict and limit_above_el. For >, a stored limit at or above the "
        "bound fails, and a stored limit below the bound gives no verdict "
        "and limit_below_el. The kind that was supplied is returned with the "
        "outcome."
    ),
    inputs={
        "comparison": TOKEN_UNIT,
        "value": SHARED_UNIT,
        "limit": SHARED_UNIT,
        "low": SHARED_UNIT,
        "high": SHARED_UNIT,
        "absolute": ABSOLUTE_UNIT,
    },
    outputs={"verdict": NO_UNIT},
    stop_rule=(
        "No stage stop. An unknown comparison, a low bound above the high "
        "bound, a kind on a numeric value, or absolute on a qualified value "
        "is refused. The refusal is not a stage stop."
    ),
    missing_data_rule=(
        "No numeric or qualified value gives no verdict and missing_input. "
        "No bound for the form gives no verdict and does not set a flag; the "
        "stage declaration names that flag. A qualified value on at_least or "
        "within gives no verdict and no flag, because CALC-REQ-19 states the "
        "qualified rules for at most only. A missing input is never zero."
    ),
    kats=(
        _limit_case("limit-at-most-0.5-passes", AT_MOST, "0.5", "0.5", "0", "1", "0", "pass"),
        _limit_case("limit-at-most-0.6-fails", AT_MOST, "0.6", "0.5", "0", "1", "0", "fail"),
        _limit_case(
            "limit-at-least-abs-0.98-passes", AT_LEAST, "-0.98", "0.980", "0", "1", "1", "pass"
        ),
        _limit_case(
            "limit-at-least-abs-0.97995-fails",
            AT_LEAST,
            "-0.97995",
            "0.980",
            "0",
            "1",
            "1",
            "fail",
        ),
        _limit_case("limit-within-50-passes", WITHIN, "50", "0", "50", "200", "0", "pass"),
        _limit_case("limit-within-200-passes", WITHIN, "200", "0", "50", "200", "0", "pass"),
        _limit_case("limit-within-49-fails", WITHIN, "49", "1000", "50", "200", "0", "fail"),
    ),
    compute=limit_compare_compute,
)

S5_CATALOG_VERSIONS: tuple[FunctionVersion, ...] = (
    REPLICATE_MEAN_CV_V1,
    SPIKE_RECOVERY_V1,
    LIMIT_COMPARE_V1,
)


# ---- public functions ------------------------------------------------------


def _numeric_replicate_strings(replicates: Any) -> list[str]:
    if isinstance(replicates, (str, bytes)) or not isinstance(replicates, Sequence):
        raise CatalogInputRefused("replicates must be an array of decimal strings")
    found: list[str] = []
    for index, item in enumerate(replicates):
        if item is None:
            continue
        if isinstance(item, bool) or not isinstance(item, str):
            raise CatalogInputRefused(
                f"replicates[{index}] must be a decimal string, not {type(item).__name__}"
            )
        if is_decimal_string(item):
            found.append(item)
    return found


def replicate_mean_cv(replicates: Any) -> StageResult:
    """Mean and sample %CV of whatever numeric replicates the caller binds. No R call."""
    fv = REPLICATE_MEAN_CV_V1
    if replicates is None:
        return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))
    numeric = _numeric_replicate_strings(replicates)
    if not numeric:
        return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))
    parsed = tuple(Decimal(item) for item in numeric)
    if len(parsed) < 2:
        return StageResult(
            fv.name,
            fv.version,
            {"mean": format_decimal(_mean_decimal(parsed))},
            False,
            flags=(REPLICATE_MISSING,),
        )
    if _mean_decimal(parsed) == 0:
        return StageResult(fv.name, fv.version, {"mean": "0"}, False, flags=(MEAN_ZERO,))
    return StageResult(fv.name, fv.version, dict(replicate_mean_cv_compute({"replicates": parsed})), False)


def spike_recovery(spiked: Any, unspiked: Any, nominal_spike: Any) -> StageResult:
    """Recovery percent from the three decimal strings. No R call. No default nominal."""
    fv = SPIKE_RECOVERY_V1
    nominal_text = _optional_input(nominal_spike, "nominal_spike")
    spiked_text = _optional_input(spiked, "spiked")
    unspiked_text = _optional_input(unspiked, "unspiked")
    if nominal_text is not None and Decimal(nominal_text) <= 0:
        raise CatalogInputRefused("nominal spike is not greater than 0")
    if spiked_text is None or unspiked_text is None or nominal_text is None:
        return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))
    outputs = spike_recovery_compute(
        {
            "spiked": Decimal(spiked_text),
            "unspiked": Decimal(unspiked_text),
            "nominal_spike": Decimal(nominal_text),
        }
    )
    return StageResult(fv.name, fv.version, dict(outputs), False)


def _parse_kind(kind: Any) -> Optional[str]:
    if kind is None:
        return None
    if not isinstance(kind, str):
        raise CatalogInputRefused(f"kind must be a string, not {type(kind).__name__}")
    if kind.strip() == "":
        return None
    return kind


def _parse_subject(value: Any, kind: Any) -> tuple[Any, ...]:
    """``("missing",)``, ``("numeric", Decimal)``, or a qualified tuple.

    A qualified tuple is ``("qualified", symbol, limit_text, Decimal, kind)``.
    """
    outer_kind = _parse_kind(kind)
    if value is None:
        if outer_kind is not None:
            raise CatalogInputRefused("kind belongs to a qualified value")
        return ("missing",)
    if isinstance(value, str):
        if is_decimal_string(value):
            if outer_kind is not None:
                raise CatalogInputRefused("kind belongs to a qualified value")
            return ("numeric", Decimal(value))
        match = QUALIFIED_RE.fullmatch(value)
        if match is not None:
            limit_text = match.group(2)
            return ("qualified", match.group(1), limit_text, Decimal(limit_text), outer_kind)
        if value[:1] in "<>":
            raise CatalogInputRefused(
                "qualified value must be < or > followed by a decimal string"
            )
        return ("missing",)
    if isinstance(value, Mapping):
        extra = sorted(set(value) - {"qualifier", "limit", "kind"})
        if extra:
            raise CatalogInputRefused("unknown field: " + ", ".join(extra))
        symbol = value.get("qualifier")
        if symbol not in ("<", ">"):
            raise CatalogInputRefused("qualifier must be < or >")
        limit_text = value.get("limit")
        if not isinstance(limit_text, str) or not is_decimal_string(limit_text):
            raise CatalogInputRefused("a qualified value needs a decimal limit")
        inner_kind = _parse_kind(value.get("kind"))
        if inner_kind is not None and outer_kind is not None and inner_kind != outer_kind:
            raise CatalogInputRefused("kind is given twice and the two differ")
        return (
            "qualified",
            symbol,
            limit_text,
            Decimal(limit_text),
            inner_kind if inner_kind is not None else outer_kind,
        )
    raise CatalogInputRefused(
        f"value must be a decimal string or a qualified value, not {type(value).__name__}"
    )


def _bound(value: Any, name: str) -> Optional[Decimal]:
    text = _optional_input(value, name)
    if text is None:
        return None
    return Decimal(text)


def _bound_missing(comparison: str, limit: Optional[Decimal], low: Optional[Decimal], high: Optional[Decimal]) -> bool:
    if comparison == WITHIN:
        return low is None or high is None
    return limit is None


def _stage(
    outputs: Mapping[str, str],
    *,
    flags: tuple[str, ...] = (),
    qualifier: Optional[str] = None,
    qualifier_limit: Optional[str] = None,
    kind: Optional[str] = None,
    no_verdict: Optional[str] = None,
) -> StageResult:
    return StageResult(
        LIMIT_COMPARE_V1.name,
        LIMIT_COMPARE_V1.version,
        dict(outputs),
        False,
        flags=flags,
        qualifier=qualifier,
        qualifier_limit=qualifier_limit,
        kind=kind,
        no_verdict=no_verdict,
    )


def _qualified_at_most(symbol: str, stored: Decimal, bound: Decimal) -> tuple[str, Optional[str]]:
    """CALC-REQ-19 at-most rules. Returns ``(verdict, flag)``. One of them is empty."""
    with decimal.localcontext(_context()):
        if symbol == "<":
            if stored <= bound:
                return "pass", None
            return "", LIMIT_ABOVE_EL
        if stored >= bound:
            return "fail", None
        return "", LIMIT_BELOW_EL


def limit_compare(
    value: Any,
    *,
    comparison: str,
    limit: Any = None,
    low: Any = None,
    high: Any = None,
    absolute: bool = False,
    kind: Any = None,
) -> StageResult:
    """Compare the value the caller passes. No R call. No choice of calculated versus reported."""
    if not isinstance(comparison, str) or comparison not in COMPARISONS:
        raise CatalogInputRefused("comparison must be at_most, at_least, or within")
    if not isinstance(absolute, bool):
        raise CatalogInputRefused("absolute must be a boolean")
    subject = _parse_subject(value, kind)
    parsed_limit = _bound(limit, "limit")
    parsed_low = _bound(low, "low")
    parsed_high = _bound(high, "high")
    if (
        comparison == WITHIN
        and parsed_low is not None
        and parsed_high is not None
        and parsed_low > parsed_high
    ):
        raise CatalogInputRefused("the low bound is above the high bound")
    if subject[0] == "missing":
        return _stage({}, flags=(MISSING_INPUT,))
    if _bound_missing(comparison, parsed_limit, parsed_low, parsed_high):
        if subject[0] == "qualified":
            return _stage(
                {},
                qualifier=subject[1],
                qualifier_limit=subject[2],
                kind=subject[4],
                no_verdict=MISSING_LIMIT,
            )
        return _stage({}, no_verdict=MISSING_LIMIT)
    if subject[0] == "qualified":
        symbol, limit_text, stored, stored_kind = subject[1], subject[2], subject[3], subject[4]
        if absolute:
            raise CatalogInputRefused("absolute applies to a numeric value")
        if comparison != AT_MOST:
            return _stage(
                {},
                qualifier=symbol,
                qualifier_limit=limit_text,
                kind=stored_kind,
                no_verdict=UNSPECIFIED,
            )
        if parsed_limit is None:
            return _stage(
                {},
                qualifier=symbol,
                qualifier_limit=limit_text,
                kind=stored_kind,
                no_verdict=MISSING_LIMIT,
            )
        verdict, flag = _qualified_at_most(symbol, stored, parsed_limit)
        if flag is not None:
            return _stage(
                {},
                flags=(flag,),
                qualifier=symbol,
                qualifier_limit=limit_text,
                kind=stored_kind,
            )
        return _stage(
            {"verdict": verdict},
            qualifier=symbol,
            qualifier_limit=limit_text,
            kind=stored_kind,
        )
    verdict = numeric_verdict(
        subject[1],
        comparison,
        limit=parsed_limit,
        low=parsed_low,
        high=parsed_high,
        absolute=absolute,
    )
    return _stage({"verdict": verdict})


# ---- HTTP ------------------------------------------------------------------


def s5_catalog_router() -> APIRouter:
    """Status-code contract for the three functions. Not mounted on the LIMS app."""
    router = APIRouter()

    @router.post("/catalog/replicate_mean_cv/v1")
    async def post_replicate_mean_cv(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            _reject_unknown(body, {"replicates"})
            result = replicate_mean_cv(body.get("replicates"))
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    @router.post("/catalog/spike_recovery/v1")
    async def post_spike_recovery(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            _reject_unknown(body, {"spiked", "unspiked", "nominal_spike"})
            result = spike_recovery(
                body.get("spiked"), body.get("unspiked"), body.get("nominal_spike")
            )
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    @router.post("/catalog/limit_compare/v1")
    async def post_limit_compare(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            comparison = body.get("comparison")
            if comparison in (AT_MOST, AT_LEAST):
                _reject_unknown(body, {"comparison", "value", "limit", "absolute", "kind"})
            elif comparison == WITHIN:
                _reject_unknown(body, {"comparison", "value", "low", "high", "absolute", "kind"})
            else:
                _reject_unknown(
                    body,
                    {"comparison", "value", "limit", "low", "high", "absolute", "kind"},
                )
            absolute = body.get("absolute", False)
            result = limit_compare(
                body.get("value"),
                comparison=comparison if isinstance(comparison, str) else "",
                limit=body.get("limit"),
                low=body.get("low"),
                high=body.get("high"),
                absolute=absolute if isinstance(absolute, bool) else absolute,
                kind=body.get("kind"),
            )
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    return router


def s5_catalog_app() -> FastAPI:
    """A tiny app that serves only the three S5 catalog routes."""
    app = FastAPI()
    app.include_router(s5_catalog_router())
    return app
