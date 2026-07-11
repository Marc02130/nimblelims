"""
Service layer for ELN Processes (Phase 1).
"""
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.eln_process_repository import ELNProcessRepository
from app.schemas.eln_process import (
    ELNProcessCreate,
    ELNProcessUpdate,
    ELNProcessStepCreate,
    ELNProcessStepUpdate,
    ELNProcessStepInstantiateRequest,
    ELNProcessSampleAssignRequest,
    ELNProcessSampleSetStepRequest,
)
from app.schemas.experiment import ExperimentCreate
from app.services.experiment_service import ExperimentService
from models.entry import ELNProcess, ELNProcessStep, ELNProcessSample
from models.experiment import Experiment
from models.user import User

VALID_SAMPLE_STATUSES = frozenset({'assigned', 'in_progress', 'completed', 'removed'})


class ELNProcessService:
    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.repo = ELNProcessRepository(db)
        self.current_user = current_user
        self.auto_commit = auto_commit

    def _user_id(self) -> Optional[UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects: Any) -> None:
        self.db.flush()
        for obj in objects:
            if obj is not None:
                try:
                    self.db.refresh(obj)
                except Exception:
                    pass
        if self.auto_commit:
            self.db.commit()

    # ---------- Process CRUD ----------

    def get_process(self, process_id: UUID) -> ELNProcess:
        p = self.repo.get_by_id(process_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ELN process not found",
            )
        return p

    def list_processes(
        self,
        active: Optional[bool] = True,
        mine: bool = False,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ELNProcess], int]:
        created_by = self._user_id() if mine else None
        return self.repo.list_processes(
            active=active,
            created_by=created_by,
            page=page,
            size=size,
        )

    def create_process(self, data: ELNProcessCreate) -> ELNProcess:
        if self.repo.get_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process with name '{data.name}' already exists",
            )
        p = self.repo.create_process(
            name=data.name,
            description=data.description,
            status_id=data.status_id,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        if data.steps:
            for i, step_in in enumerate(data.steps):
                self._add_step_internal(p.id, step_in, explicit_order=step_in.sort_order if step_in.sort_order is not None else i)
        self._commit_refresh(p)
        return self.get_process(p.id)

    def update_process(self, process_id: UUID, data: ELNProcessUpdate) -> ELNProcess:
        p = self.get_process(process_id)
        kwargs: Dict[str, Any] = {'modified_by': self._user_id()}
        if data.name is not None:
            existing = self.repo.get_by_name(data.name)
            if existing and existing.id != process_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Another process with name '{data.name}' already exists",
                )
            kwargs['name'] = data.name
        if data.description is not None:
            kwargs['description'] = data.description
        if data.active is not None:
            kwargs['active'] = data.active
        if data.status_id is not None:
            kwargs['status_id'] = data.status_id
        self.repo.update_process(p, **kwargs)
        self._commit_refresh(p)
        return self.get_process(process_id)

    def delete_process(self, process_id: UUID) -> None:
        p = self.get_process(process_id)
        self.repo.soft_delete_process(p)
        p.modified_by = self._user_id()
        self._commit_refresh(p)

    # ---------- Steps ----------

    def list_steps(self, process_id: UUID) -> List[ELNProcessStep]:
        self.get_process(process_id)
        return self.repo.list_steps(process_id)

    def add_step(self, process_id: UUID, data: ELNProcessStepCreate) -> ELNProcessStep:
        self.get_process(process_id)
        step = self._add_step_internal(
            process_id,
            data,
            explicit_order=data.sort_order,
        )
        self._commit_refresh(step)
        return step

    def _add_step_internal(
        self,
        process_id: UUID,
        data: ELNProcessStepCreate,
        explicit_order: Optional[int] = None,
    ) -> ELNProcessStep:
        if not self.repo.template_exists(data.experiment_template_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Experiment template {data.experiment_template_id} not found",
            )
        if explicit_order is not None:
            sort_order = explicit_order
            # Shift existing steps at/after this order to free the slot
            existing = self.repo.list_steps(process_id)
            for s in reversed(existing):
                if s.sort_order >= sort_order:
                    self.repo.update_step(s, sort_order=s.sort_order + 1)
        else:
            sort_order = self.repo.next_sort_order(process_id)
        return self.repo.create_step(
            process_id=process_id,
            experiment_template_id=data.experiment_template_id,
            sort_order=sort_order,
            name=data.name,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )

    def update_step(
        self,
        process_id: UUID,
        step_id: UUID,
        data: ELNProcessStepUpdate,
    ) -> ELNProcessStep:
        self.get_process(process_id)
        step = self.repo.get_step_by_id(step_id)
        if not step or step.process_id != process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        kwargs: Dict[str, Any] = {'modified_by': self._user_id()}
        if data.name is not None:
            kwargs['name'] = data.name
        if data.experiment_template_id is not None:
            if not self.repo.template_exists(data.experiment_template_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Experiment template not found",
                )
            kwargs['experiment_template_id'] = data.experiment_template_id
        if data.experiment_id is not None:
            kwargs['experiment_id'] = data.experiment_id
        if data.sort_order is not None:
            kwargs['sort_order'] = data.sort_order
        self.repo.update_step(step, **kwargs)
        self._commit_refresh(step)
        return step

    def remove_step(self, process_id: UUID, step_id: UUID) -> None:
        self.get_process(process_id)
        step = self.repo.get_step_by_id(step_id)
        if not step or step.process_id != process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        # Clear current_step on samples pointing here (DB SET NULL also covers this)
        for ps in self.repo.list_process_samples(process_id):
            if ps.current_step_id == step_id:
                self.repo.update_process_sample(
                    ps,
                    current_step_id=None,
                    modified_by=self._user_id(),
                )
        removed_order = step.sort_order
        self.repo.delete_step(step)
        # Compact sort_order
        for s in self.repo.list_steps(process_id):
            if s.sort_order > removed_order:
                self.repo.update_step(s, sort_order=s.sort_order - 1)
        if self.auto_commit:
            self.db.commit()

    def reorder_steps(self, process_id: UUID, step_ids: List[UUID]) -> List[ELNProcessStep]:
        self.get_process(process_id)
        existing = self.repo.list_steps(process_id)
        existing_ids = {s.id for s in existing}
        if set(step_ids) != existing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="step_ids must include every step of the process exactly once",
            )
        # Two-phase update to satisfy unique (process_id, sort_order)
        for i, sid in enumerate(step_ids):
            step = self.repo.get_step_by_id(sid)
            self.repo.update_step(step, sort_order=-(i + 1), modified_by=self._user_id())
        self.db.flush()
        for i, sid in enumerate(step_ids):
            step = self.repo.get_step_by_id(sid)
            self.repo.update_step(step, sort_order=i, modified_by=self._user_id())
        if self.auto_commit:
            self.db.commit()
        return self.repo.list_steps(process_id)

    def instantiate_step(
        self,
        process_id: UUID,
        step_id: UUID,
        data: Optional[ELNProcessStepInstantiateRequest] = None,
    ) -> Tuple[ELNProcessStep, Experiment]:
        """
        Create an Experiment from this step's template and link it on the step.

        Idempotent guard: fails if experiment_id is already set.
        """
        process = self.get_process(process_id)
        step = self.repo.get_step_by_id(step_id)
        if not step or step.process_id != process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        if step.experiment_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Step already has an instantiated experiment",
            )
        if not self.repo.template_exists(step.experiment_template_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment template not found",
            )

        step_label = step.name or f"Step {step.sort_order}"
        exp_name = (
            (data.name if data and data.name else None)
            or f"{process.name} — {step_label} ({uuid4().hex[:6]})"
        )
        exp_service = ExperimentService(
            self.db,
            current_user=self.current_user,
            auto_commit=False,
        )
        experiment = exp_service.create_experiment(
            ExperimentCreate(
                name=exp_name,
                description=f"From ELN process '{process.name}' step '{step_label}'",
                experiment_template_id=step.experiment_template_id,
            )
        )
        self.repo.update_step(
            step,
            experiment_id=experiment.id,
            modified_by=self._user_id(),
        )
        # Phase 2: instantiate entries declared on the template (no-op if none)
        from app.services.entry_service import EntryService
        from app.schemas.entry import InstantiateEntriesRequest

        entry_svc = EntryService(
            self.db,
            current_user=self.current_user,
            auto_commit=False,
        )
        entry_svc.instantiate_from_template(
            experiment.id,
            InstantiateEntriesRequest(
                process_step_id=step.id,
                skip_if_exists=True,
            ),
        )
        self._commit_refresh(step, experiment)
        return step, experiment

    # ---------- Samples ----------

    def list_samples(
        self,
        process_id: UUID,
        current_step_id: Optional[UUID] = None,
        sample_status: Optional[str] = None,
    ) -> List[ELNProcessSample]:
        self.get_process(process_id)
        return self.repo.list_process_samples(
            process_id,
            current_step_id=current_step_id,
            sample_status=sample_status,
        )

    def assign_samples(
        self,
        process_id: UUID,
        data: ELNProcessSampleAssignRequest,
    ) -> List[ELNProcessSample]:
        self.get_process(process_id)
        steps = self.repo.list_steps(process_id)
        first_step_id = steps[0].id if steps and data.set_to_first_step else None
        created: List[ELNProcessSample] = []
        for sample_id in data.sample_ids:
            if not self.repo.sample_exists(sample_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sample {sample_id} not found",
                )
            existing = self.repo.get_process_sample(process_id, sample_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sample {sample_id} is already assigned to this process",
                )
            status_val = 'in_progress' if first_step_id else 'assigned'
            ps = self.repo.create_process_sample(
                process_id=process_id,
                sample_id=sample_id,
                status=status_val,
                current_step_id=first_step_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            created.append(ps)
        self._commit_refresh(*created)
        return created

    def remove_sample(self, process_id: UUID, sample_id: UUID) -> None:
        self.get_process(process_id)
        ps = self.repo.get_process_sample(process_id, sample_id)
        if not ps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample is not assigned to this process",
            )
        self.repo.delete_process_sample(ps)
        if self.auto_commit:
            self.db.commit()

    def set_sample_step(
        self,
        process_id: UUID,
        sample_id: UUID,
        data: ELNProcessSampleSetStepRequest,
    ) -> ELNProcessSample:
        self.get_process(process_id)
        ps = self.repo.get_process_sample(process_id, sample_id)
        if not ps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample is not assigned to this process",
            )
        kwargs: Dict[str, Any] = {'modified_by': self._user_id()}
        if data.step_id is not None:
            step = self.repo.get_step_by_id(data.step_id)
            if not step or step.process_id != process_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Step does not belong to this process",
                )
            kwargs['current_step_id'] = data.step_id
            kwargs['status'] = data.status or 'in_progress'
        else:
            # Explicit clear when step_id is null in body — only if field was provided
            # For set endpoint with step_id: null, clear current step
            kwargs['current_step_id'] = None
            if data.status:
                kwargs['status'] = data.status
        if data.status is not None:
            if data.status not in VALID_SAMPLE_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status; allowed: {sorted(VALID_SAMPLE_STATUSES)}",
                )
            kwargs['status'] = data.status
        self.repo.update_process_sample(ps, **kwargs)
        self._commit_refresh(ps)
        return ps

    def advance_sample(self, process_id: UUID, sample_id: UUID) -> ELNProcessSample:
        """Move sample to the next step by sort_order; complete if already on last."""
        self.get_process(process_id)
        ps = self.repo.get_process_sample(process_id, sample_id)
        if not ps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample is not assigned to this process",
            )
        steps = self.repo.list_steps(process_id)
        if not steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Process has no steps; cannot advance sample",
            )
        if ps.current_step_id is None:
            # Start at first step
            self.repo.update_process_sample(
                ps,
                current_step_id=steps[0].id,
                status='in_progress',
                modified_by=self._user_id(),
            )
        else:
            idx = next((i for i, s in enumerate(steps) if s.id == ps.current_step_id), None)
            if idx is None:
                # Stale step reference — reset to first
                self.repo.update_process_sample(
                    ps,
                    current_step_id=steps[0].id,
                    status='in_progress',
                    modified_by=self._user_id(),
                )
            elif idx >= len(steps) - 1:
                self.repo.update_process_sample(
                    ps,
                    status='completed',
                    modified_by=self._user_id(),
                )
            else:
                self.repo.update_process_sample(
                    ps,
                    current_step_id=steps[idx + 1].id,
                    status='in_progress',
                    modified_by=self._user_id(),
                )
        self._commit_refresh(ps)
        return ps
