"""
Tests router for NimbleLims
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast
from app.database import get_db
from models.test import Test
from models.sample import Sample
from models.user import User
from models.project import Project, ProjectUser
from app.schemas.test import (
    TestCreate, TestUpdate, TestResponse, TestListResponse,
    TestAssignmentRequest, TestStatusUpdateRequest, TestReviewRequest
)
from app.core.rbac import (
    require_test_assign, require_test_update, require_result_review,
    require_result_read, validate_client_access
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.get("", response_model=TestListResponse)
async def get_tests(
    request: Request,
    sample_id: Optional[UUID] = Query(None, description="Filter by sample ID"),
    analysis_id: Optional[UUID] = Query(None, description="Filter by analysis ID"),
    status: Optional[UUID] = Query(None, description="Filter by status ID"),
    technician_id: Optional[UUID] = Query(None, description="Filter by technician ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tests with filtering and pagination.
    Scoped by user access via RLS policies.
    RLS policy tests_access automatically filters based on has_project_access(sample.project_id)
    """
    # Build query with filters - RLS will automatically filter based on project access
    # No need for manual Python-level filtering - RLS handles:
    # - Admin users: see all tests
    # - Lab users: see tests for samples in projects they have access to via project_users
    # - Client users: see tests for samples from their client's projects
    query = db.query(Test).filter(Test.active == True)
    
    # Apply filters
    if sample_id:
        query = query.filter(Test.sample_id == sample_id)
    if analysis_id:
        query = query.filter(Test.analysis_id == analysis_id)
    if status:
        query = query.filter(Test.status == status)
    if technician_id:
        query = query.filter(Test.technician_id == technician_id)
    
    # Parse and apply custom_attributes filters (e.g., ?custom.ph_level=7.0)
    custom_filters = {}
    for key, value in request.query_params.items():
        if key.startswith('custom.'):
            attr_name = key[7:]  # Remove 'custom.' prefix
            # Try to parse as number, otherwise keep as string
            try:
                if '.' in value:
                    custom_filters[attr_name] = float(value)
                else:
                    custom_filters[attr_name] = int(value)
            except ValueError:
                custom_filters[attr_name] = value
    
    # Apply custom_attributes JSONB filters
    if custom_filters:
        for attr_name, attr_value in custom_filters.items():
            filter_dict = {attr_name: attr_value}
            query = query.filter(
                Test.custom_attributes.op("@>")(cast(filter_dict, JSONB))
            )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    tests = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return TestListResponse(
        tests=[TestResponse.from_orm(test) for test in tests],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific test by ID.
    Scoped by user access.
    """
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Validate client access: non-System/Admin users can only view tests for their own client's projects
    # RLS also enforces this, but we add explicit check for API layer validation
    validate_client_access(current_user, test.sample.project.client_id)
    
    return TestResponse.from_orm(test)


@router.post("/", response_model=TestResponse)
async def create_test(
    test_data: TestCreate,
    current_user: User = Depends(require_test_assign),
    db: Session = Depends(get_db)
):
    """
    Create a new test.
    Requires test:assign permission.
    """
    # Verify sample exists and user has access
    sample = db.query(Sample).filter(
        Sample.id == test_data.sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Validate client access: non-System/Admin users can only create tests for their own client's projects
    validate_client_access(current_user, sample.project.client_id)
    
    # Verify analysis exists
    from models.analysis import Analysis
    analysis = db.query(Analysis).filter(
        Analysis.id == test_data.analysis_id,
        Analysis.active == True
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID"
        )
    
    # Validate custom_attributes if provided
    validated_custom_attributes = {}
    if test_data.custom_attributes:
        from app.core.custom_attributes import validate_custom_attributes
        validated_custom_attributes = validate_custom_attributes(
            db=db,
            entity_type='tests',
            custom_attributes=test_data.custom_attributes
        )
    
    # Create test
    test = Test(
        name=test_data.name,
        description=test_data.description,
        sample_id=test_data.sample_id,
        analysis_id=test_data.analysis_id,
        status=test_data.status,
        review_date=test_data.review_date,
        test_date=test_data.test_date,
        technician_id=test_data.technician_id,
        custom_attributes=validated_custom_attributes,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(test)
    db.commit()
    db.refresh(test)
    
    return TestResponse.from_orm(test)


@router.post("/assign", response_model=TestResponse)
async def assign_test_to_sample(
    assignment_data: TestAssignmentRequest,
    current_user: User = Depends(require_test_assign),
    db: Session = Depends(get_db)
):
    """
    Assign a test to a sample.
    Implements US-7: Assign Tests to Samples.
    """
    # Verify sample exists and user has access
    sample = db.query(Sample).filter(
        Sample.id == assignment_data.sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Validate client access: non-System/Admin users can only assign tests for their own client's projects
    validate_client_access(current_user, sample.project.client_id)
    
    # Verify analysis exists
    from models.analysis import Analysis
    analysis = db.query(Analysis).filter(
        Analysis.id == assignment_data.analysis_id,
        Analysis.active == True
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID"
        )
    
    # Get "In Process" status
    from models.list import ListEntry
    in_process_status = db.query(ListEntry).filter(
        ListEntry.list_id == "test_status",  # Assuming this list exists
        ListEntry.name == "In Process"
    ).first()
    
    if not in_process_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status 'In Process' not found in configuration"
        )
    
    # Create test
    test = Test(
        name=f"{sample.name}_{analysis.name}_test",
        sample_id=assignment_data.sample_id,
        analysis_id=assignment_data.analysis_id,
        status=in_process_status.id,
        test_date=assignment_data.test_date,
        technician_id=assignment_data.technician_id or current_user.id,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(test)
    db.commit()
    db.refresh(test)
    
    return TestResponse.from_orm(test)


@router.patch("/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: UUID,
    test_data: TestUpdate,
    current_user: User = Depends(require_test_update),
    db: Session = Depends(get_db)
):
    """
    Partially update a test.
    
    Requires test:update permission. Updates only the fields provided in the request.
    Validates custom attributes against EAV configuration. Updates audit fields (modified_at, modified_by).
    
    **Example: Update test status**
    ```json
    {
        "status": "uuid-of-complete-status"
    }
    ```
    
    **Example: Update technician assignment**
    ```json
    {
        "technician_id": "uuid-of-technician",
        "test_date": "2025-01-03T10:00:00Z"
    }
    ```
    
    **Example: Update custom attributes**
    ```json
    {
        "custom_attributes": {
            "instrument": "GC-MS-001",
            "run_number": "2025-001"
        }
    }
    ```
    
    Returns 404 if test not found, 403 if user lacks access (RLS enforced).
    All updates are performed in a single atomic transaction.
    """
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Validate client access: non-System/Admin users can only update tests for their own client's projects
    validate_client_access(current_user, test.sample.project.client_id)
    
    # Validate and update custom_attributes if provided
    if test_data.custom_attributes is not None:
        from app.core.custom_attributes import validate_custom_attributes
        validated_custom_attributes = validate_custom_attributes(
            db=db,
            entity_type='tests',
            custom_attributes=test_data.custom_attributes
        )
        test.custom_attributes = validated_custom_attributes
    
    # Update fields (excluding custom_attributes which is handled above)
    update_data = test_data.dict(exclude_unset=True, exclude={'custom_attributes'})
    for field, value in update_data.items():
        setattr(test, field, value)
    
    test.modified_by = current_user.id
    test.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(test)
    
    return TestResponse.from_orm(test)


@router.patch("/{test_id}/status", response_model=TestResponse)
async def update_test_status(
    test_id: UUID,
    status_data: TestStatusUpdateRequest,
    current_user: User = Depends(require_test_update),
    db: Session = Depends(get_db)
):
    """
    Update test status.
    Implements US-8: Test Status Management.
    """
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate status exists
    from models.list import ListEntry
    status_entry = db.query(ListEntry).filter(
        ListEntry.id == status_data.status,
        ListEntry.active == True
    ).first()
    
    if not status_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status ID"
        )
    
    # Update status and related fields
    test.status = status_data.status
    if status_data.review_date:
        test.review_date = status_data.review_date
    if status_data.test_date:
        test.test_date = status_data.test_date
    if status_data.technician_id:
        test.technician_id = status_data.technician_id
    
    test.modified_by = current_user.id
    test.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(test)
    
    return TestResponse.from_orm(test)


@router.patch("/{test_id}/review", response_model=TestResponse)
async def review_test(
    test_id: UUID,
    review_data: TestReviewRequest,
    current_user: User = Depends(require_result_review),
    db: Session = Depends(get_db)
):
    """
    Review and approve a test.
    Implements US-10: Results Review.
    """
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Get "Complete" status
    from models.list import ListEntry
    complete_status = db.query(ListEntry).filter(
        ListEntry.list_id == "test_status",  # Assuming this list exists
        ListEntry.name == "Complete"
    ).first()
    
    if not complete_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status 'Complete' not found in configuration"
        )
    
    # Update test with review
    test.status = complete_status.id
    test.review_date = review_data.review_date
    test.modified_by = current_user.id
    test.modified_at = datetime.utcnow()
    
    # Update sample status to "Reviewed" if all tests are complete
    from models.list import ListEntry
    reviewed_status = db.query(ListEntry).filter(
        ListEntry.list_id == "sample_status",  # Assuming this list exists
        ListEntry.name == "Reviewed"
    ).first()
    
    if reviewed_status:
        # Check if all tests for this sample are complete
        incomplete_tests = db.query(Test).filter(
            Test.sample_id == test.sample_id,
            Test.active == True,
            Test.status != complete_status.id
        ).count()
        
        if incomplete_tests == 0:
            test.sample.status = reviewed_status.id
            test.sample.modified_by = current_user.id
            test.sample.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(test)
    
    return TestResponse.from_orm(test)


@router.delete("/{test_id}")
async def delete_test(
    test_id: UUID,
    current_user: User = Depends(require_test_update),
    db: Session = Depends(get_db)
):
    """
    Soft delete a test (set active=False).
    """
    test = db.query(Test).filter(
        Test.id == test_id,
        Test.active == True
    ).first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check access control
    if current_user.role.name != "Administrator":
        if current_user.client_id and test.sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Soft delete
    test.active = False
    test.modified_by = current_user.id
    test.modified_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Test deleted successfully"}
