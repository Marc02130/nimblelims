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


class QCAddition(BaseModel):
    """Schema for QC sample addition during batch creation"""
    qc_type: UUID = Field(..., description="ID of QC type from list_entries (e.g., Blank, Blank Spike, Duplicate, Matrix Spike)")
    notes: Optional[str] = Field(None, description="Optional notes for the QC sample")


class BatchCreate(BatchBase):
    """Schema for creating a new batch"""
    container_ids: Optional[List[UUID]] = Field(None, description="List of container IDs for cross-project batching")
    cross_project: Optional[bool] = Field(None, description="Flag to indicate cross-project batching (auto-detected if container_ids provided)")
    divergent_analyses: Optional[List[UUID]] = Field(None, description="List of analysis IDs that require separate sub-batches (future: child_batch_id FK)")
    qc_additions: Optional[List[QCAddition]] = Field(None, description="List of QC samples to auto-create and add to batch (US-27)")


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


class BatchResponse(BatchBase):
    """Schema for batch response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID
    containers: Optional[List[BatchContainerResponse]] = Field(None, description="Containers in this batch")

    class Config:
        from_attributes = True


class BatchListResponse(BaseModel):
    """Schema for batch list response with pagination"""
    batches: List[BatchResponse]
    total: int
    page: int
    size: int
    pages: int


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
