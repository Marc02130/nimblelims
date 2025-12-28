"""
Pydantic schemas for samples
"""
from pydantic import BaseModel, Field, validator, root_validator
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


class BulkSampleUnique(BaseModel):
    """Schema for unique fields per sample in bulk accessioning"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Sample name (auto-generated if not provided)")
    client_sample_id: Optional[str] = Field(None, max_length=255, description="Client-provided sample ID")
    container_name: str = Field(..., min_length=1, max_length=255, description="Container name/barcode")
    temperature: Optional[float] = Field(None, description="Temperature override")
    anomalies: Optional[str] = Field(None, description="Anomalies notes override")
    description: Optional[str] = Field(None, description="Description override")

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class BulkSampleAccessioningRequest(BaseModel):
    """Schema for bulk sample accessioning workflow (US-24)"""
    # Common fields shared across all samples
    due_date: datetime = Field(..., description="Required for accessioning")
    received_date: datetime = Field(..., description="Required for accessioning")
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    matrix: UUID = Field(..., description="ID of matrix from list_entries")
    project_id: UUID = Field(..., description="ID of project")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")
    assigned_tests: List[UUID] = Field(default_factory=list, description="List of analysis IDs to assign")
    battery_id: Optional[UUID] = Field(None, description="ID of test battery to assign")
    container_type_id: UUID = Field(..., description="ID of container type")
    # Unique fields per sample
    uniques: List[BulkSampleUnique] = Field(..., min_items=1, description="List of unique fields per sample")
    # Auto-naming options
    auto_name_prefix: Optional[str] = Field(None, max_length=200, description="Prefix for auto-generated names (e.g., 'SAMPLE-')")
    auto_name_start: Optional[int] = Field(None, ge=1, description="Starting number for auto-generated names")

    @validator('due_date', 'received_date')
    def validate_dates(cls, v):
        if v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('uniques')
    def validate_uniques_have_names_or_auto_naming(cls, v, values):
        """Ensure either names are provided or auto-naming is configured"""
        if not v:
            return v
        
        has_names = any(unique.name for unique in v)
        has_auto_naming = values.get('auto_name_prefix') is not None
        
        if not has_names and not has_auto_naming:
            raise ValueError('Either provide names in uniques or configure auto_name_prefix')
        
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


class BulkSampleUnique(BaseModel):
    """Schema for unique fields per sample in bulk accessioning"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Sample name (auto-generated if not provided)")
    client_sample_id: Optional[str] = Field(None, max_length=255, description="Client-provided sample ID")
    container_name: str = Field(..., min_length=1, max_length=255, description="Container name/barcode")
    temperature: Optional[float] = Field(None, description="Temperature override")
    anomalies: Optional[str] = Field(None, description="Anomalies notes override")
    description: Optional[str] = Field(None, description="Description override")

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class BulkSampleAccessioningRequest(BaseModel):
    """Schema for bulk sample accessioning workflow (US-24)"""
    # Common fields shared across all samples
    due_date: datetime = Field(..., description="Required for accessioning")
    received_date: datetime = Field(..., description="Required for accessioning")
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    matrix: UUID = Field(..., description="ID of matrix from list_entries")
    project_id: UUID = Field(..., description="ID of project")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")
    assigned_tests: List[UUID] = Field(default_factory=list, description="List of analysis IDs to assign")
    battery_id: Optional[UUID] = Field(None, description="ID of test battery to assign")
    container_type_id: UUID = Field(..., description="ID of container type")
    # Unique fields per sample
    uniques: List[BulkSampleUnique] = Field(..., min_items=1, description="List of unique fields per sample")
    # Auto-naming options
    auto_name_prefix: Optional[str] = Field(None, max_length=200, description="Prefix for auto-generated names (e.g., 'SAMPLE-')")
    auto_name_start: Optional[int] = Field(None, ge=1, description="Starting number for auto-generated names")

    @validator('due_date', 'received_date')
    def validate_dates(cls, v):
        if v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('uniques')
    def validate_uniques_have_names_or_auto_naming(cls, v, values):
        """Ensure either names are provided or auto-naming is configured"""
        if not v:
            return v
        
        has_names = any(unique.name for unique in v)
        has_auto_naming = values.get('auto_name_prefix') is not None
        
        if not has_names and not has_auto_naming:
            raise ValueError('Either provide names in uniques or configure auto_name_prefix')
        
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
    client_project_id: Optional[UUID] = Field(None, description="ID of client project (optional, for grouping)")
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


class BulkSampleUnique(BaseModel):
    """Schema for unique fields per sample in bulk accessioning"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Sample name (auto-generated if not provided)")
    client_sample_id: Optional[str] = Field(None, max_length=255, description="Client-provided sample ID")
    container_name: str = Field(..., min_length=1, max_length=255, description="Container name/barcode")
    temperature: Optional[float] = Field(None, description="Temperature override")
    anomalies: Optional[str] = Field(None, description="Anomalies notes override")
    description: Optional[str] = Field(None, description="Description override")

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class BulkSampleAccessioningRequest(BaseModel):
    """Schema for bulk sample accessioning workflow (US-24)"""
    # Common fields shared across all samples
    due_date: datetime = Field(..., description="Required for accessioning")
    received_date: datetime = Field(..., description="Required for accessioning")
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    matrix: UUID = Field(..., description="ID of matrix from list_entries")
    project_id: UUID = Field(..., description="ID of project")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")
    assigned_tests: List[UUID] = Field(default_factory=list, description="List of analysis IDs to assign")
    battery_id: Optional[UUID] = Field(None, description="ID of test battery to assign")
    container_type_id: UUID = Field(..., description="ID of container type")
    # Unique fields per sample
    uniques: List[BulkSampleUnique] = Field(..., min_items=1, description="List of unique fields per sample")
    # Auto-naming options
    auto_name_prefix: Optional[str] = Field(None, max_length=200, description="Prefix for auto-generated names (e.g., 'SAMPLE-')")
    auto_name_start: Optional[int] = Field(None, ge=1, description="Starting number for auto-generated names")

    @validator('due_date', 'received_date')
    def validate_dates(cls, v):
        if v > datetime.now():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('uniques')
    def validate_uniques_have_names_or_auto_naming(cls, v, values):
        """Ensure either names are provided or auto-naming is configured"""
        if not v:
            return v
        
        has_names = any(unique.name for unique in v)
        has_auto_naming = values.get('auto_name_prefix') is not None
        
        if not has_names and not has_auto_naming:
            raise ValueError('Either provide names in uniques or configure auto_name_prefix')
        
        return v
