"""Pydantic schemas for Experiment Entries (P0 foundation)."""
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
        description="Sample column for write-back on entry submit (config-eligible allowlist)",
    )


class EntryCreate(BaseModel):
    experiment_id: UUID
    entry_type: str = Field(
        ...,
        description=(
            "experiment_sample_data | experiment_data | predefined_action | display_table "
            "(legacy: sample_data, experiment_detail)"
        ),
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
    row_key: Optional[str] = None
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
    row_key: Optional[str] = Field(
        None,
        max_length=64,
        description="Stable row id for multi-row experiment_data tables",
    )
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_list_entry_id: Optional[UUID] = None
    value_date: Optional[datetime] = None
    value_boolean: Optional[bool] = None
    value_json: Optional[Any] = None
    # Save path defaults False; submit applies write-back server-side
    apply_write_back: bool = False


class EntryFieldValueBulkUpsert(BaseModel):
    values: List[EntryFieldValueUpsert] = Field(..., min_length=1)


class InstantiateEntriesRequest(BaseModel):
    """Instantiate entries declared on the experiment's template (or provided defs)."""
    process_step_id: Optional[UUID] = None
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


# --- Grid (wide UI) ---

class EntryGridColumn(BaseModel):
    key: str
    kind: str  # sample_field | field_definition
    field_definition_id: Optional[UUID] = None
    label: str
    data_type: str
    editable: bool = True
    sort_order: int = 0
    write_back_target: Optional[str] = None


class EntryGridCell(BaseModel):
    value: Any = None
    display: Optional[str] = None
    value_type: Optional[str] = None
    value_id: Optional[UUID] = None


class EntryGridRow(BaseModel):
    row_id: Optional[str] = None
    sample_id: Optional[UUID] = None
    cells: Dict[str, EntryGridCell] = Field(default_factory=dict)


class EntryGridMeta(BaseModel):
    row_policy: str  # experiment_samples | manual
    status: str = "draft"  # draft | submitted
    empty_reason: Optional[str] = None


class EntryGridResponse(BaseModel):
    entry_id: UUID
    experiment_id: UUID
    entry_type: str
    name: str
    columns: List[EntryGridColumn]
    rows: List[EntryGridRow]
    row_count: int
    meta: EntryGridMeta


# --- Export (long / report) ---

class EntryExportRow(BaseModel):
    experiment_id: UUID
    experiment_name: Optional[str] = None
    entry_id: UUID
    entry_name: str
    entry_type: str
    sample_id: Optional[UUID] = None
    client_sample_id: Optional[str] = None
    field_definition_id: Optional[UUID] = None
    field_name: str
    field_display_name: str
    column_kind: str
    data_type: str
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_list_entry_id: Optional[UUID] = None
    value_list_entry_name: Optional[str] = None
    value_date: Optional[datetime] = None
    value_boolean: Optional[bool] = None
    value_json: Optional[Any] = None
    display_value: Optional[str] = None
    modified_at: Optional[datetime] = None
    modified_by: Optional[UUID] = None


class EntryExportResponse(BaseModel):
    entry_id: UUID
    rows: List[EntryExportRow]
    total: int


class EntrySubmitResponse(BaseModel):
    entry: EntryRead
    write_backs_applied: int = 0
    warning: Optional[str] = None
