from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Unit(BaseModel):
    __tablename__ = 'units'
    
    # Unit-specific fields
    multiplier = Column(Numeric(20, 10))  # relative to base unit for conversions
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    
    # Relationships
    unit_type = relationship("ListEntry", foreign_keys=[type])
