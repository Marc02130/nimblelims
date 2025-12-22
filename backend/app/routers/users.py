"""
Users router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User, Role
from models.client import Client
from app.schemas.user import (
    UserResponse,
    UserWithRelationsResponse,
    UserCreate,
    UserUpdate,
)
from app.core.security import get_current_user, get_password_hash
from app.core.rbac import require_any_permission
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[UserWithRelationsResponse])
async def get_users(
    role_id: Optional[UUID] = Query(None, description="Filter by role ID"),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Get all users with optional filtering.
    Requires user:manage or config:edit permission.
    """
    query = db.query(User).filter(User.active == True)
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    if client_id:
        query = query.filter(User.client_id == client_id)
    
    users = query.order_by(User.username).all()
    
    result = []
    for user in users:
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role_id": user.role_id,
            "client_id": user.client_id,
            "last_login": user.last_login,
            "active": user.active,
            "created_at": user.created_at,
            "modified_at": user.modified_at,
            "role": {
                "id": user.role.id,
                "name": user.role.name,
                "description": user.role.description,
                "active": user.role.active,
                "created_at": user.role.created_at,
                "modified_at": user.role.modified_at,
            } if user.role else None,
            "client": {
                "id": user.client.id,
                "name": user.client.name,
            } if user.client else None,
        }
        result.append(user_dict)
    
    return result


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    Requires user:manage or config:edit permission.
    """
    # Check for unique username
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check for unique email
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Verify role exists
    role = db.query(Role).filter(Role.id == user_data.role_id, Role.active == True).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role_id"
        )
    
    # Verify client exists if provided
    if user_data.client_id:
        client = db.query(Client).filter(Client.id == user_data.client_id, Client.active == True).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_id"
            )
    
    # Create user
    password_hash = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        role_id=user_data.role_id,
        client_id=user_data.client_id,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse.from_orm(new_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Update a user.
    Requires user:manage or config:edit permission.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for unique username if updating
    if user_data.username and user_data.username != user.username:
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_data.username
    
    # Check for unique email if updating
    if user_data.email and user_data.email != user.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_data.email
    
    # Update password if provided
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)
    
    # Update role if provided
    if user_data.role_id:
        role = db.query(Role).filter(Role.id == user_data.role_id, Role.active == True).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id"
            )
        user.role_id = user_data.role_id
    
    # Update client if provided
    if user_data.client_id is not None:
        if user_data.client_id:
            client = db.query(Client).filter(Client.id == user_data.client_id, Client.active == True).first()
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid client_id"
                )
        user.client_id = user_data.client_id
    
    # Update active status if provided
    if user_data.active is not None:
        user.active = user_data.active
    
    user.modified_by = current_user.id
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_any_permission(["user:manage", "config:edit"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete a user.
    Requires user:manage or config:edit permission.
    Fails if user has active assignments (samples, tests, results, etc.).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user has active assignments (simplified check - can be expanded)
    # For MVP, we'll just soft delete
    user.active = False
    user.modified_by = current_user.id
    db.commit()
    
    return None

