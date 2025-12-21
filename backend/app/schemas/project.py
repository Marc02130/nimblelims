"""
Pydantic schemas for projects
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProjectBase(BaseModel):
    """Base schema for project data"""
    name: str
    description: Optional[str] = None
    start_date: datetime
    client_id: UUID
    status: UUID


class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    start_date: datetime
    client_id: UUID
    status: UUID
    client: Optional[dict] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list response"""
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int

