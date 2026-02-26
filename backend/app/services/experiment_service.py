"""
Service layer for experiments and experiment templates.

Uses ExperimentRepository for DB access; handles validation, 404/400, commit/rollback.
"""
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.experiment_repository import ExperimentRepository
from app.schemas.experiment import (
    ExperimentTemplateCreate,
    ExperimentTemplateUpdate,
    ExperimentCreate,
    ExperimentUpdate,
    AddExperimentDetailStepRequest,
    LinkSampleToExperimentRequest,
    LinkExperimentsRequest,
)
from models.experiment import ExperimentTemplate, Experiment, ExperimentDetail, ExperimentSampleExecution
from models.user import User


class ExperimentService:
    """Business logic for experiments and templates."""

    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.repo = ExperimentRepository(db)
        self.current_user = current_user
        self.auto_commit = auto_commit

    def _user_id(self) -> Optional[UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects: Any) -> None:
        """Flush so IDs are set; refresh objects; commit only if auto_commit (False when used from workflow)."""
        self.db.flush()
        for obj in objects:
            if obj is not None:
                self.db.refresh(obj)
        if self.auto_commit:
            self.db.commit()

    # ---------- ExperimentTemplate ----------

    def get_template(self, template_id: UUID) -> ExperimentTemplate:
        t = self.repo.get_template_by_id(template_id)
        if not t:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment template not found")
        return t

    def list_templates(
        self,
        active: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ExperimentTemplate], int]:
        return self.repo.list_templates(active=active, page=page, size=size)

    def create_template(self, data: ExperimentTemplateCreate) -> ExperimentTemplate:
        if self.repo.get_template_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Experiment template with name '{data.name}' already exists",
            )
        t = self.repo.create_template(
            name=data.name,
            description=data.description,
            active=True,
            template_definition=data.template_definition,
            custom_attributes=data.custom_attributes,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self._commit_refresh(t)
        return t

    def update_template(self, template_id: UUID, data: ExperimentTemplateUpdate) -> ExperimentTemplate:
        t = self.get_template(template_id)
        update_kwargs: Dict[str, Any] = {}
        if data.name is not None:
            existing = self.repo.get_template_by_name(data.name)
            if existing and existing.id != template_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Another template with name '{data.name}' already exists",
                )
            update_kwargs["name"] = data.name
        if data.description is not None:
            update_kwargs["description"] = data.description
        if data.active is not None:
            update_kwargs["active"] = data.active
        if data.template_definition is not None:
            update_kwargs["template_definition"] = data.template_definition
        if data.custom_attributes is not None:
            update_kwargs["custom_attributes"] = data.custom_attributes
        update_kwargs["modified_by"] = self._user_id()
        self.repo.update_template(t, **update_kwargs)
        self._commit_refresh(t)
        return t

    def delete_template(self, template_id: UUID) -> None:
        t = self.get_template(template_id)
        self.repo.delete_template_soft(t)
        self._commit_refresh()

    # ---------- Experiment ----------

    def get_experiment(
        self,
        experiment_id: UUID,
        load_details: bool = True,
        load_sample_executions: bool = True,
    ) -> Experiment:
        e = self.repo.get_experiment_by_id(
            experiment_id,
            load_details=load_details,
            load_sample_executions=load_sample_executions,
        )
        if not e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
        return e

    def list_experiments(
        self,
        experiment_template_id: Optional[UUID] = None,
        status_id: Optional[UUID] = None,
        active: Optional[bool] = True,
        created_by: Optional[UUID] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Experiment], int]:
        return self.repo.list_experiments(
            experiment_template_id=experiment_template_id,
            status_id=status_id,
            active=active,
            created_by=created_by,
            page=page,
            size=size,
        )

    def create_experiment(self, data: ExperimentCreate) -> Experiment:
        e = self.repo.create_experiment(
            name=data.name,
            description=data.description,
            active=True,
            experiment_template_id=data.experiment_template_id,
            status_id=data.status_id,
            started_at=data.started_at,
            completed_at=data.completed_at,
            custom_attributes=data.custom_attributes,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self._commit_refresh(e)
        return e

    def update_experiment(self, experiment_id: UUID, data: ExperimentUpdate) -> Experiment:
        e = self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        update_kwargs: Dict[str, Any] = {}
        if data.name is not None:
            update_kwargs["name"] = data.name
        if data.description is not None:
            update_kwargs["description"] = data.description
        if data.active is not None:
            update_kwargs["active"] = data.active
        if data.experiment_template_id is not None:
            update_kwargs["experiment_template_id"] = data.experiment_template_id
        if data.status_id is not None:
            update_kwargs["status_id"] = data.status_id
        if data.started_at is not None:
            update_kwargs["started_at"] = data.started_at
        if data.completed_at is not None:
            update_kwargs["completed_at"] = data.completed_at
        if data.custom_attributes is not None:
            update_kwargs["custom_attributes"] = data.custom_attributes
        update_kwargs["modified_by"] = self._user_id()
        self.repo.update_experiment(e, **update_kwargs)
        self._commit_refresh(e)
        return e

    def delete_experiment(self, experiment_id: UUID) -> None:
        e = self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        self.repo.delete_experiment_soft(e)
        self._commit_refresh()

    # ---------- Experiment detail step ----------

    def add_experiment_detail_step(
        self,
        experiment_id: UUID,
        data: AddExperimentDetailStepRequest,
    ) -> ExperimentDetail:
        self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        sort_order = data.sort_order
        if sort_order is None:
            sort_order = self.repo.get_next_sort_order(experiment_id)
        d = self.repo.add_detail(
            experiment_id=experiment_id,
            detail_type=data.detail_type,
            content=data.content,
            sort_order=sort_order,
            custom_attributes={},
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self._commit_refresh(d)
        return d

    # ---------- Link sample to experiment ----------

    def link_sample_to_experiment(
        self,
        experiment_id: UUID,
        data: LinkSampleToExperimentRequest,
    ) -> ExperimentSampleExecution:
        self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        sample = self.repo.get_sample_by_id(data.sample_id)
        if not sample:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
        existing = self.repo.find_execution(
            experiment_id=experiment_id,
            sample_id=data.sample_id,
            replicate_number=data.replicate_number,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This sample is already linked to this experiment with this replicate number",
            )
        ex = self.repo.add_sample_execution(
            experiment_id=experiment_id,
            sample_id=data.sample_id,
            role_in_experiment_id=data.role_in_experiment_id,
            processing_conditions=data.processing_conditions,
            replicate_number=data.replicate_number,
            test_id=data.test_id,
            result_id=data.result_id,
            custom_attributes=data.custom_attributes,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self._commit_refresh(ex)
        return ex

    # ---------- Link experiments (store as detail type experiment_link) ----------

    def link_experiments(self, experiment_id: UUID, data: LinkExperimentsRequest) -> ExperimentDetail:
        e = self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        linked = self.repo.get_experiment_by_id(data.linked_experiment_id, load_details=False, load_sample_executions=False)
        if not linked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked experiment not found")
        if linked.id == experiment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot link an experiment to itself",
            )
        sort_order = self.repo.get_next_sort_order(experiment_id)
        d = self.repo.add_detail(
            experiment_id=experiment_id,
            detail_type="experiment_link",
            content={"linked_experiment_id": str(data.linked_experiment_id)},
            sort_order=sort_order,
            custom_attributes={},
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self._commit_refresh(d)
        return d

    # ---------- Get experiment lineage ----------

    def get_experiment_lineage(self, experiment_id: UUID) -> Tuple[Experiment, Optional[ExperimentTemplate], List[UUID]]:
        e = self.get_experiment(experiment_id, load_details=True, load_sample_executions=False)
        template = None
        if e.experiment_template_id:
            template = self.repo.get_template_by_id(e.experiment_template_id)
        linked_ids: List[UUID] = []
        for d in e.details or []:
            if d.detail_type == "experiment_link" and isinstance(d.content, dict):
                lid = d.content.get("linked_experiment_id")
                if lid:
                    try:
                        linked_ids.append(UUID(lid) if isinstance(lid, str) else lid)
                    except (ValueError, TypeError):
                        pass
        return e, template, linked_ids

    # ---------- Get sample experiments ----------

    def get_sample_experiments(self, sample_id: UUID) -> List[ExperimentSampleExecution]:
        if not self.repo.get_sample_by_id(sample_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
        return self.repo.get_executions_by_sample_id(sample_id)
