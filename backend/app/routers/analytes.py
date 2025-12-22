"""
Analytes router for LIMS MVP
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.analysis import Analyte, AnalysisAnalyte
from models.user import User
from app.schemas.analyte import AnalyteResponse, AnalyteCreate, AnalyteUpdate
from app.core.security import get_current_user
from app.core.rbac import require_any_permission
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[AnalyteResponse])
async def get_analytes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active analytes.
    """
    analytes = db.query(Analyte).filter(Analyte.active == True).order_by(Analyte.name).all()
    return [AnalyteResponse.from_orm(analyte) for analyte in analytes]


@router.post("", response_model=AnalyteResponse, status_code=status.HTTP_201_CREATED)
async def create_analyte(
    analyte_data: AnalyteCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analyte.
    Requires config:edit or test:configure permission.
    """
    # Check for unique name
    existing_analyte = db.query(Analyte).filter(Analyte.name == analyte_data.name).first()
    if existing_analyte:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyte name already exists"
        )
    
    new_analyte = Analyte(
        name=analyte_data.name,
        description=analyte_data.description,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_analyte)
    db.commit()
    db.refresh(new_analyte)
    
    return AnalyteResponse.from_orm(new_analyte)


@router.patch("/{analyte_id}", response_model=AnalyteResponse)
async def update_analyte(
    analyte_id: UUID,
    analyte_data: AnalyteUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update an analyte.
    Requires config:edit or test:configure permission.
    """
    analyte = db.query(Analyte).filter(Analyte.id == analyte_id).first()
    if not analyte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyte not found"
        )
    
    # Check for unique name if updating
    if analyte_data.name and analyte_data.name != analyte.name:
        existing_analyte = db.query(Analyte).filter(Analyte.name == analyte_data.name).first()
        if existing_analyte:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analyte name already exists"
            )
        analyte.name = analyte_data.name
    
    if analyte_data.description is not None:
        analyte.description = analyte_data.description
    
    if analyte_data.active is not None:
        analyte.active = analyte_data.active
    
    analyte.modified_by = current_user.id
    db.commit()
    db.refresh(analyte)
    
    return AnalyteResponse.from_orm(analyte)


@router.delete("/{analyte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analyte(
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete an analyte.
    Requires config:edit or test:configure permission.
    Fails if analyte is referenced in any analyses.
    """
    analyte = db.query(Analyte).filter(Analyte.id == analyte_id).first()
    if not analyte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyte not found"
        )
    
    # Check if analyte is referenced in any analyses
    analyses_count = db.query(AnalysisAnalyte).filter(
        AnalysisAnalyte.analyte_id == analyte_id
    ).count()
    
    if analyses_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete analyte: {analyses_count} analysis/analyses reference this analyte"
        )
    
    analyte.active = False
    analyte.modified_by = current_user.id
    db.commit()
    
    return None

