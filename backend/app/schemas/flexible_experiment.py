"""
Pydantic schemas for the flexible experiment engine.

TemplateDefinition  — strict validation of the JSONB stored in experiment_templates
ExperimentRun*      — CRUD schemas for experiment_runs
ExperimentData*     — schemas for instrument data rows
InstrumentParser*   — schemas for parser configs
RobotWorklistConfig* — schemas for worklist configs
SopParseJob*        — schemas for SOP parse jobs
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from models.flexible_experiment import ExperimentRunStatus, SopParseJobStatus


# ---------------------------------------------------------------------------
# TemplateDefinition — what the AI extracts from a SOP
# ---------------------------------------------------------------------------

class PlateLayout(BaseModel):
    """Well-plate layout extracted from SOP."""
    plate_type: Literal["96", "384"] = "96"
    wells: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of well_id → {condition, role, sample_type, ...}",
    )


class TransferStep(BaseModel):
    """A single liquid-handling transfer step extracted from SOP."""
    step: int
    source_plate: Optional[str] = None
    source_well: Optional[str] = None
    dest_plate: Optional[str] = None
    dest_well: Optional[str] = None
    volume_ul: Optional[float] = None
    mandatory_review: bool = True  # all robot-affecting fields default to requiring review


class TemplateDefinition(BaseModel):
    """
    Structured definition stored as JSONB in experiment_templates.template_definition.

    Fields that affect robot behavior (transfer steps, volumes, positions) have
    mandatory_review=True until a scientist explicitly confirms them.
    """
    experiment_name: str
    description: Optional[str] = None
    protocol_steps: List[str] = Field(default_factory=list)
    plate_layout: Optional[PlateLayout] = None
    transfer_steps: List[TransferStep] = Field(default_factory=list)
    result_columns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Expected output columns: [{name, data_type, unit}]",
    )
    acceptance_criteria: Optional[str] = None
    mandatory_review_count: int = Field(
        default=0,
        description="Number of fields that still require scientist sign-off",
    )

    @field_validator("mandatory_review_count", mode="before")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        return max(0, int(v))


# ---------------------------------------------------------------------------
# ExperimentRun schemas
# ---------------------------------------------------------------------------

class ExperimentRunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    experiment_template_id: uuid.UUID


class ExperimentRunRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    experiment_template_id: uuid.UUID
    status: ExperimentRunStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[uuid.UUID]
    modified_at: datetime

    model_config = {"from_attributes": True}


class ExperimentRunListResponse(BaseModel):
    runs: List[ExperimentRunRead]
    total: int
    page: int
    size: int
    pages: int


# ---------------------------------------------------------------------------
# ExperimentData schemas
# ---------------------------------------------------------------------------

class ExperimentDataRow(BaseModel):
    """A single imported instrument data row."""
    container_id: Optional[uuid.UUID] = None
    well_position: Optional[str] = Field(None, max_length=10)
    sample_id: Optional[uuid.UUID] = None
    row_data: Dict[str, Any]


class ExperimentDataRead(BaseModel):
    id: uuid.UUID
    experiment_run_id: uuid.UUID
    container_id: Optional[uuid.UUID]
    well_position: Optional[str]
    sample_id: Optional[uuid.UUID]
    row_data: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportDataRequest(BaseModel):
    """Body for POST /experiment-runs/{id}/import."""
    rows: List[ExperimentDataRow] = Field(..., min_length=1)


class ImportDataResponse(BaseModel):
    imported: int
    skipped: int
    rows: List[ExperimentDataRead]


# ---------------------------------------------------------------------------
# InstrumentParser schemas
# ---------------------------------------------------------------------------

class ParserColumn(BaseModel):
    source_col: str
    field_name: str
    data_type: Literal["string", "float", "integer", "boolean"] = "string"
    unit: Optional[str] = None


class ParserConfig(BaseModel):
    columns: List[ParserColumn]
    well_col: Optional[str] = Field(None, description="Column that identifies well position")
    skip_rows: int = Field(default=0, ge=0, description="Header rows to skip")


class InstrumentParserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parser_config: ParserConfig


class InstrumentParserRead(BaseModel):
    id: uuid.UUID
    experiment_template_id: uuid.UUID
    name: str
    description: Optional[str]
    parser_config: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# RobotWorklistConfig schemas
# ---------------------------------------------------------------------------

class WorklistStep(BaseModel):
    step: int
    source_plate: Optional[str] = None
    source_well_col: Optional[str] = None
    dest_plate: Optional[str] = None
    dest_well_col: Optional[str] = None
    volume_col: Optional[str] = None
    mandatory_review: bool = True


class WorklistConfig(BaseModel):
    steps: List[WorklistStep]


class RobotWorklistConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    worklist_config: WorklistConfig


class RobotWorklistConfigRead(BaseModel):
    id: uuid.UUID
    experiment_template_id: uuid.UUID
    name: str
    description: Optional[str]
    worklist_config: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SopParseJob schemas
# ---------------------------------------------------------------------------

class SopParseJobRead(BaseModel):
    id: uuid.UUID
    experiment_template_id: Optional[uuid.UUID]
    status: SopParseJobStatus
    sop_filename: Optional[str]
    instrument_filename: Optional[str]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


class SopApplyResponse(BaseModel):
    """Response from POST /sop-parse/{id}/apply — IDs of the newly created records."""
    job_id: uuid.UUID
    experiment_template_id: uuid.UUID
    instrument_parser_id: uuid.UUID
    robot_worklist_config_id: Optional[uuid.UUID]
