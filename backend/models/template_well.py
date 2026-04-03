"""
template_well_definitions — relational well layout replacing JSONB for concentrations.

Concentrations are analytical data (queried, validated, compared across runs).
Storing them here (not in template_definition JSONB) makes them queryable from day 1.
"""
import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from .base import Base


class TemplateWellDefinition(Base):
    """
    One row per well per experiment template.

    Unique constraint: (template_id, well_position) — one definition per well per template.
    Concentration fields are null for control wells (controls identified by sample.qc_type,
    not by concentration presence).
    """
    __tablename__ = 'template_well_definitions'

    id                  = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id         = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    well_position       = Column(String(10), nullable=False)   # "A1", "H12"
    sample_role         = Column(String(20), nullable=True)    # "test", "positive_control", "negative_control"
    concentration_value = Column(Numeric(), nullable=True)     # null for control wells
    concentration_unit  = Column(String(20), nullable=True)    # "nM", "uM", "mg/mL"
    replicate_group     = Column(String(100), nullable=True)   # groups wells of same compound + dilution series
    client_id           = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
