"""
Pydantic schemas for containers and contents
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ContainerTypeBase(BaseModel):
    """Base schema for container type data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    capacity: Optional[float] = Field(None, ge=0, description="Capacity in base units")
    material: Optional[str] = Field(None, max_length=255)
    dimensions: Optional[str] = Field(None, max_length=50, description="e.g., '8x12'")
    preservative: Optional[str] = Field(None, max_length=255)


class ContainerTypeCreate(ContainerTypeBase):
    """Schema for creating a new container type"""
    pass


class ContainerTypeUpdate(BaseModel):
    """Schema for updating a container type"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    capacity: Optional[float] = Field(None, ge=0)
    material: Optional[str] = Field(None, max_length=255)
    dimensions: Optional[str] = Field(None, max_length=50)
    preservative: Optional[str] = Field(None, max_length=255)


class ContainerTypeResponse(ContainerTypeBase):
    """Schema for container type response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class ContainerBase(BaseModel):
    """Base schema for container data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    row: int = Field(1, ge=1, description="Row position (1-based)")
    column: int = Field(1, ge=1, description="Column position (1-based)")
    concentration: Optional[float] = Field(None, ge=0, description="Concentration value")
    concentration_units: Optional[UUID] = Field(None, description="ID of concentration units")
    amount: Optional[float] = Field(None, ge=0, description="Amount value")
    amount_units: Optional[UUID] = Field(None, description="ID of amount units")
    type_id: UUID = Field(..., description="ID of container type")
    parent_container_id: Optional[UUID] = Field(None, description="ID of parent container for hierarchy")

    @validator('concentration', 'amount')
    def validate_positive_values(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ContainerCreate(ContainerBase):
    """Schema for creating a new container"""
    pass


class ContainerUpdate(BaseModel):
    """Schema for updating a container"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    row: Optional[int] = Field(None, ge=1)
    column: Optional[int] = Field(None, ge=1)
    concentration: Optional[float] = Field(None, ge=0)
    concentration_units: Optional[UUID] = None
    amount: Optional[float] = Field(None, ge=0)
    amount_units: Optional[UUID] = None
    type_id: Optional[UUID] = None
    parent_container_id: Optional[UUID] = None

    @validator('concentration', 'amount')
    def validate_positive_values(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ContainerResponse(ContainerBase):
    """Schema for container response"""
    id: UUID
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID

    class Config:
        from_attributes = True


class ContentsBase(BaseModel):
    """Base schema for contents data"""
    container_id: UUID = Field(..., description="ID of container")
    sample_id: UUID = Field(..., description="ID of sample")
    concentration: Optional[float] = Field(None, ge=0, description="Concentration value")
    concentration_units: Optional[UUID] = Field(None, description="ID of concentration units")
    amount: Optional[float] = Field(None, ge=0, description="Amount value")
    amount_units: Optional[UUID] = Field(None, description="ID of amount units")

    @validator('concentration', 'amount')
    def validate_positive_values(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ContentsCreate(ContentsBase):
    """Schema for creating new contents"""
    pass


class ContentsUpdate(BaseModel):
    """Schema for updating contents"""
    concentration: Optional[float] = Field(None, ge=0)
    concentration_units: Optional[UUID] = None
    amount: Optional[float] = Field(None, ge=0)
    amount_units: Optional[UUID] = None

    @validator('concentration', 'amount')
    def validate_positive_values(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ContentsResponse(ContentsBase):
    """Schema for contents response"""
    container_id: UUID
    sample_id: UUID

    class Config:
        from_attributes = True


class ContainerWithContentsResponse(ContainerResponse):
    """Schema for container response with contents"""
    contents: List[ContentsResponse] = []


class ContentsListResponse(BaseModel):
    """Schema for contents list response with pagination"""
    contents: List[ContentsResponse]
    total: int
    page: int
    size: int
    pages: int
