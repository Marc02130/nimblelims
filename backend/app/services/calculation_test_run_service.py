"""Run test cases and dry runs through the stage runner (calculations S9).

S8 stores test cases and reads the latest outcome per case and lock hash, and
the latest dry run, into the activation review. S9 runs them: the same stage
runner as a LIMS-run calculation, on the configuration version the analyte has
now (draft or active), with the case's inputs in place of a row.

Inputs are an object. Each key is a field name a ``run_field`` binding names;
its value is a decimal string, ``null`` (missing), a list of those, or
``{"value": ..., "knocked_out": true}``. Two keys are reserved:

* ``references``: analyte id to ``{"calculated": ..., "reported": ...}``, or
  ``{"stopped": true}`` for a reference whose calculation stopped. An analyte
  not named here is ``reference_missing``.
* ``units``: field name to the unit name of that value. A field with no unit
  is in the pairing unit.

Expected is an object with any of ``calculated``, ``reported``, ``status``,
``stop_code``, ``formula_error``, ``run_summary``, ``summary_check``, and
``flags`` (a list of flag names), plus ``tolerance``: an absolute decimal
allowed between the calculated or reported value and the expected one. A case
whose expected names no such key, or a key that is not one of them, is not run
and records nothing.

Each run is gated on ``/health`` first (CALC-REQ-4, 4a); a refusal is HTTP 400
and records nothing. The outcome is recorded with the lock hash and built
image digest it ran on. Nothing here writes a result-entry row or ``results``.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import release_transaction
from app.services.calculation_activation import _refuse_floats
from app.services.calculation_attempt_service import (
    REFERENCE_MISSING,
    REFERENCE_STOPPED,
    check_bindings,
    gate,
    load_plan,
    pairing_unit_name,
    refuse_call,
    refuse_plan,
    unit_lookup_for,
    unit_names_for,
)
from app.services.calculation_config import BINDING_RUN_FIELD
from app.services.calculation_config_service import _collect_unit_ids, get_rule, refuse
from app.services.calculation_review import list_case_rows
from app.services.calculation_runner import (
    InputRead,
    Knocked,
    Plan,
    PlanRefused,
    ReadStop,
    RunContext,
    RunOutcome,
    run_plan,
)
from app.services.calculation_runtime import CalculationCallRefused
from app.services.jcs import CanonicalizationError, canonical_json
from models.analysis import AnalysisAnalyte
from models.calculation import CalculationDryRun, CalculationTestCaseResult
from models.user import User

RESERVED_KEYS = ("references", "units")
EXPECTED_KEYS = (
    "calculated",
    "reported",
    "status",
    "stop_code",
    "formula_error",
    "run_summary",
    "summary_check",
    "flags",
)
TOLERANCE_KEY = "tolerance"
MAX_DRY_RUN_JSON = 20000

NOT_RUN_EXPECTED = "expected_unreadable"
NOT_RUN_INPUTS = "inputs_unreadable"


class _InputsUnreadable(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _value(raw: Any, where: str) -> Any:
    if raw is None or isinstance(raw, str):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool):
        return str(raw)
    if isinstance(raw, list):
        return [_value(item, where) for item in raw]
    if isinstance(raw, dict) and set(raw) <= {"value", "knocked_out"} and raw.get("knocked_out") is True:
        return Knocked(_value(raw.get("value"), where))
    raise _InputsUnreadable(
        f"{where} is not a decimal string, null, a list, or a knocked-out value"
    )


class CaseReader:
    """Reads run fields and references from a test case's or dry run's inputs."""

    def __init__(self, inputs: Mapping[str, Any]) -> None:
        if not isinstance(inputs, Mapping):
            raise _InputsUnreadable("inputs must be an object")
        references = inputs.get("references") or {}
        units = inputs.get("units") or {}
        if not isinstance(references, Mapping) or not all(isinstance(v, Mapping) for v in references.values()):
            raise _InputsUnreadable("references must map analyte ids to objects")
        if not isinstance(units, Mapping) or not all(isinstance(v, str) for v in units.values()):
            raise _InputsUnreadable("units must map field names to unit names")
        self._fields = {
            name: _value(raw, f"input {name!r}")
            for name, raw in inputs.items()
            if name not in RESERVED_KEYS
        }
        self._references = {str(key): value for key, value in references.items()}
        self._units = dict(units)

    def unit_names(self) -> List[str]:
        return list(self._units.values())

    def read(self, binding: Mapping[str, Any]) -> InputRead:
        if binding.get("kind") == BINDING_RUN_FIELD:
            name = str(binding.get("field_name"))
            value = self._fields.get(name)
            return InputRead(
                value,
                unit=self._units.get(name),
                sources=(
                    {
                        "kind": BINDING_RUN_FIELD,
                        "entry_type": binding.get("entry_type"),
                        "field": name,
                        "value": _plain_json(value),
                    },
                ),
            )
        analyte_id = str(binding.get("analyte_id"))
        column = str(binding.get("value"))
        entry = self._references.get(analyte_id)
        if entry is None:
            raise ReadStop(REFERENCE_MISSING, f"the inputs name no value for analyte {analyte_id}")
        if entry.get("stopped") is True:
            raise ReadStop(REFERENCE_STOPPED, f"the calculation of analyte {analyte_id} stopped")
        value = _value(entry.get(column), f"reference {analyte_id} {column}")
        source = {"kind": "reference", "analyte_id": analyte_id, "field": f"{column}_result", "value": _plain_json(value)}
        if value is None:
            raise ReadStop(REFERENCE_MISSING, f"the inputs give analyte {analyte_id} no {column} value")
        return InputRead(value, sources=(source,))


def _plain_json(value: Any) -> Any:
    if isinstance(value, Knocked):
        return {"knocked_out": True, "value": _plain_json(value.value)}
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    return value


# ---- comparing ----------------------------------------------------------------


def _decimal(value: Any) -> Optional[Decimal]:
    if not isinstance(value, str):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def read_expected(expected: Any) -> Optional[Tuple[Dict[str, Any], Optional[Decimal]]]:
    """The checks a case asks for, or None when the expected object is not readable."""
    if not isinstance(expected, Mapping):
        return None
    unknown = set(expected) - set(EXPECTED_KEYS) - {TOLERANCE_KEY}
    checks = {key: expected[key] for key in EXPECTED_KEYS if key in expected}
    if unknown or not checks:
        return None
    tolerance: Optional[Decimal] = None
    if TOLERANCE_KEY in expected:
        tolerance = _decimal(expected[TOLERANCE_KEY])
        if tolerance is None or tolerance < 0:
            return None
    if "flags" in checks and (
        not isinstance(checks["flags"], list) or not all(isinstance(f, str) for f in checks["flags"])
    ):
        return None
    for key in ("calculated", "reported"):
        if key in checks and checks[key] is not None and not isinstance(checks[key], str):
            return None
    return checks, tolerance


def flag_names(outcome: RunOutcome) -> List[str]:
    names: List[str] = []
    for record in outcome.flags:
        if record.get("flag"):
            names.append(record["flag"])
        names.extend(record.get("function_flags") or [])
    return sorted(set(names))


def _same_value(expected: Any, actual: Optional[str], tolerance: Optional[Decimal]) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    left, right = _decimal(expected), _decimal(actual)
    if left is None or right is None:
        return expected == actual
    if tolerance is not None:
        return abs(left - right) <= tolerance
    return left == right


def compare(outcome: RunOutcome, checks: Mapping[str, Any], tolerance: Optional[Decimal]) -> List[Dict[str, Any]]:
    actual: Dict[str, Any] = {
        "calculated": outcome.calculated,
        "reported": outcome.reported,
        "status": outcome.status,
        "stop_code": outcome.stop_code,
        "formula_error": outcome.formula_error,
        "run_summary": outcome.run_summary,
        "summary_check": outcome.summary_check,
        "flags": flag_names(outcome),
    }
    results: List[Dict[str, Any]] = []
    for key, expected in checks.items():
        if key in ("calculated", "reported"):
            passed = _same_value(expected, actual[key], tolerance)
        elif key == "flags":
            passed = sorted(set(expected)) == actual["flags"]
        else:
            passed = expected == actual[key]
        results.append({"check": key, "expected": expected, "actual": actual[key], "passed": passed})
    return results


# ---- running ------------------------------------------------------------------


def _prepare(db: Session, analysis_id: UUID, analyte_id: UUID) -> Tuple[AnalysisAnalyte, Plan, Optional[str], Dict[str, str]]:
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None or rule.calculation_config_version is None:
        raise refuse("configuration_missing", "This analyte has no calculation configuration.")
    plan = load_plan(db, rule)
    pairing = pairing_unit_name(db, rule)
    unit_names = unit_names_for(db, _collect_unit_ids(rule.calculation_config))
    return rule, plan, pairing, unit_names


def _live_refusal(plan: Plan, pairing: Optional[str]) -> Optional[Dict[str, Any]]:
    """What a LIMS-run calculation would refuse for this configuration, if anything."""
    try:
        check_bindings(plan, None, pairing)
    except HTTPException as exc:
        return dict(exc.detail) if isinstance(exc.detail, Mapping) else {"message": str(exc.detail)}
    return None


def _run(plan: Plan, reader: CaseReader, r_client: Any, lookup: Mapping[str, Any], pairing: Optional[str], unit_names: Mapping[str, str]) -> RunOutcome:
    ctx = RunContext(
        reader=reader,
        r_client=r_client,
        unit_lookup=lambda name: lookup.get(name),
        pairing_unit=pairing,
        unit_names=unit_names,
    )
    try:
        return run_plan(plan, ctx)
    except CalculationCallRefused as exc:
        raise refuse_call(exc) from exc
    except PlanRefused as exc:
        raise refuse_plan(exc) from exc


def _check_unchanged(db: Session, analysis_id: UUID, analyte_id: UUID, version: int, config: Any) -> None:
    db.expire_all()
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config_version != version or rule.calculation_config != config:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "configuration_changed",
                "message": "The configuration changed while it ran. Nothing was recorded. Run it again.",
            },
        )


def run_test_cases(
    db: Session, user: User, analysis_id: UUID, analyte_id: UUID, r_client: Any
) -> Dict[str, Any]:
    """Run every test case of the current configuration version and record each outcome."""
    rule, plan, pairing, unit_names = _prepare(db, analysis_id, analyte_id)
    version = int(rule.calculation_config_version)
    config = rule.calculation_config
    cases = list_case_rows(db, analysis_id, analyte_id, version)
    readers: Dict[UUID, Any] = {}
    unit_pool: List[Optional[str]] = [pairing, *unit_names.values()]
    for case in cases:
        try:
            reader = CaseReader(case.inputs)
        except _InputsUnreadable as exc:
            readers[case.id] = exc
            continue
        readers[case.id] = reader
        unit_pool.extend(reader.unit_names())
    lookup = unit_lookup_for(db, unit_pool)
    case_facts = [(case.id, case.name, case.expected) for case in cases]
    live_refusal = _live_refusal(plan, pairing)
    release_transaction(db, keep_loaded=True)

    lock_hash, digest = gate(r_client)
    report: List[Dict[str, Any]] = []
    to_record: List[Tuple[UUID, bool, Dict[str, Any]]] = []
    for case_id, name, expected in case_facts:
        entry: Dict[str, Any] = {"test_case_id": case_id, "name": name}
        reader = readers[case_id]
        if isinstance(reader, _InputsUnreadable):
            entry.update({"state": "not_run", "reason": NOT_RUN_INPUTS, "detail": reader.detail})
            report.append(entry)
            continue
        read = read_expected(expected)
        if read is None:
            entry.update(
                {
                    "state": "not_run",
                    "reason": NOT_RUN_EXPECTED,
                    "detail": "expected names none of " + ", ".join(EXPECTED_KEYS)
                    + ", or a key that is not one of them, or an unreadable tolerance.",
                }
            )
            report.append(entry)
            continue
        checks, tolerance = read
        outcome = _run(plan, reader, r_client, lookup, pairing, unit_names)
        compared = compare(outcome, checks, tolerance)
        passed = all(item["passed"] for item in compared)
        recorded = {"checks": compared, "run": outcome.to_json()}
        to_record.append((case_id, passed, recorded))
        entry.update({"state": "passed" if passed else "failed", "checks": compared, "outcome": outcome.to_json()})
        report.append(entry)

    _check_unchanged(db, analysis_id, analyte_id, version, config)
    for case_id, passed, recorded in to_record:
        db.add(
            CalculationTestCaseResult(
                test_case_id=case_id,
                lock_hash=lock_hash,
                passed=passed,
                outcome=recorded,
                built_image_digest=digest,
                created_by=user.id,
            )
        )
    db.flush()
    db.commit()
    return {
        "analysis_id": analysis_id,
        "analyte_id": analyte_id,
        "configuration_version": version,
        "lock_hash": lock_hash,
        "built_image_digest": digest,
        "total": len(case_facts),
        "run": len(to_record),
        "passed": sum(1 for _case, passed, _rec in to_record if passed),
        "live_refusal": live_refusal,
        "cases": report,
    }


def _dry_run_input(body: Any) -> Dict[str, Any]:
    if not isinstance(body, dict) or set(body) != {"input"}:
        raise refuse("dry_run_invalid", "The request body is {\"input\": {...}} and nothing else.")
    value = body["input"]
    if not isinstance(value, dict):
        raise refuse("dry_run_invalid", "input must be an object.")
    try:
        _refuse_floats(value, "input")
    except HTTPException as exc:
        raise refuse("dry_run_invalid", "input holds a JSON number with a fraction. Write values as decimal strings.") from exc
    try:
        size = len(canonical_json(value))
    except CanonicalizationError as exc:
        raise refuse("dry_run_invalid", f"input cannot be stored: {exc}") from exc
    if size > MAX_DRY_RUN_JSON:
        raise refuse("dry_run_invalid", f"input is larger than {MAX_DRY_RUN_JSON} characters.")
    return value


def dry_run(
    db: Session, user: User, analysis_id: UUID, analyte_id: UUID, body: Any, r_client: Any
) -> Dict[str, Any]:
    """Run the current configuration version on the given input and record it."""
    value = _dry_run_input(body)
    rule, plan, pairing, unit_names = _prepare(db, analysis_id, analyte_id)
    version = int(rule.calculation_config_version)
    config = rule.calculation_config
    try:
        reader = CaseReader(value)
    except _InputsUnreadable as exc:
        raise refuse("dry_run_invalid", exc.detail) from exc
    lookup = unit_lookup_for(db, [pairing, *unit_names.values(), *reader.unit_names()])
    live_refusal = _live_refusal(plan, pairing)
    release_transaction(db, keep_loaded=True)

    lock_hash, digest = gate(r_client)
    outcome = _run(plan, reader, r_client, lookup, pairing, unit_names)

    _check_unchanged(db, analysis_id, analyte_id, version, config)
    row = CalculationDryRun(
        analysis_id=analysis_id,
        analyte_id=analyte_id,
        configuration_version=version,
        input=value,
        outcome=outcome.to_json(),
        lock_hash=lock_hash,
        built_image_digest=digest,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "analysis_id": analysis_id,
        "analyte_id": analyte_id,
        "configuration_version": version,
        "input": row.input,
        "outcome": row.outcome,
        "lock_hash": lock_hash,
        "built_image_digest": digest,
        "live_refusal": live_refusal,
        "run_at": row.run_at,
        "created_by": row.created_by,
    }
