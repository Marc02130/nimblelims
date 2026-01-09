"""
Projects router for NimbleLims
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from models.project import Project, ProjectUser
from models.user import User
from app.schemas.project import ProjectResponse, ProjectListResponse
from app.core.security import get_current_user
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all projects accessible to the current user.
    - Administrators see all projects
    - Lab users see projects they have access to via project_users
    - Client users see only projects for their client_id
    """
    try:
        # Eagerly load client relationship to avoid lazy loading issues
        query = db.query(Project).options(joinedload(Project.client)).filter(Project.active == True)
        
        # Apply access control based on user role
        if current_user.role.name == "Administrator":
            # Administrators can see all projects
            pass
        elif current_user.client_id:
            # Client users can only see their own client's projects
            query = query.filter(Project.client_id == current_user.client_id)
        else:
            # Lab users see projects they have access to via project_users
            accessible_project_ids = db.query(ProjectUser.project_id).filter(
                ProjectUser.user_id == current_user.id
            ).subquery()
            query = query.filter(Project.id.in_(accessible_project_ids))
        
        projects = query.order_by(Project.name).all()
        
        # Convert to response format using model_validate (Pydantic v2)
        result = []
        for project in projects:
            try:
                # Create response object
                project_response = ProjectResponse.model_validate(project)
                # Add client info if available
                if project.client:
                    project_response.client = {
                        "id": str(project.client.id),
                        "name": project.client.name,
                    }
                result.append(project_response)
            except Exception as e:
                logger.error(f"Error serializing project {project.id}: {e}", exc_info=True)
                # Skip this project if serialization fails
                continue
        
        return result
    except Exception as e:
        logger.error(f"Error in get_projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )

