"""
Pydantic schemas for LimsRunChecklist and LimsRunChecklistStep.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from models.lims_run_checklist import LimsRunChecklistStepStatus


# ---------- LimsRunChecklistStep ----------

class LimsRunChecklistStepCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class LimsRunChecklistStepRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    checklist_id: uuid.UUID
    name: str
    description: Optional[str]
    sort_order: int
    status: LimsRunChecklistStepStatus
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    modified_at: Optional[datetime]
    modified_by: Optional[uuid.UUID]


class LimsRunChecklistStepUpdateNotes(BaseModel):
    notes: str


# ---------- LimsRunChecklist ----------

class LimsRunChecklistCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    steps: List[LimsRunChecklistStepCreate] = []


class LimsRunChecklistRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lims_run_id: uuid.UUID
    name: str
    description: Optional[str]
    sort_order: int
    created_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    modified_at: Optional[datetime]
    modified_by: Optional[uuid.UUID]
    steps: List[LimsRunChecklistStepRead] = []
