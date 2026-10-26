"""Pydantic schemas for instrument types (list), instruments, and CRO sources."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import Field, ConfigDict
from app.schemas._instants import APIModel as BaseModel

InstrumentStatus = Literal["in_service", "out_of_service", "retired"]


class InstrumentTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    active: bool = True


class InstrumentTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None


class InstrumentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime


class InstrumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instrument_type_id: UUID
    vendor_id: Optional[UUID] = None
    model: Optional[str] = Field(None, max_length=255)
    serial_number: Optional[str] = Field(None, max_length=255)
    asset_tag: Optional[str] = Field(None, max_length=255)
    location_id: Optional[UUID] = None
    status: InstrumentStatus = "in_service"
    active: bool = True
    maintenance_tracked: Optional[bool] = None


class InstrumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instrument_type_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    model: Optional[str] = Field(None, max_length=255)
    serial_number: Optional[str] = Field(None, max_length=255)
    asset_tag: Optional[str] = Field(None, max_length=255)
    location_id: Optional[UUID] = None
    status: Optional[InstrumentStatus] = None
    active: Optional[bool] = None
    maintenance_tracked: Optional[bool] = None


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    instrument_type_id: UUID
    vendor_id: Optional[UUID] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None
    location_id: Optional[UUID] = None
    status: str
    active: bool
    maintenance_tracked: bool
    created_at: datetime
    modified_at: datetime
    instrument_type_name: Optional[str] = None
    vendor_name: Optional[str] = None
    location_name: Optional[str] = None


class InstrumentEligibilityResponse(BaseModel):
    instrument_id: UUID
    allowed: bool
    maintenance_tracked: bool
    code: Optional[str] = None
    message: Optional[str] = None


class CroSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    active: bool = True


class CroSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    active: Optional[bool] = None


class CroSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    client_name: Optional[str] = None
