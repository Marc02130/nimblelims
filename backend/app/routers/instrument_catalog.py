"""CRUD for instrument types, instrument instances, and CRO sources (data-parsers P0).

Write operations require config:edit. List endpoints return all rows for config:edit
users; others see only active rows.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import require_config_edit
from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.schemas.instrument_catalog import (
    CroSourceCreate,
    CroSourceResponse,
    CroSourceUpdate,
    InstrumentCreate,
    InstrumentResponse,
    InstrumentTypeCreate,
    InstrumentTypeResponse,
    InstrumentTypeUpdate,
    InstrumentUpdate,
)
from models.client import Client
from models.instrument import CroSource, Instrument, InstrumentType
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


# --- Instrument types ---

@instrument_types_router.get("", response_model=List[InstrumentTypeResponse])
async def list_instrument_types(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(InstrumentType)
    q = _active_filter(q, InstrumentType, current_user, db)
    if active is not None and _has_config_edit(current_user, db):
        q = q.filter(InstrumentType.active.is_(active))
    if search:
        term = f"%{search}%"
        q = q.filter(
            (InstrumentType.name.ilike(term))
            | (InstrumentType.vendor.ilike(term))
            | (InstrumentType.model.ilike(term))
        )
    return q.order_by(InstrumentType.name).all()


@instrument_types_router.get("/{type_id}", response_model=InstrumentTypeResponse)
async def get_instrument_type(
    type_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentType).filter(InstrumentType.id == type_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Instrument type not found")
    return row


@instrument_types_router.post(
    "", response_model=InstrumentTypeResponse, status_code=status.HTTP_201_CREATED
)
async def create_instrument_type(
    body: InstrumentTypeCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if db.query(InstrumentType).filter(InstrumentType.name == body.name).first():
        raise HTTPException(status_code=400, detail="Instrument type name already exists")
    row = InstrumentType(
        **body.model_dump(),
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Instrument type name already exists")
    db.refresh(row)
    return row


@instrument_types_router.patch("/{type_id}", response_model=InstrumentTypeResponse)
async def update_instrument_type(
    type_id: UUID,
    body: InstrumentTypeUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentType).filter(InstrumentType.id == type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument type not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != row.name:
        if db.query(InstrumentType).filter(InstrumentType.name == data["name"]).first():
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
    return row


@instrument_types_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instrument_type(
    type_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentType).filter(InstrumentType.id == type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument type not found")
    in_use = db.query(Instrument).filter(Instrument.instrument_type_id == type_id).first()
    if in_use:
        # Soft-deactivate when referenced
        row.active = False
        row.modified_by = current_user.id
        db.commit()
        return None
    db.delete(row)
    db.commit()
    return None


# --- Instruments (instances) ---

def _instrument_response(row: Instrument) -> InstrumentResponse:
    t = row.instrument_type
    return InstrumentResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        instrument_type_id=row.instrument_type_id,
        serial_number=row.serial_number,
        active=row.active,
        created_at=row.created_at,
        modified_at=row.modified_at,
        instrument_type_name=t.name if t else None,
        instrument_type_vendor=t.vendor if t else None,
        instrument_type_model=t.model if t else None,
    )


@instruments_router.get("", response_model=List[InstrumentResponse])
async def list_instruments(
    search: Optional[str] = Query(None),
    instrument_type_id: Optional[UUID] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Instrument).options(joinedload(Instrument.instrument_type))
    q = _active_filter(q, Instrument, current_user, db)
    if active is not None and _has_config_edit(current_user, db):
        q = q.filter(Instrument.active.is_(active))
    if instrument_type_id:
        q = q.filter(Instrument.instrument_type_id == instrument_type_id)
    if search:
        term = f"%{search}%"
        q = q.filter(
            (Instrument.name.ilike(term)) | (Instrument.serial_number.ilike(term))
        )
    rows = q.order_by(Instrument.name).all()
    return [_instrument_response(r) for r in rows]


@instruments_router.get("/{instrument_id}", response_model=InstrumentResponse)
async def get_instrument(
    instrument_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Instrument)
        .options(joinedload(Instrument.instrument_type))
        .filter(Instrument.id == instrument_id)
        .first()
    )
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Instrument not found")
    return _instrument_response(row)


@instruments_router.post(
    "", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED
)
async def create_instrument(
    body: InstrumentCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if not db.query(InstrumentType).filter(InstrumentType.id == body.instrument_type_id).first():
        raise HTTPException(status_code=400, detail="Invalid instrument type")
    if db.query(Instrument).filter(Instrument.name == body.name).first():
        raise HTTPException(status_code=400, detail="Instrument name already exists")
    row = Instrument(
        **body.model_dump(),
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "uq_instruments_type_serial" in msg or "serial" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Serial number already exists for this instrument type",
            )
        raise HTTPException(status_code=400, detail="Could not create instrument")
    db.refresh(row)
    row = (
        db.query(Instrument)
        .options(joinedload(Instrument.instrument_type))
        .filter(Instrument.id == row.id)
        .first()
    )
    return _instrument_response(row)


@instruments_router.patch("/{instrument_id}", response_model=InstrumentResponse)
async def update_instrument(
    instrument_id: UUID,
    body: InstrumentUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument not found")
    data = body.model_dump(exclude_unset=True)
    if "instrument_type_id" in data:
        if not db.query(InstrumentType).filter(
            InstrumentType.id == data["instrument_type_id"]
        ).first():
            raise HTTPException(status_code=400, detail="Invalid instrument type")
    if "name" in data and data["name"] != row.name:
        if db.query(Instrument).filter(Instrument.name == data["name"]).first():
            raise HTTPException(status_code=400, detail="Instrument name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "uq_instruments_type_serial" in msg:
            raise HTTPException(
                status_code=400,
                detail="Serial number already exists for this instrument type",
            )
        raise HTTPException(status_code=400, detail="Could not update instrument")
    row = (
        db.query(Instrument)
        .options(joinedload(Instrument.instrument_type))
        .filter(Instrument.id == instrument_id)
        .first()
    )
    return _instrument_response(row)


@instruments_router.delete("/{instrument_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instrument(
    instrument_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instrument not found")
    # Soft-delete preferred (parsers may reference later)
    row.active = False
    row.modified_by = current_user.id
    db.commit()
    return None


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
async def list_cro_sources(
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
    rows = q.order_by(CroSource.name).all()
    return [_cro_response(r) for r in rows]


@cro_sources_router.get("/{source_id}", response_model=CroSourceResponse)
async def get_cro_source(
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
async def create_cro_source(
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
async def update_cro_source(
    source_id: UUID,
    body: CroSourceUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(CroSource).filter(CroSource.id == source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="CRO source not found")
    data = body.model_dump(exclude_unset=True)
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


@cro_sources_router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cro_source(
    source_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(CroSource).filter(CroSource.id == source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="CRO source not found")
    row.active = False
    row.modified_by = current_user.id
    db.commit()
    return None
