"""
Pydantic schemas for samples
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class SampleBase(BaseModel):
    """Base schema for sample data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    report_date: Optional[datetime] = None
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    status: UUID = Field(..., description="ID of status from list_entries")
    matrix: UUID = Field(..., description="ID of matrix from list_entries")
    temperature: Optional[float] = None
    parent_sample_id: Optional[UUID] = None
    project_id: UUID = Field(..., description="ID of project")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")

    @validator('due_date', 'received_date', 'report_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class SampleCreate(SampleBase):
    """Schema for creating a new sample"""
    pass


class SampleUpdate(BaseModel):
    """Schema for updating a sample"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    report_date: Optional[datetime] = None
    sample_type: Optional[UUID] = None
    status: Optional[UUID] = None
    matrix: Optional[UUID] = None
    temperature: Optional[float] = None
    parent_sample_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    qc_type: Optional[UUID] = None

    @validator('due_date', 'received_date', 'report_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class SampleResponse(SampleBase):
    """Schema for sample response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class SampleListResponse(BaseModel):
    """Schema for sample list response with pagination"""
    samples: List[SampleResponse]
    total: int
    page: int
    size: int
    pages: int


class SampleAccessioningRequest(BaseModel):
    """Schema for sample accessioning workflow"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: datetime = Field(..., description="Required for accessioning")
    received_date: datetime = Field(..., description="Required for accessioning")
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    matrix: UUID = Field(..., description="ID of matrix from list_entries")
    temperature: Optional[float] = None
    project_id: UUID = Field(..., description="ID of project")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")
    anomalies: Optional[str] = Field(None, description="Notes about any anomalies found")
    double_entry_required: bool = Field(False, description="Whether double entry validation is required")
    assigned_tests: List[UUID] = Field(default_factory=list, description="List of analysis IDs to assign")
    battery_id: Optional[UUID] = Field(None, description="ID of test battery to assign (creates tests for all analyses in battery)")

    @validator('due_date', 'received_date')
    def validate_dates(cls, v):
        if v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v
