"""Maintenance, downtime, and instrument-use schemas."""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, ConfigDict
from app.schemas._instants import APIModel as BaseModel


class MaintenanceScheduleCreate(BaseModel):
    instrument_id: UUID
    kind_id: UUID
    interval_days: int = Field(..., gt=0)
    service_vendor_id: Optional[UUID] = None
    active: bool = True


class MaintenanceScheduleUpdate(BaseModel):
    kind_id: Optional[UUID] = None
    interval_days: Optional[int] = Field(None, gt=0)
    service_vendor_id: Optional[UUID] = None
    active: Optional[bool] = None


class MaintenanceScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instrument_id: UUID
    kind_id: UUID
    interval_days: int
    last_done: Optional[date] = None
    next_due: Optional[date] = None
    service_vendor_id: Optional[UUID] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    kind_name: Optional[str] = None
    instrument_name: Optional[str] = None
    service_vendor_name: Optional[str] = None


class MaintenanceEventCreate(BaseModel):
    instrument_id: UUID
    schedule_id: Optional[UUID] = None
    performed_on: date
    performed_by_user_id: Optional[UUID] = None
    performed_by_vendor_id: Optional[UUID] = None
    passed: bool
    certificate_url: Optional[str] = Field(None, max_length=1024)
    note: Optional[str] = None


class MaintenanceEventUpdate(BaseModel):
    active: Optional[bool] = None
    note: Optional[str] = None
    certificate_url: Optional[str] = Field(None, max_length=1024)


class MaintenanceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instrument_id: UUID
    schedule_id: Optional[UUID] = None
    performed_on: date
    performed_by_user_id: Optional[UUID] = None
    performed_by_vendor_id: Optional[UUID] = None
    passed: bool
    certificate_url: Optional[str] = None
    note: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime


class DowntimeCreate(BaseModel):
    instrument_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    reason_id: UUID
    maintenance_event_id: Optional[UUID] = None
    note: Optional[str] = None


class DowntimeUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    reason_id: Optional[UUID] = None
    maintenance_event_id: Optional[UUID] = None
    note: Optional[str] = None
    active: Optional[bool] = None


class DowntimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instrument_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    reason_id: UUID
    maintenance_event_id: Optional[UUID] = None
    note: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    reason_name: Optional[str] = None
    instrument_name: Optional[str] = None


class InstrumentUseCreate(BaseModel):
    instrument_id: UUID
    lims_run_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    used_on: Optional[date] = None
    note: Optional[str] = None


class InstrumentUseUpdate(BaseModel):
    active: Optional[bool] = None
    note: Optional[str] = None


class InstrumentUseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instrument_id: UUID
    lims_run_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    used_on: date
    note: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    instrument_name: Optional[str] = None


class ExperimentInstrumentAdd(BaseModel):
    instrument_id: UUID


class ExperimentInstrumentStatus(BaseModel):
    instrument_id: UUID
    active: bool


class ExperimentInstrumentListResponse(BaseModel):
    experiment_id: UUID
    entry_id: UUID
    allowed_instrument_ids: List[str]
    removed_instrument_ids: List[str]
