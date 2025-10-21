from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Analysis-specific fields
    method = Column(String(255))
    turnaround_time = Column(Integer)  # in days
    cost = Column(Numeric(10, 2))
    
    # Relationships
    analytes = relationship("Analyte", secondary="analysis_analytes", back_populates="analyses")
    tests = relationship("Test", back_populates="analysis")


class Analyte(Base):
    __tablename__ = 'analytes'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    analyses = relationship("Analysis", secondary="analysis_analytes", back_populates="analytes")
    results = relationship("Result", back_populates="analyte")


class AnalysisAnalyte(Base):
    __tablename__ = 'analysis_analytes'
    
    analysis_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analyses.id'), primary_key=True)
    analyte_id = Column(PostgresUUID(as_uuid=True), ForeignKey('analytes.id'), primary_key=True)
    data_type = Column(String(50))  # e.g., 'numeric', 'text'
    list_id = Column(PostgresUUID(as_uuid=True), ForeignKey('lists.id'))
    high_value = Column(Numeric(15, 6))
    low_value = Column(Numeric(15, 6))
    significant_figures = Column(Integer)
    calculation = Column(String)
    reported_name = Column(String(255))
    display_order = Column(Integer)
    is_required = Column(Boolean, default=False)
    default_value = Column(String(255))
