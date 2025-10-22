"""
Samples router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from models.sample import Sample
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


@router.get("/", response_model=SampleListResponse)
async def get_samples(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[UUID] = Query(None, description="Filter by status ID"),
    qc_type: Optional[UUID] = Query(None, description="Filter by QC type ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get samples with filtering and pagination.
    Scoped by user access (clients see only their projects).
    """
    # Build query with filters
    query = db.query(Sample).filter(Sample.active == True)
    
    # Apply project access control
    if current_user.role.name != "Administrator":
        if current_user.client_id:
            # Client users can only see their own projects
            query = query.join("project").filter(
                "project.client_id" == current_user.client_id
            )
        else:
            # Lab users can see projects they have access to
            from models.project import ProjectUser
            accessible_projects = db.query(ProjectUser.project_id).filter(
                ProjectUser.user_id == current_user.id
            ).subquery()
            query = query.filter(Sample.project_id.in_(accessible_projects))
    
    # Apply filters
    if project_id:
        query = query.filter(Sample.project_id == project_id)
    if status:
        query = query.filter(Sample.status == status)
    if qc_type:
        query = query.filter(Sample.qc_type == qc_type)
    
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
    
    # Assign tests if specified
    if accession_data.assigned_tests:
        from models.test import Test
        from models.list import ListEntry
        
        # Get "In Process" status for tests
        in_process_status = db.query(ListEntry).filter(
            ListEntry.list_id == "test_status",  # Assuming this list exists
            ListEntry.name == "In Process"
        ).first()
        
        if not in_process_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test status 'In Process' not found in configuration"
            )
        
        for analysis_id in accession_data.assigned_tests:
            test = Test(
                name=f"{sample.name}_test_{analysis_id}",
                sample_id=sample.id,
                analysis_id=analysis_id,
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
