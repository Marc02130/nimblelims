"""
Pydantic schemas for FieldDefinition
"""
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class DataType(str, Enum):
    """Enum for field data types"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"
    LOOKUP = "lookup"


class FieldDefinitionBase(BaseModel):
    """Base schema for FieldDefinition"""
    entity_type: str = Field(..., min_length=1, max_length=64, description="Entity type (e.g., 'sample', 'experiment')")
    name: str = Field(..., min_length=1, max_length=255, description="Internal name, e.g. 'specimen_biotype'")
    display_name: Optional[str] = Field(None, max_length=255, description="Human readable label")
    data_type: DataType = Field(..., description="Data type: text, number, date, boolean, list, lookup")
    source_list_id: Optional[UUID] = Field(None, description="ID of source list for list/lookup types")
    is_required: bool = Field(False, description="Whether the field is required")
    is_unique: bool = Field(False, description="Whether values must be unique")
    default_value: Optional[Dict[str, Any]] = Field(None, description="Default value")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules as JSON")
    ui_hints: Dict[str, Any] = Field(default_factory=dict, description="UI hints")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    active: bool = Field(True, description="Whether the field definition is active")
    is_materialized_column: bool = Field(True, description="Whether this is a top-level column")
    column_name: Optional[str] = Field(None, max_length=255, description="Column name if materialized")

    @validator('entity_type')
    def validate_entity_type(cls, v):
        # Allow all for now as per requirements; can restrict later
        if not v or not v.strip():
            raise ValueError("entity_type is required")
        return v.strip().lower()

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("name must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @validator('data_type')
    def validate_data_type(cls, v, values):
        # Basic validation
        return v

    @validator('validation_rules')
    def validate_validation_rules(cls, v, values):
        if not isinstance(v, dict):
            raise ValueError("validation_rules must be a dictionary")
        # Lists are the source of truth for list data_type; validation_rules for scalars (min/max etc)
        # Do not embed options here.
        return v


class FieldDefinitionCreate(FieldDefinitionBase):
    """Schema for creating a FieldDefinition"""
    pass


class FieldDefinitionUpdate(BaseModel):
    """Schema for updating a FieldDefinition"""
    entity_type: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    data_type: Optional[DataType] = None
    source_list_id: Optional[UUID] = None
    is_required: Optional[bool] = None
    is_unique: Optional[bool] = None
    default_value: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    ui_hints: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    is_materialized_column: Optional[bool] = None
    column_name: Optional[str] = None

    @validator('entity_type')
    def validate_entity_type(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("entity_type cannot be empty")
        return v.strip().lower() if v else v

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("name must contain only alphanumeric characters, underscores, and hyphens")
        return v


class FieldDefinitionResponse(FieldDefinitionBase):
    """Response schema for FieldDefinition"""
    id: UUID
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldDefinitionListResponse(BaseModel):
    """Paginated list response"""
    items: List[FieldDefinitionResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
