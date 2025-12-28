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
    SampleAccessioningRequest, BulkSampleAccessioningRequest
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_sample_delete, require_project_access
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


def _create_tests_for_sample(
    db: Session,
    sample: Sample,
    battery_id: Optional[UUID],
    assigned_tests: List[UUID],
    in_process_status_id: UUID,
    current_user_id: UUID
):
    """
    Helper function to create tests for a sample.
    Shared between single and bulk accessioning.
    """
    from models.test import Test
    from models.test_battery import TestBattery, BatteryAnalysis
    
    # Handle battery assignment (creates tests for all analyses in battery)
    if battery_id:
        # Verify battery exists and is active
        battery = db.query(TestBattery).filter(
            TestBattery.id == battery_id,
            TestBattery.active == True
        ).first()
        
        if not battery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery not found or inactive"
            )
        
        # Get all analyses in battery, ordered by sequence
        battery_analyses = db.query(BatteryAnalysis).filter(
            BatteryAnalysis.battery_id == battery_id
        ).order_by(BatteryAnalysis.sequence).all()
        
        if not battery_analyses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery has no analyses assigned"
            )
        
        # Create tests for each analysis in the battery (in sequence order)
        for battery_analysis in battery_analyses:
            test = Test(
                name=f"{sample.name}_test_{battery_analysis.analysis_id}",
                sample_id=sample.id,
                analysis_id=battery_analysis.analysis_id,
                battery_id=battery_id,
                status=in_process_status_id,
                technician_id=current_user_id,
                created_by=current_user_id,
                modified_by=current_user_id
            )
            db.add(test)
    
    # Also handle individual test assignments (if provided)
    if assigned_tests:
        for analysis_id in assigned_tests:
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
                    status=in_process_status_id,
                    technician_id=current_user_id,
                    created_by=current_user_id,
                    modified_by=current_user_id
                )
                db.add(test)


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
    
    # Verify client_project_id if provided
    if accession_data.client_project_id:
        from models.client import ClientProject
        client_project = db.query(ClientProject).filter(
            ClientProject.id == accession_data.client_project_id,
            ClientProject.active == True
        ).first()
        
        if not client_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project not found or inactive"
            )
        
        # Verify client_project belongs to the same client as the project
        project = db.query(Project).filter(Project.id == accession_data.project_id).first()
        if project and project.client_id != client_project.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project does not belong to the same client as the project"
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
    
    # Link project to client_project if provided
    if accession_data.client_project_id:
        project = db.query(Project).filter(Project.id == accession_data.project_id).first()
        if project:
            project.client_project_id = accession_data.client_project_id
    
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
    
    # Create tests using shared helper function
    _create_tests_for_sample(
        db=db,
        sample=sample,
        battery_id=accession_data.battery_id,
        assigned_tests=accession_data.assigned_tests,
        in_process_status_id=in_process_status.id,
        current_user_id=current_user.id
    )
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.from_orm(sample)


@router.post("/bulk-accession", response_model=List[SampleResponse])
async def bulk_accession_samples(
    bulk_data: BulkSampleAccessioningRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Bulk accession multiple samples with test assignment.
    Implements US-24: Bulk Sample Accessioning.
    Creates samples, containers, contents, and tests in a single transaction.
    """
    # Check project access
    if current_user.role.name != "Administrator":
        from models.project import ProjectUser
        project_access = db.query(ProjectUser).filter(
            ProjectUser.project_id == bulk_data.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        
        if not project_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate container type exists
    from models.container import ContainerType
    container_type = db.query(ContainerType).filter(
        ContainerType.id == bulk_data.container_type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid container type ID"
        )
    
    # Verify client_project_id if provided
    if bulk_data.client_project_id:
        from models.client import ClientProject
        client_project = db.query(ClientProject).filter(
            ClientProject.id == bulk_data.client_project_id,
            ClientProject.active == True
        ).first()
        
        if not client_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project not found or inactive"
            )
        
        # Verify client_project belongs to the same client as the project
        project = db.query(Project).filter(Project.id == bulk_data.project_id).first()
        if project and project.client_id != client_project.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project does not belong to the same client as the project"
            )
    
    # Get initial status (e.g., "Received")
    from models.list import List, ListEntry
    sample_status_list = db.query(List).filter(List.name == "sample_status").first()
    if not sample_status_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status list not found in configuration"
        )
    
    received_status = db.query(ListEntry).filter(
        ListEntry.list_id == sample_status_list.id,
        ListEntry.name == "Received"
    ).first()
    
    if not received_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Received' not found in configuration"
        )
    
    # Get "In Process" status for tests
    test_status_list = db.query(List).filter(List.name == "test_status").first()
    if not test_status_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status list not found in configuration"
        )
    
    in_process_status = db.query(ListEntry).filter(
        ListEntry.list_id == test_status_list.id,
        ListEntry.name == "In Process"
    ).first()
    
    if not in_process_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status 'In Process' not found in configuration"
        )
    
    # Validate unique names and container names
    sample_names = []
    container_names = []
    client_sample_ids = []
    
    auto_name_counter = bulk_data.auto_name_start or 1
    
    for unique in bulk_data.uniques:
        # Generate name if not provided
        if unique.name:
            sample_name = unique.name
        elif bulk_data.auto_name_prefix:
            sample_name = f"{bulk_data.auto_name_prefix}{auto_name_counter}"
            auto_name_counter += 1
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample name required or auto_name_prefix must be provided"
            )
        
        sample_names.append(sample_name)
        container_names.append(unique.container_name)
        
        if unique.client_sample_id:
            client_sample_ids.append(unique.client_sample_id)
    
    # Check for duplicate sample names
    existing_samples = db.query(Sample).filter(
        Sample.name.in_(sample_names),
        Sample.active == True
    ).all()
    
    if existing_samples:
        duplicate_names = [s.name for s in existing_samples]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate sample names found: {', '.join(duplicate_names)}"
        )
    
    # Check for duplicate container names
    from models.container import Container
    existing_containers = db.query(Container).filter(
        Container.name.in_(container_names),
        Container.active == True
    ).all()
    
    if existing_containers:
        duplicate_containers = [c.name for c in existing_containers]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate container names found: {', '.join(duplicate_containers)}"
        )
    
    # Check for duplicate client_sample_ids
    if client_sample_ids:
        existing_client_ids = db.query(Sample).filter(
            Sample.client_sample_id.in_(client_sample_ids),
            Sample.active == True
        ).all()
        
        if existing_client_ids:
            duplicate_client_ids = [s.client_sample_id for s in existing_client_ids if s.client_sample_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate client_sample_ids found: {', '.join(duplicate_client_ids)}"
            )
    
    # Create all samples, containers, contents, and tests in a transaction
    created_samples = []
    auto_name_counter = bulk_data.auto_name_start or 1
    
    try:
        for idx, unique in enumerate(bulk_data.uniques):
            # Generate name if not provided
            if unique.name:
                sample_name = unique.name
            else:
                sample_name = f"{bulk_data.auto_name_prefix}{auto_name_counter}"
                auto_name_counter += 1
            
            # Create sample
            sample = Sample(
                name=sample_name,
                description=unique.description,
                due_date=bulk_data.due_date,
                received_date=bulk_data.received_date,
                sample_type=bulk_data.sample_type,
                status=received_status.id,
                matrix=bulk_data.matrix,
                temperature=unique.temperature if unique.temperature is not None else None,
                project_id=bulk_data.project_id,
                qc_type=bulk_data.qc_type,
                client_sample_id=unique.client_sample_id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(sample)
            db.flush()  # Get the ID without committing
            
            # Link project to client_project if provided (only need to do this once)
            if bulk_data.client_project_id and idx == 0:
                project = db.query(Project).filter(Project.id == bulk_data.project_id).first()
                if project:
                    project.client_project_id = bulk_data.client_project_id
            
            # Create container
            container = Container(
                name=unique.container_name,
                type_id=bulk_data.container_type_id,
                row=1,
                column=1,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(container)
            db.flush()  # Get the ID without committing
            
            # Link sample to container via contents
            from models.container import Contents
            contents = Contents(
                container_id=container.id,
                sample_id=sample.id
            )
            db.add(contents)
            
            # Create tests using shared helper function
            _create_tests_for_sample(
                db=db,
                sample=sample,
                battery_id=bulk_data.battery_id,
                assigned_tests=bulk_data.assigned_tests,
                in_process_status_id=in_process_status.id,
                current_user_id=current_user.id
            )
            
            created_samples.append(sample)
        
        # Commit all changes in a single transaction
        db.commit()
        
        # Refresh all samples to get full data
        for sample in created_samples:
            db.refresh(sample)
        
        return [SampleResponse.from_orm(sample) for sample in created_samples]
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create samples: {str(e)}"
        )


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
