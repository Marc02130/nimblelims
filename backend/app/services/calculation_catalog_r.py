"""R-side catalog functions v1 (CALC-REQ-8, 9, 12, 17, 24, 37).

``fit_4pl``, ``inverse_4pl``, ``fit_loglog_linear``, and
``inverse_loglog_linear``. Split (CALC-REQ-37):

- The backend runs every gate first, in Python ``decimal`` on the decimal
  strings it was given: missing data, the four-level count, the in-range
  check before each inversion, and the non-positive log check. A result that
  a gate decides (a stop, a qualified ``<`` / ``>``, ``missing_input``) makes
  no R call.
- R does only the fit or the inversion, on one route per function version
  (``/catalog/<name>/v1``), reached through
  ``RCalculatorClient.execute_calculation_request``, so every call passes the
  CALC-REQ-4 / 4a lock and sandbox gate. A refusal there is raised unchanged
  and nothing is written.
- R returns each output as its shortest round-trip string. The backend keeps
  that string as the unrounded decimal. Any output that is not a finite
  decimal string (NaN, Inf, NA, a JSON number, a missing key) stops the stage
  with ``r_non_finite``; it is never mapped to a number, a qualifier, or a
  verdict.

Nothing here writes an attempt or a result (S9). The versions below are
declared but not released: they have no KAT cases, so the release check
refuses them (CALC-REQ-7).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from app.services.calculation_kat import FunctionVersion, RCalculationClient
from app.services.calculation_runtime import CalculationCallRefused

DECIMAL_STRING_RE = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$")

FIT_4PL_ROUTE = "/catalog/fit_4pl/v1"
INVERSE_4PL_ROUTE = "/catalog/inverse_4pl/v1"
FIT_LOGLOG_LINEAR_ROUTE = "/catalog/fit_loglog_linear/v1"
INVERSE_LOGLOG_LINEAR_ROUTE = "/catalog/inverse_loglog_linear/v1"

R_CATALOG_SOURCES = ("R/catalog.R", "R/serialise.R")

CURVE_NOT_FITTED = "curve_not_fitted"
NON_POSITIVE_LOG_INPUT = "non_positive_log_input"
R_NON_FINITE = "r_non_finite"
R_TIMEOUT = "r_timeout"
BACKEND_TIMEOUT = "backend_timeout"
MISSING_INPUT = "missing_input"
RESPONSE_AT_ASYMPTOTE = "response_at_asymptote"

_TIMEOUT_CODES = (R_TIMEOUT, BACKEND_TIMEOUT)
FOUR_PL_PARAMETERS = ("bottom", "top", "slope", "inflection")


class CatalogInputRefused(Exception):
    """An input is not what the function version declares. No R call is made."""

    code = "invalid_input"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class StageResult:
    """The outcome of one catalog function call.

    ``outputs`` holds decimal strings. ``stop`` is a stage stop code
    (CALC-REQ-25) and then ``outputs`` is empty. ``qualifier`` is ``<`` or
    ``>`` for a response past the low or high end, with ``end`` ``low`` or
    ``high``; the kind's name, label, and limit come from configuration.
    ``flags`` holds ``missing_input`` or ``response_at_asymptote``.
    """

    function: str
    version: int
    outputs: Mapping[str, str]
    r_called: bool
    stop: Optional[str] = None
    detail: Optional[str] = None
    qualifier: Optional[str] = None
    end: Optional[str] = None
    flags: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()


def is_decimal_string(value: Any) -> bool:
    return isinstance(value, str) and DECIMAL_STRING_RE.fullmatch(value) is not None


def _decimal(value: Any, name: str) -> Decimal:
    if not isinstance(value, str):
        raise CatalogInputRefused(f"{name} must be a decimal string, not {type(value).__name__}")
    if DECIMAL_STRING_RE.fullmatch(value) is None:
        raise CatalogInputRefused(f"{name} is not a decimal string")
    return Decimal(value)


def _optional_decimal(value: Any, name: str) -> Optional[Decimal]:
    """``None`` when there is no numeric value. A non-string value is refused."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise CatalogInputRefused(f"{name} must be a decimal string, not {type(value).__name__}")
    if DECIMAL_STRING_RE.fullmatch(value) is None:
        return None
    return Decimal(value)


def _identity(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogInputRefused(f"{name} must be a non-empty string")
    return value


def _call_r(
    fv: FunctionVersion,
    r_client: RCalculationClient,
    payload: dict[str, Any],
    outputs: Sequence[str],
    allowed_stops: Sequence[str],
) -> StageResult:
    assert fv.route is not None
    try:
        body = r_client.execute_calculation_request(fv.route, payload)
    except CalculationCallRefused as exc:
        if exc.code in _TIMEOUT_CODES:
            return StageResult(fv.name, fv.version, {}, True, stop=exc.code, detail=exc.detail)
        raise
    if not isinstance(body, Mapping):
        raise CalculationCallRefused("r_service", f"{fv.name}: R service returned no object")
    stop = body.get("stop")
    if stop is not None:
        if stop not in allowed_stops:
            raise CalculationCallRefused(
                "r_service", f"{fv.name}: R service returned an undeclared stop {stop!r}"
            )
        detail = body.get("detail")
        return StageResult(
            fv.name, fv.version, {}, True, stop=stop, detail=str(detail) if detail else None
        )
    out: dict[str, str] = {}
    for name in outputs:
        value = body.get(name)
        if not is_decimal_string(value):
            return StageResult(
                fv.name,
                fv.version,
                {},
                True,
                stop=R_NON_FINITE,
                detail=f"R output {name} is not a finite decimal string",
            )
        out[name] = value
    return StageResult(fv.name, fv.version, out, True)


# ---- declarations ----------------------------------------------------------

FIT_4PL_V1 = FunctionVersion(
    name="fit_4pl",
    version=1,
    side="r",
    description=(
        "Fits a four-parameter logistic curve to calibrator responses against nominal "
        "calibrator concentrations: response = bottom + (top - bottom) / "
        "(1 + exp(slope * (ln(concentration) - ln(inflection)))) (drc LL.4, ordinary "
        "least squares, no weights, no parameter bounds). r_squared = 1 - SS_res / SS_tot."
    ),
    inputs={
        "concentration": "calibrator concentration unit (declared on the binding)",
        "response": "calibrator response unit (declared on the binding)",
        "replicate": "identity",
    },
    outputs={
        "bottom": "calibrator response unit (declared on the binding)",
        "top": "calibrator response unit (declared on the binding)",
        "slope": "1",
        "inflection": "calibrator concentration unit (declared on the binding)",
        "r_squared": "1",
        "points_used": "count",
        "points_excluded": "count",
    },
    stop_rule=(
        "Fewer than four calibrator levels with a numeric response, or a fit that does not "
        "converge, stops with curve_not_fitted. A non-finite R output stops with r_non_finite."
    ),
    missing_data_rule=(
        "A calibrator replicate with no numeric response is excluded from the fit and "
        "counted as excluded. It is never treated as zero."
    ),
    kats=(),
    route=FIT_4PL_ROUTE,
    r_sources=R_CATALOG_SOURCES,
)

INVERSE_4PL_V1 = FunctionVersion(
    name="inverse_4pl",
    version=1,
    side="r",
    description=(
        "Back-calculates a concentration from a response on a fitted 4PL curve: "
        "concentration = inflection * ((top - bottom) / (response - bottom) - 1)^(1 / slope). "
        "The backend first decides in-range against the mean responses of the lowest- and "
        "highest-concentration used calibrators; only in-range responses reach R."
    ),
    inputs={
        "bottom": "calibrator response unit (declared on the binding)",
        "top": "calibrator response unit (declared on the binding)",
        "slope": "1",
        "inflection": "calibrator concentration unit (declared on the binding)",
        "response": "calibrator response unit (declared on the binding)",
        "low_calibrator_mean_response": "calibrator response unit (declared on the binding)",
        "high_calibrator_mean_response": "calibrator response unit (declared on the binding)",
    },
    outputs={"concentration": "calibrator concentration unit (declared on the binding)"},
    stop_rule=(
        "Never extrapolates. A response past the high-concentration calibrator's mean is a "
        "qualified result stored > (end high); past the low-concentration calibrator's mean, "
        "stored < (end low). Neither stores a number or calls R. A non-finite R output stops "
        "with r_non_finite."
    ),
    missing_data_rule=(
        "No numeric response gives no concentration and missing_input. A response at or "
        "beyond an asymptote has no inverse and is flagged response_at_asymptote, not "
        "assigned a number."
    ),
    kats=(),
    route=INVERSE_4PL_ROUTE,
    r_sources=R_CATALOG_SOURCES,
)

FIT_LOGLOG_LINEAR_V1 = FunctionVersion(
    name="fit_loglog_linear",
    version=1,
    side="r",
    description=(
        "Linear regression of log10(y) on log10(x): log10(y) = intercept + slope * log10(x). "
        "r is the Pearson correlation of log10(x) and log10(y)."
    ),
    inputs={
        "x": "x unit (declared on the binding)",
        "y": "y unit (declared on the binding)",
        "point_id": "identity",
        "replicates": "y unit (declared on the binding)",
    },
    outputs={
        "slope": "1",
        "intercept": "1 (label log10(<y unit>))",
        "r": "1",
        "points_used": "count",
        "points_dropped": "count",
    },
    stop_rule=(
        "An x <= 0, a y <= 0, or a replicate value <= 0 that would enter a mean stops with "
        "non_positive_log_input; nothing is passed to log10. A non-finite R output stops "
        "with r_non_finite."
    ),
    missing_data_rule=(
        "A point with no y value is dropped and counted, with its identity. No point with a "
        "y value gives no fit and missing_input."
    ),
    kats=(),
    route=FIT_LOGLOG_LINEAR_ROUTE,
    r_sources=R_CATALOG_SOURCES,
)

INVERSE_LOGLOG_LINEAR_V1 = FunctionVersion(
    name="inverse_loglog_linear",
    version=1,
    side="r",
    description=(
        "Back-calculates x from y on a log-log linear fit: "
        "x = 10^((log10(y) - intercept) / slope). The backend first decides in-range "
        "against the y means of the lowest-x and highest-x used points; only in-range "
        "values reach R."
    ),
    inputs={
        "slope": "1",
        "intercept": "1 (label log10(<y unit>))",
        "y": "y unit (declared on the binding)",
        "lowest_x_mean_y": "y unit (declared on the binding)",
        "highest_x_mean_y": "y unit (declared on the binding)",
    },
    outputs={"x": "x unit of the fit (declared on the binding)"},
    stop_rule=(
        "Never extrapolates. With a negative slope, y below the highest-x mean is stored > "
        "and y above the lowest-x mean is stored <; with a positive slope, y above the "
        "highest-x mean is stored > and y below the lowest-x mean is stored <. Neither "
        "stores a number or calls R. An endpoint mean <= 0 stops with "
        "non_positive_log_input. A non-finite R output stops with r_non_finite."
    ),
    missing_data_rule="No y value gives no x and missing_input.",
    kats=(),
    route=INVERSE_LOGLOG_LINEAR_ROUTE,
    r_sources=R_CATALOG_SOURCES,
)

R_CATALOG_VERSIONS: tuple[FunctionVersion, ...] = (
    FIT_4PL_V1,
    INVERSE_4PL_V1,
    FIT_LOGLOG_LINEAR_V1,
    INVERSE_LOGLOG_LINEAR_V1,
)


# ---- fit_4pl ---------------------------------------------------------------


def fit_4pl(points: Sequence[Mapping[str, Any]], r_client: RCalculationClient) -> StageResult:
    """Each point has ``concentration``, ``response`` (or no numeric value), and ``replicate``."""
    fv = FIT_4PL_V1
    used: list[tuple[str, str]] = []
    excluded = 0
    for i, point in enumerate(points):
        if not isinstance(point, Mapping):
            raise CatalogInputRefused(f"point {i} is not an object")
        conc = _decimal(point.get("concentration"), f"point {i} concentration")
        _identity(point.get("replicate"), f"point {i} replicate")
        if conc < 0:
            raise CatalogInputRefused(f"point {i} concentration is negative")
        response = _optional_decimal(point.get("response"), f"point {i} response")
        if response is None:
            excluded += 1
            continue
        used.append((point["concentration"], point["response"]))

    levels = {Decimal(c) for c, _r in used}
    counts = {"points_used": str(len(used)), "points_excluded": str(excluded)}
    if len(levels) < 4:
        return StageResult(
            fv.name,
            fv.version,
            {},
            False,
            stop=CURVE_NOT_FITTED,
            detail=f"{len(levels)} calibrator levels with a numeric response; four are needed",
        )
    result = _call_r(
        fv,
        r_client,
        {"concentration": [c for c, _r in used], "response": [r for _c, r in used]},
        FOUR_PL_PARAMETERS + ("r_squared",),
        (CURVE_NOT_FITTED, R_NON_FINITE),
    )
    if result.stop is not None:
        return result
    return StageResult(fv.name, fv.version, {**result.outputs, **counts}, True)


# ---- inverse_4pl -----------------------------------------------------------


def inverse_4pl(
    curve: Mapping[str, Any],
    response: Any,
    low_calibrator_mean_response: Any,
    high_calibrator_mean_response: Any,
    r_client: RCalculationClient,
) -> StageResult:
    """Back-calculate one response. ``curve`` holds the ``fit_4pl`` parameters."""
    fv = INVERSE_4PL_V1
    params = {name: _decimal(curve.get(name), name) for name in FOUR_PL_PARAMETERS}
    if params["slope"] == 0:
        raise CatalogInputRefused("slope is 0; the curve has no inverse")
    low = _decimal(low_calibrator_mean_response, "low_calibrator_mean_response")
    high = _decimal(high_calibrator_mean_response, "high_calibrator_mean_response")
    if low == high:
        raise CatalogInputRefused("the low and high calibrator mean responses are equal")
    y = _optional_decimal(response, "response")
    if y is None:
        return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))

    increasing = high > low
    past_high = y > high if increasing else y < high
    past_low = y < low if increasing else y > low
    if past_high:
        return StageResult(fv.name, fv.version, {}, False, qualifier=">", end="high")
    if past_low:
        return StageResult(fv.name, fv.version, {}, False, qualifier="<", end="low")

    lower = min(params["bottom"], params["top"])
    upper = max(params["bottom"], params["top"])
    if not lower < y < upper:
        return StageResult(fv.name, fv.version, {}, False, flags=(RESPONSE_AT_ASYMPTOTE,))

    payload = {name: curve[name] for name in FOUR_PL_PARAMETERS}
    payload["response"] = response
    return _call_r(fv, r_client, payload, ("concentration",), (R_NON_FINITE,))


# ---- fit_loglog_linear -----------------------------------------------------


def fit_loglog_linear(
    points: Sequence[Mapping[str, Any]], r_client: RCalculationClient
) -> StageResult:
    """Each point has ``x``, ``y`` (a replicate mean, or no value), ``point_id``, and
    optionally ``replicates``, the values that entered that mean."""
    fv = FIT_LOGLOG_LINEAR_V1
    used: list[tuple[str, str]] = []
    dropped: list[str] = []
    for i, point in enumerate(points):
        if not isinstance(point, Mapping):
            raise CatalogInputRefused(f"point {i} is not an object")
        point_id = _identity(point.get("point_id"), f"point {i} point_id")
        x = _decimal(point.get("x"), f"point {point_id} x")
        y = _optional_decimal(point.get("y"), f"point {point_id} y")
        replicates = point.get("replicates")
        if replicates is not None:
            if isinstance(replicates, (str, bytes)) or not isinstance(replicates, Sequence):
                raise CatalogInputRefused(f"point {point_id} replicates must be an array")
            for j, rep in enumerate(replicates):
                value = _optional_decimal(rep, f"point {point_id} replicate {j}")
                if value is not None and value <= 0:
                    return _non_positive(fv, f"point {point_id} replicate {j} is not greater than 0")
        if x <= 0:
            return _non_positive(fv, f"point {point_id} x is not greater than 0")
        if y is None:
            dropped.append(point_id)
            continue
        if y <= 0:
            return _non_positive(fv, f"point {point_id} y is not greater than 0")
        used.append((point["x"], point["y"]))

    if not used:
        return StageResult(
            fv.name, fv.version, {}, False, flags=(MISSING_INPUT,), dropped=tuple(dropped)
        )
    result = _call_r(
        fv,
        r_client,
        {"x": [x for x, _y in used], "y": [y for _x, y in used]},
        ("slope", "intercept", "r"),
        (NON_POSITIVE_LOG_INPUT, R_NON_FINITE),
    )
    if result.stop is not None:
        return StageResult(
            fv.name,
            fv.version,
            {},
            True,
            stop=result.stop,
            detail=result.detail,
            dropped=tuple(dropped),
        )
    counts = {"points_used": str(len(used)), "points_dropped": str(len(dropped))}
    return StageResult(
        fv.name, fv.version, {**result.outputs, **counts}, True, dropped=tuple(dropped)
    )


def _non_positive(fv: FunctionVersion, detail: str) -> StageResult:
    return StageResult(fv.name, fv.version, {}, False, stop=NON_POSITIVE_LOG_INPUT, detail=detail)


# ---- inverse_loglog_linear -------------------------------------------------


def inverse_loglog_linear(
    fit: Mapping[str, Any],
    y: Any,
    lowest_x_mean_y: Any,
    highest_x_mean_y: Any,
    r_client: RCalculationClient,
) -> StageResult:
    """Back-calculate one y. ``fit`` holds the ``fit_loglog_linear`` slope and intercept."""
    fv = INVERSE_LOGLOG_LINEAR_V1
    slope = _decimal(fit.get("slope"), "slope")
    _decimal(fit.get("intercept"), "intercept")
    if slope == 0:
        raise CatalogInputRefused("slope is 0; the fit has no inverse")
    low_x_mean = _decimal(lowest_x_mean_y, "lowest_x_mean_y")
    high_x_mean = _decimal(highest_x_mean_y, "highest_x_mean_y")
    if low_x_mean <= 0 or high_x_mean <= 0:
        return _non_positive(fv, "an endpoint mean is not greater than 0")
    if (slope > 0 and not high_x_mean > low_x_mean) or (
        slope < 0 and not high_x_mean < low_x_mean
    ):
        raise CatalogInputRefused("the endpoint means do not follow the sign of the slope")
    value = _optional_decimal(y, "y")
    if value is None:
        return StageResult(fv.name, fv.version, {}, False, flags=(MISSING_INPUT,))

    if slope < 0:
        past_high = value < high_x_mean
        past_low = value > low_x_mean
    else:
        past_high = value > high_x_mean
        past_low = value < low_x_mean
    if past_high:
        return StageResult(fv.name, fv.version, {}, False, qualifier=">", end="high")
    if past_low:
        return StageResult(fv.name, fv.version, {}, False, qualifier="<", end="low")

    payload = {"slope": fit["slope"], "intercept": fit["intercept"], "y": y}
    return _call_r(fv, r_client, payload, ("x",), (NON_POSITIVE_LOG_INPUT, R_NON_FINITE))
