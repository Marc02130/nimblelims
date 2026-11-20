"""Result model — instance of an analyte value on a test (not a named entity)."""
import uuid
from sqlalchemy import Column, Date, String, DateTime, ForeignKey, Boolean, Integer, Text, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Result(Base):
    """
    Structured LIMS result: value for one analyte on one test.

    Does not use BaseModel: results have no global unique name (Decision #17).
    Identity: (test_id, analyte_id, replicate). The run a result came from is
    its Test's ``lims_run_id``; ``results`` has no run column (CALC-REQ-49).
    """
    __tablename__ = 'results'
    __table_args__ = (
        CheckConstraint(
            "knocked_out OR (knocked_out_by IS NULL AND knocked_out_at IS NULL)",
            name="ck_results_knockout_fields",
        ),
        CheckConstraint(
            "NOT knocked_out OR knocked_out_at IS NOT NULL",
            name="ck_results_knockout_time",
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default='true', default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    test_id = Column(PostgresUUID(as_uuid=True), ForeignKey('tests.id'), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), nullable=False)
    raw_result = Column(String(255), nullable=True)
    reported_result = Column(String(255), nullable=True)
    qualifiers = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    calculated_result = Column(String(255), nullable=True)
    entry_date = Column(Date, server_default=text("current_lab_day()"), nullable=False)
    entered_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')

    # Distinguishes multi-row same analyte (default 1; order-based if import has no replicate)
    replicate = Column(Integer, nullable=False, server_default='1', default=1)
    # Copied from the result entry on publish (CALC-REQ-49, CALC-REQ-28).
    display_order = Column(Integer, nullable=True)
    raw_units = Column(String(64), nullable=True)
    final_units_id = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'), nullable=True)
    knocked_out = Column(Boolean, nullable=False, server_default='false', default=False)
    knocked_out_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='RESTRICT'), nullable=True)
    knocked_out_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    test = relationship("Test", back_populates="results")
    analyte = relationship("Analyte", back_populates="results")
    entered_by_user = relationship("User", foreign_keys=[entered_by], back_populates="entered_results")
    knocked_out_by_user = relationship("User", foreign_keys=[knocked_out_by])
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_results")
    modifier = relationship("User", foreign_keys=[modified_by], back_populates="modified_results")
    experiment_sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="result",
        foreign_keys="ExperimentSampleExecution.result_id",
    )

    @property
    def lims_run_id(self):
        """The LIMS run this result came from: its Test's run. Read-only."""
        return self.test.lims_run_id if self.test is not None else None
