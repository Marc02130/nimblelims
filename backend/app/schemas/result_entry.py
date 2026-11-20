"""Schemas for LIMS-run result-entry rows (calculations S6)."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.schemas._instants import APIModel as BaseModel


class ResultEntryRead(BaseModel):
    id: UUID
    entry_id: UUID
    lims_run_id: UUID
    test_id: UUID
    sample_id: UUID
    sample_name: Optional[str] = None
    analyte_id: UUID
    analyte_name: Optional[str] = None
    replicate: int
    raw_result: Optional[str] = None
    raw_units: Optional[str] = None
    raw_origin: Optional[str] = None
    final_units_id: Optional[UUID] = None
    calculated_result: Optional[str] = None
    reported_result: Optional[str] = None
    qualifiers: Optional[UUID] = None
    knocked_out: bool = False
    knocked_out_by: Optional[UUID] = None
    knocked_out_at: Optional[datetime] = None
    display_order: Optional[int] = None
    modified_at: Optional[datetime] = None
    modified_by: Optional[UUID] = None


class ResultEntryListResponse(BaseModel):
    result_entries: List[ResultEntryRead]
    total: int
    page: int
    size: int
    pages: int
