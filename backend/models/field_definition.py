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
# Value storage for dynamic columns inside Entries
# (used when the column is defined per-template/per-entry rather than
#  as a permanent column on the parent entity table)
# ---------------------------------------------------------------------------

class EntryFieldValue(Base):
    """
    Stores the actual value for a FieldDefinition that lives inside a custom Entry.

    This table is used **only** for the variable / per-template columns inside
    custom Entries (sample_data entries or experiment_detail entries).

    It allows templates to define arbitrary columns (via FieldDefinitions)
    without making the main entity tables (samples, experiments) infinitely wide.

    For top-level fields (e.g. adding specimen_biotype directly to the samples table),
    we instead add a real column during migration and set is_materialized_column=True
    on the FieldDefinition. No row is needed in this table for those.

    For sample_data entries:
    - There is typically one Entry per "data table" defined for the experiment.
    - For each sample in that experiment + each column (FieldDefinition) → one row here.
    - sample_id links it.
    - After saving, the app can selectively write values back to the core Sample
      (e.g. concentration, volume) as per the design.

    Typed columns are used so we avoid generic JSONB for modeled data.
    value_json is only a rare fallback for complex OOB cases inside entries.
    """

    __tablename__ = 'entry_field_values'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The Entry this value belongs to.
    # For now we keep it generic; later we can have separate tables or
    # a polymorphic link if needed.
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


# ---------------------------------------------------------------------------
# ===========================================================================
# PATH 1 FOCUS: Direct columns on entity tables for top-level fields
# (High ROI MVP: list-backed + simple scalars on Samples, Experiments, etc.)
# ===========================================================================

"""
Path 1: When adding a top-level field (e.g. via schema admin or template),
we generate a migration to ADD a real column to the target table.

This is preferred for:
- Fields that should be queryable with standard SQL
- List-backed fields (FK to list_entries)
- Simple scalars that appear on the main entity

Concrete examples:

A. List-backed (specimen_biotype on samples)
- FieldDefinition:
    entity_type='sample'
    name='specimen_biotype'
    data_type='list'
    source_list_id = <uuid of 'specimen_biotypes' list>
    is_materialized_column=True
    column_name='specimen_biotype_id'

- Generated migration snippet:
  op.add_column('samples', sa.Column(
      'specimen_biotype_id', postgresql.UUID(as_uuid=True),
      sa.ForeignKey('list_entries.id'), nullable=True))
  op.create_index('ix_samples_specimen_biotype_id', 'samples', ['specimen_biotype_id'])

- In models/sample.py (after):
  specimen_biotype_id = Column(
      PostgresUUID(as_uuid=True),
      ForeignKey('list_entries.id'),
      nullable=True, index=True
  )
  specimen_biotype = relationship(
      'ListEntry', foreign_keys=[specimen_biotype_id]
  )

- Usage:
  sample.specimen_biotype.name   # the value
  # Appears in Entries if referenced, in Processes via ProcessSample

B. Simple text column (e.g. "lot_number" on samples)
- data_type='text'
- Migration: op.add_column('samples', sa.Column('lot_number', sa.Text(), nullable=True))
- Model: lot_number = Column(Text)

C. Numeric column (e.g. "dilution_factor")
- data_type='number' → NUMERIC column

Pros of Path 1 (direct columns):
- Excellent performance, indexes, joins, constraints
- Standard SQLAlchemy / reporting
- RLS applies naturally
- Consistent with existing list fields (matrix, qc_type etc.)

Cons:
- Migration required per new top-level field (mitigated by generated + reviewed migrations)
- Tables get wider (ok for focused use on Samples/Experiments first)

When to use Path 1:
- Top-level on core entities
- List or simple scalar
- High ROI for replacing custom_attributes / spreadsheets

Integration:
- New columns on Sample usable in sample_data Entries
- Usable in Processes
- Hard cutover: migrate data from old JSONB to new column
"""
#            entry_id=..., field_definition_id=conc_fd, sample_id=..., value_number=1.23
#            entry_id=..., field_definition_id=temp_fd, sample_id=..., value_number=37.0
#            entry_id=..., field_definition_id=notes_fd, sample_id=..., value_text="..."
#
#    - Pros of this table: flexible per-template columns without schema bloat.
#    - Write-back: app can copy value_number from conc_fd to sample.concentration.
#
# When to use which:
# - Direct column: top-level, commonly used, benefits from native DB features (e.g. specimen_biotype on Sample).
# - entry_field_values: highly variable columns inside template-defined Entries.
# ---------------------------------------------------------------------------