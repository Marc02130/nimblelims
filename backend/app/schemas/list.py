"""
Pydantic schemas for lists and list entries
"""
from app.schemas._instants import APIModel as BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from app.services.qc_controls import CONTROL_CODES


def _control_code(value):
    """None stays None. A set code is the positive or negative control role."""
    if value is None:
        return None
    if value not in CONTROL_CODES:
        raise ValueError("code must be 'positive' or 'negative'")
    return value


class ListEntryResponse(BaseModel):
    """Schema for list entry response"""
    id: UUID
    name: str
    description: Optional[str] = None
    code: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    list_id: UUID

    class Config:
        from_attributes = True


class ListEntryCreate(BaseModel):
    """Schema for creating a list entry"""
    name: str
    description: Optional[str] = None
    code: Optional[str] = None
    active: bool = True

    @field_validator("code")
    @classmethod
    def code_is_a_control_role(cls, value):
        return _control_code(value)


class ListEntryUpdate(BaseModel):
    """Schema for updating a list entry"""
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def code_is_a_control_role(cls, value):
        return _control_code(value)


class ListResponse(BaseModel):
    """Schema for list response"""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    modified_at: datetime
    entries: List[ListEntryResponse] = []

    class Config:
        from_attributes = True


class ListCreate(BaseModel):
    """Schema for creating a list"""
    name: str
    description: Optional[str] = None


class ListUpdate(BaseModel):
    """Schema for updating a list"""
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

