"""
Roles and permissions router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User, Role, Permission, role_permissions
from app.schemas.user import (
    RoleResponse,
    RoleWithPermissionsResponse,
    RoleCreate,
    RoleUpdate,
    RolePermissionsUpdate,
    PermissionResponse,
    PermissionCreate,
    PermissionUpdate,
)
from app.core.security import get_current_user
from app.core.rbac import require_any_permission
from uuid import UUID

router = APIRouter()


# Roles endpoints
@router.get("", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active roles.
    """
    roles = db.query(Role).filter(Role.active == True).order_by(Role.name).all()
    return [RoleResponse.from_orm(role) for role in roles]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Create a new role.
    Requires user:manage or config:edit permission.
    """
    # Check for unique name
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    new_role = Role(
        name=role_data.name,
        description=role_data.description,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return RoleResponse.from_orm(new_role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Update a role.
    Requires user:manage or config:edit permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check for unique name if updating
    if role_data.name and role_data.name != role.name:
        existing_role = db.query(Role).filter(Role.name == role_data.name).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )
        role.name = role_data.name
    
    if role_data.description is not None:
        role.description = role_data.description
    
    if role_data.active is not None:
        role.active = role_data.active
    
    role.modified_by = current_user.id
    db.commit()
    db.refresh(role)
    
    return RoleResponse.from_orm(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete a role.
    Requires user:manage or config:edit permission.
    Fails if role is assigned to any users.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if role is assigned to any users
    users_with_role = db.query(User).filter(User.role_id == role_id, User.active == True).count()
    if users_with_role > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role: {users_with_role} user(s) are assigned to this role"
        )
    
    role.active = False
    role.modified_by = current_user.id
    db.commit()
    
    return None


@router.get("/{role_id}/permissions", response_model=List[PermissionResponse])
async def get_role_permissions(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all permissions for a role.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    permissions = db.query(Permission).join(role_permissions).filter(
        role_permissions.c.role_id == role_id,
        Permission.active == True
    ).all()
    
    return [PermissionResponse.from_orm(perm) for perm in permissions]


@router.put("/{role_id}/permissions", response_model=List[PermissionResponse])
async def update_role_permissions(
    role_id: UUID,
    permissions_data: RolePermissionsUpdate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Update permissions for a role.
    Requires user:manage or config:edit permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Verify all permission IDs exist
    permissions = db.query(Permission).filter(
        Permission.id.in_(permissions_data.permission_ids),
        Permission.active == True
    ).all()
    
    if len(permissions) != len(permissions_data.permission_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more permission IDs are invalid"
        )
    
    # Clear existing permissions
    db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    
    # Add new permissions
    for perm_id in permissions_data.permission_ids:
        db.execute(role_permissions.insert().values(role_id=role_id, permission_id=perm_id))
    
    role.modified_by = current_user.id
    db.commit()
    
    # Return updated permissions
    updated_permissions = db.query(Permission).join(role_permissions).filter(
        role_permissions.c.role_id == role_id,
        Permission.active == True
    ).all()
    
    return [PermissionResponse.from_orm(perm) for perm in updated_permissions]



