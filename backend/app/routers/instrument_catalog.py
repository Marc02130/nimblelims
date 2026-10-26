"""CRUD for instrument types (list), instruments, and CRO sources.

Write operations require config:edit. There is no DELETE: retire with
``active`` / ``status``. Types are rows on the ``instrument_types`` list.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.patch_fields import explicit_updates
from app.core.rbac import require_config_edit
from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.schemas.instrument_catalog import (
    CroSourceCreate,
    CroSourceResponse,
    CroSourceUpdate,
    InstrumentCreate,
    InstrumentEligibilityResponse,
    InstrumentResponse,
    InstrumentTypeCreate,
    InstrumentTypeResponse,
    InstrumentTypeUpdate,
    InstrumentUpdate,
)
from app.services.instrument_eligibility import instrument_block_reason
from models.client import Client, Location
from models.instrument import (
    CroSource,
    Instrument,
    InstrumentMaintenanceAudit,
)
from models.list import List as ListModel, ListEntry
from models.reagent import Vendor
from models.user import User

instrument_types_router = APIRouter(prefix="/instrument-types", tags=["instrument-types"])
instruments_router = APIRouter(prefix="/instruments", tags=["instruments"])
cro_sources_router = APIRouter(prefix="/cro-sources", tags=["cro-sources"])


def _has_config_edit(user: User, db: Session) -> bool:
    return "config:edit" in get_user_permissions(user, db)


def _active_filter(query, model, user: User, db: Session):
    if _has_config_edit(user, db):
        return query
    return query.filter(model.active.is_(True))


def _types_list_id(db: Session) -> UUID:
    row = db.query(ListModel).filter(ListModel.name == "instrument_types").first()
    if row is None:
        raise HTTPException(status_code=500, detail="A required list is not seeded")
    return row.id


def _type_query(db: Session):
    return db.query(ListEntry).filter(ListEntry.list_id == _types_list_id(db))


def _type_out(db: Session, row: ListEntry) -> InstrumentTypeResponse:
    return InstrumentTypeResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        active=row.active,
        created_at=row.created_at,
        modified_at=row.modified_at,
    )


def _audit_maintenance_tracked(
    db: Session,
    instrument: Instrument,
    previous: bool,
    new_value: bool,
    user: User,
    always: bool = False,
) -> None:
    if not always and previous == new_value:
        return
    db.add(
        InstrumentMaintenanceAudit(
            instrument_id=instrument.id,
            previous_value=previous,
            new_value=new_value,
            created_by=user.id,
        )
    )


def _require_type(db: Session, type_id: UUID) -> ListEntry:
    row = _type_query(db).filter(ListEntry.id == type_id).first()
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid instrument type")
    return row


def _require_active_type(db: Session, type_id: UUID) -> ListEntry:
    row = _require_type(db, type_id)
    if row.active is not True:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "instrument_type_inactive",
                "message": "That instrument type is inactive and cannot be used.",
            },
        )
    return row


# --- Instrument types (list entries) ---

@instrument_types_router.get("", response_model=List[InstrumentTypeResponse])
def list_instrument_types(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _type_query(db)
    q = _active_filter(q, ListEntry, current_user, db)
    if active is not None and _has_config_edit(current_user, db):
        q = q.filter(ListEntry.active.is_(active))
    if search:
        term = f"%{search}%"
        q = q.filter(ListEntry.name.ilike(term))
    return [_type_out(db, r) for r in q.order_by(ListEntry.name).all()]


@instrument_types_router.get("/{type_id}", response_model=InstrumentTypeResponse)
def get_instrument_type(
    type_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _type_query(db).filter(ListEntry.id == type_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Instrument type not found")
    return _type_out(db, row)


@instrument_types_router.post(
    "", response_model=InstrumentTypeResponse, status_code=status.HTTP_201_CREATED
)
def create_instrument_type(
    body: InstrumentTypeCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if _type_query(db).filter(ListEntry.name == body.name).first():
        raise HTTPException(status_code=400, detail="Instrument type name already exists")
    row = ListEntry(
        name=body.name,
        description=body.description,
        list_id=_types_list_id(db),
        active=body.active,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    db.flush()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Instrument type name already exists")
    db.refresh(row)
    return _type_out(db, row)


@instrument_types_router.patch("/{type_id}", response_model=InstrumentTypeResponse)
def update_instrument_type(
    type_id: UUID,
    body: InstrumentTypeUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = _type_query(db).filter(ListEntry.id == type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument type not found")
    data = explicit_updates(body, row, refuse_null={"active"})
    if "name" in data and data["name"] != row.name:
        if _type_query(db).filter(ListEntry.name == data["name"]).first():
            raise HTTPException(status_code=400, detail="Instrument type name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update instrument type")
    db.refresh(row)
    return _type_out(db, row)


# --- Instruments (instances) ---

def _instrument_response(row: Instrument) -> InstrumentResponse:
    t = row.instrument_type
    vendor = row.vendor
    loc = row.location
    return InstrumentResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        instrument_type_id=row.instrument_type_id,
        vendor_id=row.vendor_id,
        model=row.model,
        serial_number=row.serial_number,
        asset_tag=row.asset_tag,
        location_id=row.location_id,
        status=row.status,
        active=row.active,
        maintenance_tracked=row.maintenance_tracked,
        created_at=row.created_at,
        modified_at=row.modified_at,
        instrument_type_name=t.name if t else None,
        vendor_name=vendor.name if vendor else None,
        location_name=loc.name if loc else None,
    )


def _instrument_query(db: Session):
    return db.query(Instrument).options(
        joinedload(Instrument.instrument_type),
        joinedload(Instrument.vendor),
        joinedload(Instrument.location),
    )


@instruments_router.get("", response_model=List[InstrumentResponse])
def list_instruments(
    search: Optional[str] = Query(None),
    instrument_type_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    eligible: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _instrument_query(db)
    q = _active_filter(q, Instrument, current_user, db)
    if active is not None and _has_config_edit(current_user, db):
        q = q.filter(Instrument.active.is_(active))
    if instrument_type_id:
        q = q.filter(Instrument.instrument_type_id == instrument_type_id)
    if status:
        q = q.filter(Instrument.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            (Instrument.name.ilike(term))
            | (Instrument.serial_number.ilike(term))
            | (Instrument.asset_tag.ilike(term))
            | (Instrument.model.ilike(term))
        )
    rows = q.order_by(Instrument.name).all()
    if eligible is True:
        rows = [r for r in rows if instrument_block_reason(db, r.id) is None]
    return [_instrument_response(r) for r in rows]


@instruments_router.get("/{instrument_id}", response_model=InstrumentResponse)
def get_instrument(
    instrument_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _instrument_query(db).filter(Instrument.id == instrument_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Instrument not found")
    return _instrument_response(row)


@instruments_router.get(
    "/{instrument_id}/eligibility", response_model=InstrumentEligibilityResponse
)
def get_instrument_eligibility(
    instrument_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reason = instrument_block_reason(db, instrument_id)
    if reason and reason.get("code") == "instrument_not_found":
        raise HTTPException(status_code=404, detail="Instrument not found")
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    tracked = bool(row.maintenance_tracked) if row is not None else False
    if reason is None:
        return InstrumentEligibilityResponse(
            instrument_id=instrument_id,
            allowed=True,
            maintenance_tracked=tracked,
        )
    return InstrumentEligibilityResponse(
        instrument_id=instrument_id,
        allowed=False,
        maintenance_tracked=tracked,
        code=reason["code"],
        message=reason["message"],
    )


@instruments_router.post(
    "", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED
)
def create_instrument(
    body: InstrumentCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    _require_active_type(db, body.instrument_type_id)
    if body.vendor_id and not db.query(Vendor).filter(Vendor.id == body.vendor_id).first():
        raise HTTPException(status_code=400, detail="Invalid vendor")
    if body.location_id and not db.query(Location).filter(Location.id == body.location_id).first():
        raise HTTPException(status_code=400, detail="Invalid location")
    if db.query(Instrument).filter(Instrument.name == body.name).first():
        raise HTTPException(status_code=400, detail="Instrument name already exists")
    payload = body.model_dump()
    if payload.get("maintenance_tracked") is None:
        payload["maintenance_tracked"] = False
    row = Instrument(
        **payload,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    db.flush()
    if row.maintenance_tracked is False:
        _audit_maintenance_tracked(
            db, row, False, False, current_user, always=True
        )
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "uq_instruments_vendor_model_serial" in msg or "serial" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Serial number already exists for this vendor and model",
            )
        raise HTTPException(status_code=400, detail="Could not create instrument")
    row = _instrument_query(db).filter(Instrument.id == row.id).first()
    return _instrument_response(row)


@instruments_router.patch("/{instrument_id}", response_model=InstrumentResponse)
def update_instrument(
    instrument_id: UUID,
    body: InstrumentUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument not found")
    data = explicit_updates(body, row, refuse_null={"active", "status", "maintenance_tracked"})
    previous_tracked = row.maintenance_tracked
    if "instrument_type_id" in data:
        _require_active_type(db, data["instrument_type_id"])
    if "vendor_id" in data and data["vendor_id"] is not None:
        if not db.query(Vendor).filter(Vendor.id == data["vendor_id"]).first():
            raise HTTPException(status_code=400, detail="Invalid vendor")
    if "location_id" in data and data["location_id"] is not None:
        if not db.query(Location).filter(Location.id == data["location_id"]).first():
            raise HTTPException(status_code=400, detail="Invalid location")
    if "name" in data and data["name"] != row.name:
        if db.query(Instrument).filter(Instrument.name == data["name"]).first():
            raise HTTPException(status_code=400, detail="Instrument name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    if row.status == "retired":
        row.active = False
    if "maintenance_tracked" in data:
        _audit_maintenance_tracked(
            db, row, previous_tracked, row.maintenance_tracked, current_user
        )
    row.modified_by = current_user.id
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "uq_instruments_vendor_model_serial" in msg:
            raise HTTPException(
                status_code=400,
                detail="Serial number already exists for this vendor and model",
            )
        raise HTTPException(status_code=400, detail="Could not update instrument")
    row = _instrument_query(db).filter(Instrument.id == instrument_id).first()
    return _instrument_response(row)


# --- CRO sources ---

def _cro_response(row: CroSource) -> CroSourceResponse:
    return CroSourceResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        client_id=row.client_id,
        active=row.active,
        created_at=row.created_at,
        modified_at=row.modified_at,
        client_name=row.client.name if row.client else None,
    )


@cro_sources_router.get("", response_model=List[CroSourceResponse])
def list_cro_sources(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(CroSource).options(joinedload(CroSource.client))
    q = _active_filter(q, CroSource, current_user, db)
    if active is not None and _has_config_edit(current_user, db):
        q = q.filter(CroSource.active.is_(active))
    if search:
        term = f"%{search}%"
        q = q.filter(CroSource.name.ilike(term))
    return [_cro_response(r) for r in q.order_by(CroSource.name).all()]


@cro_sources_router.get("/{source_id}", response_model=CroSourceResponse)
def get_cro_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(CroSource)
        .options(joinedload(CroSource.client))
        .filter(CroSource.id == source_id)
        .first()
    )
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="CRO source not found")
    return _cro_response(row)


@cro_sources_router.post(
    "", response_model=CroSourceResponse, status_code=status.HTTP_201_CREATED
)
def create_cro_source(
    body: CroSourceCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if db.query(CroSource).filter(CroSource.name == body.name).first():
        raise HTTPException(status_code=400, detail="CRO source name already exists")
    if body.client_id and not db.query(Client).filter(Client.id == body.client_id).first():
        raise HTTPException(status_code=400, detail="Invalid client")
    row = CroSource(
        **body.model_dump(),
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="CRO source name already exists")
    row = (
        db.query(CroSource)
        .options(joinedload(CroSource.client))
        .filter(CroSource.id == row.id)
        .first()
    )
    return _cro_response(row)


@cro_sources_router.patch("/{source_id}", response_model=CroSourceResponse)
def update_cro_source(
    source_id: UUID,
    body: CroSourceUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(CroSource).filter(CroSource.id == source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="CRO source not found")
    data = explicit_updates(body, row, refuse_null={"active"})
    if "name" in data and data["name"] != row.name:
        if db.query(CroSource).filter(CroSource.name == data["name"]).first():
            raise HTTPException(status_code=400, detail="CRO source name already exists")
    if "client_id" in data and data["client_id"] is not None:
        if not db.query(Client).filter(Client.id == data["client_id"]).first():
            raise HTTPException(status_code=400, detail="Invalid client")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update CRO source")
    row = (
        db.query(CroSource)
        .options(joinedload(CroSource.client))
        .filter(CroSource.id == source_id)
        .first()
    )
    return _cro_response(row)
