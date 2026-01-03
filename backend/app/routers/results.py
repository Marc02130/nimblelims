"""
Results router for NimbleLims
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
from models.batch import Batch, BatchContainer
from models.container import Container, Contents
from models.list import ListEntry, List as ListModel
import os
from app.schemas.result import (
    ResultCreate, ResultUpdate, ResultResponse, ResultListResponse,
    BatchResultEntryRequest, BatchResultsEntryRequest, ResultValidationRequest, ResultValidationResponse,
    BatchResultsEntryRequestUS28, TestResultEntry, AnalyteResultEntry
)
from app.schemas.batch import BatchResponse, BatchContainerResponse
from app.core.rbac import (
    require_result_enter, require_result_read, require_result_update,
    require_result_delete, require_result_review, require_permission
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


@router.post("/batch", response_model=BatchResponse)
async def enter_batch_results_us28(
    batch_data: BatchResultsEntryRequestUS28,
    current_user: User = Depends(require_result_enter),
    db: Session = Depends(get_db)
):
    """
    Enter results for a batch (US-28: Batch Results Entry).
    Accepts batch_id and list of test results with analyte_results.
    Validates permissions, runs validations, checks QC, and updates test statuses.
    """
    from app.core.rbac import require_batch_read
    
    # Check batch access (batch:read permission)
    batch_read_check = require_batch_read()
    await batch_read_check(current_user=current_user, db=db)
    
    # Fetch batch
    batch = db.query(Batch).filter(
        Batch.id == batch_data.batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    # Get all containers in batch
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    if not batch_containers:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch has no containers"
            )
    
    # Get all samples from batch containers
    container_ids = [bc.container_id for bc in batch_containers]
    contents = db.query(Contents).filter(
        Contents.container_id.in_(container_ids)
    ).all()
    
    sample_ids = [c.sample_id for c in contents]
    if not sample_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch has no samples"
        )
    
    # Get all tests for samples in batch
    tests = db.query(Test).filter(
        Test.sample_id.in_(sample_ids),
        Test.active == True
    ).all()
    
    test_ids = {t.id for t in tests}
    
    # Validate all test_ids in request exist in batch
    requested_test_ids = {tr.test_id for tr in batch_data.results}
    invalid_test_ids = requested_test_ids - test_ids
    if invalid_test_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tests not found in batch: {', '.join(str(tid) for tid in invalid_test_ids)}"
        )
    
    # Build test lookup
    test_lookup = {t.id: t for t in tests}
    
    # Validation errors per row
    validation_errors = []
    qc_failures = []
    
    # Get "Complete" status for tests
    test_status_list = db.query(ListModel).filter(
        ListModel.name == "test_status"
    ).first()
    
    if test_status_list:
        complete_status_entry = db.query(ListEntry).filter(
            ListEntry.list_id == test_status_list.id,
            ListEntry.name == "Complete"
        ).first()
    else:
        complete_status_entry = None
    
    if not complete_status_entry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test status 'Complete' not found in database"
        )
    
    complete_status_id = complete_status_entry.id
    
    # Get QC block configuration
    fail_qc_blocks_batch = os.getenv("FAIL_QC_BLOCKS_BATCH", "false").lower() == "true"
    
    # Start transaction
    try:
        created_results = []
        updated_tests = []
        
        # Process each test result entry
        for test_result_entry in batch_data.results:
            test = test_lookup.get(test_result_entry.test_id)
            if not test:
                validation_errors.append({
                    "test_id": str(test_result_entry.test_id),
                    "error": "Test not found in batch"
                })
                continue
            
            # Get analysis_analytes for this test
            analysis_analytes = db.query(AnalysisAnalyte).filter(
                AnalysisAnalyte.analysis_id == test.analysis_id,
                AnalysisAnalyte.active == True
            ).all()
            
            analyte_lookup = {aa.analyte_id: aa for aa in analysis_analytes}
            
            # Process each analyte result
            for analyte_result in test_result_entry.analyte_results:
                analyte_id = analyte_result.analyte_id
                analysis_analyte = analyte_lookup.get(analyte_id)
                
                if not analysis_analyte:
                    validation_errors.append({
                        "test_id": str(test_result_entry.test_id),
                        "analyte_id": str(analyte_id),
                        "error": "Analyte not configured for this analysis"
                    })
                    continue
                
                # Validate required analytes
                if analysis_analyte.is_required and not analyte_result.raw_result and not analyte_result.reported_result:
                    validation_errors.append({
                        "test_id": str(test_result_entry.test_id),
                        "analyte_id": str(analyte_id),
                        "error": f"Required analyte '{analysis_analyte.reported_name or analysis_analyte.analyte.name}' must have a result"
                    })
                    continue
                
                # Validate data type
                if analysis_analyte.data_type == "numeric":
                    if analyte_result.raw_result:
                        try:
                            float(analyte_result.raw_result)
                        except ValueError:
                            validation_errors.append({
                                "test_id": str(test_result_entry.test_id),
                                "analyte_id": str(analyte_id),
                                "error": f"Raw result '{analyte_result.raw_result}' is not numeric"
                            })
                            continue
                    
                    if analyte_result.reported_result:
                        try:
                            float(analyte_result.reported_result)
                        except ValueError:
                            validation_errors.append({
                                "test_id": str(test_result_entry.test_id),
                                "analyte_id": str(analyte_id),
                                "error": f"Reported result '{analyte_result.reported_result}' is not numeric"
                            })
                            continue
                
                # Validate range
                if analysis_analyte.data_type == "numeric" and analyte_result.raw_result:
                    try:
                        raw_val = float(analyte_result.raw_result)
                        if analysis_analyte.low_value is not None and raw_val < analysis_analyte.low_value:
                            validation_errors.append({
                                "test_id": str(test_result_entry.test_id),
                                "analyte_id": str(analyte_id),
                                "error": f"Raw result {raw_val} is below minimum {analysis_analyte.low_value}"
                            })
                            continue
                        if analysis_analyte.high_value is not None and raw_val > analysis_analyte.high_value:
                            validation_errors.append({
                                "test_id": str(test_result_entry.test_id),
                                "analyte_id": str(analyte_id),
                                "error": f"Raw result {raw_val} is above maximum {analysis_analyte.high_value}"
                            })
                            continue
                    except ValueError:
                        pass  # Already caught by data type validation
                
                # Check if result already exists (update) or create new
                existing_result = db.query(Result).filter(
                    Result.test_id == test_result_entry.test_id,
                    Result.analyte_id == analyte_id,
                    Result.active == True
                ).first()
                
                if existing_result:
                    # Update existing result
                    existing_result.raw_result = analyte_result.raw_result
                    existing_result.reported_result = analyte_result.reported_result
                    existing_result.qualifiers = analyte_result.qualifiers
                    existing_result.modified_by = current_user.id
                    existing_result.modified_at = datetime.utcnow()
                    created_results.append(existing_result)
                else:
                    # Create new result
                    new_result = Result(
                        test_id=test_result_entry.test_id,
                        analyte_id=analyte_id,
                        raw_result=analyte_result.raw_result,
                        reported_result=analyte_result.reported_result,
                        qualifiers=analyte_result.qualifiers,
            entry_date=datetime.utcnow(),
            entered_by=current_user.id,
            created_by=current_user.id,
            modified_by=current_user.id
        )
                    db.add(new_result)
                    created_results.append(new_result)
    
            # Check if all required analytes are entered for this test
            required_analytes = [aa for aa in analysis_analytes if aa.is_required]
            entered_analyte_ids = {ar.analyte_id for ar in test_result_entry.analyte_results}
            missing_required = [aa for aa in required_analytes if aa.analyte_id not in entered_analyte_ids]
            
            # Check if test has all results (all analytes have results)
            all_analyte_ids = {aa.analyte_id for aa in analysis_analytes}
            existing_results = db.query(Result).filter(
                Result.test_id == test_result_entry.test_id,
                Result.analyte_id.in_(all_analyte_ids),
                Result.active == True
            ).all()
            existing_analyte_ids = {r.analyte_id for r in existing_results}
            
            # Add newly entered analytes
            all_entered_analyte_ids = existing_analyte_ids | entered_analyte_ids
            
            # Update test status to Complete if all analytes have results
            if all_analyte_ids.issubset(all_entered_analyte_ids) and test.status != complete_status_id:
                test.status = complete_status_id
                test.modified_by = current_user.id
                test.modified_at = datetime.utcnow()
                updated_tests.append(test)
        
        # Check QC samples for failures
        qc_samples = db.query(Sample).filter(
            Sample.id.in_(sample_ids),
            Sample.qc_type.isnot(None),
            Sample.active == True
        ).all()
        
        if qc_samples:
            # Get QC test results
            qc_sample_ids = {s.id for s in qc_samples}
            qc_tests = db.query(Test).filter(
                Test.sample_id.in_(qc_sample_ids),
                Test.active == True
            ).all()
            
            # Check for QC failures (simplified: check if any QC test has no results or failed validation)
            for qc_test in qc_tests:
                qc_results = db.query(Result).filter(
                    Result.test_id == qc_test.id,
                    Result.active == True
                ).all()
                
                if not qc_results:
                    qc_failures.append({
                        "test_id": str(qc_test.id),
                        "sample_id": str(qc_test.sample_id),
                        "reason": "No results entered for QC sample"
                    })
                else:
                    # Check if QC results are within expected ranges (simplified check)
                    # In practice, this would check against QC acceptance criteria
                    pass
        
        # If validation errors exist, rollback and return errors
        if validation_errors:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Validation errors found",
                    "errors": validation_errors
                }
            )
        
        # If QC failures and blocking is enabled, rollback
        if qc_failures and fail_qc_blocks_batch:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "QC failures detected and blocking is enabled",
                    "qc_failures": qc_failures
                }
            )
        
        # Check if all tests in batch are complete and update batch status
        all_batch_tests = db.query(Test).filter(
            Test.sample_id.in_(sample_ids),
            Test.active == True
        ).all()
        
        # Get batch status list
        batch_status_list = db.query(ListModel).filter(
            ListModel.name == "batch_status"
        ).first()
        
        if batch_status_list:
            completed_status_entry = db.query(ListEntry).filter(
                ListEntry.list_id == batch_status_list.id,
                ListEntry.name == "Completed"
            ).first()
            
            if completed_status_entry:
                # Check if all tests are complete
                all_tests_complete = all(
                    test.status == complete_status_id for test in all_batch_tests
                ) if all_batch_tests else False
                
                # Update batch status to "Completed" if all tests are complete
                if all_tests_complete and batch.status != completed_status_entry.id:
                    batch.status = completed_status_entry.id
                    batch.end_date = datetime.utcnow()
                    batch.modified_by = current_user.id
                    batch.modified_at = datetime.utcnow()
        
        # Commit transaction
        db.commit()
        
        # Refresh batch and return with containers
        db.refresh(batch)
        
        # Get batch containers for response
        batch_containers_response = []
        for bc in batch_containers:
            batch_containers_response.append(BatchContainerResponse(
                batch_id=bc.batch_id,
                container_id=bc.container_id,
                position=bc.position,
                notes=bc.notes
            ))
        
        return BatchResponse(
            id=batch.id,
            name=batch.name,
            description=batch.description,
            type=batch.type,
            status=batch.status,
            start_date=batch.start_date,
            end_date=batch.end_date,
            active=batch.active,
            created_at=batch.created_at,
            created_by=batch.created_by,
            modified_at=batch.modified_at,
            modified_by=batch.modified_by,
            containers=batch_containers_response
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error entering batch results: {str(e)}"
        )


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
