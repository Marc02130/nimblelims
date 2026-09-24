"""Pydantic schemas for UI schema DDL registries."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


SCREEN_KEYS = ("receive", "samples.detail", "samples.list")
P1_TYPES = ("text", "numeric", "integer", "boolean", "date", "timestamptz", "list")
SOP_HINTS = ("barcode", "container", "parent", "sample_type")


class SchemaTableRead(BaseModel):
    id: UUID
    client_id: UUID
    display_name: str
    physical_name: str
    kind: str
    status: str
    column_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class SchemaTableCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    physical_name: Optional[str] = Field(None, max_length=63)


class SchemaColumnRead(BaseModel):
    id: UUID
    table_id: UUID
    display_name: str
    physical_name: str
    data_type: str
    nullable: bool
    list_id: Optional[UUID] = None
    sop_hint: Optional[str] = None
    sort_order: int
    status: str
    is_platform: bool
    is_identity: bool

    class Config:
        from_attributes = True


class SchemaColumnCreate(BaseModel):
    table_id: UUID
    display_name: str = Field(..., min_length=1, max_length=255)
    physical_name: Optional[str] = Field(None, max_length=63)
    data_type: Literal["text", "numeric", "integer", "boolean", "date", "timestamptz", "list"]
    nullable: bool = True
    list_id: Optional[UUID] = None
    sop_hint: Optional[Literal["barcode", "container", "parent", "sample_type"]] = None
    sort_order: int = 0


class ConfirmBody(BaseModel):
    confirm: bool = False


class LayoutFieldIn(BaseModel):
    column_id: UUID
    section: Optional[str] = None
    sort_order: int = 0


class SchemaLayoutPut(BaseModel):
    role_id: UUID
    screen_key: str
    fields: List[LayoutFieldIn] = Field(default_factory=list)


class SchemaLayoutRead(BaseModel):
    id: UUID
    role_id: UUID
    screen_key: str
    fields: List[Dict[str, Any]] = Field(default_factory=list)


class PrivilegeIn(BaseModel):
    role_id: UUID
    table_id: UUID
    column_id: Optional[UUID] = None
    access: Literal["read", "write", "none", "inherit"]


class SchemaPrivilegeRead(BaseModel):
    id: UUID
    role_id: UUID
    table_id: UUID
    column_id: Optional[UUID] = None
    access: str

    class Config:
        from_attributes = True


class RuntimeColumn(BaseModel):
    id: UUID
    physical_name: str
    display_name: str
    data_type: str
    on_layout: bool
    can_read: bool
    can_write: bool
    sort_order: int
    section: Optional[str] = None
