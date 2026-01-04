"""
Pydantic schemas for tests
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class TestBase(BaseModel):
    """Base schema for test data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sample_id: UUID = Field(..., description="ID of sample")
    analysis_id: UUID = Field(..., description="ID of analysis")
    status: UUID = Field(..., description="ID of status from list_entries")
    review_date: Optional[datetime] = None
    test_date: Optional[datetime] = None
    technician_id: Optional[UUID] = Field(None, description="ID of technician user")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")

    @validator('review_date', 'test_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v


class TestCreate(TestBase):
    """Schema for creating a new test"""
    pass


class TestUpdate(BaseModel):
    """Schema for updating a test"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sample_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    status: Optional[UUID] = None
    review_date: Optional[datetime] = None
    test_date: Optional[datetime] = None
    technician_id: Optional[UUID] = None
    custom_attributes: Optional[Dict[str, Any]] = Field(None, description="Custom attributes as JSON")

    @validator('review_date', 'test_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v


class TestResponse(TestBase):
    """Schema for test response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class TestListResponse(BaseModel):
    """Schema for test list response with pagination"""
    tests: List[TestResponse]
    total: int
    page: int
    size: int
    pages: int


class TestAssignmentRequest(BaseModel):
    """Schema for assigning tests to samples"""
    sample_id: UUID = Field(..., description="ID of sample")
    analysis_id: UUID = Field(..., description="ID of analysis to assign")
    technician_id: Optional[UUID] = Field(None, description="ID of technician user")
    test_date: Optional[datetime] = Field(None, description="Planned test date")

    @validator('test_date')
    def validate_test_date(cls, v):
        if v and v > datetime.now():
            raise ValueError('Test date cannot be in the future')
        return v


class TestStatusUpdateRequest(BaseModel):
    """Schema for updating test status"""
    status: UUID = Field(..., description="ID of new status from list_entries")
    review_date: Optional[datetime] = None
    test_date: Optional[datetime] = None
    technician_id: Optional[UUID] = None

    @validator('review_date', 'test_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v


class TestReviewRequest(BaseModel):
    """Schema for reviewing tests"""
    review_date: datetime = Field(..., description="Review completion date")
    notes: Optional[str] = Field(None, description="Review notes")

    @validator('review_date')
    def validate_review_date(cls, v):
        if v > datetime.now():
            raise ValueError('Review date cannot be in the future')
        return v
