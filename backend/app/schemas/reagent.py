"""Pydantic schemas for reagent tracking: vendors, reagents, lots, uses."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field
from app.schemas._instants import APIModel as BaseModel

StorageCondition = Literal["-80C", "-20C", "4C", "RT"]
QcStatus = Literal["pending", "released", "rejected"]


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    contact: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    website: Optional[str] = Field(None, max_length=255)
    active: bool = True


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    contact: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    website: Optional[str] = Field(None, max_length=255)
    active: Optional[bool] = None


class VendorResponse(VendorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None


class ReagentCreate(BaseModel):
    """Vendor-agnostic. Vendors and catalog numbers go on /v1/reagent-vendors."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    storage_condition: Optional[StorageCondition] = None
    unit: Optional[str] = Field(None, max_length=64)
    hazard_class: Optional[str] = Field(None, max_length=255)
    sds_url: Optional[str] = Field(None, max_length=1024)
    stability_after_opening_days: Optional[Decimal] = Field(None, ge=0)
    active: bool = True


class ReagentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    storage_condition: Optional[StorageCondition] = None
    unit: Optional[str] = Field(None, max_length=64)
    hazard_class: Optional[str] = Field(None, max_length=255)
    sds_url: Optional[str] = Field(None, max_length=1024)
    stability_after_opening_days: Optional[Decimal] = Field(None, ge=0)
    active: Optional[bool] = None


class ReagentResponse(ReagentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_names: list[str] = []
    quantity_on_hand: Optional[Decimal] = None
    below_reorder_point: bool = False
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None


class ReagentVendorCreate(BaseModel):
    reagent_id: UUID
    vendor_id: UUID
    catalog_number: Optional[str] = Field(None, max_length=255)
    unit: Optional[str] = Field(None, max_length=64)
    unit_of_sale: Optional[str] = Field(None, max_length=255)
    quantity_per_unit_of_sale: Optional[Decimal] = Field(None, ge=0)
    reorder_point: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    lead_time_days: Optional[Decimal] = Field(None, ge=0)
    price_per_unit: Optional[Decimal] = Field(None, ge=0)
    is_preferred: bool = False
    notes: Optional[str] = None
    active: bool = True


class ReagentVendorUpdate(BaseModel):
    """Reagent and vendor stay; everything else can change."""

    catalog_number: Optional[str] = Field(None, max_length=255)
    unit: Optional[str] = Field(None, max_length=64)
    unit_of_sale: Optional[str] = Field(None, max_length=255)
    quantity_per_unit_of_sale: Optional[Decimal] = Field(None, ge=0)
    reorder_point: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    lead_time_days: Optional[Decimal] = Field(None, ge=0)
    price_per_unit: Optional[Decimal] = Field(None, ge=0)
    is_preferred: Optional[bool] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class ReagentVendorResponse(ReagentVendorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reagent_name: Optional[str] = None
    vendor_name: Optional[str] = None
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None


class ReagentLotCreate(BaseModel):
    reagent_id: Optional[UUID] = None
    reagent_vendor_id: Optional[UUID] = None
    lot_number: str = Field(..., min_length=1, max_length=255)
    expiration_date: Optional[date] = None
    purchased_date: Optional[date] = None
    quantity_received: Optional[Decimal] = Field(None, ge=0)
    quantity_remaining: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=64)
    received_date: Optional[date] = None
    received_by: Optional[UUID] = None
    opened_date: Optional[date] = None
    storage_location: Optional[str] = Field(None, max_length=255)
    coa_url: Optional[str] = Field(None, max_length=1024)
    qc_status: QcStatus = "pending"
    released: bool = True
    description: Optional[str] = None
    active: bool = True


class ReagentLotUpdate(BaseModel):
    """No reagent change. Retire with active false; use it up with quantity_remaining 0."""

    lot_number: Optional[str] = Field(None, min_length=1, max_length=255)
    reagent_vendor_id: Optional[UUID] = None
    expiration_date: Optional[date] = None
    purchased_date: Optional[date] = None
    quantity_received: Optional[Decimal] = Field(None, ge=0)
    quantity_remaining: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=64)
    received_date: Optional[date] = None
    received_by: Optional[UUID] = None
    opened_date: Optional[date] = None
    storage_location: Optional[str] = Field(None, max_length=255)
    coa_url: Optional[str] = Field(None, max_length=1024)
    qc_status: Optional[QcStatus] = None
    released: Optional[bool] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ReagentLotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reagent_id: UUID
    reagent_name: Optional[str] = None
    reagent_vendor_id: Optional[UUID] = None
    vendor_name: Optional[str] = None
    catalog_number: Optional[str] = None
    lot_number: str
    expiration_date: Optional[date] = None
    purchased_date: Optional[date] = None
    quantity_received: Optional[Decimal] = None
    quantity_remaining: Optional[Decimal] = None
    unit: Optional[str] = None
    received_date: Optional[date] = None
    received_by: Optional[UUID] = None
    opened_date: Optional[date] = None
    storage_location: Optional[str] = None
    qc_status: str = "pending"
    released: bool = True
    usable: bool = True
    coa_url: Optional[str] = None
    effective_expiration_date: Optional[date] = None
    description: Optional[str] = None
    active: bool
    expired: bool = False
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None
    created_at: datetime
    modified_at: datetime


class ExperimentReagentAdd(BaseModel):
    """Add one active catalog reagent to an experiment's saved reagent list."""

    reagent_id: UUID


class ExperimentReagentListResponse(BaseModel):
    """The experiment's reagent entry after an add or a removal. The active list is what reloads."""

    experiment_id: UUID
    entry_id: UUID
    allowed_reagent_ids: list[str]
    removed_reagent_ids: list[str] = Field(default_factory=list)


class ExperimentReagentStatus(BaseModel):
    """Turn a saved reagent off the active list. Add it again to restore it."""

    reagent_id: UUID
    active: bool


class ReagentUseCreate(BaseModel):
    """Select a lot, then the quantity used. The lot's quantity remaining goes down."""

    reagent_lot_id: UUID
    quantity_used: Decimal
    lims_run_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    used_on: Optional[date] = None
    unit: Optional[str] = Field(None, max_length=64)
    note: Optional[str] = None


class ReagentUseUpdate(BaseModel):
    """Only a void (active false) or a note. Lot, run and quantity stay as recorded."""

    active: Optional[bool] = None
    note: Optional[str] = None


class ReagentUseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reagent_lot_id: UUID
    reagent_id: Optional[UUID] = None
    reagent_name: Optional[str] = None
    lims_run_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    lot_number: str
    expiration_date: Optional[date] = None
    used_on: date
    quantity_used: Decimal
    unit: Optional[str] = None
    note: Optional[str] = None
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: Optional[datetime] = None
    modified_by: Optional[UUID] = None
