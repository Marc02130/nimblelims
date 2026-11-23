"""Calculation configuration: the builder's rules (calculations S7).

A configuration is the content of one ``analysis_analytes`` row's
``calculation_config`` column (CALC-REQ-40, OQ-CALC-48). It is a name and an
ordered list of stages. A stage is one catalog-function call, one saved
formula, or one ad hoc formula (CALC-REQ-23). Each stage binds its inputs and
declares what happens when it fails (CALC-REQ-48).

This module is pure: it reads no database and calls no R. The caller passes a
:class:`ConfigContext` with the facts the checks need (sibling calculation
orders, the units that exist, the saved formulas). Every refusal is a
:class:`ConfigRefusal` with a stable ``code``; the route turns it into HTTP 400.
A configuration stores no result unit (CALC-REQ-28) and no formula text for an
attempt to copy (CALC-REQ-40, the attempt records the analysis version).

Wording (Marc, 2026-11-22): a stage output is a *calculated value*, not a
result. It becomes a result only when the experiment is published (S13). The
configuration's ``result`` key is a pointer to the one stage output that will
be published as the analyte's result. The key keeps its name; it writes nothing.

What the builder refuses
------------------------
* Anything not in the closed catalog (CALC-REQ-22): the stage names a function
  and version, and the pair must be one of the eleven. The catalog is read here,
  never written.
* A binding that is not one of four kinds: a field of an entry in the same run
  (CALC-REQ-50), an upstream stage output, a reference input (an earlier
  analyte's calculated or reported value in the same run), or a value bound
  directly (CALC-REQ-23). There is no constants kind and no picker (#258).
* A stage without all four on-fail declarations, an outcome named ``pass``,
  and an outcome that is neither one of the four nor a named stage-stop code.
  A catalog function whose failure is a stage stop declares that stop code, not
  one of the four (CALC-REQ-48).
* A unit on a binding that disagrees with the function's declared unit
  (CALC-REQ-28). Lab-written formulas are not unit-checked and store no unit
  (CALC-REQ-23).
* A formula outside the grammar, with an unknown name or function, or with a
  term that is not bound in this stage (CALC-REQ-23).
* A reference to an analyte whose calculation order is not earlier
  (OQ-CALC-35).

Nothing here holds an acceptance limit, a cutoff, or a threshold. A bound a
stage compares against is a value the lab binds directly in the configuration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence
from uuid import UUID

from app.services.calculation_catalog import closed_catalog
from app.services.calculation_catalog_r import is_decimal_string
from app.services.calculation_catalog_s5 import COMPARISONS
from app.services.calculation_formula import (
    FormulaSyntaxError,
    ParsedFormula,
    check_names,
    parse_formula,
    term_name_error,
)
from app.services.calculation_formula import Call as FormulaCall

MAX_STAGES = 50
MAX_NAME_LENGTH = 100
MAX_FIELD_NAME_LENGTH = 100
MAX_LABEL_LENGTH = 64
MAX_PRECEDENCE_PLACE = 1000

STAGE_KIND_CATALOG = "catalog_function"
STAGE_KIND_SAVED = "saved_formula"
STAGE_KIND_AD_HOC = "ad_hoc_formula"
STAGE_KINDS = (STAGE_KIND_CATALOG, STAGE_KIND_SAVED, STAGE_KIND_AD_HOC)
FORMULA_KINDS = (STAGE_KIND_SAVED, STAGE_KIND_AD_HOC)

BINDING_RUN_FIELD = "run_field"
BINDING_STAGE_OUTPUT = "stage_output"
BINDING_REFERENCE = "reference"
BINDING_DIRECT = "direct"
BINDING_KINDS = (BINDING_RUN_FIELD, BINDING_STAGE_OUTPUT, BINDING_REFERENCE, BINDING_DIRECT)

ENTRY_TYPES = ("experiment_data", "experiment_sample_data")
REFERENCE_VALUES = ("calculated", "reported")

STATE_DRAFT = "draft"
STATE_ACTIVE = "active"

FORMULA_OUTPUT = "result"

# The four outcomes of CALC-REQ-48.
OUTCOME_RUN_FAILED = "run_failed"
OUTCOME_DILUTION_INVALID = "dilution_invalid"
OUTCOME_SAMPLE_VERDICT = "sample_verdict"
OUTCOME_FLAG = "flag"
ON_FAIL_OUTCOMES = (
    OUTCOME_RUN_FAILED,
    OUTCOME_DILUTION_INVALID,
    OUTCOME_SAMPLE_VERDICT,
    OUTCOME_FLAG,
)

# Stage stops a stage may declare in place of the four (CALC-REQ-25).
# ``on_fail_undeclared`` is the fail-closed default, not a declaration, and
# the two unit stops have no locked spelling, so none of them is listed.
STAGE_STOP_CODES = (
    "non_positive_log_input",
    "r_timeout",
    "backend_timeout",
    "r_non_finite",
    "curve_not_fitted",
    "reference_missing",
    "reference_ambiguous",
    "reference_stopped",
)

ABOVE_LIST = "above_list"

# Stage stops that a catalog function's own failure is. A stage on one of
# these functions declares one of these, never one of the four outcomes
# (CALC-REQ-48: ``fit_4pl`` declaring ``run_failed`` for ``curve_not_fitted``
# fails). Backend functions have no stop of their own: their failure is a
# check miss, which is one of the four.
FAILURE_STOPS: Mapping[str, tuple[str, ...]] = {
    "fit_4pl": ("curve_not_fitted", "r_non_finite", "r_timeout"),
    "inverse_4pl": ("r_non_finite", "r_timeout"),
    "fit_loglog_linear": ("non_positive_log_input", "r_non_finite", "r_timeout"),
    "inverse_loglog_linear": ("non_positive_log_input", "r_non_finite", "r_timeout"),
}

# Inputs a stage must bind. The rest of a function's inputs are optional:
# an unbound optional input is a missing input at run time, which the function
# answers with its own missing-data rule.
REQUIRED_INPUTS: Mapping[str, tuple[str, ...]] = {
    "fit_4pl": ("concentration", "response"),
    "inverse_4pl": ("bottom", "top", "slope", "inflection", "response"),
    "fit_loglog_linear": ("x", "y"),
    "inverse_loglog_linear": ("slope", "intercept", "y"),
    "replicate_mean_cv": ("replicates",),
    "spike_recovery": ("spiked", "unspiked", "nominal_spike"),
    "limit_compare": ("comparison", "value"),
    "apply_dilution": ("value", "dilution_factor"),
    "convert_units": ("value",),
    "subtract": ("minuend", "subtrahend"),
    "copy_raw": ("value",),
}

# limit_compare inputs that carry a limit. A stage that binds one reads a limit.
LIMIT_INPUTS = ("limit", "low", "high")

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_LABEL_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class ConfigRefusal(Exception):
    """A configuration is refused. ``code`` is stable; ``stage`` names the stage."""

    def __init__(self, code: str, message: str, stage: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage

    def detail(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.stage is not None:
            body["stage"] = self.stage
        return body


# ---- unit contracts (CALC-REQ-28) ------------------------------------------

CONTRACT_ONE = "one"
CONTRACT_PERCENT = "percent"
CONTRACT_NONE = "none"
CONTRACT_GROUP = "group"


@dataclass(frozen=True)
class UnitContract:
    """What a function's declared unit string asks of a binding.

    ``one``: dimensionless (the declaration ``1``). ``percent``: ``%``.
    ``none``: no unit (count, identity, token, pass/fail). ``group``: the unit
    is the lab's, declared on the binding; inputs and outputs in one group
    share one unit.
    """

    kind: str
    group: Optional[str] = None


def unit_contract(declared: str) -> UnitContract:
    """Read a catalog unit declaration. Raises ``ValueError`` for prose it does not know.

    A new catalog function with a new kind of declaration fails the test that
    reads the whole catalog, so the builder never silently skips a check.
    """
    text = declared.strip()
    if text == "1" or text.startswith("1 ("):
        return UnitContract(CONTRACT_ONE)
    if text == "%":
        return UnitContract(CONTRACT_PERCENT)
    if text in ("count", "identity", "token", ""):
        return UnitContract(CONTRACT_NONE)
    if text.startswith("square of"):
        return UnitContract(CONTRACT_GROUP, None)
    if "calibrator concentration unit" in text:
        return UnitContract(CONTRACT_GROUP, "concentration")
    if "calibrator response unit" in text:
        return UnitContract(CONTRACT_GROUP, "response")
    if text.startswith("x unit"):
        return UnitContract(CONTRACT_GROUP, "x")
    if text.startswith("y unit"):
        return UnitContract(CONTRACT_GROUP, "y")
    if text == "shared unit":
        return UnitContract(CONTRACT_GROUP, "shared")
    if text == "the replicate unit":
        return UnitContract(CONTRACT_GROUP, "replicate")
    if text in ("the value's unit", "the input's unit"):
        return UnitContract(CONTRACT_GROUP, "value")
    if text == "numerator unit":
        return UnitContract(CONTRACT_GROUP, "numerator")
    if text == "amount unit":
        return UnitContract(CONTRACT_GROUP, "amount")
    if text == "declared quotient":
        return UnitContract(CONTRACT_GROUP, None)
    raise ValueError(f"unit declaration not understood: {declared!r}")


@dataclass(frozen=True)
class UnitInfo:
    id: str
    name: str
    type_name: str


@dataclass(frozen=True)
class ConfigContext:
    """The facts a configuration is checked against. Nothing here is read from the database by this module."""

    analyte_id: str
    calculation_order: int
    # Calculation order of every analyte in the analysis that has a configuration.
    analyte_orders: Mapping[str, int] = field(default_factory=dict)
    # Every active unit the configuration names, by id.
    units: Mapping[str, UnitInfo] = field(default_factory=dict)
    # Saved formulas by (lower-cased name, version) -> text.
    saved_formulas: Mapping[tuple[str, int], str] = field(default_factory=dict)


# ---- parsed form ------------------------------------------------------------


@dataclass(frozen=True)
class OnFail:
    outcome: str
    verdict: Optional[str]
    flag: Optional[str]
    missing_limit_flag: Optional[str]
    gates: tuple[str, ...]
    precedence_place: Any  # int >= 1, or ABOVE_LIST

    def to_json(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "verdict": self.verdict,
            "flag": self.flag,
            "missing_limit_flag": self.missing_limit_flag,
            "gates": list(self.gates),
            "precedence_place": self.precedence_place,
        }


@dataclass(frozen=True)
class Stage:
    id: str
    kind: str
    bindings: Mapping[str, Mapping[str, Any]]
    on_fail: OnFail
    function: Optional[str] = None
    function_version: Optional[int] = None
    formula_name: Optional[str] = None
    formula_version: Optional[int] = None
    formula_text: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        body: dict[str, Any] = {"id": self.id, "kind": self.kind}
        if self.kind == STAGE_KIND_CATALOG:
            body["function"] = self.function
            body["function_version"] = self.function_version
        elif self.kind == STAGE_KIND_SAVED:
            body["formula_name"] = self.formula_name
            body["formula_version"] = self.formula_version
        else:
            body["formula_text"] = self.formula_text
            if self.formula_version is not None:
                body["formula_version"] = self.formula_version
        body["bindings"] = {name: dict(binding) for name, binding in self.bindings.items()}
        body["on_fail"] = self.on_fail.to_json()
        return body

    def with_formula_version(self, version: int) -> "Stage":
        return Stage(
            id=self.id,
            kind=self.kind,
            bindings=self.bindings,
            on_fail=self.on_fail,
            function=self.function,
            function_version=self.function_version,
            formula_name=self.formula_name,
            formula_version=version,
            formula_text=self.formula_text,
        )


@dataclass(frozen=True)
class ParsedConfig:
    name: str
    stages: tuple[Stage, ...]
    # The pointer to the stage output that will be published as the analyte's
    # result at experiment publish (S13). Every stage output is a calculated value.
    result_stage: str
    result_output: str

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "stages": [stage.to_json() for stage in self.stages],
            "result": {"stage": self.result_stage, "output": self.result_output},
        }


# ---- small readers ----------------------------------------------------------


def _object(value: Any, where: str, stage: Optional[str] = None) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ConfigRefusal("config_invalid", f"{where} must be an object.", stage)
    return value


def _check_keys(
    obj: Mapping[str, Any],
    allowed: Sequence[str],
    where: str,
    stage: Optional[str] = None,
) -> None:
    unknown = sorted(str(key) for key in obj if key not in allowed)
    if unknown:
        raise ConfigRefusal(
            "unknown_field", f"{where} has unknown field(s): {', '.join(unknown)}.", stage
        )


def _text(
    value: Any,
    where: str,
    max_length: int,
    stage: Optional[str] = None,
    code: str = "config_invalid",
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigRefusal(code, f"{where} must be non-empty text.", stage)
    if value != value.strip():
        raise ConfigRefusal(code, f"{where} cannot start or end with a space.", stage)
    if len(value) > max_length:
        raise ConfigRefusal(code, f"{where} is at most {max_length} characters.", stage)
    if _CONTROL_RE.search(value):
        raise ConfigRefusal(code, f"{where} cannot contain a control character.", stage)
    return value


def _integer(value: Any, where: str, minimum: int, stage: Optional[str] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigRefusal(
            "config_invalid", f"{where} must be a whole number of at least {minimum}.", stage
        )
    return value


def _uuid_text(value: Any, where: str, code: str, stage: Optional[str] = None) -> str:
    if not isinstance(value, str):
        raise ConfigRefusal(code, f"{where} must be a UUID.", stage)
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise ConfigRefusal(code, f"{where} must be a UUID.", stage) from exc


# ---- catalog access ---------------------------------------------------------


def _catalog_by_key() -> Mapping[tuple[str, int], Any]:
    return {version.key: version for version in closed_catalog()}


# ---- unit resolution --------------------------------------------------------

_UNKNOWN = None


def _resolve_unit(unit_id: str, ctx: ConfigContext, stage: str, input_name: str) -> tuple[str, ...]:
    info = ctx.units.get(unit_id)
    if info is None:
        raise ConfigRefusal(
            "unit_not_found",
            f"Stage {stage}: the unit on {input_name} is not an active unit.",
            stage,
        )
    if info.name == "%":
        return ("percent",)
    if info.type_name == "dimensionless":
        return ("one",)
    return ("unit", info.id)


def _unit_label(resolved: tuple[str, ...], ctx: ConfigContext) -> str:
    if resolved == ("one",):
        return "1"
    if resolved == ("percent",):
        return "%"
    if resolved == ("none",):
        return "no unit"
    info = ctx.units.get(resolved[1]) if len(resolved) > 1 else None
    return info.name if info else "a unit"


# ---- bindings ---------------------------------------------------------------


def _parse_binding(
    raw: Any,
    input_name: str,
    stage: str,
    stage_index: int,
    earlier: Mapping[str, "_StageInfo"],
    ctx: ConfigContext,
    *,
    unit_allowed: bool,
) -> dict[str, Any]:
    where = f"Stage {stage}: binding {input_name}"
    obj = _object(raw, where, stage)
    kind = obj.get("kind")
    if kind not in BINDING_KINDS:
        raise ConfigRefusal(
            "binding_kind_unknown",
            f"{where} must have kind run_field, stage_output, reference, or direct.",
            stage,
        )
    unit_keys = ("unit_id",)
    if kind == BINDING_RUN_FIELD:
        _check_keys(obj, ("kind", "entry_type", "field_name", "match_field", *unit_keys), where, stage)
        if obj.get("entry_type") not in ENTRY_TYPES:
            raise ConfigRefusal(
                "binding_invalid",
                f"{where}: entry_type must be experiment_data or experiment_sample_data.",
                stage,
            )
        binding: dict[str, Any] = {
            "kind": kind,
            "entry_type": obj["entry_type"],
            "field_name": _text(
                obj.get("field_name"), f"{where}: field_name", MAX_FIELD_NAME_LENGTH, stage, "binding_invalid"
            ),
        }
        if obj.get("match_field") is not None:
            binding["match_field"] = _text(
                obj["match_field"], f"{where}: match_field", MAX_FIELD_NAME_LENGTH, stage, "binding_invalid"
            )
    elif kind == BINDING_STAGE_OUTPUT:
        _check_keys(obj, ("kind", "stage", "output"), where, stage)
        source = obj.get("stage")
        output = obj.get("output")
        if not isinstance(source, str) or source not in earlier:
            raise ConfigRefusal(
                "stage_order_violation",
                f"{where}: stage_output must name an earlier stage. {source!r} is not one.",
                stage,
            )
        if not isinstance(output, str) or output not in earlier[source].outputs:
            raise ConfigRefusal(
                "binding_invalid",
                f"{where}: stage {source} has no output {output!r}.",
                stage,
            )
        binding = {"kind": kind, "stage": source, "output": output}
    elif kind == BINDING_REFERENCE:
        _check_keys(obj, ("kind", "analyte_id", "value", *unit_keys), where, stage)
        analyte_id = _uuid_text(obj.get("analyte_id"), f"{where}: analyte_id", "binding_invalid", stage)
        if obj.get("value") not in REFERENCE_VALUES:
            raise ConfigRefusal(
                "binding_invalid",
                f"{where}: value must be calculated or reported.",
                stage,
            )
        order = ctx.analyte_orders.get(analyte_id)
        if analyte_id == ctx.analyte_id:
            raise ConfigRefusal(
                "calculation_order_violation",
                f"{where}: a calculation cannot read its own analyte.",
                stage,
            )
        if order is None:
            raise ConfigRefusal(
                "reference_analyte_unknown",
                f"{where}: analyte {analyte_id} has no calculation in this analysis.",
                stage,
            )
        if order >= ctx.calculation_order:
            raise ConfigRefusal(
                "calculation_order_violation",
                f"{where}: analyte {analyte_id} is at calculation order {order}. "
                f"A calculation reads only an analyte earlier than its own order "
                f"({ctx.calculation_order}).",
                stage,
            )
        binding = {"kind": kind, "analyte_id": analyte_id, "value": obj["value"]}
    else:
        _check_keys(obj, ("kind", "value", *unit_keys), where, stage)
        value = obj.get("value")
        if not isinstance(value, str):
            raise ConfigRefusal(
                "direct_value_invalid",
                f"{where}: a value bound directly is text. A JSON number or boolean is refused.",
                stage,
            )
        if not value.strip() or value != value.strip() or len(value) > 64 or _CONTROL_RE.search(value):
            raise ConfigRefusal(
                "direct_value_invalid", f"{where}: the direct value is not usable text.", stage
            )
        binding = {"kind": kind, "value": value}

    if "unit_id" in obj and obj["unit_id"] is not None:
        if not unit_allowed:
            raise ConfigRefusal(
                "formula_term_unit_not_allowed",
                f"{where}: a saved or ad hoc formula stores no unit and does not check units.",
                stage,
            )
        binding["unit_id"] = _uuid_text(obj["unit_id"], f"{where}: unit_id", "unit_not_found", stage)
    return binding


@dataclass(frozen=True)
class _StageInfo:
    outputs: Mapping[str, Optional[tuple[str, ...]]]
    index: int


# ---- on-fail ----------------------------------------------------------------

_ON_FAIL_REQUIRED = ("outcome", "flag", "gates", "precedence_place")
_ON_FAIL_ALLOWED = (*_ON_FAIL_REQUIRED, "verdict", "missing_limit_flag")


def _label(value: Any, where: str, stage: str) -> str:
    text = _text(value, where, MAX_LABEL_LENGTH, stage, "on_fail_invalid")
    if not _LABEL_RE.match(text):
        raise ConfigRefusal(
            "on_fail_invalid",
            f"{where} uses lower-case letters, digits, and underscores, and starts with a letter.",
            stage,
        )
    if text == "pass":
        raise ConfigRefusal(
            "on_fail_pass_refused",
            f"Stage {stage}: {where} cannot be pass. There is no fail-open outcome.",
            stage,
        )
    return text


def _parse_on_fail(
    raw: Any,
    stage: str,
    stage_ids: Sequence[str],
    stage_index: int,
    function_name: Optional[str],
    reads_limit: bool,
) -> OnFail:
    if raw is None:
        raise ConfigRefusal(
            "on_fail_declaration_missing",
            f"Stage {stage} has no on-fail declaration. Declare the outcome, the flag it sets, "
            f"the stages it gates, and its precedence place.",
            stage,
        )
    obj = _object(raw, f"Stage {stage}: on_fail", stage)
    _check_keys(obj, _ON_FAIL_ALLOWED, f"Stage {stage}: on_fail", stage)
    missing = [key for key in _ON_FAIL_REQUIRED if key not in obj]
    if missing:
        raise ConfigRefusal(
            "on_fail_declaration_missing",
            f"Stage {stage}: the on-fail declaration is missing {', '.join(missing)}.",
            stage,
        )

    outcome = obj["outcome"]
    if outcome == "pass":
        raise ConfigRefusal(
            "on_fail_pass_refused",
            f"Stage {stage}: the on-fail outcome cannot be pass. There is no fail-open outcome.",
            stage,
        )
    if outcome is None or outcome == "":
        raise ConfigRefusal(
            "on_fail_declaration_missing",
            f"Stage {stage}: the on-fail outcome is empty.",
            stage,
        )
    if outcome == "on_fail_undeclared":
        raise ConfigRefusal(
            "on_fail_outcome_unknown",
            f"Stage {stage}: on_fail_undeclared is the stop for a missing declaration. It is not declared.",
            stage,
        )
    if not isinstance(outcome, str) or (
        outcome not in ON_FAIL_OUTCOMES and outcome not in STAGE_STOP_CODES
    ):
        raise ConfigRefusal(
            "on_fail_outcome_unknown",
            f"Stage {stage}: the on-fail outcome must be run_failed, dilution_invalid, "
            f"sample_verdict, flag, or a stage-stop code.",
            stage,
        )

    stops = FAILURE_STOPS.get(function_name or "", ())
    if stops:
        if outcome not in stops:
            raise ConfigRefusal(
                "on_fail_stage_stop_required",
                f"Stage {stage}: {function_name} fails with a stage stop. Declare one of "
                f"{', '.join(stops)}, not {outcome}.",
                stage,
            )
    elif outcome in STAGE_STOP_CODES:
        raise ConfigRefusal(
            "on_fail_stage_stop_not_applicable",
            f"Stage {stage}: this stage does not fail with the stage stop {outcome}. "
            f"Declare run_failed, dilution_invalid, sample_verdict, or flag.",
            stage,
        )

    flag = obj["flag"]
    if flag is not None:
        flag = _label(flag, "flag", stage)
    verdict = obj.get("verdict")
    if outcome == OUTCOME_SAMPLE_VERDICT:
        if verdict is None:
            raise ConfigRefusal(
                "on_fail_declaration_missing",
                f"Stage {stage}: a sample_verdict outcome names the verdict.",
                stage,
            )
        verdict = _label(verdict, "verdict", stage)
    elif verdict is not None:
        raise ConfigRefusal(
            "on_fail_invalid",
            f"Stage {stage}: verdict is only for the sample_verdict outcome.",
            stage,
        )
    if outcome == OUTCOME_FLAG and flag is None:
        raise ConfigRefusal(
            "on_fail_declaration_missing",
            f"Stage {stage}: a flag outcome names the flag it sets.",
            stage,
        )

    missing_limit_flag = obj.get("missing_limit_flag")
    if reads_limit:
        if missing_limit_flag is None:
            raise ConfigRefusal(
                "missing_limit_flag_required",
                f"Stage {stage} reads a limit, so it declares the missing-limit flag.",
                stage,
            )
        missing_limit_flag = _label(missing_limit_flag, "missing_limit_flag", stage)
    elif missing_limit_flag is not None:
        raise ConfigRefusal(
            "missing_limit_flag_not_applicable",
            f"Stage {stage} does not read a limit, so it has no missing-limit flag.",
            stage,
        )

    gates_raw = obj["gates"]
    if not isinstance(gates_raw, list):
        raise ConfigRefusal(
            "on_fail_invalid", f"Stage {stage}: gates must be a list of stage ids.", stage
        )
    gates: list[str] = []
    for gate in gates_raw:
        if not isinstance(gate, str) or gate not in stage_ids:
            raise ConfigRefusal(
                "gate_unknown_stage",
                f"Stage {stage}: gates names {gate!r}, which is not a stage in this configuration.",
                stage,
            )
        if stage_ids.index(gate) <= stage_index:
            raise ConfigRefusal(
                "gate_not_later",
                f"Stage {stage}: gates names {gate}, which does not come after this stage.",
                stage,
            )
        if gate in gates:
            raise ConfigRefusal(
                "on_fail_invalid", f"Stage {stage}: gates names {gate} twice.", stage
            )
        gates.append(gate)

    place = obj["precedence_place"]
    is_stop = outcome in STAGE_STOP_CODES
    if place == ABOVE_LIST:
        if not is_stop:
            raise ConfigRefusal(
                "precedence_place_invalid",
                f"Stage {stage}: only a stage stop sits above the list. Give a place number.",
                stage,
            )
    else:
        if isinstance(place, bool) or not isinstance(place, int) or not 1 <= place <= MAX_PRECEDENCE_PLACE:
            raise ConfigRefusal(
                "precedence_place_invalid",
                f"Stage {stage}: the precedence place is a whole number from 1, or above_list "
                f"for a stage stop.",
                stage,
            )
        if is_stop:
            raise ConfigRefusal(
                "precedence_place_invalid",
                f"Stage {stage}: a stage stop is above the list. Declare precedence_place above_list.",
                stage,
            )
    return OnFail(
        outcome=outcome,
        verdict=verdict,
        flag=flag,
        missing_limit_flag=missing_limit_flag,
        gates=tuple(gates),
        precedence_place=place,
    )


def _claim(on_fail: OnFail) -> str:
    """What a stage claims its precedence place for: the flag, else the verdict, else the outcome."""
    if on_fail.flag is not None:
        return f"flag:{on_fail.flag}"
    if on_fail.verdict is not None:
        return f"verdict:{on_fail.verdict}"
    return f"outcome:{on_fail.outcome}"


def _check_precedence(stages: Sequence[Stage]) -> None:
    """A place is claimed for one thing. Two stages at place 1 for different flags are refused."""
    claims: dict[int, tuple[str, str]] = {}
    for stage in stages:
        place = stage.on_fail.precedence_place
        if place == ABOVE_LIST:
            continue
        claim = _claim(stage.on_fail)
        held = claims.get(place)
        if held is None:
            claims[place] = (claim, stage.id)
        elif held[0] != claim:
            raise ConfigRefusal(
                "precedence_place_conflict",
                f"Stages {held[1]} and {stage.id} both claim precedence place {place} "
                f"for different outcomes ({held[0]} and {claim}).",
                stage.id,
            )


# ---- formulas ---------------------------------------------------------------


def _parse_formula_text(text: Any, stage: str) -> ParsedFormula:
    if not isinstance(text, str):
        raise ConfigRefusal("formula_invalid", f"Stage {stage}: the formula must be text.", stage)
    try:
        parsed = parse_formula(text)
    except FormulaSyntaxError as exc:
        raise ConfigRefusal(exc.code, f"Stage {stage}: {exc.message}", stage) from exc
    root = parsed.root
    if isinstance(root, FormulaCall) and root.name in ("LINEST", "TREND"):
        raise ConfigRefusal(
            "formula_result_not_scalar",
            f"Stage {stage}: the formula returns a list. Use one value.",
            stage,
        )
    for name in sorted(parsed.names):
        problem = term_name_error(name)
        if problem:
            raise ConfigRefusal("formula_unknown_name", f"Stage {stage}: {problem}", stage)
    return parsed


# ---- the configuration ------------------------------------------------------


def parse_config(raw: Any, ctx: ConfigContext) -> ParsedConfig:
    """Check ``raw`` against the builder's rules. Returns the normal form, or raises :class:`ConfigRefusal`."""
    obj = _object(raw, "The configuration")
    _check_keys(obj, ("name", "stages", "result"), "The configuration")
    name = _text(obj.get("name"), "name", MAX_NAME_LENGTH, None, "config_invalid")

    stages_raw = obj.get("stages")
    if not isinstance(stages_raw, list) or not stages_raw:
        raise ConfigRefusal("config_invalid", "stages must be a list with at least one stage.")
    if len(stages_raw) > MAX_STAGES:
        raise ConfigRefusal("config_invalid", f"A configuration has at most {MAX_STAGES} stages.")

    stage_ids: list[str] = []
    for index, item in enumerate(stages_raw):
        stage_obj = _object(item, f"Stage {index + 1}")
        stage_id = stage_obj.get("id")
        if not isinstance(stage_id, str) or not _ID_RE.match(stage_id):
            raise ConfigRefusal(
                "stage_id_invalid",
                f"Stage {index + 1}: id uses lower-case letters, digits, and underscores, "
                f"starts with a letter, and is at most 40 characters.",
            )
        if stage_id in stage_ids:
            raise ConfigRefusal(
                "stage_id_duplicate", f"Stage id {stage_id} is used twice.", stage_id
            )
        stage_ids.append(stage_id)

    catalog = _catalog_by_key()
    earlier: dict[str, _StageInfo] = {}
    stages: list[Stage] = []

    for index, item in enumerate(stages_raw):
        stage_obj: Mapping[str, Any] = item
        stage_id = stage_ids[index]
        kind = stage_obj.get("kind")
        if kind not in STAGE_KINDS:
            raise ConfigRefusal(
                "stage_kind_unknown",
                f"Stage {stage_id}: kind must be catalog_function, saved_formula, or ad_hoc_formula.",
                stage_id,
            )
        common = ("id", "kind", "bindings", "on_fail")
        function_name: Optional[str] = None
        function_version: Optional[int] = None
        formula_name: Optional[str] = None
        formula_version: Optional[int] = None
        formula_text: Optional[str] = None
        function = None
        parsed_formula: Optional[ParsedFormula] = None

        if kind == STAGE_KIND_CATALOG:
            _check_keys(stage_obj, (*common, "function", "function_version"), f"Stage {stage_id}", stage_id)
            function_name = stage_obj.get("function")
            function_version = stage_obj.get("function_version")
            if (
                not isinstance(function_name, str)
                or isinstance(function_version, bool)
                or not isinstance(function_version, int)
                or (function_name, function_version) not in catalog
            ):
                raise ConfigRefusal(
                    "catalog_function_unknown",
                    f"Stage {stage_id}: {function_name!r} version {function_version!r} is not in the "
                    f"catalog. The builder offers only catalog functions.",
                    stage_id,
                )
            function = catalog[(function_name, function_version)]
        elif kind == STAGE_KIND_SAVED:
            _check_keys(stage_obj, (*common, "formula_name", "formula_version"), f"Stage {stage_id}", stage_id)
            formula_name = _text(
                stage_obj.get("formula_name"), "formula_name", MAX_NAME_LENGTH, stage_id, "saved_formula_unknown"
            )
            formula_version = _integer(stage_obj.get("formula_version"), "formula_version", 1, stage_id)
            key = (formula_name.lower(), formula_version)
            if key not in ctx.saved_formulas:
                raise ConfigRefusal(
                    "saved_formula_unknown",
                    f"Stage {stage_id}: there is no saved formula {formula_name!r} version {formula_version}.",
                    stage_id,
                )
            formula_text = None
            parsed_formula = _parse_formula_text(ctx.saved_formulas[key], stage_id)
        else:
            _check_keys(stage_obj, (*common, "formula_text"), f"Stage {stage_id}", stage_id)
            formula_text = stage_obj.get("formula_text")
            parsed_formula = _parse_formula_text(formula_text, stage_id)

        bindings_raw = stage_obj.get("bindings")
        if bindings_raw is None:
            bindings_raw = {}
        bindings_obj = _object(bindings_raw, f"Stage {stage_id}: bindings", stage_id)

        if function is not None:
            known_inputs = list(function.inputs)
        else:
            assert parsed_formula is not None
            known_inputs = sorted(parsed_formula.names)
            try:
                check_names(parsed_formula, set(bindings_obj))
            except FormulaSyntaxError as exc:
                raise ConfigRefusal(
                    "formula_term_unbound",
                    f"Stage {stage_id}: {exc.message} Bind each term the formula names.",
                    stage_id,
                ) from exc

        for input_name in bindings_obj:
            if input_name not in known_inputs:
                raise ConfigRefusal(
                    "binding_unknown_input",
                    f"Stage {stage_id}: {input_name!r} is not an input of this stage.",
                    stage_id,
                )
        if function is not None:
            for required in REQUIRED_INPUTS.get(function.name, ()):
                if required not in bindings_obj:
                    raise ConfigRefusal(
                        "binding_missing",
                        f"Stage {stage_id}: {function.name} needs {required} bound.",
                        stage_id,
                    )

        bindings: dict[str, dict[str, Any]] = {}
        for input_name, binding_raw in bindings_obj.items():
            bindings[input_name] = _parse_binding(
                binding_raw,
                input_name,
                stage_id,
                index,
                earlier,
                ctx,
                unit_allowed=function is not None,
            )

        reads_limit = False
        if function is not None:
            _check_catalog_bindings(function, bindings, stage_id)
            reads_limit = function.name == "limit_compare" and any(
                limit_input in bindings for limit_input in LIMIT_INPUTS
            )
            outputs = _check_units(function, bindings, stage_id, earlier, ctx)
        else:
            for term, binding in bindings.items():
                if binding["kind"] == BINDING_DIRECT and not is_decimal_string(binding["value"]):
                    raise ConfigRefusal(
                        "direct_value_invalid",
                        f"Stage {stage_id}: the direct value of {term} is a decimal string such as 0.5.",
                        stage_id,
                    )
            outputs = {FORMULA_OUTPUT: None}

        on_fail = _parse_on_fail(
            stage_obj.get("on_fail"),
            stage_id,
            stage_ids,
            index,
            function.name if function is not None else None,
            reads_limit,
        )

        stages.append(
            Stage(
                id=stage_id,
                kind=kind,
                bindings=bindings,
                on_fail=on_fail,
                function=function_name,
                function_version=function_version,
                formula_name=formula_name,
                formula_version=formula_version,
                formula_text=formula_text,
            )
        )
        earlier[stage_id] = _StageInfo(outputs=outputs, index=index)

    _check_precedence(stages)

    # ``result`` points at the output that will be published as the analyte's
    # result when the experiment is published (S13). It is not a result itself.
    result_obj = _object(obj.get("result"), "result")
    _check_keys(result_obj, ("stage", "output"), "result")
    result_stage = result_obj.get("stage")
    result_output = result_obj.get("output")
    if not isinstance(result_stage, str) or result_stage not in earlier:
        raise ConfigRefusal("result_invalid", "result.stage must name a stage in this configuration.")
    if not isinstance(result_output, str) or result_output not in earlier[result_stage].outputs:
        raise ConfigRefusal(
            "result_invalid", f"Stage {result_stage} has no output {result_output!r}."
        )
    return ParsedConfig(
        name=name,
        stages=tuple(stages),
        result_stage=result_stage,
        result_output=result_output,
    )


def _check_catalog_bindings(
    function: Any, bindings: Mapping[str, Mapping[str, Any]], stage: str
) -> None:
    """Rules specific to a function's inputs that are not unit rules."""
    function_name = function.name
    for input_name, binding in bindings.items():
        declared = function.inputs[input_name]
        contract = unit_contract(declared)
        if contract.kind == CONTRACT_NONE:
            if "unit_id" in binding:
                raise ConfigRefusal(
                    "unit_binding_mismatch",
                    f"Stage {stage}: {input_name} has no unit. Remove unit_id.",
                    stage,
                )
            if declared == "token":
                if binding["kind"] != BINDING_DIRECT or binding["value"] not in COMPARISONS:
                    raise ConfigRefusal(
                        "binding_invalid",
                        f"Stage {stage}: {input_name} is bound directly, as one of "
                        f"{', '.join(COMPARISONS)}.",
                        stage,
                    )
            elif declared == "identity" and binding["kind"] not in (BINDING_RUN_FIELD, BINDING_REFERENCE):
                raise ConfigRefusal(
                    "binding_invalid",
                    f"Stage {stage}: {input_name} identifies a record. Bind it to a field of an entry in the run.",
                    stage,
                )
            elif binding["kind"] == BINDING_STAGE_OUTPUT:
                raise ConfigRefusal(
                    "binding_invalid",
                    f"Stage {stage}: {input_name} cannot take a stage output.",
                    stage,
                )
        if binding["kind"] == BINDING_DIRECT and contract.kind != CONTRACT_NONE:
            if not is_decimal_string(binding["value"]):
                raise ConfigRefusal(
                    "direct_value_invalid",
                    f"Stage {stage}: the direct value of {input_name} is a decimal string such as 0.5.",
                    stage,
                )
        if function_name == "limit_compare" and input_name == "absolute" and binding["kind"] == BINDING_DIRECT:
            if binding["value"] not in ("0", "1"):
                raise ConfigRefusal(
                    "direct_value_invalid",
                    f"Stage {stage}: absolute is 0 or 1.",
                    stage,
                )
    if function_name == "limit_compare":
        comparison = bindings["comparison"]["value"]
        needed = ("low", "high") if comparison == "within" else ("limit",)
        for bound in needed:
            if bound not in bindings:
                raise ConfigRefusal(
                    "binding_missing",
                    f"Stage {stage}: comparison {comparison} needs {bound} bound.",
                    stage,
                )
        unused = [name for name in LIMIT_INPUTS if name in bindings and name not in needed]
        if unused:
            raise ConfigRefusal(
                "binding_unknown_input",
                f"Stage {stage}: comparison {comparison} does not use {', '.join(unused)}.",
                stage,
            )


def _check_units(
    function: Any,
    bindings: Mapping[str, Mapping[str, Any]],
    stage: str,
    earlier: Mapping[str, _StageInfo],
    ctx: ConfigContext,
) -> dict[str, Optional[tuple[str, ...]]]:
    """CALC-REQ-28: a binding's unit must fit the function's declared unit.

    Returns the unit each output carries, so a later stage that takes it is
    checked the same way. A group with no known unit gives an output with no
    known unit.
    """
    groups: dict[str, dict[str, tuple[str, ...]]] = {}
    for input_name, binding in bindings.items():
        contract = unit_contract(function.inputs[input_name])
        resolved: Optional[tuple[str, ...]] = _UNKNOWN
        if "unit_id" in binding:
            resolved = _resolve_unit(binding["unit_id"], ctx, stage, input_name)
        elif binding["kind"] == BINDING_STAGE_OUTPUT:
            resolved = earlier[binding["stage"]].outputs.get(binding["output"])

        if contract.kind == CONTRACT_ONE:
            if resolved is not None and resolved != ("one",):
                raise ConfigRefusal(
                    "unit_binding_mismatch",
                    f"Stage {stage}: {input_name} is dimensionless (declared 1). "
                    f"It cannot take {_unit_label(resolved, ctx)}.",
                    stage,
                )
        elif contract.kind == CONTRACT_PERCENT:
            if resolved is not None and resolved != ("percent",):
                raise ConfigRefusal(
                    "unit_binding_mismatch",
                    f"Stage {stage}: {input_name} is a percentage. It cannot take {_unit_label(resolved, ctx)}.",
                    stage,
                )
        elif contract.kind == CONTRACT_GROUP and contract.group is not None and resolved is not None:
            members = groups.setdefault(contract.group, {})
            for other_name, other in members.items():
                if other != resolved:
                    raise ConfigRefusal(
                        "unit_binding_mismatch",
                        f"Stage {stage}: {input_name} ({_unit_label(resolved, ctx)}) and "
                        f"{other_name} ({_unit_label(other, ctx)}) share one declared unit in "
                        f"{function.name}.",
                        stage,
                    )
            members[input_name] = resolved

    outputs: dict[str, Optional[tuple[str, ...]]] = {}
    for output_name, declared in function.outputs.items():
        contract = unit_contract(declared)
        if contract.kind == CONTRACT_ONE:
            outputs[output_name] = ("one",)
        elif contract.kind == CONTRACT_PERCENT:
            outputs[output_name] = ("percent",)
        elif contract.kind == CONTRACT_NONE:
            outputs[output_name] = ("none",)
        elif contract.group is not None and contract.group in groups:
            outputs[output_name] = next(iter(groups[contract.group].values()))
        else:
            outputs[output_name] = _UNKNOWN
    return outputs


# ---- versions of an ad hoc formula ------------------------------------------


def assign_ad_hoc_versions(
    parsed: ParsedConfig, prior_config: Optional[Mapping[str, Any]]
) -> ParsedConfig:
    """Give each ad hoc formula its version: 1 when new, +1 when its text changed, else unchanged.

    CALC-REQ-40 pins the text and version of every ad hoc formula. The client
    sends the text only; the server owns the number.
    """
    prior: dict[str, tuple[str, int]] = {}
    if prior_config:
        for stage in prior_config.get("stages", []):
            if stage.get("kind") == STAGE_KIND_AD_HOC:
                prior[stage["id"]] = (stage["formula_text"], int(stage.get("formula_version", 1)))
    stages: list[Stage] = []
    for stage in parsed.stages:
        if stage.kind == STAGE_KIND_AD_HOC:
            before = prior.get(stage.id)
            if before is None:
                version = 1
            elif before[0] == stage.formula_text:
                version = before[1]
            else:
                version = before[1] + 1
            stage = stage.with_formula_version(version)
        stages.append(stage)
    return ParsedConfig(
        name=parsed.name,
        stages=tuple(stages),
        result_stage=parsed.result_stage,
        result_output=parsed.result_output,
    )


def formula_stage_signature(stage: Mapping[str, Any]) -> str:
    """A stable text for comparing one stored formula stage with a submitted one."""
    import json

    return json.dumps(stage, sort_keys=True, separators=(",", ":"))


def formula_stages_changed(
    new_config: Mapping[str, Any], prior_config: Optional[Mapping[str, Any]]
) -> list[str]:
    """Ids of formula stages that are new or differ from the stored configuration.

    Only a lab admin writes a formula (CALC-REQ-23). A save by anyone else is
    refused when this list is not empty.
    """
    prior: dict[str, str] = {}
    if prior_config:
        for stage in prior_config.get("stages", []):
            if stage.get("kind") in FORMULA_KINDS:
                prior[stage["id"]] = formula_stage_signature(stage)
    changed: list[str] = []
    for stage in new_config.get("stages", []):
        if stage.get("kind") not in FORMULA_KINDS:
            continue
        if prior.get(stage["id"]) != formula_stage_signature(stage):
            changed.append(stage["id"])
    return changed


def referenced_analytes(config: Mapping[str, Any]) -> set[str]:
    """Analyte ids a stored configuration reads through reference bindings."""
    found: set[str] = set()
    for stage in config.get("stages", []):
        for binding in stage.get("bindings", {}).values():
            if binding.get("kind") == BINDING_REFERENCE:
                found.add(binding["analyte_id"])
    return found


def catalog_entries() -> list[dict[str, Any]]:
    """The read-only catalog for the builder's picker (CALC-REQ-22, CALC-REQ-45)."""
    entries: list[dict[str, Any]] = []
    for version in closed_catalog():
        entries.append(
            {
                "name": version.name,
                "version": version.version,
                "side": str(getattr(version.side, "value", version.side)),
                "description": version.description,
                "inputs": dict(version.inputs),
                "outputs": dict(version.outputs),
                "required_inputs": list(REQUIRED_INPUTS.get(version.name, ())),
                "stop_rule": version.stop_rule,
                "missing_data_rule": version.missing_data_rule,
                "failure_stops": list(FAILURE_STOPS.get(version.name, ())),
            }
        )
    return entries
