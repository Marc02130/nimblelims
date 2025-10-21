from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class ContainerType(Base):
    __tablename__ = 'container_types'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Container type-specific fields
    capacity = Column(Numeric(10, 3))
    material = Column(String(255))
    dimensions = Column(String(50))  # e.g., '8x12'
    preservative = Column(String(255))
    
    # Relationships
    containers = relationship("Container", back_populates="container_type")


class Container(Base):
    __tablename__ = 'containers'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
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
    parent_container = relationship("Container", remote_side=[id], back_populates="child_containers")
    child_containers = relationship("Container", back_populates="parent_container")
    contents = relationship("Contents", back_populates="container")
    batches = relationship("Batch", secondary="batch_containers", back_populates="containers")


class Contents(Base):
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
