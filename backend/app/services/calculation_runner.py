"""The stage runner (calculations S9).

CALC-REQ-25 (stop rules), 26 (missing data), 21 (run summary), 48 (on-fail at
run time), 37 (decimal in the backend, R only on named routes), 53
(``copy_raw``), 58 (a metadata analyte is read as an analyte).

This module is pure. It reads no database. The caller gives it the stored
configuration, the saved formula texts, and a :class:`RunContext`: an input
reader for run fields and reference inputs, the R client, a unit lookup, and
the pairing unit. :func:`prepare_plan` checks the stored configuration before
any call is accepted; a :class:`PlanRefused` there is HTTP 400 and writes
nothing. :func:`run_plan` runs the stages in order and returns a
:class:`RunOutcome`, which the caller records as the calculation attempt.

How a stage ends
----------------
* ``ok``: it produced its outputs.
* ``flagged``: it produced outputs and the function raised a flag
  (``replicate_missing``, ``mean_zero``). The flag is recorded and carried;
  the on-fail declaration is not applied.
* ``failed``: a check missed. No output with a flag (``missing_input``,
  ``limit_above_el``, ``inactive``, ``response_at_asymptote``), a
  ``missing_limit`` with no verdict, a ``fail`` verdict, or an input the
  function refuses (``apply_dilution`` below 1). The declared outcome applies
  at its precedence place, and the declared gates do not run.
* ``no_verdict``: ``limit_compare`` does not judge this qualified value
  (``unspecified``). Not a failure.
* ``qualified``: an inverse function answered ``<`` or ``>``. Not a stop and
  not missing. A stage that reads its output does not run (``skipped``).
* ``stopped``: a stage stop (CALC-REQ-25) or a lab-written formula error. The
  attempt stops, nothing further runs, and calculated and reported are cleared.
* ``gated``, ``skipped``, ``not_reached``: the stage did not run.

A stage with no usable on-fail declaration stops with ``on_fail_undeclared``.
An R refusal that is not a timeout (lock, sandbox, route, service) is raised
unchanged: the caller writes nothing. A timeout is a stage stop.

Wording (Marc, 2026-11-22): a stage output is a calculated value, not a
result, until the experiment is published (S13).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence

from app.services.calculation_catalog import closed_catalog
from app.services.calculation_catalog_decimal import (
    PER_AMOUNT,
    WITHIN_TYPE,
    UnitFactor,
    apply_dilution,
    convert_units,
    copy_raw,
    subtract,
)
from app.services.calculation_catalog_r import (
    FOUR_PL_PARAMETERS,
    CatalogInputRefused,
    StageResult,
    fit_4pl,
    fit_loglog_linear,
    inverse_4pl,
    inverse_loglog_linear,
)
from app.services.calculation_catalog_s5 import (
    MISSING_LIMIT,
    UNSPECIFIED,
    limit_compare,
    replicate_mean_cv,
    spike_recovery,
)
from app.services.calculation_config import (
    BINDING_DIRECT,
    BINDING_REFERENCE,
    BINDING_RUN_FIELD,
    BINDING_STAGE_OUTPUT,
    FAILURE_STOPS,
    FORMULA_OUTPUT,
    ON_FAIL_OUTCOMES,
    OUTCOME_FLAG,
    OUTCOME_RUN_FAILED,
    STAGE_KIND_AD_HOC,
    STAGE_KIND_CATALOG,
    STAGE_KIND_SAVED,
    STAGE_STOP_CODES,
)
from app.services.calculation_formula import (
    KNOCKED_OUT,
    FormulaSyntaxError,
    ParsedFormula,
    format_value,
    parse_formula,
    run_formula,
)

ATTEMPT_COMPLETED = "completed"
ATTEMPT_STOPPED = "stopped"

SUMMARY_PASS = "pass"
SUMMARY_FAIL = "fail"
SUMMARY_STOPPED = "stopped"

ON_FAIL_UNDECLARED = "on_fail_undeclared"
# CALC-REQ-28 names two unit stops and locks no spelling for them. The catalog
# function already returns ``unit_not_found``; this is the other one.
UNIT_TYPE_MISMATCH = "unit_type_mismatch"

STAGE_OK = "ok"
STAGE_FLAGGED = "flagged"
STAGE_FAILED = "failed"
STAGE_NO_VERDICT = "no_verdict"
STAGE_QUALIFIED = "qualified"
STAGE_STOPPED = "stopped"
STAGE_GATED = "gated"
STAGE_SKIPPED = "skipped"
STAGE_NOT_REACHED = "not_reached"

_RAN = (STAGE_OK, STAGE_FLAGGED, STAGE_FAILED, STAGE_NO_VERDICT)


class PlanRefused(Exception):
    """The stored configuration cannot be run. HTTP 400; no attempt is written."""

    def __init__(self, code: str, message: str, stage: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage


class ReadStop(Exception):
    """A run field or reference cannot be read: ``reference_missing``,
    ``reference_ambiguous``, or ``reference_stopped`` (CALC-REQ-25, 50)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Knocked:
    """A value that is knocked out. A formula reads it as ``#N/A``; a catalog
    function reads it as missing (CALC-REQ-27)."""

    value: Any


@dataclass(frozen=True)
class InputRead:
    """What a reader returns for one binding.

    ``value`` is a decimal string, ``None``, a :class:`Knocked`, or a list of
    those. ``unit`` is the unit name of the value as read (the raw units, or
    the pairing unit when there are none). ``sources`` names each entry,
    record, and field read, with its value (CALC-REQ-30, 50).
    """

    value: Any
    unit: Optional[str] = None
    sources: tuple[Mapping[str, Any], ...] = ()


class InputReader(Protocol):
    def read(self, binding: Mapping[str, Any]) -> InputRead:
        ...


UnitLookup = Callable[[str], Optional[UnitFactor]]


@dataclass
class RunContext:
    reader: InputReader
    r_client: Any
    unit_lookup: UnitLookup
    pairing_unit: Optional[str] = None
    unit_names: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedStage:
    index: int
    id: str
    kind: str
    raw: Mapping[str, Any]
    bindings: Mapping[str, Mapping[str, Any]]
    function: Optional[Any] = None
    formula: Optional[ParsedFormula] = None
    formula_name: Optional[str] = None
    formula_version: Optional[int] = None


@dataclass(frozen=True)
class Plan:
    name: str
    stages: tuple[PlannedStage, ...]
    result_stage: str
    result_output: str

    def bindings(self) -> List[tuple[PlannedStage, str, Mapping[str, Any]]]:
        return [
            (stage, input_name, binding)
            for stage in self.stages
            for input_name, binding in stage.bindings.items()
        ]


@dataclass
class RunOutcome:
    status: str
    run_summary: str
    summary_check: Optional[str]
    summary_code: Optional[str]
    calculated: Optional[str]
    reported: Optional[str]
    stop_code: Optional[str] = None
    stop_stage: Optional[str] = None
    stop_detail: Optional[str] = None
    formula_error: Optional[str] = None
    stages: List[Dict[str, Any]] = field(default_factory=list)
    function_versions: List[Dict[str, Any]] = field(default_factory=list)
    formula_versions: List[Dict[str, Any]] = field(default_factory=list)
    inputs_read: List[Dict[str, Any]] = field(default_factory=list)
    values_used: List[Dict[str, Any]] = field(default_factory=list)
    knocked_out_points: List[Dict[str, Any]] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)
    result_note: Optional[Dict[str, Any]] = None

    @property
    def stopped(self) -> bool:
        return self.status == ATTEMPT_STOPPED

    def to_json(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "stop_code": self.stop_code,
            "stop_stage": self.stop_stage,
            "stop_detail": self.stop_detail,
            "formula_error": self.formula_error,
            "run_summary": self.run_summary,
            "summary_check": self.summary_check,
            "summary_code": self.summary_code,
            "calculated": self.calculated,
            "reported": self.reported,
            "result_note": self.result_note,
            "stages": self.stages,
            "function_versions": self.function_versions,
            "formula_versions": self.formula_versions,
            "inputs_read": self.inputs_read,
            "values_used": self.values_used,
            "knocked_out_points": self.knocked_out_points,
            "flags": [flag["flag"] for flag in self.flags if flag.get("flag")],
            "flag_records": self.flags,
        }


# ---- the plan -----------------------------------------------------------------


def _catalog() -> Mapping[tuple[str, int], Any]:
    return {version.key: version for version in closed_catalog()}


def _parse(text: Any, stage_id: str) -> ParsedFormula:
    if not isinstance(text, str):
        raise PlanRefused("configuration_unreadable", f"Stage {stage_id}: the formula is not text.", stage_id)
    try:
        return parse_formula(text)
    except FormulaSyntaxError as exc:
        raise PlanRefused(
            "configuration_unreadable", f"Stage {stage_id}: {exc.message}", stage_id
        ) from exc


def prepare_plan(config: Any, saved_formulas: Mapping[tuple[str, int], str]) -> Plan:
    """Read a stored configuration. Nothing is called; a refusal writes nothing."""
    if not isinstance(config, Mapping):
        raise PlanRefused("configuration_unreadable", "The stored configuration is not an object.")
    stages_raw = config.get("stages")
    result = config.get("result")
    if not isinstance(stages_raw, list) or not stages_raw or not isinstance(result, Mapping):
        raise PlanRefused("configuration_unreadable", "The stored configuration has no stages or no result pointer.")
    catalog = _catalog()
    stages: list[PlannedStage] = []
    seen: set[str] = set()
    for index, raw in enumerate(stages_raw):
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            raise PlanRefused("configuration_unreadable", f"Stage {index + 1} has no id.")
        stage_id = raw["id"]
        if stage_id in seen:
            raise PlanRefused("configuration_unreadable", f"Stage id {stage_id} is used twice.", stage_id)
        seen.add(stage_id)
        bindings = raw.get("bindings") or {}
        if not isinstance(bindings, Mapping) or not all(isinstance(b, Mapping) for b in bindings.values()):
            raise PlanRefused("configuration_unreadable", f"Stage {stage_id}: bindings are not objects.", stage_id)
        kind = raw.get("kind")
        if kind == STAGE_KIND_CATALOG:
            key = (raw.get("function"), raw.get("function_version"))
            function = catalog.get(key)  # type: ignore[arg-type]
            if function is None:
                raise PlanRefused(
                    "catalog_function_unknown",
                    f"Stage {stage_id}: {key[0]!r} version {key[1]!r} is not in the catalog.",
                    stage_id,
                )
            stages.append(PlannedStage(index, stage_id, kind, raw, bindings, function=function))
        elif kind == STAGE_KIND_SAVED:
            name = raw.get("formula_name")
            version = raw.get("formula_version")
            if not isinstance(name, str) or isinstance(version, bool) or not isinstance(version, int):
                raise PlanRefused("configuration_unreadable", f"Stage {stage_id}: no saved formula is named.", stage_id)
            text = saved_formulas.get((name.lower(), version))
            if text is None:
                raise PlanRefused(
                    "saved_formula_unknown",
                    f"Stage {stage_id}: there is no saved formula {name!r} version {version}.",
                    stage_id,
                )
            stages.append(
                PlannedStage(
                    index, stage_id, kind, raw, bindings,
                    formula=_parse(text, stage_id), formula_name=name, formula_version=version,
                )
            )
        elif kind == STAGE_KIND_AD_HOC:
            version = raw.get("formula_version")
            stages.append(
                PlannedStage(
                    index, stage_id, kind, raw, bindings,
                    formula=_parse(raw.get("formula_text"), stage_id),
                    formula_version=version if isinstance(version, int) and not isinstance(version, bool) else None,
                )
            )
        else:
            raise PlanRefused("configuration_unreadable", f"Stage {stage_id}: unknown kind {kind!r}.", stage_id)
    pointer_stage = result.get("stage")
    pointer_output = result.get("output")
    if pointer_stage not in seen or not isinstance(pointer_output, str):
        raise PlanRefused("configuration_unreadable", "The result pointer does not name a stage output.")
    name = config.get("name")
    return Plan(
        name=name if isinstance(name, str) else "",
        stages=tuple(stages),
        result_stage=pointer_stage,
        result_output=pointer_output,
    )


# ---- on-fail ------------------------------------------------------------------


@dataclass(frozen=True)
class _OnFail:
    outcome: str
    verdict: Optional[str]
    flag: Optional[str]
    missing_limit_flag: Optional[str]
    gates: tuple[str, ...]
    place: Any


def _on_fail(stage: PlannedStage) -> Optional[_OnFail]:
    """The stage's declaration, or None when it is missing or not usable (fail closed)."""
    raw = stage.raw.get("on_fail")
    if not isinstance(raw, Mapping):
        return None
    if any(key not in raw for key in ("outcome", "flag", "gates", "precedence_place")):
        return None
    outcome = raw.get("outcome")
    if not isinstance(outcome, str) or outcome == "pass":
        return None
    if outcome not in ON_FAIL_OUTCOMES and outcome not in STAGE_STOP_CODES:
        return None
    gates = raw.get("gates")
    if not isinstance(gates, list) or not all(isinstance(gate, str) for gate in gates):
        return None
    flag = raw.get("flag")
    verdict = raw.get("verdict")
    missing_limit_flag = raw.get("missing_limit_flag")
    return _OnFail(
        outcome=outcome,
        verdict=verdict if isinstance(verdict, str) else None,
        flag=flag if isinstance(flag, str) else None,
        missing_limit_flag=missing_limit_flag if isinstance(missing_limit_flag, str) else None,
        gates=tuple(gates),
        place=raw.get("precedence_place"),
    )


# ---- values -------------------------------------------------------------------


def jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, Knocked):
        return {"knocked_out": True, "value": jsonable(value.value)}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return format_value(value)
    return value


def _plain(value: Any) -> Any:
    """What a catalog function reads: a knocked-out value is missing."""
    if isinstance(value, Knocked):
        return None
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _term(value: Any) -> Any:
    """What a formula reads: a knocked-out value is ``#N/A`` (CALC-REQ-27)."""
    if isinstance(value, Knocked):
        return KNOCKED_OUT
    return value


def _as_list(value: Any) -> Optional[list]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _knocked_items(value: Any) -> List[Any]:
    if isinstance(value, Knocked):
        return [jsonable(value.value)]
    if isinstance(value, (list, tuple)):
        return [jsonable(item.value) for item in value if isinstance(item, Knocked)]
    return []


# ---- one catalog call ---------------------------------------------------------


def _absolute(value: Any) -> bool:
    if value is None:
        return False
    if value in ("0", "1"):
        return value == "1"
    raise CatalogInputRefused("absolute is 0 or 1")


def _points(columns: Mapping[str, Optional[list]], required: Sequence[str]) -> list[dict[str, Any]]:
    lengths = {len(values) for values in columns.values() if values is not None}
    if len(lengths) > 1:
        raise CatalogInputRefused("the point inputs are lists of different lengths")
    count = lengths.pop() if lengths else 0
    points: list[dict[str, Any]] = []
    for i in range(count):
        point: dict[str, Any] = {}
        for name, values in columns.items():
            if values is not None:
                point[name] = values[i]
            elif name in required:
                point[name] = None
        points.append(point)
    return points


def _convert(
    value: Any, amount: Any, amount_bound: bool, value_unit: Optional[str], ctx: RunContext
) -> StageResult:
    if amount_bound:
        return convert_units(value, mode=PER_AMOUNT, amount=amount)
    source = value_unit or ctx.pairing_unit
    target = ctx.pairing_unit
    if source and target:
        source_factor = ctx.unit_lookup(source)
        target_factor = ctx.unit_lookup(target)
        if (
            source_factor is not None
            and target_factor is not None
            and source_factor.type_name != target_factor.type_name
        ):
            return StageResult(
                "convert_units",
                1,
                {},
                False,
                stop=UNIT_TYPE_MISMATCH,
                detail=(
                    f"cannot convert {source} ({source_factor.type_name}) to "
                    f"{target} ({target_factor.type_name}): the unit types differ"
                ),
            )
    return convert_units(
        value, mode=WITHIN_TYPE, from_unit=source, to_unit=target, lookup=ctx.unit_lookup
    )


def _call_catalog(
    stage: PlannedStage,
    inputs: Mapping[str, Any],
    units: Mapping[str, Optional[str]],
    ctx: RunContext,
) -> StageResult:
    name = stage.function.name

    def get(key: str) -> Any:
        return _plain(inputs.get(key))

    if name == "copy_raw":
        return copy_raw(get("value"))
    if name == "apply_dilution":
        return apply_dilution(get("value"), get("dilution_factor"))
    if name == "subtract":
        return subtract(get("minuend"), get("subtrahend"))
    if name == "replicate_mean_cv":
        return replicate_mean_cv(_as_list(get("replicates")))
    if name == "spike_recovery":
        return spike_recovery(get("spiked"), get("unspiked"), get("nominal_spike"))
    if name == "limit_compare":
        return limit_compare(
            get("value"),
            comparison=get("comparison"),
            limit=get("limit"),
            low=get("low"),
            high=get("high"),
            absolute=_absolute(get("absolute")),
        )
    if name == "convert_units":
        return _convert(get("value"), get("amount"), "amount" in stage.bindings, units.get("value"), ctx)
    if name == "fit_4pl":
        replicate = _as_list(get("replicate"))
        concentration = _as_list(get("concentration"))
        if replicate is None and concentration is not None:
            replicate = [str(i + 1) for i in range(len(concentration))]
        points = _points(
            {
                "concentration": concentration,
                "response": _as_list(get("response")),
                "replicate": replicate,
            },
            ("concentration", "response", "replicate"),
        )
        return fit_4pl(points, ctx.r_client)
    if name == "inverse_4pl":
        curve = {parameter: get(parameter) for parameter in FOUR_PL_PARAMETERS}
        return inverse_4pl(
            curve,
            get("response"),
            get("low_calibrator_mean_response"),
            get("high_calibrator_mean_response"),
            ctx.r_client,
        )
    if name == "fit_loglog_linear":
        x = _as_list(get("x"))
        point_id = _as_list(get("point_id"))
        if point_id is None and x is not None:
            point_id = [str(i + 1) for i in range(len(x))]
        replicates = get("replicates")
        columns: dict[str, Optional[list]] = {"x": x, "y": _as_list(get("y")), "point_id": point_id}
        if replicates is not None:
            columns["replicates"] = [_as_list(item) for item in _as_list(replicates) or []]
        return fit_loglog_linear(_points(columns, ("x", "y", "point_id")), ctx.r_client)
    if name == "inverse_loglog_linear":
        return inverse_loglog_linear(
            {"slope": get("slope"), "intercept": get("intercept")},
            get("y"),
            get("lowest_x_mean_y"),
            get("highest_x_mean_y"),
            ctx.r_client,
        )
    raise PlanRefused("catalog_function_unknown", f"Stage {stage.id}: {name} has no runner.", stage.id)


# ---- the run ------------------------------------------------------------------


class _Skip(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _stage_head(stage: PlannedStage) -> Dict[str, Any]:
    head: Dict[str, Any] = {"stage": stage.id, "kind": stage.kind}
    if stage.function is not None:
        head["function"] = stage.function.name
        head["function_version"] = stage.function.version
        if stage.function.route:
            head["route"] = stage.function.route
    else:
        head["formula_name"] = stage.formula_name
        head["formula_version"] = stage.formula_version
    return head


def _place_key(record: Mapping[str, Any]) -> tuple:
    place = record.get("place")
    numbered = isinstance(place, int) and not isinstance(place, bool)
    return (0 if numbered else 1, place if numbered else 0, record["index"])


def run_plan(plan: Plan, ctx: RunContext) -> RunOutcome:
    """Run every stage in order. See the module docstring for how each ends."""
    records: Dict[str, Dict[str, Any]] = {}
    outputs: Dict[str, Dict[str, str]] = {}
    gated: Dict[str, str] = {}
    flags: List[Dict[str, Any]] = []
    outcome = RunOutcome(
        status=ATTEMPT_COMPLETED,
        run_summary=SUMMARY_PASS,
        summary_check=None,
        summary_code=None,
        calculated=None,
        reported=None,
    )

    def stop(stage: PlannedStage, record: Dict[str, Any], code: Optional[str], detail: Optional[str], excel: Optional[str] = None) -> None:
        record["status"] = STAGE_STOPPED
        record["stop"] = code
        record["formula_error"] = excel
        if detail:
            record["detail"] = detail
        outcome.status = ATTEMPT_STOPPED
        outcome.stop_code = code
        outcome.formula_error = excel
        outcome.stop_stage = stage.id
        outcome.stop_detail = detail

    for stage in plan.stages:
        record = _stage_head(stage)
        records[stage.id] = record
        outcome.stages.append(record)
        if stage.function is not None:
            entry = {"stage": stage.id, "function": stage.function.name, "version": stage.function.version}
            if stage.function.route:
                entry["route"] = stage.function.route
            outcome.function_versions.append(entry)
        else:
            outcome.formula_versions.append(
                {
                    "stage": stage.id,
                    "kind": stage.kind,
                    "name": stage.formula_name,
                    "version": stage.formula_version,
                }
            )
        if outcome.stopped:
            record["status"] = STAGE_NOT_REACHED
            continue

        declaration = _on_fail(stage)
        if declaration is None:
            stop(stage, record, ON_FAIL_UNDECLARED, "The stage has no usable on-fail declaration.")
            continue
        if stage.id in gated:
            record["status"] = STAGE_GATED
            record["gated_by"] = gated[stage.id]
            continue

        inputs: Dict[str, Any] = {}
        units: Dict[str, Optional[str]] = {}
        try:
            for input_name, binding in stage.bindings.items():
                kind = binding.get("kind")
                if kind == BINDING_STAGE_OUTPUT:
                    source = records.get(str(binding.get("stage")))
                    if source is None or source["status"] not in (*_RAN, STAGE_QUALIFIED):
                        raise _Skip(f"stage {binding.get('stage')} did not run")
                    if source["status"] == STAGE_QUALIFIED:
                        raise _Skip(f"stage {binding.get('stage')} gave a qualified value with no number")
                    value = outputs.get(str(binding.get("stage")), {}).get(str(binding.get("output")))
                    read = InputRead(value)
                elif kind == BINDING_DIRECT:
                    read = InputRead(binding.get("value"))
                elif kind in (BINDING_RUN_FIELD, BINDING_REFERENCE):
                    read = ctx.reader.read(binding)
                    for source_row in read.sources:
                        outcome.inputs_read.append(
                            {"stage": stage.id, "input": input_name, **jsonable(dict(source_row))}
                        )
                else:
                    raise PlanRefused(
                        "configuration_unreadable",
                        f"Stage {stage.id}: binding {input_name} has an unknown kind.",
                        stage.id,
                    )
                inputs[input_name] = read.value
                unit = read.unit
                if unit is None and isinstance(binding.get("unit_id"), str):
                    unit = ctx.unit_names.get(binding["unit_id"])
                units[input_name] = unit
                outcome.values_used.append(
                    {"stage": stage.id, "input": input_name, "kind": kind, "value": jsonable(read.value)}
                )
                for item in _knocked_items(read.value):
                    outcome.knocked_out_points.append({"stage": stage.id, "input": input_name, "value": item})
        except _Skip as skip:
            record["status"] = STAGE_SKIPPED
            record["reason"] = skip.reason
            continue
        except ReadStop as read_stop:
            stop(stage, record, read_stop.code, read_stop.detail)
            continue

        failed = False
        no_verdict: Optional[str] = None
        if stage.formula is not None:
            result = run_formula(stage.formula, {name: _term(value) for name, value in inputs.items()})
            if result.stopped:
                stop(stage, record, None, result.detail or None, result.error)
                continue
            if isinstance(result.value, tuple):
                stop(stage, record, None, "a formula result is one value", "#VALUE!")
                continue
            record["outputs"] = {FORMULA_OUTPUT: format_value(result.value)}
            record["status"] = STAGE_OK
            outputs[stage.id] = dict(record["outputs"])
        else:
            try:
                result = _call_catalog(stage, inputs, units, ctx)
            except CatalogInputRefused as refused:
                record["status"] = STAGE_FAILED
                record["refused"] = {"code": refused.code, "detail": refused.detail}
                record["outputs"] = {}
                outputs[stage.id] = {}
                failed = True
                result = None
            if result is not None:
                record["r_called"] = result.r_called
                record["outputs"] = dict(result.outputs)
                outputs[stage.id] = dict(result.outputs)
                if result.flags:
                    record["flags"] = list(result.flags)
                if result.dropped:
                    record["dropped"] = list(result.dropped)
                if result.qualifier:
                    record["qualifier"] = result.qualifier
                    if result.end:
                        record["end"] = result.end
                    if result.qualifier_limit:
                        record["qualifier_limit"] = result.qualifier_limit
                if result.no_verdict:
                    record["no_verdict"] = result.no_verdict
                if result.stop is not None:
                    stop(stage, record, result.stop, result.detail)
                    continue
                no_verdict = result.no_verdict
                if result.outputs:
                    if result.outputs.get("verdict") == "fail":
                        failed = True
                        record["status"] = STAGE_FAILED
                    elif result.flags:
                        record["status"] = STAGE_FLAGGED
                    else:
                        record["status"] = STAGE_OK
                elif result.flags or no_verdict == MISSING_LIMIT:
                    failed = True
                    record["status"] = STAGE_FAILED
                elif result.qualifier and no_verdict is None:
                    record["status"] = STAGE_QUALIFIED
                elif no_verdict == UNSPECIFIED or no_verdict is not None:
                    record["status"] = STAGE_NO_VERDICT
                else:
                    failed = True
                    record["status"] = STAGE_FAILED

        if record["status"] == STAGE_FLAGGED:
            flags.append(
                {
                    "index": stage.index,
                    "stage": stage.id,
                    "place": None,
                    "outcome": None,
                    "flag": None,
                    "verdict": None,
                    "function_flags": list(record.get("flags", [])),
                }
            )
        if failed:
            applied_outcome = declaration.outcome
            if applied_outcome in STAGE_STOP_CODES or applied_outcome in FAILURE_STOPS.get(
                stage.function.name if stage.function is not None else "", ()
            ):
                applied_outcome = OUTCOME_FLAG
            flag = declaration.flag
            if no_verdict == MISSING_LIMIT:
                flag = declaration.missing_limit_flag or flag
            applied = {
                "outcome": applied_outcome,
                "flag": flag,
                "verdict": declaration.verdict,
                "place": declaration.place,
                "gates": list(declaration.gates),
            }
            record["applied"] = applied
            flags.append(
                {
                    "index": stage.index,
                    "stage": stage.id,
                    "place": declaration.place,
                    "outcome": applied_outcome,
                    "flag": flag,
                    "verdict": declaration.verdict,
                    "function_flags": list(record.get("flags", [])),
                }
            )
            for gate in declaration.gates:
                gated.setdefault(gate, stage.id)

    ordered = sorted(flags, key=_place_key)
    outcome.flags = [{key: value for key, value in item.items() if key != "index"} for item in ordered]

    if outcome.stopped:
        outcome.run_summary = SUMMARY_STOPPED
        outcome.summary_check = outcome.stop_stage
        outcome.summary_code = outcome.stop_code or outcome.formula_error
        outcome.calculated = None
        outcome.reported = None
        return outcome

    run_failed = [item for item in ordered if item["outcome"] == OUTCOME_RUN_FAILED]
    if run_failed:
        outcome.run_summary = SUMMARY_FAIL
        outcome.summary_check = run_failed[0]["stage"]
        outcome.summary_code = OUTCOME_RUN_FAILED

    pointer = records.get(plan.result_stage)
    produced = outputs.get(plan.result_stage, {})
    if pointer is not None and pointer["status"] in _RAN and plan.result_output in produced:
        if (
            pointer.get("function") == "copy_raw"
            and "calculated" in produced
            and "reported" in produced
        ):
            outcome.calculated = produced["calculated"]
            outcome.reported = produced["reported"]
        else:
            outcome.calculated = produced[plan.result_output]
            outcome.reported = produced[plan.result_output]
    elif pointer is not None and pointer["status"] == STAGE_QUALIFIED:
        outcome.result_note = {
            "code": "result_qualified",
            "qualifier": pointer.get("qualifier"),
            "end": pointer.get("end"),
            "message": "The value is past a cutoff. Writing a qualified value with its limit is slice S11.",
        }
    else:
        outcome.result_note = {
            "code": "result_not_produced",
            "stage": plan.result_stage,
            "status": pointer["status"] if pointer is not None else None,
            "message": "The stage the result pointer names produced no value.",
        }
    return outcome
