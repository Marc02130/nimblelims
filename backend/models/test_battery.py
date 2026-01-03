"""
Test Battery models for NimbleLims
"""
from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from .base import BaseModel, Base


class TestBattery(BaseModel):
    """Model for test batteries (grouped analyses)"""
    __tablename__ = 'test_batteries'
    
    # Relationships
    battery_analyses = relationship("BatteryAnalysis", back_populates="battery", cascade="all, delete-orphan")
    tests = relationship("Test", back_populates="battery")
    creator = relationship("User", foreign_keys="TestBattery.created_by", back_populates="created_test_batteries")
    modifier = relationship("User", foreign_keys="TestBattery.modified_by", back_populates="modified_test_batteries")


class BatteryAnalysis(Base):
    """Junction model for battery-analyses relationship"""
    __tablename__ = 'battery_analyses'
    
    # Composite primary key
    battery_id = Column(PostgresUUID(as_uuid=True), ForeignKey('test_batteries.id'), primary_key=True)
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), primary_key=True)
    
    # Battery-specific fields
    sequence = Column(Integer, nullable=False, default=1)
    optional = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    battery = relationship("TestBattery", back_populates="battery_analyses")
    analysis = relationship("Analysis", back_populates="battery_analyses")

