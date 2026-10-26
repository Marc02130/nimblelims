"""Schemas for data_parsers CRUD, versions, activate, and test suite."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, model_validator
from app.schemas._instants import APIModel as BaseModel

from app.schemas.flexible_experiment import ParserConfig


class ParserAnalysisLink(BaseModel):
    analysis_id: UUID
    is_default: bool = False


class DataParserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instrument_id: Optional[UUID] = None
    cro_source_id: Optional[UUID] = None
    instrument_type_id: Optional[UUID] = None
    parser_config: ParserConfig
    analyses: List[ParserAnalysisLink] = Field(..., min_length=1)
    activate: bool = False

    @model_validator(mode="after")
    def source_xor(self):
        n = sum(
            1
            for v in (self.instrument_id, self.cro_source_id, self.instrument_type_id)
            if v is not None
        )
        if n != 1:
            raise ValueError(
                "Exactly one of instrument_id, cro_source_id, or instrument_type_id is required"
            )
        return self


class DataParserNewVersion(BaseModel):
    """Create a new version in an existing version_group."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parser_config: ParserConfig
    analyses: List[ParserAnalysisLink] = Field(..., min_length=1)
    activate: bool = False


class DataParserRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    instrument_id: Optional[UUID]
    cro_source_id: Optional[UUID]
    instrument_type_id: Optional[UUID] = None
    version_group_id: UUID
    version: int
    active: bool
    parser_config: Dict[str, Any]
    analysis_ids: List[UUID] = []
    analyses: List[ParserAnalysisLink] = []
    instrument_name: Optional[str] = None
    cro_source_name: Optional[str] = None
    instrument_type_name: Optional[str] = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


class SetupFileMeta(BaseModel):
    id: UUID
    parser_id: Optional[UUID]
    role: str
    filename: str
    content_type: Optional[str]
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FileTestReport(BaseModel):
    filename: str
    ok: bool
    hard_errors: List[str] = []
    warnings: List[str] = []
    row_count: int = 0


class TestSuiteRequest(BaseModel):
    parser_config: ParserConfig


class TestSuiteResponse(BaseModel):
    all_clean: bool
    files: List[FileTestReport]


class LimsRunImportRead(BaseModel):
    id: UUID
    lims_run_id: UUID
    instrument_id: Optional[UUID]
    cro_source_id: Optional[UUID]
    parser_id: Optional[UUID]
    filename: Optional[str]
    note: Optional[str] = None
    imported_at: datetime
    imported_by: Optional[UUID]
    parser_name: Optional[str] = None
    parser_version: Optional[int] = None
    instrument_name: Optional[str] = None
    cro_source_name: Optional[str] = None

    model_config = {"from_attributes": True}


class UnmatchedImportRow(BaseModel):
    """A kept row that did not bind to a sample."""

    row_index: int
    well_position: Optional[str] = None
    sample_key: Optional[str] = None
    reason: str


class ImportFileResponse(BaseModel):
    imported: int
    skipped: int
    linked: int = 0
    unmatched_count: int = 0
    unmatched: List[UnmatchedImportRow] = []
    warnings: List[str] = []
    import_id: UUID
    parser_id: UUID
