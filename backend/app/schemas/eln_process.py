"""
Pydantic schemas for ELN Processes (Phase 1).

Distinct from LIMS experiment_process schemas (run sub-checklists).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ---------- Steps ----------


class ELNProcessStepCreate(BaseModel):
    experiment_template_id: UUID
    name: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0, description="If omitted, appended after last step")


class ELNProcessStepUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    experiment_template_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    sort_order: Optional[int] = Field(None, ge=0)


class ELNProcessStepRead(BaseModel):
    id: UUID
    process_id: UUID
    experiment_template_id: UUID
    experiment_id: Optional[UUID] = None
    name: Optional[str] = None
    sort_order: int
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ELNProcessStepReorderRequest(BaseModel):
    """Ordered list of step IDs; becomes sort_order 0..n-1."""
    step_ids: List[UUID] = Field(..., min_length=1)


# ---------- Samples ----------


class ELNProcessSampleAssignRequest(BaseModel):
    sample_ids: List[UUID] = Field(..., min_length=1)
    # If true (default), set current_step to first step when process has steps
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
    step_id: Optional[UUID] = Field(
        None,
        description="Target step; null clears current step",
    )
    status: Optional[str] = Field(
        None,
        description="Optional status override (assigned|in_progress|completed)",
    )


# ---------- Process ----------


class ELNProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status_id: Optional[UUID] = None
    # Optional initial steps (template refs)
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
