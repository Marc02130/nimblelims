"""
Pydantic schemas for client projects
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClientProjectBase(BaseModel):
    """Base schema for client project data"""
    name: str = Field(..., min_length=1, max_length=255, description="Client project name (unique)")
    description: Optional[str] = Field(None, description="Client project description")
    client_id: UUID = Field(..., description="ID of the client that owns this project")


class ClientProjectCreate(ClientProjectBase):
    """Schema for creating a new client project"""
    pass


class ClientProjectUpdate(BaseModel):
    """Schema for updating a client project (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Client project name (unique)")
    description: Optional[str] = Field(None, description="Client project description")
    active: Optional[bool] = Field(None, description="Whether the client project is active")


class ClientProjectResponse(ClientProjectBase):
    """Schema for client project response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: Optional[UUID]
    modified_at: datetime
    modified_by: Optional[UUID]

    class Config:
        from_attributes = True


class ClientProjectListResponse(BaseModel):
    """Schema for paginated client project list response"""
    client_projects: list[ClientProjectResponse]
    total: int
    page: int
    size: int
    pages: int

