"""Backend decimal catalog functions v1 (CALC-REQ-38, 39, 51, 53, 28, 37).

``apply_dilution``, ``subtract``, ``copy_raw``, and ``convert_units``.
Arithmetic uses Python ``decimal`` at precision 50 with ``ROUND_HALF_EVEN``.
None of these functions calls R, and none has an R route (CALC-REQ-24).

``convert_units`` looks up ``units.multiplier`` with a plain SELECT.
``units`` has no row-level security policy. That lookup does not enable RLS
and does not run under it (OQ-CALC-44, decided Marc 2026-11-15: shared
reference data). The shipped helpers that return ``float`` are not used.

Nothing here writes an attempt or a result (S9). The versions below are
declared with KATs and are not released: S4 does not write a release record.
"""
from __future__ import annotations

import decimal
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping, Optional

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.calculation_catalog_r import (
    MISSING_INPUT,
    CatalogInputRefused,
    StageResult,
    is_decimal_string,
)
from app.services.calculation_kat import (
    DECIMAL_PRECISION,
    DECIMAL_ROUNDING,
    FunctionVersion,
    KatCase,
    Quantity,
    Tolerance,
)

# The Spec does not lock a spelling for the two unit stops in CALC-REQ-28.
# A named unit that is not in the table uses this code. A cross-type
# conversion is a refusal (CALC-REQ-39), not this stop. See the manual.
UNIT_NOT_FOUND = "unit_not_found"

WITHIN_TYPE = "within_type"
PER_AMOUNT = "per_amount"

VALUE_UNIT = "the value's unit"
SHARED_UNIT = "shared unit"
INPUT_UNIT = "the input's unit"
NUMERATOR_UNIT = "numerator unit"
AMOUNT_UNIT = "amount unit"
QUOTIENT_UNIT = "declared quotient"
DILUTION_UNIT = "1"


def _context() -> decimal.Context:
    ctx = decimal.Context(prec=DECIMAL_PRECISION, rounding=DECIMAL_ROUNDING)
    return ctx


def format_decimal(value: Decimal) -> str:
    """Plain decimal text of an arithmetic result.

    Trailing zeros that ``Decimal`` keeps on the coefficient are dropped, so
    ``2.600`` is ``2.6``. ``copy_raw`` does not use this: it returns the
    input characters unchanged.
    """
    if not value.is_finite():
        raise CatalogInputRefused("result is not a finite decimal")
    text_value = format(value, "f")
    if "." in text_value:
        whole, frac = text_value.split(".", 1)
        frac = frac.rstrip("0")
        text_value = whole if frac == "" else f"{whole}.{frac}"
    if text_value in ("-0", "-", ""):
        return "0"
    return text_value


def _optional_input(value: Any, name: str) -> Optional[str]:
    """The original decimal string, or None when the input is missing.

    A JSON number or a boolean is refused (CALC-REQ-37). A string that is
    not a decimal (``N/A``, empty) is missing, not a refusal.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, str):
        raise CatalogInputRefused(
            f"{name} must be a decimal string, not {type(value).__name__}"
        )
    if not is_decimal_string(value):
        return None
    return value


def _parse(value: str) -> Decimal:
    return Decimal(value)


def _result(fv: FunctionVersion, outputs: Mapping[str, str]) -> StageResult:
    return StageResult(fv.name, fv.version, dict(outputs), False)


def _missing(fv: FunctionVersion) -> StageResult:
    return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))


def _stopped(fv: FunctionVersion, code: str, detail: str) -> StageResult:
    return StageResult(fv.name, fv.version, {}, False, stop=code, detail=detail)


def _exact(unit: str) -> Tolerance:
    return Tolerance(kind="absolute", value="0", unit=unit)


def _quantity(value: str, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit)


# ---- arithmetic (also the KAT compute functions) ---------------------------


def apply_dilution_compute(inputs: Mapping[str, Decimal]) -> Mapping[str, str]:
    """value × dilution factor. A factor below 1 is refused."""
    factor = inputs["dilution_factor"]
    if factor < 1:
        raise CatalogInputRefused("dilution factor is below 1")
    with decimal.localcontext(_context()):
        return {"value": format_decimal(inputs["value"] * factor)}


def subtract_compute(inputs: Mapping[str, Decimal]) -> Mapping[str, str]:
    """minuend − subtrahend. Zero is stored as 0. Nothing is substituted."""
    with decimal.localcontext(_context()):
        return {"difference": format_decimal(inputs["minuend"] - inputs["subtrahend"])}


def copy_raw_compute(inputs: Mapping[str, Decimal]) -> Mapping[str, str]:
    """KAT path. The public function returns the original decimal string."""
    text_value = format_decimal(inputs["value"])
    return {"calculated": text_value, "reported": text_value}


def convert_units_compute(inputs: Mapping[str, Decimal]) -> Mapping[str, str]:
    """Per-amount mode: value ÷ amount, one division. Amount ≤ 0 is refused."""
    amount = inputs["amount"]
    if amount <= 0:
        raise CatalogInputRefused("amount is not greater than 0")
    with decimal.localcontext(_context()):
        return {"value": format_decimal(inputs["value"] / amount)}


def within_type_quotient(value: Decimal, from_multiplier: Decimal, to_multiplier: Decimal) -> str:
    """value × from multiplier ÷ to multiplier. Products first, one division last."""
    if from_multiplier <= 0 or to_multiplier <= 0:
        raise CatalogInputRefused("a unit multiplier must be greater than 0")
    with decimal.localcontext(_context()):
        return format_decimal((value * from_multiplier) / to_multiplier)


# ---- KATs (tolerance 0; expected values are the Spec acceptance criteria) --

_APPLY_CITATION = (
    "CALC-REQ-38 acceptance criterion, worked by hand outside this function "
    "and recorded with this case: 0.026 times 100 is 2.6 exactly. "
    "Not an SOP and not a configuration constant."
)
_SUBTRACT_CITATION = (
    "CALC-REQ-51 acceptance criterion, worked by hand outside this function "
    "and recorded with this case: 2.572 minus 0.050 is 2.522 exactly. "
    "Not an SOP and not a configuration constant."
)
_COPY_CITATION = (
    "CALC-REQ-53 acceptance criterion, recorded with this case: the input "
    "decimal string 0.026 is the calculated value and the reported value. "
    "Not an SOP and not a configuration constant."
)
_CONVERT_CITATION = (
    "CALC-REQ-39 acceptance criterion, worked by hand outside this function "
    "and recorded with this case: 2.6 divided by 10 is 0.26 exactly. "
    "Not an SOP and not a configuration constant."
)


def _apply_kat() -> KatCase:
    return KatCase(
        case_id="apply-dilution-0.026-times-100",
        inputs={
            "value": _quantity("0.026", VALUE_UNIT),
            "dilution_factor": _quantity("100", DILUTION_UNIT),
        },
        expected={"value": _quantity("2.6", VALUE_UNIT)},
        tolerance={"value": _exact(VALUE_UNIT)},
        citation=_APPLY_CITATION,
    )


def _subtract_kat() -> KatCase:
    return KatCase(
        case_id="subtract-2.572-minus-0.050",
        inputs={
            "minuend": _quantity("2.572", SHARED_UNIT),
            "subtrahend": _quantity("0.050", SHARED_UNIT),
        },
        expected={"difference": _quantity("2.522", SHARED_UNIT)},
        tolerance={"difference": _exact(SHARED_UNIT)},
        citation=_SUBTRACT_CITATION,
    )


def _copy_kat() -> KatCase:
    return KatCase(
        case_id="copy-raw-0.026",
        inputs={"value": _quantity("0.026", INPUT_UNIT)},
        expected={
            "calculated": _quantity("0.026", INPUT_UNIT),
            "reported": _quantity("0.026", INPUT_UNIT),
        },
        tolerance={
            "calculated": _exact(INPUT_UNIT),
            "reported": _exact(INPUT_UNIT),
        },
        citation=_COPY_CITATION,
    )


def _convert_kat() -> KatCase:
    return KatCase(
        case_id="convert-units-2.6-over-10",
        inputs={
            "value": _quantity("2.6", NUMERATOR_UNIT),
            "amount": _quantity("10", AMOUNT_UNIT),
        },
        expected={"value": _quantity("0.26", QUOTIENT_UNIT)},
        tolerance={"value": _exact(QUOTIENT_UNIT)},
        citation=_CONVERT_CITATION,
    )


# ---- declarations ----------------------------------------------------------

APPLY_DILUTION_V1 = FunctionVersion(
    name="apply_dilution",
    version=1,
    side="backend",
    description=(
        "Multiplies a value by a dilution factor and keeps the value's unit. "
        "The dilution factor is dimensionless (unit 1). output = value × dilution factor."
    ),
    inputs={"value": VALUE_UNIT, "dilution_factor": DILUTION_UNIT},
    outputs={"value": VALUE_UNIT},
    stop_rule=(
        "A dilution factor below 1 is refused for that value. "
        "The refusal is not a stage stop."
    ),
    missing_data_rule=(
        "No dilution factor, or no value, gives no output and missing_input. "
        "A missing input is never replaced with zero."
    ),
    kats=(_apply_kat(),),
    compute=apply_dilution_compute,
)

SUBTRACT_V1 = FunctionVersion(
    name="subtract",
    version=1,
    side="backend",
    description=(
        "Subtracts the subtrahend from the minuend. Both are decimal strings in one "
        "shared unit. output = minuend − subtrahend, in that unit. A difference of "
        "zero is stored as 0."
    ),
    inputs={"minuend": SHARED_UNIT, "subtrahend": SHARED_UNIT},
    outputs={"difference": SHARED_UNIT},
    stop_rule=(
        "No stop of its own. A missing, ambiguous, or stopped reference input is "
        "handled before this function runs (CALC-REQ-50). It never substitutes zero."
    ),
    missing_data_rule=(
        "A missing minuend or subtrahend gives no output and missing_input. "
        "This function does not resolve a reference input."
    ),
    kats=(_subtract_kat(),),
    compute=subtract_compute,
)

COPY_RAW_V1 = FunctionVersion(
    name="copy_raw",
    version=1,
    side="backend",
    description=(
        "Copies the input decimal string. The same characters are written to "
        "calculated and to reported. It does not convert the number and it does "
        "not change the text."
    ),
    inputs={"value": INPUT_UNIT},
    outputs={"calculated": INPUT_UNIT, "reported": INPUT_UNIT},
    stop_rule=(
        "No additional stop. missing_input and a general stop remain. "
        "A difference between file units and the pairing unit is OQ-CALC-39 and "
        "is not a stop inside this function."
    ),
    missing_data_rule=(
        "No input gives no output and missing_input. It never substitutes zero."
    ),
    kats=(_copy_kat(),),
    compute=copy_raw_compute,
)

CONVERT_UNITS_V1 = FunctionVersion(
    name="convert_units",
    version=1,
    side="backend",
    description=(
        "Two modes. Within one unit type, output = value × from-unit multiplier "
        "÷ to-unit multiplier, using units.multiplier (products first, one division "
        "last). A conversion across unit types is refused. Per-amount normalisation "
        "divides the value by an amount; the output unit is the declared quotient, "
        "and this function writes the number only. The multiplier lookup reads units "
        "directly. units has no row-level security policy, and the lookup does not "
        "run under row-level security (OQ-CALC-44, decided Marc 2026-11-15)."
    ),
    inputs={"value": NUMERATOR_UNIT, "amount": AMOUNT_UNIT},
    outputs={"value": QUOTIENT_UNIT},
    stop_rule=(
        "An amount that is not greater than 0 is refused. A conversion across unit "
        "types is refused. A named unit that is not an active row in units stops "
        "with unit_not_found and the detail names the unit. The Spec does not lock "
        "that spelling."
    ),
    missing_data_rule=(
        "No amount, in per-amount mode, gives no output and missing_input. "
        "No value gives no output and missing_input. A missing unit name gives "
        "missing_input. A missing input is never replaced with zero."
    ),
    kats=(_convert_kat(),),
    compute=convert_units_compute,
)

DECIMAL_CATALOG_VERSIONS: tuple[FunctionVersion, ...] = (
    APPLY_DILUTION_V1,
    SUBTRACT_V1,
    COPY_RAW_V1,
    CONVERT_UNITS_V1,
)


# ---- public functions ------------------------------------------------------


def apply_dilution(value: Any, dilution_factor: Any) -> StageResult:
    """value × dilution factor, in the value's unit. No R call."""
    factor_text = _optional_input(dilution_factor, "dilution_factor")
    if factor_text is None:
        return _missing(APPLY_DILUTION_V1)
    factor = _parse(factor_text)
    if factor < 1:
        raise CatalogInputRefused("dilution factor is below 1")
    value_text = _optional_input(value, "value")
    if value_text is None:
        return _missing(APPLY_DILUTION_V1)
    outputs = apply_dilution_compute({"value": _parse(value_text), "dilution_factor": factor})
    return _result(APPLY_DILUTION_V1, outputs)


def subtract(minuend: Any, subtrahend: Any) -> StageResult:
    """minuend − subtrahend. No R call. Does not resolve a reference input."""
    left = _optional_input(minuend, "minuend")
    right = _optional_input(subtrahend, "subtrahend")
    if left is None or right is None:
        return _missing(SUBTRACT_V1)
    outputs = subtract_compute({"minuend": _parse(left), "subtrahend": _parse(right)})
    return _result(SUBTRACT_V1, outputs)


def copy_raw(value: Any) -> StageResult:
    """Return the input decimal string as calculated and as reported. No conversion."""
    text_value = _optional_input(value, "value")
    if text_value is None:
        return _missing(COPY_RAW_V1)
    return _result(COPY_RAW_V1, {"calculated": text_value, "reported": text_value})


@dataclass(frozen=True)
class UnitFactor:
    """One active unit row. ``multiplier`` is ``units.multiplier`` as ``Decimal``."""

    name: str
    type_name: str
    multiplier: Optional[Decimal]


UnitLookup = Callable[[str], Optional[UnitFactor]]


def load_unit_factor(session: Session, name: str) -> Optional[UnitFactor]:
    """Read one active unit's multiplier. Does not run under row-level security.

    ``units`` has no RLS policy. This SELECT does not enable one, does not
    set ``row_security``, and does not filter by client or project. The
    multiplier is taken from ``numeric`` text so it is never a binary float.
    """
    if not isinstance(name, str) or name == "":
        return None
    row = session.execute(
        text(
            """
            SELECT u.name AS name,
                   t.name AS type_name,
                   u.multiplier::text AS multiplier_text
            FROM units AS u
            JOIN list_entries AS t ON t.id = u.type
            WHERE u.name = :name
              AND u.active IS TRUE
            """
        ),
        {"name": name},
    ).mappings().first()
    if row is None:
        return None
    raw = row["multiplier_text"]
    multiplier = None if raw is None else Decimal(str(raw))
    return UnitFactor(name=str(row["name"]), type_name=str(row["type_name"]), multiplier=multiplier)


def _lookup_from_session(session: Session) -> UnitLookup:
    def lookup(name: str) -> Optional[UnitFactor]:
        return load_unit_factor(session, name)

    return lookup


class _MissingUnitName(Exception):
    """A within-type call did not name a unit. Becomes ``missing_input``."""


class _UnitNotFound(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)


def _named_unit(name: Any) -> str:
    if name is None:
        raise _MissingUnitName()
    if not isinstance(name, str):
        raise CatalogInputRefused(f"unit name must be a string, not {type(name).__name__}")
    if name.strip() == "":
        raise _MissingUnitName()
    return name


def _require_factor(lookup: UnitLookup, name: Any) -> UnitFactor:
    unit_name = _named_unit(name)
    factor = lookup(unit_name)
    if factor is None:
        raise _UnitNotFound(unit_name)
    if factor.multiplier is None or factor.multiplier <= 0:
        raise CatalogInputRefused(f"unit {unit_name!r} has no positive multiplier")
    return factor


def convert_units(
    value: Any,
    *,
    mode: str,
    amount: Any = None,
    from_unit: Any = None,
    to_unit: Any = None,
    lookup: Optional[UnitLookup] = None,
    session: Optional[Session] = None,
) -> StageResult:
    """``within_type`` or ``per_amount``. No R call. Does not assign the output unit."""
    if not isinstance(mode, str) or mode not in (WITHIN_TYPE, PER_AMOUNT):
        raise CatalogInputRefused("mode must be within_type or per_amount")
    if mode == PER_AMOUNT:
        return _per_amount(value, amount)
    return _within_type(value, from_unit, to_unit, lookup, session)


def _per_amount(value: Any, amount: Any) -> StageResult:
    amount_text = _optional_input(amount, "amount")
    if amount_text is None:
        return _missing(CONVERT_UNITS_V1)
    parsed_amount = _parse(amount_text)
    if parsed_amount <= 0:
        raise CatalogInputRefused("amount is not greater than 0")
    value_text = _optional_input(value, "value")
    if value_text is None:
        return _missing(CONVERT_UNITS_V1)
    outputs = convert_units_compute({"value": _parse(value_text), "amount": parsed_amount})
    return _result(CONVERT_UNITS_V1, outputs)


def _within_type(
    value: Any,
    from_unit: Any,
    to_unit: Any,
    lookup: Optional[UnitLookup],
    session: Optional[Session],
) -> StageResult:
    if lookup is None and session is None:
        raise CatalogInputRefused("within_type conversion needs a unit lookup")
    if lookup is None:
        if session is None:
            raise CatalogInputRefused("within_type conversion needs a unit lookup")
        lookup = _lookup_from_session(session)
    try:
        source = _require_factor(lookup, from_unit)
        target = _require_factor(lookup, to_unit)
    except _MissingUnitName:
        return _missing(CONVERT_UNITS_V1)
    except _UnitNotFound as exc:
        return _stopped(
            CONVERT_UNITS_V1,
            UNIT_NOT_FOUND,
            f"unit {exc.name!r} is not in the units table",
        )
    if source.type_name != target.type_name:
        raise CatalogInputRefused(
            f"cannot convert {source.name} ({source.type_name}) to "
            f"{target.name} ({target.type_name}): the unit types differ"
        )
    value_text = _optional_input(value, "value")
    if value_text is None:
        return _missing(CONVERT_UNITS_V1)
    from_multiplier = source.multiplier
    to_multiplier = target.multiplier
    if from_multiplier is None or to_multiplier is None:
        raise CatalogInputRefused("a unit multiplier must be greater than 0")
    quotient = within_type_quotient(_parse(value_text), from_multiplier, to_multiplier)
    return _result(CONVERT_UNITS_V1, {"value": quotient})


# ---- HTTP status map -------------------------------------------------------
#
# Stops are HTTP 200 with ``stop`` and ``detail``. Refusals are HTTP 400 with
# ``code`` ``invalid_input``. ``missing_input`` is neither: HTTP 200, empty
# outputs, and the flag. These routes are the contract a caller must use.
# They are not mounted on the LIMS app (the stage runner is S9) and they are
# not R routes.


def stage_http_body(result: StageResult) -> dict[str, Any]:
    body: dict[str, Any] = {
        "function": result.function,
        "version": result.version,
        "r_called": result.r_called,
        "outputs": dict(result.outputs),
    }
    if result.stop is not None:
        body["stop"] = result.stop
        if result.detail:
            body["detail"] = result.detail
    if result.flags:
        body["flags"] = list(result.flags)
    return body


def _http_result(result: StageResult) -> JSONResponse:
    return JSONResponse(status_code=200, content=stage_http_body(result))


def _http_refusal(exc: CatalogInputRefused) -> JSONResponse:
    return JSONResponse(
        status_code=400, content={"code": exc.code, "detail": exc.detail}
    )


async def _json_object(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise CatalogInputRefused("body must be a JSON object") from exc
    if not isinstance(body, dict):
        raise CatalogInputRefused("body must be a JSON object")
    return body


def _reject_unknown(body: Mapping[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(body) - allowed)
    if extra:
        raise CatalogInputRefused("unknown field: " + ", ".join(extra))


def decimal_catalog_router(lookup: UnitLookup) -> APIRouter:
    """Status-code contract for the four functions. Not mounted on the LIMS app."""
    router = APIRouter()

    @router.post("/catalog/apply_dilution/v1")
    async def post_apply_dilution(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            _reject_unknown(body, {"value", "dilution_factor"})
            result = apply_dilution(body.get("value"), body.get("dilution_factor"))
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    @router.post("/catalog/subtract/v1")
    async def post_subtract(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            _reject_unknown(body, {"minuend", "subtrahend"})
            result = subtract(body.get("minuend"), body.get("subtrahend"))
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    @router.post("/catalog/copy_raw/v1")
    async def post_copy_raw(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            _reject_unknown(body, {"value"})
            result = copy_raw(body.get("value"))
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    @router.post("/catalog/convert_units/v1")
    async def post_convert_units(request: Request) -> JSONResponse:
        try:
            body = await _json_object(request)
            mode = body.get("mode")
            if mode == WITHIN_TYPE:
                _reject_unknown(body, {"mode", "value", "from_unit", "to_unit"})
            elif mode == PER_AMOUNT:
                _reject_unknown(body, {"mode", "value", "amount"})
            else:
                _reject_unknown(body, {"mode", "value", "amount", "from_unit", "to_unit"})
            result = convert_units(
                body.get("value"),
                mode=mode if isinstance(mode, str) else "",
                amount=body.get("amount"),
                from_unit=body.get("from_unit"),
                to_unit=body.get("to_unit"),
                lookup=lookup,
            )
        except CatalogInputRefused as exc:
            return _http_refusal(exc)
        return _http_result(result)

    return router


def decimal_catalog_app(lookup: UnitLookup) -> FastAPI:
    """A tiny app that serves only the four decimal catalog routes."""
    app = FastAPI()
    app.include_router(decimal_catalog_router(lookup))
    return app
