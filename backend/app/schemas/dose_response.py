from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from models.dose_response import CurveCategory, ReviewStatus


# ── Request schemas ────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    status: ReviewStatus
    notes: Optional[str] = None


class BatchReviewRequest(BaseModel):
    category: CurveCategory
    status: ReviewStatus


class ExcludeRequest(BaseModel):
    reason: Optional[str] = None


class ResetFitRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Why the fit_in_progress flag is being cleared (audit trail)")


# ── Response schemas ───────────────────────────────────────────────────────────

class DoseResponseResultSummary(BaseModel):
    """Compact result for the Curve Curator grid (includes thumbnail_svg)."""
    id:               uuid.UUID
    sample_id:        uuid.UUID
    sample_name:      Optional[str] = None
    potency:          Optional[float] = None
    potency_type:     str
    r_squared:        Optional[float] = None
    ci_low_95:        Optional[float] = None
    ci_high_95:       Optional[float] = None
    ci_method:        Optional[str] = None
    curve_category:   CurveCategory
    quality_flag:     str
    points_used:      Optional[int] = None
    points_excluded:  Optional[int] = None
    thumbnail_svg:    Optional[str] = None
    review_status:    ReviewStatus
    reviewed_by:      Optional[uuid.UUID] = None
    reviewed_at:      Optional[datetime] = None
    fit_version:      int
    superseded_by:    Optional[uuid.UUID] = None
    fit_triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DoseResponseResultDetail(BaseModel):
    """Full result for CurveDetail — no thumbnail_svg (Plotly renders client-side)."""
    id:               uuid.UUID
    sample_id:        uuid.UUID
    sample_name:      Optional[str] = None
    model:            str
    potency:          Optional[float] = None
    potency_type:     str
    hill_slope:       Optional[float] = None
    top:              Optional[float] = None
    bottom:           Optional[float] = None
    r_squared:        Optional[float] = None
    ci_low_95:        Optional[float] = None
    ci_high_95:       Optional[float] = None
    ci_method:        Optional[str] = None
    curve_category:   CurveCategory
    quality_flag:     str
    points_used:      Optional[int] = None
    points_excluded:  Optional[int] = None
    review_status:    ReviewStatus
    reviewed_by:      Optional[uuid.UUID] = None
    reviewed_at:      Optional[datetime] = None
    review_notes:     Optional[str] = None
    fit_version:      int
    superseded_by:    Optional[uuid.UUID] = None
    fit_triggered_at: Optional[datetime] = None
    created_at:       datetime

    class Config:
        from_attributes = True


class DoseResponseResultListResponse(BaseModel):
    results: List[DoseResponseResultSummary]
    total:   int
    page:    int
    size:    int
    pages:   int


class FitResponse(BaseModel):
    fitted:   int
    failed:   int
    warnings: List[str] = []
    results:  List[dict]


class DoseResponseSummary(BaseModel):
    total:           int
    by_category:     dict
    by_review_status: dict
    ic50_range:      Optional[dict] = None
    mean_r_squared:  Optional[float] = None
    fit_in_progress: bool


class ExclusionRead(BaseModel):
    id:                 uuid.UUID
    experiment_data_id: uuid.UUID
    excluded_by:        uuid.UUID
    excluded_at:        datetime
    reason:             Optional[str] = None

    class Config:
        from_attributes = True
