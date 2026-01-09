from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class NameTemplate(BaseModel):
    __tablename__ = 'name_templates'
    
    # Name template-specific fields
    entity_type = Column(String(50), nullable=False)
    template = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys="NameTemplate.created_by", back_populates="created_name_templates")
    modifier = relationship("User", foreign_keys="NameTemplate.modified_by", back_populates="modified_name_templates")
    
    # Exclude name from mapper since name_templates table doesn't have a name column
    __mapper_args__ = {
        'exclude_properties': ['name']
    }

