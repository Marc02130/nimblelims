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
    ELNProcessSampleAdvanceResponse,
    ELNProcessSampleRead,
    ELNProcessStepStartResponse,
    ELNProcessStepRead,
    SampleJourneyResponse,
    SampleJourneyStep,
    ProcessAssignmentItem,
)
from app.schemas.eln_process_definition import (
    ELNProcessDefinitionCreate,
    ELNProcessDefinitionUpdate,
    ELNProcessDefinitionStepCreate,
    InstantiateProcessFromDefinitionRequest,
)
from app.schemas.experiment import ExperimentCreate, StartExperimentRequest
from app.schemas.flexible_experiment import LimsRunCreate
from app.services.experiment_service import ExperimentService
from models.entry import (
    ELNProcess,
    ELNProcessStep,
    ELNProcessSample,
    ELNProcessDefinition,
    STEP_KINDS,
)
from models.container import Contents
from models.experiment import Experiment
from models.flexible_experiment import LimsRun
from models.user import User
from models.sample import Sample

# Process-sample lifecycle (not Sample.status):
#   queued      — assigned to process / waiting for experiment start
#   in_progress — experiment for current step has started
#   completed   — finished last step (or process done for this sample)
#   removed     — unassigned
#   assigned    — legacy alias of queued (still accepted)
VALID_SAMPLE_STATUSES = frozenset({'queued', 'assigned', 'in_progress', 'completed', 'removed'})
QUEUED_STATUSES = frozenset({'queued', 'assigned'})
_RUN_SOFT_GATE_OK = frozenset({'complete', 'published'})


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

    # ---------- Definitions (Phase 3) ----------

    def get_definition(self, definition_id: UUID) -> ELNProcessDefinition:
        d = self.repo.get_definition(definition_id)
        if not d:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process definition not found",
            )
        return d

    def list_definitions(
        self,
        active: Optional[bool] = True,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ELNProcessDefinition], int]:
        return self.repo.list_definitions(active=active, page=page, size=size)

    def create_definition(self, data: ELNProcessDefinitionCreate) -> ELNProcessDefinition:
        if self.repo.get_definition_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process definition with name '{data.name}' already exists",
            )
        d = self.repo.create_definition(
            name=data.name,
            description=data.description,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        if data.steps:
            for i, s in enumerate(data.steps):
                self._add_definition_step(d.id, s, i if s.sort_order is None else s.sort_order)
        self._commit_refresh(d)
        return self.get_definition(d.id)

    def _add_definition_step(
        self,
        definition_id: UUID,
        s: ELNProcessDefinitionStepCreate,
        sort_order: int,
    ) -> None:
        kind = s.step_kind
        mode = s.execution_mode or kind
        if mode != kind:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="execution_mode must match step_kind",
            )
        if kind == "eln_experiment":
            if not s.experiment_template_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="experiment_template_id is required for eln_experiment steps",
                )
            if not self.repo.template_exists(s.experiment_template_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Experiment template {s.experiment_template_id} not found",
                )
        elif kind == "lims_run":
            if not s.analysis_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="analysis_id is required for lims_run steps",
                )
        self.repo.create_definition_step(
            process_definition_id=definition_id,
            experiment_template_id=s.experiment_template_id,
            analysis_id=getattr(s, "analysis_id", None),
            sort_order=sort_order,
            step_kind=kind,
            execution_mode=mode,
            name=s.name,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )

    def update_definition(
        self,
        definition_id: UUID,
        data: ELNProcessDefinitionUpdate,
    ) -> ELNProcessDefinition:
        d = self.get_definition(definition_id)
        kwargs: Dict[str, Any] = {'modified_by': self._user_id()}
        if data.name is not None:
            existing = self.repo.get_definition_by_name(data.name)
            if existing and existing.id != definition_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Another definition named '{data.name}' exists",
                )
            kwargs['name'] = data.name
        if data.description is not None:
            kwargs['description'] = data.description
        if data.active is not None:
            kwargs['active'] = data.active
        self.repo.update_definition(d, **kwargs)
        self._commit_refresh(d)
        return self.get_definition(definition_id)

    def add_definition_step(
        self,
        definition_id: UUID,
        data: ELNProcessDefinitionStepCreate,
    ):
        self.get_definition(definition_id)
        steps = self.repo.list_definition_steps(definition_id)
        order = data.sort_order if data.sort_order is not None else len(steps)
        self._add_definition_step(definition_id, data, order)
        if self.auto_commit:
            self.db.commit()
        return self.get_definition(definition_id)

    def instantiate_from_definition(
        self,
        definition_id: UUID,
        data: Optional[InstantiateProcessFromDefinitionRequest] = None,
    ) -> ELNProcess:
        """Create process instance by snapshotting definition steps."""
        data = data or InstantiateProcessFromDefinitionRequest()
        definition = self.get_definition(definition_id)
        if not definition.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot instantiate an inactive process definition",
            )
        def_steps = self.repo.list_definition_steps(definition_id)
        inst_name = data.name or f"{definition.name} ({uuid4().hex[:6]})"
        if self.repo.get_by_name(inst_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process with name '{inst_name}' already exists",
            )
        p = self.repo.create_process(
            name=inst_name,
            description=data.description or definition.description,
            status_id=data.status_id,
            process_definition_id=definition_id,
            work_order_id=data.work_order_id,
            work_order_route_position=data.work_order_route_position,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        for s in def_steps:
            self.repo.create_step(
                process_id=p.id,
                experiment_template_id=s.experiment_template_id,
                analysis_id=getattr(s, "analysis_id", None),
                sort_order=s.sort_order,
                name=s.name,
                step_kind=s.step_kind,
                execution_mode=s.execution_mode,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
        if data.assignments or data.sample_ids:
            self.assign_samples(
                p.id,
                ELNProcessSampleAssignRequest(
                    sample_ids=data.sample_ids,
                    assignments=data.assignments,
                    set_to_first_step=data.set_to_first_step,
                ),
            )
        else:
            self._commit_refresh(p)
        return self.get_process(p.id)

    def create_process(self, data: ELNProcessCreate) -> ELNProcess:
        """
        Create instance. If process_definition_id set, snapshot from definition.
        Else free-form steps auto-create a snapshot definition (Decision #6).
        """
        if data.process_definition_id:
            return self.instantiate_from_definition(
                data.process_definition_id,
                InstantiateProcessFromDefinitionRequest(
                    name=data.name,
                    description=data.description,
                    status_id=data.status_id,
                ),
            )

        if self.repo.get_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process with name '{data.name}' already exists",
            )

        # Auto definition from free-form steps (or empty)
        def_name = f"{data.name} (definition)"
        n = 0
        while self.repo.get_definition_by_name(def_name):
            n += 1
            def_name = f"{data.name} (definition {n})"
        definition = self.repo.create_definition(
            name=def_name,
            description=data.description,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        if data.steps:
            for i, step_in in enumerate(data.steps):
                kind = getattr(step_in, 'step_kind', None) or 'eln_experiment'
                mode = getattr(step_in, 'execution_mode', None) or kind
                self._add_definition_step(
                    definition.id,
                    ELNProcessDefinitionStepCreate(
                        experiment_template_id=step_in.experiment_template_id,
                        step_kind=kind,
                        execution_mode=mode,
                        name=step_in.name,
                        sort_order=step_in.sort_order if step_in.sort_order is not None else i,
                    ),
                    step_in.sort_order if step_in.sort_order is not None else i,
                )
        return self.instantiate_from_definition(
            definition.id,
            InstantiateProcessFromDefinitionRequest(
                name=data.name,
                description=data.description,
                status_id=data.status_id,
            ),
        )

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
        kind = data.step_kind or 'eln_experiment'
        mode = data.execution_mode or kind
        if kind == 'eln_experiment':
            if not data.experiment_template_id or not self.repo.template_exists(
                data.experiment_template_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="experiment_template_id is required for eln_experiment steps",
                )
        elif kind == 'lims_run' and not data.analysis_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analysis_id is required for lims_run steps",
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
            analysis_id=getattr(data, 'analysis_id', None),
            sort_order=sort_order,
            name=data.name,
            step_kind=kind,
            execution_mode=mode,
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
    ) -> ELNProcessStepStartResponse:
        """
        Start/materialize a process step (Decision #1 typed steps).

        eln_experiment → create Experiment (+ entries)
        lims_run → lazy create LimsRun (or return current unless force_new)
        """
        process = self.get_process(process_id)
        step = self.repo.get_step_by_id(step_id)
        if not step or step.process_id != process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        extra_sample_ids = list(data.sample_ids) if data and data.sample_ids else []
        kind = getattr(step, 'step_kind', None) or 'eln_experiment'
        force_new = bool(data and data.force_new)
        already_started = (
            (kind == "lims_run" and step.current_lims_run_id and not force_new)
            or (
                kind != "lims_run"
                and step.experiment_id is not None
                and not force_new
                and not extra_sample_ids
            )
        )
        if not already_started:
            from app.services.routing_service import (
                assert_instance_step_accepts_current_type,
            )

            assert_instance_step_accepts_current_type(
                self.db, process, step, extra_sample_ids=extra_sample_ids
            )
        if kind != 'lims_run' and not self.repo.template_exists(step.experiment_template_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment template not found",
            )
        step_label = step.name or f"Step {step.sort_order}"
        default_name = (
            (data.name if data and data.name else None)
            or f"{process.name} — {step_label} ({uuid4().hex[:6]})"
        )

        if kind == 'lims_run':
            analysis_id = getattr(step, 'analysis_id', None)
            if not analysis_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="analysis_id is required to start a lims_run step",
                )
            if step.current_lims_run_id and not force_new:
                return ELNProcessStepStartResponse(
                    step=ELNProcessStepRead.model_validate(step),
                    lims_run_id=step.current_lims_run_id,
                    warning="Step already has a LimsRun; pass force_new=true to retest",
                )
            from app.services.lims_run_service import LimsRunService

            run_svc = LimsRunService(self.db, current_user=self.current_user)
            # LimsRunService always commits; temporarily OK for start-step
            run = run_svc.create_run(
                LimsRunCreate(
                    name=default_name,
                    description=f"From process '{process.name}' step '{step_label}'",
                    experiment_template_id=step.experiment_template_id,
                    analysis_id=analysis_id,
                )
            )
            self.repo.update_step(
                step,
                current_lims_run_id=run.id,
                modified_by=self._user_id(),
            )
            self.repo.add_step_lims_run_history(
                process_step_id=step.id,
                lims_run_id=run.id,
                created_by=self._user_id(),
            )
            self._commit_refresh(step)
            return ELNProcessStepStartResponse(
                step=ELNProcessStepRead.model_validate(step),
                lims_run_id=run.id,
            )

        # eln_experiment
        exp_service = ExperimentService(
            self.db,
            current_user=self.current_user,
            auto_commit=False,
        )
        sample_ids = list(data.sample_ids) if data and data.sample_ids else []
        warning = None

        if step.experiment_id is not None and not force_new:
            experiment_id = step.experiment_id
            experiment = exp_service.get_experiment(
                experiment_id, load_details=False, load_sample_executions=True,
            )
            warning = "Step already has an experiment"
            if not sample_ids:
                self._commit_refresh(step)
                return ELNProcessStepStartResponse(
                    step=ELNProcessStepRead.model_validate(step),
                    experiment_id=experiment_id,
                    warning=warning,
                )
        else:
            experiment = exp_service.create_experiment(
                ExperimentCreate(
                    name=default_name,
                    description=f"From ELN process '{process.name}' step '{step_label}'",
                    experiment_template_id=step.experiment_template_id,
                )
            )
            self.repo.update_step(
                step,
                experiment_id=experiment.id,
                modified_by=self._user_id(),
            )
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
            self.db.flush()
            experiment_id = experiment.id

        linked_count = 0
        process_samples_updated = 0
        if sample_ids:
            # Decision #24: start cohort + process sample status
            start_res = exp_service.start_experiment(
                experiment_id,
                StartExperimentRequest(
                    sample_ids=sample_ids,
                    set_started_at=True,
                ),
            )
            linked_count = start_res.linked_count + start_res.already_linked_count
            process_samples_updated = start_res.process_samples_updated
            warning = None  # successful start with cohort
            step = self.repo.get_step_by_id(step_id)

        self._commit_refresh(step)
        return ELNProcessStepStartResponse(
            step=ELNProcessStepRead.model_validate(step),
            experiment_id=experiment_id,
            linked_count=linked_count,
            process_samples_updated=process_samples_updated,
            warning=warning,
        )

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

    def list_eligible_for_step(
        self,
        process_id: UUID,
        step_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Decision #24: process samples eligible to start this step."""
        self.get_process(process_id)
        step = self.repo.get_step_by_id(step_id)
        if not step or step.process_id != process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process step not found",
            )
        exp_svc = ExperimentService(
            self.db,
            current_user=self.current_user,
            auto_commit=False,
        )
        return exp_svc.list_cohort_eligible_for_process(process_id, step_id=step_id)

    def _contents_for_sample(self, sample_id: UUID) -> List[Contents]:
        return (
            self.db.query(Contents)
            .filter(Contents.sample_id == sample_id)
            .order_by(Contents.container_id)
            .all()
        )

    def _resolve_assignment(
        self, sample_id: UUID, container_id: Optional[UUID] = None
    ) -> ProcessAssignmentItem:
        if not self.repo.sample_exists(sample_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sample {sample_id} not found",
            )
        rows = self._contents_for_sample(sample_id)
        if container_id is not None:
            if not any(row.container_id == container_id for row in rows):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "process_container_required",
                        "message": (
                            "Sample is not in that container; only a sample in a "
                            "container can be assigned to a process"
                        ),
                    },
                )
            return ProcessAssignmentItem(
                sample_id=sample_id, container_id=container_id
            )
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "process_container_required",
                    "message": (
                        "Sample has no container; only a sample in a container "
                        "can be assigned to a process"
                    ),
                },
            )
        if len(rows) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "process_container_required",
                    "message": (
                        "Sample is in more than one container; specify which "
                        "container is in the process"
                    ),
                },
            )
        return ProcessAssignmentItem(
            sample_id=sample_id, container_id=rows[0].container_id
        )

    def assign_samples(
        self,
        process_id: UUID,
        data: ELNProcessSampleAssignRequest,
    ) -> List[ELNProcessSample]:
        """Assign container-with-sample (Contents) to the process queue."""
        self.get_process(process_id)
        steps = self.repo.list_steps(process_id)
        first_step_id = steps[0].id if steps and data.set_to_first_step else None
        items: List[ProcessAssignmentItem] = list(data.assignments or [])
        if data.sample_ids:
            items.extend(
                self._resolve_assignment(sample_id) for sample_id in data.sample_ids
            )
        if not items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "process_container_required",
                    "message": "Provide sample_ids or assignments (sample + container)",
                },
            )
        created: List[ELNProcessSample] = []
        for item in items:
            resolved = self._resolve_assignment(item.sample_id, item.container_id)
            existing = self.repo.get_process_sample(
                process_id, resolved.sample_id
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Sample {resolved.sample_id} is already assigned to this process"
                    ),
                )
            ps = self.repo.create_process_sample(
                process_id=process_id,
                sample_id=resolved.sample_id,
                container_id=resolved.container_id,
                status='queued',
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
            # Moving to a step without starting experiment → still queued
            kwargs['status'] = data.status or 'queued'
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

    def advance_sample(
        self,
        process_id: UUID,
        sample_id: UUID,
        *,
        force: bool = False,
    ) -> ELNProcessSampleAdvanceResponse:
        """
        Finish current step and move sample to the next step (or complete process).

        - After a step: status → **queued** on the next step (waiting for that experiment start)
        - On last step: status → **completed**
        Soft gate (Decision #1f) for lims_run completeness.
        """
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

        warning: Optional[str] = None
        if ps.current_step_id:
            cur = self.repo.get_step_by_id(ps.current_step_id)
            if cur and (getattr(cur, 'step_kind', None) or 'eln_experiment') == 'lims_run':
                if cur.current_lims_run_id:
                    run = self.repo.get_lims_run(cur.current_lims_run_id)
                    status_val = getattr(run.status, 'value', run.status) if run else None
                    if run and status_val not in _RUN_SOFT_GATE_OK:
                        warning = (
                            f"Current LimsRun status is '{status_val}' "
                            f"(not complete/published); advancing anyway (soft gate)"
                        )
                else:
                    warning = "Current lims_run step has no LimsRun started yet; advancing anyway (soft gate)"

        if ps.current_step_id is None:
            # Place on first step as queued (not in_progress until experiment starts)
            self.repo.update_process_sample(
                ps,
                current_step_id=steps[0].id,
                status='queued',
                modified_by=self._user_id(),
            )
        else:
            idx = next((i for i, s in enumerate(steps) if s.id == ps.current_step_id), None)
            if idx is None:
                self.repo.update_process_sample(
                    ps,
                    current_step_id=steps[0].id,
                    status='queued',
                    modified_by=self._user_id(),
                )
            elif idx >= len(steps) - 1:
                self.repo.update_process_sample(
                    ps,
                    status='completed',
                    modified_by=self._user_id(),
                )
            else:
                # Next step: queued until that experiment is started
                self.repo.update_process_sample(
                    ps,
                    current_step_id=steps[idx + 1].id,
                    status='queued',
                    modified_by=self._user_id(),
                )
        self._commit_refresh(ps)
        return ELNProcessSampleAdvanceResponse(
            sample=ELNProcessSampleRead.model_validate(ps),
            warning=warning,
            advanced=True,
        )

    def sample_journey(self, sample_id: UUID) -> SampleJourneyResponse:
        """
        Sample-scoped process progress (Decision #7).
        Caller must ensure sample access (router checks sample visibility).
        """
        if not self.repo.sample_exists(sample_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample not found",
            )
        assignments = self.repo.list_samples_journey(sample_id)
        items: List[SampleJourneyStep] = []
        for a in assignments:
            proc = a.process
            if not proc or not proc.active:
                continue
            cur = None
            if a.current_step_id:
                cur = next((s for s in (proc.steps or []) if s.id == a.current_step_id), None)
            run_status = None
            lims_run_id = cur.current_lims_run_id if cur else None
            if lims_run_id:
                run = self.repo.get_lims_run(lims_run_id)
                if run:
                    run_status = getattr(run.status, 'value', str(run.status))
            items.append(
                SampleJourneyStep(
                    process_id=proc.id,
                    process_name=proc.name,
                    process_definition_id=proc.process_definition_id,
                    process_sample_status=a.status,
                    current_step_id=a.current_step_id,
                    current_step_name=cur.name if cur else None,
                    current_step_kind=getattr(cur, 'step_kind', None) if cur else None,
                    current_step_sort_order=cur.sort_order if cur else None,
                    experiment_id=cur.experiment_id if cur else None,
                    lims_run_id=lims_run_id,
                    lims_run_status=run_status,
                )
            )
        return SampleJourneyResponse(sample_id=sample_id, processes=items)
