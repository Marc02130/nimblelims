"""
Repositories for LimsRunChecklist and LimsRunChecklistStep.

Pure DB access — no HTTP exceptions, no business logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, selectinload

from models.lims_run_checklist import LimsRunChecklist, LimsRunChecklistStep, LimsRunChecklistStepStatus


class LimsRunChecklistRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        run_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> LimsRunChecklist:
        process = LimsRunChecklist(
            lims_run_id=run_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(process)
        return process

    def get_by_id(self, checklist_id: uuid.UUID) -> Optional[LimsRunChecklist]:
        return self.db.query(LimsRunChecklist).filter(
            LimsRunChecklist.id == checklist_id
        ).first()

    def list_for_run(self, run_id: uuid.UUID) -> List[LimsRunChecklist]:
        return (
            self.db.query(LimsRunChecklist)
            .options(selectinload(LimsRunChecklist.steps))
            .filter(LimsRunChecklist.lims_run_id == run_id)
            .order_by(LimsRunChecklist.sort_order)
            .all()
        )

    def delete(self, process: LimsRunChecklist) -> None:
        self.db.delete(process)


class LimsRunChecklistStepRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        checklist_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> LimsRunChecklistStep:
        step = LimsRunChecklistStep(
            checklist_id=checklist_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(step)
        return step

    def get_by_id(self, step_id: uuid.UUID) -> Optional[LimsRunChecklistStep]:
        return self.db.query(LimsRunChecklistStep).filter(LimsRunChecklistStep.id == step_id).first()

    def list_for_process(self, checklist_id: uuid.UUID) -> List[LimsRunChecklistStep]:
        return (
            self.db.query(LimsRunChecklistStep)
            .filter(LimsRunChecklistStep.checklist_id == checklist_id)
            .order_by(LimsRunChecklistStep.sort_order)
            .all()
        )

    def update_status(
        self,
        step: LimsRunChecklistStep,
        new_status: LimsRunChecklistStepStatus,
        modified_by: Optional[uuid.UUID] = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        step.status = new_status
        step.modified_by = modified_by
        if new_status == LimsRunChecklistStepStatus.in_process:
            step.started_at = now
        elif new_status == LimsRunChecklistStepStatus.complete:
            step.completed_at = now
        elif new_status == LimsRunChecklistStepStatus.failed:
            step.failed_at = now

    def update_notes(
        self,
        step: LimsRunChecklistStep,
        notes: str,
        modified_by: Optional[uuid.UUID] = None,
    ) -> None:
        step.notes = notes
        step.modified_by = modified_by
