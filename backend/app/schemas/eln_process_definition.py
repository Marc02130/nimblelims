"""Schemas for ELN process definitions (Phase 3)."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from models.entry import STEP_KINDS, EXECUTION_MODES


class ELNProcessDefinitionStepCreate(BaseModel):
    experiment_template_id: UUID
    step_kind: str = Field(default='eln_experiment', description='eln_experiment | lims_run')
    execution_mode: Optional[str] = Field(
        None,
        description="Defaults to step_kind if omitted",
    )
    name: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)

    @field_validator('step_kind')
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in STEP_KINDS:
            raise ValueError(f"step_kind must be one of {sorted(STEP_KINDS)}")
        return v

    @field_validator('execution_mode')
    @classmethod
    def _mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in EXECUTION_MODES:
            raise ValueError(f"execution_mode must be one of {sorted(EXECUTION_MODES)}")
        return v


class ELNProcessDefinitionStepRead(BaseModel):
    id: UUID
    process_definition_id: UUID
    step_kind: str
    execution_mode: str
    experiment_template_id: UUID
    name: Optional[str] = None
    sort_order: int
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ELNProcessDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    steps: Optional[List[ELNProcessDefinitionStepCreate]] = None


class ELNProcessDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None


class ELNProcessDefinitionRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None
    steps: List[ELNProcessDefinitionStepRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ELNProcessDefinitionListEntry(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    step_count: int = 0

    class Config:
        from_attributes = True


class ELNProcessDefinitionListResponse(BaseModel):
    definitions: List[ELNProcessDefinitionListEntry]
    total: int
    page: int
    size: int
    pages: int


class InstantiateProcessFromDefinitionRequest(BaseModel):
    """Start a process instance from a definition (snapshot steps)."""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Instance name; default derived from definition + short id",
    )
    description: Optional[str] = None
    status_id: Optional[UUID] = None
    sample_ids: Optional[List[UUID]] = None
    set_to_first_step: bool = True
