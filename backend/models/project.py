from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import BaseModel, Base


class Project(BaseModel):
    __tablename__ = 'projects'
    
    # Project-specific fields
    start_date = Column(DateTime, nullable=False)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    status = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="projects")
    users = relationship(
        "User", 
        secondary="project_users", 
        primaryjoin="Project.id == project_users.c.project_id",
        secondaryjoin="User.id == project_users.c.user_id",
        back_populates="projects"
    )
    samples = relationship("Sample", back_populates="project")


class ProjectUser(Base):
    __tablename__ = 'project_users'
    
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey('projects.id'), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    access_level = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    granted_at = Column(DateTime, default=func.now())
    granted_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
