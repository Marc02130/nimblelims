"""Instruments, CRO sources, maintenance, downtime, and instrument use.

Instrument kinds live on the ``instrument_types`` list (list_entries).
The old ``instrument_types`` table was renamed ``instrument_types_legacy``
and is unused. Nothing is deleted: rows retire with ``active`` and ``status``.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base, BaseModel

INSTRUMENT_TYPES_LIST_ID = "a1000001-0001-4001-8001-000000000001"
MAINTENANCE_TYPES_LIST_ID = "a1000001-0001-4001-8001-000000000002"
DOWNTIME_REASONS_LIST_ID = "a1000001-0001-4001-8001-000000000003"

INSTRUMENT_STATUSES = ("in_service", "out_of_service", "retired")


class _InstrumentTypesInstantAnchor(Base):
    """Unused leftover name so 0102's frozen instant list still matches metadata.

    The live table was renamed to ``instrument_types_legacy``. Nothing reads
    or writes this mapping.
    """

    __tablename__ = "instrument_types"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Instrument(BaseModel):
    """Named instrument instance. Type is a list entry; vendor/model live here."""

    __tablename__ = "instruments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_service', 'out_of_service', 'retired')",
            name="ck_instruments_status",
        ),
        Index(
            "uq_instruments_vendor_model_serial",
            "vendor_id",
            "model",
            "serial_number",
            unique=True,
            postgresql_where=text("serial_number IS NOT NULL"),
        ),
    )

    instrument_type_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        nullable=False,
    )
    vendor_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("vendors.id"),
        nullable=True,
    )
    model = Column(String(255), nullable=True)
    serial_number = Column(String(255), nullable=True)
    asset_tag = Column(String(255), nullable=True)
    location_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("locations.id"),
        nullable=True,
    )
    status = Column(String(32), nullable=False, default="in_service")
    maintenance_tracked = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    instrument_type = relationship("ListEntry", foreign_keys=[instrument_type_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    location = relationship("Location", foreign_keys=[location_id])


class InstrumentTypeDefault(Base):
    """Per-type default for ``instruments.maintenance_tracked``.

    Types are ``list_entries`` on ``instrument_types``. A side table keeps
    the default off ``list_entries`` so other lists are untouched, and so
    the configuring agent never adds a column on lists.
    """

    __tablename__ = "instrument_type_defaults"

    instrument_type_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        primary_key=True,
    )
    maintenance_tracked = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    instrument_type = relationship("ListEntry", foreign_keys=[instrument_type_id])


class InstrumentMaintenanceAudit(Base):
    """Previous ``maintenance_tracked`` kept when the flag changes."""

    __tablename__ = "instrument_maintenance_audits"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False, index=True
    )
    previous_value = Column(Boolean, nullable=False)
    new_value = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )


class CroSource(BaseModel):
    """External/CRO export-source catalog (file shape lineage)."""

    __tablename__ = "cro_sources"

    client_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=True,
    )

    client = relationship("Client", foreign_keys=[client_id])


class InstrumentMaintenanceSchedule(Base):
    __tablename__ = "instrument_maintenance_schedules"
    __table_args__ = (
        CheckConstraint("interval_days > 0", name="ck_instrument_schedules_interval"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False, index=True
    )
    kind_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )
    interval_days = Column(Integer, nullable=False)
    last_done = Column(Date, nullable=True)
    next_due = Column(Date, nullable=True)
    service_vendor_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
    )
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    instrument = relationship("Instrument", foreign_keys=[instrument_id])
    kind = relationship("ListEntry", foreign_keys=[kind_id])
    service_vendor = relationship("Vendor", foreign_keys=[service_vendor_id])


class InstrumentMaintenanceEvent(Base):
    __tablename__ = "instrument_maintenance_events"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(performed_by_user_id, performed_by_vendor_id) >= 1",
            name="ck_instrument_events_performer",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("instrument_maintenance_schedules.id"),
        nullable=True,
        index=True,
    )
    instrument_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False, index=True
    )
    performed_on = Column(Date, nullable=False)
    performed_by_user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    performed_by_vendor_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
    )
    passed = Column(Boolean, nullable=False)
    certificate_url = Column(String(1024), nullable=True)
    note = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    schedule = relationship("InstrumentMaintenanceSchedule", foreign_keys=[schedule_id])
    instrument = relationship("Instrument", foreign_keys=[instrument_id])
    performed_by_user = relationship("User", foreign_keys=[performed_by_user_id])
    performed_by_vendor = relationship("Vendor", foreign_keys=[performed_by_vendor_id])


class InstrumentDowntime(Base):
    __tablename__ = "instrument_downtime"
    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_instrument_downtime_window",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False, index=True
    )
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    reason_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )
    maintenance_event_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("instrument_maintenance_events.id"),
        nullable=True,
    )
    note = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    instrument = relationship("Instrument", foreign_keys=[instrument_id])
    reason = relationship("ListEntry", foreign_keys=[reason_id])
    maintenance_event = relationship(
        "InstrumentMaintenanceEvent", foreign_keys=[maintenance_event_id]
    )


class InstrumentUse(Base):
    __tablename__ = "instrument_uses"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(lims_run_id, experiment_id) >= 1",
            name="ck_instrument_uses_target",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False, index=True
    )
    lims_run_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("lims_runs.id"), nullable=True, index=True
    )
    experiment_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("experiments.id"), nullable=True, index=True
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=True
    )
    used_on = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    instrument = relationship("Instrument", foreign_keys=[instrument_id])
