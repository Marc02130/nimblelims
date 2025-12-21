"""
Analyses router for LIMS MVP
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from models.analysis import Analysis
from models.user import User
from app.core.security import get_current_user
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class AnalysisResponse(BaseModel):
    """Schema for analysis response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    method: Optional[str] = None
    turnaround_time: Optional[int] = None
    cost: Optional[float] = None

    class Config:
        from_attributes = True


router = APIRouter()


@router.get("", response_model=List[AnalysisResponse])
async def get_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active analyses.
    """
    analyses = db.query(Analysis).filter(Analysis.active == True).order_by(Analysis.name).all()
    return [AnalysisResponse.from_orm(analysis) for analysis in analyses]

