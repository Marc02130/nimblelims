"""
Dose-response curve fitting models.

dose_response_results  — IC50/EC50 fit results with versioning + review workflow
experiment_data_exclusions — soft knockout audit trail (DELETE row to reverse)
"""
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class CurveCategory(str, enum.Enum):
    SIGMOID      = "SIGMOID"
    INACTIVE     = "INACTIVE"
    INVERSE      = "INVERSE"
    PARTIAL_HIGH = "PARTIAL_HIGH"
    PARTIAL_LOW  = "PARTIAL_LOW"
    HOOK_EFFECT  = "HOOK_EFFECT"
    NOISY        = "NOISY"
    CANNOT_FIT   = "CANNOT_FIT"


class ReviewStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"
    flagged  = "flagged"


class DoseResponseResult(Base):
    """
    One fit result per compound per experiment run.

    Versioning:
        Re-fit after knockout creates a new row (fit_version + 1).
        Old row: superseded_by = new row id.
        The Curve Curator grid shows only rows WHERE superseded_by IS NULL.
        Historical versions accessible via GET /results/{result_id} directly.
    """
    __tablename__ = 'dose_response_results'

    id                = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_run_id = Column(PostgresUUID(as_uuid=True), ForeignKey('experiment_runs.id'), nullable=False, index=True)
    sample_id         = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), nullable=False, index=True)
    model             = Column(String(10), nullable=False)  # '4PL', '3PL_FB', '3PL_FT', '5PL'

    # Fit parameters
    potency      = Column(Numeric(), nullable=True)
    potency_type = Column(String(4), nullable=False, default='IC50')
    hill_slope   = Column(Numeric(), nullable=True)
    top          = Column(Numeric(), nullable=True)
    bottom       = Column(Numeric(), nullable=True)
    r_squared    = Column(Numeric(), nullable=True)
    ci_low_95    = Column(Numeric(), nullable=True)
    ci_high_95   = Column(Numeric(), nullable=True)
    ci_method    = Column(String(10), nullable=True)  # 'profiled' or 'vcov'

    # Classification
    curve_category = Column(
        SAEnum(CurveCategory, name='curve_category_enum', create_type=False),
        nullable=False,
    )
    quality_flag = Column(String(20), nullable=False)

    # Point accounting
    points_used     = Column(Integer(), nullable=True)
    points_excluded = Column(Integer(), nullable=True)

    # Visualization
    thumbnail_svg = Column(Text(), nullable=True)

    # Review workflow
    review_status = Column(
        SAEnum(ReviewStatus, name='review_status_enum', create_type=False),
        nullable=False,
        default=ReviewStatus.pending,
    )
    reviewed_by   = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at   = Column(DateTime(timezone=True), nullable=True)
    review_notes  = Column(Text(), nullable=True)

    # Fit versioning
    fit_version  = Column(Integer(), nullable=False, default=1)
    superseded_by = Column(PostgresUUID(as_uuid=True), ForeignKey('dose_response_results.id'), nullable=True)

    # Audit
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fit_triggered_at  = Column(DateTime(timezone=True), nullable=True)
    fit_triggered_by  = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # RLS
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)


class ExperimentDataExclusion(Base):
    """
    Soft knockout: excludes a single experiment_data point from curve fitting.

    Reversal: DELETE this row (soft exclusion, hard reversal — no deleted_at).
    The unique constraint on experiment_data_id prevents double-exclusion.
    """
    __tablename__ = 'experiment_data_exclusions'

    id                  = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_data_id  = Column(PostgresUUID(as_uuid=True), ForeignKey('experiment_data.id'), nullable=False, index=True)
    excluded_by         = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    excluded_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason              = Column(Text(), nullable=True)
    client_id           = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
