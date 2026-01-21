"""
Pydantic schemas for analyses and analysis-analyte rules
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class AnalyteSimple(BaseModel):
    """Simple analyte representation for embedding in analysis response"""
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisBase(BaseModel):
    """Base schema for analysis data"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Analysis name (auto-generated if not provided)")
    description: Optional[str] = None
    method: Optional[str] = Field(None, max_length=255, description="Analysis method")
    turnaround_time: Optional[int] = Field(None, ge=0, description="Turnaround time in days")
    cost: Optional[Decimal] = Field(None, ge=0, description="Analysis cost")
    shelf_life: Optional[int] = Field(None, ge=1, description="Days until expiration (expiration = date_sampled + shelf_life)")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")


class AnalysisCreate(BaseModel):
    """Schema for creating an analysis"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Analysis name (auto-generated if not provided)")
    description: Optional[str] = None
    method: str = Field(..., min_length=1, max_length=255, description="Analysis method (required)")
    turnaround_time: Optional[int] = Field(None, ge=0, description="Turnaround time in days")
    cost: Optional[Decimal] = Field(None, ge=0, description="Analysis cost")
    shelf_life: Optional[int] = Field(None, ge=1, description="Days until expiration (expiration = date_sampled + shelf_life)")
    custom_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom attributes as JSON")


class AnalysisUpdate(BaseModel):
    """Schema for updating an analysis (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    method: Optional[str] = Field(None, max_length=255)
    turnaround_time: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    shelf_life: Optional[int] = Field(None, ge=1, description="Days until expiration (expiration = date_sampled + shelf_life)")
    active: Optional[bool] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """Schema for analysis response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None
    method: Optional[str] = None
    turnaround_time: Optional[int] = None
    cost: Optional[Decimal] = None
    shelf_life: Optional[int] = Field(None, description="Days until expiration (expiration = date_sampled + shelf_life)")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")
    analytes: List[AnalyteSimple] = Field(default_factory=list, description="Linked analytes")

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    """Schema for paginated analysis list response"""
    analyses: List[AnalysisResponse]
    total: int
    page: int
    size: int
    pages: int


class AnalyteRuleResponse(BaseModel):
    """Schema for analysis-analyte rule response"""
    analyte_id: UUID
    analyte_name: str
    data_type: Optional[str] = None
    list_id: Optional[UUID] = None
    high_value: Optional[Decimal] = None
    low_value: Optional[Decimal] = None
    significant_figures: Optional[int] = None
    calculation: Optional[str] = None
    reported_name: Optional[str] = None
    display_order: Optional[int] = None
    is_required: bool
    default_value: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyteRuleCreate(BaseModel):
    """Schema for creating an analysis-analyte rule"""
    analyte_id: UUID
    data_type: Optional[str] = None
    list_id: Optional[UUID] = None
    high_value: Optional[Decimal] = None
    low_value: Optional[Decimal] = None
    significant_figures: Optional[int] = None
    calculation: Optional[str] = None
    reported_name: Optional[str] = None
    display_order: Optional[int] = None
    is_required: bool = False
    default_value: Optional[str] = None


class AnalyteRuleUpdate(BaseModel):
    """Schema for updating an analysis-analyte rule"""
    data_type: Optional[str] = None
    list_id: Optional[UUID] = None
    high_value: Optional[Decimal] = None
    low_value: Optional[Decimal] = None
    significant_figures: Optional[int] = None
    calculation: Optional[str] = None
    reported_name: Optional[str] = None
    display_order: Optional[int] = None
    is_required: Optional[bool] = None
    default_value: Optional[str] = None


class AnalyteLinkRequest(BaseModel):
    """Schema for linking analytes to an analysis"""
    analyte_ids: List[UUID] = Field(..., min_length=1, description="List of analyte IDs to link")
