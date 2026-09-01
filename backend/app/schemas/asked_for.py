"""Pydantic schemas for asked-for (P1) and analysis param defs."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


PARAM_DATA_TYPES = ("number", "int", "text", "bool")
ASKED_FOR_STATUSES = ("requested", "routed", "cancelled")


class AnalysisParamDefItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    data_type: str = Field(..., description="number | int | text | bool")
    unit: Optional[str] = None
    required: bool = False
    source_list_id: Optional[UUID] = None
    allowed_values: Optional[List[Any]] = None
    sort_order: int = 0

    @model_validator(mode="after")
    def check_data_type(self):
        if self.data_type not in PARAM_DATA_TYPES:
            raise ValueError(
                f"data_type must be one of {', '.join(PARAM_DATA_TYPES)}"
            )
        return self


class AnalysisParamDefRead(AnalysisParamDefItem):
    id: UUID
    analysis_id: UUID

    class Config:
        from_attributes = True


class AnalysisParamDefsPut(BaseModel):
    items: List[AnalysisParamDefItem] = Field(default_factory=list)


class AnalysisParamDefsResponse(BaseModel):
    items: List[AnalysisParamDefRead]
    count: int


class AskedForCreate(BaseModel):
    """One operator action: one analysis + TAT + params for a set of samples."""

    sample_ids: List[UUID] = Field(default_factory=list)
    sample_id: Optional[UUID] = None
    analysis_id: UUID
    tat_days: int = Field(..., ge=1)
    params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coerce_sample_ids(self):
        ids: List[UUID] = list(self.sample_ids or [])
        if self.sample_id is not None and self.sample_id not in ids:
            ids.append(self.sample_id)
        seen = set()
        out: List[UUID] = []
        for sid in ids:
            if sid not in seen:
                seen.add(sid)
                out.append(sid)
        if not out:
            raise ValueError("sample_ids must contain at least one sample")
        self.sample_ids = out
        return self


class AskedForRead(BaseModel):
    id: UUID
    sample_id: UUID
    sample_name: Optional[str] = None
    analysis_id: UUID
    analysis_name: Optional[str] = None
    tat_days: int
    params: Dict[str, Any]
    status: str
    routed_work_order_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class AskedForListResponse(BaseModel):
    items: List[AskedForRead]
    count: int
