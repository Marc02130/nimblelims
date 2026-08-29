"""P2 routing map, type gate, and Route → work_order."""
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
NO_ROUTE = "no_route"


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
        sample_type_id: UUID,
        tat_min: int,
        tat_max: int,
        process_definition_ids: Sequence[UUID],
        active: bool = True,
    ) -> RoutingMap:
        chain = list(process_definition_ids)
        self._require_definitions(chain)
        self.assert_chain_accepts_sample_type(chain, sample_type_id)
        self._refuse_overlap(analysis_id, sample_type_id, tat_min, tat_max)
        row = RoutingMap(
            analysis_id=analysis_id,
            sample_type_id=sample_type_id,
            tat_range=_range(tat_min, tat_max),
            process_definition_ids=chain,
            active=active,
            created_by=self.user.id,
            modified_by=self.user.id,
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.info("Routing map overlap: %s", e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Overlapping TAT range for this analysis and sample type",
            ) from e
        self.db.refresh(row)
        return row

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
        self.assert_chain_accepts_sample_type(chain, row.sample_type_id)
        self._refuse_overlap(
            row.analysis_id, row.sample_type_id, lo, hi, exclude_id=row.id
        )
        row.tat_range = _range(lo, hi)
        row.process_definition_ids = chain
        if active is not None:
            row.active = active
        row.modified_by = self.user.id
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Overlapping TAT range for this analysis and sample type",
            ) from e
        self.db.refresh(row)
        return row

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
        self.db.commit()
        return list(seen)

    def assert_chain_accepts_sample_type(
        self, process_definition_ids: Sequence[UUID], sample_type_id: UUID
    ) -> None:
        """Fail closed if any step has empty accepted set or does not include sample_type."""
        for def_id in process_definition_ids:
            steps = (
                self.db.query(ELNProcessDefinitionStep)
                .filter(ELNProcessDefinitionStep.process_definition_id == def_id)
                .order_by(ELNProcessDefinitionStep.sort_order)
                .all()
            )
            if not steps:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": ROUTE_SAMPLE_TYPE,
                        "message": "Process definition has no steps",
                    },
                )
            for step in steps:
                accepted = self.list_step_accepted_types(step.id)
                if not accepted or sample_type_id not in accepted:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "code": ROUTE_SAMPLE_TYPE,
                            "message": (
                                "Sample type is not accepted on every step in the chain"
                            ),
                        },
                    )

    def find_map(
        self, analysis_id: UUID, sample_type_id: UUID, tat_days: int
    ) -> Optional[RoutingMap]:
        return (
            self.db.query(RoutingMap)
            .filter(
                RoutingMap.active == True,  # noqa: E712
                RoutingMap.analysis_id == analysis_id,
                RoutingMap.sample_type_id == sample_type_id,
                RoutingMap.tat_range.op("@>")(tat_days),
            )
            .first()
        )

    def _refuse_overlap(
        self,
        analysis_id: UUID,
        sample_type_id: UUID,
        tat_min: int,
        tat_max: int,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        q = self.db.query(RoutingMap).filter(
            RoutingMap.active == True,  # noqa: E712
            RoutingMap.analysis_id == analysis_id,
            RoutingMap.sample_type_id == sample_type_id,
            RoutingMap.tat_range.op("&&")(_range(tat_min, tat_max)),
        )
        if exclude_id is not None:
            q = q.filter(RoutingMap.id != exclude_id)
        if q.first():
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
        match = self.find_map(row.analysis_id, sample.sample_type, row.tat_days)
        if not match:
            return {"asked_for_id": row.id, "work_order": None, "no_route": True}

        chain = list(match.process_definition_ids or [])
        self.assert_chain_accepts_sample_type(chain, sample.sample_type)

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

    def start_work_order(self, work_order_id: UUID):
        """Instantiate the first snapshot definition and link eln_processes.work_order_id."""
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
        if wo.process_id:
            return wo
        chain = list(wo.process_definition_ids or [])
        if not chain:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Work order has an empty process chain",
            )
        from app.schemas.eln_process_definition import InstantiateProcessFromDefinitionRequest
        from app.services.eln_process_service import ELNProcessService

        sample_name = getattr(wo.sample, "name", None) or "sample"
        analysis_name = getattr(wo.analysis, "name", None) or "analysis"
        inst = ELNProcessService(self.db, current_user=self.user).instantiate_from_definition(
            chain[0],
            InstantiateProcessFromDefinitionRequest(
                name=f"WO {sample_name} {analysis_name} {uuid4().hex[:6]}"[:240],
                sample_ids=[wo.sample_id],
                work_order_id=wo.id,
            ),
        )
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

    def _require_definitions(self, ids: Sequence[UUID]) -> None:
        if not ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "process_definition_ids must not be empty",
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


def work_order_to_read(row: WorkOrder) -> dict:
    sample = getattr(row, "sample", None)
    analysis = getattr(row, "analysis", None)
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
        "created_at": row.created_at,
    }
