"""Calculate one result-entry row and record the attempt (calculations S9).

CALC-REQ-30 (provenance), 49 (the calculation write), 4a (timeouts recorded),
25 (stops clear the row), 21 (run summary), 58 (a metadata analyte is read as
an analyte). OQ-CALC-25 Spec default: provenance lives on the attempt row and
the result-entry row links to it.

Three steps, so no transaction is open while R runs:

1. Read the row, its run, the active configuration, the units, the saved
   formulas, and the referenced rows on the same Test. Any refusal here is
   HTTP 400 and writes nothing. Then the transaction is released.
2. Read ``/health`` and accept or refuse the call (CALC-REQ-4, 4a). A refusal
   is HTTP 400 and writes nothing. Once accepted, the stage runner runs. An R
   refusal that is not a timeout is also HTTP 400 and writes nothing; a
   timeout is a stage stop.
3. Lock the row, check that nothing read in step 1 changed (HTTP 409 when it
   did), insert the attempt, and write calculated, reported, and the link on
   the calculation path. A stop writes both values empty.

S9 reads the row's own raw value (``run_field`` on the experiment sample data
entry, field ``raw_result``, no match field) and a reference to another
analyte's row on the same Test. Any other run field is refused with
``binding_not_readable``. Nothing here writes ``results``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import release_transaction
from app.services.calculation_catalog_decimal import UnitFactor, load_unit_factor
from app.services.calculation_config import (
    BINDING_REFERENCE,
    BINDING_RUN_FIELD,
    STATE_ACTIVE,
)
from app.services.calculation_config_service import (
    _collect_saved_formulas,
    _collect_unit_ids,
    _load_saved_formulas,
)
from app.services.calculation_runner import (
    InputRead,
    Knocked,
    Plan,
    PlanRefused,
    ReadStop,
    RunContext,
    RunOutcome,
    prepare_plan,
    run_plan,
)
from app.services.calculation_runtime import CalculationCallRefused, begin_calculation_call
from app.services.r_calculator_client import RCalculatorClient
from app.services.result_entry_service import (
    RESULTS_ENTRY_TYPE,
    ResultEntryService,
    calculation_write,
    refuse,
)
from models.analysis import Analysis, AnalysisAnalyte
from models.calculation import CalculationAttempt
from models.entry import ResultEntry
from models.flexible_experiment import LimsRun, LimsRunStatus
from models.unit import Unit
from models.user import User

RAW_FIELD = "raw_result"
REFERENCE_MISSING = "reference_missing"
REFERENCE_AMBIGUOUS = "reference_ambiguous"
REFERENCE_STOPPED = "reference_stopped"


def calculation_r_client() -> RCalculatorClient:
    """The R client the calculation routes use. Tests override this dependency."""
    return RCalculatorClient()


def gate(r_client: Any) -> Tuple[str, str]:
    """Accept or refuse the call. Returns the lock hash and built image digest."""
    try:
        health = r_client.fetch_health_body()
        lock = begin_calculation_call(health)
    except CalculationCallRefused as exc:
        raise refuse_call(exc) from exc
    return lock.lock_hash, str(health["R_IMAGE_DIGEST"])


def refuse_call(exc: CalculationCallRefused) -> HTTPException:
    return refuse(exc.code, f"The calculation call is refused: {exc.detail}")


def refuse_plan(exc: PlanRefused) -> HTTPException:
    detail: Dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.stage is not None:
        detail["stage"] = exc.stage
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def unit_lookup_for(db: Session, names: Sequence[Optional[str]]) -> Dict[str, Optional[UnitFactor]]:
    """Load every unit the run can name, before the transaction is released."""
    return {name: load_unit_factor(db, name) for name in {n for n in names if n}}


def unit_names_for(db: Session, unit_ids: Sequence[str]) -> Dict[str, str]:
    ids: List[UUID] = []
    for raw in unit_ids:
        try:
            ids.append(UUID(str(raw)))
        except ValueError:
            continue
    if not ids:
        return {}
    rows = db.execute(select(Unit.id, Unit.name).where(Unit.id.in_(ids))).all()
    return {str(unit_id): name for unit_id, name in rows}


def load_plan(db: Session, rule: AnalysisAnalyte) -> Plan:
    config = rule.calculation_config
    saved = _load_saved_formulas(db, _collect_saved_formulas(config))
    try:
        return prepare_plan(config, saved)
    except PlanRefused as exc:
        raise refuse_plan(exc) from exc


def pairing_unit_name(db: Session, rule: AnalysisAnalyte) -> Optional[str]:
    if rule.pairing_unit_id is None:
        return None
    return db.execute(select(Unit.name).where(Unit.id == rule.pairing_unit_id)).scalar_one_or_none()


# ---- the reads ------------------------------------------------------------------


@dataclass(frozen=True)
class _ReferenceRow:
    id: UUID
    replicate: int
    calculated: Optional[str]
    reported: Optional[str]
    knocked_out: bool
    attempt_id: Optional[UUID]
    attempt_stopped: bool


@dataclass(frozen=True)
class _Snapshot:
    """Everything step 1 read. Step 3 compares a fresh copy to it."""

    raw_result: Optional[str]
    raw_units: Optional[str]
    knocked_out: bool
    attempt_id: Optional[UUID]
    config_version: Optional[int]
    config_state: Optional[str]
    analysis_version: int
    references: Tuple[Tuple[str, Tuple[_ReferenceRow, ...]], ...]


def _reference_ids(plan: Plan) -> List[str]:
    return sorted(
        {
            str(binding.get("analyte_id"))
            for _stage, _name, binding in plan.bindings()
            if binding.get("kind") == BINDING_REFERENCE
        }
    )


def _read_references(db: Session, row: ResultEntry, analyte_ids: Sequence[str]) -> Dict[str, Tuple[_ReferenceRow, ...]]:
    found: Dict[str, Tuple[_ReferenceRow, ...]] = {}
    for analyte_id in analyte_ids:
        rows = db.execute(
            select(ResultEntry, CalculationAttempt.status)
            .outerjoin(CalculationAttempt, CalculationAttempt.id == ResultEntry.calculation_attempt_id)
            .where(ResultEntry.test_id == row.test_id, ResultEntry.analyte_id == UUID(analyte_id))
            .order_by(ResultEntry.replicate)
        ).all()
        found[analyte_id] = tuple(
            _ReferenceRow(
                id=entry.id,
                replicate=entry.replicate,
                calculated=entry.calculated_result,
                reported=entry.reported_result,
                knocked_out=bool(entry.knocked_out),
                attempt_id=entry.calculation_attempt_id,
                attempt_stopped=attempt_status == "stopped",
            )
            for entry, attempt_status in rows
        )
    return found


def _snapshot(db: Session, row: ResultEntry, rule: AnalysisAnalyte, plan_refs: Sequence[str]) -> _Snapshot:
    version = db.execute(select(Analysis.version).where(Analysis.id == rule.analysis_id)).scalar_one()
    references = _read_references(db, row, plan_refs)
    return _Snapshot(
        raw_result=row.raw_result,
        raw_units=row.raw_units,
        knocked_out=bool(row.knocked_out),
        attempt_id=row.calculation_attempt_id,
        config_version=rule.calculation_config_version,
        config_state=rule.calculation_config_state,
        analysis_version=int(version),
        references=tuple(sorted(references.items())),
    )


class RowReader:
    """Reads the row's own raw value and same-Test references from a snapshot."""

    def __init__(self, row: ResultEntry, snapshot: _Snapshot) -> None:
        self._row_id = row.id
        self._entry_id = row.entry_id
        self._test_id = row.test_id
        self._snapshot = snapshot
        self._references = dict(snapshot.references)

    def read(self, binding: Mapping[str, Any]) -> InputRead:
        if binding.get("kind") == BINDING_RUN_FIELD:
            value = self._snapshot.raw_result
            return InputRead(
                value,
                unit=self._snapshot.raw_units,
                sources=(
                    {
                        "kind": BINDING_RUN_FIELD,
                        "entry_id": str(self._entry_id),
                        "record_id": str(self._row_id),
                        "field": RAW_FIELD,
                        "value": value,
                        "units": self._snapshot.raw_units,
                    },
                ),
            )
        analyte_id = str(binding.get("analyte_id"))
        column = str(binding.get("value"))
        rows = self._references.get(analyte_id, ())
        if not rows:
            raise ReadStop(REFERENCE_MISSING, f"analyte {analyte_id} has no row on this Test")
        if len(rows) > 1:
            raise ReadStop(
                REFERENCE_AMBIGUOUS,
                f"analyte {analyte_id} has {len(rows)} replicate rows on this Test; "
                "which one a reference reads is not decided (OQ-CALC-40)",
            )
        ref = rows[0]
        value = ref.calculated if column == "calculated" else ref.reported
        source = {
            "kind": BINDING_REFERENCE,
            "analyte_id": analyte_id,
            "test_id": str(self._test_id),
            "record_id": str(ref.id),
            "replicate": ref.replicate,
            "field": f"{column}_result",
            "value": value,
            "attempt_id": None if ref.attempt_id is None else str(ref.attempt_id),
            "knocked_out": ref.knocked_out,
        }
        if ref.knocked_out:
            return InputRead(Knocked(value), sources=(source,))
        if ref.attempt_stopped:
            raise ReadStop(REFERENCE_STOPPED, f"the calculation of analyte {analyte_id} on this Test stopped")
        if value is None:
            raise ReadStop(REFERENCE_MISSING, f"analyte {analyte_id} has no {column} value on this Test")
        return InputRead(value, sources=(source,))


def check_bindings(plan: Plan, raw_units: Optional[str], pairing_unit: Optional[str]) -> None:
    """Refuse what S9 cannot read, before any call is accepted."""
    for stage, input_name, binding in plan.bindings():
        if binding.get("kind") != BINDING_RUN_FIELD:
            continue
        if (
            binding.get("entry_type") != RESULTS_ENTRY_TYPE
            or binding.get("field_name") != RAW_FIELD
            or binding.get("match_field") is not None
        ):
            raise refuse_plan(
                PlanRefused(
                    "binding_not_readable",
                    f"Stage {stage.id}: input {input_name} reads field {binding.get('field_name')!r} of the "
                    f"{binding.get('entry_type')} entry. A LIMS-run calculation reads the row's own "
                    f"{RAW_FIELD} here; other run fields are read in a later slice.",
                    stage.id,
                )
            )
        converts = stage.function is not None and stage.function.name == "convert_units" and input_name == "value"
        if raw_units is not None and not converts and raw_units != pairing_unit:
            raise refuse_plan(
                PlanRefused(
                    "raw_units_differ",
                    f"Stage {stage.id}: the raw units {raw_units!r} are not the pairing unit "
                    f"{pairing_unit!r}, and this stage does not convert. What a calculation does "
                    "when the file units differ from the pairing unit is open (OQ-CALC-39).",
                    stage.id,
                )
            )


# ---- the attempt --------------------------------------------------------------


def attempt_response(row: CalculationAttempt) -> Dict[str, Any]:
    return {
        "id": row.id,
        "result_entry_id": row.result_entry_id,
        "test_id": row.test_id,
        "analyte_id": row.analyte_id,
        "lims_run_id": row.lims_run_id,
        "analysis_id": row.analysis_id,
        "status": row.status,
        "stop_code": row.stop_code,
        "stop_stage": row.stop_stage,
        "stop_detail": row.stop_detail,
        "formula_error": row.formula_error,
        "run_summary": row.run_summary,
        "summary_check": row.summary_check,
        "summary_code": row.summary_code,
        "lock_hash": row.lock_hash,
        "built_image_digest": row.built_image_digest,
        "configuration_name": row.configuration_name,
        "configuration_version": row.configuration_version,
        "analysis_version": row.analysis_version,
        "function_versions": row.function_versions,
        "formula_versions": row.formula_versions,
        "inputs_read": row.inputs_read,
        "values_used": row.values_used,
        "knocked_out_points": row.knocked_out_points,
        "flags": row.flags,
        "stages": row.stages,
        "calculated_result": row.calculated_result,
        "reported_result": row.reported_result,
        "result_note": row.result_note,
        "created_at": row.created_at,
        "created_by": row.created_by,
    }


def _active_rule(db: Session, analysis_id: UUID, analyte_id: UUID) -> AnalysisAnalyte:
    rule = db.execute(
        select(AnalysisAnalyte).where(
            AnalysisAnalyte.analysis_id == analysis_id,
            AnalysisAnalyte.analyte_id == analyte_id,
        )
    ).scalar_one_or_none()
    if rule is None or rule.calculation_config is None or rule.calculation_config_state != STATE_ACTIVE:
        raise refuse(
            "configuration_not_active",
            "This analyte has no active calculation configuration on the run's analysis. "
            "An Admin activates a configuration before it runs.",
        )
    return rule


def _check_row(db: Session, service: ResultEntryService, row: ResultEntry) -> LimsRun:
    run = db.get(LimsRun, row.test.lims_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LIMS run not found")
    if run.status == LimsRunStatus.published:
        raise refuse("run_published", "This LIMS run is published. Its rows are not calculated again.")
    if run.analysis_id is None:
        raise refuse("run_has_no_analysis", "This LIMS run has no analysis, so it has no calculation.")
    if row.knocked_out:
        raise refuse(
            "row_knocked_out",
            "This row is knocked out. A knocked-out row has no calculated or reported value.",
        )
    if row.calculation_attempt_id is not None:
        raise refuse(
            "already_calculated",
            "This row already has a calculation attempt. Recalculation is a later slice.",
        )
    return run


def calculate_row(
    db: Session, user: User, run_id: UUID, row_id: UUID, r_client: Any
) -> Tuple[CalculationAttempt, ResultEntry]:
    """Run the active configuration on one row. See the module docstring."""
    service = ResultEntryService(db, user.id)
    row = service.get_row(run_id, row_id)
    run = _check_row(db, service, row)
    rule = _active_rule(db, run.analysis_id, row.analyte_id)
    plan = load_plan(db, rule)
    pairing = pairing_unit_name(db, rule)
    check_bindings(plan, row.raw_units, pairing)
    refs = _reference_ids(plan)
    snapshot = _snapshot(db, row, rule, refs)
    unit_ids = _collect_unit_ids(rule.calculation_config)
    unit_names = unit_names_for(db, unit_ids)
    lookup = unit_lookup_for(db, [pairing, row.raw_units, *unit_names.values()])
    configuration_name = rule.calculation_config_name or plan.name
    configuration_version = int(rule.calculation_config_version or 0)
    ids = {
        "row": row.id,
        "test": row.test_id,
        "analyte": row.analyte_id,
        "run": run.id,
        "analysis": run.analysis_id,
    }
    release_transaction(db, keep_loaded=True)

    lock_hash, digest = gate(r_client)
    ctx = RunContext(
        reader=RowReader(row, snapshot),
        r_client=r_client,
        unit_lookup=lambda name: lookup.get(name),
        pairing_unit=pairing,
        unit_names=unit_names,
    )
    try:
        outcome = run_plan(plan, ctx)
    except CalculationCallRefused as exc:
        raise refuse_call(exc) from exc
    except PlanRefused as exc:
        raise refuse_plan(exc) from exc

    locked = db.execute(
        select(ResultEntry).where(ResultEntry.id == ids["row"]).with_for_update()
    ).scalar_one()
    db.refresh(locked)
    fresh_rule = db.execute(
        select(AnalysisAnalyte).where(
            AnalysisAnalyte.analysis_id == ids["analysis"],
            AnalysisAnalyte.analyte_id == ids["analyte"],
        )
    ).scalar_one()
    db.refresh(fresh_rule)
    if _snapshot(db, locked, fresh_rule, refs) != snapshot:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "calculation_inputs_changed",
                "message": "The row, its configuration, or a value it reads changed while it was calculated. "
                "Nothing was written. Calculate again.",
            },
        )
    service._refuse_if_published(locked)

    attempt = CalculationAttempt(
        id=uuid4(),
        result_entry_id=ids["row"],
        test_id=ids["test"],
        analyte_id=ids["analyte"],
        lims_run_id=ids["run"],
        analysis_id=ids["analysis"],
        lock_hash=lock_hash,
        built_image_digest=digest,
        configuration_name=configuration_name,
        configuration_version=configuration_version,
        analysis_version=snapshot.analysis_version,
        created_by=user.id,
        **attempt_columns(outcome),
    )
    db.add(attempt)
    db.flush()
    with calculation_write(db):
        locked.calculated_result = outcome.calculated
        locked.reported_result = outcome.reported
        locked.calculation_attempt_id = attempt.id
        locked.modified_by = user.id
    db.commit()
    db.refresh(attempt)
    db.refresh(locked)
    return attempt, locked


def attempt_columns(outcome: RunOutcome) -> Dict[str, Any]:
    return {
        "status": outcome.status,
        "stop_code": outcome.stop_code,
        "stop_stage": outcome.stop_stage,
        "stop_detail": outcome.stop_detail,
        "formula_error": outcome.formula_error,
        "run_summary": outcome.run_summary,
        "summary_check": outcome.summary_check,
        "summary_code": outcome.summary_code,
        "function_versions": outcome.function_versions,
        "formula_versions": outcome.formula_versions,
        "inputs_read": outcome.inputs_read,
        "values_used": outcome.values_used,
        "knocked_out_points": outcome.knocked_out_points,
        "flags": outcome.flags,
        "stages": outcome.stages,
        "calculated_result": outcome.calculated,
        "reported_result": outcome.reported,
        "result_note": outcome.result_note,
    }


def list_attempts(db: Session, run_id: UUID, row_id: UUID, user: User) -> List[CalculationAttempt]:
    row = ResultEntryService(db, user.id).get_row(run_id, row_id)
    return list(
        db.execute(
            select(CalculationAttempt)
            .where(CalculationAttempt.result_entry_id == row.id)
            .order_by(CalculationAttempt.created_at, CalculationAttempt.id)
        ).scalars()
    )
