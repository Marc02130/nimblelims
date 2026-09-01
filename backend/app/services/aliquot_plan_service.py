"""Concrete-method aliquot/pool planning and transactional execution."""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Sequence, Tuple
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from fastapi import HTTPException, status

from app.schemas.aliquot_plan import (
    AliquotMethod,
    AliquotOperation,
    AliquotPlanLine,
    AliquotPlanSaveRequest,
    AliquotPlanSaveResponse,
    ResolvedTransfer,
    AliquotExecuteRequest,
    AliquotExecuteResponse,
    AliquotExecuteLineResult,
    DestSampleTypeOptionsResponse,
    SampleTypeOption,
    METHOD_PROFILES,
)
from app.core.rbac import validate_client_access
from models.entry import (
    ELNProcessSample,
    ELNProcessStep,
    Entry,
    normalize_entry_type,
)
from models.sample import Sample, SampleTypeTransition
from models.container import Container, Contents, ContainerType
from models.project import Project
from models.user import User
from models.list import ListEntry, List as ListModel
from models.experiment import ExperimentSampleExecution
from models.result import Result
from models.test import Test
from models.analysis import Analyte


class AliquotPlanService:
    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.current_user = current_user
        self.auto_commit = auto_commit

    def _user_id(self) -> Optional[UUID]:
        return self.current_user.id if self.current_user else None

    def list_methods(self) -> List[Dict[str, Any]]:
        out = []
        for key, prof in METHOD_PROFILES.items():
            out.append({"method": key, **prof})
        return out

    @staticmethod
    def _method_operation(method: AliquotMethod) -> AliquotOperation:
        return AliquotOperation(METHOD_PROFILES[method.value]["mint_op"])

    @staticmethod
    def _configured_method(entry: Entry) -> AliquotMethod:
        raw = (entry.config or {}).get("method", AliquotMethod.aliquot_by_volume.value)
        try:
            return AliquotMethod(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_aliquot_method",
                    "message": f"Unknown concrete aliquot/pool method: {raw}",
                },
            ) from exc

    def list_dest_sample_types(
        self,
        source_sample_id: UUID,
        operation: AliquotOperation,
    ) -> DestSampleTypeOptionsResponse:
        """List catalog destinations for the source sample's type and operation."""
        source_row = self.db.execute(
            select(Sample, Project.client_id)
            .join(Project, Project.id == Sample.project_id)
            .where(Sample.id == source_sample_id)
        ).first()
        if not source_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source sample not found",
            )

        source, client_id = source_row
        if self.current_user:
            validate_client_access(self.current_user, client_id)

        source_type = self.db.execute(
            select(ListEntry).where(ListEntry.id == source.sample_type)
        ).scalar_one()
        destination_types = (
            self.db.execute(
                select(ListEntry)
                .join(
                    SampleTypeTransition,
                    SampleTypeTransition.allowed_dest_sample_type == ListEntry.id,
                )
                .where(
                    SampleTypeTransition.client_id == client_id,
                    SampleTypeTransition.source_sample_type == source.sample_type,
                    SampleTypeTransition.operation == operation.value,
                    SampleTypeTransition.active.is_(True),
                    ListEntry.active.is_(True),
                )
                .order_by(ListEntry.name.asc())
            )
            .scalars()
            .all()
        )

        return DestSampleTypeOptionsResponse(
            source_sample_type=SampleTypeOption(
                id=source_type.id,
                name=source_type.name,
            ),
            operation=operation,
            options=[
                SampleTypeOption(id=destination.id, name=destination.name)
                for destination in destination_types
            ],
        )

    def _get_plan_entry(self, entry_id: UUID) -> Entry:
        entry = self.db.query(Entry).filter(Entry.id == entry_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
            )
        key = entry.predefined_entry_key
        if key not in (None, "aliquot_pool_plan") and normalize_entry_type(
            entry.entry_type
        ) not in (
            "experiment_data",
            "predefined_action",
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry is not an aliquot/pool plan entry",
            )
        # Allow experiment_data or predefined_action with aliquot key
        if (
            key
            and key != "aliquot_pool_plan"
            and entry.entry_type == "predefined_action"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"predefined_entry_key {key} does not support aliquot execute",
            )
        return entry

    def save_plan(
        self, entry_id: UUID, data: AliquotPlanSaveRequest
    ) -> AliquotPlanSaveResponse:
        entry = self._get_plan_entry(entry_id)
        cfg = dict(entry.config or {})
        existing_lines = cfg.get("plan_lines") or []
        current_method = self._configured_method(entry)
        if existing_lines and data.method != current_method:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "method_change_requires_cancel",
                    "message": (
                        "Method cannot change after plan lines exist. Cancel the "
                        "experiment and create a new plan; minted daughters are not removed."
                    ),
                },
            )
        self._validate_plan_shape(data.method, data.lines)
        self._validate_dest_sample_types(
            data.lines,
            data.method,
            data.default_dest_sample_type,
        )
        lines = []
        for line in data.lines:
            d = line.model_dump(mode="json")
            if not d.get("line_id"):
                d["line_id"] = str(uuid4())
            validated_line = AliquotPlanLine.model_validate(d)
            dest_type = self._resolved_dest_sample_type(
                validated_line,
                data.default_dest_sample_type,
            )
            self.resolve_line(data.method, validated_line, dest_type)
            lines.append(d)
        cfg["method"] = data.method.value
        cfg["default_dest_sample_type"] = (
            str(data.default_dest_sample_type)
            if data.default_dest_sample_type
            else None
        )
        cfg["plan_lines"] = lines
        cfg["plan_updated_at"] = datetime.now(timezone.utc).isoformat()
        entry.config = cfg
        entry.modified_by = self._user_id()
        self.db.flush()
        if self.auto_commit:
            self.db.commit()
            self.db.refresh(entry)
        return AliquotPlanSaveResponse(
            entry_id=entry.id,
            method=data.method,
            default_dest_sample_type=data.default_dest_sample_type,
            lines=[AliquotPlanLine.model_validate(x) for x in lines],
            line_count=len(lines),
        )

    def get_plan(self, entry_id: UUID) -> AliquotPlanSaveResponse:
        entry = self._get_plan_entry(entry_id)
        cfg = entry.config or {}
        raw = cfg.get("plan_lines") or []
        lines = [AliquotPlanLine.model_validate(x) for x in raw]
        default_dest_sample_type = cfg.get("default_dest_sample_type")
        return AliquotPlanSaveResponse(
            entry_id=entry.id,
            method=self._configured_method(entry),
            default_dest_sample_type=default_dest_sample_type,
            lines=lines,
            line_count=len(lines),
        )

    def _prior_concentration_result(self, sample_id: UUID) -> float:
        """Return the newest numeric concentration result recorded for a sample."""
        rows = (
            self.db.query(Result)
            .join(Test, Test.id == Result.test_id)
            .join(Analyte, Analyte.id == Result.analyte_id)
            .filter(
                Test.sample_id == sample_id,
                Result.active.is_(True),
                Analyte.name.ilike("%concentration%"),
            )
            .order_by(Result.entry_date.desc(), Result.created_at.desc())
            .all()
        )
        for result in rows:
            for raw_value in (
                result.calculated_result,
                result.reported_result,
                result.raw_result,
            ):
                if raw_value is None:
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    return value
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "prior_concentration_required",
                "message": (
                    "Normalization requires a prior numeric concentration result "
                    "on the source sample."
                ),
            },
        )

    def resolve_line(
        self,
        method: AliquotMethod,
        line: AliquotPlanLine,
        dest_sample_type: Optional[UUID],
    ) -> ResolvedTransfer:
        """Resolve one transfer using the entry method and tracked source data."""
        warnings: List[str] = []
        amount: Optional[float] = None
        conc: Optional[float] = None
        conc_unit = line.concentration_unit_id
        amount_unit = line.amount_unit_id
        content = self._find_source_content(
            line.source_sample_id,
            line.source_container_id,
        )
        if line.concentration is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "free_text_concentration_not_allowed",
                    "message": (
                        "Source concentration cannot be entered on a plan line; "
                        "use a prior result on the source sample."
                    ),
                },
            )

        volume_methods = {
            AliquotMethod.aliquot_by_volume,
            AliquotMethod.pool_by_volume_per_source,
            AliquotMethod.pool_equal_volume_each,
        }
        target_amount_methods = {
            AliquotMethod.aliquot_by_target_amount,
            AliquotMethod.pool_by_target_amount_per_source,
        }
        if method in volume_methods:
            if line.volume is None:
                raise HTTPException(400, detail=f"{method.value} requires volume")
            if content.concentration is None or float(content.concentration) <= 0:
                raise HTTPException(
                    400,
                    detail=(
                        f"{method.value} requires tracked source concentration "
                        "on container contents"
                    ),
                )
            conc = float(content.concentration)
            conc_unit = content.concentration_units
            amount = float(line.volume) * conc
            warnings.append(
                "Volume converted to tracked amount using source concentration"
            )
        elif method in target_amount_methods:
            if line.target_amount is None:
                raise HTTPException(
                    400, detail=f"{method.value} requires target_amount"
                )
            amount = float(line.target_amount)
        elif method == AliquotMethod.aliquot_by_target_concentration:
            if line.target_concentration is None:
                raise HTTPException(
                    400,
                    detail=(
                        "aliquot_by_target_concentration requires "
                        "target_concentration"
                    ),
                )
            parent_concentration = self._prior_concentration_result(
                line.source_sample_id
            )
            conc = float(line.target_concentration)
            if line.target_amount is not None:
                amount = float(line.target_amount)
            elif line.target_volume is not None:
                amount = float(line.target_volume) * conc
            else:
                raise HTTPException(
                    400,
                    detail=(
                        "aliquot_by_target_concentration requires target_volume "
                        "or target_amount"
                    ),
                )
            warnings.append(
                "Normalization used prior source concentration result "
                f"{parent_concentration:g}"
            )
        elif method == AliquotMethod.aliquot_n_way_equal_split:
            if not line.split_count or line.split_count < 2:
                raise HTTPException(
                    400,
                    detail="aliquot_n_way_equal_split requires split_count of at least 2",
                )
            if content.amount is None:
                raise HTTPException(400, detail="Tracked source amount is required")
            amount = float(content.amount) / line.split_count
        elif method == AliquotMethod.pool_consolidate_remaining:
            if content.amount is None:
                raise HTTPException(400, detail="Tracked source amount is required")
            amount = float(content.amount)
        else:
            raise HTTPException(400, detail=f"Unknown method {method}")

        if amount is None or amount <= 0:
            raise HTTPException(400, detail="Resolved transfer amount must be positive")

        return ResolvedTransfer(
            line_id=line.line_id,
            method=method,
            source_sample_id=line.source_sample_id,
            source_container_id=line.source_container_id,
            transfer_amount=amount,
            amount_unit_id=amount_unit,
            concentration=conc,
            concentration_unit_id=conc_unit or line.concentration_unit_id,
            pool_group=line.pool_group,
            dest_container_id=line.dest_container_id,
            dest_container_type_id=line.dest_container_type_id,
            dest_container_name=line.dest_container_name,
            dest_sample_type=dest_sample_type,
            warnings=warnings,
        )

    def _validate_plan_shape(
        self,
        method: AliquotMethod,
        plan_lines: Sequence[AliquotPlanLine],
    ) -> None:
        """Enforce the entry's single mint operation across every line."""
        operation = self._method_operation(method)
        for line in plan_lines:
            has_pool_group = bool(line.pool_group and line.pool_group.strip())
            if operation == AliquotOperation.pool and not has_pool_group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "pool_group_required",
                        "message": (
                            f"{method.value} is a pool method; every line requires "
                            "a pool group."
                        ),
                    },
                )
            if operation == AliquotOperation.aliquot and has_pool_group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "dual_mint_not_allowed",
                        "message": (
                            f"{method.value} is an aliquot method and cannot contain "
                            "pool lines. Use a separate pool plan entry."
                        ),
                    },
                )

    @staticmethod
    def _resolved_dest_sample_type(
        line: AliquotPlanLine,
        default_dest_sample_type: Optional[UUID],
        source_sample_type: Optional[UUID] = None,
    ) -> Optional[UUID]:
        if line.inherit_entry_dest_sample_type:
            return default_dest_sample_type or source_sample_type
        return line.dest_sample_type or source_sample_type

    def _validate_dest_sample_types(
        self,
        plan_lines: Sequence[AliquotPlanLine],
        method: AliquotMethod,
        default_dest_sample_type: Optional[UUID],
    ) -> None:
        """Validate pool source homogeneity and all non-parent catalog choices."""
        sample_ids = {line.source_sample_id for line in plan_lines}
        source_rows = self.db.execute(
            select(Sample, Project.client_id)
            .join(Project, Project.id == Sample.project_id)
            .where(Sample.id.in_(sample_ids))
        ).all()
        source_data = {
            sample.id: (sample.sample_type, client_id)
            for sample, client_id in source_rows
        }
        missing_ids = sample_ids.difference(source_data)
        if missing_ids:
            missing = sorted(str(sample_id) for sample_id in missing_ids)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "source_sample_not_found",
                    "message": f"Source sample(s) not found: {', '.join(missing)}",
                },
            )

        operation = self._method_operation(method)
        if operation == AliquotOperation.pool:
            pool_types: Dict[str, set] = {}
            for line in plan_lines:
                group = (line.pool_group or "").strip()
                pool_types.setdefault(group, set()).add(
                    source_data[line.source_sample_id][0]
                )
            mixed_groups = sorted(
                group
                for group, sample_types in pool_types.items()
                if len(sample_types) > 1
            )
            if mixed_groups:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "mixed_pool_source_types",
                        "message": (
                            "Each pool must use one source sample type. Mixed types "
                            f"found in pool(s): {', '.join(mixed_groups)}"
                        ),
                        "pool_groups": mixed_groups,
                    },
                )

        for line in plan_lines:
            source_type, client_id = source_data[line.source_sample_id]
            if self.current_user:
                validate_client_access(self.current_user, client_id)
            destination_type = self._resolved_dest_sample_type(
                line,
                default_dest_sample_type,
                source_type,
            )
            if destination_type is None or destination_type == source_type:
                continue
            transition = self.db.execute(
                select(SampleTypeTransition.id).where(
                    SampleTypeTransition.client_id == client_id,
                    SampleTypeTransition.source_sample_type == source_type,
                    SampleTypeTransition.operation == operation.value,
                    SampleTypeTransition.allowed_dest_sample_type == destination_type,
                    SampleTypeTransition.active.is_(True),
                )
            ).scalar_one_or_none()
            if transition is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "dest_sample_type_not_allowed",
                        "message": (
                            "Destination sample type is not allowed for this "
                            f"source sample and {operation.value} operation"
                        ),
                        "line_id": line.line_id,
                    },
                )

    def _experiment_cohort_ids(self, experiment_id: UUID) -> set:
        rows = (
            self.db.query(ExperimentSampleExecution.sample_id)
            .filter(ExperimentSampleExecution.experiment_id == experiment_id)
            .all()
        )
        return {r[0] for r in rows if r[0]}

    def _process_step_for_entry(self, entry: Entry) -> Optional[ELNProcessStep]:
        """Resolve the process step without requiring entry.process_step_id."""
        if entry.process_step_id:
            step = (
                self.db.query(ELNProcessStep)
                .filter(ELNProcessStep.id == entry.process_step_id)
                .first()
            )
            if step:
                return step
        if entry.experiment_id:
            return (
                self.db.query(ELNProcessStep)
                .filter(ELNProcessStep.experiment_id == entry.experiment_id)
                .first()
            )
        return None

    def _active_assignment(
        self,
        process_id: UUID,
        sample_id: UUID,
        container_id: Optional[UUID] = None,
    ) -> Optional[ELNProcessSample]:
        query = self.db.query(ELNProcessSample).filter(
            ELNProcessSample.process_id == process_id,
            ELNProcessSample.sample_id == sample_id,
            ELNProcessSample.status != "removed",
        )
        if container_id is not None:
            query = query.filter(ELNProcessSample.container_id == container_id)
        return query.first()

    def _insert_process_assignment(
        self,
        process_id: UUID,
        sample_id: UUID,
        container_id: UUID,
        current_step_id: Optional[UUID],
    ) -> None:
        existing = (
            self.db.query(ELNProcessSample)
            .filter(
                ELNProcessSample.process_id == process_id,
                ELNProcessSample.container_id == container_id,
            )
            .first()
        )
        if existing:
            existing.sample_id = sample_id
            existing.status = "in_progress"
            existing.current_step_id = current_step_id
            existing.modified_by = self._user_id()
            return
        self.db.add(
            ELNProcessSample(
                process_id=process_id,
                sample_id=sample_id,
                container_id=container_id,
                status="in_progress",
                current_step_id=current_step_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
        )

    def _follow_destination_in_process(
        self,
        entry: Entry,
        source_sample_id: UUID,
        dest_sample_id: UUID,
        source_container_id: Optional[UUID],
        dest_container_id: UUID,
    ) -> None:
        """In the execute txn: dest continues the process; inbound source does not.

        Equivalent aliquot (same sample, new container) retargets container_id.
        Dest mint / pool (new sample) removes the source then inserts the dest pair.
        Does not require entry.process_step_id. PATCH of eln_process_samples is not
        a path.
        """
        if (
            source_sample_id == dest_sample_id
            and source_container_id
            and source_container_id == dest_container_id
        ):
            return
        step = self._process_step_for_entry(entry)
        process_id = step.process_id if step else None
        current_step_id = step.id if step else None
        if process_id is None:
            source_row = (
                self.db.query(ELNProcessSample)
                .filter(
                    ELNProcessSample.sample_id == source_sample_id,
                    ELNProcessSample.status != "removed",
                )
            )
            if source_container_id is not None:
                source_row = source_row.filter(
                    ELNProcessSample.container_id == source_container_id
                )
            assignment = source_row.first()
            if assignment is None:
                return
            process_id = assignment.process_id
            current_step_id = assignment.current_step_id

        if dest_sample_id == source_sample_id:
            active = self._active_assignment(process_id, source_sample_id)
            if active:
                active.container_id = dest_container_id
                active.status = "in_progress"
                if current_step_id:
                    active.current_step_id = current_step_id
                active.modified_by = self._user_id()
                return
            self._insert_process_assignment(
                process_id, dest_sample_id, dest_container_id, current_step_id
            )
            return

        source_row = self._active_assignment(
            process_id, source_sample_id, source_container_id
        )
        if source_row is None:
            source_row = self._active_assignment(process_id, source_sample_id)
        if source_row:
            source_row.status = "removed"
            source_row.current_step_id = None
            source_row.modified_by = self._user_id()
            self.db.flush()
        self._insert_process_assignment(
            process_id, dest_sample_id, dest_container_id, current_step_id
        )

    def _join_minted_destination(
        self, entry: Entry, sample: Sample, container_id: UUID
    ) -> None:
        """Record dest on the experiment cohort and Aliquots / pools list."""
        execution = (
            self.db.query(ExperimentSampleExecution)
            .filter(
                ExperimentSampleExecution.experiment_id == entry.experiment_id,
                ExperimentSampleExecution.sample_id == sample.id,
            )
            .first()
        )
        if not execution:
            self.db.add(
                ExperimentSampleExecution(
                    experiment_id=entry.experiment_id,
                    sample_id=sample.id,
                    processing_conditions={
                        "source": "aliquot_pool_execute",
                        "entry_id": str(entry.id),
                    },
                    created_by=self._user_id(),
                    modified_by=self._user_id(),
                )
            )

        destination_entries = (
            self.db.query(Entry)
            .filter(
                Entry.experiment_id == entry.experiment_id,
                Entry.predefined_entry_key == "aliquots_pools",
                Entry.active.is_(True),
            )
            .all()
        )
        for destination_entry in destination_entries:
            cfg = dict(destination_entry.config or {})
            minted_ids = list(cfg.get("minted_sample_ids") or [])
            sample_id = str(sample.id)
            if sample_id not in minted_ids:
                minted_ids.append(sample_id)
            cfg["minted_sample_ids"] = minted_ids
            cfg["populated_after_execute"] = True
            destination_entry.config = cfg
            destination_entry.modified_by = self._user_id()

    def execute(
        self, entry_id: UUID, data: AliquotExecuteRequest
    ) -> AliquotExecuteResponse:
        """
        Execute aliquot/pool plan.

        S5: one transaction for real execute (any failure rolls back);
        every source_sample_id must be in the experiment cohort;
        null source contents.amount is refused.
        """
        entry = self._get_plan_entry(entry_id)
        method = self._configured_method(entry)
        raw_default_dest_sample_type = (entry.config or {}).get(
            "default_dest_sample_type"
        )
        default_dest_sample_type = (
            UUID(str(raw_default_dest_sample_type))
            if raw_default_dest_sample_type
            else None
        )
        if data.lines is not None:
            plan_lines = data.lines
        else:
            raw = (entry.config or {}).get("plan_lines") or []
            plan_lines = [AliquotPlanLine.model_validate(x) for x in raw]
        if not plan_lines:
            raise HTTPException(400, detail="No plan lines to execute")

        self._validate_plan_shape(method, plan_lines)
        self._validate_dest_sample_types(
            plan_lines,
            method,
            default_dest_sample_type,
        )
        cohort = self._experiment_cohort_ids(entry.experiment_id)
        # S5: all sources must be on the experiment cohort (before mutations)
        for line in plan_lines:
            if line.source_sample_id not in cohort:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "source_not_in_cohort",
                        "message": (
                            f"source_sample_id {line.source_sample_id} is not in the "
                            f"experiment cohort ({entry.experiment_id})"
                        ),
                        "line_id": line.line_id,
                    },
                )

        results: List[AliquotExecuteLineResult] = []
        resolve_errors: List[AliquotExecuteLineResult] = []
        resolved: List[ResolvedTransfer] = []
        for line in plan_lines:
            try:
                source_type = self.db.execute(
                    select(Sample.sample_type).where(Sample.id == line.source_sample_id)
                ).scalar_one()
                dest_type = self._resolved_dest_sample_type(
                    line,
                    default_dest_sample_type,
                    source_type,
                )
                resolved.append(self.resolve_line(method, line, dest_type))
            except HTTPException as e:
                resolve_errors.append(
                    AliquotExecuteLineResult(
                        line_id=line.line_id,
                        source_sample_id=line.source_sample_id,
                        transfer_amount=0,
                        status="error",
                        message=str(e.detail),
                    )
                )

        if data.dry_run:
            results.extend(resolve_errors)
            for r in resolved:
                results.append(
                    AliquotExecuteLineResult(
                        line_id=r.line_id,
                        source_sample_id=r.source_sample_id,
                        transfer_amount=r.transfer_amount,
                        amount_unit_id=r.amount_unit_id,
                        concentration=r.concentration,
                        status="dry_run",
                        message="; ".join(r.warnings) if r.warnings else None,
                    )
                )
            return AliquotExecuteResponse(
                entry_id=entry_id,
                dry_run=True,
                results=results,
                success_count=sum(1 for x in results if x.status == "dry_run"),
                error_count=sum(1 for x in results if x.status == "error"),
            )

        # Real execute: fail closed if any line cannot resolve — no partial commit (S5)
        if resolve_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "aliquot_resolve_failed",
                    "message": "One or more plan lines failed to resolve; nothing executed",
                    "errors": [x.model_dump(mode="json") for x in resolve_errors],
                },
            )

        if not self._user_id():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "auth_required",
                    "message": "Authenticated user required to execute aliquot plan",
                },
            )

        pool_containers: Dict[str, UUID] = {}
        try:
            for r in resolved:
                dest_sample, dest_c = self._execute_transfer(r, pool_containers)
                if dest_sample is not None and dest_c is not None:
                    self._join_minted_destination(entry, dest_sample, dest_c.id)
                    self._follow_destination_in_process(
                        entry,
                        r.source_sample_id,
                        dest_sample.id,
                        r.source_container_id,
                        dest_c.id,
                    )
                results.append(
                    AliquotExecuteLineResult(
                        line_id=r.line_id,
                        source_sample_id=r.source_sample_id,
                        dest_sample_id=dest_sample.id if dest_sample else None,
                        dest_container_id=dest_c.id if dest_c else None,
                        transfer_amount=r.transfer_amount,
                        amount_unit_id=r.amount_unit_id,
                        concentration=r.concentration,
                        status="ok",
                        message="; ".join(r.warnings) if r.warnings else None,
                    )
                )

            cfg = dict(entry.config or {})
            cfg["last_execute_at"] = datetime.now(timezone.utc).isoformat()
            cfg["last_execute_results"] = [x.model_dump(mode="json") for x in results]
            cfg["executed_method"] = method.value
            entry.config = cfg
            entry.modified_by = self._user_id()
            self.db.flush()
            if self.auto_commit:
                self.db.commit()
        except HTTPException:
            self.db.rollback()
            raise
        except (IntegrityError, ProgrammingError, DBAPIError) as e:
            self.db.rollback()
            orig = str(getattr(e, "orig", e)).lower()
            if (
                "row-level security" in orig
                or "insufficient_privilege" in orig
                or "permission denied" in orig
            ):
                # Sec9: never surface RLS as 500
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "rls_denied",
                        "message": (
                            "Database policy denied creating aliquot destination "
                            "(containers/samples). Ensure created_by is set and "
                            "project access is valid."
                        ),
                    },
                ) from e
            raise
        except Exception:
            self.db.rollback()
            raise

        return AliquotExecuteResponse(
            entry_id=entry_id,
            dry_run=False,
            results=results,
            success_count=sum(1 for x in results if x.status == "ok"),
            error_count=sum(1 for x in results if x.status == "error"),
        )

    def _find_source_content(
        self,
        sample_id: UUID,
        container_id: Optional[UUID],
    ) -> Contents:
        q = self.db.query(Contents).filter(Contents.sample_id == sample_id)
        if container_id:
            q = q.filter(Contents.container_id == container_id)
        content = q.first()
        if not content:
            raise HTTPException(
                400,
                detail=f"No container contents for sample {sample_id}"
                + (f" in container {container_id}" if container_id else ""),
            )
        return content

    def _available_status_id(self) -> UUID:
        sample_status_list = (
            self.db.query(ListModel).filter(ListModel.name == "sample_status").first()
        )
        if sample_status_list:
            available = (
                self.db.query(ListEntry)
                .filter(
                    ListEntry.list_id == sample_status_list.id,
                    ListEntry.name == "Available for Testing",
                )
                .first()
            )
            if available:
                return available.id
        # Fallback: any list entry named Available for Testing
        available = (
            self.db.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        if available:
            return available.id
        raise HTTPException(
            400,
            detail="Sample status 'Available for Testing' not found in configuration",
        )

    def _execute_transfer(
        self,
        r: ResolvedTransfer,
        pool_containers: Dict[str, UUID],
    ) -> Tuple[Sample, Container]:
        parent = self.db.query(Sample).filter(Sample.id == r.source_sample_id).first()
        if not parent:
            raise HTTPException(
                404, detail=f"Source sample {r.source_sample_id} not found"
            )

        content = self._find_source_content(r.source_sample_id, r.source_container_id)
        # S5: refuse null source amount (no silent create-dest-without-debit)
        if content.amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "source_amount_null",
                    "message": (
                        f"Source contents amount is null for sample {r.source_sample_id}; "
                        "set a tracked amount before execute"
                    ),
                },
            )
        current = float(content.amount)
        if r.transfer_amount > current:
            raise HTTPException(
                400,
                detail=(
                    f"Insufficient amount on source contents: have {current}, "
                    f"need {r.transfer_amount}"
                ),
            )
        content.amount = Decimal(str(current - r.transfer_amount))

        # Destination container
        dest_c: Optional[Container] = None
        if r.pool_group and r.pool_group in pool_containers:
            dest_c = (
                self.db.query(Container)
                .filter(Container.id == pool_containers[r.pool_group])
                .first()
            )
        elif r.dest_container_id:
            dest_c = (
                self.db.query(Container)
                .filter(
                    Container.id == r.dest_container_id,
                    Container.active == True,  # noqa: E712
                )
                .first()
            )
            if not dest_c:
                raise HTTPException(400, detail="dest_container_id not found")
        else:
            type_id = r.dest_container_type_id
            if not type_id:
                # default to source container type
                src_c = (
                    self.db.query(Container)
                    .filter(Container.id == content.container_id)
                    .first()
                )
                type_id = src_c.type_id if src_c else None
            if not type_id:
                raise HTTPException(
                    400,
                    detail="dest_container_type_id required when dest_container_id omitted",
                )
            name = r.dest_container_name or f"ALIQUOT-{uuid4().hex[:8]}"
            dest_c = Container(
                name=name,
                type_id=type_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            self.db.add(dest_c)
            self.db.flush()

        if r.pool_group and r.pool_group not in pool_containers:
            pool_containers[r.pool_group] = dest_c.id

        equivalent = (
            self._method_operation(r.method) == AliquotOperation.aliquot
            and (
                r.dest_sample_type is None
                or r.dest_sample_type == parent.sample_type
            )
        )
        if equivalent:
            dest_sample = parent
        else:
            # Dest mint / pool: new sample row. Dest-type Hold is a different punch.
            status_id = self._available_status_id()
            dest_sample = Sample(
                name=(
                    f"{parent.name}-ALQ-{uuid4().hex[:6]}"
                    if parent.name
                    else f"ALQ-{uuid4().hex[:8]}"
                ),
                description=(
                    f"Aliquot from {parent.name or parent.id} ({r.method.value})"
                ),
                sample_type=r.dest_sample_type or parent.sample_type,
                status=status_id,
                matrix=parent.matrix,
                temperature=parent.temperature,
                parent_sample_id=parent.id,
                project_id=parent.project_id,
                qc_type=parent.qc_type,
                due_date=parent.due_date,
                received_date=parent.received_date,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            self.db.add(dest_sample)
            self.db.flush()

        # Dest contents amount = transfer (mass/count); conc from plan when present
        dest_amount = Decimal(str(r.transfer_amount))
        dest_conc = (
            Decimal(str(r.concentration))
            if r.concentration is not None
            else content.concentration
        )
        dest_conc_units = r.concentration_unit_id or content.concentration_units
        amount_units = r.amount_unit_id or content.amount_units

        # If pool already has this sample, sum amount
        existing_dest = (
            self.db.query(Contents)
            .filter(
                Contents.container_id == dest_c.id,
                Contents.sample_id == dest_sample.id,
            )
            .first()
        )
        if existing_dest:
            if existing_dest.amount is not None:
                existing_dest.amount = Decimal(
                    str(float(existing_dest.amount) + float(dest_amount))
                )
            else:
                existing_dest.amount = dest_amount
        else:
            self.db.add(
                Contents(
                    container_id=dest_c.id,
                    sample_id=dest_sample.id,
                    amount=dest_amount,
                    amount_units=amount_units,
                    concentration=dest_conc,
                    concentration_units=dest_conc_units,
                )
            )
        self.db.flush()
        return dest_sample, dest_c
