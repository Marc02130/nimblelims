"""
Pydantic schemas for analytes
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class AnalyteResponse(BaseModel):
    """Schema for analyte response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class AnalyteCreate(BaseModel):
    """Schema for creating an analyte"""
    name: str
    description: Optional[str] = None


class AnalyteUpdate(BaseModel):
    """Schema for updating an analyte"""
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

