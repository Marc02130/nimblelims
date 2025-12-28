from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Sample(BaseModel):
    __tablename__ = 'samples'
    
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
    client_sample_id = Column(String(255), nullable=True, unique=True)
    
    # Relationships
    project = relationship("Project", back_populates="samples")
    parent_sample = relationship("Sample", primaryjoin="Sample.parent_sample_id == Sample.id")
    child_samples = relationship("Sample", primaryjoin="Sample.id == Sample.parent_sample_id")
    tests = relationship("Test", back_populates="sample")
    contents = relationship("Contents", back_populates="sample")
    creator = relationship("User", foreign_keys="Sample.created_by", back_populates="created_samples")
    modifier = relationship("User", foreign_keys="Sample.modified_by", back_populates="modified_samples")
