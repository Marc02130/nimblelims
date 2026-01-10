"""
Pydantic schemas for projects
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ProjectBase(BaseModel):
    """Base schema for project data"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name (auto-generated if not provided)")
    description: Optional[str] = None
    start_date: datetime
    client_id: UUID
    client_project_id: Optional[UUID] = Field(None, description="Optional client project ID for grouping (US-25)")
    status: UUID
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name (auto-generated if not provided)")
    description: Optional[str] = None
    start_date: datetime
    client_id: UUID
    client_project_id: Optional[UUID] = Field(None, description="Optional client project ID for grouping (US-25)")
    status: UUID
    custom_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom attributes as JSON")


class ProjectUpdate(BaseModel):
    """Schema for updating a project (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    client_id: Optional[UUID] = None
    client_project_id: Optional[UUID] = Field(None, description="Optional client project ID for grouping (US-25)")
    status: Optional[UUID] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None
    start_date: datetime
    client_id: UUID
    client_project_id: Optional[UUID] = None
    status: UUID
    client: Optional[dict] = None
    client_project: Optional[dict] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list response"""
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int
