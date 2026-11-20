from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Test(BaseModel):
    __tablename__ = 'tests'
    
    # Test-specific fields
    sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=False)
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    review_date = Column(Date)
    test_date = Column(Date)
    technician_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    asked_for_params = Column(JSONB, nullable=True)
    # The LIMS run this Test belongs to (CALC-REQ-49). A result is refused on a
    # Test with no run. Set once; a new generation is a new Test (CALC-REQ-55).
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_runs.id', ondelete='RESTRICT'),
        nullable=True,
        index=True,
    )
    
    # Relationships
    sample = relationship("Sample", back_populates="tests")
    analysis = relationship("Analysis", back_populates="tests")
    technician = relationship("User", foreign_keys=[technician_id])
    lims_run = relationship("LimsRun", foreign_keys=[lims_run_id])
    results = relationship("Result", back_populates="test")
    experiment_sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="test",
        foreign_keys="ExperimentSampleExecution.test_id",
    )
