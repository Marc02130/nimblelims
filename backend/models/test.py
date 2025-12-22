from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Test(BaseModel):
    __tablename__ = 'tests'
    
    # Test-specific fields
    sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=False)
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), nullable=False)
    battery_id = Column(PostgresUUID(as_uuid=True), ForeignKey('test_batteries.id'), nullable=True)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    review_date = Column(DateTime)
    test_date = Column(DateTime)
    technician_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    sample = relationship("Sample", back_populates="tests")
    analysis = relationship("Analysis", back_populates="tests")
    battery = relationship("TestBattery", back_populates="tests")
    technician = relationship("User", foreign_keys=[technician_id])
    results = relationship("Result", back_populates="test")
