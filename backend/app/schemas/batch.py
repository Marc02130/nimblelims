"""
Pydantic schemas for batches
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class BatchBase(BaseModel):
    """Base schema for batch data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[UUID] = Field(None, description="ID of batch type from list_entries")
    status: UUID = Field(..., description="ID of status from list_entries")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v


class BatchCreate(BatchBase):
    """Schema for creating a new batch"""
    pass


class BatchUpdate(BaseModel):
    """Schema for updating a batch"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v


class BatchResponse(BatchBase):
    """Schema for batch response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class BatchListResponse(BaseModel):
    """Schema for batch list response with pagination"""
    batches: List[BatchResponse]
    total: int
    page: int
    size: int
    pages: int


class BatchContainerRequest(BaseModel):
    """Schema for adding containers to batch"""
    container_id: UUID = Field(..., description="ID of container to add")
    position: Optional[str] = Field(None, max_length=50, description="Position in batch (e.g., 'A1', 'B2')")
    notes: Optional[str] = Field(None, description="Notes about this container in the batch")


class BatchContainerResponse(BaseModel):
    """Schema for batch container response"""
    batch_id: UUID
    container_id: UUID
    position: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class BatchCreateWithContainersRequest(BaseModel):
    """Schema for creating batch with containers"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: UUID = Field(..., description="ID of status from list_entries")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    containers: List[BatchContainerRequest] = Field(default_factory=list, description="Containers to add to batch")

    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v
