"""Schemas for the sample-type transition catalog (E-14)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SampleTypeTransitionCreate(BaseModel):
    source_sample_type: UUID
    operation: str = Field(..., pattern="^(aliquot|pool)$")
    allowed_dest_sample_type: UUID
    active: bool = True


class SampleTypeTransitionUpdate(BaseModel):
    source_sample_type: Optional[UUID] = None
    operation: Optional[str] = Field(None, pattern="^(aliquot|pool)$")
    allowed_dest_sample_type: Optional[UUID] = None
    active: Optional[bool] = None


class SampleTypeTransitionRead(BaseModel):
    id: UUID
    client_id: UUID
    source_sample_type: UUID
    source_sample_type_name: Optional[str] = None
    operation: str
    allowed_dest_sample_type: UUID
    allowed_dest_sample_type_name: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True
