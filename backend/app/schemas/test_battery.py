"""
Pydantic schemas for test batteries
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class TestBatteryBase(BaseModel):
    """Base schema for test battery data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TestBatteryCreate(TestBatteryBase):
    """Schema for creating a new test battery"""
    pass


class TestBatteryUpdate(BaseModel):
    """Schema for updating a test battery"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None


class TestBatteryResponse(TestBatteryBase):
    """Schema for test battery response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: Optional[UUID]
    modified_at: datetime
    modified_by: Optional[UUID]
    analyses_count: Optional[int] = Field(None, description="Number of analyses in battery")

    class Config:
        from_attributes = True


class BatteryAnalysisBase(BaseModel):
    """Base schema for battery-analysis junction"""
    analysis_id: UUID = Field(..., description="ID of analysis")
    sequence: int = Field(..., ge=1, description="Sequence order (1-based)")
    optional: bool = Field(False, description="Whether this analysis is optional in the battery")


class BatteryAnalysisCreate(BatteryAnalysisBase):
    """Schema for adding an analysis to a battery"""
    pass


class BatteryAnalysisUpdate(BaseModel):
    """Schema for updating battery-analysis relationship"""
    sequence: Optional[int] = Field(None, ge=1, description="Sequence order (1-based)")
    optional: Optional[bool] = Field(None, description="Whether this analysis is optional in the battery")


class BatteryAnalysisResponse(BaseModel):
    """Schema for battery-analysis response"""
    battery_id: UUID
    analysis_id: UUID
    analysis_name: str
    analysis_method: Optional[str]
    sequence: int
    optional: bool

    class Config:
        from_attributes = True


class TestBatteryWithAnalysesResponse(TestBatteryResponse):
    """Schema for test battery response with analyses"""
    analyses: List[BatteryAnalysisResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TestBatteryListResponse(BaseModel):
    """Schema for test battery list response"""
    batteries: List[TestBatteryResponse]
    total: int
    page: int
    size: int
    pages: int

