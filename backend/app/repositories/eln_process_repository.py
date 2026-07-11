"""
Repository for ELN Process data access (Phase 1).
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models.entry import (
    ELNProcess,
    ELNProcessStep,
    ELNProcessSample,
    ELNProcessDefinition,
    ELNProcessDefinitionStep,
    ELNProcessStepLimsRun,
)
from models.experiment import ExperimentTemplate
from models.sample import Sample
from models.flexible_experiment import LimsRun


class ELNProcessRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- Definitions ----------

    def get_definition(self, definition_id: UUID) -> Optional[ELNProcessDefinition]:
        return (
            self.db.query(ELNProcessDefinition)
            .options(joinedload(ELNProcessDefinition.steps))
            .filter(ELNProcessDefinition.id == definition_id)
            .first()
        )

    def get_definition_by_name(self, name: str) -> Optional[ELNProcessDefinition]:
        return (
            self.db.query(ELNProcessDefinition)
            .filter(ELNProcessDefinition.name == name)
            .first()
        )

    def list_definitions(
        self,
        active: Optional[bool] = True,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ELNProcessDefinition], int]:
        q = self.db.query(ELNProcessDefinition)
        if active is not None:
            q = q.filter(ELNProcessDefinition.active == active)
        total = q.count()
        items = (
            q.order_by(ELNProcessDefinition.name)
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return items, total

    def count_definition_steps(self, definition_id: UUID) -> int:
        return (
            self.db.query(func.count(ELNProcessDefinitionStep.id))
            .filter(ELNProcessDefinitionStep.process_definition_id == definition_id)
            .scalar()
            or 0
        )

    def create_definition(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ELNProcessDefinition:
        d = ELNProcessDefinition(
            name=name,
            description=description,
            active=active,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(d)
        self.db.flush()
        return d

    def update_definition(self, definition: ELNProcessDefinition, **kwargs) -> ELNProcessDefinition:
        for k, v in kwargs.items():
            if hasattr(definition, k):
                setattr(definition, k, v)
        self.db.flush()
        return definition

    def create_definition_step(
        self,
        process_definition_id: UUID,
        experiment_template_id: UUID,
        sort_order: int,
        step_kind: str = 'eln_experiment',
        execution_mode: str = 'eln_experiment',
        name: Optional[str] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ELNProcessDefinitionStep:
        s = ELNProcessDefinitionStep(
            process_definition_id=process_definition_id,
            experiment_template_id=experiment_template_id,
            step_kind=step_kind,
            execution_mode=execution_mode,
            name=name,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(s)
        self.db.flush()
        return s

    def list_definition_steps(self, definition_id: UUID) -> List[ELNProcessDefinitionStep]:
        return (
            self.db.query(ELNProcessDefinitionStep)
            .filter(ELNProcessDefinitionStep.process_definition_id == definition_id)
            .order_by(ELNProcessDefinitionStep.sort_order)
            .all()
        )

    # ---------- Process ----------

    def get_by_id(
        self,
        process_id: UUID,
        load_steps: bool = True,
        load_samples: bool = True,
    ) -> Optional[ELNProcess]:
        query = self.db.query(ELNProcess).filter(ELNProcess.id == process_id)
        if load_steps:
            query = query.options(
                joinedload(ELNProcess.steps).joinedload(ELNProcessStep.experiment_template)
            )
        if load_samples:
            query = query.options(joinedload(ELNProcess.process_samples))
        return query.first()

    def get_by_name(self, name: str) -> Optional[ELNProcess]:
        return self.db.query(ELNProcess).filter(ELNProcess.name == name).first()

    def list_processes(
        self,
        active: Optional[bool] = True,
        created_by: Optional[UUID] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ELNProcess], int]:
        query = self.db.query(ELNProcess)
        if active is not None:
            query = query.filter(ELNProcess.active == active)
        if created_by is not None:
            query = query.filter(ELNProcess.created_by == created_by)
        total = query.count()
        offset = (page - 1) * size
        items = (
            query.order_by(ELNProcess.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )
        return items, total

    def count_steps(self, process_id: UUID) -> int:
        return (
            self.db.query(func.count(ELNProcessStep.id))
            .filter(ELNProcessStep.process_id == process_id)
            .scalar()
            or 0
        )

    def count_samples(self, process_id: UUID) -> int:
        return (
            self.db.query(func.count(ELNProcessSample.id))
            .filter(ELNProcessSample.process_id == process_id)
            .scalar()
            or 0
        )

    def create_process(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
        status_id: Optional[UUID] = None,
        process_definition_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ELNProcess:
        p = ELNProcess(
            name=name,
            description=description,
            active=active,
            status_id=status_id,
            process_definition_id=process_definition_id,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(p)
        self.db.flush()
        return p

    def update_process(self, process: ELNProcess, **kwargs) -> ELNProcess:
        for k, v in kwargs.items():
            if hasattr(process, k):
                setattr(process, k, v)
        self.db.flush()
        return process

    def soft_delete_process(self, process: ELNProcess) -> None:
        process.active = False
        self.db.flush()

    # ---------- Steps ----------

    def get_step_by_id(self, step_id: UUID) -> Optional[ELNProcessStep]:
        return (
            self.db.query(ELNProcessStep)
            .filter(ELNProcessStep.id == step_id)
            .first()
        )

    def list_steps(self, process_id: UUID) -> List[ELNProcessStep]:
        return (
            self.db.query(ELNProcessStep)
            .filter(ELNProcessStep.process_id == process_id)
            .order_by(ELNProcessStep.sort_order)
            .all()
        )

    def next_sort_order(self, process_id: UUID) -> int:
        r = self.db.query(func.coalesce(func.max(ELNProcessStep.sort_order), -1) + 1).filter(
            ELNProcessStep.process_id == process_id,
        ).scalar()
        return int(r) if r is not None else 0

    def create_step(
        self,
        process_id: UUID,
        experiment_template_id: UUID,
        sort_order: int,
        name: Optional[str] = None,
        experiment_id: Optional[UUID] = None,
        step_kind: str = 'eln_experiment',
        execution_mode: str = 'eln_experiment',
        current_lims_run_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ELNProcessStep:
        step = ELNProcessStep(
            process_id=process_id,
            experiment_template_id=experiment_template_id,
            experiment_id=experiment_id,
            step_kind=step_kind,
            execution_mode=execution_mode,
            current_lims_run_id=current_lims_run_id,
            name=name,
            sort_order=sort_order,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(step)
        self.db.flush()
        return step

    def add_step_lims_run_history(
        self,
        process_step_id: UUID,
        lims_run_id: UUID,
        created_by: Optional[UUID] = None,
    ) -> ELNProcessStepLimsRun:
        link = ELNProcessStepLimsRun(
            process_step_id=process_step_id,
            lims_run_id=lims_run_id,
            created_by=created_by,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def list_samples_journey(self, sample_id: UUID) -> List[ELNProcessSample]:
        return (
            self.db.query(ELNProcessSample)
            .options(
                joinedload(ELNProcessSample.process).joinedload(ELNProcess.steps),
            )
            .filter(ELNProcessSample.sample_id == sample_id)
            .order_by(ELNProcessSample.assigned_at.desc())
            .all()
        )

    def get_lims_run(self, run_id: UUID) -> Optional[LimsRun]:
        return self.db.query(LimsRun).filter(LimsRun.id == run_id).first()

    def update_step(self, step: ELNProcessStep, **kwargs) -> ELNProcessStep:
        for k, v in kwargs.items():
            if hasattr(step, k):
                setattr(step, k, v)
        self.db.flush()
        return step

    def delete_step(self, step: ELNProcessStep) -> None:
        self.db.delete(step)
        self.db.flush()

    def template_exists(self, template_id: UUID) -> bool:
        return (
            self.db.query(ExperimentTemplate.id)
            .filter(ExperimentTemplate.id == template_id)
            .first()
            is not None
        )

    # ---------- Samples ----------

    def get_process_sample(
        self,
        process_id: UUID,
        sample_id: UUID,
    ) -> Optional[ELNProcessSample]:
        return (
            self.db.query(ELNProcessSample)
            .filter(
                ELNProcessSample.process_id == process_id,
                ELNProcessSample.sample_id == sample_id,
            )
            .first()
        )

    def get_process_sample_by_id(self, assignment_id: UUID) -> Optional[ELNProcessSample]:
        return (
            self.db.query(ELNProcessSample)
            .filter(ELNProcessSample.id == assignment_id)
            .first()
        )

    def list_process_samples(
        self,
        process_id: UUID,
        current_step_id: Optional[UUID] = None,
        sample_status: Optional[str] = None,
    ) -> List[ELNProcessSample]:
        query = self.db.query(ELNProcessSample).filter(
            ELNProcessSample.process_id == process_id,
        )
        if current_step_id is not None:
            query = query.filter(ELNProcessSample.current_step_id == current_step_id)
        if sample_status is not None:
            query = query.filter(ELNProcessSample.status == sample_status)
        return query.order_by(ELNProcessSample.assigned_at).all()

    def sample_exists(self, sample_id: UUID) -> bool:
        return (
            self.db.query(Sample.id).filter(Sample.id == sample_id).first() is not None
        )

    def create_process_sample(
        self,
        process_id: UUID,
        sample_id: UUID,
        status: str = 'assigned',
        current_step_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ELNProcessSample:
        ps = ELNProcessSample(
            process_id=process_id,
            sample_id=sample_id,
            status=status,
            current_step_id=current_step_id,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(ps)
        self.db.flush()
        return ps

    def update_process_sample(self, ps: ELNProcessSample, **kwargs) -> ELNProcessSample:
        for k, v in kwargs.items():
            if hasattr(ps, k):
                setattr(ps, k, v)
        self.db.flush()
        return ps

    def delete_process_sample(self, ps: ELNProcessSample) -> None:
        self.db.delete(ps)
        self.db.flush()
