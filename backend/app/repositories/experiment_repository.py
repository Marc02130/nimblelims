"""
Repository for experiment-related database access.

Follows project patterns: session-based queries, no business logic.
"""
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models.experiment import (
    ExperimentTemplate,
    Experiment,
    ExperimentDetail,
    ExperimentSampleExecution,
)
from models.sample import Sample


class ExperimentRepository:
    """Data access for experiments, templates, details, and sample executions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- ExperimentTemplate ----------

    def get_template_by_id(self, template_id: UUID) -> Optional[ExperimentTemplate]:
        return self.db.query(ExperimentTemplate).filter(
            ExperimentTemplate.id == template_id,
        ).first()

    def get_template_by_name(self, name: str) -> Optional[ExperimentTemplate]:
        return self.db.query(ExperimentTemplate).filter(
            ExperimentTemplate.name == name,
        ).first()

    def list_templates(
        self,
        active: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ExperimentTemplate], int]:
        query = self.db.query(ExperimentTemplate)
        if active is not None:
            query = query.filter(ExperimentTemplate.active == active)
        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(ExperimentTemplate.name).offset(offset).limit(size).all()
        return items, total

    def create_template(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
        lifecycle_type: Optional[str] = None,
        template_definition: Optional[dict] = None,
        custom_attributes: Optional[dict] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ExperimentTemplate:
        t = ExperimentTemplate(
            name=name,
            description=description,
            active=active,
            lifecycle_type=lifecycle_type or "standard",
            template_definition=template_definition or {},
            custom_attributes=custom_attributes or {},
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(t)
        self.db.flush()
        return t

    def update_template(
        self,
        template: ExperimentTemplate,
        **kwargs,
    ) -> ExperimentTemplate:
        for k, v in kwargs.items():
            if hasattr(template, k) and v is not None:
                setattr(template, k, v)
        self.db.flush()
        return template

    def delete_template_soft(self, template: ExperimentTemplate) -> None:
        template.active = False
        self.db.flush()

    # ---------- Experiment ----------

    def get_experiment_by_id(
        self,
        experiment_id: UUID,
        load_details: bool = True,
        load_sample_executions: bool = True,
    ) -> Optional[Experiment]:
        query = self.db.query(Experiment).filter(Experiment.id == experiment_id)
        if load_details:
            query = query.options(joinedload(Experiment.details))
        if load_sample_executions:
            query = query.options(joinedload(Experiment.sample_executions))
        query = query.options(joinedload(Experiment.experiment_template))
        return query.first()

    def list_experiments(
        self,
        experiment_template_id: Optional[UUID] = None,
        status_id: Optional[UUID] = None,
        active: Optional[bool] = True,
        created_by: Optional[UUID] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Experiment], int]:
        query = self.db.query(Experiment)
        if active is not None:
            query = query.filter(Experiment.active == active)
        if experiment_template_id is not None:
            query = query.filter(Experiment.experiment_template_id == experiment_template_id)
        if status_id is not None:
            query = query.filter(Experiment.status_id == status_id)
        if created_by is not None:
            query = query.filter(Experiment.created_by == created_by)
        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(Experiment.created_at.desc()).offset(offset).limit(size).all()
        return items, total

    def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
        experiment_template_id: Optional[UUID] = None,
        status_id: Optional[UUID] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        custom_attributes: Optional[dict] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> Experiment:
        e = Experiment(
            name=name,
            description=description,
            active=active,
            experiment_template_id=experiment_template_id,
            status_id=status_id,
            started_at=started_at,
            completed_at=completed_at,
            custom_attributes=custom_attributes or {},
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(e)
        self.db.flush()
        return e

    def update_experiment(self, experiment: Experiment, **kwargs) -> Experiment:
        for k, v in kwargs.items():
            if hasattr(experiment, k) and v is not None:
                setattr(experiment, k, v)
        self.db.flush()
        return experiment

    def delete_experiment_soft(self, experiment: Experiment) -> None:
        experiment.active = False
        self.db.flush()

    # ---------- ExperimentDetail ----------

    def get_detail_by_id(self, detail_id: UUID) -> Optional[ExperimentDetail]:
        return self.db.query(ExperimentDetail).filter(ExperimentDetail.id == detail_id).first()

    def get_next_sort_order(self, experiment_id: UUID) -> int:
        r = self.db.query(func.coalesce(func.max(ExperimentDetail.sort_order), -1) + 1).filter(
            ExperimentDetail.experiment_id == experiment_id,
        ).scalar()
        return int(r) if r is not None else 0

    def add_detail(
        self,
        experiment_id: UUID,
        detail_type: str,
        content: dict,
        sort_order: int,
        custom_attributes: Optional[dict] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ExperimentDetail:
        d = ExperimentDetail(
            experiment_id=experiment_id,
            detail_type=detail_type,
            content=content or {},
            sort_order=sort_order,
            custom_attributes=custom_attributes or {},
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(d)
        self.db.flush()
        return d

    # ---------- ExperimentSampleExecution ----------

    def get_execution_by_id(self, execution_id: UUID) -> Optional[ExperimentSampleExecution]:
        return self.db.query(ExperimentSampleExecution).filter(
            ExperimentSampleExecution.id == execution_id,
        ).first()

    def find_execution(
        self,
        experiment_id: UUID,
        sample_id: UUID,
        replicate_number: int,
    ) -> Optional[ExperimentSampleExecution]:
        return self.db.query(ExperimentSampleExecution).filter(
            ExperimentSampleExecution.experiment_id == experiment_id,
            ExperimentSampleExecution.sample_id == sample_id,
            ExperimentSampleExecution.replicate_number == replicate_number,
        ).first()

    def add_sample_execution(
        self,
        experiment_id: UUID,
        sample_id: UUID,
        role_in_experiment_id: Optional[UUID] = None,
        processing_conditions: Optional[dict] = None,
        replicate_number: int = 1,
        test_id: Optional[UUID] = None,
        result_id: Optional[UUID] = None,
        custom_attributes: Optional[dict] = None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> ExperimentSampleExecution:
        ex = ExperimentSampleExecution(
            experiment_id=experiment_id,
            sample_id=sample_id,
            role_in_experiment_id=role_in_experiment_id,
            processing_conditions=processing_conditions or {},
            replicate_number=replicate_number,
            test_id=test_id,
            result_id=result_id,
            custom_attributes=custom_attributes or {},
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(ex)
        self.db.flush()
        return ex

    def get_executions_by_sample_id(self, sample_id: UUID) -> List[ExperimentSampleExecution]:
        return self.db.query(ExperimentSampleExecution).filter(
            ExperimentSampleExecution.sample_id == sample_id,
        ).options(
            joinedload(ExperimentSampleExecution.experiment),
        ).all()

    def get_details_by_experiment_id(
        self,
        experiment_id: UUID,
        detail_type: Optional[str] = None,
    ) -> List[ExperimentDetail]:
        query = self.db.query(ExperimentDetail).filter(
            ExperimentDetail.experiment_id == experiment_id,
        ).order_by(ExperimentDetail.sort_order)
        if detail_type:
            query = query.filter(ExperimentDetail.detail_type == detail_type)
        return query.all()

    def get_sample_by_id(self, sample_id: UUID) -> Optional[Sample]:
        return self.db.query(Sample).filter(Sample.id == sample_id).first()
