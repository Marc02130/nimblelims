"""
LIMS Runs API — /api/v1/lims-runs

Routes:
    GET    /lims-runs                          — list runs
    POST   /lims-runs                          — create run (draft)
    GET    /lims-runs/{id}                     — get run detail
    PATCH  /lims-runs/{id}/order               — draft → ordered         (CRO only)
    PATCH  /lims-runs/{id}/start               — draft → running (standard) | ordered → running (CRO)
    PATCH  /lims-runs/{id}/results-received    — running → results_received (CRO only)
    PATCH  /lims-runs/{id}/review              — running|results_received → complete
    PATCH  /lims-runs/{id}/complete            — complete → published (requires experiment:publish)
    PATCH  /lims-runs/{id}/cancel              — non-terminal → canceled, only before any import row
    POST   /lims-runs/{id}/fail                — non-terminal → failed, reason required
    POST   /lims-runs/{id}/reject              — same as /fail (kept for existing clients)
    POST   /lims-runs/{id}/import              — import instrument data (running or results_received)
    GET    /lims-runs/{id}/data                — list imported data rows
    GET    /lims-runs/{id}/worklist            — download robot worklist CSV
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, object_session

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.core.rbac import require_experiment_manage
from app.services.lims_run_service import LimsRunService
from app.schemas.flexible_experiment import (
    AcceptValueRequest,
    LimsRunCreate,
    LimsRunUpdate,
    LimsRunStartRequest,
    LimsRunSubstituteInstrumentTypeRequest,
    LimsRunRead,
    LimsRunListResponse,
    ImportDataRequest,
    ImportDataResponse,
    LimsRunDataRead,
    LimsRunDataListResponse,
    FailRunRequest,
    RerunCreateRequest,
    ValueChoiceRead,
)
from app.services.result_acceptance_service import ResultAcceptanceService
from app.services.run_failure import has_imported_data, runs_with_imported_data
from models.flexible_experiment import LimsRunStatus, LimsRun
from models.user import User

router = APIRouter(prefix="/lims-runs", tags=["lims-runs"])


def _run_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> LimsRunService:
    return LimsRunService(db, current_user=current_user)


_TERMINAL_STATUSES = {
    LimsRunStatus.published,
    LimsRunStatus.failed,
    LimsRunStatus.canceled,
}


def _can_substitute(run: LimsRun, user: Optional[User]) -> bool:
    if run.status in _TERMINAL_STATUSES:
        return False
    if user is None:
        return False
    role = getattr(getattr(user, "role", None), "name", None)
    if role in ("Administrator", "Lab Manager"):
        return True
    return run.created_by == user.id  # lims_runs.created_by (the run)


def _run_read(
    run: LimsRun,
    has_data: Optional[bool] = None,
    user: Optional[User] = None,
) -> LimsRunRead:
    data = LimsRunRead.model_validate(run)
    # Attach lifecycle_type from template for UI buttons
    lt = None
    if run.experiment_template is not None:
        lt = getattr(run.experiment_template, "lifecycle_type", None) or "standard"
    if has_data is None:
        session = object_session(run)
        has_data = has_imported_data(session, run.id) if session is not None else False
    type_name = None
    if getattr(run, "instrument_type", None) is not None:
        type_name = run.instrument_type.name
    return data.model_copy(
        update={
            "lifecycle_type": lt,
            "has_imported_data": has_data,
            "instrument_type_name": type_name,
            "can_substitute_instrument_type": _can_substitute(run, user),
        }
    )


@router.get("", response_model=LimsRunListResponse)
def list_runs(
    template_id: Optional[UUID] = Query(None),
    run_status: Optional[LimsRunStatus] = Query(None, alias="status"),
    mine: bool = Query(False, description="Filter to runs created by current user"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    service: LimsRunService = Depends(_run_service),
):
    items, total = service.list_runs(
        template_id=template_id,
        status=run_status,
        mine=mine,
        page=page,
        size=size,
    )
    pages = (total + size - 1) // size if size else 0
    with_data = runs_with_imported_data(service.db, [r.id for r in items])
    return LimsRunListResponse(
        runs=[
            _run_read(r, has_data=r.id in with_data, user=service.current_user)
            for r in items
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=LimsRunRead, status_code=201)
def create_run(
    data: LimsRunCreate,
    service: LimsRunService = Depends(_run_service),
):
    run = service.create_run(data)
    return _run_read(run, user=service.current_user)


@router.get("/{run_id}", response_model=LimsRunRead)
def get_run(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    run = service.get_run(run_id)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}", response_model=LimsRunRead)
def update_run(
    run_id: UUID,
    data: LimsRunUpdate,
    service: LimsRunService = Depends(_run_service),
):
    """Update run fields (e.g. analysis_id for promote-on-publish opt-in)."""
    run = service.update_run(run_id, data)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}/order", response_model=LimsRunRead)
def order_run(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: draft → ordered. CRO lifecycle only — sends experiment to external lab."""
    run = service.order_run(run_id)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}/start", response_model=LimsRunRead)
def start_run(
    run_id: UUID,
    body: LimsRunStartRequest = LimsRunStartRequest(),
    service: LimsRunService = Depends(_run_service),
):
    """
    Transition: draft → running (standard) or ordered → running (CRO).
    Requires analysis_id and a sample cohort (body.sample_ids or previously set).
    Cohort is locked at start — no mid-flight sample changes.
    """
    run = service.start_run(
        run_id,
        sample_ids=body.sample_ids,
        instrument_type_id=body.instrument_type_id,
    )
    return _run_read(run, user=service.current_user)


@router.post("/{run_id}/substitute-instrument-type", response_model=LimsRunRead)
def substitute_instrument_type(
    run_id: UUID,
    body: LimsRunSubstituteInstrumentTypeRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Substitute the run's instrument type snapshot. Does not change the template."""
    run = service.substitute_instrument_type(
        run_id,
        instrument_type_id=body.instrument_type_id,
        reason=body.reason,
    )
    return _run_read(run, user=service.current_user)


@router.put("/{run_id}/cohort", response_model=LimsRunRead)
def set_run_cohort(
    run_id: UUID,
    body: LimsRunStartRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Set draft cohort without starting (sample_ids required)."""
    if not body.sample_ids:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="sample_ids required",
        )
    run = service.set_cohort(run_id, body.sample_ids, lock=False)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}/results-received", response_model=LimsRunRead)
def mark_results_received(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: running → results_received. CRO lifecycle only — instrument data returned by CRO."""
    run = service.mark_results_received(run_id)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}/review", response_model=LimsRunRead)
def submit_for_review(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: running → complete (standard) or results_received → complete (CRO)."""
    run = service.move_to_review(run_id)
    return _run_read(run, user=service.current_user)


@router.patch("/{run_id}/complete", response_model=LimsRunRead)
def publish_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    publisher: User = Depends(require_permission("experiment:publish")),
):
    """
    Transition: complete → published (requires experiment:publish).

    When analysis_id is set, promotes instrument data to tests/results in the same
    transaction. Conflicts with other runs return 409.
    """
    service = LimsRunService(db, current_user=publisher)
    run = service.publish_run(run_id)
    return _run_read(run, user=service.current_user)


@router.get("/{run_id}/promotion/preview")
def promotion_preview(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """
    Preview what would happen on publish for structured promote
    (creates/updates/conflicts/unresolved columns). Does not write.
    """
    return service.promotion_preview(run_id)


@router.patch("/{run_id}/cancel", response_model=LimsRunRead)
def cancel_run(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Non-terminal → canceled, only while the run has no imported data.

    A run with imported data has already run: 422 ``run_has_imported_data``.
    Fail it instead.
    """
    run = service.cancel_run(run_id)
    return _run_read(run, user=service.current_user)


@router.post("/{run_id}/fail", response_model=LimsRunRead)
def fail_run(
    run_id: UUID,
    body: FailRunRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Fail the run. Status becomes failed, the reason is kept, rows stay.

    SOP §13: when the plate fails, every sample on it is rerun. Nothing is deleted.
    """
    run = service.fail_run(run_id, body.reason)
    return _run_read(run, user=service.current_user)


@router.post("/{run_id}/reject", response_model=LimsRunRead)
def reject_run(
    run_id: UUID,
    body: FailRunRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Same as POST /fail. Kept so existing clients keep working."""
    run = service.fail_run(run_id, body.reason)
    return _run_read(run, user=service.current_user)


@router.post("/{run_id}/rerun", response_model=LimsRunRead, status_code=201)
def create_rerun(
    run_id: UUID,
    body: Optional[RerunCreateRequest] = None,
    service: LimsRunService = Depends(_run_service),
):
    """Create a draft run that replaces this one and copies its cohort."""
    run = service.create_rerun(run_id, body.name if body else None)
    return _run_read(run, user=service.current_user)


@router.get("/{run_id}/value-choices", response_model=List[ValueChoiceRead])
def list_value_choices(
    run_id: UUID,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_permission("experiment:publish")),
):
    """Values from this rerun and the run it replaces. Nothing is removed.

    Same permission as accepting a value: experiment:publish.
    """
    return ResultAcceptanceService(db, current_user=reviewer).list_for_run(run_id)


@router.post("/{run_id}/value-choices", response_model=ValueChoiceRead)
def accept_value(
    run_id: UUID,
    body: AcceptValueRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_permission("experiment:publish")),
):
    """Record which value is accepted. The other value stays on its run.

    Same permission as listing choices: experiment:publish.
    """
    return ResultAcceptanceService(db, current_user=reviewer).accept(run_id, body)


@router.post("/{run_id}/import", response_model=ImportDataResponse)
def import_data(
    run_id: UUID,
    data: ImportDataRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Import pre-parsed rows (prefer multipart /import-file for CSV + parser)."""
    return service.import_data(
        run_id,
        data.rows,
        instrument_id=data.instrument_id,
        cro_source_id=data.cro_source_id,
        parser_id=data.parser_id,
    )


@router.post("/{run_id}/import-file")
def import_file(
    run_id: UUID,
    file: UploadFile = File(...),
    instrument_id: Optional[UUID] = Form(None),
    cro_source_id: Optional[UUID] = Form(None),
    parser_id: Optional[UUID] = Form(None),
    service: LimsRunService = Depends(_run_service),
):
    """
    Multipart import: file + instrument_id XOR cro_source_id + optional parser_id.
    Uses active data parser for run.analysis_id + source.
    """
    from app.core.uploads import read_upload_capped

    content = read_upload_capped(file, field_name=file.filename or "import-file")
    return service.import_file(
        run_id,
        content,
        instrument_id=instrument_id,
        cro_source_id=cro_source_id,
        parser_id=parser_id,
        filename=file.filename,
    )


@router.get("/{run_id}/imports")
def list_imports(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Import history for a run (source + parser version per batch)."""
    return service.list_imports(run_id)


@router.get("/{run_id}/data", response_model=LimsRunDataListResponse)
def get_data_rows(
    run_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    service: LimsRunService = Depends(_run_service),
):
    """List imported data rows for a run (paginated)."""
    rows, total = service.get_data_rows(run_id, page=page, size=size)
    pages = (total + size - 1) // size if size else 0
    return LimsRunDataListResponse(
        rows=[LimsRunDataRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{run_id}/worklist")
def export_worklist(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Download robot worklist as generic CSV (source_well, dest_well, volume)."""
    csv_content = service.export_worklist_csv(run_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="worklist_{run_id}.csv"',
        },
    )
