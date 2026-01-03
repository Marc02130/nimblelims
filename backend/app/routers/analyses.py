"""
Analyses router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.analysis import Analysis, Analyte, AnalysisAnalyte
from models.user import User
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisCreate,
    AnalysisUpdate,
    AnalyteRuleResponse,
    AnalyteRuleCreate,
    AnalyteRuleUpdate,
)
from app.core.security import get_current_user
from app.core.rbac import require_any_permission
from uuid import UUID

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


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    analysis_data: AnalysisCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analysis.
    Requires config:edit or test:configure permission.
    """
    # Check for unique name
    existing_analysis = db.query(Analysis).filter(Analysis.name == analysis_data.name).first()
    if existing_analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis name already exists"
        )
    
    new_analysis = Analysis(
        name=analysis_data.name,
        description=analysis_data.description,
        method=analysis_data.method,
        turnaround_time=analysis_data.turnaround_time,
        cost=analysis_data.cost,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)
    
    return AnalysisResponse.from_orm(new_analysis)


@router.patch("/{analysis_id}", response_model=AnalysisResponse)
async def update_analysis(
    analysis_id: UUID,
    analysis_data: AnalysisUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update an analysis.
    Requires config:edit or test:configure permission.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
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
    
    if analysis_data.active is not None:
        analysis.active = analysis_data.active
    
    analysis.modified_by = current_user.id
    db.commit()
    db.refresh(analysis)
    
    return AnalysisResponse.from_orm(analysis)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete an analysis.
    Requires config:edit or test:configure permission.
    Fails if analysis is referenced in any tests.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Check if analysis is referenced in any tests
    from models.test import Test
    tests_count = db.query(Test).filter(Test.analysis_id == analysis_id, Test.active == True).count()
    if tests_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete analysis: {tests_count} test(s) reference this analysis"
        )
    
    analysis.active = False
    analysis.modified_by = current_user.id
    db.commit()
    
    return None


@router.get("/{analysis_id}/analytes", response_model=List[dict])
async def get_analysis_analytes(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analytes for an analysis (simple list for assignment).
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Get analytes via the many-to-many relationship
    analytes = analysis.analytes
    return [{"id": str(a.id), "name": a.name, "description": a.description} for a in analytes if a.active]


@router.put("/{analysis_id}/analytes", response_model=List[dict])
async def update_analysis_analytes(
    analysis_id: UUID,
    analyte_ids: dict,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update analytes for an analysis (simple assignment).
    Requires config:edit or test:configure permission.
    """
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
        Analyte.id.in_([UUID(id) for id in ids]),
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
    
    return [{"id": str(a.id), "name": a.name, "description": a.description} for a in analysis.analytes if a.active]


# Analysis-Analyte Rules endpoints (for configuring validation rules)
@router.get("/{analysis_id}/analyte-rules", response_model=List[AnalyteRuleResponse])
async def get_analysis_analyte_rules(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analyte rules for an analysis.
    """
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
            result.append({
                "analyte_id": rule.analyte_id,
                "analyte_name": rule.analyte.name,
                "data_type": rule.data_type,
                "list_id": rule.list_id,
                "high_value": rule.high_value,
                "low_value": rule.low_value,
                "significant_figures": rule.significant_figures,
                "calculation": rule.calculation,
                "reported_name": rule.reported_name,
                "display_order": rule.display_order,
                "is_required": rule.is_required,
                "default_value": rule.default_value,
            })
    
    return result


@router.post("/{analysis_id}/analyte-rules", response_model=AnalyteRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_analyte_rule(
    analysis_id: UUID,
    rule_data: AnalyteRuleCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Create a new analyte rule for an analysis.
    Requires config:edit or test:configure permission.
    """
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
    # Note: AnalysisAnalyte is a junction table with composite primary key (analysis_id, analyte_id)
    # It does NOT have id, name, active, created_at, modified_at fields in the database
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
    
    return {
        "analyte_id": new_rule.analyte_id,
        "analyte_name": analyte.name,
        "data_type": new_rule.data_type,
        "list_id": new_rule.list_id,
        "high_value": new_rule.high_value,
        "low_value": new_rule.low_value,
        "significant_figures": new_rule.significant_figures,
        "calculation": new_rule.calculation,
        "reported_name": new_rule.reported_name,
        "display_order": new_rule.display_order,
        "is_required": new_rule.is_required,
        "default_value": new_rule.default_value,
    }


@router.patch("/{analysis_id}/analyte-rules/{analyte_id}", response_model=AnalyteRuleResponse)
async def update_analysis_analyte_rule(
    analysis_id: UUID,
    analyte_id: UUID,
    rule_data: AnalyteRuleUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update an analyte rule for an analysis.
    Requires config:edit or test:configure permission.
    """
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
    
    # Note: AnalysisAnalyte doesn't have modified_by field in database
    db.commit()
    db.refresh(rule)
    
    analyte = rule.analyte
    return {
        "analyte_id": rule.analyte_id,
        "analyte_name": analyte.name if analyte else "Unknown",
        "data_type": rule.data_type,
        "list_id": rule.list_id,
        "high_value": rule.high_value,
        "low_value": rule.low_value,
        "significant_figures": rule.significant_figures,
        "calculation": rule.calculation,
        "reported_name": rule.reported_name,
        "display_order": rule.display_order,
        "is_required": rule.is_required,
        "default_value": rule.default_value,
    }


@router.delete("/{analysis_id}/analyte-rules/{analyte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_analyte_rule(
    analysis_id: UUID,
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Delete an analyte rule for an analysis.
    Requires config:edit or test:configure permission.
    """
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
