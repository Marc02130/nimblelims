"""
Analyses router for NimbleLIMS
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.database import get_db
from models.analysis import Analysis, Analyte, AnalysisAnalyte
from models.user import User
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisListResponse,
    AnalysisCreate,
    AnalysisUpdate,
    AnalyteRuleResponse,
    AnalyteRuleCreate,
    AnalyteRuleUpdate,
    AnalyteLinkRequest,
    AnalyteSimple,
)
from app.core.security import get_current_user, get_user_permissions
from app.core.rbac import require_any_permission
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_analysis_response(analysis: Analysis) -> AnalysisResponse:
    """Helper to build AnalysisResponse from Analysis model"""
    return AnalysisResponse(
        id=analysis.id,
        name=analysis.name,
        description=analysis.description,
        active=analysis.active,
        created_at=analysis.created_at,
        modified_at=analysis.modified_at,
        created_by=analysis.created_by,
        modified_by=analysis.modified_by,
        method=analysis.method,
        turnaround_time=analysis.turnaround_time,
        cost=analysis.cost,
        shelf_life=analysis.shelf_life,
        custom_attributes=analysis.custom_attributes or {},
        analytes=[
            AnalyteSimple(id=a.id, name=a.name, description=a.description)
            for a in analysis.analytes if a.active
        ],
    )


@router.get("", response_model=AnalysisListResponse)
async def get_analyses(
    search: Optional[str] = Query(None, description="Search by name or method (ilike)"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analyses with optional filtering and pagination.
    - search: Filter by name or method (case-insensitive)
    - active: Filter by active status (default: show all for config:edit users, only active for others)
    - Supports pagination via page and size parameters
    """
    try:
        # Check if user has config:edit permission
        user_permissions = get_user_permissions(current_user, db)
        has_config_edit = "config:edit" in user_permissions
        
        # Base query with eager loading of analytes
        query = db.query(Analysis).options(joinedload(Analysis.analytes))
        
        # Apply active filter
        if active is not None:
            query = query.filter(Analysis.active == active)
        elif not has_config_edit:
            # For non-config users, default to only active
            query = query.filter(Analysis.active == True)
        
        # Apply search filter (ilike on name and method)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Analysis.name.ilike(search_pattern),
                    Analysis.method.ilike(search_pattern)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        analyses = query.order_by(Analysis.name).offset(offset).limit(size).all()
        
        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 0
        
        # Build response
        result = [_build_analysis_response(analysis) for analysis in analyses]
        
        return AnalysisListResponse(
            analyses=result,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except Exception as e:
        logger.error(f"Error in get_analyses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analyses: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single analysis by ID.
    Returns 404 if analysis not found.
    """
    try:
        analysis = db.query(Analysis).options(
            joinedload(Analysis.analytes)
        ).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        return _build_analysis_response(analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    analysis_data: AnalysisCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    - name must be unique (auto-generated if not provided)
    - method is required
    """
    try:
        # Generate name if not provided
        analysis_name = analysis_data.name
        if not analysis_name:
            from app.core.name_generation import generate_name_for_analysis
            try:
                analysis_name = generate_name_for_analysis(db=db)
            except Exception as e:
                # Fallback to UUID if generation fails
                import uuid
                analysis_name = str(uuid.uuid4())
        
        # Check for unique name
        existing_analysis = db.query(Analysis).filter(Analysis.name == analysis_name).first()
        if existing_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analysis name already exists"
            )
        
        new_analysis = Analysis(
            name=analysis_name,
            description=analysis_data.description,
            method=analysis_data.method,
            turnaround_time=analysis_data.turnaround_time,
            cost=analysis_data.cost,
            shelf_life=analysis_data.shelf_life,
            custom_attributes=analysis_data.custom_attributes or {},
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        
        return _build_analysis_response(new_analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analysis: {str(e)}"
        )


@router.patch("/{analysis_id}", response_model=AnalysisResponse)
async def update_analysis(
    analysis_id: UUID,
    analysis_data: AnalysisUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Update an analysis (partial update).
    Requires config:edit, test:configure, or analysis:manage permission.
    Updates audit fields (modified_by, modified_at).
    """
    try:
        analysis = db.query(Analysis).options(
            joinedload(Analysis.analytes)
        ).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Check for unique name if updating
        if analysis_data.name and analysis_data.name != analysis.name:
            existing_analysis = db.query(Analysis).filter(Analysis.name == analysis_data.name).first()
            if existing_analysis:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Analysis name already exists"
                )
            analysis.name = analysis_data.name
        
        if analysis_data.description is not None:
            analysis.description = analysis_data.description
        
        if analysis_data.method is not None:
            analysis.method = analysis_data.method
        
        if analysis_data.turnaround_time is not None:
            analysis.turnaround_time = analysis_data.turnaround_time
        
        if analysis_data.cost is not None:
            analysis.cost = analysis_data.cost
        
        if analysis_data.shelf_life is not None:
            analysis.shelf_life = analysis_data.shelf_life
        
        if analysis_data.active is not None:
            analysis.active = analysis_data.active
        
        if analysis_data.custom_attributes is not None:
            analysis.custom_attributes = analysis_data.custom_attributes
        
        analysis.modified_by = current_user.id
        db.commit()
        db.refresh(analysis)
        
        return _build_analysis_response(analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analysis: {str(e)}"
        )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete an analysis (sets active=false).
    Requires config:edit, test:configure, or analysis:manage permission.
    Fails if analysis is referenced in any active tests.
    """
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Check if analysis is referenced in any active tests
        from models.test import Test
        tests_count = db.query(Test).filter(Test.analysis_id == analysis_id, Test.active == True).count()
        if tests_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete analysis: {tests_count} active test(s) reference this analysis"
            )
        
        analysis.active = False
        analysis.modified_by = current_user.id
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete analysis: {str(e)}"
        )


# ============================================================================
# Analysis-Analyte Relationship Endpoints
# ============================================================================

@router.get("/{analysis_id}/analytes", response_model=List[AnalyteSimple])
async def get_analysis_analytes(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analytes linked to an analysis.
    """
    try:
        analysis = db.query(Analysis).options(
            joinedload(Analysis.analytes)
        ).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        return [
            AnalyteSimple(id=a.id, name=a.name, description=a.description)
            for a in analysis.analytes if a.active
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analysis_analytes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytes: {str(e)}"
        )


@router.post("/{analysis_id}/analytes", response_model=List[AnalyteSimple], status_code=status.HTTP_201_CREATED)
async def link_analytes_to_analysis(
    analysis_id: UUID,
    link_request: AnalyteLinkRequest,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Link existing analyte(s) to an analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    Skips analytes that are already linked (idempotent).
    """
    try:
        analysis = db.query(Analysis).options(
            joinedload(Analysis.analytes)
        ).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get existing linked analyte IDs
        existing_ids = {a.id for a in analysis.analytes}
        
        # Verify all analyte IDs exist and are active
        analytes = db.query(Analyte).filter(
            Analyte.id.in_(link_request.analyte_ids),
            Analyte.active == True
        ).all()
        
        found_ids = {a.id for a in analytes}
        missing_ids = set(link_request.analyte_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or inactive analyte IDs: {[str(id) for id in missing_ids]}"
            )
        
        # Link new analytes (skip existing)
        new_analytes = [a for a in analytes if a.id not in existing_ids]
        for analyte in new_analytes:
            analysis.analytes.append(analyte)
        
        analysis.modified_by = current_user.id
        db.commit()
        db.refresh(analysis)
        
        return [
            AnalyteSimple(id=a.id, name=a.name, description=a.description)
            for a in analysis.analytes if a.active
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in link_analytes_to_analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link analytes: {str(e)}"
        )


@router.put("/{analysis_id}/analytes", response_model=List[AnalyteSimple])
async def update_analysis_analytes(
    analysis_id: UUID,
    analyte_ids: dict,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Replace all analytes for an analysis (full replacement).
    Requires config:edit, test:configure, or analysis:manage permission.
    """
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get analyte IDs from request
        ids = analyte_ids.get("analyte_ids", [])
        
        # Verify all analyte IDs exist
        analytes = db.query(Analyte).filter(
            Analyte.id.in_([UUID(id) if isinstance(id, str) else id for id in ids]),
            Analyte.active == True
        ).all()
        
        if len(analytes) != len(ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more analyte IDs are invalid"
            )
        
        # Clear existing analytes and set new ones
        analysis.analytes = analytes
        analysis.modified_by = current_user.id
        db.commit()
        db.refresh(analysis)
        
        return [
            AnalyteSimple(id=a.id, name=a.name, description=a.description)
            for a in analysis.analytes if a.active
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_analysis_analytes: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analytes: {str(e)}"
        )


@router.delete("/{analysis_id}/analytes/{analyte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_analyte_from_analysis(
    analysis_id: UUID,
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Unlink a single analyte from an analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    """
    try:
        analysis = db.query(Analysis).options(
            joinedload(Analysis.analytes)
        ).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Find the analyte to remove
        analyte_to_remove = None
        for analyte in analysis.analytes:
            if analyte.id == analyte_id:
                analyte_to_remove = analyte
                break
        
        if not analyte_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyte not linked to this analysis"
            )
        
        analysis.analytes.remove(analyte_to_remove)
        analysis.modified_by = current_user.id
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unlink_analyte_from_analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink analyte: {str(e)}"
        )


# ============================================================================
# Analysis-Analyte Rules Endpoints (for configuring validation rules)
# ============================================================================

@router.get("/{analysis_id}/analyte-rules", response_model=List[AnalyteRuleResponse])
async def get_analysis_analyte_rules(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analyte rules for an analysis.
    """
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get all analysis_analytes entries for this analysis
        rules = db.query(AnalysisAnalyte).filter(
            AnalysisAnalyte.analysis_id == analysis_id
        ).all()
        
        result = []
        for rule in rules:
            if rule.analyte and rule.analyte.active:
                result.append(AnalyteRuleResponse(
                    analyte_id=rule.analyte_id,
                    analyte_name=rule.analyte.name,
                    data_type=rule.data_type,
                    list_id=rule.list_id,
                    high_value=rule.high_value,
                    low_value=rule.low_value,
                    significant_figures=rule.significant_figures,
                    calculation=rule.calculation,
                    reported_name=rule.reported_name,
                    display_order=rule.display_order,
                    is_required=rule.is_required,
                    default_value=rule.default_value,
                ))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analysis_analyte_rules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analyte rules: {str(e)}"
        )


@router.post("/{analysis_id}/analyte-rules", response_model=AnalyteRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_analyte_rule(
    analysis_id: UUID,
    rule_data: AnalyteRuleCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analyte rule for an analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    """
    try:
        # Verify analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Verify analyte exists
        analyte = db.query(Analyte).filter(
            Analyte.id == rule_data.analyte_id,
            Analyte.active == True
        ).first()
        if not analyte:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid analyte_id"
            )
        
        # Check if rule already exists
        existing_rule = db.query(AnalysisAnalyte).filter(
            AnalysisAnalyte.analysis_id == analysis_id,
            AnalysisAnalyte.analyte_id == rule_data.analyte_id
        ).first()
        if existing_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analyte rule already exists for this analysis"
            )
        
        # Validate low <= high if both are provided
        if rule_data.low_value is not None and rule_data.high_value is not None:
            if rule_data.low_value > rule_data.high_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Low value must be less than or equal to high value"
                )
        
        # Create rule
        new_rule = AnalysisAnalyte(
            analysis_id=analysis_id,
            analyte_id=rule_data.analyte_id,
            data_type=rule_data.data_type,
            list_id=rule_data.list_id,
            high_value=rule_data.high_value,
            low_value=rule_data.low_value,
            significant_figures=rule_data.significant_figures,
            calculation=rule_data.calculation,
            reported_name=rule_data.reported_name,
            display_order=rule_data.display_order,
            is_required=rule_data.is_required,
            default_value=rule_data.default_value,
        )
        
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return AnalyteRuleResponse(
            analyte_id=new_rule.analyte_id,
            analyte_name=analyte.name,
            data_type=new_rule.data_type,
            list_id=new_rule.list_id,
            high_value=new_rule.high_value,
            low_value=new_rule.low_value,
            significant_figures=new_rule.significant_figures,
            calculation=new_rule.calculation,
            reported_name=new_rule.reported_name,
            display_order=new_rule.display_order,
            is_required=new_rule.is_required,
            default_value=new_rule.default_value,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_analysis_analyte_rule: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analyte rule: {str(e)}"
        )


@router.patch("/{analysis_id}/analyte-rules/{analyte_id}", response_model=AnalyteRuleResponse)
async def update_analysis_analyte_rule(
    analysis_id: UUID,
    analyte_id: UUID,
    rule_data: AnalyteRuleUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Update an analyte rule for an analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    """
    try:
        # Verify analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get existing rule
        rule = db.query(AnalysisAnalyte).filter(
            AnalysisAnalyte.analysis_id == analysis_id,
            AnalysisAnalyte.analyte_id == analyte_id
        ).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyte rule not found"
            )
        
        # Validate low <= high if both are provided
        low_value = rule_data.low_value if rule_data.low_value is not None else rule.low_value
        high_value = rule_data.high_value if rule_data.high_value is not None else rule.high_value
        if low_value is not None and high_value is not None:
            if low_value > high_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Low value must be less than or equal to high value"
                )
        
        # Update rule fields
        if rule_data.data_type is not None:
            rule.data_type = rule_data.data_type
        if rule_data.list_id is not None:
            rule.list_id = rule_data.list_id
        if rule_data.high_value is not None:
            rule.high_value = rule_data.high_value
        if rule_data.low_value is not None:
            rule.low_value = rule_data.low_value
        if rule_data.significant_figures is not None:
            rule.significant_figures = rule_data.significant_figures
        if rule_data.calculation is not None:
            rule.calculation = rule_data.calculation
        if rule_data.reported_name is not None:
            rule.reported_name = rule_data.reported_name
        if rule_data.display_order is not None:
            rule.display_order = rule_data.display_order
        if rule_data.is_required is not None:
            rule.is_required = rule_data.is_required
        if rule_data.default_value is not None:
            rule.default_value = rule_data.default_value
        
        db.commit()
        db.refresh(rule)
        
        analyte = rule.analyte
        return AnalyteRuleResponse(
            analyte_id=rule.analyte_id,
            analyte_name=analyte.name if analyte else "Unknown",
            data_type=rule.data_type,
            list_id=rule.list_id,
            high_value=rule.high_value,
            low_value=rule.low_value,
            significant_figures=rule.significant_figures,
            calculation=rule.calculation,
            reported_name=rule.reported_name,
            display_order=rule.display_order,
            is_required=rule.is_required,
            default_value=rule.default_value,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_analysis_analyte_rule: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analyte rule: {str(e)}"
        )


@router.delete("/{analysis_id}/analyte-rules/{analyte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_analyte_rule(
    analysis_id: UUID,
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure", "analysis:manage"])),
    db: Session = Depends(get_db)
):
    """
    Delete an analyte rule for an analysis.
    Requires config:edit, test:configure, or analysis:manage permission.
    """
    try:
        # Verify analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get existing rule
        rule = db.query(AnalysisAnalyte).filter(
            AnalysisAnalyte.analysis_id == analysis_id,
            AnalysisAnalyte.analyte_id == analyte_id
        ).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyte rule not found"
            )
        
        db.delete(rule)
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_analysis_analyte_rule: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete analyte rule: {str(e)}"
        )
