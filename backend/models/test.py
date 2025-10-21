from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Test(Base):
    __tablename__ = 'tests'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Test-specific fields
    sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=False)
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    review_date = Column(DateTime)
    test_date = Column(DateTime)
    technician_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    sample = relationship("Sample", back_populates="tests")
    analysis = relationship("Analysis", back_populates="tests")
    technician = relationship("User", foreign_keys=[technician_id])
    results = relationship("Result", back_populates="test")
