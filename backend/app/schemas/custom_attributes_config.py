"""
Pydantic schemas for custom attributes configuration
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DataType(str, Enum):
    """Enum for custom attribute data types"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"


class CustomAttributeConfigBase(BaseModel):
    """Base schema for custom attribute configuration"""
    entity_type: str = Field(..., min_length=1, max_length=255, description="Entity type (e.g., 'samples', 'tests')")
    attr_name: str = Field(..., min_length=1, max_length=255, description="Attribute name")
    data_type: DataType = Field(..., description="Data type: text, number, date, boolean, or select")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules as JSON")
    description: Optional[str] = Field(None, description="Description of the attribute")
    active: bool = Field(True, description="Whether the attribute is active")

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type is one of the supported types"""
        allowed_types = ['samples', 'tests', 'results', 'projects', 'client_projects', 'batches']
        if v not in allowed_types:
            raise ValueError(f"entity_type must be one of: {', '.join(allowed_types)}")
        return v

    @validator('attr_name')
    def validate_attr_name(cls, v):
        """Validate attribute name format"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("attr_name must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @validator('validation_rules')
    def validate_validation_rules(cls, v, values):
        """Validate validation rules based on data type"""
        if not isinstance(v, dict):
            raise ValueError("validation_rules must be a dictionary")
        
        data_type = values.get('data_type')
        if not data_type:
            return v
        
        # Validate rules based on data type
        if data_type == DataType.NUMBER:
            if 'min' in v and 'max' in v:
                if v['min'] > v['max']:
                    raise ValueError("min must be less than or equal to max")
        elif data_type == DataType.DATE:
            if 'min_date' in v and 'max_date' in v:
                try:
                    min_date = datetime.fromisoformat(v['min_date']) if isinstance(v['min_date'], str) else v['min_date']
                    max_date = datetime.fromisoformat(v['max_date']) if isinstance(v['max_date'], str) else v['max_date']
                    if min_date > max_date:
                        raise ValueError("min_date must be less than or equal to max_date")
                except (ValueError, TypeError, AttributeError):
                    raise ValueError("min_date and max_date must be valid ISO date strings (YYYY-MM-DD)")
        elif data_type == DataType.SELECT:
            if 'options' not in v or not isinstance(v['options'], list):
                raise ValueError("select data type requires 'options' list in validation_rules")
            if not v['options']:
                raise ValueError("options list cannot be empty")
        
        return v


class CustomAttributeConfigCreate(CustomAttributeConfigBase):
    """Schema for creating a custom attribute configuration"""
    pass


class CustomAttributeConfigUpdate(BaseModel):
    """Schema for updating a custom attribute configuration"""
    entity_type: Optional[str] = Field(None, min_length=1, max_length=255)
    attr_name: Optional[str] = Field(None, min_length=1, max_length=255)
    data_type: Optional[DataType] = None
    validation_rules: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    active: Optional[bool] = None

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type is one of the supported types"""
        if v is None:
            return v
        allowed_types = ['samples', 'tests', 'results', 'projects', 'client_projects', 'batches']
        if v not in allowed_types:
            raise ValueError(f"entity_type must be one of: {', '.join(allowed_types)}")
        return v

    @validator('attr_name')
    def validate_attr_name(cls, v):
        """Validate attribute name format"""
        if v is None:
            return v
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("attr_name must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @validator('validation_rules')
    def validate_validation_rules(cls, v, values):
        """Validate validation rules based on data type"""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("validation_rules must be a dictionary")
        
        data_type = values.get('data_type')
        if not data_type:
            return v
        
        # Validate rules based on data type
        if data_type == DataType.NUMBER:
            if 'min' in v and 'max' in v:
                if v['min'] > v['max']:
                    raise ValueError("min must be less than or equal to max")
        elif data_type == DataType.DATE:
            if 'min_date' in v and 'max_date' in v:
                try:
                    min_date = datetime.fromisoformat(v['min_date']) if isinstance(v['min_date'], str) else v['min_date']
                    max_date = datetime.fromisoformat(v['max_date']) if isinstance(v['max_date'], str) else v['max_date']
                    if min_date > max_date:
                        raise ValueError("min_date must be less than or equal to max_date")
                except (ValueError, TypeError, AttributeError):
                    raise ValueError("min_date and max_date must be valid ISO date strings (YYYY-MM-DD)")
        elif data_type == DataType.SELECT:
            if 'options' not in v or not isinstance(v['options'], list):
                raise ValueError("select data type requires 'options' list in validation_rules")
            if not v['options']:
                raise ValueError("options list cannot be empty")
        
        return v


class CustomAttributeConfigResponse(CustomAttributeConfigBase):
    """Schema for custom attribute configuration response"""
    id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class CustomAttributeConfigListResponse(BaseModel):
    """Schema for custom attribute configuration list response with pagination"""
    configs: List[CustomAttributeConfigResponse]
    total: int
    page: int
    size: int
    pages: int

