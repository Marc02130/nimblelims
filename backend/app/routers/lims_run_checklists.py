"""
Experiment Process API — /api/v1/lims-runs/{run_id}/checklists
                         /api/v1/lims-run-checklists/{checklist_id}
                         /api/v1/lims-run-checklist-steps/{step_id}

Routes:
    POST   /lims-runs/{run_id}/checklists          — create process (with optional steps)
    GET    /lims-runs/{run_id}/checklists          — list processes for a run
    GET    /lims-run-checklists/{checklist_id}                      — get process detail
    DELETE /lims-run-checklists/{checklist_id}                      — delete process

    POST   /lims-run-checklists/{checklist_id}/steps                — add a step to a process
    GET    /lims-run-checklists/{checklist_id}/steps                — list steps for a process
    GET    /lims-run-checklist-steps/{step_id}                     — get step detail
    POST   /lims-run-checklist-steps/{step_id}/start               — queued → in_process
    POST   /lims-run-checklist-steps/{step_id}/complete            — in_process → complete
    POST   /lims-run-checklist-steps/{step_id}/fail                — any → failed
    PATCH  /lims-run-checklist-steps/{step_id}/notes               — update notes (any status)
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.lims_run_checklist_service import LimsRunChecklistService
from app.schemas.lims_run_checklist import (
    LimsRunChecklistCreate,
    LimsRunChecklistRead,
    LimsRunChecklistStepCreate,
    LimsRunChecklistStepRead,
    LimsRunChecklistStepUpdateNotes,
)
from models.lims_run_checklist import LimsRunChecklistStepStatus
from models.user import User

router = APIRouter(tags=["lims-run-checklists"])


def _service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> LimsRunChecklistService:
    return LimsRunChecklistService(db, current_user=current_user)


# ---------- Processes ----------

@router.post(
    "/lims-runs/{run_id}/checklists",
    response_model=LimsRunChecklistRead,
    status_code=status.HTTP_201_CREATED,
)
def create_checklist(
    run_id: UUID,
    data: LimsRunChecklistCreate,
    service: LimsRunChecklistService = Depends(_service),
):
    """Create a named process (with optional initial steps) within an LIMS run."""
    process = service.create_checklist(run_id, data)
    return LimsRunChecklistRead.model_validate(process)


@router.get(
    "/lims-runs/{run_id}/checklists",
    response_model=List[LimsRunChecklistRead],
)
def list_checklists(
    run_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    """List all processes for an LIMS run, ordered by sort_order."""
    processes, _ = service.list_checklists(run_id)
    return [LimsRunChecklistRead.model_validate(p) for p in processes]


@router.get("/lims-run-checklists/{checklist_id}", response_model=LimsRunChecklistRead)
def get_checklist(
    checklist_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    process = service.get_checklist(checklist_id)
    return LimsRunChecklistRead.model_validate(process)


@router.delete("/lims-run-checklists/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checklist(
    checklist_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    service.delete_checklist(checklist_id)


# ---------- Steps ----------

@router.post(
    "/lims-run-checklists/{checklist_id}/steps",
    response_model=LimsRunChecklistStepRead,
    status_code=status.HTTP_201_CREATED,
)
def create_step(
    checklist_id: UUID,
    data: LimsRunChecklistStepCreate,
    service: LimsRunChecklistService = Depends(_service),
):
    """Add a step to an existing process."""
    step = service.create_step(
        checklist_id=checklist_id,
        name=data.name,
        sort_order=data.sort_order,
        description=data.description,
    )
    return LimsRunChecklistStepRead.model_validate(step)


@router.get("/lims-run-checklists/{checklist_id}/steps", response_model=List[LimsRunChecklistStepRead])
def list_steps(
    checklist_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    steps = service.list_steps(checklist_id)
    return [LimsRunChecklistStepRead.model_validate(s) for s in steps]


@router.get("/lims-run-checklist-steps/{step_id}", response_model=LimsRunChecklistStepRead)
def get_step(
    step_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    step = service.get_step(step_id)
    return LimsRunChecklistStepRead.model_validate(step)


# ---------- Step state transitions ----------

@router.post("/lims-run-checklist-steps/{step_id}/start", response_model=LimsRunChecklistStepRead)
def start_step(
    step_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    """queued → in_process"""
    step = service.transition_step(step_id, LimsRunChecklistStepStatus.in_process)
    return LimsRunChecklistStepRead.model_validate(step)


@router.post("/lims-run-checklist-steps/{step_id}/complete", response_model=LimsRunChecklistStepRead)
def complete_step(
    step_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    """in_process → complete"""
    step = service.transition_step(step_id, LimsRunChecklistStepStatus.complete)
    return LimsRunChecklistStepRead.model_validate(step)


@router.post("/lims-run-checklist-steps/{step_id}/fail", response_model=LimsRunChecklistStepRead)
def fail_step(
    step_id: UUID,
    service: LimsRunChecklistService = Depends(_service),
):
    """queued | in_process → failed"""
    step = service.transition_step(step_id, LimsRunChecklistStepStatus.failed)
    return LimsRunChecklistStepRead.model_validate(step)


# ---------- Notes ----------

@router.patch("/lims-run-checklist-steps/{step_id}/notes", response_model=LimsRunChecklistStepRead)
def update_step_notes(
    step_id: UUID,
    data: LimsRunChecklistStepUpdateNotes,
    service: LimsRunChecklistService = Depends(_service),
):
    """Update free-text notes on a step (allowed at any status)."""
    step = service.update_step_notes(step_id, data.notes)
    return LimsRunChecklistStepRead.model_validate(step)
