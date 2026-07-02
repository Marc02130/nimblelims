from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Sample(BaseModel):
    __tablename__ = 'samples'
    
    # Sample-specific fields
    due_date = Column(DateTime)
    received_date = Column(DateTime)
    report_date = Column(DateTime)
    date_sampled = Column(DateTime, nullable=True)  # When sample was collected (for expiration calc)
    sample_type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    matrix = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    temperature = Column(Numeric(10, 2))
    parent_sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=True)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    qc_type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    client_sample_id = Column(String(255), nullable=True, unique=True)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')  # legacy - phased out for modeled fields via hard cutover

    # Path 1: direct column for top-level list-backed field (specimen_biotype)
    # Defined via FieldDefinition (data_type='list', source_list=...), added via migration.
    # This replaces any previous hack in custom_attributes['specimen_biotype'].
    specimen_biotype_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id'),
        nullable=True,
        index=True
    )
    specimen_biotype = relationship(
        "ListEntry", foreign_keys=[specimen_biotype_id]
    )

    # Example simple scalar (text) - also via FieldDefinition + direct column
    # lot_number = Column(Text)

    # Example simple scalar (numeric)
    # dilution_factor = Column(Numeric)

    # Deprecation plan for custom_attributes (hard cutover):
    # - During transition: keep the column but stop writing new modeled fields to it.
    # - Backfill script moves values to the new typed columns (see migration-strategy doc).
    # - Post-cutover: custom_attributes becomes read-only for legacy data only.
    # - Eventually drop or leave as-is for truly unstructured per-sample notes.
    # Accessor example (temporary compat):
    # @property
    # def specimen_biotype_legacy(self):
    #     if self.specimen_biotype_id:
    #         return self.specimen_biotype.name
    #     return self.custom_attributes.get('specimen_biotype')
    
    # Relationships
    project = relationship("Project", back_populates="samples")
    parent_sample = relationship("Sample", primaryjoin="Sample.parent_sample_id == Sample.id")
    child_samples = relationship("Sample", primaryjoin="Sample.id == Sample.parent_sample_id")
    tests = relationship("Test", back_populates="sample")
    contents = relationship("Contents", back_populates="sample")
    experiment_sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="sample",
        foreign_keys="ExperimentSampleExecution.sample_id",
    )
    creator = relationship("User", foreign_keys="Sample.created_by", back_populates="created_samples")
    modifier = relationship("User", foreign_keys="Sample.modified_by", back_populates="modified_samples")
