"""
Units router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from models.unit import Unit
from models.user import User
from models.list import ListEntry
from app.core.security import get_current_user, get_user_permissions
from app.core.rbac import require_config_edit
from app.core.conversions import (
    ConversionError,
    assert_multiplier_for_save,
    active_base_units,
    designate_base_unit,
    is_base_multiplier,
)
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal


class UnitResponse(BaseModel):
    """Schema for unit response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    multiplier: Optional[Decimal] = None
    type: UUID
    type_name: Optional[str] = None  # Name of the unit type (concentration, mass, volume, molar)
    is_base: bool = False  # True when multiplier is 1, the lab's base for this type

    class Config:
        from_attributes = True


class UnitCreate(BaseModel):
    """Schema for creating a unit"""
    name: str
    description: Optional[str] = None
    multiplier: Decimal
    type: UUID  # UUID of the unit type list entry


class UnitUpdate(BaseModel):
    """Schema for updating a unit"""
    name: Optional[str] = None
    description: Optional[str] = None
    multiplier: Optional[Decimal] = None
    type: Optional[UUID] = None
    active: Optional[bool] = None


router = APIRouter()


def _unit_response(unit: Unit) -> UnitResponse:
    return UnitResponse(
        id=unit.id,
        name=unit.name,
        description=unit.description,
        active=unit.active,
        created_at=unit.created_at,
        modified_at=unit.modified_at,
        multiplier=unit.multiplier,
        type=unit.type,
        type_name=unit.type_rel.name if unit.type_rel else None,
        is_base=is_base_multiplier(unit.multiplier),
    )


def _reject_multiplier(exc: ConversionError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=List[UnitResponse])
async def get_units(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all units.
    For users with config:edit permission, returns all units (active and inactive).
    For other users, returns only active units.
    Includes type_name for frontend filtering.
    """
    # Check if user has config:edit permission
    user_permissions = get_user_permissions(current_user, db)
    has_config_edit = "config:edit" in user_permissions
    
    # If user has config:edit permission, show all units; otherwise, only active
    if has_config_edit:
        units = db.query(Unit).options(joinedload(Unit.type_rel)).order_by(Unit.name).all()
    else:
        units = db.query(Unit).options(joinedload(Unit.type_rel)).filter(Unit.active == True).order_by(Unit.name).all()
    
    return [_unit_response(unit) for unit in units]


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    unit_data: UnitCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new unit.
    Requires config:edit permission.
    """
    # Check for unique name
    existing_unit = db.query(Unit).filter(Unit.name == unit_data.name).first()
    if existing_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit name already exists"
        )
    
    # Verify unit type exists
    unit_type = db.query(ListEntry).filter(ListEntry.id == unit_data.type).first()
    if not unit_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid unit type"
        )
    try:
        multiplier = assert_multiplier_for_save(
            db, type_id=unit_data.type, multiplier=unit_data.multiplier
        )
    except ConversionError as exc:
        _reject_multiplier(exc)

    new_unit = Unit(
        name=unit_data.name,
        description=unit_data.description,
        multiplier=multiplier,
        type=unit_data.type,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_unit)
    db.commit()
    
    unit = db.query(Unit).options(joinedload(Unit.type_rel)).filter(Unit.id == new_unit.id).first()
    return _unit_response(unit)


@router.patch("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: UUID,
    unit_data: UnitUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a unit.
    Requires config:edit permission.
    """
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Check for unique name if updating
    if unit_data.name and unit_data.name != unit.name:
        existing_unit = db.query(Unit).filter(Unit.name == unit_data.name).first()
        if existing_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit name already exists"
            )
        unit.name = unit_data.name
    
    if unit_data.description is not None:
        unit.description = unit_data.description
    new_type = unit.type
    if unit_data.type is not None:
        unit_type = db.query(ListEntry).filter(ListEntry.id == unit_data.type).first()
        if not unit_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit type"
            )
        new_type = unit_data.type
    new_multiplier = unit.multiplier if unit_data.multiplier is None else unit_data.multiplier
    if new_multiplier is not None:
        try:
            checked = assert_multiplier_for_save(
                db, type_id=new_type, multiplier=new_multiplier, current=unit
            )
        except ConversionError as exc:
            _reject_multiplier(exc)
        unit.multiplier = checked
    unit.type = new_type
    if unit_data.active is not None:
        unit.active = unit_data.active
    
    unit.modified_by = current_user.id
    db.commit()
    
    updated_unit = db.query(Unit).options(joinedload(Unit.type_rel)).filter(Unit.id == unit_id).first()
    return _unit_response(updated_unit)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft delete a unit (set active=False).
    Requires config:edit permission.
    """
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    if is_base_multiplier(unit.multiplier):
        other_bases = [base for base in active_base_units(db, unit.type) if base.id != unit.id]
        other_active = (
            db.query(Unit)
            .filter(Unit.type == unit.type, Unit.active == True, Unit.id != unit.id)  # noqa: E712
            .count()
        )
        if not other_bases and other_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pick another unit as the base before deactivating this one.",
            )

    unit.active = False
    unit.modified_by = current_user.id
    db.commit()

    return None


@router.post("/{unit_id}/base", response_model=UnitResponse)
async def set_base_unit(
    unit_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """Make this unit the base for its type. Its multiplier becomes 1.

    Other units of the type are rescaled so a quantity still converts to the
    same amount. Requires config:edit.
    """
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    try:
        designate_base_unit(db, unit)
    except ConversionError as exc:
        db.rollback()
        _reject_multiplier(exc)
    unit.modified_by = current_user.id
    db.commit()
    updated = db.query(Unit).options(joinedload(Unit.type_rel)).filter(Unit.id == unit_id).first()
    return _unit_response(updated)

