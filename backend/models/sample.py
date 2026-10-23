import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, BaseModel


class Sample(BaseModel):
    __tablename__ = "samples"

    # Sample-specific fields
    due_date = Column(Date)
    received_date = Column(Date)
    report_date = Column(Date)
    date_sampled = Column(
        Date, nullable=True
    )  # When sample was collected (for expiration calc)
    sample_type = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )
    status = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=False
    )
    matrix = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=True
    )  # nullable: matrix being dropped from intake; sample_type is SoT at receive
    temperature = Column(Numeric(10, 2))
    parent_sample_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("samples.id"), nullable=True
    )
    project_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    qc_type = Column(
        PostgresUUID(as_uuid=True), ForeignKey("list_entries.id"), nullable=True
    )
    client_sample_id = Column(String(255), nullable=True, unique=True)
    # Receipt facts from the manifest (SOP sample receipt). Collection day is
    # date_sampled. These stay on the sample; nothing is deleted.
    volume_ul = Column(Numeric(12, 2), nullable=True)
    receipt_condition = Column(String(255), nullable=True)
    thaw_count = Column(Integer, nullable=True)
    custom_attributes = Column(
        JSONB, nullable=True, server_default="{}"
    )  # legacy - phased out for modeled fields via hard cutover

    # Path 1: direct column for top-level list-backed field (specimen_biotype)
    # Defined via FieldDefinition (data_type='list', source_list=...), added via migration.
    # This replaces any previous hack in custom_attributes['specimen_biotype'].
    specimen_biotype_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        nullable=True,
        index=True,
    )
    specimen_biotype = relationship("ListEntry", foreign_keys=[specimen_biotype_id])

    # Example simple scalar (text) - also via FieldDefinition + direct column
    # lot_number = Column(Text)

    # Example simple scalar (numeric)
    # dilution_factor = Column(Numeric)

    # === Deprecation plan for custom_attributes (hard cutover) ===
    # Phase 1: Keep the column for backward compat during transition.
    # Phase 2: For any field promoted to FieldDefinition (like specimen_biotype_id above),
    #          add the real column (Path 1), migrate data from JSONB, update all code/Entries/Processes.
    # Phase 3: Hard cutover - stop reading/writing the key in custom_attributes for modeled fields.
    #          Provide a one-time backfill script.
    # Phase 4: After validation, custom_attributes becomes legacy-only (unstructured notes only)
    #          or can be dropped in a later migration.
    # Use FieldDefinition to drive new fields; old JSONB access should be flagged deprecated.
    # See local .docs/internal/design/migration-strategy-schema-evolution.md (not committed) for detailed backfill/validation/rollback.

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
    parent_sample = relationship(
        "Sample", primaryjoin="Sample.parent_sample_id == Sample.id"
    )
    child_samples = relationship(
        "Sample", primaryjoin="Sample.id == Sample.parent_sample_id"
    )
    tests = relationship("Test", back_populates="sample")
    contents = relationship("Contents", back_populates="sample")
    experiment_sample_executions = relationship(
        "ExperimentSampleExecution",
        back_populates="sample",
        foreign_keys="ExperimentSampleExecution.sample_id",
    )
    creator = relationship(
        "User", foreign_keys="Sample.created_by", back_populates="created_samples"
    )
    modifier = relationship(
        "User", foreign_keys="Sample.modified_by", back_populates="modified_samples"
    )

    __table_args__ = (
        CheckConstraint(
            "volume_ul IS NULL OR volume_ul >= 0",
            name="ck_samples_volume_ul_nonneg",
        ),
        CheckConstraint(
            "volume_ul IS NULL OR volume_ul <= 10000000",
            name="ck_samples_volume_ul_max",
        ),
        CheckConstraint(
            "thaw_count IS NULL OR thaw_count >= 0",
            name="ck_samples_thaw_count_nonneg",
        ),
    )


class SampleTypeTransition(Base):
    """Client catalog edge for an allowed derivative or pool destination type (aliquots keep the type)."""

    __tablename__ = "sample_type_transitions"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('aliquot', 'derivative', 'pool')",
            name="ck_sample_type_transitions_operation",
        ),
        UniqueConstraint(
            "client_id",
            "source_sample_type",
            "operation",
            "allowed_dest_sample_type",
            name="uq_sample_type_transitions_client_source_operation_dest",
        ),
    )

    id = Column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )
    source_sample_type = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        nullable=False,
        index=True,
    )
    operation = Column(String(16), nullable=False, index=True)
    allowed_dest_sample_type = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        nullable=False,
        index=True,
    )
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    client = relationship("Client", foreign_keys=[client_id])
    source_type = relationship(
        "ListEntry",
        foreign_keys=[source_sample_type],
    )
    allowed_dest_type = relationship(
        "ListEntry",
        foreign_keys=[allowed_dest_sample_type],
    )
