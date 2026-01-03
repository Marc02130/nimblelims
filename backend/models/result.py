from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Result(BaseModel):
    __tablename__ = 'results'
    
    # Result-specific fields
    test_id = Column(PostgresUUID(as_uuid=True), ForeignKey('tests.id'), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), nullable=False)
    raw_result = Column(String(255), nullable=True)
    reported_result = Column(String(255), nullable=True)
    qualifiers = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    calculated_result = Column(String(255), nullable=True)
    entry_date = Column(DateTime, default=func.now(), nullable=False)
    entered_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    
    # Relationships
    test = relationship("Test", back_populates="results")
    analyte = relationship("Analyte", back_populates="results")
    entered_by_user = relationship("User", foreign_keys=[entered_by], back_populates="entered_results")
    creator = relationship("User", foreign_keys="Result.created_by", back_populates="created_results")
    modifier = relationship("User", foreign_keys="Result.modified_by", back_populates="modified_results")
