"""P2 routing map and Route → work_order."""
from __future__ import annotations

import logging
from typing import List, Optional, Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from psycopg2.extras import NumericRange
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.services.asked_for_service import AskedForService, deny_client_write
from models.entry import ELNProcessDefinition, ELNProcessDefinitionStep
from models.experiment import ExperimentTemplate
from models.sample import Sample
from models.user import User
from models.work_order import RoutingMap, StepAcceptedSampleType, WorkOrder

logger = logging.getLogger(__name__)

ROUTE_SAMPLE_TYPE = "route_sample_type"


def _type_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": ROUTE_SAMPLE_TYPE, "message": message},
    )


def assert_instance_step_accepts_current_type(
    db: Session,
    process,
    instance_step,
    extra_sample_ids: Optional[Sequence[UUID]] = None,
) -> None:
    """Gate a process-step start against that step's accepted types.

    Work-order instances fail closed on an empty allow-list. Free-form
    processes without accepted types stay ungated.
    """
    from models.entry import ELNProcessSample

    def_id = getattr(process, "process_definition_id", None)
    wo_linked = getattr(process, "work_order_id", None)
    if not def_id:
        if wo_linked:
            raise _type_error("Process instance has no definition to type-gate")
        return
    def_step = (
        db.query(ELNProcessDefinitionStep)
        .filter(
            ELNProcessDefinitionStep.process_definition_id == def_id,
            ELNProcessDefinitionStep.sort_order == instance_step.sort_order,
        )
        .first()
    )
    if not def_step:
        if wo_linked:
            raise _type_error("Process step has no matching definition step")
        return
    types = [
        r.sample_type_id
        for r in db.query(StepAcceptedSampleType).filter(
            StepAcceptedSampleType.step_id == def_step.id
        )
    ]
    if not types:
        if wo_linked:
            raise _type_error(
                "Step has no accepted sample types; empty allow-list fails closed"
            )
        return
    sample_ids = set()
    for assignment in (
        db.query(ELNProcessSample)
        .filter(ELNProcessSample.process_id == process.id)
        .all()
    ):
        if assignment.status == "removed":
            continue
        sample_ids.add(assignment.sample_id)
    for sid in extra_sample_ids or []:
        sample_ids.add(sid)
    for sid in sample_ids:
        sample = db.query(Sample).filter(Sample.id == sid).first()
        if sample is None:
            continue
        if sample.sample_type not in types:
            raise _type_error(
                "Sample type is not accepted on this process step"
            )


def _range(tat_min: int, tat_max: int) -> NumericRange:
    return NumericRange(tat_min, tat_max, "[]")


def _range_bounds(value) -> tuple[int, int]:
    lower = int(value.lower) if value.lower is not None else 1
    upper = int(value.upper) if value.upper is not None else lower
    # psycopg2 may return exclusive upper
    if value.upper is not None and not value.upper_inc:
        upper = upper - 1
    return lower, upper


class RoutingService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.user = current_user
        self.asked_for = AskedForService(db, current_user)

    def list_maps(
        self,
        analysis_id: Optional[UUID] = None,
        sample_type_id: Optional[UUID] = None,
        active_only: bool = True,
    ) -> List[RoutingMap]:
        q = self.db.query(RoutingMap)
        if sample_type_id is not None:
            q = q.filter(RoutingMap.sample_type_id == sample_type_id)
        if active_only:
            q = q.filter(RoutingMap.active == True)  # noqa: E712
        rows = q.order_by(RoutingMap.created_at.desc()).all()
        if analysis_id is None:
            return rows
        return [
            row
            for row in rows
            if analysis_id in self._chain_lims_analysis_ids(
                list(row.process_definition_ids or [])
            )
        ]

    def create_map(
        self,
        tat_min: int,
        tat_max: int,
        process_definition_ids: Sequence[UUID],
        active: bool = True,
        analysis_id: Optional[UUID] = None,
    ) -> List[RoutingMap]:
        """A route is an ordered process list. analysis_id is ignored."""
        chain = list(process_definition_ids)
        self._require_definitions(chain)
        types = self._require_first_step_types(chain)
        analyses = self._require_chain_analyses(chain)
        self._assert_chain_handoffs(chain)
        self._refuse_map_overlap(chain, types, analyses, tat_min, tat_max)
        hint = analyses[0]
        created: List[RoutingMap] = []
        for sid in types:
            row = RoutingMap(
                analysis_id=hint,
                sample_type_id=sid,
                tat_range=_range(tat_min, tat_max),
                process_definition_ids=chain,
                active=active,
                created_by=self.user.id,
                modified_by=self.user.id,
            )
            self.db.add(row)
            created.append(row)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.info("Routing map overlap: %s", e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Overlapping TAT, first-step sample types, and LIMS Run "
                    "analyses"
                ),
            ) from e
        for row in created:
            self.db.refresh(row)
        return created

    def update_map(
        self,
        map_id: UUID,
        *,
        tat_min: Optional[int] = None,
        tat_max: Optional[int] = None,
        process_definition_ids: Optional[Sequence[UUID]] = None,
        active: Optional[bool] = None,
    ) -> RoutingMap:
        row = self.db.query(RoutingMap).filter(RoutingMap.id == map_id).first()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing map row not found")
        lo, hi = _range_bounds(row.tat_range)
        if tat_min is not None:
            lo = tat_min
        if tat_max is not None:
            hi = tat_max
        if hi < lo:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "tat_max must be >= tat_min",
            )
        chain = list(process_definition_ids) if process_definition_ids is not None else list(
            row.process_definition_ids or []
        )
        if process_definition_ids is not None:
            self._require_definitions(chain)
        types = self._require_first_step_types(chain)
        analyses = self._require_chain_analyses(chain)
        self._assert_chain_handoffs(chain)
        exclude_ids = {
            m.id
            for m in self.db.query(RoutingMap).all()
            if tuple(m.process_definition_ids or [])
            == tuple(row.process_definition_ids or [])
            and _range_bounds(m.tat_range) == _range_bounds(row.tat_range)
        }
        self._refuse_map_overlap(
            chain, types, analyses, lo, hi, exclude_ids=exclude_ids
        )
        row.tat_range = _range(lo, hi)
        row.process_definition_ids = chain
        row.analysis_id = analyses[0]
        if active is not None:
            row.active = active
        row.modified_by = self.user.id
        try:
            self.db.flush()
            if chain:
                self._sync_maps_for_first_process(chain[0])
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Overlapping TAT, first-step sample types, and LIMS Run "
                    "analyses"
                ),
            ) from e
        refreshed = self.db.query(RoutingMap).filter(RoutingMap.id == map_id).first()
        return refreshed or row

    def delete_map(self, map_id: UUID) -> None:
        row = self.db.query(RoutingMap).filter(RoutingMap.id == map_id).first()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing map row not found")
        self.db.delete(row)
        self.db.commit()

    def list_step_accepted_types(self, step_id: UUID) -> List[UUID]:
        rows = (
            self.db.query(StepAcceptedSampleType)
            .filter(StepAcceptedSampleType.step_id == step_id)
            .all()
        )
        return [r.sample_type_id for r in rows]

    def replace_step_accepted_types(
        self,
        step_id: UUID,
        sample_type_ids: Sequence[UUID],
        definition_id: Optional[UUID] = None,
    ) -> List[UUID]:
        step = (
            self.db.query(ELNProcessDefinitionStep)
            .filter(ELNProcessDefinitionStep.id == step_id)
            .first()
        )
        if not step:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Process definition step not found")
        if definition_id is not None and step.process_definition_id != definition_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Process definition step not found")
        existing = (
            self.db.query(StepAcceptedSampleType)
            .filter(StepAcceptedSampleType.step_id == step_id)
            .all()
        )
        for row in existing:
            self.db.delete(row)
        self.db.flush()
        seen = set()
        for sid in sample_type_ids:
            if sid in seen:
                continue
            seen.add(sid)
            self.db.add(
                StepAcceptedSampleType(step_id=step_id, sample_type_id=sid)
            )
        self.db.flush()
        try:
            if self._is_first_typed_step(step):
                self._sync_maps_for_first_process(step.process_definition_id)
            self.db.commit()
        except HTTPException:
            self.db.rollback()
            raise
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Overlapping TAT, first-step sample types, and LIMS Run "
                    "analyses"
                ),
            ) from e
        return list(seen)

    def _first_typed_step(
        self, process_definition_id: UUID
    ) -> Optional[ELNProcessDefinitionStep]:
        steps = (
            self.db.query(ELNProcessDefinitionStep)
            .filter(ELNProcessDefinitionStep.process_definition_id == process_definition_id)
            .order_by(ELNProcessDefinitionStep.sort_order.asc())
            .all()
        )
        if not steps:
            return None
        for step in steps:
            if (step.step_kind or "") in ("eln_experiment", "lims_run"):
                return step
        return steps[0]

    def _is_first_typed_step(self, step: ELNProcessDefinitionStep) -> bool:
        first = self._first_typed_step(step.process_definition_id)
        return first is not None and first.id == step.id

    def _typed_steps(
        self, process_definition_id: UUID
    ) -> List[ELNProcessDefinitionStep]:
        steps = (
            self.db.query(ELNProcessDefinitionStep)
            .filter(
                ELNProcessDefinitionStep.process_definition_id
                == process_definition_id
            )
            .order_by(ELNProcessDefinitionStep.sort_order.asc())
            .all()
        )
        typed = [
            s
            for s in steps
            if (s.step_kind or "") in ("eln_experiment", "lims_run")
        ]
        return typed or list(steps)

    def _dest_types_from_step(
        self, step: ELNProcessDefinitionStep
    ) -> List[UUID]:
        tid = getattr(step, "experiment_template_id", None)
        if not tid:
            return []
        tpl = (
            self.db.query(ExperimentTemplate)
            .filter(ExperimentTemplate.id == tid)
            .first()
        )
        if not tpl:
            return []
        entries = (tpl.template_definition or {}).get("entries") or []
        dests: List[UUID] = []
        seen = set()
        for entry in entries:
            cfg = entry.get("config") or {}
            raw = cfg.get("default_dest_sample_type")
            if not raw:
                continue
            try:
                dest = raw if isinstance(raw, UUID) else UUID(str(raw))
            except (ValueError, TypeError, AttributeError):
                continue
            if dest not in seen:
                seen.add(dest)
                dests.append(dest)
        return dests

    def emerging_types_for_process(
        self, process_definition_id: UUID
    ) -> List[UUID]:
        """Type(s) that leave this process: aliquot/pool dest on the last
        experiment/LIMS Run, else that last step's accepted types."""
        steps = self._typed_steps(process_definition_id)
        if not steps:
            return []
        last = steps[-1]
        dest = self._dest_types_from_step(last)
        if dest:
            return dest
        return self.list_step_accepted_types(last.id)

    def _assert_chain_handoffs(self, chain: Sequence[UUID]) -> None:
        for idx in range(len(chain) - 1):
            emerging = self.emerging_types_for_process(chain[idx])
            next_step = self._first_typed_step(chain[idx + 1])
            next_types = (
                self.list_step_accepted_types(next_step.id) if next_step else []
            )
            if not emerging:
                raise _type_error(
                    f"Process {idx + 1} last experiment/LIMS Run has no "
                    "emerging sample type (set aliquot/pool dest or accepted types)"
                )
            if not next_types:
                raise _type_error(
                    f"Process {idx + 2} first experiment/LIMS Run has no "
                    "accepted sample types"
                )
            missing = [t for t in emerging if t not in next_types]
            if missing:
                raise _type_error(
                    f"Sample type emerging from process {idx + 1} is not "
                    f"accepted by process {idx + 2}"
                )

    def _require_first_step_types(self, chain: Sequence[UUID]) -> List[UUID]:
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": ROUTE_SAMPLE_TYPE,
                    "message": "Process definition has no experiment or LIMS Run step",
                },
            )
        step = self._first_typed_step(chain[0])
        if step is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": ROUTE_SAMPLE_TYPE,
                    "message": "Process definition has no experiment or LIMS Run step",
                },
            )
        types = self.list_step_accepted_types(step.id)
        if not types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": ROUTE_SAMPLE_TYPE,
                    "message": (
                        "First experiment/LIMS Run has no accepted sample types"
                    ),
                },
            )
        return types

    def _assert_sample_matches_first_step(
        self, chain: Sequence[UUID], sample_type_id: UUID
    ) -> None:
        types = self._require_first_step_types(chain)
        if sample_type_id not in types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": ROUTE_SAMPLE_TYPE,
                    "message": (
                        "Sample type is not accepted on the first experiment/"
                        "LIMS Run of the first process"
                    ),
                },
            )

    def _chain_lims_analysis_ids(self, chain: Sequence[UUID]) -> List[UUID]:
        if not chain:
            return []
        steps = (
            self.db.query(ELNProcessDefinitionStep)
            .filter(ELNProcessDefinitionStep.process_definition_id.in_(list(chain)))
            .all()
        )
        by_def: dict = {}
        for step in steps:
            by_def.setdefault(step.process_definition_id, []).append(step)
        ids: List[UUID] = []
        seen = set()
        for def_id in chain:
            ordered = sorted(
                by_def.get(def_id, []), key=lambda s: s.sort_order or 0
            )
            for step in ordered:
                if (step.step_kind or "") != "lims_run":
                    continue
                aid = getattr(step, "analysis_id", None)
                if aid and aid not in seen:
                    seen.add(aid)
                    ids.append(aid)
        return ids

    def _require_chain_analyses(self, chain: Sequence[UUID]) -> List[UUID]:
        ids = self._chain_lims_analysis_ids(chain)
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": ROUTE_SAMPLE_TYPE,
                    "message": "Route has no LIMS Run analysis",
                },
            )
        return ids

    def _sync_maps_for_first_process(self, process_definition_id: UUID) -> None:
        """Keep routing_map.sample_type_id in line with the first typed step."""
        step = self._first_typed_step(process_definition_id)
        desired = (
            list(dict.fromkeys(self.list_step_accepted_types(step.id)))
            if step
            else []
        )
        maps = [
            m
            for m in self.db.query(RoutingMap).all()
            if (m.process_definition_ids or [None])[0] == process_definition_id
        ]
        groups: dict[tuple, list] = {}
        for row in maps:
            lo, hi = _range_bounds(row.tat_range)
            key = (
                lo,
                hi,
                tuple(row.process_definition_ids or []),
                row.active,
            )
            groups.setdefault(key, []).append(row)
        for (lo, hi, chain, active), group in groups.items():
            existing = {m.sample_type_id: m for m in group}
            for sid, row in existing.items():
                if sid not in desired:
                    self.db.delete(row)
            self.db.flush()
            owner = group[0]
            analyses = self._chain_lims_analysis_ids(chain)
            hint = analyses[0] if analyses else owner.analysis_id
            group_ids = {m.id for m in group}
            for sid in desired:
                if sid in existing:
                    continue
                if self._map_conflicts(
                    list(chain),
                    desired,
                    analyses,
                    lo,
                    hi,
                    exclude_ids=group_ids,
                ):
                    continue
                self.db.add(
                    RoutingMap(
                        analysis_id=hint,
                        sample_type_id=sid,
                        tat_range=_range(lo, hi),
                        process_definition_ids=list(chain),
                        active=active,
                        created_by=owner.created_by,
                        modified_by=self.user.id,
                    )
                )
        self.db.flush()

    def find_map(
        self, analysis_id: UUID, sample_type_id: UUID, tat_days: int
    ) -> Optional[RoutingMap]:
        acceptable = self._acceptable_maps(analysis_id, sample_type_id, tat_days)
        return acceptable[0] if len(acceptable) == 1 else None

    def _tat_candidates(self, tat_days: int) -> List[RoutingMap]:
        return (
            self.db.query(RoutingMap)
            .filter(
                RoutingMap.active == True,  # noqa: E712
                RoutingMap.tat_range.op("@>")(tat_days),
            )
            .all()
        )

    def _unique_logical_maps(self, rows: Sequence[RoutingMap]) -> List[RoutingMap]:
        seen: dict[tuple, RoutingMap] = {}
        for row in rows:
            lo, hi = _range_bounds(row.tat_range)
            key = (lo, hi, tuple(row.process_definition_ids or []))
            seen.setdefault(key, row)
        return list(seen.values())

    def _acceptable_maps(
        self, analysis_id: UUID, sample_type_id: UUID, tat_days: int
    ) -> List[RoutingMap]:
        unique = self._unique_logical_maps(self._tat_candidates(tat_days))
        acceptable: List[RoutingMap] = []
        for row in unique:
            chain = list(row.process_definition_ids or [])
            try:
                types = self._require_first_step_types(chain)
                analyses = self._require_chain_analyses(chain)
            except HTTPException:
                continue
            if sample_type_id in types and analysis_id in analyses:
                acceptable.append(row)
        return acceptable

    def _map_conflicts(
        self,
        chain: Sequence[UUID],
        types: Sequence[UUID],
        analyses: Sequence[UUID],
        tat_min: int,
        tat_max: int,
        exclude_ids: Optional[set] = None,
    ) -> bool:
        exclude_ids = exclude_ids or set()
        proposed_types = set(types)
        proposed_analyses = set(analyses)
        unique = self._unique_logical_maps(
            [
                m
                for m in self.db.query(RoutingMap)
                .filter(RoutingMap.active == True)  # noqa: E712
                .all()
                if m.id not in exclude_ids
            ]
        )
        for other in unique:
            if other.id in exclude_ids:
                continue
            olo, ohi = _range_bounds(other.tat_range)
            if ohi < tat_min or olo > tat_max:
                continue
            other_chain = list(other.process_definition_ids or [])
            try:
                other_types = set(self._require_first_step_types(other_chain))
                other_analyses = set(self._chain_lims_analysis_ids(other_chain))
            except HTTPException:
                continue
            if proposed_types & other_types and proposed_analyses & other_analyses:
                return True
        return False

    def _refuse_map_overlap(
        self,
        chain: Sequence[UUID],
        types: Sequence[UUID],
        analyses: Sequence[UUID],
        tat_min: int,
        tat_max: int,
        exclude_ids: Optional[set] = None,
    ) -> None:
        if self._map_conflicts(
            chain, types, analyses, tat_min, tat_max, exclude_ids=exclude_ids
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Overlapping TAT, first-step sample types, and LIMS Run "
                    "analyses"
                ),
            )

    def route_one(self, asked_for_id: UUID) -> dict:
        deny_client_write(self.user)
        row = self.asked_for.get(asked_for_id)
        self.asked_for._require_visible_sample(row.sample_id)
        if row.status == "cancelled":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Cannot route a cancelled asked-for",
            )
        if row.status == "routed" and row.routed_work_order_id:
            wo = (
                self.db.query(WorkOrder)
                .options(joinedload(WorkOrder.sample), joinedload(WorkOrder.analysis))
                .filter(WorkOrder.id == row.routed_work_order_id)
                .first()
            )
            return {"asked_for_id": row.id, "work_order": wo, "no_route": False}

        sample = self.db.query(Sample).filter(Sample.id == row.sample_id).first()
        if not sample:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Access denied: insufficient project permissions",
            )
        acceptable = self._acceptable_maps(
            row.analysis_id, sample.sample_type, row.tat_days
        )
        if not acceptable:
            raise _type_error(
                "No routing-map row accepts this analysis, TAT, and sample type"
            )
        if len(acceptable) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Two routing-map rows accept this analysis and sample type",
            )
        match = acceptable[0]
        chain = list(match.process_definition_ids or [])
        self._assert_sample_matches_first_step(chain, sample.sample_type)

        wo = WorkOrder(
            asked_for_id=row.id,
            sample_id=row.sample_id,
            analysis_id=row.analysis_id,
            process_definition_ids=chain,
            status="queued",
            created_by=self.user.id,
            modified_by=self.user.id,
        )
        self.db.add(wo)
        self.db.flush()
        row.status = "routed"
        row.routed_work_order_id = wo.id
        row.modified_by = self.user.id
        self.db.commit()
        wo = (
            self.db.query(WorkOrder)
            .options(joinedload(WorkOrder.sample), joinedload(WorkOrder.analysis))
            .filter(WorkOrder.id == wo.id)
            .first()
        )
        return {"asked_for_id": row.id, "work_order": wo, "no_route": False}

    def route_many(self, asked_for_ids: Sequence[UUID]) -> List[dict]:
        return [self.route_one(aid) for aid in asked_for_ids]

    def list_work_orders(
        self,
        status_filter: Optional[str] = None,
        sample_id: Optional[UUID] = None,
    ) -> List[WorkOrder]:
        q = self.db.query(WorkOrder).options(
            joinedload(WorkOrder.sample), joinedload(WorkOrder.analysis)
        )
        if status_filter:
            q = q.filter(WorkOrder.status == status_filter)
        if sample_id:
            q = q.filter(WorkOrder.sample_id == sample_id)
        return q.order_by(WorkOrder.created_at.desc()).all()

    def _started_processes(self, work_order_ids: Sequence[UUID]):
        from models.entry import ELNProcess

        if not work_order_ids:
            return {}
        rows = (
            self.db.query(ELNProcess)
            .filter(ELNProcess.work_order_id.in_(list(work_order_ids)))
            .all()
        )
        grouped: dict = {}
        for process in rows:
            grouped.setdefault(process.work_order_id, []).append(process)
        for items in grouped.values():
            items.sort(
                key=lambda p: (
                    p.work_order_route_position is None,
                    p.work_order_route_position or 0,
                )
            )
        return grouped

    def _continuing_assignments(self, process) -> List[dict]:
        """Container-with-sample still on the process after aliquot/pool mint."""
        from models.entry import ELNProcessSample

        rows = (
            self.db.query(ELNProcessSample)
            .filter(
                ELNProcessSample.process_id == process.id,
                ELNProcessSample.status != "removed",
            )
            .all()
        )
        return [
            {"sample_id": row.sample_id, "container_id": row.container_id}
            for row in rows
        ]

    def _assignment_for_sample(self, sample_id: UUID) -> dict:
        from models.container import Contents

        rows = (
            self.db.query(Contents)
            .filter(Contents.sample_id == sample_id)
            .order_by(Contents.container_id)
            .all()
        )
        if not rows:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
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
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "process_container_required",
                    "message": (
                        "Sample is in more than one container; specify which "
                        "container is in the process"
                    ),
                },
            )
        return {"sample_id": sample_id, "container_id": rows[0].container_id}

    def start_work_order(self, work_order_id: UUID):
        """Instantiate the next pending process in snapshot order."""
        deny_client_write(self.user)
        wo = (
            self.db.query(WorkOrder)
            .options(joinedload(WorkOrder.sample), joinedload(WorkOrder.analysis))
            .filter(WorkOrder.id == work_order_id)
            .first()
        )
        if not wo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Work order not found")
        self.asked_for._require_visible_sample(wo.sample_id)
        if wo.status not in ("queued", "in_progress"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Only queued or in-progress work orders can be started",
            )
        chain = list(wo.process_definition_ids or [])
        if not chain:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Work order has an empty process chain",
            )
        started = self._started_processes([wo.id]).get(wo.id, [])
        started_defs = {
            p.process_definition_id for p in started if p.process_definition_id
        }
        next_idx = next(
            (i for i, def_id in enumerate(chain) if def_id not in started_defs),
            None,
        )
        if next_idx is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "All processes in the route have been started",
            )
        assignments = (
            self._continuing_assignments(started[-1]) if started else []
        )
        if not assignments:
            assignments = [self._assignment_for_sample(wo.sample_id)]
        for item in assignments:
            sample = (
                self.db.query(Sample).filter(Sample.id == item["sample_id"]).first()
            )
            sample_type_id = getattr(sample, "sample_type", None) if sample else None
            if sample_type_id is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Work order sample has no sample type",
                )
            self._assert_sample_matches_first_step([chain[next_idx]], sample_type_id)
        from app.schemas.eln_process_definition import InstantiateProcessFromDefinitionRequest
        from app.schemas.eln_process import ProcessAssignmentItem
        from app.services.eln_process_service import ELNProcessService

        sample_name = getattr(wo.sample, "name", None) or "sample"
        analysis_name = getattr(wo.analysis, "name", None) or "analysis"
        position = next_idx + 1
        inst = ELNProcessService(self.db, current_user=self.user).instantiate_from_definition(
            chain[next_idx],
            InstantiateProcessFromDefinitionRequest(
                name=f"WO {sample_name} {analysis_name} p{position} {uuid4().hex[:6]}"[:240],
                assignments=[
                    ProcessAssignmentItem(
                        sample_id=item["sample_id"],
                        container_id=item["container_id"],
                    )
                    for item in assignments
                ],
                work_order_id=wo.id,
                work_order_route_position=position,
            ),
        )
        if wo.process_id is None:
            wo.process_id = inst.id
        wo.status = "in_progress"
        wo.modified_by = self.user.id
        self.db.commit()
        self.db.refresh(wo)
        return (
            self.db.query(WorkOrder)
            .options(joinedload(WorkOrder.sample), joinedload(WorkOrder.analysis))
            .filter(WorkOrder.id == wo.id)
            .first()
        )

    def read_maps(self, rows: Sequence[RoutingMap]) -> List[dict]:
        cache: dict[tuple, List[UUID]] = {}
        payloads = []
        for row in rows:
            key = tuple(row.process_definition_ids or [])
            if key not in cache:
                cache[key] = self._chain_lims_analysis_ids(key)
            payloads.append(map_to_read(row, cache[key]))
        return payloads

    def read_map(self, row: RoutingMap) -> dict:
        return self.read_maps([row])[0]

    def read_work_order(self, row: WorkOrder) -> dict:
        started = self._started_processes([row.id]).get(row.id, [])
        return work_order_to_read(row, started)

    def read_work_orders(self, rows: Sequence[WorkOrder]) -> List[dict]:
        grouped = self._started_processes([r.id for r in rows])
        return [work_order_to_read(r, grouped.get(r.id, [])) for r in rows]

    def _require_definitions(self, ids: Sequence[UUID]) -> None:
        if not ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "process_definition_ids must not be empty",
            )
        if len(ids) != len(set(ids)):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "process_definition_ids must be unique in listed order",
            )
        found = (
            self.db.query(ELNProcessDefinition.id)
            .filter(ELNProcessDefinition.id.in_(list(ids)))
            .all()
        )
        if len(found) != len(set(ids)):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "One or more process definitions were not found",
            )


def map_to_read(row: RoutingMap, analysis_ids: Optional[Sequence[UUID]] = None) -> dict:
    lo, hi = _range_bounds(row.tat_range)
    ids = list(analysis_ids or [])
    return {
        "id": row.id,
        "analysis_id": row.analysis_id or (ids[0] if ids else None),
        "analysis_ids": ids,
        "sample_type_id": row.sample_type_id,
        "tat_min": lo,
        "tat_max": hi,
        "process_definition_ids": list(row.process_definition_ids or []),
        "active": row.active,
        "created_at": row.created_at,
        "modified_at": row.modified_at,
    }


def work_order_to_read(row: WorkOrder, started: Optional[Sequence] = None) -> dict:
    sample = getattr(row, "sample", None)
    analysis = getattr(row, "analysis", None)
    started = list(started or [])
    latest = started[-1] if started else None
    return {
        "id": row.id,
        "asked_for_id": row.asked_for_id,
        "sample_id": row.sample_id,
        "sample_name": getattr(sample, "name", None),
        "analysis_id": row.analysis_id,
        "analysis_name": getattr(analysis, "name", None),
        "process_definition_ids": list(row.process_definition_ids or []),
        "status": row.status,
        "process_id": row.process_id,
        "latest_process_id": latest.id if latest else row.process_id,
        "started_count": len(started),
        "created_at": row.created_at,
    }
