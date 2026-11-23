"""Response schemas for calculation configuration (calculations S7)."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas._instants import APIModel as BaseModel


class CalculationConfigurationResponse(BaseModel):
    analysis_id: UUID
    analyte_id: UUID
    analysis_version: int = Field(..., description="The analysis version after this change")
    calculation_order: Optional[int] = None
    state: Optional[str] = Field(None, description="draft or active")
    name: Optional[str] = None
    version: Optional[int] = Field(None, description="The configuration's own integer version")
    configuration: Optional[Dict[str, Any]] = None


class NewAnalysisVersionResponse(BaseModel):
    analysis_id: UUID
    previous_version: int
    analysis_version: int
    drafted_analyte_ids: List[UUID]


class AnalysisVersionSummary(BaseModel):
    analysis_id: UUID
    version: int
    created_at: datetime
    created_by: Optional[UUID] = None


class AnalysisVersionDetail(AnalysisVersionSummary):
    snapshot: Dict[str, Any]


class CalculationFormulaResponse(BaseModel):
    id: UUID
    name: str
    version: int
    formula_text: str
    description: Optional[str] = None
    terms: List[str] = Field(default_factory=list)
    created_at: datetime
    created_by: Optional[UUID] = None


class FormulaEvaluationResponse(BaseModel):
    value: Optional[str] = None
    error: Optional[str] = Field(None, description="#DIV/0!, #VALUE!, #N/A, or #NUM!")
    detail: str = ""


class CatalogEntryResponse(BaseModel):
    name: str
    version: int
    side: str
    description: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    required_inputs: List[str]
    stop_rule: str
    missing_data_rule: str
    failure_stops: List[str]
