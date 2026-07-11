"""
Pydantic schemas for ELN Process instances (Phase 1–3).

Distinct from lims_run_checklist schemas (checklist inside a LimsRun).
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

from models.entry import STEP_KINDS, EXECUTION_MODES


# ---------- Steps ----------


class ELNProcessStepCreate(BaseModel):
    experiment_template_id: UUID
    step_kind: str = Field(default='eln_experiment')
    execution_mode: Optional[str] = None
    name: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)

    @field_validator('step_kind')
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in STEP_KINDS:
            raise ValueError(f"step_kind must be one of {sorted(STEP_KINDS)}")
        return v


class ELNProcessStepUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    experiment_template_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    current_lims_run_id: Optional[UUID] = None
    sort_order: Optional[int] = Field(None, ge=0)
    step_kind: Optional[str] = None
    execution_mode: Optional[str] = None


class ELNProcessStepRead(BaseModel):
    id: UUID
    process_id: UUID
    step_kind: str = 'eln_experiment'
    execution_mode: str = 'eln_experiment'
    experiment_template_id: UUID
    experiment_id: Optional[UUID] = None
    current_lims_run_id: Optional[UUID] = None
    name: Optional[str] = None
    sort_order: int
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ELNProcessStepReorderRequest(BaseModel):
    step_ids: List[UUID] = Field(..., min_length=1)


class ELNProcessStepInstantiateRequest(BaseModel):
    """Start/materialize a step (Experiment or LimsRun)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    # For lims_run retest: create a new run even if one exists
    force_new: bool = False


class ELNProcessStepStartResponse(BaseModel):
    step: ELNProcessStepRead
    experiment_id: Optional[UUID] = None
    lims_run_id: Optional[UUID] = None
    warning: Optional[str] = None


# ---------- Samples ----------


class ELNProcessSampleAssignRequest(BaseModel):
    sample_ids: List[UUID] = Field(..., min_length=1)
    set_to_first_step: bool = True


class ELNProcessSampleRead(BaseModel):
    id: UUID
    process_id: UUID
    sample_id: UUID
    status: str
    current_step_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ELNProcessSampleSetStepRequest(BaseModel):
    step_id: Optional[UUID] = None
    status: Optional[str] = None


class ELNProcessSampleAdvanceResponse(BaseModel):
    sample: ELNProcessSampleRead
    warning: Optional[str] = None
    # Soft gate: true if advanced despite incomplete LimsRun step
    advanced: bool = True


# ---------- Process instance ----------


class ELNProcessCreate(BaseModel):
    """
    Create instance. Prefer process_definition_id (Decision #6).
    Free-form steps still allowed: auto-creates a snapshot definition.
    """
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status_id: Optional[UUID] = None
    process_definition_id: Optional[UUID] = None
    steps: Optional[List[ELNProcessStepCreate]] = None


class ELNProcessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    status_id: Optional[UUID] = None


class ELNProcessRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    status_id: Optional[UUID] = None
    process_definition_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None
    steps: List[ELNProcessStepRead] = Field(default_factory=list)
    process_samples: List[ELNProcessSampleRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ELNProcessListEntry(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    status_id: Optional[UUID] = None
    process_definition_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    step_count: int = 0
    sample_count: int = 0

    class Config:
        from_attributes = True


class ELNProcessListResponse(BaseModel):
    processes: List[ELNProcessListEntry]
    total: int
    page: int
    size: int
    pages: int


# ---------- Sample journey (#7) ----------


class SampleJourneyStep(BaseModel):
    process_id: UUID
    process_name: str
    process_definition_id: Optional[UUID] = None
    process_sample_status: str
    current_step_id: Optional[UUID] = None
    current_step_name: Optional[str] = None
    current_step_kind: Optional[str] = None
    current_step_sort_order: Optional[int] = None
    experiment_id: Optional[UUID] = None
    lims_run_id: Optional[UUID] = None
    lims_run_status: Optional[str] = None


class SampleJourneyResponse(BaseModel):
    sample_id: UUID
    processes: List[SampleJourneyStep] = Field(default_factory=list)
