from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Project-specific fields
    start_date = Column(DateTime, nullable=False)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="projects")
    users = relationship("User", secondary="project_users", back_populates="projects")
    samples = relationship("Sample", back_populates="project")


class ProjectUser(Base):
    __tablename__ = 'project_users'
    
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey('projects.id'), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    access_level = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    granted_at = Column(DateTime, default=func.now())
    granted_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
