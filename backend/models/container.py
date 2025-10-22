from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric, Integer, Table
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class ContainerType(BaseModel):
    __tablename__ = 'container_types'
    
    # Container type-specific fields
    capacity = Column(Numeric(10, 3))
    material = Column(String(255))
    dimensions = Column(String(50))  # e.g., '8x12'
    preservative = Column(String(255))
    
    # Relationships
    containers = relationship("Container", back_populates="container_type")


class Container(BaseModel):
    __tablename__ = 'containers'
    
    # Container-specific fields
    row = Column(Integer, default=1)
    column = Column(Integer, default=1)
    concentration = Column(Numeric(15, 6))
    concentration_units = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'))
    amount = Column(Numeric(15, 6))
    amount_units = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'))
    type_id = Column(PostgresUUID(as_uuid=True), ForeignKey('container_types.id'), nullable=False)
    parent_container_id = Column(PostgresUUID(as_uuid=True), ForeignKey('containers.id'), nullable=True)
    
    # Relationships
    container_type = relationship("ContainerType", back_populates="containers")
    parent_container = relationship("Container", remote_side=[BaseModel.id], back_populates="child_containers")
    child_containers = relationship("Container", back_populates="parent_container")
    contents = relationship("Contents", back_populates="container")
    batches = relationship("Batch", secondary="batch_containers", back_populates="containers")


class Contents(BaseModel):
    __tablename__ = 'contents'
    
    container_id = Column(PostgresUUID(as_uuid=True), ForeignKey('containers.id'), primary_key=True)
    sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), primary_key=True)
    concentration = Column(Numeric(15, 6))
    concentration_units = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'))
    amount = Column(Numeric(15, 6))
    amount_units = Column(PostgresUUID(as_uuid=True), ForeignKey('units.id'))
    
    # Relationships
    container = relationship("Container", back_populates="contents")
    sample = relationship("Sample", back_populates="contents")
