"""
ExperimentProcessService — business logic for experiment_processes and process_steps.

State machine (ProcessStep):
    queued      → in_process  (started_at set)
    in_process  → complete    (completed_at set)
    any         → failed      (failed_at set, terminal)
    complete    → (terminal, no transitions)

VALID_STEP_TRANSITIONS from the model is the single source of truth for allowed moves.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.experiment_process_repository import (
    ExperimentProcessRepository,
    ProcessStepRepository,
)
from app.repositories.flexible_experiment_repository import ExperimentRunRepository
from app.schemas.experiment_process import ExperimentProcessCreate
from models.experiment_process import (
    ExperimentProcess,
    ProcessStep,
    ProcessStepStatus,
    VALID_STEP_TRANSITIONS,
)
from models.user import User


class ExperimentProcessService:
    """
    Business logic for ExperimentProcess and ProcessStep.

    Status transition enforcement: VALID_STEP_TRANSITIONS in model is authoritative.
    """

    def __init__(self, db: Session, current_user: Optional[User] = None) -> None:
        self.db = db
        self.current_user = current_user
        self.process_repo = ExperimentProcessRepository(db)
        self.step_repo = ProcessStepRepository(db)
        self.run_repo = ExperimentRunRepository(db)

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects) -> None:
        self.db.flush()
        for obj in objects:
            if obj is not None:
                self.db.refresh(obj)
        self.db.commit()

    # ---------- ExperimentProcess CRUD ----------

    def _get_run_or_404(self, run_id: uuid.UUID):
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment run not found",
            )
        return run

    def create_process(
        self, run_id: uuid.UUID, data: ExperimentProcessCreate
    ) -> ExperimentProcess:
        self._get_run_or_404(run_id)
        process = self.process_repo.create(
            run_id=run_id,
            name=data.name,
            description=data.description,
            sort_order=data.sort_order,
            created_by=self._user_id(),
        )
        self.db.flush()
        for step_data in data.steps:
            self.step_repo.create(
                process_id=process.id,
                name=step_data.name,
                description=step_data.description,
                sort_order=step_data.sort_order,
                created_by=self._user_id(),
            )
        self._commit_refresh(process)
        return process

    def get_process(self, process_id: uuid.UUID) -> ExperimentProcess:
        process = self.process_repo.get_by_id(process_id)
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment process not found",
            )
        return process

    def list_processes(
        self, run_id: uuid.UUID
    ) -> Tuple[List[ExperimentProcess], int]:
        self._get_run_or_404(run_id)
        processes = self.process_repo.list_for_run(run_id)
        return processes, len(processes)

    def delete_process(self, process_id: uuid.UUID) -> None:
        process = self.get_process(process_id)
        self.process_repo.delete(process)
        self.db.commit()

    # ---------- ProcessStep CRUD ----------

    def create_step(
        self,
        process_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
    ) -> ProcessStep:
        self.get_process(process_id)  # 404 guard
        step = self.step_repo.create(
            process_id=process_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=self._user_id(),
        )
        self._commit_refresh(step)
        return step

    def get_step(self, step_id: uuid.UUID) -> ProcessStep:
        step = self.step_repo.get_by_id(step_id)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        return step

    def list_steps(self, process_id: uuid.UUID) -> List[ProcessStep]:
        self.get_process(process_id)  # 404 guard
        return self.step_repo.list_for_process(process_id)

    # ---------- Step state machine ----------

    def transition_step(
        self, step_id: uuid.UUID, new_status: ProcessStepStatus
    ) -> ProcessStep:
        """
        Transition a step to a new status, enforcing VALID_STEP_TRANSITIONS.
        Raises 400 on invalid transition, 404 if step not found.
        """
        step = self.get_step(step_id)
        current = ProcessStepStatus(step.status)
        allowed = VALID_STEP_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot transition from '{current.value}' to '{new_status.value}'. "
                    f"Allowed transitions: {sorted(s.value for s in allowed) or 'none (terminal state)'}"
                ),
            )
        self.step_repo.update_status(step, new_status, self._user_id())
        self._commit_refresh(step)
        return step

    def update_step_notes(self, step_id: uuid.UUID, notes: str) -> ProcessStep:
        step = self.get_step(step_id)
        self.step_repo.update_notes(step, notes, self._user_id())
        self._commit_refresh(step)
        return step
