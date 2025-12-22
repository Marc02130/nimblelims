"""
Pydantic schemas for analyses and analysis-analyte rules
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class AnalysisResponse(BaseModel):
    """Schema for analysis response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    method: Optional[str] = None
    turnaround_time: Optional[int] = None
    cost: Optional[Decimal] = None

    class Config:
        from_attributes = True


class AnalysisCreate(BaseModel):
    """Schema for creating an analysis"""
    name: str
    description: Optional[str] = None
    method: Optional[str] = None
    turnaround_time: Optional[int] = None
    cost: Optional[Decimal] = None


class AnalysisUpdate(BaseModel):
    """Schema for updating an analysis"""
    name: Optional[str] = None
    description: Optional[str] = None
    method: Optional[str] = None
    turnaround_time: Optional[int] = None
    cost: Optional[Decimal] = None
    active: Optional[bool] = None


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

