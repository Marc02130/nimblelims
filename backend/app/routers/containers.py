"""
Containers router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.container import Container, ContainerType, Contents
from models.user import User
from app.schemas.container import (
    ContainerCreate, ContainerUpdate, ContainerResponse, ContainerWithContentsResponse,
    ContainerTypeCreate, ContainerTypeUpdate, ContainerTypeResponse,
    ContentsCreate, ContentsUpdate, ContentsResponse, ContentsListResponse
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_config_edit
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter()


# Container Types endpoints
@router.get("/types", response_model=List[ContainerTypeResponse])
async def get_container_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all container types.
    """
    container_types = db.query(ContainerType).filter(ContainerType.active == True).all()
    return [ContainerTypeResponse.from_orm(ct) for ct in container_types]


@router.post("/types", response_model=ContainerTypeResponse)
async def create_container_type(
    container_type_data: ContainerTypeCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new container type.
    Requires config:edit permission.
    """
    container_type = ContainerType(
        name=container_type_data.name,
        description=container_type_data.description,
        capacity=container_type_data.capacity,
        material=container_type_data.material,
        dimensions=container_type_data.dimensions,
        preservative=container_type_data.preservative,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(container_type)
    db.commit()
    db.refresh(container_type)
    
    return ContainerTypeResponse.from_orm(container_type)


@router.patch("/types/{type_id}", response_model=ContainerTypeResponse)
async def update_container_type(
    type_id: UUID,
    container_type_data: ContainerTypeUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a container type.
    Requires config:edit permission.
    """
    container_type = db.query(ContainerType).filter(
        ContainerType.id == type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container type not found"
        )
    
    # Update fields
    update_data = container_type_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(container_type, field, value)
    
    container_type.modified_by = current_user.id
    container_type.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(container_type)
    
    return ContainerTypeResponse.from_orm(container_type)


# Containers endpoints
@router.get("/", response_model=List[ContainerResponse])
async def get_containers(
    type_id: Optional[UUID] = Query(None, description="Filter by container type"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent container"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get containers with filtering.
    """
    query = db.query(Container).filter(Container.active == True)
    
    if type_id:
        query = query.filter(Container.type_id == type_id)
    if parent_id:
        query = query.filter(Container.parent_container_id == parent_id)
    
    containers = query.all()
    return [ContainerResponse.from_orm(container) for container in containers]


@router.get("/{container_id}", response_model=ContainerWithContentsResponse)
async def get_container(
    container_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific container with its contents.
    """
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Get contents
    contents = db.query(Contents).filter(Contents.container_id == container_id).all()
    
    container_response = ContainerResponse.from_orm(container)
    contents_response = [ContentsResponse.from_orm(content) for content in contents]
    
    return ContainerWithContentsResponse(
        **container_response.dict(),
        contents=contents_response
    )


@router.post("/", response_model=ContainerResponse)
async def create_container(
    container_data: ContainerCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create a new container.
    Implements US-5: Container Management.
    """
    # Validate container type exists
    container_type = db.query(ContainerType).filter(
        ContainerType.id == container_data.type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid container type ID"
        )
    
    # Validate parent container if specified
    if container_data.parent_container_id:
        parent = db.query(Container).filter(
            Container.id == container_data.parent_container_id,
            Container.active == True
        ).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent container ID"
            )
    
    # Create container
    container = Container(
        name=container_data.name,
        description=container_data.description,
        row=container_data.row,
        column=container_data.column,
        concentration=container_data.concentration,
        concentration_units=container_data.concentration_units,
        amount=container_data.amount,
        amount_units=container_data.amount_units,
        type_id=container_data.type_id,
        parent_container_id=container_data.parent_container_id,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(container)
    db.commit()
    db.refresh(container)
    
    return ContainerResponse.from_orm(container)


@router.patch("/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: UUID,
    container_data: ContainerUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update a container.
    """
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Update fields
    update_data = container_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(container, field, value)
    
    container.modified_by = current_user.id
    container.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(container)
    
    return ContainerResponse.from_orm(container)


# Contents endpoints
@router.get("/{container_id}/contents", response_model=ContentsListResponse)
async def get_container_contents(
    container_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get contents of a container with pagination.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Get contents with pagination
    query = db.query(Contents).filter(Contents.container_id == container_id)
    total = query.count()
    
    offset = (page - 1) * size
    contents = query.offset(offset).limit(size).all()
    
    pages = (total + size - 1) // size
    
    return ContentsListResponse(
        contents=[ContentsResponse.from_orm(content) for content in contents],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/{container_id}/contents", response_model=ContentsResponse)
async def add_sample_to_container(
    container_id: UUID,
    contents_data: ContentsCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Add a sample to a container (create contents).
    Implements US-6: Pooled Samples Creation.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Verify sample exists
    from models.sample import Sample
    sample = db.query(Sample).filter(
        Sample.id == contents_data.sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check if contents already exists
    existing_contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == contents_data.sample_id
    ).first()
    
    if existing_contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample already exists in this container"
        )
    
    # Create contents
    contents = Contents(
        container_id=container_id,
        sample_id=contents_data.sample_id,
        concentration=contents_data.concentration,
        concentration_units=contents_data.concentration_units,
        amount=contents_data.amount,
        amount_units=contents_data.amount_units
    )
    
    db.add(contents)
    db.commit()
    db.refresh(contents)
    
    return ContentsResponse.from_orm(contents)


@router.patch("/{container_id}/contents/{sample_id}", response_model=ContentsResponse)
async def update_container_contents(
    container_id: UUID,
    sample_id: UUID,
    contents_data: ContentsUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update contents of a container.
    """
    contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == sample_id
    ).first()
    
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contents not found"
        )
    
    # Update fields
    update_data = contents_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contents, field, value)
    
    db.commit()
    db.refresh(contents)
    
    return ContentsResponse.from_orm(contents)


@router.delete("/{container_id}/contents/{sample_id}")
async def remove_sample_from_container(
    container_id: UUID,
    sample_id: UUID,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Remove a sample from a container.
    """
    contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == sample_id
    ).first()
    
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contents not found"
        )
    
    db.delete(contents)
    db.commit()
    
    return {"message": "Sample removed from container successfully"}
