"""
Experiment Management (Chunk 1): experiments, templates, details, sample executions.

EAV compatibility via custom_attributes JSONB on all entity tables.
Rich junction experiment_sample_executions links experiments to samples with
role_in_experiment, processing_conditions JSONB, replicate_number, and optional
test_id/result_id for direct linking.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, BaseModel


class ExperimentTemplate(BaseModel):
    """Reusable experiment definition; template_definition JSONB holds structure/params."""
    __tablename__ = 'experiment_templates'

    template_definition = Column(JSONB, nullable=False, server_default='{}')
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    # Controls which state machine applies to ExperimentRuns created from this template.
    # 'standard': draft → running → complete → published | failed | canceled
    # 'cro':      draft → ordered → running → results_received → complete → published | failed | canceled
    lifecycle_type = Column(String(32), nullable=False, server_default='standard', default='standard')

    experiments = relationship("Experiment", back_populates="experiment_template")


class Experiment(BaseModel):
    """A run of an experiment (from template or ad-hoc)."""
    __tablename__ = 'experiments'

    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id'),
        nullable=True,
    )
    status_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id'),
        nullable=True,
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')

    experiment_template = relationship(
        "ExperimentTemplate",
        back_populates="experiments",
    )
    status = relationship("ListEntry", foreign_keys=[status_id])
    details = relationship(
        "ExperimentDetail",
        back_populates="experiment",
        order_by="ExperimentDetail.sort_order",
        cascade="all, delete-orphan",
    )
    sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class ExperimentDetail(Base):
    """
    Key-value / structured details for an experiment (protocol, conditions, notes).
    Uses Base (no unique name); one or more rows per experiment.
    """
    __tablename__ = 'experiment_details'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=False,
    )
    detail_type = Column(String(255), nullable=False, index=True)  # e.g. 'protocol', 'conditions'
    content = Column(JSONB, nullable=False, server_default='{}')
    sort_order = Column(Integer, nullable=False, server_default='0')
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment = relationship("Experiment", back_populates="details")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class ExperimentSampleExecution(Base):
    """
    Rich junction: experiment <-> sample (or aliquot) with role, processing_conditions,
    replicate_number. Optional test_id/result_id for direct linking to tests/results.
    """
    __tablename__ = 'experiment_sample_executions'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=False,
    )
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('samples.id'),
        nullable=False,
    )
    role_in_experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id'),
        nullable=True,
    )
    processing_conditions = Column(JSONB, nullable=True, server_default='{}')
    replicate_number = Column(Integer, nullable=False, server_default='1')
    test_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('tests.id'),
        nullable=True,
    )
    result_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('results.id'),
        nullable=True,
    )
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'experiment_id',
            'sample_id',
            'replicate_number',
            name='uq_experiment_sample_execution_experiment_sample_replicate',
        ),
    )

    experiment = relationship("Experiment", back_populates="sample_executions")
    sample = relationship("Sample", back_populates="experiment_sample_executions")
    role_in_experiment = relationship("ListEntry", foreign_keys=[role_in_experiment_id])
    test = relationship("Test", back_populates="experiment_sample_executions")
    result = relationship("Result", back_populates="experiment_sample_executions")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])
