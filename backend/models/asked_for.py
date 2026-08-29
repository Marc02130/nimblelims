"""Asked-for request lake and analysis method-param catalog (P1).

Not BaseModel: requests have no global unique name.
"""
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


PARAM_DATA_TYPES = ("number", "int", "text", "bool")
ASKED_FOR_STATUSES = ("requested", "routed", "cancelled")


class AnalysisParamDef(Base):
    """Catalog of method params that belong to an analysis (assay)."""

    __tablename__ = "analysis_param_defs"
    __table_args__ = (
        UniqueConstraint("analysis_id", "key", name="uq_analysis_param_defs_key"),
        CheckConstraint(
            "data_type IN ('number', 'int', 'text', 'bool')",
            name="analysis_param_defs_data_type_chk",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    key = Column(Text, nullable=False)
    data_type = Column(Text, nullable=False)
    unit = Column(Text, nullable=True)
    required = Column(Boolean, nullable=False, server_default="false", default=False)
    source_list_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lists.id"),
        nullable=True,
    )
    allowed_values = Column(JSONB, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0", default=0)
    active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    analysis = relationship("Analysis", foreign_keys=[analysis_id])


class AskedFor(Base):
    """Requested analysis on a sample. Does not create Tests or work orders."""

    __tablename__ = "asked_for"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'routed', 'cancelled')",
            name="asked_for_status_chk",
        ),
        CheckConstraint("tat_days > 0", name="asked_for_tat_days_chk"),
        Index("ix_asked_for_sample_id", "sample_id"),
        Index("ix_asked_for_status", "status"),
        Index(
            "uq_asked_for_open",
            "sample_id",
            "analysis_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("samples.id"), nullable=False
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    tat_days = Column(Integer, nullable=False)
    params = Column(JSONB, nullable=False, server_default="{}", default=dict)
    status = Column(Text, nullable=False)
    routed_work_order_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("work_orders.id", use_alter=True, name="fk_asked_for_routed_work_order_id"),
        nullable=True,
    )
    active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    sample = relationship("Sample", foreign_keys=[sample_id])
    analysis = relationship("Analysis", foreign_keys=[analysis_id])
