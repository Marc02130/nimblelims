"""P2 APIs: routing map, work orders, step accepted sample types."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import require_config_edit, require_experiment_manage, require_sample_read
from app.core.security import get_current_user
from app.database import get_db
from app.schemas.work_order import (
    RouteItem,
    RouteRequest,
    RouteResponse,
    RoutingMapCreate,
    RoutingMapRead,
    RoutingMapUpdate,
    StepAcceptedSampleTypesPut,
    StepAcceptedSampleTypesResponse,
    WorkOrderListResponse,
    WorkOrderRead,
)
from app.services.routing_service import RoutingService
from models.user import User

routing_map_router = APIRouter(prefix="/routing-map", tags=["routing-map"])
work_orders_router = APIRouter(prefix="/work-orders", tags=["work-orders"])


def _svc(db: Session, user: User) -> RoutingService:
    return RoutingService(db, current_user=user)


@routing_map_router.get("", response_model=List[RoutingMapRead])
def list_routing_map(
    analysis_id: Optional[UUID] = None,
    sample_type_id: Optional[UUID] = None,
    active_only: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    rows = svc.list_maps(
        analysis_id=analysis_id,
        sample_type_id=sample_type_id,
        active_only=active_only,
    )
    return [RoutingMapRead(**payload) for payload in svc.read_maps(rows)]


@routing_map_router.post(
    "",
    response_model=List[RoutingMapRead],
    status_code=status.HTTP_201_CREATED,
)
def create_routing_map(
    body: RoutingMapCreate,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    rows = svc.create_map(
        tat_min=body.tat_min,
        tat_max=body.tat_max,
        process_definition_ids=body.process_definition_ids,
        active=body.active,
        analysis_id=body.analysis_id,
    )
    return [RoutingMapRead(**payload) for payload in svc.read_maps(rows)]


@routing_map_router.patch("/{map_id}", response_model=RoutingMapRead)
def update_routing_map(
    map_id: UUID,
    body: RoutingMapUpdate,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    row = svc.update_map(
        map_id,
        tat_min=body.tat_min,
        tat_max=body.tat_max,
        process_definition_ids=body.process_definition_ids,
        active=body.active,
    )
    return RoutingMapRead(**svc.read_map(row))


@routing_map_router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routing_map(
    map_id: UUID,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    _svc(db, user).delete_map(map_id)


@work_orders_router.post("/{work_order_id}/start", response_model=WorkOrderRead)
def start_work_order(
    work_order_id: UUID,
    user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    row = svc.start_work_order(work_order_id)
    return WorkOrderRead(**svc.read_work_order(row))


@work_orders_router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    sample_id: Optional[UUID] = None,
    user: User = Depends(require_sample_read),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    rows = svc.list_work_orders(
        status_filter=status_filter, sample_id=sample_id
    )
    items = [WorkOrderRead(**payload) for payload in svc.read_work_orders(rows)]
    return WorkOrderListResponse(items=items, count=len(items))


step_types_router = APIRouter(
    prefix="/eln-process-definitions",
    tags=["eln-process-definitions"],
)


@step_types_router.get(
    "/{definition_id}/steps/{step_id}/accepted-sample-types",
    response_model=StepAcceptedSampleTypesResponse,
)
def get_step_accepted_types(
    definition_id: UUID,
    step_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = _svc(db, user).list_step_accepted_types(step_id)
    return StepAcceptedSampleTypesResponse(
        step_id=step_id, sample_type_ids=ids, count=len(ids)
    )


@step_types_router.put(
    "/{definition_id}/steps/{step_id}/accepted-sample-types",
    response_model=StepAcceptedSampleTypesResponse,
)
def put_step_accepted_types(
    definition_id: UUID,
    step_id: UUID,
    body: StepAcceptedSampleTypesPut,
    user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    ids = _svc(db, user).replace_step_accepted_types(
        step_id, body.sample_type_ids, definition_id=definition_id
    )
    return StepAcceptedSampleTypesResponse(
        step_id=step_id, sample_type_ids=ids, count=len(ids)
    )
