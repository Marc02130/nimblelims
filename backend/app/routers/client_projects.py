"""
Client Projects router for LIMS Post-MVP
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.client import ClientProject
from models.user import User
from app.schemas.client_project import (
    ClientProjectResponse,
    ClientProjectCreate,
    ClientProjectUpdate,
    ClientProjectListResponse,
)
from app.core.security import get_current_user
from app.core.rbac import require_permission
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ClientProjectListResponse)
async def get_client_projects(
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all accessible client projects with optional filtering and pagination.
    - Administrators see all client projects
    - Client users see only their own client's projects (via RLS)
    - Lab users see client projects they have access to via project associations
    """
    query = db.query(ClientProject).filter(ClientProject.active == True)
    
    # Apply access control based on user role
    if current_user.role.name == "Administrator":
        # Administrators can see all client projects
        pass
    elif current_user.client_id:
        # Client users can only see their own client's projects
        # RLS will also enforce this, but we filter here for efficiency
        query = query.filter(ClientProject.client_id == current_user.client_id)
    # Lab users without client_id will see projects via RLS based on project associations
    
    # Apply client_id filter if provided
    if client_id:
        query = query.filter(ClientProject.client_id == client_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    client_projects = query.order_by(ClientProject.name).offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Convert to response format
    result = []
    for cp in client_projects:
        result.append(ClientProjectResponse(
            id=cp.id,
            name=cp.name,
            description=cp.description,
            client_id=cp.client_id,
            active=cp.active,
            created_at=cp.created_at,
            created_by=cp.created_by,
            modified_at=cp.modified_at,
            modified_by=cp.modified_by
        ))
    
    return ClientProjectListResponse(
        client_projects=result,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{client_project_id}", response_model=ClientProjectResponse)
async def get_client_project(
    client_project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a client project by ID.
    Returns 404 if not found or not accessible.
    """
    client_project = db.query(ClientProject).filter(
        ClientProject.id == client_project_id,
        ClientProject.active == True
    ).first()
    
    if not client_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client project not found"
        )
    
    # RLS will enforce access control, but we can add explicit check here for clarity
    if current_user.role.name != "Administrator":
        if current_user.client_id and client_project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client project not found"
            )
    
    return ClientProjectResponse(
        id=client_project.id,
        name=client_project.name,
        description=client_project.description,
        client_id=client_project.client_id,
        active=client_project.active,
        created_at=client_project.created_at,
        created_by=client_project.created_by,
        modified_at=client_project.modified_at,
        modified_by=client_project.modified_by
    )


@router.post("", response_model=ClientProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_client_project(
    client_project_data: ClientProjectCreate,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Create a new client project.
    Requires project:manage permission.
    Sets audit fields (created_by, modified_by).
    """
    # Check for unique name
    existing_client_project = db.query(ClientProject).filter(
        ClientProject.name == client_project_data.name
    ).first()
    if existing_client_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client project name already exists"
        )
    
    # Verify client exists
    from models.client import Client
    client = db.query(Client).filter(Client.id == client_project_data.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client not found"
        )
    
    new_client_project = ClientProject(
        name=client_project_data.name,
        description=client_project_data.description,
        client_id=client_project_data.client_id,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_client_project)
    db.commit()
    db.refresh(new_client_project)
    
    return ClientProjectResponse(
        id=new_client_project.id,
        name=new_client_project.name,
        description=new_client_project.description,
        client_id=new_client_project.client_id,
        active=new_client_project.active,
        created_at=new_client_project.created_at,
        created_by=new_client_project.created_by,
        modified_at=new_client_project.modified_at,
        modified_by=new_client_project.modified_by
    )


@router.patch("/{client_project_id}", response_model=ClientProjectResponse)
async def update_client_project(
    client_project_id: UUID,
    client_project_data: ClientProjectUpdate,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Update a client project (partial update).
    Requires project:manage permission.
    Updates audit fields (modified_by, modified_at).
    """
    client_project = db.query(ClientProject).filter(
        ClientProject.id == client_project_id
    ).first()
    
    if not client_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client project not found"
        )
    
    # Check for unique name if updating
    if client_project_data.name and client_project_data.name != client_project.name:
        existing_client_project = db.query(ClientProject).filter(
            ClientProject.name == client_project_data.name
        ).first()
        if existing_client_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project name already exists"
            )
        client_project.name = client_project_data.name
    
    if client_project_data.description is not None:
        client_project.description = client_project_data.description
    
    if client_project_data.active is not None:
        client_project.active = client_project_data.active
    
    # Update audit fields
    client_project.modified_by = current_user.id
    # modified_at is updated automatically via onupdate in BaseModel
    
    db.commit()
    db.refresh(client_project)
    
    return ClientProjectResponse(
        id=client_project.id,
        name=client_project.name,
        description=client_project.description,
        client_id=client_project.client_id,
        active=client_project.active,
        created_at=client_project.created_at,
        created_by=client_project.created_by,
        modified_at=client_project.modified_at,
        modified_by=client_project.modified_by
    )


@router.delete("/{client_project_id}", status_code=status.HTTP_200_OK)
async def delete_client_project(
    client_project_id: UUID,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Soft delete a client project (sets active=False).
    Requires project:manage permission.
    """
    client_project = db.query(ClientProject).filter(
        ClientProject.id == client_project_id
    ).first()
    
    if not client_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client project not found"
        )
    
    # Soft delete
    client_project.active = False
    client_project.modified_by = current_user.id
    # modified_at is updated automatically via onupdate in BaseModel
    
    db.commit()
    
    return {"message": "Client project deleted successfully"}

