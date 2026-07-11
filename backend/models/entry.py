"""
Entry and related models for data capture inside Experiments and Processes.

This is part of the new structured approach replacing loose ExperimentDetail + JSONB.

An Entry represents a "component" or "block" inside an Experiment (or a step in a Process).

Types of Entries (entry_type):
- 'predefined_action'     : OOB actions like aliquoting, pooling, index assignment, flowcell loading, QC review (pass/fail)
- 'sample_data'           : Per-sample data table (columns defined in template via FieldDefinitions)
- 'experiment_detail'     : Experiment-level data / notes (columns defined in template)
- 'display_table'         : For displaying structured table data

Custom data entries (sample_data, experiment_detail) use FieldDefinitions to define their columns.
Values are stored in EntryFieldValue (typed columns, not generic JSONB for modeled data).

Predefined entries have built-in behavior and may still reference FieldDefinitions for any configurable parameters.
"""

import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Text, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, BaseModel


class Entry(BaseModel):
    """
    A data capture / action component inside an Experiment.

    Entries are typically defined in an ExperimentTemplate and instantiated
    for a specific Experiment (or Process step).

    For custom data entries, the actual columns are described by FieldDefinitions
    associated with this Entry (via EntryFieldDefinition junction or direct association).
    """

    __tablename__ = 'entries'

    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=False,
        index=True
    )

    # Links the Entry to a specific step inside a Process.
    # Per design: "An Entry can be linked to a process step via process_step_id."
    # NOTE: uses 'eln_process_steps' to avoid name collision with existing 'process_steps' (LIMS ExperimentProcess steps)
    process_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('eln_process_steps.id'),
        nullable=True,
        index=True
    )

    entry_type = Column(String(64), nullable=False, index=True)  # see class docstring
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # For predefined entries: reference to a built-in entry definition
    # (could be a code constant or a registry)
    predefined_entry_key = Column(String(128), nullable=True, index=True)

    # Sort order within the Experiment / Process step
    sort_order = Column(Integer, nullable=False, default=0)

    # Configuration specific to this entry instance (for predefined entries)
    # e.g. which predefined actions are enabled, parameters, etc.
    # For custom entries this may be minimal.
    config = Column(JSONB, nullable=True, server_default='{}')

    # Whether this entry is active in this particular experiment run
    active = Column(Boolean, nullable=False, server_default='true')

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))

    # Relationships
    experiment = relationship("Experiment", back_populates="entries")
    process_step = relationship("ELNProcessStep", back_populates="entries")

    # For custom entries: the FieldDefinitions that define the columns of this entry
    field_definitions = relationship(
        "FieldDefinition",
        secondary="entry_field_definitions",  # junction table
        back_populates="entries"
    )

    # Link rows (for accessing extra columns like sort_order, visible on the association)
    field_definition_links = relationship(
        "EntryFieldDefinition",
        back_populates="entry",
        cascade="all, delete-orphan",
        overlaps="field_definitions,entries"
    )

    # Values for the fields (for custom data entries)
    values = relationship(
        "EntryFieldValue",
        back_populates="entry",
        cascade="all, delete-orphan"
    )


# Junction table to associate FieldDefinitions (columns) with a specific Entry.
# This is what allows a template to define "these are the columns for this
# sample data entry in this experiment".
class EntryFieldDefinition(Base):
    __tablename__ = 'entry_field_definitions'

    entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('entries.id'),
        primary_key=True
    )
    field_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('field_definitions.id'),
        primary_key=True
    )

    # Column ordering within the entry's table / form
    sort_order = Column(Integer, default=0)

    # Whether this column is shown in the UI for this entry
    visible = Column(Boolean, default=True)

    # Note: We avoid conflicting back_populates here because Entry.field_definitions
    # is a many-to-many to FieldDefinition (via secondary). Use a separate collection
    # for the link rows if you need to access sort_order/visible metadata.
    entry = relationship("Entry", back_populates="field_definition_links", overlaps="entries,field_definitions")
    field_definition = relationship("FieldDefinition", overlaps="entries,field_definitions")


# Extend the previous EntryFieldValue with better relationship
class EntryFieldValue(Base):
    """
    Value for one FieldDefinition inside one Entry.

    For sample data entries:
        - There will typically be one row per sample per field in the entry.
        - Link via sample_id or via the ExperimentSampleExecution.

    This replaces putting dynamic column data inside JSONB.
    """

    __tablename__ = 'entry_field_values'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('entries.id'),
        nullable=False,
        index=True
    )

    field_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('field_definitions.id'),
        nullable=False,
        index=True
    )

    # For sample-specific data entries: which sample this value belongs to
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('samples.id'),
        nullable=True,
        index=True
    )

    # Typed storage (only the relevant one populated)
    value_text = Column(Text)
    value_number = Column(Numeric(precision=20, scale=10))
    value_list_entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id')
    )
    value_date = Column(DateTime(timezone=True))
    value_boolean = Column(Boolean)

    # Only for truly complex OOB cases inside entries (avoid if possible)
    value_json = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))

    entry = relationship("Entry", back_populates="values")
    field_definition = relationship("FieldDefinition")


# To wire this up, add to the Experiment model:
# entries = relationship("Entry", back_populates="experiment", cascade="all, delete-orphan")
#
# You may also want a link from Entry to Sample (directly or via
# ExperimentSampleExecution) for non-pure sample_data entries.


# ---------------------------------------------------------------------------
# Full Relationship Sketch (user clarification incorporated verbatim)
#
# Processes are composed of experiments (templates)
# Experiments are composed of entries
#
# This does make sense
#  Processes:
#   An Entry can be linked to a process step via process_step_id.
#   ProcessSample tracks which samples are assigned to the overall process; the per-step data lives in the Entry + EntryFieldValue layer.
#
# Experiments are composed of entries:
#   - An Experiment has one or more Entry records.
#   - Entry can be predefined (OOB actions) or custom (sample_data or experiment_detail).
#   - For custom entries, columns come from FieldDefinitions (defined in the template).
#   - Values for those columns go into EntryFieldValue.
#
# Process <-> Entry / data flow:
#   - An Entry can be linked to a process step via process_step_id.
#     (This allows tracing which Entry belongs to which step in the Process.)
#   - ProcessSample tracks which samples are assigned to the overall process.
#   - The per-step data lives in the Entry + EntryFieldValue layer.
#     (Not duplicated at ProcessSample; ProcessSample is the assignment/queueing at process level.)
#
# Example flow for a sample in a Process:
#   1. Sample assigned to Process → ProcessSample row created.
#   2. For step 1 (Experiment from template):
#      - Experiment created.
#      - Entries created for that Experiment (from template).
#      - For a 'sample_data' Entry: EntryFieldValue rows created for the sample's values in that entry's columns.
#   3. Data in EntryFieldValue can drive write-back to Sample.
#   4. Move to next step, new Entries / values for the next Experiment.
#
# This keeps:
# - Process level: which samples, overall ordering of experiment templates.
# - Experiment level: the entries (data capture components).
# - Step/Entry level: the actual per-sample or per-experiment data values.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Minimal Process sketch for composition (to complete the picture)
#
# Processes are composed of experiment (templates):
#
# class Process(BaseModel):
#     name = ...
#     description = ...
#     # status etc.
#
# class ProcessStep(Base):
#     """One step in a Process: references an ExperimentTemplate."""
#     process_id = Column(FK('processes.id'))
#     experiment_template_id = Column(FK('experiment_templates.id'))
#     sort_order = Column(Integer)
#     # When the process is executed for samples:
#     #   - An Experiment instance is created from the template.
#     #   - Entries are created for that Experiment.
#     #   - The Entry can reference this ProcessStep via process_step_id.
#
# ---------------------------------------------------------------------------
# ELN Process (Phase 1)
#
# Distinct from LIMS experiment_processes / process_steps (run sub-checklists).
# Tables: eln_processes, eln_process_steps, eln_process_samples
# API: /v1/eln-processes
# ---------------------------------------------------------------------------

class ELNProcess(BaseModel):
    """
    Ordered composition of experiment templates (ELN multi-step workflow).

    Inherits BaseModel: id, name, description, active, audit fields.
    Name uniqueness is global (same pattern as Experiment / ExperimentTemplate).
    """
    __tablename__ = 'eln_processes'

    status_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id'),
        nullable=True,
        index=True,
    )

    status = relationship("ListEntry", foreign_keys=[status_id])
    steps = relationship(
        "ELNProcessStep",
        back_populates="process",
        order_by="ELNProcessStep.sort_order",
        cascade="all, delete-orphan",
    )
    process_samples = relationship(
        "ELNProcessSample",
        back_populates="process",
        cascade="all, delete-orphan",
    )


# Backward-compatible alias used by earlier sketches / imports
Process = ELNProcess


class ELNProcessStep(Base):
    """
    One ordered step in an ELN Process.
    References an ExperimentTemplate; optional experiment_id when instantiated.
    """
    __tablename__ = 'eln_process_steps'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('eln_processes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id'),
        nullable=False,
        index=True,
    )
    # Optional: experiment instance created when this step is executed
    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=True)  # optional label override
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    process = relationship("ELNProcess", back_populates="steps")
    experiment_template = relationship("ExperimentTemplate")
    experiment = relationship("Experiment")
    entries = relationship("Entry", back_populates="process_step")


class ELNProcessSample(Base):
    """
    Sample assignment at the ELN Process level.

    Authoritative for "this sample belongs to this process".
    Per-step execution detail remains ExperimentSampleExecution / Entry (Phase 2).
    """
    __tablename__ = 'eln_process_samples'
    __table_args__ = (
        UniqueConstraint('process_id', 'sample_id', name='uq_eln_process_samples_process_sample'),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('eln_processes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('samples.id'),
        nullable=False,
        index=True,
    )
    # assigned | in_progress | completed | removed
    status = Column(String(32), nullable=False, server_default='assigned', default='assigned')
    current_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('eln_process_steps.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    process = relationship("ELNProcess", back_populates="process_samples")
    sample = relationship("Sample")
    current_step = relationship("ELNProcessStep", foreign_keys=[current_step_id])


# Backward-compatible alias
ProcessSample = ELNProcessSample



# ---------------------------------------------------------------------------
# Sketch: How an ExperimentTemplate declares the entries it is composed of
#
# "Experiments are composed of entries"
#
# class ExperimentTemplate(BaseModel):
#     ...
#     # Predefined entries (OOB) that instances of this template will have
#     # Can be a JSONB list of keys or a proper association table
#     predefined_entry_keys = Column(JSONB, default=list)
#
#     # FieldDefinitions that define custom columns for entries in this template
#     # These can be grouped (e.g. "my_sample_data_entry_columns")
#     # For simplicity in MVP, FieldDefinitions can have template_id
#
# When an Experiment is instantiated from the template:
#   - For each key in predefined_entry_keys:
#       create Entry(..., entry_type='predefined_action', predefined_entry_key=key, ...)
#   - For custom entries defined in the template:
#       create Entry(..., entry_type='sample_data' or 'experiment_detail')
#       link the relevant FieldDefinitions to it via the junction
#
# This is how "samples and experiment detail entries will have the columns
# displayed defined in the template."
# ---------------------------------------------------------------------------

# Path 1 top-level fields (e.g. specimen_biotype_id on Sample) are available
# in sample_data Entries (the Entry can include or display the sample's
# direct columns). They also appear when working with ProcessSample in Processes.

# ---------------------------------------------------------------------------
# Sketch: How ExperimentTemplate declares the entries it is composed of
#
# "Experiments are composed of entries"
#
# In the new model, ExperimentTemplate declares:
#
# - Predefined entries (OOB): list of keys for built-in actions/entries
#   that will be instantiated for every Experiment created from this template.
#
# - Custom entries: groups of FieldDefinitions that define the columns
#   for sample_data and experiment_detail entries.
#   The "columns displayed defined in the template" come from here.
#
# Example associations (add to ExperimentTemplate or as separate models):
#
# class ExperimentTemplate(BaseModel):
#     ...
#     # Predefined OOB entries (simple for MVP)
#     # e.g. ["aliquoting", "qc_review_pass_fail", "index_assignment"]
#     predefined_entry_keys = Column(JSONB, default=list)
#
#     # Or a proper many-to-many to a PredefinedEntry registry
#
#     # Custom entry definitions (the columns for custom entries)
#     # These FieldDefinitions are "defined in the template"
#     custom_entry_definitions = relationship(
#         "TemplateCustomEntry",
#         back_populates="template",
#         cascade="all, delete-orphan"
#     )
#
# class TemplateCustomEntry(Base):
#     """A named custom entry (sample_data or experiment_detail) in the template."""
#     __tablename__ = 'template_custom_entries'
#
#     template_id = Column(FK('experiment_templates.id'))
#     entry_name = Column(String(255))      # e.g. "my_sample_data_table", "experiment_notes"
#     entry_type = Column(String(64))       # 'sample_data' or 'experiment_detail'
#     sort_order = Column(Integer, default=0)
#
#     # The columns for this entry are the linked FieldDefinitions
#     field_definitions = relationship(
#         "TemplateCustomEntryField",
#         back_populates="custom_entry"
#     )
#
# class TemplateCustomEntryField(Base):
#     """Links a FieldDefinition as a column in a custom entry."""
#     __tablename__ = 'template_custom_entry_fields'
#
#     custom_entry_id = Column(FK('template_custom_entries.id'))
#     field_definition_id = Column(FK('field_definitions.id'))
#     sort_order = Column(Integer, default=0)
#     visible = Column(Boolean, default=True)
#
#     custom_entry = relationship("TemplateCustomEntry", back_populates="field_definitions")
#     field_definition = relationship("FieldDefinition")
#
# Instantiation (when creating Experiment from template):
#   for key in template.predefined_entry_keys:
#       Entry(
#           experiment=exp,
#           entry_type='predefined_action',
#           predefined_entry_key=key,
#           ...
#       )
#
#   for custom in template.custom_entry_definitions:
#       entry = Entry(
#           experiment=exp,
#           entry_type=custom.entry_type,   # 'sample_data' or 'experiment_detail'
#           name=custom.entry_name,
#           ...
#       )
#       for tcef in custom.field_definitions:   # ordered
#           EntryFieldDefinition(
#               entry=entry,
#               field_definition=tcef.field_definition,
#               sort_order=...
#           )
#
# ---------------------------------------------------------------------------
