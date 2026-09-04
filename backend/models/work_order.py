"""P2 routing map, work orders, and step accepted sample types."""
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


WORK_ORDER_STATUSES = ("queued", "in_progress", "completed", "cancelled")


class RoutingMap(Base):
    """analysis × sample_type × TAT range → process-definition chain."""

    __tablename__ = "routing_map"
    __table_args__ = (
        CheckConstraint(
            "array_length(process_definition_ids, 1) >= 1",
            name="routing_map_chain_chk",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    asked_for_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_definition_steps.id"),
        nullable=True,
        index=True,
    )
    sample_type_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )
    tat_range = Column(INT4RANGE, nullable=False)
    process_definition_ids = Column(ARRAY(PostgresUUID(as_uuid=True)), nullable=False)
    active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class WorkOrder(Base):
    """Backlog item minted on Route. Snapshot of process-definition chain."""

    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'in_progress', 'completed', 'cancelled')",
            name="work_orders_status_chk",
        ),
        CheckConstraint(
            "array_length(process_definition_ids, 1) >= 1",
            name="work_orders_chain_chk",
        ),
        UniqueConstraint("asked_for_id", name="uq_work_orders_asked_for_id"),
        Index("ix_work_orders_status", "status"),
        Index("ix_work_orders_sample_id", "sample_id"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asked_for_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("asked_for.id"), nullable=False
    )
    sample_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("samples.id"), nullable=False
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    process_definition_ids = Column(ARRAY(PostgresUUID(as_uuid=True)), nullable=False)
    status = Column(Text, nullable=False)
    process_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("eln_processes.id"), nullable=True
    )
    active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    asked_for = relationship("AskedFor", foreign_keys=[asked_for_id])
    sample = relationship("Sample", foreign_keys=[sample_id])
    analysis = relationship("Analysis", foreign_keys=[analysis_id])


class StepAcceptedSampleType(Base):
    """Accepted sample type for one process-definition step (experiment or LimsRun)."""

    __tablename__ = "eln_process_definition_step_accepted_sample_types"
    __table_args__ = (
        UniqueConstraint(
            "step_id", "sample_type_id", name="uq_step_accepted_sample_type"
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_definition_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_type_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )

    step = relationship("ELNProcessDefinitionStep", foreign_keys=[step_id])
