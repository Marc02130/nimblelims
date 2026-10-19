"""Reagent tracking (step 2): vendors, reagents, reagent lots, reagent use.

Vendors, reagents, reagent-vendor sources and lots are a lab-wide catalog like
instruments. A reagent is vendor-agnostic; each vendor that sells it is a
ReagentVendor (catalog number, units, reorder info). A lot can name the
ReagentVendor it was bought from. A reagent
use records which lot was used on a LIMS run or an experiment, and copies the
lot number and expiry onto the use row so the run keeps them even if the lot
row is corrected later.

Locks: nothing is deleted. Rows retire with ``active`` (Set inactive); a lot's
quantity remaining can be set to 0. A use is voided with ``active`` false.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base, BaseModel


class Vendor(BaseModel):
    __tablename__ = "vendors"

    contact = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    website = Column(String(255), nullable=True)

    sources = relationship("ReagentVendor", back_populates="vendor")


class Reagent(BaseModel):
    """Vendor-agnostic: what the reagent is. Where it is bought is a ReagentVendor."""

    __tablename__ = "reagents"

    storage_condition = Column(String(32), nullable=True)  # -80C | -20C | 4C | RT
    unit = Column(String(64), nullable=True)
    hazard_class = Column(String(255), nullable=True)
    sds_url = Column(String(1024), nullable=True)
    stability_after_opening_days = Column(Numeric, nullable=True)

    sources = relationship("ReagentVendor", back_populates="reagent")
    lots = relationship("ReagentLot", back_populates="reagent")


class ReagentVendor(Base):
    """A reagent as sold by one vendor: catalog number and reordering info."""

    __tablename__ = "reagent_vendors"
    __table_args__ = (UniqueConstraint("reagent_id", "vendor_id", "catalog_number", name="uq_reagent_vendors"),)

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reagent_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False, index=True)
    vendor_id = Column(PostgresUUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True)
    catalog_number = Column(String(255), nullable=True)
    unit = Column(String(64), nullable=True)
    unit_of_sale = Column(String(255), nullable=True)
    quantity_per_unit_of_sale = Column(Numeric, nullable=True)
    reorder_point = Column(Numeric, nullable=True)
    reorder_quantity = Column(Numeric, nullable=True)
    lead_time_days = Column(Numeric, nullable=True)
    price_per_unit = Column(Numeric, nullable=True)
    is_preferred = Column(Boolean, nullable=False, default=False, server_default="false")
    notes = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    reagent = relationship("Reagent", back_populates="sources")
    vendor = relationship("Vendor", back_populates="sources")


class ReagentLot(Base):
    __tablename__ = "reagent_lots"
    __table_args__ = (
        UniqueConstraint("reagent_id", "lot_number", name="uq_reagent_lots_reagent_lot"),
        CheckConstraint("quantity_remaining IS NULL OR quantity_remaining >= 0", name="ck_reagent_lots_remaining"),
        CheckConstraint("qc_status IN ('pending', 'released', 'rejected')", name="ck_reagent_lots_qc_status"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reagent_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reagents.id"), nullable=False, index=True)
    reagent_vendor_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reagent_vendors.id"), nullable=True, index=True)
    lot_number = Column(String(255), nullable=False)
    expiration_date = Column(Date, nullable=True)
    purchased_date = Column(Date, nullable=True)
    quantity_received = Column(Numeric, nullable=True)
    quantity_remaining = Column(Numeric, nullable=True)
    unit = Column(String(64), nullable=True)
    received_date = Column(Date, nullable=True)
    received_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    opened_date = Column(Date, nullable=True)
    storage_location = Column(String(255), nullable=True)
    qc_status = Column(String(16), nullable=False, default="pending", server_default="pending")
    # Lab-controlled gate, separate from active: a lot is usable only when
    # released. Defaults true; labs that hold lots for QC set it false on receipt.
    released = Column(Boolean, nullable=False, default=True, server_default="true")
    coa_url = Column(String(1024), nullable=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    reagent = relationship("Reagent", back_populates="lots")
    source = relationship("ReagentVendor")


class ReagentUse(Base):
    __tablename__ = "reagent_uses"
    __table_args__ = (
        CheckConstraint("num_nonnulls(lims_run_id, experiment_id) >= 1", name="ck_reagent_uses_target"),
        CheckConstraint("quantity_used >= 0", name="ck_reagent_uses_quantity"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reagent_lot_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reagent_lots.id"), nullable=False, index=True)
    lims_run_id = Column(PostgresUUID(as_uuid=True), ForeignKey("lims_runs.id"), nullable=True, index=True)
    experiment_id = Column(PostgresUUID(as_uuid=True), ForeignKey("experiments.id"), nullable=True, index=True)
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=True)
    # Copied from the lot at record time: the run keeps what was on the label.
    lot_number = Column(String(255), nullable=False)
    expiration_date = Column(Date, nullable=True)
    used_on = Column(Date, nullable=False)
    quantity_used = Column(Numeric, nullable=False)
    unit = Column(String(64), nullable=True)
    note = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    lot = relationship("ReagentLot")
