"""Pydantic schemas for instrument types, instruments (instances), and CRO sources."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class InstrumentTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    vendor: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    active: bool = True


class InstrumentTypeCreate(InstrumentTypeBase):
    pass


class InstrumentTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    vendor: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    active: Optional[bool] = None


class InstrumentTypeResponse(InstrumentTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    modified_at: datetime


class InstrumentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instrument_type_id: UUID
    serial_number: Optional[str] = Field(None, max_length=255)
    active: bool = True


class InstrumentCreate(InstrumentBase):
    pass


class InstrumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instrument_type_id: Optional[UUID] = None
    serial_number: Optional[str] = Field(None, max_length=255)
    active: Optional[bool] = None


class InstrumentResponse(InstrumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    modified_at: datetime
    instrument_type_name: Optional[str] = None
    instrument_type_vendor: Optional[str] = None
    instrument_type_model: Optional[str] = None


class CroSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    active: bool = True


class CroSourceCreate(CroSourceBase):
    pass


class CroSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    active: Optional[bool] = None


class CroSourceResponse(CroSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    modified_at: datetime
    client_name: Optional[str] = None
