"""
Samples router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from models.sample import Sample
from models.project import Project
from models.user import User
from app.schemas.sample import (
    SampleCreate, SampleUpdate, SampleResponse, SampleListResponse,
    SampleAccessioningRequest
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_sample_delete, require_project_access
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.get("", response_model=SampleListResponse)
async def get_samples(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status ID"),
    qc_type: Optional[str] = Query(None, description="Filter by QC type ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get samples with filtering and pagination.
    Scoped by user access (clients see only their projects).
    """
    # Convert empty strings to None and parse UUIDs
    project_id_uuid = None
    status_uuid = None
    qc_type_uuid = None
    
    if project_id and project_id.strip():
        try:
            project_id_uuid = UUID(project_id)
        except (ValueError, AttributeError):
            pass
    
    if status and status.strip():
        try:
            status_uuid = UUID(status)
        except (ValueError, AttributeError):
            pass
    
    if qc_type and qc_type.strip():
        try:
            qc_type_uuid = UUID(qc_type)
        except (ValueError, AttributeError):
            pass
    
    # Build query with filters
    query = db.query(Sample).filter(Sample.active == True)
    
    # Apply project access control
    if current_user.role.name != "Administrator":
        if current_user.client_id:
            # Client users can only see their own projects
            query = query.join(Project).filter(
                Project.client_id == current_user.client_id
            )
        else:
            # Lab users can see projects they have access to
            from models.project import ProjectUser
            accessible_projects = db.query(ProjectUser.project_id).filter(
                ProjectUser.user_id == current_user.id
            ).subquery()
            query = query.filter(Sample.project_id.in_(accessible_projects))
    
    # Apply filters
    if project_id_uuid:
        query = query.filter(Sample.project_id == project_id_uuid)
    if status_uuid:
        query = query.filter(Sample.status == status_uuid)
    if qc_type_uuid:
        query = query.filter(Sample.qc_type == qc_type_uuid)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    samples = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return SampleListResponse(
        samples=[SampleResponse.from_orm(sample) for sample in samples],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get a specific sample by ID.
    Scoped by user access.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    return SampleResponse.from_orm(sample)


@router.post("/", response_model=SampleResponse)
async def create_sample(
    sample_data: SampleCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create a new sample.
    Requires sample:create permission.
    """
    # Check project access
    if current_user.role.name != "Administrator":
        from models.project import ProjectUser
        project_access = db.query(ProjectUser).filter(
            ProjectUser.project_id == sample_data.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        
        if not project_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Create sample
    sample = Sample(
        name=sample_data.name,
        description=sample_data.description,
        due_date=sample_data.due_date,
        received_date=sample_data.received_date,
        report_date=sample_data.report_date,
        sample_type=sample_data.sample_type,
        status=sample_data.status,
        matrix=sample_data.matrix,
        temperature=sample_data.temperature,
        parent_sample_id=sample_data.parent_sample_id,
        project_id=sample_data.project_id,
        qc_type=sample_data.qc_type,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(sample)
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.from_orm(sample)


@router.post("/accession", response_model=SampleResponse)
async def accession_sample(
    accession_data: SampleAccessioningRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Accession a new sample with test assignment.
    Implements US-1: Sample Accessioning workflow.
    """
    # Check project access
    if current_user.role.name != "Administrator":
        from models.project import ProjectUser
        project_access = db.query(ProjectUser).filter(
            ProjectUser.project_id == accession_data.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        
        if not project_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Get initial status (e.g., "Received")
    from models.list import ListEntry
    received_status = db.query(ListEntry).filter(
        ListEntry.list_id == "sample_status",  # Assuming this list exists
        ListEntry.name == "Received"
    ).first()
    
    if not received_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Received' not found in configuration"
        )
    
    # Create sample
    sample = Sample(
        name=accession_data.name,
        description=accession_data.description,
        due_date=accession_data.due_date,
        received_date=accession_data.received_date,
        sample_type=accession_data.sample_type,
        status=received_status.id,
        matrix=accession_data.matrix,
        temperature=accession_data.temperature,
        project_id=accession_data.project_id,
        qc_type=accession_data.qc_type,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(sample)
    db.flush()  # Get the ID without committing
    
    # Get "In Process" status for tests
    from models.test import Test
    from models.list import ListEntry
    from models.test_battery import TestBattery, BatteryAnalysis
    
    in_process_status = db.query(ListEntry).filter(
        ListEntry.list_id == "test_status",  # Assuming this list exists
        ListEntry.name == "In Process"
    ).first()
    
    if not in_process_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status 'In Process' not found in configuration"
        )
    
    # Handle battery assignment (creates tests for all analyses in battery)
    if accession_data.battery_id:
        # Verify battery exists and is active
        battery = db.query(TestBattery).filter(
            TestBattery.id == accession_data.battery_id,
            TestBattery.active == True
        ).first()
        
        if not battery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery not found or inactive"
            )
        
        # Get all analyses in battery, ordered by sequence
        battery_analyses = db.query(BatteryAnalysis).filter(
            BatteryAnalysis.battery_id == accession_data.battery_id
        ).order_by(BatteryAnalysis.sequence).all()
        
        if not battery_analyses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery has no analyses assigned"
            )
        
        # Create tests for each analysis in the battery (in sequence order)
        for battery_analysis in battery_analyses:
            # Skip optional analyses if needed (for now, create all)
            # In future, could add logic to skip optional analyses based on user preference
            test = Test(
                name=f"{sample.name}_test_{battery_analysis.analysis_id}",
                sample_id=sample.id,
                analysis_id=battery_analysis.analysis_id,
                battery_id=accession_data.battery_id,
                status=in_process_status.id,
                technician_id=current_user.id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(test)
    
    # Also handle individual test assignments (if provided)
    if accession_data.assigned_tests:
        for analysis_id in accession_data.assigned_tests:
            # Check if test already exists (from battery assignment)
            existing_test = db.query(Test).filter(
                Test.sample_id == sample.id,
                Test.analysis_id == analysis_id,
                Test.active == True
            ).first()
            
            if not existing_test:
                test = Test(
                    name=f"{sample.name}_test_{analysis_id}",
                    sample_id=sample.id,
                    analysis_id=analysis_id,
                    battery_id=None,  # Individual assignment, not from battery
                    status=in_process_status.id,
                    technician_id=current_user.id,
                    created_by=current_user.id,
                    modified_by=current_user.id
                )
                db.add(test)
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.from_orm(sample)


@router.patch("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    sample_data: SampleUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update a sample.
    Requires sample:update permission.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Update fields
    update_data = sample_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sample, field, value)
    
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.from_orm(sample)


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: UUID,
    current_user: User = Depends(require_sample_delete),
    db: Session = Depends(get_db)
):
    """
    Soft delete a sample (set active=False).
    Requires sample:delete permission.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Soft delete
    sample.active = False
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Sample deleted successfully"}


@router.patch("/{sample_id}/status", response_model=SampleResponse)
async def update_sample_status(
    sample_id: UUID,
    status_id: UUID,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update sample status.
    Implements US-2: Sample Status Management.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate status exists
    from models.list import ListEntry
    status_entry = db.query(ListEntry).filter(
        ListEntry.id == status_id,
        ListEntry.active == True
    ).first()
    
    if not status_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status ID"
        )
    
    # Update status
    sample.status = status_id
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.from_orm(sample)
