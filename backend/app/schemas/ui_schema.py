"""Pydantic schemas for UI schema DDL registries."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


SCREEN_KEYS = ("receive", "samples.detail", "samples.list")
P1_TYPES = ("text", "numeric", "integer", "boolean", "date", "timestamptz", "list")
# Reflected-only types: describe real columns the UI did not create. Never addable.
REFLECTED_TYPES = ("uuid", "jsonb", "other")
SOP_HINTS = ("barcode", "container", "parent", "sample_type")
TABLE_KINDS = ("core", "ui", "system")
TABLE_CATEGORIES = ("lab", "system")
CARDINALITIES = ("one_to_many", "one_to_one")


class SchemaTableRead(BaseModel):
    id: UUID
    client_id: UUID
    display_name: str
    physical_name: str
    kind: str
    category: str = "lab"
    status: str
    column_count: int = 0
    relation_count: int = 0
    can_add_columns: bool = False
    can_remove: bool = False
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
    pg_type: Optional[str] = None
    nullable: bool
    list_id: Optional[UUID] = None
    sop_hint: Optional[str] = None
    sort_order: int
    status: str
    is_platform: bool
    is_identity: bool
    is_fk: bool = False
    fk_table: Optional[str] = None
    is_unique: bool = False
    origin: str = "ui"
    is_system: bool = False
    system_reason: Optional[str] = None
    editable: bool = False

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


class SchemaRelationCreate(BaseModel):
    """Side link: ``from`` is the one side (parent); ``to`` is the child holding the key."""

    display_name: str = Field(..., min_length=1, max_length=255)
    from_table_id: UUID
    to_table_id: UUID
    fk_column_id: UUID
    cardinality: Literal["one_to_many", "one_to_one"] = "one_to_many"


class SchemaRelationRead(BaseModel):
    id: UUID
    display_name: str
    from_table_id: UUID
    from_table_name: Optional[str] = None
    from_physical_name: Optional[str] = None
    to_table_id: UUID
    to_table_name: Optional[str] = None
    to_physical_name: Optional[str] = None
    fk_column_id: UUID
    fk_column_name: Optional[str] = None
    fk_physical_name: Optional[str] = None
    cardinality: str
    status: str
    created_at: datetime


class TableKeyRead(BaseModel):
    column_id: UUID
    column_name: str
    physical_name: str
    fk_table: Optional[str] = None
    fk_table_id: Optional[UUID] = None
    fk_table_name: Optional[str] = None
    is_unique: bool = False


class TableLinksRead(BaseModel):
    table_id: UUID
    keys: List[TableKeyRead] = Field(default_factory=list)
    children: List[SchemaRelationRead] = Field(default_factory=list)
    parents: List[SchemaRelationRead] = Field(default_factory=list)


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
