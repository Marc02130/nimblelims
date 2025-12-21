from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import BaseModel


class List(BaseModel):
    __tablename__ = 'lists'
    
    # Relationships
    entries = relationship("ListEntry", back_populates="list")


class ListEntry(BaseModel):
    __tablename__ = 'list_entries'
    
    # List entry-specific fields
    list_id = Column(PostgresUUID(as_uuid=True), ForeignKey('lists.id'), nullable=False)
    
    # Relationships
    list = relationship("List", back_populates="entries")