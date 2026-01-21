"""
Pydantic schemas for analytes
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class AnalyteDataType(str, Enum):
    """Enum for analyte data types"""
    numeric = "numeric"
    text = "text"
    date = "date"
    boolean = "boolean"


class AnalyteBase(BaseModel):
    """Base schema for analyte data"""
    name: str = Field(..., min_length=1, max_length=255, description="Analyte name (unique)")
    description: Optional[str] = None
    cas_number: Optional[str] = Field(None, max_length=50, description="CAS registry number")
    units_default: Optional[UUID] = Field(None, description="Default units FK to units.id")
    data_type: Optional[AnalyteDataType] = Field(None, description="Data type: numeric, text, date, boolean")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")


class AnalyteCreate(BaseModel):
    """Schema for creating an analyte"""
    name: str = Field(..., min_length=1, max_length=255, description="Analyte name (unique)")
    description: Optional[str] = None
    cas_number: Optional[str] = Field(None, max_length=50, description="CAS registry number")
    units_default: Optional[UUID] = Field(None, description="Default units FK to units.id")
    data_type: Optional[AnalyteDataType] = Field(None, description="Data type: numeric, text, date, boolean")
    custom_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom attributes as JSON")


class AnalyteUpdate(BaseModel):
    """Schema for updating an analyte (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cas_number: Optional[str] = Field(None, max_length=50)
    units_default: Optional[UUID] = None
    data_type: Optional[AnalyteDataType] = None
    active: Optional[bool] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class AnalyteResponse(BaseModel):
    """Schema for analyte response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None
    cas_number: Optional[str] = None
    units_default: Optional[UUID] = None
    data_type: Optional[str] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")

    class Config:
        from_attributes = True


class AnalyteListResponse(BaseModel):
    """Schema for paginated analyte list response"""
    analytes: List[AnalyteResponse]
    total: int
    page: int
    size: int
    pages: int
