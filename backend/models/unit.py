from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Unit(BaseModel):
    __tablename__ = 'units'
    
    # Unit-specific fields
    multiplier = Column(Numeric(20, 10), nullable=True)  # relative to base unit for conversions
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    
    # Relationships
    type_rel = relationship("ListEntry", foreign_keys=[type])
    concentration_containers = relationship("Container", foreign_keys="Container.concentration_units", back_populates="concentration_units_rel")
    amount_containers = relationship("Container", foreign_keys="Container.amount_units", back_populates="amount_units_rel")
    concentration_contents = relationship("Contents", foreign_keys="Contents.concentration_units", back_populates="concentration_units_rel")
    amount_contents = relationship("Contents", foreign_keys="Contents.amount_units", back_populates="amount_units_rel")
    creator = relationship("User", foreign_keys="Unit.created_by", back_populates="created_units")
    modifier = relationship("User", foreign_keys="Unit.modified_by", back_populates="modified_units")