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
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
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

    # Optional: if this entry is part of a specific step in a Process
    process_step_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('process_steps.id'),  # or the new process step if modeled separately
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
    experiment = relationship("Experiment", back_populates="entries")  # add to Experiment model
    # process_step = relationship(...)

    # For custom entries: the FieldDefinitions that define the columns of this entry
    field_definitions = relationship(
        "FieldDefinition",
        secondary="entry_field_definitions",  # junction table
        back_populates="entries"
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

    entry = relationship("Entry", back_populates="field_definitions")
    field_definition = relationship("FieldDefinition", back_populates="entries")


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


# To wire this up, you would add to the Experiment model:
# entries = relationship("Entry", back_populates="experiment", cascade="all, delete-orphan")
#
# You may also want a many-to-many or direct link from Entry to Sample
# for entries that are not purely sample_data (or use ExperimentSampleExecution).
```

# ---------------------------------------------------------------------------
# Usage Notes & Relationships (for the sketch)
#
# Entry
#   - belongs to Experiment (and optionally a Process step)
#   - has many FieldDefinitions (its columns) via the junction
#   - has many EntryFieldValue (the data)
#
# For a custom sample_data entry:
#   - The template defines which FieldDefinitions are the columns of this entry.
#   - For each sample assigned to the experiment, one EntryFieldValue row per field.
#   - After validation, selected values can be written back to the Sample record
#     (e.g. concentration, volume).
#
# Predefined entries mostly use `predefined_entry_key` + `config`.
# They rarely populate many EntryFieldValue rows.
#
# This gives template-controlled structure while keeping storage efficient.
# ---------------------------------------------------------------------------
- Updates to the `Experiment` model to include `entries`?