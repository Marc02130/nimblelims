"""
Pydantic schemas for batches
"""
from pydantic import Field, validator
from app.schemas._dates import store_calendar_day
from app.schemas._instants import APIModel as BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class BatchBase(BaseModel):
    """Base schema for batch data"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Batch name (auto-generated if not provided)")
    description: Optional[str] = None
    type: Optional[UUID] = Field(None, description="ID of batch type from list_entries")
    status: UUID = Field(..., description="ID of status from list_entries")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes as JSON")

    # Removed date validation - dates can be in the future for scheduling
    # End dates are typically set when batch is completed, not during creation


class QCAddition(BaseModel):
    """Schema for QC sample addition during batch creation"""
    qc_type: UUID = Field(..., description="ID of QC type from list_entries (e.g., Blank, Blank Spike, Duplicate, Matrix Spike)")
    container_type_id: UUID = Field(..., description="Container type ID - a new container of this type will be created for the QC sample")
    matrix_id: UUID = Field(..., description="Matrix ID from list_entries for the QC sample")
    notes: Optional[str] = Field(None, description="Optional notes for the QC sample")


class BatchCreate(BatchBase):
    """Schema for creating a new batch"""
    container_ids: Optional[List[UUID]] = Field(None, description="List of container IDs for cross-project batching")
    sample_ids: Optional[List[UUID]] = Field(None, description="List of sample IDs to include in the batch (for sample-based batching)")
    cross_project: Optional[bool] = Field(None, description="Flag to indicate cross-project batching (auto-detected if container_ids provided)")
    divergent_analyses: Optional[List[UUID]] = Field(None, description="List of analysis IDs that require separate sub-batches (future: child_batch_id FK)")
    qc_additions: Optional[List[QCAddition]] = Field(None, description="List of QC samples to auto-create and add to batch (US-27). QC samples are automatically assigned to the system Laboratory QC project.")

    @validator('start_date', 'end_date')
    def store_calendar_dates(cls, v):
        """Start and end are lab calendar days. A later day is allowed for scheduling."""
        return store_calendar_day(v)


class BatchUpdate(BaseModel):
    """Schema for updating a batch"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_attributes: Optional[Dict[str, Any]] = Field(None, description="Custom attributes as JSON")

    # Removed date validation - dates can be in the future for scheduling
    # End dates are typically set when batch is completed, not during creation
    @validator('start_date', 'end_date')
    def store_calendar_dates(cls, v):
        return store_calendar_day(v)


class BatchContainerRequest(BaseModel):
    """Schema for adding containers to batch"""
    container_id: UUID = Field(..., description="ID of container to add")
    position: Optional[str] = Field(None, max_length=50, description="Position in batch (e.g., 'A1', 'B2')")
    notes: Optional[str] = Field(None, description="Notes about this container in the batch")


class BatchContainerBody(BaseModel):
    """Container fields the batch grid edits. id is the container id."""
    id: UUID
    name: Optional[str] = None
    row: Optional[int] = None
    column: Optional[int] = None
    type_id: Optional[UUID] = None
    concentration: Optional[float] = None
    concentration_units: Optional[UUID] = None
    amount: Optional[float] = None
    amount_units: Optional[UUID] = None

    class Config:
        from_attributes = True


class BatchContainerResponse(BaseModel):
    """Schema for batch container response.

    id, row, and column are copied from the container. The grid edits that
    container, so a response without them becomes PATCH /containers/undefined.
    """
    batch_id: UUID
    container_id: UUID
    position: Optional[str] = None
    notes: Optional[str] = None
    id: UUID
    name: Optional[str] = None
    row: Optional[int] = None
    column: Optional[int] = None
    type_id: Optional[UUID] = None
    container: Optional[BatchContainerBody] = None

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
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Batch name (auto-generated if not provided)")
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: UUID = Field(..., description="ID of status from list_entries")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    containers: List[BatchContainerRequest] = Field(default_factory=list, description="Containers to add to batch")

    # Removed date validation - dates can be in the future for scheduling
    # End dates are typically set when batch is completed, not during creation
    @validator('start_date', 'end_date')
    def store_calendar_dates(cls, v):
        return store_calendar_day(v)


class BatchContentSample(BaseModel):
    """Sample fields Enter Results reads off a container content."""
    qc_type: Optional[UUID] = None


class BatchContainerContentRead(BaseModel):
    """One sample sitting in a batch container."""
    sample_id: UUID
    sample_name: Optional[str] = None
    qc_type: Optional[UUID] = None
    sample: Optional[BatchContentSample] = None


class BatchContainerRead(BaseModel):
    """Container plus contents for GET /batches/{id}/containers."""
    id: UUID
    name: Optional[str] = None
    row: Optional[int] = None
    column: Optional[int] = None
    contents: List[BatchContainerContentRead] = Field(default_factory=list)
