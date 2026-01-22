"""
Role-Based Access Control (RBAC) dependencies for NimbleLims
"""
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User, Role, Permission
from app.core.security import get_current_user, get_user_permissions
from uuid import UUID

# System client ID (hardcoded for consistency with migrations)
SYSTEM_CLIENT_ID = UUID('00000000-0000-0000-0000-000000000001')


def is_system_client_or_admin(user: User) -> bool:
    """
    Check if user is Administrator or associated with System client (lab employees).
    System client users and Administrators have full access to all data.
    """
    if user.role.name == "Administrator":
        return True
    if user.client_id == SYSTEM_CLIENT_ID:
        return True
    return False


def validate_client_access(user: User, project_client_id: Optional[UUID]) -> None:
    """
    Validate that user has access to a project based on client_id.
    Raises HTTPException 403 if access is denied.
    
    Rules:
    - Administrators: Full access
    - System client users (lab employees): Full access
    - Regular client users: Only if project.client_id == user.client_id
    """
    if is_system_client_or_admin(user):
        return  # Full access granted
    
    if project_client_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: project client_id is required"
        )
    
    if user.client_id != project_client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient client permissions"
        )


def require_permission(permission: str):
    """
    Dependency factory for permission-based authorization.
    Returns a dependency that checks if the current user has the required permission.
    """
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = get_user_permissions(current_user, db)
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


def require_any_permission(permissions: List[str]):
    """
    Dependency factory for requiring any of the specified permissions.
    Returns a dependency that checks if the current user has at least one of the required permissions.
    """
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = get_user_permissions(current_user, db)
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following permissions required: {', '.join(permissions)}"
            )
        return current_user
    
    return permission_checker


def require_all_permissions(permissions: List[str]):
    """
    Dependency factory for requiring all of the specified permissions.
    Returns a dependency that checks if the current user has all of the required permissions.
    """
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = get_user_permissions(current_user, db)
        missing_permissions = [perm for perm in permissions if perm not in user_permissions]
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        return current_user
    
    return permission_checker


def require_role(role_name: str):
    """
    Dependency factory for role-based authorization.
    Returns a dependency that checks if the current user has the required role.
    """
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if current_user.role.name != role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        return current_user
    
    return role_checker


def require_any_role(role_names: List[str]):
    """
    Dependency factory for requiring any of the specified roles.
    Returns a dependency that checks if the current user has at least one of the required roles.
    """
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if current_user.role.name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following roles required: {', '.join(role_names)}"
            )
        return current_user
    
    return role_checker


def require_client_access(client_id: Optional[str] = None):
    """
    Dependency factory for client-based data access control.
    Ensures users can only access data from their own client or if they're an admin.
    """
    def client_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Admins can access all data
        if current_user.role.name == "Administrator":
            return current_user
        
        # If client_id is specified, check if user belongs to that client
        if client_id and current_user.client_id != client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient client permissions"
            )
        
        # If no client_id specified, user can only access their own client's data
        if not current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: user not associated with any client"
            )
        
        return current_user
    
    return client_checker


def require_project_access(project_id: Optional[str] = None):
    """
    Dependency factory for project-based data access control.
    Ensures users can only access data from projects they have access to.
    """
    def project_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Admins can access all data
        if current_user.role.name == "Administrator":
            return current_user
        
        # If project_id is specified, check if user has access to that project
        if project_id:
            from models.project import ProjectUser
            project_access = db.query(ProjectUser).filter(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == current_user.id
            ).first()
            
            if not project_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: insufficient project permissions"
                )
        
        return current_user
    
    return project_checker


# Pre-defined permission dependencies for common operations
require_sample_create = require_permission("sample:create")
require_sample_read = require_permission("sample:read")
require_sample_update = require_permission("sample:update")
require_sample_delete = require_permission("sample:delete")

require_test_assign = require_permission("test:assign")
require_test_update = require_permission("test:update")

require_result_enter = require_permission("result:enter")
require_result_review = require_permission("result:review")
require_result_read = require_permission("result:read")
require_result_update = require_permission("result:update")
require_result_delete = require_permission("result:delete")

require_batch_manage = require_permission("batch:manage")
require_batch_read = require_permission("batch:read")
require_batch_update = require_permission("batch:update")
require_batch_delete = require_permission("batch:delete")

require_project_manage = require_permission("project:manage")
require_project_read = require_permission("project:read")

require_user_manage = require_permission("user:manage")
require_config_edit = require_permission("config:edit")

require_analysis_manage = require_permission("analysis:manage")

# Role-based dependencies
require_admin = require_role("Administrator")
require_lab_manager = require_any_role(["Administrator", "Lab Manager"])
require_lab_technician = require_any_role(["Administrator", "Lab Manager", "Lab Technician"])
require_client = require_any_role(["Administrator", "Lab Manager", "Lab Technician", "Client"])
