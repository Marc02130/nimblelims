"""
Pydantic schemas for results
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ResultBase(BaseModel):
    """Base schema for result data"""
    test_id: UUID = Field(..., description="ID of test")
    analyte_id: UUID = Field(..., description="ID of analyte")
    raw_result: Optional[str] = Field(None, max_length=255, description="Raw result value")
    reported_result: Optional[str] = Field(None, max_length=255, description="Reported result value")
    qualifiers: Optional[UUID] = Field(None, description="ID of qualifier from list_entries")
    calculated_result: Optional[str] = Field(None, max_length=255, description="Calculated result (post-MVP)")
    entry_date: datetime = Field(default_factory=datetime.utcnow, description="Date result was entered")
    entered_by: UUID = Field(..., description="ID of user who entered result")

    @validator('entry_date')
    def validate_entry_date(cls, v):
        if v > datetime.now():
            raise ValueError('Entry date cannot be in the future')
        return v


class ResultCreate(ResultBase):
    """Schema for creating a new result"""
    pass


class ResultUpdate(BaseModel):
    """Schema for updating a result"""
    raw_result: Optional[str] = Field(None, max_length=255)
    reported_result: Optional[str] = Field(None, max_length=255)
    qualifiers: Optional[UUID] = None
    calculated_result: Optional[str] = Field(None, max_length=255)
    entry_date: Optional[datetime] = None
    entered_by: Optional[UUID] = None

    @validator('entry_date')
    def validate_entry_date(cls, v):
        if v and v > datetime.now():
            raise ValueError('Entry date cannot be in the future')
        return v


class ResultResponse(ResultBase):
    """Schema for result response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class ResultListResponse(BaseModel):
    """Schema for result list response with pagination"""
    results: List[ResultResponse]
    total: int
    page: int
    size: int
    pages: int


class BatchResultEntryRequest(BaseModel):
    """Schema for entering results for a batch"""
    test_id: UUID = Field(..., description="ID of test")
    analyte_id: UUID = Field(..., description="ID of analyte")
    raw_result: Optional[str] = Field(None, max_length=255)
    reported_result: Optional[str] = Field(None, max_length=255)
    qualifiers: Optional[UUID] = None
    calculated_result: Optional[str] = Field(None, max_length=255)


class BatchResultsEntryRequest(BaseModel):
    """Schema for entering multiple results for a batch"""
    batch_id: UUID = Field(..., description="ID of batch")
    test_id: UUID = Field(..., description="ID of test")
    results: List[BatchResultEntryRequest] = Field(..., description="List of results to enter")


class ResultValidationRequest(BaseModel):
    """Schema for validating results against analysis_analytes rules"""
    test_id: UUID = Field(..., description="ID of test")
    analyte_id: UUID = Field(..., description="ID of analyte")
    raw_result: str = Field(..., description="Raw result to validate")
    reported_result: Optional[str] = Field(None, description="Reported result to validate")


class ResultValidationResponse(BaseModel):
    """Schema for result validation response"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list, description="Validation errors if any")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings if any")
    significant_figures: Optional[int] = Field(None, description="Required significant figures")
    data_type: Optional[str] = Field(None, description="Expected data type")
    high_value: Optional[float] = Field(None, description="High validation limit")
    low_value: Optional[float] = Field(None, description="Low validation limit")
