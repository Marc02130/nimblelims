from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Sample(Base):
    __tablename__ = 'samples'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Sample-specific fields
    due_date = Column(DateTime)
    received_date = Column(DateTime)
    report_date = Column(DateTime)
    sample_type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    matrix = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    temperature = Column(Numeric(10, 2))
    parent_sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=True)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    qc_type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="samples")
    parent_sample = relationship("Sample", remote_side=[id], back_populates="child_samples")
    child_samples = relationship("Sample", back_populates="parent_sample")
    tests = relationship("Test", back_populates="sample")
    contents = relationship("Contents", back_populates="sample")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_samples")
    modifier = relationship("User", foreign_keys=[modified_by], back_populates="modified_samples")
