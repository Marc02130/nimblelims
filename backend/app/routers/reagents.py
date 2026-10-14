"""Reagent tracking: vendors, reagents, reagent-vendor sources, lots, and use.

A reagent is vendor-agnostic. Each vendor that sells it is a reagent-vendor
row (catalog number, unit, unit of sale, reorder point/quantity, lead time,
price). A lot belongs to a reagent and may name the source it was bought from.

Catalog writes (vendors, reagents, sources, lots) need config:edit. Recording a lot used
on a LIMS run or experiment needs experiment:manage, the same seat that runs
them. There are no DELETE routes: retire a row with ``active`` false, use a lot
up with ``quantity_remaining`` 0, and void a use with ``active`` false.

Use flow: the run or experiment holds the reagent; pick a lot, enter the
quantity used, and the lot's quantity remaining goes down. An expired lot
(effective expiry before the use date), an unreleased, QC-rejected or
inactive lot is refused (422). ``released`` defaults true; QC release sets it.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.rbac import require_config_edit, require_experiment_manage
from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.schemas.reagent import (
    ReagentCreate,
    ReagentLotCreate,
    ReagentLotResponse,
    ReagentLotUpdate,
    ReagentResponse,
    ReagentUpdate,
    ReagentUseCreate,
    ReagentUseResponse,
    ReagentUseUpdate,
    ReagentVendorCreate,
    ReagentVendorResponse,
    ReagentVendorUpdate,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from models.reagent import Reagent, ReagentLot, ReagentUse, ReagentVendor, Vendor
from models.user import User

vendors_router = APIRouter(prefix="/vendors", tags=["reagents"])
reagents_router = APIRouter(prefix="/reagents", tags=["reagents"])
reagent_vendors_router = APIRouter(prefix="/reagent-vendors", tags=["reagents"])
reagent_lots_router = APIRouter(prefix="/reagent-lots", tags=["reagents"])
reagent_uses_router = APIRouter(prefix="/reagent-uses", tags=["reagents"])


def _has_config_edit(user: User, db: Session) -> bool:
    return "config:edit" in get_user_permissions(user, db)


def _visible(query, model, user: User, db: Session, active: Optional[bool]):
    if not _has_config_edit(user, db):
        return query.filter(model.active.is_(True))
    if active is not None:
        return query.filter(model.active.is_(active))
    return query


def _commit(db: Session, row, conflict: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=conflict)
    db.refresh(row)
    return row


def effective_expiration(lot: ReagentLot) -> Optional[date]:
    """The earlier of the printed expiry and opened date + the reagent's
    stability after opening (days). None when neither is known."""
    dates = [lot.expiration_date] if lot.expiration_date else []
    stability = lot.reagent.stability_after_opening_days if lot.reagent is not None else None
    if lot.opened_date is not None and stability is not None:
        dates.append(lot.opened_date + timedelta(days=int(Decimal(stability))))
    return min(dates) if dates else None


def lot_expired(lot: ReagentLot, on: Optional[date] = None) -> bool:
    effective = effective_expiration(lot)
    return effective is not None and effective < (on or date.today())


# ------------------------------------------------------------------ vendors ---

@vendors_router.get("", response_model=List[VendorResponse])
async def list_vendors(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _visible(db.query(Vendor), Vendor, current_user, db, active)
    if search:
        q = q.filter(Vendor.name.ilike(f"%{search}%"))
    return q.order_by(Vendor.name).all()


@vendors_router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Vendor not found")
    return row


@vendors_router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if db.query(Vendor).filter(func.lower(Vendor.name) == body.name.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Vendor name already exists")
    row = Vendor(**body.model_dump(), created_by=current_user.id, modified_by=current_user.id)
    db.add(row)
    return _commit(db, row, "Vendor name already exists")


@vendors_router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID,
    body: VendorUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Vendor not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("name") and data["name"].strip().lower() != row.name.lower():
        if db.query(Vendor).filter(func.lower(Vendor.name) == data["name"].strip().lower()).first():
            raise HTTPException(status_code=400, detail="Vendor name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    return _commit(db, row, "Could not update vendor")


# ----------------------------------------------------------------- reagents ---

def _reagent_out(db: Session, row: Reagent) -> ReagentResponse:
    out = ReagentResponse.model_validate(row)
    sources = [src for src in row.sources if src.active]
    out.vendor_names = sorted({src.vendor.name for src in sources if src.vendor is not None})
    on_hand = db.query(func.coalesce(func.sum(ReagentLot.quantity_remaining), 0)).filter(
        ReagentLot.reagent_id == row.id,
        ReagentLot.active.is_(True),
        (ReagentLot.expiration_date.is_(None)) | (ReagentLot.expiration_date >= date.today()),
    ).scalar()
    out.quantity_on_hand = on_hand
    points = [src.reorder_point for src in sources if src.reorder_point is not None]
    out.below_reorder_point = bool(points) and Decimal(on_hand or 0) <= max(Decimal(p) for p in points)
    return out


@reagents_router.get("", response_model=List[ReagentResponse])
async def list_reagents(
    search: Optional[str] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _visible(db.query(Reagent), Reagent, current_user, db, active)
    if vendor_id:
        q = q.filter(Reagent.sources.any(ReagentVendor.vendor_id == vendor_id))
    if search:
        term = f"%{search}%"
        q = q.filter(Reagent.name.ilike(term) | Reagent.sources.any(ReagentVendor.catalog_number.ilike(term)))
    return [_reagent_out(db, r) for r in q.order_by(Reagent.name).all()]


@reagents_router.get("/{reagent_id}", response_model=ReagentResponse)
async def get_reagent(reagent_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Reagent).filter(Reagent.id == reagent_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Reagent not found")
    return _reagent_out(db, row)


@reagents_router.post("", response_model=ReagentResponse, status_code=status.HTTP_201_CREATED)
async def create_reagent(
    body: ReagentCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    if db.query(Reagent).filter(func.lower(Reagent.name) == body.name.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Reagent name already exists")
    row = Reagent(**body.model_dump(), created_by=current_user.id, modified_by=current_user.id)
    db.add(row)
    return _reagent_out(db, _commit(db, row, "Reagent name already exists"))


@reagents_router.patch("/{reagent_id}", response_model=ReagentResponse)
async def update_reagent(
    reagent_id: UUID,
    body: ReagentUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(Reagent).filter(Reagent.id == reagent_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reagent not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("name") and data["name"].strip().lower() != row.name.lower():
        if db.query(Reagent).filter(func.lower(Reagent.name) == data["name"].strip().lower()).first():
            raise HTTPException(status_code=400, detail="Reagent name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    return _reagent_out(db, _commit(db, row, "Could not update reagent"))


# --------------------------------------------------------- reagent vendors ---

def _source_out(row: ReagentVendor) -> ReagentVendorResponse:
    out = ReagentVendorResponse.model_validate(row)
    out.reagent_name = row.reagent.name if row.reagent is not None else None
    out.vendor_name = row.vendor.name if row.vendor is not None else None
    return out


@reagent_vendors_router.get("", response_model=List[ReagentVendorResponse])
async def list_reagent_vendors(
    reagent_id: Optional[UUID] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _visible(db.query(ReagentVendor), ReagentVendor, current_user, db, active)
    if reagent_id:
        q = q.filter(ReagentVendor.reagent_id == reagent_id)
    if vendor_id:
        q = q.filter(ReagentVendor.vendor_id == vendor_id)
    return [_source_out(r) for r in q.order_by(ReagentVendor.created_at).all()]


@reagent_vendors_router.get("/{source_id}", response_model=ReagentVendorResponse)
async def get_reagent_vendor(source_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(ReagentVendor).filter(ReagentVendor.id == source_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Reagent vendor not found")
    return _source_out(row)


@reagent_vendors_router.post("", response_model=ReagentVendorResponse, status_code=status.HTTP_201_CREATED)
async def create_reagent_vendor(
    body: ReagentVendorCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    reagent = db.query(Reagent).filter(Reagent.id == body.reagent_id).first()
    if reagent is None or not reagent.active:
        raise HTTPException(status_code=422, detail="Reagent not found or inactive")
    vendor = db.query(Vendor).filter(Vendor.id == body.vendor_id).first()
    if vendor is None or not vendor.active:
        raise HTTPException(status_code=422, detail="Vendor not found or inactive")
    exists = db.query(ReagentVendor).filter(
        ReagentVendor.reagent_id == body.reagent_id,
        ReagentVendor.vendor_id == body.vendor_id,
        ReagentVendor.catalog_number.is_not_distinct_from(body.catalog_number),
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="This vendor and catalog number are already on the reagent")
    row = ReagentVendor(**body.model_dump(), created_by=current_user.id, modified_by=current_user.id)
    db.add(row)
    return _source_out(_commit(db, row, "This vendor and catalog number are already on the reagent"))


@reagent_vendors_router.patch("/{source_id}", response_model=ReagentVendorResponse)
async def update_reagent_vendor(
    source_id: UUID,
    body: ReagentVendorUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(ReagentVendor).filter(ReagentVendor.id == source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reagent vendor not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    return _source_out(_commit(db, row, "This vendor and catalog number are already on the reagent"))


# --------------------------------------------------------------------- lots ---

def _lot_out(row: ReagentLot) -> ReagentLotResponse:
    out = ReagentLotResponse.model_validate(row)
    out.reagent_name = row.reagent.name if row.reagent is not None else None
    if row.source is not None:
        out.vendor_name = row.source.vendor.name if row.source.vendor is not None else None
        out.catalog_number = row.source.catalog_number
    out.effective_expiration_date = effective_expiration(row)
    out.expired = lot_expired(row)
    out.usable = bool(row.active and row.released and row.qc_status != "rejected" and not out.expired)
    return out


@reagent_lots_router.get("", response_model=List[ReagentLotResponse])
async def list_reagent_lots(
    reagent_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    usable: Optional[bool] = Query(None, description="Only active, unexpired lots with quantity left"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _visible(db.query(ReagentLot), ReagentLot, current_user, db, active)
    if reagent_id:
        q = q.filter(ReagentLot.reagent_id == reagent_id)
    if search:
        q = q.filter(ReagentLot.lot_number.ilike(f"%{search}%"))
    if usable:
        q = q.filter(
            ReagentLot.active.is_(True),
            ReagentLot.released.is_(True),
            ReagentLot.qc_status != "rejected",
            (ReagentLot.quantity_remaining.is_(None)) | (ReagentLot.quantity_remaining > 0),
        )
    rows = q.order_by(ReagentLot.expiration_date.asc().nullslast(), ReagentLot.lot_number).all()
    if usable:
        rows = [r for r in rows if not lot_expired(r)]
    return [_lot_out(r) for r in rows]


@reagent_lots_router.get("/{lot_id}", response_model=ReagentLotResponse)
async def get_reagent_lot(lot_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(ReagentLot).filter(ReagentLot.id == lot_id).first()
    if not row or (not row.active and not _has_config_edit(current_user, db)):
        raise HTTPException(status_code=404, detail="Reagent lot not found")
    return _lot_out(row)


def _source_for(db: Session, source_id: Optional[UUID], reagent_id: Optional[UUID]) -> Optional[ReagentVendor]:
    if source_id is None:
        return None
    source = db.query(ReagentVendor).filter(ReagentVendor.id == source_id).first()
    if source is None:
        raise HTTPException(status_code=422, detail="Reagent vendor not found")
    if reagent_id is not None and source.reagent_id != reagent_id:
        raise HTTPException(status_code=422, detail="That reagent vendor sells a different reagent")
    return source


@reagent_lots_router.post("", response_model=ReagentLotResponse, status_code=status.HTTP_201_CREATED)
async def create_reagent_lot(
    body: ReagentLotCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    source = _source_for(db, body.reagent_vendor_id, body.reagent_id)
    reagent_id = body.reagent_id or (source.reagent_id if source is not None else None)
    if reagent_id is None:
        raise HTTPException(status_code=422, detail="Give the reagent or the reagent vendor the lot was bought from")
    reagent = db.query(Reagent).filter(Reagent.id == reagent_id).first()
    if reagent is None:
        raise HTTPException(status_code=422, detail="Reagent not found")
    if not reagent.active:
        raise HTTPException(status_code=422, detail="Reagent is inactive")
    lot_number = body.lot_number.strip()
    exists = db.query(ReagentLot).filter(
        ReagentLot.reagent_id == reagent_id, ReagentLot.lot_number == lot_number
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="This lot number already exists for the reagent")
    data = body.model_dump()
    data["reagent_id"] = reagent_id
    data["lot_number"] = lot_number
    if data.get("quantity_remaining") is None:
        data["quantity_remaining"] = data.get("quantity_received")
    if not data.get("unit"):
        data["unit"] = (source.unit if source is not None else None) or reagent.unit
    if data.get("received_date") and not data.get("received_by"):
        data["received_by"] = current_user.id
    row = ReagentLot(**data, created_by=current_user.id, modified_by=current_user.id)
    db.add(row)
    return _lot_out(_commit(db, row, "This lot number already exists for the reagent"))


@reagent_lots_router.patch("/{lot_id}", response_model=ReagentLotResponse)
async def update_reagent_lot(
    lot_id: UUID,
    body: ReagentLotUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    row = db.query(ReagentLot).filter(ReagentLot.id == lot_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reagent lot not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("reagent_vendor_id"):
        _source_for(db, data["reagent_vendor_id"], row.reagent_id)
    if data.get("lot_number"):
        data["lot_number"] = data["lot_number"].strip()
    if data.get("qc_status") == "released" and "released" not in data:
        # QC release releases the lot unless the caller says otherwise.
        data["released"] = True
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    return _lot_out(_commit(db, row, "This lot number already exists for the reagent"))


# --------------------------------------------------------------------- uses ---

def _use_out(row: ReagentUse) -> ReagentUseResponse:
    out = ReagentUseResponse.model_validate(row)
    if row.lot is not None:
        out.reagent_id = row.lot.reagent_id
        out.reagent_name = row.lot.reagent.name if row.lot.reagent is not None else None
    return out


@reagent_uses_router.get("", response_model=List[ReagentUseResponse])
async def list_reagent_uses(
    lims_run_id: Optional[UUID] = Query(None),
    experiment_id: Optional[UUID] = Query(None),
    reagent_lot_id: Optional[UUID] = Query(None),
    include_voided: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ReagentUse)
    if lims_run_id:
        q = q.filter(ReagentUse.lims_run_id == lims_run_id)
    if experiment_id:
        q = q.filter(ReagentUse.experiment_id == experiment_id)
    if reagent_lot_id:
        q = q.filter(ReagentUse.reagent_lot_id == reagent_lot_id)
    if not include_voided:
        q = q.filter(ReagentUse.active.is_(True))
    return [_use_out(r) for r in q.order_by(ReagentUse.used_on.desc(), ReagentUse.created_at.desc()).limit(500).all()]


@reagent_uses_router.post("", response_model=ReagentUseResponse, status_code=status.HTTP_201_CREATED)
async def record_reagent_use(
    body: ReagentUseCreate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    from models.experiment import Experiment
    from models.flexible_experiment import LimsRun

    if body.lims_run_id is None and body.experiment_id is None:
        raise HTTPException(status_code=422, detail="Record the use on a LIMS run or an experiment")
    if body.lims_run_id is not None and not db.query(LimsRun).filter(LimsRun.id == body.lims_run_id).first():
        raise HTTPException(status_code=404, detail="LIMS run not found")
    if body.experiment_id is not None and not db.query(Experiment).filter(Experiment.id == body.experiment_id).first():
        raise HTTPException(status_code=404, detail="Experiment not found")
    lot = db.query(ReagentLot).filter(ReagentLot.id == body.reagent_lot_id).with_for_update().first()
    if lot is None:
        raise HTTPException(status_code=404, detail="Reagent lot not found")
    if not lot.active:
        raise HTTPException(status_code=422, detail=f"Lot {lot.lot_number} is inactive and can't be used")
    used_on = body.used_on or date.today()
    if not lot.released:
        raise HTTPException(status_code=422, detail=f"Lot {lot.lot_number} is not released for use")
    if lot.qc_status == "rejected":
        raise HTTPException(status_code=422, detail=f"Lot {lot.lot_number} was rejected by QC and can't be used")
    if lot_expired(lot, used_on):
        effective = effective_expiration(lot)
        why = " (opened lot past its stability)" if effective != lot.expiration_date else ""
        raise HTTPException(
            status_code=422,
            detail=f"Lot {lot.lot_number} expired on {effective.isoformat()}{why} and can't be used",
        )
    quantity = Decimal(body.quantity_used)
    if body.unit and lot.unit and body.unit.strip().lower() != lot.unit.strip().lower():
        raise HTTPException(
            status_code=422,
            detail=f"Lot {lot.lot_number} is counted in {lot.unit}; enter the quantity in {lot.unit}",
        )
    if lot.quantity_remaining is not None:
        if quantity > Decimal(lot.quantity_remaining):
            raise HTTPException(
                status_code=422,
                detail=f"Lot {lot.lot_number} has {lot.quantity_remaining} {lot.unit or ''} left".strip(),
            )
        lot.quantity_remaining = Decimal(lot.quantity_remaining) - quantity
        lot.modified_by = current_user.id
    row = ReagentUse(
        reagent_lot_id=lot.id,
        lims_run_id=body.lims_run_id,
        experiment_id=body.experiment_id,
        analysis_id=body.analysis_id,
        lot_number=lot.lot_number,
        expiration_date=effective_expiration(lot),
        used_on=used_on,
        quantity_used=quantity,
        unit=lot.unit,
        note=body.note,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    return _use_out(_commit(db, row, "Could not record reagent use"))


@reagent_uses_router.patch("/{use_id}", response_model=ReagentUseResponse)
async def update_reagent_use(
    use_id: UUID,
    body: ReagentUseUpdate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    """Void a use (active false; the quantity goes back to the lot) or edit its note."""
    row = db.query(ReagentUse).filter(ReagentUse.id == use_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reagent use not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("active") is True and not row.active:
        raise HTTPException(status_code=422, detail="A voided use stays voided. Record the use again.")
    if data.get("active") is False and row.active:
        row.active = False
        lot = db.query(ReagentLot).filter(ReagentLot.id == row.reagent_lot_id).with_for_update().first()
        if lot is not None and lot.quantity_remaining is not None:
            lot.quantity_remaining = Decimal(lot.quantity_remaining) + Decimal(row.quantity_used)
            lot.modified_by = current_user.id
    if "note" in data:
        row.note = data["note"]
    row.modified_by = current_user.id
    return _use_out(_commit(db, row, "Could not update reagent use"))
