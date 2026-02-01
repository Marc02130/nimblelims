"""
Pydantic schemas for name templates
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime


VALID_PLACEHOLDERS = ['{SEQ}', '{YYYY}', '{YY}', '{MM}', '{DD}', '{YYYYMMDD}', '{CLIENT}', '{CLIABV}', '{BATCH}', '{PROJECT}']


class NameTemplateBase(BaseModel):
    """Base schema for name template data"""
    entity_type: str = Field(..., min_length=1, max_length=50, description="Entity type (sample, project, batch, analysis, container)")
    template: str = Field(..., min_length=1, max_length=500, description="Template string with placeholders")
    description: Optional[str] = Field(None, description="Description of the template")
    active: bool = Field(True, description="Whether the template is active")
    seq_padding_digits: int = Field(1, ge=1, description="Number of digits for {SEQ} padding (1 = no padding)")

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type is one of the supported types"""
        allowed_types = ['sample', 'project', 'batch', 'analysis', 'container']
        if v.lower() not in allowed_types:
            raise ValueError(f"entity_type must be one of: {', '.join(allowed_types)}")
        return v.lower()

    @validator('template')
    def validate_template(cls, v):
        """Validate template contains valid placeholders"""
        valid_placeholders = VALID_PLACEHOLDERS
        # Check if template contains at least one valid placeholder or is a simple string
        if not any(ph in v for ph in valid_placeholders) and '{' in v:
            # Contains invalid placeholder
            invalid_placeholders = []
            import re
            matches = re.findall(r'\{[^}]+\}', v)
            for match in matches:
                if match not in valid_placeholders:
                    invalid_placeholders.append(match)
            if invalid_placeholders:
                raise ValueError(f"Invalid placeholders found: {', '.join(invalid_placeholders)}. Valid placeholders: {', '.join(valid_placeholders)}")
        return v


class NameTemplateCreate(NameTemplateBase):
    """Schema for creating a new name template"""
    pass


class NameTemplateUpdate(BaseModel):
    """Schema for updating a name template"""
    entity_type: Optional[str] = Field(None, min_length=1, max_length=50)
    template: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    active: Optional[bool] = None
    seq_padding_digits: Optional[int] = Field(None, ge=1)

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type is one of the supported types"""
        if v is None:
            return v
        allowed_types = ['sample', 'project', 'batch', 'analysis', 'container']
        if v.lower() not in allowed_types:
            raise ValueError(f"entity_type must be one of: {', '.join(allowed_types)}")
        return v.lower()

    @validator('template')
    def validate_template(cls, v):
        """Validate template contains valid placeholders"""
        if v is None:
            return v
        valid_placeholders = VALID_PLACEHOLDERS
        if not any(ph in v for ph in valid_placeholders) and '{' in v:
            import re
            matches = re.findall(r'\{[^}]+\}', v)
            invalid_placeholders = [m for m in matches if m not in valid_placeholders]
            if invalid_placeholders:
                raise ValueError(f"Invalid placeholders found: {', '.join(invalid_placeholders)}. Valid placeholders: {', '.join(valid_placeholders)}")
        return v


class NameTemplateResponse(NameTemplateBase):
    """Schema for name template response"""
    id: UUID
    created_at: datetime
    modified_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class NameTemplateListResponse(BaseModel):
    """Schema for paginated name template list response"""
    templates: list[NameTemplateResponse]
    total: int
    page: int
    size: int
    pages: int

