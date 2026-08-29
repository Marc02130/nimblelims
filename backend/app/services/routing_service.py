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
        if analysis_id is not None:
            q = q.filter(RoutingMap.analysis_id == analysis_id)
        if sample_type_id is not None:
            q = q.filter(RoutingMap.sample_type_id == sample_type_id)
        if active_only:
            q = q.filter(RoutingMap.active == True)  # noqa: E712
        return q.order_by(RoutingMap.created_at.desc()).all()

    def create_map(
        self,
        analysis_id: UUID,
        tat_min: int,
        tat_max: int,
        process_definition_ids: Sequence[UUID],
        active: bool = True,
    ) -> List[RoutingMap]:
        """Sample types come from the first process's first experiment/LIMS Run."""
        chain = list(process_definition_ids)
        self._require_definitions(chain)
        types = self._require_first_step_types(chain)
        for sid in types:
            self._refuse_overlap(analysis_id, sid, tat_min, tat_max)
        created: List[RoutingMap] = []
        for sid in types:
            row = RoutingMap(
                analysis_id=analysis_id,
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
                detail="Overlapping TAT range for this analysis and sample type",
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
        self._refuse_overlap(
            row.analysis_id, row.sample_type_id, lo, hi, exclude_id=row.id
        )
        row.tat_range = _range(lo, hi)
        row.process_definition_ids = chain
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
                detail="Overlapping TAT range for this analysis and sample type",
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
                detail="Overlapping TAT range for this analysis and sample type",
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
                row.analysis_id,
                lo,
                hi,
                tuple(row.process_definition_ids or []),
                row.active,
            )
            groups.setdefault(key, []).append(row)
        for (analysis_id, lo, hi, chain, active), group in groups.items():
            existing = {m.sample_type_id: m for m in group}
            for sid, row in existing.items():
                if sid not in desired:
                    self.db.delete(row)
            self.db.flush()
            owner = group[0]
            for sid in desired:
                if sid in existing:
                    continue
                if self._has_overlap(analysis_id, sid, lo, hi):
                    # Live first-step list is SoT. Skip a denorm row that
                    # would collide; Route 409s when two maps accept the type.
                    continue
                self.db.add(
                    RoutingMap(
                        analysis_id=analysis_id,
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

    def _analysis_tat_candidates(
        self, analysis_id: UUID, tat_days: int
    ) -> List[RoutingMap]:
        return (
            self.db.query(RoutingMap)
            .filter(
                RoutingMap.active == True,  # noqa: E712
                RoutingMap.analysis_id == analysis_id,
                RoutingMap.tat_range.op("@>")(tat_days),
            )
            .all()
        )

    def _unique_logical_maps(self, rows: Sequence[RoutingMap]) -> List[RoutingMap]:
        seen: dict[tuple, RoutingMap] = {}
        for row in rows:
            lo, hi = _range_bounds(row.tat_range)
            key = (
                row.analysis_id,
                lo,
                hi,
                tuple(row.process_definition_ids or []),
            )
            seen.setdefault(key, row)
        return list(seen.values())

    def _acceptable_maps(
        self, analysis_id: UUID, sample_type_id: UUID, tat_days: int
    ) -> List[RoutingMap]:
        unique = self._unique_logical_maps(
            self._analysis_tat_candidates(analysis_id, tat_days)
        )
        acceptable: List[RoutingMap] = []
        for row in unique:
            chain = list(row.process_definition_ids or [])
            try:
                types = self._require_first_step_types(chain)
            except HTTPException:
                continue
            if sample_type_id in types:
                acceptable.append(row)
        return acceptable

    def _has_overlap(
        self,
        analysis_id: UUID,
        sample_type_id: UUID,
        tat_min: int,
        tat_max: int,
        exclude_id: Optional[UUID] = None,
    ) -> bool:
        q = self.db.query(RoutingMap).filter(
            RoutingMap.active == True,  # noqa: E712
            RoutingMap.analysis_id == analysis_id,
            RoutingMap.sample_type_id == sample_type_id,
            RoutingMap.tat_range.op("&&")(_range(tat_min, tat_max)),
        )
        if exclude_id is not None:
            q = q.filter(RoutingMap.id != exclude_id)
        return q.first() is not None

    def _refuse_overlap(
        self,
        analysis_id: UUID,
        sample_type_id: UUID,
        tat_min: int,
        tat_max: int,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        if self._has_overlap(
            analysis_id, sample_type_id, tat_min, tat_max, exclude_id=exclude_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Overlapping TAT range for this analysis and sample type",
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
                detail="Two routing-map rows accept this sample type",
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
        sample_type_id = getattr(wo.sample, "sample_type", None)
        if sample_type_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Work order sample has no sample type",
            )
        self._assert_sample_matches_first_step([chain[next_idx]], sample_type_id)
        from app.schemas.eln_process_definition import InstantiateProcessFromDefinitionRequest
        from app.services.eln_process_service import ELNProcessService

        sample_name = getattr(wo.sample, "name", None) or "sample"
        analysis_name = getattr(wo.analysis, "name", None) or "analysis"
        position = next_idx + 1
        inst = ELNProcessService(self.db, current_user=self.user).instantiate_from_definition(
            chain[next_idx],
            InstantiateProcessFromDefinitionRequest(
                name=f"WO {sample_name} {analysis_name} p{position} {uuid4().hex[:6]}"[:240],
                sample_ids=[wo.sample_id],
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


def map_to_read(row: RoutingMap) -> dict:
    lo, hi = _range_bounds(row.tat_range)
    return {
        "id": row.id,
        "analysis_id": row.analysis_id,
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
