"""Pydantic schemas for Experiment Entries (Phase 2)."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


class EntryFieldDefinitionLink(BaseModel):
    field_definition_id: UUID
    sort_order: int = 0
    visible: bool = True
    write_back_target: Optional[str] = None

    class Config:
        from_attributes = True


class EntryFieldDefinitionLinkCreate(BaseModel):
    field_definition_id: UUID
    sort_order: Optional[int] = 0
    visible: bool = True
    write_back_target: Optional[str] = Field(
        None,
        description="Allowlisted Sample column for write-back (e.g. specimen_biotype_id)",
    )


class EntryCreate(BaseModel):
    experiment_id: UUID
    entry_type: str = Field(
        ...,
        description="predefined_action | sample_data | experiment_detail | display_table",
    )
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    predefined_entry_key: Optional[str] = None
    sort_order: Optional[int] = 0
    config: Optional[Dict[str, Any]] = None
    process_step_id: Optional[UUID] = None
    fields: Optional[List[EntryFieldDefinitionLinkCreate]] = None


class EntryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    process_step_id: Optional[UUID] = None


class EntryFieldValueRead(BaseModel):
    id: UUID
    entry_id: UUID
    field_definition_id: UUID
    sample_id: Optional[UUID] = None
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_list_entry_id: Optional[UUID] = None
    value_date: Optional[datetime] = None
    value_boolean: Optional[bool] = None
    value_json: Optional[Any] = None
    write_back_at: Optional[datetime] = None
    write_back_previous: Optional[Any] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class EntryRead(BaseModel):
    id: UUID
    experiment_id: UUID
    process_step_id: Optional[UUID] = None
    entry_type: str
    name: str
    description: Optional[str] = None
    predefined_entry_key: Optional[str] = None
    sort_order: int
    config: Optional[Dict[str, Any]] = None
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None
    field_definition_links: List[EntryFieldDefinitionLink] = Field(default_factory=list)
    values: List[EntryFieldValueRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class EntryListResponse(BaseModel):
    entries: List[EntryRead]
    total: int


class EntryFieldValueUpsert(BaseModel):
    field_definition_id: UUID
    sample_id: Optional[UUID] = None
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_list_entry_id: Optional[UUID] = None
    value_date: Optional[datetime] = None
    value_boolean: Optional[bool] = None
    value_json: Optional[Any] = None
    # When true (default), apply write-back if the field link has write_back_target
    apply_write_back: bool = True


class EntryFieldValueBulkUpsert(BaseModel):
    values: List[EntryFieldValueUpsert] = Field(..., min_length=1)


class InstantiateEntriesRequest(BaseModel):
    """Instantiate entries declared on the experiment's template (or provided defs)."""
    process_step_id: Optional[UUID] = None
    # If true, skip if experiment already has entries
    skip_if_exists: bool = True


class TemplateEntryDeclaration(BaseModel):
    """Shape stored in ExperimentTemplate.template_definition['entries']."""
    entry_type: str
    name: str
    description: Optional[str] = None
    predefined_entry_key: Optional[str] = None
    sort_order: int = 0
    config: Optional[Dict[str, Any]] = None
    fields: Optional[List[EntryFieldDefinitionLinkCreate]] = None
