"""
Results router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from models.result import Result
from models.test import Test
from models.sample import Sample
from models.analysis import AnalysisAnalyte
from models.user import User
from app.schemas.result import (
    ResultCreate, ResultUpdate, ResultResponse, ResultListResponse,
    BatchResultEntryRequest, BatchResultsEntryRequest, ResultValidationRequest, ResultValidationResponse
)
from app.core.rbac import (
    require_result_enter, require_result_read, require_result_update,
    require_result_delete, require_result_review
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=ResultListResponse)
async def get_results(
    test_id: Optional[UUID] = Query(None, description="Filter by test ID"),
    analyte_id: Optional[UUID] = Query(None, description="Filter by analyte ID"),
    entered_by: Optional[UUID] = Query(None, description="Filter by user who entered results"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_result_read),
    db: Session = Depends(get_db)
):
    """
    Get results with filtering and pagination.
    Scoped by user access.
    """
    # Build query with filters
    query = db.query(Result).filter(Result.active == True)
    
    # Apply user access control
    if current_user.role.name != "Administrator":
        if current_user.client_id:
            # Client users can only see results for their own samples
            query = query.join(Test).join(Sample).filter(
                Sample.project.has(client_id=current_user.client_id)
            )
        else:
            # Lab users can see results for samples in projects they have access to
            from models.project import ProjectUser
            accessible_projects = db.query(ProjectUser.project_id).filter(
                ProjectUser.user_id == current_user.id
            ).subquery()
            query = query.join(Test).join(Sample).filter(Sample.project_id.in_(accessible_projects))
    
    # Apply filters
    if test_id:
        query = query.filter(Result.test_id == test_id)
    if analyte_id:
        query = query.filter(Result.analyte_id == analyte_id)
    if entered_by:
        query = query.filter(Result.entered_by == entered_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    results = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return ResultListResponse(
        results=[ResultResponse.from_orm(result) for result in results],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: UUID,
    current_user: User = Depends(require_result_read),
    db: Session = Depends(get_db)
):
    """
    Get a specific result by ID.
    Scoped by user access.
    """
    result = db.query(Result).filter(
        Result.id == result_id,
        Result.active == True
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and result.test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    return ResultResponse.from_orm(result)


@router.post("/", response_model=ResultResponse)
async def create_result(
    result_data: ResultCreate,
    current_user: User = Depends(require_result_enter),
    db: Session = Depends(get_db)
):
    """
    Create a new result.
    Requires result:enter permission.
    """
    # Verify test exists and user has access
    test = db.query(Test).filter(
        Test.id == result_data.test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Create result
    result = Result(
        test_id=result_data.test_id,
        analyte_id=result_data.analyte_id,
        raw_result=result_data.raw_result,
        reported_result=result_data.reported_result,
        qualifiers=result_data.qualifiers,
        calculated_result=result_data.calculated_result,
        entry_date=result_data.entry_date,
        entered_by=result_data.entered_by,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(result)
    db.commit()
    db.refresh(result)
    
    return ResultResponse.from_orm(result)


@router.post("/batch", response_model=List[ResultResponse])
async def enter_batch_results(
    batch_data: BatchResultsEntryRequest,
    current_user: User = Depends(require_result_enter),
    db: Session = Depends(get_db)
):
    """
    Enter results for a batch.
    Implements US-9: Batch-Based Results Entry.
    """
    # Verify test exists and user has access
    test = db.query(Test).filter(
        Test.id == batch_data.test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate results against analysis_analytes rules
    validation_errors = []
    for result_data in batch_data.results:
        validation = await validate_result(
            ResultValidationRequest(
                test_id=batch_data.test_id,
                analyte_id=result_data.analyte_id,
                raw_result=result_data.raw_result or "",
                reported_result=result_data.reported_result
            ),
            db
        )
        if not validation.is_valid:
            validation_errors.extend(validation.errors)
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation errors: {', '.join(validation_errors)}"
        )
    
    # Create results
    created_results = []
    for result_data in batch_data.results:
        result = Result(
            test_id=batch_data.test_id,
            analyte_id=result_data.analyte_id,
            raw_result=result_data.raw_result,
            reported_result=result_data.reported_result,
            qualifiers=result_data.qualifiers,
            calculated_result=result_data.calculated_result,
            entry_date=datetime.utcnow(),
            entered_by=current_user.id,
            created_by=current_user.id,
            modified_by=current_user.id
        )
        db.add(result)
        created_results.append(result)
    
    # Update test status to "In Analysis" if not already
    from models.list import ListEntry
    in_analysis_status = db.query(ListEntry).filter(
        ListEntry.list_id == "test_status",  # Assuming this list exists
        ListEntry.name == "In Analysis"
    ).first()
    
    if in_analysis_status and test.status != in_analysis_status.id:
        test.status = in_analysis_status.id
        test.modified_by = current_user.id
        test.modified_at = datetime.utcnow()
    
    db.commit()
    
    return [ResultResponse.from_orm(result) for result in created_results]


@router.post("/validate", response_model=ResultValidationResponse)
async def validate_result(
    validation_data: ResultValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a result against analysis_analytes rules.
    """
    # Get analysis_analytes configuration
    analysis_analyte = db.query(AnalysisAnalyte).filter(
        AnalysisAnalyte.analysis_id == validation_data.test_id,  # This should be analysis_id from test
        AnalysisAnalyte.analyte_id == validation_data.analyte_id
    ).first()
    
    if not analysis_analyte:
        return ResultValidationResponse(
            is_valid=False,
            errors=["Analyte not configured for this analysis"]
        )
    
    errors = []
    warnings = []
    
    # Validate data type
    if analysis_analyte.data_type == "numeric":
        try:
            if validation_data.raw_result:
                float(validation_data.raw_result)
            if validation_data.reported_result:
                float(validation_data.reported_result)
        except ValueError:
            errors.append("Result must be numeric")
    
    # Validate range
    if analysis_analyte.low_value is not None or analysis_analyte.high_value is not None:
        try:
            if validation_data.raw_result:
                raw_val = float(validation_data.raw_result)
                if analysis_analyte.low_value is not None and raw_val < analysis_analyte.low_value:
                    errors.append(f"Raw result {raw_val} is below minimum {analysis_analyte.low_value}")
                if analysis_analyte.high_value is not None and raw_val > analysis_analyte.high_value:
                    errors.append(f"Raw result {raw_val} is above maximum {analysis_analyte.high_value}")
        except ValueError:
            pass  # Already caught by data type validation
    
    # Check significant figures
    if analysis_analyte.significant_figures:
        try:
            if validation_data.reported_result:
                reported_val = float(validation_data.reported_result)
                # This is a simplified check - in practice, you'd count actual significant figures
                if len(str(reported_val).replace('.', '').lstrip('0')) > analysis_analyte.significant_figures:
                    warnings.append(f"Reported result may have more than {analysis_analyte.significant_figures} significant figures")
        except ValueError:
            pass
    
    return ResultValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        significant_figures=analysis_analyte.significant_figures,
        data_type=analysis_analyte.data_type,
        high_value=float(analysis_analyte.high_value) if analysis_analyte.high_value else None,
        low_value=float(analysis_analyte.low_value) if analysis_analyte.low_value else None
    )


@router.patch("/{result_id}", response_model=ResultResponse)
async def update_result(
    result_id: UUID,
    result_data: ResultUpdate,
    current_user: User = Depends(require_result_update),
    db: Session = Depends(get_db)
):
    """
    Update a result.
    Requires result:update permission.
    """
    result = db.query(Result).filter(
        Result.id == result_id,
        Result.active == True
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and result.test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Update fields
    update_data = result_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(result, field, value)
    
    result.modified_by = current_user.id
    result.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(result)
    
    return ResultResponse.from_orm(result)


@router.delete("/{result_id}")
async def delete_result(
    result_id: UUID,
    current_user: User = Depends(require_result_delete),
    db: Session = Depends(get_db)
):
    """
    Soft delete a result (set active=False).
    Requires result:delete permission.
    """
    result = db.query(Result).filter(
        Result.id == result_id,
        Result.active == True
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and result.test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Soft delete
    result.active = False
    result.modified_by = current_user.id
    result.modified_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Result deleted successfully"}
