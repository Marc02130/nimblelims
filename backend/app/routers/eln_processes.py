"""
ELN Processes API — /api/v1/eln-processes

Phase 1: process CRUD, ordered steps (template refs), sample assignment + advance.

Distinct from LIMS routes under /v1/processes (LIMS run sub-processes).
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.eln_process_service import ELNProcessService
from app.schemas.eln_process import (
    ELNProcessCreate,
    ELNProcessUpdate,
    ELNProcessRead,
    ELNProcessListEntry,
    ELNProcessListResponse,
    ELNProcessStepCreate,
    ELNProcessStepUpdate,
    ELNProcessStepRead,
    ELNProcessStepReorderRequest,
    ELNProcessStepInstantiateRequest,
    ELNProcessStepStartResponse,
    ELNProcessSampleAssignRequest,
    ELNProcessSampleRead,
    ELNProcessSampleSetStepRequest,
    ELNProcessSampleAdvanceResponse,
    SampleJourneyResponse,
)
from models.user import User
from models.sample import Sample
from fastapi import HTTPException

router = APIRouter(
    prefix="/eln-processes",
    tags=["eln-processes"],
)


def get_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> ELNProcessService:
    return ELNProcessService(db, current_user=current_user)


# ---------- Process CRUD ----------


@router.get("", response_model=ELNProcessListResponse)
def list_eln_processes(
    active: Optional[bool] = Query(True, description="Filter by active (default true)"),
    mine: bool = Query(False, description="Only processes created by current user"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=500),
    service: ELNProcessService = Depends(get_service),
):
    items, total = service.list_processes(active=active, mine=mine, page=page, size=size)
    pages = (total + size - 1) // size if size else 0
    entries = []
    for p in items:
        entries.append(
            ELNProcessListEntry(
                id=p.id,
                name=p.name,
                description=p.description,
                active=p.active,
                status_id=p.status_id,
                process_definition_id=p.process_definition_id,
                created_at=p.created_at,
                created_by=p.created_by,
                step_count=service.repo.count_steps(p.id),
                sample_count=service.repo.count_samples(p.id),
            )
        )
    return ELNProcessListResponse(
        processes=entries,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=ELNProcessRead, status_code=status.HTTP_201_CREATED)
def create_eln_process(
    data: ELNProcessCreate,
    service: ELNProcessService = Depends(get_service),
):
    p = service.create_process(data)
    return ELNProcessRead.model_validate(p)


@router.get("/{process_id}", response_model=ELNProcessRead)
def get_eln_process(
    process_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    p = service.get_process(process_id)
    return ELNProcessRead.model_validate(p)


@router.patch("/{process_id}", response_model=ELNProcessRead)
def update_eln_process(
    process_id: UUID,
    data: ELNProcessUpdate,
    service: ELNProcessService = Depends(get_service),
):
    p = service.update_process(process_id, data)
    return ELNProcessRead.model_validate(p)


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_eln_process(
    process_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    service.delete_process(process_id)
    return None


# ---------- Steps ----------


@router.get("/{process_id}/steps", response_model=List[ELNProcessStepRead])
def list_steps(
    process_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    return [ELNProcessStepRead.model_validate(s) for s in service.list_steps(process_id)]


@router.post(
    "/{process_id}/steps",
    response_model=ELNProcessStepRead,
    status_code=status.HTTP_201_CREATED,
)
def add_step(
    process_id: UUID,
    data: ELNProcessStepCreate,
    service: ELNProcessService = Depends(get_service),
):
    step = service.add_step(process_id, data)
    return ELNProcessStepRead.model_validate(step)


@router.patch("/{process_id}/steps/{step_id}", response_model=ELNProcessStepRead)
def update_step(
    process_id: UUID,
    step_id: UUID,
    data: ELNProcessStepUpdate,
    service: ELNProcessService = Depends(get_service),
):
    step = service.update_step(process_id, step_id, data)
    return ELNProcessStepRead.model_validate(step)


@router.delete("/{process_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_step(
    process_id: UUID,
    step_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    service.remove_step(process_id, step_id)
    return None


@router.post("/{process_id}/steps/reorder", response_model=List[ELNProcessStepRead])
def reorder_steps(
    process_id: UUID,
    data: ELNProcessStepReorderRequest,
    service: ELNProcessService = Depends(get_service),
):
    steps = service.reorder_steps(process_id, data.step_ids)
    return [ELNProcessStepRead.model_validate(s) for s in steps]


@router.post(
    "/{process_id}/steps/{step_id}/instantiate",
    response_model=ELNProcessStepStartResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{process_id}/steps/{step_id}/start",
    response_model=ELNProcessStepStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_step(
    process_id: UUID,
    step_id: UUID,
    data: ELNProcessStepInstantiateRequest = ELNProcessStepInstantiateRequest(),
    service: ELNProcessService = Depends(get_service),
):
    """Start step: create Experiment or lazy LimsRun (typed steps, Decision #1)."""
    return service.instantiate_step(process_id, step_id, data)


# ---------- Samples ----------


@router.get("/{process_id}/samples", response_model=List[ELNProcessSampleRead])
def list_samples(
    process_id: UUID,
    current_step_id: Optional[UUID] = Query(
        None,
        description="Filter samples currently at this process step",
    ),
    sample_status: Optional[str] = Query(
        None,
        description="Filter by assignment status (assigned|in_progress|completed|removed)",
    ),
    service: ELNProcessService = Depends(get_service),
):
    return [
        ELNProcessSampleRead.model_validate(s)
        for s in service.list_samples(
            process_id,
            current_step_id=current_step_id,
            sample_status=sample_status,
        )
    ]


@router.post(
    "/{process_id}/samples",
    response_model=List[ELNProcessSampleRead],
    status_code=status.HTTP_201_CREATED,
)
def assign_samples(
    process_id: UUID,
    data: ELNProcessSampleAssignRequest,
    service: ELNProcessService = Depends(get_service),
):
    samples = service.assign_samples(process_id, data)
    return [ELNProcessSampleRead.model_validate(s) for s in samples]


@router.delete(
    "/{process_id}/samples/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_sample(
    process_id: UUID,
    sample_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    service.remove_sample(process_id, sample_id)
    return None


@router.patch(
    "/{process_id}/samples/{sample_id}/step",
    response_model=ELNProcessSampleRead,
)
def set_sample_step(
    process_id: UUID,
    sample_id: UUID,
    data: ELNProcessSampleSetStepRequest,
    service: ELNProcessService = Depends(get_service),
):
    ps = service.set_sample_step(process_id, sample_id, data)
    return ELNProcessSampleRead.model_validate(ps)


@router.post(
    "/{process_id}/samples/{sample_id}/advance",
    response_model=ELNProcessSampleAdvanceResponse,
)
def advance_sample(
    process_id: UUID,
    sample_id: UUID,
    force: bool = Query(False, description="Reserved for future hard gate"),
    service: ELNProcessService = Depends(get_service),
):
    """Advance sample; soft warning if lims_run step incomplete."""
    return service.advance_sample(process_id, sample_id, force=force)


# Journey is registered on a separate router (sample-scoped, Decision #7)
