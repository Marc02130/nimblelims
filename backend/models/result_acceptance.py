"""Reviewer pick of which run's value is the accepted result.

Both values stay. A later pick sets the previous row inactive. Nothing is deleted.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ResultAcceptance(Base):
    """One recorded choice for a sample, analyte, and replicate.

    ``active`` is true for the current choice only. Earlier choices stay.
    """

    __tablename__ = "result_acceptances"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    analyte_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analytes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    replicate = Column(Integer, nullable=False, server_default="1", default=1)
    accepted_lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lims_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    accepted_value = Column(Text, nullable=False)
    other_lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lims_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    other_value = Column(Text, nullable=True)
    previous_lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lims_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    previous_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    sample = relationship("Sample")
    analyte = relationship("Analyte")
    accepted_run = relationship("LimsRun", foreign_keys=[accepted_lims_run_id])

    __table_args__ = (
        Index(
            "uq_result_acceptances_live",
            "sample_id",
            "analyte_id",
            "replicate",
            unique=True,
            postgresql_where=text("active = true"),
        ),
    )
