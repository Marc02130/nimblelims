"""
LimsRunChecklistService — business logic for lims_run_checklistes and lims_run_checklist_steps.

State machine (LimsRunChecklistStep):
    queued      → in_process  (started_at set)
    in_process  → complete    (completed_at set)
    any         → failed      (failed_at set, terminal)
    complete    → (terminal, no transitions)

VALID_CHECKLIST_STEP_TRANSITIONS from the model is the single source of truth for allowed moves.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.lims_run_checklist_repository import (
    LimsRunChecklistRepository,
    LimsRunChecklistStepRepository,
)
from app.repositories.flexible_experiment_repository import LimsRunRepository
from app.schemas.lims_run_checklist import LimsRunChecklistCreate
from models.lims_run_checklist import (
    LimsRunChecklist,
    LimsRunChecklistStep,
    LimsRunChecklistStepStatus,
    VALID_CHECKLIST_STEP_TRANSITIONS,
)
from models.user import User


class LimsRunChecklistService:
    """
    Business logic for LimsRunChecklist and LimsRunChecklistStep.

    Status transition enforcement: VALID_CHECKLIST_STEP_TRANSITIONS in model is authoritative.
    """

    def __init__(self, db: Session, current_user: Optional[User] = None) -> None:
        self.db = db
        self.current_user = current_user
        self.process_repo = LimsRunChecklistRepository(db)
        self.step_repo = LimsRunChecklistStepRepository(db)
        self.run_repo = LimsRunRepository(db)

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects) -> None:
        self.db.flush()
        for obj in objects:
            if obj is not None:
                self.db.refresh(obj)
        self.db.commit()

    # ---------- LimsRunChecklist CRUD ----------

    def _get_run_or_404(self, run_id: uuid.UUID):
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LIMS run not found",
            )
        return run

    def create_checklist(
        self, run_id: uuid.UUID, data: LimsRunChecklistCreate
    ) -> LimsRunChecklist:
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
                checklist_id=process.id,
                name=step_data.name,
                description=step_data.description,
                sort_order=step_data.sort_order,
                created_by=self._user_id(),
            )
        self._commit_refresh(process)
        return process

    def get_checklist(self, checklist_id: uuid.UUID) -> LimsRunChecklist:
        process = self.process_repo.get_by_id(checklist_id)
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment process not found",
            )
        return process

    def list_checklists(
        self, run_id: uuid.UUID
    ) -> Tuple[List[LimsRunChecklist], int]:
        self._get_run_or_404(run_id)
        processes = self.process_repo.list_for_run(run_id)
        return processes, len(processes)

    def delete_checklist(self, checklist_id: uuid.UUID) -> None:
        process = self.get_checklist(checklist_id)
        self.process_repo.delete(process)
        self.db.commit()

    # ---------- LimsRunChecklistStep CRUD ----------

    def create_step(
        self,
        checklist_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
    ) -> LimsRunChecklistStep:
        self.get_checklist(checklist_id)  # 404 guard
        step = self.step_repo.create(
            checklist_id=checklist_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=self._user_id(),
        )
        self._commit_refresh(step)
        return step

    def get_step(self, step_id: uuid.UUID) -> LimsRunChecklistStep:
        step = self.step_repo.get_by_id(step_id)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        return step

    def list_steps(self, checklist_id: uuid.UUID) -> List[LimsRunChecklistStep]:
        self.get_checklist(checklist_id)  # 404 guard
        return self.step_repo.list_for_process(checklist_id)

    # ---------- Step state machine ----------

    def transition_step(
        self, step_id: uuid.UUID, new_status: LimsRunChecklistStepStatus
    ) -> LimsRunChecklistStep:
        """
        Transition a step to a new status, enforcing VALID_CHECKLIST_STEP_TRANSITIONS.
        Raises 400 on invalid transition, 404 if step not found.
        """
        step = self.get_step(step_id)
        current = LimsRunChecklistStepStatus(step.status)
        allowed = VALID_CHECKLIST_STEP_TRANSITIONS.get(current, set())
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

    def update_step_notes(self, step_id: uuid.UUID, notes: str) -> LimsRunChecklistStep:
        step = self.get_step(step_id)
        self.step_repo.update_notes(step, notes, self._user_id())
        self._commit_refresh(step)
        return step
