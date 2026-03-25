"""
Repositories for ExperimentProcess and ProcessStep.

Pure DB access — no HTTP exceptions, no business logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from models.experiment_process import ExperimentProcess, ProcessStep, ProcessStepStatus


class ExperimentProcessRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        run_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ExperimentProcess:
        process = ExperimentProcess(
            experiment_run_id=run_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(process)
        return process

    def get_by_id(self, process_id: uuid.UUID) -> Optional[ExperimentProcess]:
        return self.db.query(ExperimentProcess).filter(
            ExperimentProcess.id == process_id
        ).first()

    def list_for_run(self, run_id: uuid.UUID) -> List[ExperimentProcess]:
        return (
            self.db.query(ExperimentProcess)
            .filter(ExperimentProcess.experiment_run_id == run_id)
            .order_by(ExperimentProcess.sort_order)
            .all()
        )

    def delete(self, process: ExperimentProcess) -> None:
        self.db.delete(process)


class ProcessStepRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        process_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
        description: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ProcessStep:
        step = ProcessStep(
            process_id=process_id,
            name=name,
            description=description,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(step)
        return step

    def get_by_id(self, step_id: uuid.UUID) -> Optional[ProcessStep]:
        return self.db.query(ProcessStep).filter(ProcessStep.id == step_id).first()

    def list_for_process(self, process_id: uuid.UUID) -> List[ProcessStep]:
        return (
            self.db.query(ProcessStep)
            .filter(ProcessStep.process_id == process_id)
            .order_by(ProcessStep.sort_order)
            .all()
        )

    def update_status(
        self,
        step: ProcessStep,
        new_status: ProcessStepStatus,
        modified_by: Optional[uuid.UUID] = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        step.status = new_status
        step.modified_by = modified_by
        if new_status == ProcessStepStatus.in_process:
            step.started_at = now
        elif new_status == ProcessStepStatus.complete:
            step.completed_at = now
        elif new_status == ProcessStepStatus.failed:
            step.failed_at = now

    def update_notes(
        self,
        step: ProcessStep,
        notes: str,
        modified_by: Optional[uuid.UUID] = None,
    ) -> None:
        step.notes = notes
        step.modified_by = modified_by
