"""
Units router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from models.unit import Unit
from models.user import User
from app.core.security import get_current_user
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

    class Config:
        from_attributes = True


router = APIRouter()


@router.get("", response_model=List[UnitResponse])
async def get_units(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active units.
    """
    units = db.query(Unit).filter(Unit.active == True).order_by(Unit.name).all()
    return [UnitResponse.from_orm(unit) for unit in units]

