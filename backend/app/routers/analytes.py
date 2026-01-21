"""
Analytes router for NimbleLIMS
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from models.analysis import Analyte, AnalysisAnalyte
from models.user import User
from app.schemas.analyte import (
    AnalyteResponse,
    AnalyteListResponse,
    AnalyteCreate,
    AnalyteUpdate,
)
from app.core.security import get_current_user, get_user_permissions
from app.core.rbac import require_any_permission
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_analyte_response(analyte: Analyte) -> AnalyteResponse:
    """Helper to build AnalyteResponse from Analyte model"""
    return AnalyteResponse(
        id=analyte.id,
        name=analyte.name,
        description=analyte.description,
        active=analyte.active,
        created_at=analyte.created_at,
        modified_at=analyte.modified_at,
        created_by=analyte.created_by,
        modified_by=analyte.modified_by,
        cas_number=analyte.cas_number if hasattr(analyte, 'cas_number') else None,
        units_default=analyte.units_default if hasattr(analyte, 'units_default') else None,
        data_type=analyte.data_type if hasattr(analyte, 'data_type') else None,
        custom_attributes=analyte.custom_attributes if hasattr(analyte, 'custom_attributes') and analyte.custom_attributes else {},
    )


@router.get("", response_model=AnalyteListResponse)
async def get_analytes(
    search: Optional[str] = Query(None, description="Search by name or CAS number (ilike)"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analytes with optional filtering and pagination.
    - search: Filter by name or CAS number (case-insensitive)
    - active: Filter by active status (default: show all for config:edit users, only active for others)
    - Supports pagination via page and size parameters
    """
    try:
        # Check if user has config:edit permission
        user_permissions = get_user_permissions(current_user, db)
        has_config_edit = "config:edit" in user_permissions
        
        # Base query
        query = db.query(Analyte)
        
        # Apply active filter
        if active is not None:
            query = query.filter(Analyte.active == active)
        elif not has_config_edit:
            # For non-config users, default to only active
            query = query.filter(Analyte.active == True)
        
        # Apply search filter (ilike on name and cas_number)
        if search:
            search_pattern = f"%{search}%"
            # Handle case where cas_number column may not exist yet
            if hasattr(Analyte, 'cas_number'):
                query = query.filter(
                    or_(
                        Analyte.name.ilike(search_pattern),
                        Analyte.cas_number.ilike(search_pattern)
                    )
                )
            else:
                query = query.filter(Analyte.name.ilike(search_pattern))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        analytes = query.order_by(Analyte.name).offset(offset).limit(size).all()
        
        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 0
        
        # Build response
        result = [_build_analyte_response(analyte) for analyte in analytes]
        
        return AnalyteListResponse(
            analytes=result,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except Exception as e:
        logger.error(f"Error in get_analytes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytes: {str(e)}"
        )


@router.get("/{analyte_id}", response_model=AnalyteResponse)
async def get_analyte(
    analyte_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single analyte by ID.
    Returns 404 if analyte not found.
    """
    try:
        analyte = db.query(Analyte).filter(Analyte.id == analyte_id).first()
        
        if not analyte:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyte not found"
            )
        
        return _build_analyte_response(analyte)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analyte: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analyte: {str(e)}"
        )


@router.post("", response_model=AnalyteResponse, status_code=status.HTTP_201_CREATED)
async def create_analyte(
    analyte_data: AnalyteCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analyte.
    Requires config:edit, test:configure, or analysis:manage permission.
    - name must be unique
    """
    try:
        # Check for unique name
        existing_analyte = db.query(Analyte).filter(Analyte.name == analyte_data.name).first()
        if existing_analyte:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analyte name already exists"
            )
        
        # Validate units_default if provided
        if analyte_data.units_default:
            from models.unit import Unit
            unit = db.query(Unit).filter(Unit.id == analyte_data.units_default).first()
            if not unit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid units_default: unit not found"
                )
        
        new_analyte = Analyte(
            name=analyte_data.name,
            description=analyte_data.description,
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        
        # Set optional fields if they exist on the model
        if hasattr(new_analyte, 'cas_number') and analyte_data.cas_number:
            new_analyte.cas_number = analyte_data.cas_number
        if hasattr(new_analyte, 'units_default') and analyte_data.units_default:
            new_analyte.units_default = analyte_data.units_default
        if hasattr(new_analyte, 'data_type') and analyte_data.data_type:
            new_analyte.data_type = analyte_data.data_type.value if analyte_data.data_type else None
        if hasattr(new_analyte, 'custom_attributes'):
            new_analyte.custom_attributes = analyte_data.custom_attributes or {}
        
        db.add(new_analyte)
        db.commit()
        db.refresh(new_analyte)
        
        return _build_analyte_response(new_analyte)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_analyte: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analyte: {str(e)}"
        )


@router.patch("/{analyte_id}", response_model=AnalyteResponse)
async def update_analyte(
    analyte_id: UUID,
    analyte_data: AnalyteUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Update an analyte (partial update).
    Requires config:edit, test:configure, or analysis:manage permission.
    Updates audit fields (modified_by, modified_at).
    """
    try:
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
        
        # Update optional fields if they exist on the model
        if hasattr(analyte, 'cas_number') and analyte_data.cas_number is not None:
            analyte.cas_number = analyte_data.cas_number
        
        if hasattr(analyte, 'units_default') and analyte_data.units_default is not None:
            # Validate units_default if provided
            if analyte_data.units_default:
                from models.unit import Unit
                unit = db.query(Unit).filter(Unit.id == analyte_data.units_default).first()
                if not unit:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid units_default: unit not found"
                    )
            analyte.units_default = analyte_data.units_default
        
        if hasattr(analyte, 'data_type') and analyte_data.data_type is not None:
            analyte.data_type = analyte_data.data_type.value if analyte_data.data_type else None
        
        if hasattr(analyte, 'custom_attributes') and analyte_data.custom_attributes is not None:
            analyte.custom_attributes = analyte_data.custom_attributes
        
        analyte.modified_by = current_user.id
        db.commit()
        db.refresh(analyte)
        
        return _build_analyte_response(analyte)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_analyte: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analyte: {str(e)}"
        )


@router.delete("/{analyte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analyte(
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete an analyte (sets active=false).
    Requires config:edit, test:configure, or analysis:manage permission.
    Fails if analyte is referenced in any analyses.
    """
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_analyte: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete analyte: {str(e)}"
        )
