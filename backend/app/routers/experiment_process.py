"""
Experiment Process API — /api/v1/experiment-runs/{run_id}/processes
                         /api/v1/processes/{process_id}
                         /api/v1/process-steps/{step_id}

Routes:
    POST   /experiment-runs/{run_id}/processes          — create process (with optional steps)
    GET    /experiment-runs/{run_id}/processes          — list processes for a run
    GET    /processes/{process_id}                      — get process detail
    DELETE /processes/{process_id}                      — delete process

    POST   /processes/{process_id}/steps                — add a step to a process
    GET    /processes/{process_id}/steps                — list steps for a process
    GET    /process-steps/{step_id}                     — get step detail
    POST   /process-steps/{step_id}/start               — queued → in_process
    POST   /process-steps/{step_id}/complete            — in_process → complete
    POST   /process-steps/{step_id}/fail                — any → failed
    PATCH  /process-steps/{step_id}/notes               — update notes (any status)
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.experiment_process_service import ExperimentProcessService
from app.schemas.experiment_process import (
    ExperimentProcessCreate,
    ExperimentProcessRead,
    ProcessStepCreate,
    ProcessStepRead,
    ProcessStepUpdateNotes,
)
from models.experiment_process import ProcessStepStatus
from models.user import User

router = APIRouter(tags=["experiment-processes"])


def _service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> ExperimentProcessService:
    return ExperimentProcessService(db, current_user=current_user)


# ---------- Processes ----------

@router.post(
    "/experiment-runs/{run_id}/processes",
    response_model=ExperimentProcessRead,
    status_code=status.HTTP_201_CREATED,
)
def create_process(
    run_id: UUID,
    data: ExperimentProcessCreate,
    service: ExperimentProcessService = Depends(_service),
):
    """Create a named process (with optional initial steps) within an experiment run."""
    process = service.create_process(run_id, data)
    return ExperimentProcessRead.model_validate(process)


@router.get(
    "/experiment-runs/{run_id}/processes",
    response_model=List[ExperimentProcessRead],
)
def list_processes(
    run_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    """List all processes for an experiment run, ordered by sort_order."""
    processes, _ = service.list_processes(run_id)
    return [ExperimentProcessRead.model_validate(p) for p in processes]


@router.get("/processes/{process_id}", response_model=ExperimentProcessRead)
def get_process(
    process_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    process = service.get_process(process_id)
    return ExperimentProcessRead.model_validate(process)


@router.delete("/processes/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process(
    process_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    service.delete_process(process_id)


# ---------- Steps ----------

@router.post(
    "/processes/{process_id}/steps",
    response_model=ProcessStepRead,
    status_code=status.HTTP_201_CREATED,
)
def create_step(
    process_id: UUID,
    data: ProcessStepCreate,
    service: ExperimentProcessService = Depends(_service),
):
    """Add a step to an existing process."""
    step = service.create_step(
        process_id=process_id,
        name=data.name,
        sort_order=data.sort_order,
        description=data.description,
    )
    return ProcessStepRead.model_validate(step)


@router.get("/processes/{process_id}/steps", response_model=List[ProcessStepRead])
def list_steps(
    process_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    steps = service.list_steps(process_id)
    return [ProcessStepRead.model_validate(s) for s in steps]


@router.get("/process-steps/{step_id}", response_model=ProcessStepRead)
def get_step(
    step_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    step = service.get_step(step_id)
    return ProcessStepRead.model_validate(step)


# ---------- Step state transitions ----------

@router.post("/process-steps/{step_id}/start", response_model=ProcessStepRead)
def start_step(
    step_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    """queued → in_process"""
    step = service.transition_step(step_id, ProcessStepStatus.in_process)
    return ProcessStepRead.model_validate(step)


@router.post("/process-steps/{step_id}/complete", response_model=ProcessStepRead)
def complete_step(
    step_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    """in_process → complete"""
    step = service.transition_step(step_id, ProcessStepStatus.complete)
    return ProcessStepRead.model_validate(step)


@router.post("/process-steps/{step_id}/fail", response_model=ProcessStepRead)
def fail_step(
    step_id: UUID,
    service: ExperimentProcessService = Depends(_service),
):
    """queued | in_process → failed"""
    step = service.transition_step(step_id, ProcessStepStatus.failed)
    return ProcessStepRead.model_validate(step)


# ---------- Notes ----------

@router.patch("/process-steps/{step_id}/notes", response_model=ProcessStepRead)
def update_step_notes(
    step_id: UUID,
    data: ProcessStepUpdateNotes,
    service: ExperimentProcessService = Depends(_service),
):
    """Update free-text notes on a step (allowed at any status)."""
    step = service.update_step_notes(step_id, data.notes)
    return ProcessStepRead.model_validate(step)
