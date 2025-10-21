from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Batch(Base):
    __tablename__ = 'batches'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Batch-specific fields
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # Relationships
    containers = relationship("Container", secondary="batch_containers", back_populates="batches")


class BatchContainer(Base):
    __tablename__ = 'batch_containers'
    
    batch_id = Column(PostgresUUID(as_uuid=True), ForeignKey('batches.id'), primary_key=True)
    container_id = Column(PostgresUUID(as_uuid=True), ForeignKey('containers.id'), primary_key=True)
    position = Column(String(50))
    notes = Column(String)
