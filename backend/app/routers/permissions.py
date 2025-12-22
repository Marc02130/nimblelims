"""
Permissions router for LIMS MVP
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User, Permission
from app.schemas.user import (
    PermissionResponse,
    PermissionCreate,
    PermissionUpdate,
)
from app.core.security import get_current_user
from app.core.rbac import require_any_permission
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[PermissionResponse])
async def get_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active permissions.
    """
    permissions = db.query(Permission).filter(Permission.active == True).order_by(Permission.name).all()
    return [PermissionResponse.from_orm(perm) for perm in permissions]


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Create a new permission.
    Requires user:manage or config:edit permission.
    """
    # Check for unique name
    existing_permission = db.query(Permission).filter(Permission.name == permission_data.name).first()
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission name already exists"
        )
    
    new_permission = Permission(
        name=permission_data.name,
        description=permission_data.description,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    
    return PermissionResponse.from_orm(new_permission)


@router.patch("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: UUID,
    permission_data: PermissionUpdate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Update a permission.
    Requires user:manage or config:edit permission.
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Check for unique name if updating
    if permission_data.name and permission_data.name != permission.name:
        existing_permission = db.query(Permission).filter(Permission.name == permission_data.name).first()
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission name already exists"
            )
        permission.name = permission_data.name
    
    if permission_data.description is not None:
        permission.description = permission_data.description
    
    if permission_data.active is not None:
        permission.active = permission_data.active
    
    permission.modified_by = current_user.id
    db.commit()
    db.refresh(permission)
    
    return PermissionResponse.from_orm(permission)


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete a permission.
    Requires user:manage or config:edit permission.
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    permission.active = False
    permission.modified_by = current_user.id
    db.commit()
    
    return None

