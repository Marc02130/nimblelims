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
    PATCH  /lims-runs/{id}/cancel              — any non-terminal → canceled
    POST   /lims-runs/{id}/import              — import instrument data (running or results_received)
    GET    /lims-runs/{id}/data                — list imported data rows
    GET    /lims-runs/{id}/worklist            — download robot worklist CSV
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.core.rbac import require_experiment_manage
from app.services.lims_run_service import LimsRunService
from app.schemas.flexible_experiment import (
    LimsRunCreate,
    LimsRunUpdate,
    LimsRunStartRequest,
    LimsRunRead,
    LimsRunListResponse,
    ImportDataRequest,
    ImportDataResponse,
    LimsRunDataRead,
    LimsRunDataListResponse,
)
from models.flexible_experiment import LimsRunStatus, LimsRun
from models.user import User

router = APIRouter(prefix="/lims-runs", tags=["lims-runs"])


def _run_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> LimsRunService:
    return LimsRunService(db, current_user=current_user)


def _run_read(run: LimsRun) -> LimsRunRead:
    data = LimsRunRead.model_validate(run)
    # Attach lifecycle_type from template for UI buttons
    lt = None
    if run.experiment_template is not None:
        lt = getattr(run.experiment_template, "lifecycle_type", None) or "standard"
    return data.model_copy(update={"lifecycle_type": lt})


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
    return LimsRunListResponse(
        runs=[_run_read(r) for r in items],
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
    return _run_read(run)


@router.get("/{run_id}", response_model=LimsRunRead)
def get_run(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    run = service.get_run(run_id)
    return _run_read(run)


@router.patch("/{run_id}", response_model=LimsRunRead)
def update_run(
    run_id: UUID,
    data: LimsRunUpdate,
    service: LimsRunService = Depends(_run_service),
):
    """Update run fields (e.g. analysis_id for promote-on-publish opt-in)."""
    run = service.update_run(run_id, data)
    return _run_read(run)


@router.patch("/{run_id}/order", response_model=LimsRunRead)
def order_run(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: draft → ordered. CRO lifecycle only — sends experiment to external lab."""
    run = service.order_run(run_id)
    return _run_read(run)


@router.patch("/{run_id}/start", response_model=LimsRunRead)
def start_run(
    run_id: UUID,
    body: LimsRunStartRequest = LimsRunStartRequest(),
    service: LimsRunService = Depends(_run_service),
):
    """
    Transition: draft → running (standard) or ordered → running (CRO).

    If the run has no analysis_id, pass acknowledge_no_analysis=true after the UI
    warns that Tests/Results will not be written on publish.
    """
    run = service.start_run(
        run_id,
        acknowledge_no_analysis=body.acknowledge_no_analysis,
    )
    return _run_read(run)


@router.patch("/{run_id}/results-received", response_model=LimsRunRead)
def mark_results_received(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: running → results_received. CRO lifecycle only — instrument data returned by CRO."""
    run = service.mark_results_received(run_id)
    return _run_read(run)


@router.patch("/{run_id}/review", response_model=LimsRunRead)
def submit_for_review(
    run_id: UUID,
    service: LimsRunService = Depends(_run_service),
):
    """Transition: running → complete (standard) or results_received → complete (CRO)."""
    run = service.move_to_review(run_id)
    return _run_read(run)


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
    return _run_read(run)


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
    """Transition: any non-terminal state → canceled."""
    run = service.cancel_run(run_id)
    return _run_read(run)


@router.post("/{run_id}/import", response_model=ImportDataResponse)
def import_data(
    run_id: UUID,
    data: ImportDataRequest,
    service: LimsRunService = Depends(_run_service),
):
    """Import instrument data rows into a running experiment."""
    return service.import_data(run_id, data.rows)


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
