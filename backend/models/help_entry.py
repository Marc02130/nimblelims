"""
Help Entry model for role-filtered help content
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from .base import BaseModel


class HelpEntry(BaseModel):
    """Model for help entries with role-based filtering"""
    __tablename__ = 'help_entries'
    
    # Override name column to remove unique constraint (help entries can share sections)
    name = Column(String(255), unique=False, nullable=False)
    
    # BaseModel provides: id, description, active, created_at, created_by, modified_at, modified_by
    # name will be set from section, description can be a summary
    section = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    role_filter = Column(String(255), nullable=True)  # NULL = public, otherwise role name
    
    def __init__(self, **kwargs):
        # Set name from section if not provided (required by BaseModel)
        if 'name' not in kwargs and 'section' in kwargs:
            kwargs['name'] = kwargs['section']
        # Set description from content summary if not provided
        if 'description' not in kwargs and 'content' in kwargs:
            content = kwargs['content']
            kwargs['description'] = content[:255] if len(content) > 255 else content
        super().__init__(**kwargs)

