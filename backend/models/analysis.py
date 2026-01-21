from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class Analysis(BaseModel):
    __tablename__ = 'analyses'
    
    # Analysis-specific fields
    method = Column(String(255), nullable=True)
    turnaround_time = Column(Integer, nullable=True)  # in days
    cost = Column(Numeric(10, 2), nullable=True)
    shelf_life = Column(Integer, nullable=True)  # Days until expiration = date_sampled + shelf_life
    custom_attributes = Column(JSONB, nullable=True, default={})  # Custom attributes as JSON
    
    # Relationships
    analytes = relationship("Analyte", secondary="analysis_analytes", back_populates="analyses")
    tests = relationship("Test", back_populates="analysis")
    analysis_analytes = relationship("AnalysisAnalyte", back_populates="analysis")
    battery_analyses = relationship("BatteryAnalysis", back_populates="analysis")
    creator = relationship("User", foreign_keys="Analysis.created_by", back_populates="created_analyses")
    modifier = relationship("User", foreign_keys="Analysis.modified_by", back_populates="modified_analyses")


class Analyte(BaseModel):
    __tablename__ = 'analytes'
    
    # Analyte-specific fields
    cas_number = Column(String(50), nullable=True)  # CAS registry number
    units_default = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'), nullable=True)
    data_type = Column(String(20), nullable=True)  # numeric, text, date, boolean
    custom_attributes = Column(JSONB, nullable=True, default={})  # Custom attributes as JSON
    
    # Relationships
    analyses = relationship("Analysis", secondary="analysis_analytes", back_populates="analytes")
    results = relationship("Result", back_populates="analyte")
    analysis_analytes = relationship("AnalysisAnalyte", back_populates="analyte")
    default_unit = relationship("Unit", foreign_keys=[units_default])
    creator = relationship("User", foreign_keys="Analyte.created_by", back_populates="created_analytes")
    modifier = relationship("User", foreign_keys="Analyte.modified_by", back_populates="modified_analytes")


class AnalysisAnalyte(BaseModel):
    __tablename__ = 'analysis_analytes'
    
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), primary_key=True)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), primary_key=True)
    data_type = Column(String(50), nullable=True)  # e.g., 'numeric', 'text'
    list_id = Column(PostgresUUID(as_uuid=True), ForeignKey('lists.id'), nullable=True)
    high_value = Column(Numeric(15, 6), nullable=True)
    low_value = Column(Numeric(15, 6), nullable=True)
    significant_figures = Column(Integer, nullable=True)
    calculation = Column(String, nullable=True)
    reported_name = Column(String(255), nullable=True)
    display_order = Column(Integer, nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    default_value = Column(String(255), nullable=True)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="analysis_analytes")
    analyte = relationship("Analyte", back_populates="analysis_analytes")
