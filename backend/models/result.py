"""Result model — instance of an analyte value on a test (not a named entity)."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Result(Base):
    """
    Structured LIMS result: value for one analyte on one test.

    Does not use BaseModel: results have no global unique name (Decision #17).
    Identity for promote conflicts: (test_id, analyte_id, replicate) + lims_run_id ownership.
    """
    __tablename__ = 'results'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default='true', default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    test_id = Column(PostgresUUID(as_uuid=True), ForeignKey('tests.id'), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), nullable=False)
    raw_result = Column(String(255), nullable=True)
    reported_result = Column(String(255), nullable=True)
    qualifiers = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    calculated_result = Column(String(255), nullable=True)
    entry_date = Column(DateTime, server_default=func.now(), nullable=False)
    entered_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')

    # Promote-on-publish lineage (null for manual entry)
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_runs.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    # Distinguishes multi-row same analyte (default 1; order-based if import has no replicate)
    replicate = Column(Integer, nullable=False, server_default='1', default=1)

    # Relationships
    test = relationship("Test", back_populates="results")
    analyte = relationship("Analyte", back_populates="results")
    lims_run = relationship("LimsRun", foreign_keys=[lims_run_id])
    entered_by_user = relationship("User", foreign_keys=[entered_by], back_populates="entered_results")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_results")
    modifier = relationship("User", foreign_keys=[modified_by], back_populates="modified_results")
    experiment_sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="result",
        foreign_keys="ExperimentSampleExecution.result_id",
    )
