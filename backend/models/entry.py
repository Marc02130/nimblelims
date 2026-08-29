"""
Entry and related models for data capture inside Experiments and Processes.

This is part of the new structured approach replacing loose ExperimentDetail + JSONB.

An Entry represents a "component" or "block" inside an Experiment (or a step in a Process).

Types of Entries (entry_type):
- 'experiment_sample_data' : One row per sample in the experiment (process data + RO sample fields)
- 'experiment_data'        : Purpose-specific table/form (plan lines, header); rows not auto from cohort
- 'predefined_action'      : OOB behaviors (aliquot/pool execute, etc.)
- 'display_table'          : Read-only structured display (legacy)
- Legacy aliases (normalized on write): 'sample_data' → experiment_sample_data,
  'experiment_detail' → experiment_data

Custom columns use FieldDefinitions; values in EntryFieldValue (typed columns).
"""

import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    Text,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, BaseModel

# Canonical + legacy aliases (legacy accepted, normalized to canonical on create/instantiate)
ENTRY_TYPES = frozenset(
    {
        "experiment_sample_data",
        "experiment_data",
        "predefined_action",
        "display_table",
        # legacy
        "sample_data",
        "experiment_detail",
    }
)

ENTRY_TYPE_ALIASES = {
    "sample_data": "experiment_sample_data",
    "experiment_detail": "experiment_data",
}

SAMPLE_SCOPED_ENTRY_TYPES = frozenset(
    {
        "experiment_sample_data",
        "sample_data",
    }
)

EXPERIMENT_SCOPED_ENTRY_TYPES = frozenset(
    {
        "experiment_data",
        "experiment_detail",
    }
)

READ_ONLY_ENTRY_TYPES = frozenset(
    {
        "display_table",
    }
)


def normalize_entry_type(entry_type: str) -> str:
    return ENTRY_TYPE_ALIASES.get(entry_type, entry_type)


def is_sample_scoped_entry(entry_type: str) -> bool:
    return normalize_entry_type(entry_type) == "experiment_sample_data"


def is_experiment_scoped_entry(entry_type: str) -> bool:
    return normalize_entry_type(entry_type) == "experiment_data"


# Display-only Sample system fields (accessioning SoT — never write-back)
SAMPLE_SYSTEM_FIELDS = {
    "client_sample_id": {"label": "Client Sample ID", "data_type": "text"},
    "received_date": {"label": "Received date", "data_type": "date"},
    "date_sampled": {"label": "Date sampled", "data_type": "date"},
    "specimen_biotype_id": {"label": "Biotype", "data_type": "list"},
    "sample_type": {"label": "Sample type", "data_type": "list"},
    "status": {"label": "Status", "data_type": "list"},
    "matrix": {"label": "Matrix", "data_type": "list"},
    "temperature": {"label": "Temperature", "data_type": "number"},
}

# Experiment-mutable Sample columns eligible for write-back on entry submit
# (identity/accessioning + system display fields excluded — S14 / OQ-S14)
# specimen_biotype_id and temperature stay in SAMPLE_SYSTEM_FIELDS (RO display only)
SAMPLE_WRITE_BACK_COLUMNS = frozenset(
    {
        "due_date",
        "report_date",
    }
)

# v1 predefined entry keys (functionality wrappers; columns via field defs / config)
PREDEFINED_ENTRY_KEYS = frozenset(
    {
        "experiment_header",  # experiment_data — start context
        "samples",  # experiment_sample_data — cohort display
        "aliquot_pool_plan",  # experiment_data — plan lines + execute
        "aliquots_pools",  # experiment_sample_data — post-execute view
    }
)

PREDEFINED_ENTRY_DEFAULTS = {
    "experiment_header": {
        "entry_type": "experiment_data",
        "name": "Experiment header",
        "description": "Start context for the experiment",
    },
    "samples": {
        "entry_type": "experiment_sample_data",
        "name": "Samples",
        "description": "Cohort selected at experiment start (queue / scan)",
        "config": {
            "sample_columns": [
                "client_sample_id",
                "specimen_biotype_id",
                "received_date",
                "sample_type",
                "status",
            ],
        },
    },
    "aliquot_pool_plan": {
        "entry_type": "experiment_data",
        "name": "Aliquot / pool plan",
        "description": "Plan amounts to remove/add; execute creates dest samples",
        "config": {
            "method": "aliquot_by_volume",
            "default_dest_sample_type": None,
        },
    },
    "aliquots_pools": {
        "entry_type": "experiment_sample_data",
        "name": "Aliquots / pools",
        "description": "Post-execute view of resulting samples",
        "config": {
            "sample_columns": ["client_sample_id", "sample_type"],
            "minted_sample_ids": [],
            "populated_after_execute": False,
        },
    },
}


class Entry(Base):
    """
    A data capture / action component inside an Experiment.

    Does not use BaseModel: entry names are not globally unique (scoped to experiment).
    Entries are typically declared on ExperimentTemplate.template_definition['entries']
    and instantiated when an Experiment is created / a process step is instantiated.
    """

    __tablename__ = "entries"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to an ELN process step (when experiment lives inside a process)
    process_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entry_type = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    predefined_entry_key = Column(String(128), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, server_default="0", default=0)
    config = Column(JSONB, nullable=True, server_default="{}")
    active = Column(Boolean, nullable=False, server_default="true", default=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    experiment = relationship("Experiment", back_populates="entries")
    process_step = relationship("ELNProcessStep", back_populates="entries")

    field_definitions = relationship(
        "FieldDefinition",
        secondary="entry_field_definitions",
        back_populates="entries",
        overlaps="field_definition_links,entry,field_definition",
    )
    field_definition_links = relationship(
        "EntryFieldDefinition",
        back_populates="entry",
        cascade="all, delete-orphan",
        overlaps="field_definitions,entries,field_definition",
    )
    values = relationship(
        "EntryFieldValue",
        back_populates="entry",
        cascade="all, delete-orphan",
    )


class EntryFieldDefinition(Base):
    """Junction: which FieldDefinitions are columns on this Entry instance."""

    __tablename__ = "entry_field_definitions"

    entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    field_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("field_definitions.id"),
        primary_key=True,
    )
    sort_order = Column(Integer, nullable=False, server_default="0", default=0)
    visible = Column(Boolean, nullable=False, server_default="true", default=True)
    # If set, upserting a value for this field may write through to Sample.<column>
    # Must be in SAMPLE_WRITE_BACK_COLUMNS.
    write_back_target = Column(String(128), nullable=True)

    entry = relationship(
        "Entry",
        back_populates="field_definition_links",
        overlaps="entries,field_definitions",
    )
    field_definition = relationship(
        "FieldDefinition",
        overlaps="entries,field_definitions",
    )


class EntryFieldValue(Base):
    """
    Typed value for one FieldDefinition inside one Entry.

    experiment_sample_data: one cell per (entry, field, sample); row_key null.
    experiment_data: multi-row table; each logical row has a stable row_key;
      sample_id optional (purpose subset). Legacy single cell: both null.
    """

    __tablename__ = "entry_field_values"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("field_definitions.id"),
        nullable=False,
        index=True,
    )
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("samples.id"),
        nullable=True,
        index=True,
    )
    # Free multi-row identity for experiment_data tables (not sample-scoped).
    row_key = Column(String(64), nullable=True, index=True)

    value_text = Column(Text)
    value_number = Column(Numeric(precision=20, scale=10))
    value_list_entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
    )
    value_date = Column(DateTime(timezone=True))
    value_boolean = Column(Boolean)
    value_json = Column(JSONB)

    # Last write-back audit (Phase 2: last-write-wins; store previous sample value here)
    write_back_at = Column(DateTime(timezone=True), nullable=True)
    write_back_previous = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

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
# ELN Process definitions + instances (Phase 1–3)
#
# Distinct from lims_run_checklists (checklist inside a LimsRun).
# Decision #6: processes are always defined → instance from definition.
# Decision #1: typed steps eln_experiment | lims_run.
# ---------------------------------------------------------------------------

STEP_KINDS = frozenset({"eln_experiment", "lims_run"})
EXECUTION_MODES = frozenset({"eln_experiment", "lims_run"})


class ELNProcessDefinition(BaseModel):
    """Reusable multi-step protocol (first-class definition)."""

    __tablename__ = "eln_process_definitions"

    # name, description, active, audit from BaseModel
    steps = relationship(
        "ELNProcessDefinitionStep",
        back_populates="process_definition",
        order_by="ELNProcessDefinitionStep.sort_order",
        cascade="all, delete-orphan",
    )
    instances = relationship("ELNProcess", back_populates="process_definition")


class ELNProcessDefinitionStep(Base):
    """One ordered step in a process definition (typed)."""

    __tablename__ = "eln_process_definition_steps"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_kind = Column(
        String(32),
        nullable=False,
        server_default="eln_experiment",
        default="eln_experiment",
    )
    execution_mode = Column(
        String(32),
        nullable=False,
        server_default="eln_experiment",
        default="eln_experiment",
    )
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("experiment_templates.id"),
        nullable=True,
        index=True,
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    process_definition = relationship("ELNProcessDefinition", back_populates="steps")
    experiment_template = relationship("ExperimentTemplate")


class ELNProcess(BaseModel):
    """
    Process *instance* — one execution of a process definition.
    """

    __tablename__ = "eln_processes"

    work_order_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("work_orders.id", use_alter=True, name="fk_eln_processes_work_order_id"),
        nullable=True,
        index=True,
    )
    status_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("list_entries.id"),
        nullable=True,
        index=True,
    )
    process_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_definitions.id"),
        nullable=True,
        index=True,
    )

    status = relationship("ListEntry", foreign_keys=[status_id])
    process_definition = relationship(
        "ELNProcessDefinition", back_populates="instances"
    )
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


Process = ELNProcess


class ELNProcessStep(Base):
    """
    One ordered step in a process instance (snapshot from definition).
    """

    __tablename__ = "eln_process_steps"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_kind = Column(
        String(32),
        nullable=False,
        server_default="eln_experiment",
        default="eln_experiment",
    )
    execution_mode = Column(
        String(32),
        nullable=False,
        server_default="eln_experiment",
        default="eln_experiment",
    )
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("experiment_templates.id"),
        nullable=True,
        index=True,
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id"),
        nullable=True,
        index=True,
    )
    experiment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("experiments.id"),
        nullable=True,
        index=True,
    )
    current_lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lims_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    process = relationship("ELNProcess", back_populates="steps")
    experiment_template = relationship("ExperimentTemplate")
    experiment = relationship("Experiment")
    current_lims_run = relationship("LimsRun", foreign_keys=[current_lims_run_id])
    entries = relationship("Entry", back_populates="process_step")
    lims_run_links = relationship(
        "ELNProcessStepLimsRun",
        back_populates="process_step",
        cascade="all, delete-orphan",
    )


class ELNProcessStepLimsRun(Base):
    """History of LimsRuns attached to a process step instance."""

    __tablename__ = "eln_process_step_lims_runs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("lims_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    process_step = relationship("ELNProcessStep", back_populates="lims_run_links")
    lims_run = relationship("LimsRun")


class ELNProcessSample(Base):
    """
    Sample assignment at the ELN Process level.

    Authoritative for "this sample belongs to this process".
    Per-step execution detail remains ExperimentSampleExecution / Entry (Phase 2).
    """

    __tablename__ = "eln_process_samples"
    __table_args__ = (
        UniqueConstraint(
            "process_id", "sample_id", name="uq_eln_process_samples_process_sample"
        ),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("samples.id"),
        nullable=False,
        index=True,
    )
    # queued (ready/waiting) | in_progress (experiment started) | completed | removed
    # legacy: "assigned" treated as queued
    status = Column(
        String(32), nullable=False, server_default="queued", default="queued"
    )
    current_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("eln_process_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

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
