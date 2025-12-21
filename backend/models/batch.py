from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel, Base


class Batch(BaseModel):
    __tablename__ = 'batches'
    
    # Batch-specific fields
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Relationships
    containers = relationship("Container", secondary="batch_containers", back_populates="batches")
    batch_containers = relationship("BatchContainer", back_populates="batch")
    creator = relationship("User", foreign_keys="Batch.created_by", back_populates="created_batches")
    modifier = relationship("User", foreign_keys="Batch.modified_by", back_populates="modified_batches")


class BatchContainer(Base):  # Changed from BaseModel
    __tablename__ = 'batch_containers'
    
    batch_id = Column(PostgresUUID(as_uuid=True), ForeignKey('batches.id'), primary_key=True)
    container_id = Column(PostgresUUID(as_uuid=True), ForeignKey('containers.id'), primary_key=True)
    position = Column(String(50), nullable=True)
    notes = Column(String, nullable=True)
    
    # Relationships
    batch = relationship("Batch", back_populates="batch_containers")
    container = relationship("Container", back_populates="batch_containers")