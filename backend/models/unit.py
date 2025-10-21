from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Unit(Base):
    __tablename__ = 'units'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Unit-specific fields
    multiplier = Column(Numeric(20, 10))  # relative to base unit for conversions
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    
    # Relationships
    unit_type = relationship("ListEntry", foreign_keys=[type])
