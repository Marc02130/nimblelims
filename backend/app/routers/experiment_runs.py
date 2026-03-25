"""
Experiment Runs API — /api/v1/experiment-runs

Routes:
    GET    /experiment-runs                  — list runs
    POST   /experiment-runs                  — create run (draft)
    GET    /experiment-runs/{id}             — get run detail
    PATCH  /experiment-runs/{id}/start       — draft → running
    PATCH  /experiment-runs/{id}/review      — running → complete ("Ready for Review")
    PATCH  /experiment-runs/{id}/complete    — complete → published (requires experiment:publish)
    POST   /experiment-runs/{id}/import      — import instrument data CSV (running only)
    GET    /experiment-runs/{id}/data        — list imported data rows
    GET    /experiment-runs/{id}/worklist    — download robot worklist CSV
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.core.rbac import require_experiment_manage
from app.services.experiment_run_service import ExperimentRunService
from app.schemas.flexible_experiment import (
    ExperimentRunCreate,
    ExperimentRunRead,
    ExperimentRunListResponse,
    ImportDataRequest,
    ImportDataResponse,
    ExperimentDataRead,
    ExperimentDataListResponse,
)
from models.flexible_experiment import ExperimentRunStatus
from models.user import User

router = APIRouter(prefix="/experiment-runs", tags=["experiment-runs"])


def _run_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> ExperimentRunService:
    return ExperimentRunService(db, current_user=current_user)


@router.get("", response_model=ExperimentRunListResponse)
def list_runs(
    template_id: Optional[UUID] = Query(None),
    run_status: Optional[ExperimentRunStatus] = Query(None, alias="status"),
    mine: bool = Query(False, description="Filter to runs created by current user"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    service: ExperimentRunService = Depends(_run_service),
):
    items, total = service.list_runs(
        template_id=template_id,
        status=run_status,
        mine=mine,
        page=page,
        size=size,
    )
    pages = (total + size - 1) // size if size else 0
    return ExperimentRunListResponse(
        runs=[ExperimentRunRead.model_validate(r) for r in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=ExperimentRunRead, status_code=201)
def create_run(
    data: ExperimentRunCreate,
    service: ExperimentRunService = Depends(_run_service),
):
    run = service.create_run(data)
    return ExperimentRunRead.model_validate(run)


@router.get("/{run_id}", response_model=ExperimentRunRead)
def get_run(
    run_id: UUID,
    service: ExperimentRunService = Depends(_run_service),
):
    run = service.get_run(run_id)
    return ExperimentRunRead.model_validate(run)


@router.patch("/{run_id}/start", response_model=ExperimentRunRead)
def start_run(
    run_id: UUID,
    service: ExperimentRunService = Depends(_run_service),
):
    """Transition: draft → running (sets started_at)."""
    run = service.start_run(run_id)
    return ExperimentRunRead.model_validate(run)


@router.patch("/{run_id}/review", response_model=ExperimentRunRead)
def submit_for_review(
    run_id: UUID,
    service: ExperimentRunService = Depends(_run_service),
):
    """Transition: running → complete (UI label: 'Ready for Review')."""
    run = service.move_to_review(run_id)
    return ExperimentRunRead.model_validate(run)


@router.patch("/{run_id}/complete", response_model=ExperimentRunRead)
def publish_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    publisher: User = Depends(require_permission("experiment:publish")),
):
    """Transition: complete → published (requires experiment:publish permission)."""
    service = ExperimentRunService(db, current_user=publisher)
    run = service.publish_run(run_id)
    return ExperimentRunRead.model_validate(run)


@router.post("/{run_id}/import", response_model=ImportDataResponse)
def import_data(
    run_id: UUID,
    data: ImportDataRequest,
    service: ExperimentRunService = Depends(_run_service),
):
    """Import instrument data rows into a running experiment."""
    return service.import_data(run_id, data.rows)


@router.get("/{run_id}/data", response_model=ExperimentDataListResponse)
def get_data_rows(
    run_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    service: ExperimentRunService = Depends(_run_service),
):
    """List imported data rows for a run (paginated)."""
    rows, total = service.get_data_rows(run_id, page=page, size=size)
    pages = (total + size - 1) // size if size else 0
    return ExperimentDataListResponse(
        rows=[ExperimentDataRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{run_id}/worklist")
def export_worklist(
    run_id: UUID,
    service: ExperimentRunService = Depends(_run_service),
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
