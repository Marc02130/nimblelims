"""
Service layer for experiments and experiment templates.

Uses ExperimentRepository for DB access; handles validation, 404/400, commit/rollback.
"""
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
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
    ResolveScanRequest,
    ResolveScanResponse,
    ResolveScanSample,
    StartExperimentRequest,
    StartExperimentResponse,
    ExperimentRead,
)
from models.experiment import ExperimentTemplate, Experiment, ExperimentDetail, ExperimentSampleExecution
from models.container import Container, Contents
from models.sample import Sample
from models.user import User
from models.list import List as ListModel, ListEntry
from models.entry import ELNProcessStep, ELNProcessSample

# Decision #24 — sample must be Available for Testing (list entry name)
AVAILABLE_FOR_TESTING_STATUS_NAME = "Available for Testing"


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

    def _available_for_testing_status_ids(self) -> set:
        """ListEntry ids whose name is Available for Testing (prefer sample_status list)."""
        q = (
            self.db.query(ListEntry.id)
            .join(ListModel, ListModel.id == ListEntry.list_id)
            .filter(ListEntry.name == AVAILABLE_FOR_TESTING_STATUS_NAME)
        )
        ids = {row[0] for row in q.all()}
        return ids

    def _sample_status_name(self, sample: Sample) -> Optional[str]:
        if not sample.status:
            return None
        le = self.db.query(ListEntry).filter(ListEntry.id == sample.status).first()
        return le.name if le else None

    def ensure_available_for_testing(self, sample_id: UUID) -> bool:
        """
        System transition: if sample is Received (or not Available for Testing),
        set status to Available for Testing when queueing for process work.
        Returns True if status was changed.
        """
        sample = self.repo.get_sample_by_id(sample_id)
        if not sample:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
        available_ids = self._available_for_testing_status_ids()
        if not available_ids:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"List entry '{AVAILABLE_FOR_TESTING_STATUS_NAME}' is not configured",
            )
        if sample.status in available_ids:
            return False
        # Prefer canonical Available for Testing from sample_status list
        target = (
            self.db.query(ListEntry)
            .join(ListModel, ListModel.id == ListEntry.list_id)
            .filter(
                ListModel.name == "sample_status",
                ListEntry.name == AVAILABLE_FOR_TESTING_STATUS_NAME,
            )
            .first()
        )
        if not target:
            target_id = next(iter(available_ids))
        else:
            target_id = target.id
        sample.status = target_id
        sample.modified_by = self._user_id()
        self.db.flush()
        return True

    def check_sample_eligibility(
        self,
        sample: Sample,
        *,
        process_id: Optional[UUID] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Decision #24 gates.
        Returns (eligible, reason_if_not).
        """
        available_ids = self._available_for_testing_status_ids()
        if not available_ids:
            return False, (
                f"System list entry '{AVAILABLE_FOR_TESTING_STATUS_NAME}' is not configured"
            )
        if sample.status not in available_ids:
            name = self._sample_status_name(sample) or "unknown"
            return False, (
                f"Sample status must be '{AVAILABLE_FOR_TESTING_STATUS_NAME}' "
                f"(current: {name})"
            )
        if process_id is not None:
            ps = (
                self.db.query(ELNProcessSample)
                .filter(
                    ELNProcessSample.process_id == process_id,
                    ELNProcessSample.sample_id == sample.id,
                )
                .first()
            )
            if not ps or ps.status == "removed":
                return False, "Sample is not assigned to this process"
        return True, None

    def _process_step_for_experiment(self, experiment_id: UUID) -> Optional[ELNProcessStep]:
        return (
            self.db.query(ELNProcessStep)
            .filter(ELNProcessStep.experiment_id == experiment_id)
            .first()
        )

    def _annotate_scan_sample(
        self,
        sample: Sample,
        *,
        container_id: Optional[UUID] = None,
        container_name: Optional[str] = None,
        process_id: Optional[UUID] = None,
    ) -> ResolveScanSample:
        eligible, reason = self.check_sample_eligibility(sample, process_id=process_id)
        return ResolveScanSample(
            sample_id=sample.id,
            client_sample_id=getattr(sample, "client_sample_id", None),
            sample_name=getattr(sample, "name", None),
            container_id=container_id,
            container_name=container_name,
            eligible=eligible,
            ineligible_reason=None if eligible else reason,
        )

    def list_cohort_eligible_for_process(
        self,
        process_id: UUID,
        step_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process samples for start dialog (Decision #24).

        Returns *all* non-removed process samples with eligible/ineligible_reason
        so the UI can show why a sample is not startable (e.g. status Received).
        """
        q = (
            self.db.query(ELNProcessSample, Sample)
            .join(Sample, Sample.id == ELNProcessSample.sample_id)
            .filter(
                ELNProcessSample.process_id == process_id,
                ELNProcessSample.status != "removed",
            )
        )
        rows = q.order_by(ELNProcessSample.assigned_at).all()
        out: List[Dict[str, Any]] = []
        for ps, sample in rows:
            ok, reason = self.check_sample_eligibility(sample, process_id=process_id)
            # Process-sample lifecycle gates for this step
            if ps.status == "completed":
                ok = False
                reason = "Sample already completed on this process"
            elif ps.status == "in_progress":
                if step_id is not None and ps.current_step_id == step_id:
                    ok = False
                    reason = "Sample already in progress on this step"
                elif step_id is not None and ps.current_step_id != step_id:
                    ok = False
                    reason = "Sample is in progress on a different step"
            elif step_id is not None and ps.current_step_id is not None and ps.current_step_id != step_id:
                # Queued for a different step — not for this experiment start
                if ps.status in ("queued", "assigned"):
                    ok = False
                    reason = "Sample is queued for a different process step"
            out.append({
                "sample_id": sample.id,
                "client_sample_id": sample.client_sample_id,
                "sample_name": sample.name,
                "process_sample_status": ps.status if ps.status != "assigned" else "queued",
                "current_step_id": ps.current_step_id,
                "sample_status_name": self._sample_status_name(sample),
                "eligible": ok,
                "ineligible_reason": None if ok else reason,
            })
        return out

    def list_cohort_eligible_ad_hoc(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Ad hoc experiment: Available for Testing samples (no process)."""
        available_ids = self._available_for_testing_status_ids()
        if not available_ids:
            return []
        samples = (
            self.db.query(Sample)
            .filter(Sample.active == True, Sample.status.in_(available_ids))  # noqa: E712
            .order_by(Sample.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "sample_id": s.id,
                "client_sample_id": s.client_sample_id,
                "sample_name": s.name,
                "process_sample_status": None,
                "current_step_id": None,
            }
            for s in samples
        ]

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
            lifecycle_type=data.lifecycle_type,
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
        if data.lifecycle_type is not None:
            update_kwargs["lifecycle_type"] = data.lifecycle_type
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
        # Phase 2: auto-instantiate entries from template_definition['entries']
        if data.experiment_template_id:
            from app.services.entry_service import EntryService
            from app.schemas.entry import InstantiateEntriesRequest

            entry_svc = EntryService(
                self.db,
                current_user=self.current_user,
                auto_commit=False,
            )
            entry_svc.instantiate_from_template(
                e.id,
                InstantiateEntriesRequest(skip_if_exists=True),
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

    def _cohort_locked(self, experiment: Experiment) -> bool:
        """After start, cohort is fixed — no mid-flight sample adds."""
        return experiment.started_at is not None

    def link_sample_to_experiment(
        self,
        experiment_id: UUID,
        data: LinkSampleToExperimentRequest,
    ) -> ExperimentSampleExecution:
        experiment = self.get_experiment(experiment_id, load_details=False, load_sample_executions=False)
        if self._cohort_locked(experiment):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Experiment cohort is locked (already started). "
                    "Cancel/restart or create a new experiment to change samples."
                ),
            )
        from app.services.sample_access import require_accessible_sample

        sample = require_accessible_sample(self.db, data.sample_id)
        process_step = self._process_step_for_experiment(experiment_id)
        process_id = process_step.process_id if process_step else None
        ok, reason = self.check_sample_eligibility(sample, process_id=process_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
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

    def resolve_scan(self, data: ResolveScanRequest) -> ResolveScanResponse:
        """Resolve plate/tube barcode (container name) or client_sample_id to sample list."""
        barcode = (data.barcode or "").strip()
        if not barcode:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="barcode is required")
        process_id = data.process_id

        # Prefer exact container name match (plate → all contents; tube → contents, may be pool)
        container = (
            self.db.query(Container)
            .filter(Container.name == barcode, Container.active == True)  # noqa: E712
            .first()
        )
        if container:
            contents = (
                self.db.query(Contents)
                .filter(Contents.container_id == container.id)
                .all()
            )
            samples_out: List[ResolveScanSample] = []
            seen = set()
            for c in contents:
                if not c.sample_id or c.sample_id in seen:
                    continue
                seen.add(c.sample_id)
                sample = self.repo.get_sample_by_id(c.sample_id)
                if not sample:
                    continue
                samples_out.append(
                    self._annotate_scan_sample(
                        sample,
                        container_id=container.id,
                        container_name=container.name,
                        process_id=process_id,
                    )
                )
            return ResolveScanResponse(
                barcode=barcode,
                match_type='container',
                container_id=container.id,
                container_name=container.name,
                samples=samples_out,
                total=len(samples_out),
                eligible_total=sum(1 for s in samples_out if s.eligible),
            )

        # Fallback: client_sample_id or sample name
        sample = (
            self.db.query(Sample)
            .filter(Sample.client_sample_id == barcode, Sample.active == True)  # noqa: E712
            .first()
        )
        if not sample:
            sample = (
                self.db.query(Sample)
                .filter(Sample.name == barcode, Sample.active == True)  # noqa: E712
                .first()
            )
        if sample:
            row = self._annotate_scan_sample(sample, process_id=process_id)
            return ResolveScanResponse(
                barcode=barcode,
                match_type='sample',
                samples=[row],
                total=1,
                eligible_total=1 if row.eligible else 0,
            )

        return ResolveScanResponse(
            barcode=barcode,
            match_type='none',
            samples=[],
            total=0,
            eligible_total=0,
        )

    def start_experiment(
        self,
        experiment_id: UUID,
        data: StartExperimentRequest,
    ) -> StartExperimentResponse:
        """
        Link selected samples as the experiment cohort and optionally set started_at.
        After start, cohort is fixed (no mid-flight adds via link_sample).
        """
        experiment = self.get_experiment(
            experiment_id, load_details=False, load_sample_executions=True,
        )
        if experiment.completed_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a completed experiment",
            )

        # Deduplicate while preserving order
        seen = set()
        sample_ids: List[UUID] = []
        for sid in data.sample_ids:
            if sid not in seen:
                seen.add(sid)
                sample_ids.append(sid)

        if not sample_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one sample_id is required",
            )

        # If already started with a different cohort, reject mid-flight changes
        existing_execs = experiment.sample_executions or []
        existing_ids = {ex.sample_id for ex in existing_execs if ex.sample_id}
        if self._cohort_locked(experiment) and existing_ids:
            new_set = set(sample_ids)
            if not new_set.issubset(existing_ids) or new_set != existing_ids:
                # Allow re-start only if same set; adding/removing is mid-flight change
                if new_set != existing_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Experiment cohort is locked (already started). "
                            "Cancel/restart or create a new experiment to change samples."
                        ),
                    )

        process_step = self._process_step_for_experiment(experiment_id)
        process_id = process_step.process_id if process_step else None

        from app.services.sample_access import require_accessible_sample

        linked = 0
        already = 0
        for sid in sample_ids:
            # S7: RLS + has_project_access — not merely "row exists"
            sample = require_accessible_sample(self.db, sid)
            ok, reason = self.check_sample_eligibility(sample, process_id=process_id)
            if not ok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sample {sid}: {reason}",
                )
            existing = self.repo.find_execution(
                experiment_id=experiment_id,
                sample_id=sid,
                replicate_number=1,
            )
            if existing:
                already += 1
                continue
            if self._cohort_locked(experiment) and existing_ids:
                # Started with empty cohort edge case: allow first fill only if no samples yet
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Experiment cohort is locked; cannot add samples",
                )
            self.repo.add_sample_execution(
                experiment_id=experiment_id,
                sample_id=sid,
                processing_conditions={},
                replicate_number=1,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            linked += 1

        if data.set_started_at and experiment.started_at is None:
            self.repo.update_experiment(
                experiment,
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                modified_by=self._user_id(),
            )

        # Decision #24: update process sample status for selected cohort
        process_samples_updated = 0
        if process_step is not None:
            for sid in sample_ids:
                ps = (
                    self.db.query(ELNProcessSample)
                    .filter(
                        ELNProcessSample.process_id == process_step.process_id,
                        ELNProcessSample.sample_id == sid,
                    )
                    .first()
                )
                if not ps or ps.status == "removed":
                    continue
                ps.status = "in_progress"
                ps.current_step_id = process_step.id
                ps.modified_by = self._user_id()
                process_samples_updated += 1
            self.db.flush()

        self._commit_refresh(experiment)
        full = self.get_experiment(experiment_id, load_details=True, load_sample_executions=True)
        return StartExperimentResponse(
            experiment=ExperimentRead.model_validate(full),
            linked_count=linked,
            already_linked_count=already,
            cohort_locked=full.started_at is not None,
            process_samples_updated=process_samples_updated,
        )

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
