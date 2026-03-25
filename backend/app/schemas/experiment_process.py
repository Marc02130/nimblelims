"""
Pydantic schemas for ExperimentProcess and ProcessStep.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from models.experiment_process import ProcessStepStatus


# ---------- ProcessStep ----------

class ProcessStepCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class ProcessStepRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    process_id: uuid.UUID
    name: str
    description: Optional[str]
    sort_order: int
    status: ProcessStepStatus
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    modified_at: Optional[datetime]
    modified_by: Optional[uuid.UUID]


class ProcessStepUpdateNotes(BaseModel):
    notes: str


# ---------- ExperimentProcess ----------

class ExperimentProcessCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    steps: List[ProcessStepCreate] = []


class ExperimentProcessRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    experiment_run_id: uuid.UUID
    name: str
    description: Optional[str]
    sort_order: int
    created_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    modified_at: Optional[datetime]
    modified_by: Optional[uuid.UUID]
    steps: List[ProcessStepRead] = []
