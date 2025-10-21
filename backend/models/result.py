from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Result(Base):
    __tablename__ = 'results'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Result-specific fields
    test_id = Column(PostgresUUID(as_uuid=True), ForeignKey('tests.id'), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), nullable=False)
    raw_result = Column(String(255))
    reported_result = Column(String(255))
    qualifiers = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    calculated_result = Column(String(255))
    entry_date = Column(DateTime, default=func.now())
    entered_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Relationships
    test = relationship("Test", back_populates="results")
    analyte = relationship("Analyte", back_populates="results")
    entered_by_user = relationship("User", foreign_keys=[entered_by])
