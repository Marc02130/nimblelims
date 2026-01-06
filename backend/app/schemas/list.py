"""
Pydantic schemas for lists and list entries
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ListEntryResponse(BaseModel):
    """Schema for list entry response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    list_id: UUID

    class Config:
        from_attributes = True


class ListEntryCreate(BaseModel):
    """Schema for creating a list entry"""
    name: str
    description: Optional[str] = None
    active: bool = True


class ListEntryUpdate(BaseModel):
    """Schema for updating a list entry"""
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ListResponse(BaseModel):
    """Schema for list response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    entries: List[ListEntryResponse] = []

    class Config:
        from_attributes = True

