"""
Batches router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from models.batch import Batch, BatchContainer
from models.container import Container
from models.user import User
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


@router.get("/", response_model=BatchListResponse)
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
    
    return BatchListResponse(
        batches=[BatchResponse.from_orm(batch) for batch in batches],
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
    
    return BatchResponse.from_orm(batch)


@router.post("/", response_model=BatchResponse)
async def create_batch(
    batch_data: BatchCreate,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Create a new batch.
    Requires batch:manage permission.
    """
    # Create batch
    batch = Batch(
        name=batch_data.name,
        description=batch_data.description,
        type=batch_data.type,
        status=batch_data.status,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch)
    db.commit()
    db.refresh(batch)
    
    return BatchResponse.from_orm(batch)


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
    # Create batch
    batch = Batch(
        name=batch_data.name,
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
    
    # Update fields
    update_data = batch_data.dict(exclude_unset=True)
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
