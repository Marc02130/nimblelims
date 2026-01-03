"""
Pydantic schemas for help entries
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class HelpEntryResponse(BaseModel):
    """Schema for help entry response"""
    id: UUID
    section: str
    content: str
    role_filter: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class HelpEntryCreate(BaseModel):
    """Schema for creating a help entry"""
    section: str
    content: str
    role_filter: Optional[str] = None


class HelpEntryUpdate(BaseModel):
    """Schema for updating a help entry"""
    section: Optional[str] = None
    content: Optional[str] = None
    role_filter: Optional[str] = None
    active: Optional[bool] = None


class HelpEntryListResponse(BaseModel):
    """Schema for paginated help entry list response"""
    help_entries: List[HelpEntryResponse]
    total: int
    page: int
    size: int
    pages: int

