"""
Custom Attributes Configuration model for EAV support
"""
from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class CustomAttributeConfig(BaseModel):
    """Model for custom attribute configuration"""
    __tablename__ = 'custom_attributes_config'
    
    # Custom attribute configuration fields
    entity_type = Column(String(255), nullable=False, index=True)
    attr_name = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)  # text, number, date, boolean, select
    validation_rules = Column(JSONB, nullable=True, server_default='{}')
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default='true', index=True)
    
    # Relationships
    creator = relationship("User", foreign_keys="CustomAttributeConfig.created_by", back_populates="created_custom_attribute_configs")
    modifier = relationship("User", foreign_keys="CustomAttributeConfig.modified_by", back_populates="modified_custom_attribute_configs")
    
    __mapper_args__ = {
        'exclude_properties': ['name']  # Exclude name column from BaseModel since this table uses attr_name
    }
    
    __table_args__ = (
        {'comment': 'Configuration for custom attributes in EAV pattern'},
    )

