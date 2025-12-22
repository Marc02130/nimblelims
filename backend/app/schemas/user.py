"""
Pydantic schemas for users, roles, and permissions
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PermissionResponse(BaseModel):
    """Schema for permission response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    """Schema for creating a permission"""
    name: str
    description: Optional[str] = None


class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class RoleResponse(BaseModel):
    """Schema for role response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class RoleWithPermissionsResponse(RoleResponse):
    """Schema for role response with permissions"""
    permissions: List[PermissionResponse] = []


class RoleCreate(BaseModel):
    """Schema for creating a role"""
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class RolePermissionsUpdate(BaseModel):
    """Schema for updating role permissions"""
    permission_ids: List[UUID]


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    username: str
    email: str
    role_id: UUID
    client_id: Optional[UUID] = None
    last_login: Optional[datetime] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class UserWithRelationsResponse(UserResponse):
    """Schema for user response with relations"""
    role: Optional[RoleResponse] = None
    client: Optional[dict] = None  # Will be populated with client info


class UserCreate(BaseModel):
    """Schema for creating a user"""
    username: str
    email: EmailStr
    password: str
    role_id: UUID
    client_id: Optional[UUID] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    active: Optional[bool] = None

