"""
Projects router for NimbleLIMS
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from app.database import get_db
from models.project import Project
from models.user import User
from models.client import Client, ClientProject
from app.schemas.project import (
    ProjectResponse,
    ProjectListResponse,
    ProjectCreate,
    ProjectUpdate,
)
from app.core.security import get_current_user
from app.core.rbac import require_permission
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    status: Optional[UUID] = Query(None, description="Filter by status"),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all projects accessible to the current user with optional filtering and pagination.
    - Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
    - No Python-level filtering is applied - RLS automatically filters projects based on projects_access policy
    - Administrators see all projects
    - Lab Technicians and Lab Managers see all active projects (per RLS policy in migration 0024)
    - Client users see only projects for their client_id (RLS enforced)
    - Lab users with project_users entries see those specific projects (via has_project_access function)
    - The session variable app.current_user_id is set via set_current_user_id() in get_current_user() dependency
    """
    try:
        # Base query with eager loading to avoid lazy loading issues
        # RLS will automatically filter based on projects_access policy
        # No Python-level filtering applied - RLS handles all access control
        query = db.query(Project).options(
            joinedload(Project.client),
            joinedload(Project.client_project)
        ).filter(Project.active == True)
        
        # Apply filters
        if status:
            query = query.filter(Project.status == status)
        if client_id:
            query = query.filter(Project.client_id == client_id)
        
        # Get total count (RLS will filter this automatically)
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        projects = query.order_by(Project.name).offset(offset).limit(size).all()
        
        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 0
        
        # Convert to response format
        result = []
        for project in projects:
            try:
                # Create response object
                project_response = ProjectResponse(
                    id=project.id,
                    name=project.name,
                    description=project.description,
                    active=project.active,
                    created_at=project.created_at,
                    modified_at=project.modified_at,
                    created_by=project.created_by,
                    modified_by=project.modified_by,
                    start_date=project.start_date,
                    client_id=project.client_id,
                    client_project_id=project.client_project_id,
                    status=project.status,
                    custom_attributes=project.custom_attributes or {},
                )
                # Add client info if available
                if project.client:
                    project_response.client = {
                        "id": str(project.client.id),
                        "name": project.client.name,
                    }
                # Add client_project info if available
                if project.client_project:
                    project_response.client_project = {
                        "id": str(project.client_project.id),
                        "name": project.client_project.name,
                    }
                result.append(project_response)
            except Exception as e:
                logger.error(f"Error serializing project {project.id}: {e}", exc_info=True)
                # Skip this project if serialization fails
                continue
        
        return ProjectListResponse(
            projects=result,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except Exception as e:
        logger.error(f"Error in get_projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single project by ID.
    Access controlled via RLS (projects_access policy).
    Returns 404 if project not found or user doesn't have access.
    """
    try:
        # RLS will automatically filter based on projects_access policy
        project = db.query(Project).options(
            joinedload(Project.client),
            joinedload(Project.client_project)
        ).filter(
            Project.id == project_id,
            Project.active == True
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Create response object
        project_response = ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            active=project.active,
            created_at=project.created_at,
            modified_at=project.modified_at,
            created_by=project.created_by,
            modified_by=project.modified_by,
            start_date=project.start_date,
            client_id=project.client_id,
            client_project_id=project.client_project_id,
            status=project.status,
            custom_attributes=project.custom_attributes or {},
        )
        # Add client info if available
        if project.client:
            project_response.client = {
                "id": str(project.client.id),
                "name": project.client.name,
            }
        # Add client_project info if available
        if project.client_project:
            project_response.client_project = {
                "id": str(project.client_project.id),
                "name": project.client_project.name,
            }
        
        return project_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}"
        )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Create a new project.
    Requires project:manage permission.
    Sets audit fields (created_by, modified_by).
    Validates client_id and client_project_id if provided.
    """
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == project_data.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client not found"
            )
        
        # Validate client_project_id if provided
        if project_data.client_project_id:
            client_project = db.query(ClientProject).filter(
                ClientProject.id == project_data.client_project_id
            ).first()
            if not client_project:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client project not found"
                )
            # Verify client_project belongs to the same client
            if client_project.client_id != project_data.client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client project does not belong to the specified client"
                )
        
        # Validate custom_attributes if provided
        validated_custom_attributes = {}
        if project_data.custom_attributes:
            from app.core.custom_attributes import validate_custom_attributes
            try:
                validated_custom_attributes = validate_custom_attributes(
                    db, "projects", project_data.custom_attributes
                )
            except HTTPException:
                raise
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # Generate name if not provided (using client name + timestamp)
        project_name = project_data.name
        if not project_name:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            project_name = f"{client.name}-{timestamp}"
        
        # Check for unique name
        existing_project = db.query(Project).filter(Project.name == project_name).first()
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name already exists"
            )
        
        new_project = Project(
            name=project_name,
            description=project_data.description,
            start_date=project_data.start_date,
            client_id=project_data.client_id,
            client_project_id=project_data.client_project_id,
            status=project_data.status,
            custom_attributes=validated_custom_attributes,
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        # Load relationships for response
        db.refresh(new_project, ["client", "client_project"])
        
        # Create response object
        project_response = ProjectResponse(
            id=new_project.id,
            name=new_project.name,
            description=new_project.description,
            active=new_project.active,
            created_at=new_project.created_at,
            modified_at=new_project.modified_at,
            created_by=new_project.created_by,
            modified_by=new_project.modified_by,
            start_date=new_project.start_date,
            client_id=new_project.client_id,
            client_project_id=new_project.client_project_id,
            status=new_project.status,
            custom_attributes=new_project.custom_attributes or {},
        )
        # Add client info
        if new_project.client:
            project_response.client = {
                "id": str(new_project.client.id),
                "name": new_project.client.name,
            }
        # Add client_project info if available
        if new_project.client_project:
            project_response.client_project = {
                "id": str(new_project.client_project.id),
                "name": new_project.client_project.name,
            }
        
        return project_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Update a project (partial update).
    Requires project:manage permission.
    Updates audit fields (modified_by, modified_at).
    Validates client_id and client_project_id if provided.
    """
    try:
        # RLS will automatically filter based on projects_access policy
        project = db.query(Project).options(
            joinedload(Project.client),
            joinedload(Project.client_project)
        ).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check for unique name if updating
        if project_data.name and project_data.name != project.name:
            existing_project = db.query(Project).filter(Project.name == project_data.name).first()
            if existing_project:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project name already exists"
                )
            project.name = project_data.name
        
        # Update fields if provided
        if project_data.description is not None:
            project.description = project_data.description
        
        if project_data.start_date is not None:
            project.start_date = project_data.start_date
        
        if project_data.client_id is not None:
            # Verify client exists
            client = db.query(Client).filter(Client.id == project_data.client_id).first()
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client not found"
                )
            project.client_id = project_data.client_id
        
        if project_data.client_project_id is not None:
            if project_data.client_project_id:
                # Validate client_project_id
                client_project = db.query(ClientProject).filter(
                    ClientProject.id == project_data.client_project_id
                ).first()
                if not client_project:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Client project not found"
                    )
                # Verify client_project belongs to the project's client
                target_client_id = project_data.client_id if project_data.client_id else project.client_id
                if client_project.client_id != target_client_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Client project does not belong to the specified client"
                    )
            project.client_project_id = project_data.client_project_id
        
        if project_data.status is not None:
            project.status = project_data.status
        
        if project_data.active is not None:
            project.active = project_data.active
        
        # Validate and update custom_attributes if provided
        if project_data.custom_attributes is not None:
            from app.core.custom_attributes import validate_custom_attributes
            try:
                validated_custom_attributes = validate_custom_attributes(
                    db, "projects", project_data.custom_attributes
                )
                project.custom_attributes = validated_custom_attributes
            except HTTPException:
                raise
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        project.modified_by = current_user.id
        db.commit()
        db.refresh(project, ["client", "client_project"])
        
        # Create response object
        project_response = ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            active=project.active,
            created_at=project.created_at,
            modified_at=project.modified_at,
            created_by=project.created_by,
            modified_by=project.modified_by,
            start_date=project.start_date,
            client_id=project.client_id,
            client_project_id=project.client_project_id,
            status=project.status,
            custom_attributes=project.custom_attributes or {},
        )
        # Add client info
        if project.client:
            project_response.client = {
                "id": str(project.client.id),
                "name": project.client.name,
            }
        # Add client_project info if available
        if project.client_project:
            project_response.client_project = {
                "id": str(project.client_project.id),
                "name": project.client_project.name,
            }
        
        return project_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db)
):
    """
    Soft delete a project (sets active=false).
    Requires project:manage permission.
    Updates audit fields (modified_by, modified_at).
    """
    try:
        # RLS will automatically filter based on projects_access policy
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Soft delete
        project.active = False
        project.modified_by = current_user.id
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
