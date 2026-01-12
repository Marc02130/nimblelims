"""
Batches router for NimbleLims
"""
import os
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.database import get_db
from models.batch import Batch, BatchContainer
from models.container import Container, Contents, ContainerType
from models.sample import Sample
from models.test import Test
from models.project import Project, ProjectUser
from models.user import User
from models.list import ListEntry
from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchResponse, BatchListResponse,
    BatchContainerRequest, BatchContainerResponse, BatchCreateWithContainersRequest
)
from app.core.rbac import (
    require_batch_manage, require_batch_read, require_batch_update,
    require_batch_delete, require_project_access
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.get("", response_model=BatchListResponse)
async def get_batches(
    type: Optional[UUID] = Query(None, description="Filter by batch type ID"),
    status: Optional[UUID] = Query(None, description="Filter by status ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db)
):
    """
    Get batches with filtering and pagination.
    Scoped by user access.
    """
    # Build query with filters
    query = db.query(Batch).filter(Batch.active == True)
    
    # Apply filters
    if type:
        query = query.filter(Batch.type == type)
    if status:
        query = query.filter(Batch.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    batches = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    # Load containers for each batch
    batch_responses = []
    for batch in batches:
        batch_containers = db.query(BatchContainer).filter(
            BatchContainer.batch_id == batch.id
        ).all()
        batch_response = BatchResponse.from_orm(batch)
        batch_response.containers = [BatchContainerResponse.from_orm(bc) for bc in batch_containers] if batch_containers else []
        batch_responses.append(batch_response)
    
    return BatchListResponse(
        batches=batch_responses,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db)
):
    """
    Get a specific batch by ID.
    """
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    # Load containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    batch_response = BatchResponse.from_orm(batch)
    batch_response.containers = [BatchContainerResponse.from_orm(bc) for bc in batch_containers] if batch_containers else []
    return batch_response


@router.post("/validate-compatibility")
async def validate_batch_compatibility(
    data: dict,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Validate compatibility of containers for cross-project batching.
    Returns compatibility status and details.
    """
    container_ids = data.get("container_ids", [])
    
    if not container_ids or len(container_ids) < 2:
        return {
            "compatible": False,
            "error": "At least 2 containers are required for compatibility validation"
        }
    
    # Verify all containers exist
    containers = db.query(Container).filter(
        Container.id.in_(container_ids),
        Container.active == True
    ).all()
    
    if len(containers) != len(container_ids):
        found_ids = {c.id for c in containers}
        missing_ids = set(container_ids) - found_ids
        return {
            "compatible": False,
            "error": f"Containers not found: {missing_ids}"
        }
    
    # Get all samples in these containers via Contents junction
    sample_ids = db.query(Contents.sample_id).filter(
        Contents.container_id.in_(container_ids)
    ).distinct().all()
    sample_ids = [s[0] for s in sample_ids]
    
    if not sample_ids:
        return {
            "compatible": False,
            "error": "No samples found in the specified containers"
        }
    
    # Get all projects for these samples
    projects = db.query(Sample.project_id).filter(
        Sample.id.in_(sample_ids),
        Sample.active == True
    ).distinct().all()
    project_ids = [p[0] for p in projects]
    
    # Check RLS access for all projects
    inaccessible_projects = []
    for project_id in project_ids:
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(project_id)}
        ).scalar()
        if not result:
            inaccessible_projects.append(project_id)
    
    if inaccessible_projects:
        return {
            "compatible": False,
            "error": f"Access denied: insufficient permissions for projects: {inaccessible_projects}"
        }
    
    # Validate compatibility: check if samples share a common analysis
    tests = db.query(Test.analysis_id).filter(
        Test.sample_id.in_(sample_ids),
        Test.active == True
    ).distinct().all()
    analysis_ids = {t[0] for t in tests}
    
    if not analysis_ids:
        return {
            "compatible": False,
            "error": "No tests found for samples in the specified containers"
        }
    
    # Get analysis names
    from models.analysis import Analysis
    analyses = db.query(Analysis).filter(
        Analysis.id.in_(analysis_ids),
        Analysis.active == True
    ).all()
    
    # Group tests by sample to find common analyses
    sample_analyses = {}
    for sample_id in sample_ids:
        sample_tests = db.query(Test.analysis_id).filter(
            Test.sample_id == sample_id,
            Test.active == True
        ).all()
        sample_analyses[sample_id] = {t[0] for t in sample_tests}
    
    # Find common analyses across all samples
    if sample_analyses:
        common_analyses = set.intersection(*sample_analyses.values())
        
        if not common_analyses:
            analysis_names = {a.name for a in analyses if a.id in analysis_ids}
            return {
                "compatible": False,
                "error": "Incompatible samples: no shared analyses found",
                "details": {
                    "projects": [str(p) for p in project_ids],
                    "analyses": list(analysis_names),
                    "suggestion": "Samples must share at least one common analysis (e.g., prep method) for cross-project batching"
                }
            }
        else:
            common_analysis_names = {a.name for a in analyses if a.id in common_analyses}
            return {
                "compatible": True,
                "details": {
                    "projects": [str(p) for p in project_ids],
                    "common_analyses": list(common_analysis_names)
                }
            }
    
    return {
        "compatible": False,
        "error": "Unable to determine compatibility"
    }


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    batch_data: BatchCreate,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Create a new batch.
    Implements US-26: Cross-Project Batching.
    Supports cross-project batching with compatibility validation.
    Requires batch:manage permission.
    """
    # Generate name if not provided
    batch_name = batch_data.name
    if not batch_name:
        from app.core.name_generation import generate_name_for_batch
        try:
            batch_name = generate_name_for_batch(
                db=db,
                start_date=batch_data.start_date
            )
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            batch_name = str(uuid.uuid4())
    
    # Auto-detect cross-project if container_ids provided
    is_cross_project = batch_data.cross_project
    if batch_data.container_ids:
        if is_cross_project is None:
            is_cross_project = True  # Auto-detect as cross-project
    
    # If container_ids provided, validate cross-project compatibility
    if batch_data.container_ids:
        # Verify all containers exist
        containers = db.query(Container).filter(
            Container.id.in_(batch_data.container_ids),
            Container.active == True
        ).all()
        
        if len(containers) != len(batch_data.container_ids):
            found_ids = {c.id for c in containers}
            missing_ids = set(batch_data.container_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Containers not found: {missing_ids}"
            )
        
        # Get all samples in these containers via Contents junction
        sample_ids = db.query(Contents.sample_id).filter(
            Contents.container_id.in_(batch_data.container_ids)
        ).distinct().all()
        sample_ids = [s[0] for s in sample_ids]
        
        if not sample_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No samples found in the specified containers"
            )
        
        # Get all projects for these samples
        projects = db.query(Sample.project_id).filter(
            Sample.id.in_(sample_ids),
            Sample.active == True
        ).distinct().all()
        project_ids = [p[0] for p in projects]
        
        # Check RLS access for all projects using SQL function
        # This handles admin, project_users, client_id, and client_projects
        inaccessible_projects = []
        for project_id in project_ids:
            # Use SQL function to check access (handles all RLS cases)
            result = db.execute(
                text("SELECT has_project_access(:project_id)"),
                {"project_id": str(project_id)}
            ).scalar()
            if not result:
                inaccessible_projects.append(project_id)
        
        if inaccessible_projects:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: insufficient permissions for projects: {inaccessible_projects}"
            )
        
        # Validate compatibility: check if samples share a common analysis
        # Get all tests for these samples
        tests = db.query(Test.analysis_id).filter(
            Test.sample_id.in_(sample_ids),
            Test.active == True
        ).distinct().all()
        analysis_ids = {t[0] for t in tests}
        
        if not analysis_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tests found for samples in the specified containers"
            )
        
        # Check compatibility: all samples should have at least one shared analysis
        # For cross-project batching, we require a shared prep analysis (e.g., 'EPA Method 8080 Prep')
        # Get analysis names to check for prep analyses
        from models.analysis import Analysis
        analyses = db.query(Analysis).filter(
            Analysis.id.in_(analysis_ids),
            Analysis.active == True
        ).all()
        
        # Check if there's a shared analysis across all samples
        # Group tests by sample to find common analyses
        sample_analyses = {}
        for sample_id in sample_ids:
            sample_tests = db.query(Test.analysis_id).filter(
                Test.sample_id == sample_id,
                Test.active == True
            ).all()
            sample_analyses[sample_id] = {t[0] for t in sample_tests}
        
        # Find common analyses across all samples
        if sample_analyses:
            common_analyses = set.intersection(*sample_analyses.values())
            
            # If divergent_analyses specified, check if they're in common_analyses
            if batch_data.divergent_analyses:
                divergent_set = set(batch_data.divergent_analyses)
                if divergent_set.intersection(common_analyses):
                    # These analyses require separate sub-batches
                    # For now, we'll create a note but still create the main batch
                    # Future: child_batch_id FK will be added for sub-batches
                    pass
            
            if not common_analyses:
                # Get analysis names for error message
                analysis_names = {a.name for a in analyses if a.id in analysis_ids}
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Incompatible samples: no shared analyses found",
                        "projects": list(project_ids),
                        "analyses": list(analysis_names),
                        "suggestion": "Samples must share at least one common analysis (e.g., prep method) for cross-project batching"
                    }
                )
    
    # Check QC requirement based on batch type and env var
    require_qc_types = os.getenv("REQUIRE_QC_FOR_BATCH_TYPES", "")
    require_qc_type_ids = []
    if require_qc_types:
        # Parse comma-separated UUIDs
        try:
            require_qc_type_ids = [UUID(t.strip()) for t in require_qc_types.split(",") if t.strip()]
        except ValueError:
            # Invalid UUID format, ignore
            pass
    
    # Check if QC is required for this batch type
    qc_required = False
    if batch_data.type and require_qc_type_ids and batch_data.type in require_qc_type_ids:
        qc_required = True
    
    # Validate QC additions if required
    if qc_required and (not batch_data.qc_additions or len(batch_data.qc_additions) == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"QC samples are required for batch type {batch_data.type}. Please provide qc_additions."
        )
    
    # Get first sample for QC inheritance (project_id, sample_type, matrix, status)
    first_sample = None
    if batch_data.qc_additions:
        if batch_data.container_ids:
            # Get first sample from first container
            first_container_id = batch_data.container_ids[0]
            first_contents = db.query(Contents).filter(
                Contents.container_id == first_container_id
            ).first()
            if first_contents:
                first_sample = db.query(Sample).filter(
                    Sample.id == first_contents.sample_id,
                    Sample.active == True
                ).first()
        
        if not first_sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create QC samples: no samples found in containers to inherit project/sample properties. Provide container_ids with samples."
            )
    
    # Validate status exists and is active
    if batch_data.status:
        status_entry = db.query(ListEntry).filter(
            ListEntry.id == batch_data.status,
            ListEntry.active == True
        ).first()
        if not status_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid batch status ID: {batch_data.status}"
            )
    
    # Create batch
    batch = Batch(
        name=batch_name,
        description=batch_data.description,
        type=batch_data.type,
        status=batch_data.status,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch)
    db.flush()  # Get the ID without committing
    
    # Add containers to batch if provided
    if batch_data.container_ids:
        for idx, container_id in enumerate(batch_data.container_ids):
            batch_container = BatchContainer(
                batch_id=batch.id,
                container_id=container_id,
                position=None,  # Can be set later if needed
                notes=None,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(batch_container)
    
    # Create QC samples if provided (US-27)
    # All QC creation happens atomically within the batch creation transaction
    if batch_data.qc_additions and first_sample:
        # Get "Received" status for QC samples
        from models.list import List
        sample_status_list = db.query(List).filter(
            List.name == "sample_status"
        ).first()
        
        if not sample_status_list:
            # Create sample_status list if it doesn't exist
            sample_status_list = List(
                name="sample_status",
                description="Sample status list",
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(sample_status_list)
            db.flush()
        
        received_status = db.query(ListEntry).filter(
            ListEntry.list_id == sample_status_list.id,
            ListEntry.name == "Received",
            ListEntry.active == True
        ).first()
        
        if not received_status:
            # Create "Received" status if it doesn't exist
            received_status = ListEntry(
                name="Received",
                description="Sample received",
                list_id=sample_status_list.id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(received_status)
            db.flush()
            db.refresh(received_status)  # Ensure ID is available
        
        # Get default container type for QC samples (use first container's type or a default)
        default_container_type = None
        if batch_data.container_ids:
            first_container = db.query(Container).filter(
                Container.id == batch_data.container_ids[0]
            ).first()
            if first_container:
                default_container_type = first_container.type_id
        
        if not default_container_type:
            # Get first active container type as fallback
            default_container_type_obj = db.query(ContainerType).filter(
                ContainerType.active == True
            ).first()
            if default_container_type_obj:
                default_container_type = default_container_type_obj.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC samples: no container type available"
                )
        
        # Create QC samples
        for qc_idx, qc_addition in enumerate(batch_data.qc_additions):
            # Validate QC type exists
            qc_type_entry = db.query(ListEntry).filter(
                ListEntry.id == qc_addition.qc_type,
                ListEntry.active == True
            ).first()
            
            if not qc_type_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid QC type ID: {qc_addition.qc_type}"
                )
            
            # Generate QC sample name
            qc_sample_name = f"QC-{batch.name}-{qc_idx + 1}"
            
            # Validate all required fields are present
            if not first_sample.sample_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC sample: first sample has no sample_type"
                )
            if not first_sample.matrix:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC sample: first sample has no matrix"
                )
            if not first_sample.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC sample: first sample has no project_id"
                )
            if not received_status or not received_status.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC sample: received status not found or invalid"
                )
            
            # Create QC sample (inherit from first sample)
            qc_sample = Sample(
                name=qc_sample_name,
                description=f"QC sample ({qc_type_entry.name})" + (f": {qc_addition.notes}" if qc_addition.notes else ""),
                due_date=first_sample.due_date,
                received_date=datetime.utcnow(),
                sample_type=first_sample.sample_type,  # Inherit sample type
                status=received_status.id,
                matrix=first_sample.matrix,  # Inherit matrix
                temperature=first_sample.temperature,  # Inherit temperature
                project_id=first_sample.project_id,  # Inherit project
                qc_type=qc_addition.qc_type,  # Set QC type
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(qc_sample)
            db.flush()  # Get the ID without committing
            
            # Create container for QC sample
            qc_container = Container(
                name=f"QC-{batch.name}-{qc_idx + 1}-Container",
                description=f"Container for QC sample {qc_sample_name}",
                type_id=default_container_type,
                row=1,
                column=1,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(qc_container)
            db.flush()  # Get the ID without committing
            
            # Link QC sample to container via Contents
            qc_contents = Contents(
                container_id=qc_container.id,
                sample_id=qc_sample.id
            )
            db.add(qc_contents)
            
            # Link QC container to batch
            qc_batch_container = BatchContainer(
                batch_id=batch.id,
                container_id=qc_container.id,
                position=None,
                notes=qc_addition.notes,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(qc_batch_container)
    
    # Commit all changes atomically (batch, containers, QC samples, contents, batch_containers)
    # If any error occurs, the entire transaction is rolled back
    try:
        db.commit()
        db.refresh(batch)
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating batch: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Batch data: name={batch_name}, type={batch_data.type}, status={batch_data.status}")
        logger.error(f"Container IDs: {batch_data.container_ids}")
        logger.error(f"QC additions: {batch_data.qc_additions}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch: {str(e)}"
        )
    
    # Load containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    batch_response = BatchResponse.from_orm(batch)
    batch_response.containers = [BatchContainerResponse.from_orm(bc) for bc in batch_containers] if batch_containers else []
    return batch_response


@router.post("/with-containers", response_model=BatchResponse)
async def create_batch_with_containers(
    batch_data: BatchCreateWithContainersRequest,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Create a new batch with containers.
    Implements US-11: Create and Manage Batches.
    """
    # Generate name if not provided
    batch_name = batch_data.name
    if not batch_name:
        from app.core.name_generation import generate_name_for_batch
        try:
            batch_name = generate_name_for_batch(
                db=db,
                start_date=batch_data.start_date
            )
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            batch_name = str(uuid.uuid4())
    
    # Create batch
    batch = Batch(
        name=batch_name,
        description=batch_data.description,
        type=batch_data.type,
        status=batch_data.status,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch)
    db.flush()  # Get the ID without committing
    
    # Add containers to batch
    for container_req in batch_data.containers:
        # Verify container exists
        container = db.query(Container).filter(
            Container.id == container_req.container_id,
            Container.active == True
        ).first()
        
        if not container:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container {container_req.container_id} not found"
            )
        
        batch_container = BatchContainer(
            batch_id=batch.id,
            container_id=container_req.container_id,
            position=container_req.position,
            notes=container_req.notes,
            created_by=current_user.id,
            modified_by=current_user.id
        )
        db.add(batch_container)
    
    db.commit()
    db.refresh(batch)
    
    return BatchResponse.from_orm(batch)


@router.post("/{batch_id}/containers", response_model=BatchContainerResponse)
async def add_container_to_batch(
    batch_id: UUID,
    container_data: BatchContainerRequest,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Add a container to a batch.
    """
    # Verify batch exists
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Check if container is already in batch
    existing = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch_id,
        BatchContainer.container_id == container_data.container_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container is already in this batch"
        )
    
    # Add container to batch
    batch_container = BatchContainer(
        batch_id=batch_id,
        container_id=container_data.container_id,
        position=container_data.position,
        notes=container_data.notes,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch_container)
    db.commit()
    db.refresh(batch_container)
    
    return BatchContainerResponse.from_orm(batch_container)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    batch_data: BatchUpdate,
    current_user: User = Depends(require_batch_update),
    db: Session = Depends(get_db)
):
    """
    Update a batch.
    Requires batch:update permission.
    """
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    # Validate and update custom_attributes if provided
    update_data = batch_data.dict(exclude_unset=True)
    if 'custom_attributes' in update_data:
        from app.core.custom_attributes import validate_custom_attributes
        try:
            validated_custom_attributes = validate_custom_attributes(
                db, "batches", update_data['custom_attributes']
            )
            update_data['custom_attributes'] = validated_custom_attributes
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(batch, field, value)
    
    batch.modified_by = current_user.id
    batch.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(batch)
    
    return BatchResponse.from_orm(batch)


@router.patch("/{batch_id}/status", response_model=BatchResponse)
async def update_batch_status(
    batch_id: UUID,
    status_id: UUID,
    current_user: User = Depends(require_batch_update),
    db: Session = Depends(get_db)
):
    """
    Update batch status.
    Implements US-11: Create and Manage Batches status flow.
    """
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
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
    
    # Update status and dates
    batch.status = status_id
    if status_id == "in_process":  # Assuming this is the "In Process" status
        batch.start_date = datetime.utcnow()
    elif status_id == "completed":  # Assuming this is the "Completed" status
        batch.end_date = datetime.utcnow()
    
    batch.modified_by = current_user.id
    batch.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(batch)
    
    return BatchResponse.from_orm(batch)


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: UUID,
    current_user: User = Depends(require_batch_delete),
    db: Session = Depends(get_db)
):
    """
    Soft delete a batch (set active=False).
    Requires batch:delete permission.
    """
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    # Soft delete
    batch.active = False
    batch.modified_by = current_user.id
    batch.modified_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Batch deleted successfully"}


@router.delete("/{batch_id}/containers/{container_id}")
async def remove_container_from_batch(
    batch_id: UUID,
    container_id: UUID,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Remove a container from a batch.
    """
    batch_container = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch_id,
        BatchContainer.container_id == container_id
    ).first()
    
    if not batch_container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in batch"
        )
    
    db.delete(batch_container)
    db.commit()
    
    return {"message": "Container removed from batch successfully"}
