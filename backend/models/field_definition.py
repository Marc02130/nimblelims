"""
FieldDefinition model.

This replaces the old custom_attributes / custom_attributes_config pattern
for modeled extensibility.

JSONB is no longer used for user-defined modeled fields.
It remains only for true OOB unstructured data (template_definition, row_data, etc.).

A FieldDefinition describes a typed field that can be:
- Added as a real column on a core entity table (top-level extension)
- Used as a column definition inside a custom Entry (inside Experiments/Processes)

Lists (simple values) vs full lookup tables (with metadata) are distinguished
at the data_type level and storage level.
"""

import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, BaseModel
from .list import List

class FieldDefinition(BaseModel):
    """
    Definition of an extensible, typed field.

    data_type possibilities (MVP):
      - 'text'
      - 'number' (numeric)
      - 'date'
      - 'boolean'
      - 'list'          → simple value from a List (just the value)
      - 'lookup'        → FK to another entity table when metadata is needed

    For list-backed fields we reference the existing `lists` + `list_entries` system.
    """

    __tablename__ = 'field_definitions'

    # What this field belongs to
    entity_type = Column(String(64), nullable=False, index=True)   # 'sample', 'experiment', 'project', etc.

    # Core identity
    name = Column(String(255), nullable=False, index=True)         # internal name, e.g. 'specimen_biotype'
    display_name = Column(String(255), nullable=True)              # human label

    # Type information
    data_type = Column(String(32), nullable=False)                 # text, number, date, boolean, list, lookup
    source_list_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lists.id'),
        nullable=True,
        index=True
    )   # for data_type in ('list', 'lookup') when using the list system

    # Behavior
    is_required = Column(Boolean, nullable=False, server_default='false')
    is_unique = Column(Boolean, nullable=False, server_default='false')  # scope can be added later
    default_value = Column(JSONB, nullable=True)   # simple default; more complex defaults in app

    # Validation & UI
    validation_rules = Column(JSONB, nullable=True, server_default='{}')
    ui_hints = Column(JSONB, nullable=True, server_default='{}')     # order, section, widget type, etc.

    # Scope (MVP: mostly global; can be narrowed later)
    template_id = Column(PostgresUUID(as_uuid=True), ForeignKey('experiment_templates.id'), nullable=True)
    process_id = Column(PostgresUUID(as_uuid=True), ForeignKey('processes.id'), nullable=True)

    # Whether this field is materialized as a real column on the parent entity table
    # (true for top-level extensions like specimen_biotype on samples)
    # or only exists inside Entry values (for highly variable per-template columns).
    is_materialized_column = Column(Boolean, nullable=False, server_default='true')

    # For materialized top-level fields, this is the actual column name on the entity table
    # (e.g. 'specimen_biotype_id'). For non-materialized (inside entries), this is null.
    column_name = Column(String(255), nullable=True)

    active = Column(Boolean, nullable=False, server_default='true', index=True)

    # Relationships
    source_list = relationship("List", foreign_keys=[source_list_id])

    # Entries that use this FieldDefinition as one of their columns
    entries = relationship(
        "Entry",
        secondary="entry_field_definitions",
        back_populates="field_definitions"
    )

    # creator / modifier inherited from BaseModel

    __table_args__ = (
        # You may want a unique constraint on (entity_type, name) + scope later
    )

# ---------------------------------------------------------------------------
# Value storage for dynamic columns inside Entries (Path 2, but available)
# (used when the column is defined per-template/per-entry rather than
#  as a permanent column on the parent entity table)
# ---------------------------------------------------------------------------

class EntryFieldValue(Base):
    """
    Stores the actual value for a FieldDefinition that lives inside a custom Entry.

    This table is used for the variable columns inside:
      - Sample data entries
      - Experiment detail entries

    It allows templates to define arbitrary columns without making the main
    entity tables infinitely wide.

    For top-level fields added directly to Sample / Experiment / etc.,
    we add real columns instead of (or in addition to) rows in this table.
    """

    __tablename__ = 'entry_field_values'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The Entry this value belongs to.
    entry_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)

    field_definition_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('field_definitions.id'),
        nullable=False,
        index=True
    )

    # Typed value columns (only one should be populated based on data_type)
    value_text = Column(Text)
    value_number = Column(Numeric)          # or use separate integer / float if needed
    value_list_entry_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('list_entries.id')
    )
    value_date = Column(DateTime(timezone=True))
    value_boolean = Column(Boolean)

    # Fallback / complex values (should be rare after migration)
    value_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))

    field_definition = relationship("FieldDefinition")
