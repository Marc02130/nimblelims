"""
Pydantic schemas for the flexible experiment engine.

TemplateDefinition  — strict validation of the JSONB stored in experiment_templates
LimsRun*      — CRUD schemas for lims_runs
LimsRunData*     — schemas for instrument data rows
InstrumentParser*   — schemas for parser configs
RobotWorklistConfig* — schemas for worklist configs
SopParseJob*        — schemas for SOP parse jobs
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from models.flexible_experiment import LimsRunStatus, SopParseJobStatus


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
# LimsRun schemas
# ---------------------------------------------------------------------------

class LimsRunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    experiment_template_id: uuid.UUID
    analysis_id: uuid.UUID = Field(
        ...,
        description="Required analysis for the run (import + promote).",
    )


class LimsRunUpdate(BaseModel):
    """Partial update for draft (and limited fields later)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    analysis_id: Optional[uuid.UUID] = None


class LimsRunStartRequest(BaseModel):
    """Optional body for start transition (analysis must already be set)."""
    pass


class LimsRunRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    experiment_template_id: uuid.UUID
    analysis_id: Optional[uuid.UUID] = None
    status: LimsRunStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    published_at: Optional[datetime]
    canceled_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[uuid.UUID]
    modified_at: datetime
    # Convenience for UI lifecycle buttons
    lifecycle_type: Optional[str] = None

    model_config = {"from_attributes": True}


class LimsRunListResponse(BaseModel):
    runs: List[LimsRunRead]
    total: int
    page: int
    size: int
    pages: int


# ---------------------------------------------------------------------------
# LimsRunData schemas
# ---------------------------------------------------------------------------

class LimsRunDataRow(BaseModel):
    """A single imported instrument data row."""
    container_id: Optional[uuid.UUID] = None
    well_position: Optional[str] = Field(None, max_length=10)
    sample_id: Optional[uuid.UUID] = None
    row_data: Dict[str, Any]


class LimsRunDataRead(BaseModel):
    id: uuid.UUID
    lims_run_id: uuid.UUID
    container_id: Optional[uuid.UUID]
    well_position: Optional[str]
    sample_id: Optional[uuid.UUID]
    row_data: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class LimsRunDataListResponse(BaseModel):
    rows: List[LimsRunDataRead]
    total: int
    page: int
    size: int
    pages: int


class ImportDataRequest(BaseModel):
    """Body for POST /lims-runs/{id}/import."""
    rows: List[LimsRunDataRow] = Field(..., min_length=1)


class ImportDataResponse(BaseModel):
    imported: int
    skipped: int
    rows: List[LimsRunDataRead]


# ---------------------------------------------------------------------------
# InstrumentParser schemas
# ---------------------------------------------------------------------------

class ParserColumn(BaseModel):
    model_config = {"extra": "forbid"}

    source_col: str
    field_name: str
    data_type: Literal["string", "float", "integer", "boolean"] = "string"
    unit: Optional[str] = None


class ParserConfig(BaseModel):
    """Canonical parse instructions — Decision #1 schema-first."""
    model_config = {"extra": "forbid"}

    schema_version: Literal["1"] = "1"
    delimiter: Literal[",", "\t", ";", "|"] = ","
    encoding: str = "utf-8"
    skip_rows: int = Field(default=0, ge=0)
    header_row: int = Field(default=0, ge=0)
    columns: List[ParserColumn] = Field(..., min_length=1)
    well_col: Optional[str] = Field(
        None,
        description=(
            "Optional. Source column that holds a LIMS well id (max 10 chars). "
            "Omit (null) when the file has no wells — not required for every instrument."
        ),
    )
    sample_col: Optional[str] = Field(
        None,
        description="Optional. Source column that holds a sample label (metadata hint only).",
    )


class InstrumentParserCreate(BaseModel):
    """Legacy template parser create — deprecated; use /v1/data-parsers."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parser_config: ParserConfig


class InstrumentParserRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    parser_config: Dict[str, Any]
    version: Optional[int] = None
    active: Optional[bool] = None
    instrument_id: Optional[uuid.UUID] = None
    cro_source_id: Optional[uuid.UUID] = None
    version_group_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FileImportRequest(BaseModel):
    """Metadata for multipart file import on a run."""
    instrument_id: Optional[uuid.UUID] = None
    cro_source_id: Optional[uuid.UUID] = None
    parser_id: Optional[uuid.UUID] = None



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
