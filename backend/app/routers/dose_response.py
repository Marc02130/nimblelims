"""
Dose-response curve fitting and Curve Curator review endpoints.

All endpoints require experiment:manage permission.
RLS is enforced at the DB layer via client_id on all dose-response tables.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import require_experiment_manage
from app.database import get_db
from app.schemas.dose_response import (
    BatchReviewRequest,
    DoseResponseResultDetail,
    DoseResponseResultListResponse,
    DoseResponseResultSummary,
    DoseResponseSummary,
    ExcludeRequest,
    ExclusionRead,
    FitResponse,
    ResetFitRequest,
    ReviewRequest,
)
from app.services.dose_response_fit import DoseResponseFitService
from app.services.r_calculator_client import RCalculatorClient
from models.dose_response import (
    CurveCategory,
    DoseResponseResult,
    ExperimentDataExclusion,
    ReviewStatus,
)
from models.flexible_experiment import ExperimentData, ExperimentRun
from models.user import User

router = APIRouter(prefix="/experiment-runs", tags=["dose-response"])

_r_client = RCalculatorClient()


def _get_run(run_id: uuid.UUID, db: Session) -> ExperimentRun:
    run = db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment run not found")
    return run


# ── Fit ───────────────────────────────────────────────────────────────────────

@router.post(
    "/{run_id}/dose-response/fit",
    response_model=FitResponse,
    summary="Fit dose-response curves for all compounds in a run",
)
def trigger_fit(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Synchronous. Blocks until all compounds are fitted (up to 60s).
    Returns 409 if a fit is already in progress for this run.
    Returns 422 if controls are missing or normalization is invalid.
    Returns 503 if the R calculation service is unavailable or times out.
    All results are written in a single transaction — partial writes never occur.
    """
    svc = DoseResponseFitService(db, current_user, r_client=_r_client)
    result = svc.trigger_fit(run_id)
    return FitResponse(**result)


@router.post(
    "/{run_id}/dose-response/refit/{sample_id}",
    response_model=FitResponse,
    summary="Re-fit a single compound after data point knockout",
)
def trigger_refit(
    run_id: uuid.UUID,
    sample_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Creates a new dose_response_results row (fit_version + 1).
    Old row: superseded_by = new row id.
    New row: review_status = 'pending' — scientist must re-review.
    """
    svc = DoseResponseFitService(db, current_user, r_client=_r_client)
    result = svc.trigger_refit(run_id, sample_id)
    return FitResponse(**result)


@router.post(
    "/{run_id}/dose-response/fit/reset",
    summary="Reset stale fit_in_progress flag (crash recovery)",
)
def reset_fit_in_progress(
    run_id: uuid.UUID,
    body: ResetFitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Clears fit_in_progress=True if stuck after a process crash.
    Requires a reason for audit trail. Returns 409 if already False.
    """
    import logging
    _logger = logging.getLogger(__name__)
    run = _get_run(run_id, db)
    if not run.fit_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="fit_in_progress is already False — nothing to reset.",
        )
    _logger.warning(
        "fit_in_progress reset by user",
        extra={"run_id": str(run_id), "user_id": str(current_user.id), "reason": body.reason},
    )
    run.fit_in_progress = False
    db.commit()
    return {"status": "ok", "run_id": str(run_id), "reason": body.reason}


# ── Results ───────────────────────────────────────────────────────────────────

@router.get(
    "/{run_id}/dose-response/results",
    response_model=DoseResponseResultListResponse,
    summary="List dose-response results (Curve Curator grid)",
)
def list_results(
    run_id: uuid.UUID,
    category: Optional[CurveCategory] = Query(None),
    review_status: Optional[ReviewStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Returns only the latest version per compound (superseded_by IS NULL).
    Includes thumbnail_svg for the Curve Curator grid.
    """
    _get_run(run_id, db)

    q = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.experiment_run_id == run_id,
            DoseResponseResult.superseded_by.is_(None),
        )
    )
    if category:
        q = q.filter(DoseResponseResult.curve_category == category)
    if review_status:
        q = q.filter(DoseResponseResult.review_status == review_status)

    total = q.count()
    rows  = q.order_by(DoseResponseResult.created_at).offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size

    # Attach sample names
    from models.sample import Sample
    sample_ids = [r.sample_id for r in rows]
    samples_by_id = {}
    if sample_ids:
        for s in db.query(Sample).filter(Sample.id.in_(sample_ids)).all():
            samples_by_id[s.id] = s

    results = []
    for row in rows:
        sample = samples_by_id.get(row.sample_id)
        d = DoseResponseResultSummary.from_orm(row)
        if sample:
            d.sample_name = sample.name
        results.append(d)

    return DoseResponseResultListResponse(
        results=results, total=total, page=page, size=size, pages=pages
    )


@router.get(
    "/{run_id}/dose-response/results/{result_id}",
    response_model=DoseResponseResultDetail,
    summary="Get a single result (Curve Detail view)",
)
def get_result(
    run_id: uuid.UUID,
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """Does not include thumbnail_svg — Plotly renders client-side from fit parameters."""
    result = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.id == result_id,
            DoseResponseResult.experiment_run_id == run_id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    from models.sample import Sample
    sample = db.query(Sample).filter(Sample.id == result.sample_id).first()
    detail = DoseResponseResultDetail.from_orm(result)
    if sample:
        detail.sample_name = sample.name
    return detail


@router.get(
    "/{run_id}/dose-response/results/{result_id}/svg",
    summary="Get full-size SVG for a result (PDF export hook)",
)
def get_result_svg(
    run_id: uuid.UUID,
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """Generates a full-size SVG via the R service. Not cached — generated on demand."""
    result = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.id == result_id,
            DoseResponseResult.experiment_run_id == run_id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    from models.sample import Sample
    from models.list import ListEntry
    from models.template_well import TemplateWellDefinition
    from app.services.dose_response_fit import DoseResponseFitService

    sample = db.query(Sample).filter(Sample.id == result.sample_id).first()
    run = _get_run(run_id, db)

    well_defs = {
        wd.well_position: wd
        for wd in db.query(TemplateWellDefinition)
        .filter(TemplateWellDefinition.template_id == run.experiment_template_id)
        .all()
    }

    # Load the original data points (non-excluded) from experiment_data
    excluded_ids = {
        str(exc.experiment_data_id)
        for exc in db.query(ExperimentDataExclusion)
        .join(ExperimentData, ExperimentDataExclusion.experiment_data_id == ExperimentData.id)
        .filter(ExperimentData.experiment_run_id == run_id)
        .all()
    }
    data_rows = (
        db.query(ExperimentData)
        .filter(
            ExperimentData.experiment_run_id == run_id,
            ExperimentData.sample_id == result.sample_id,
        )
        .all()
    )

    # Compute % inhibition normalization from run's control wells
    template_def = (run.experiment_template.template_definition or {})
    dr_config = template_def.get("dose_response_config", {})
    result_col = dr_config.get("result_column")

    all_run_rows = (
        db.query(ExperimentData)
        .filter(ExperimentData.experiment_run_id == run_id)
        .all()
    )
    all_sample_ids = {r.sample_id for r in all_run_rows if r.sample_id}
    samples_map = {s.id: s for s in db.query(Sample).filter(Sample.id.in_(all_sample_ids)).all()} if all_sample_ids else {}
    qc_entries = db.query(ListEntry).filter(ListEntry.name.in_(["positive_control", "negative_control"])).all()
    qc_by_id = {e.id: e.name for e in qc_entries}

    pos_signals: list = []
    neg_signals: list = []
    for r in all_run_rows:
        if not r.sample_id:
            continue
        if str(r.id) in excluded_ids:
            continue
        s = samples_map.get(r.sample_id)
        if not s:
            continue
        sig = DoseResponseFitService._extract_signal(r, result_col)
        if sig is None:
            continue
        qc_name = qc_by_id.get(s.qc_type)
        if qc_name == "positive_control":
            pos_signals.append(sig)
        elif qc_name == "negative_control":
            neg_signals.append(sig)

    if pos_signals and neg_signals:
        pos_mean = sum(pos_signals) / len(pos_signals)
        neg_mean = sum(neg_signals) / len(neg_signals)
        if pos_mean != neg_mean:
            def _norm(sig: float) -> float:
                return (sig - neg_mean) / (pos_mean - neg_mean) * 100.0
        else:
            def _norm(sig: float) -> float:
                return sig
    else:
        def _norm(sig: float) -> float:
            return sig

    points = []
    for row in data_rows:
        wd = well_defs.get(row.well_position or "")
        if not wd or wd.concentration_value is None:
            continue
        sig = DoseResponseFitService._extract_signal(row, result_col)
        points.append({
            "conc": float(wd.concentration_value),
            "response": _norm(sig) if sig is not None else 0.0,
            "point_id": str(row.id),
        })

    svg = _r_client.full_svg(
        points=points,
        model=result.model,
        excluded_point_ids=list(excluded_ids),
        x_label=f"Concentration",
        y_label="% Inhibition",
        title=sample.name if sample else str(result.sample_id),
    )
    from fastapi.responses import Response
    return Response(content=svg, media_type="image/svg+xml")


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get(
    "/{run_id}/dose-response/summary",
    response_model=DoseResponseSummary,
    summary="Curve Curator summary (category counts, review status, IC50 range)",
)
def get_summary(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    run = _get_run(run_id, db)

    # Latest results only — load once, aggregate in Python (avoids 13 separate COUNT queries)
    all_latest = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.experiment_run_id == run_id,
            DoseResponseResult.superseded_by.is_(None),
        )
        .all()
    )
    total = len(all_latest)

    by_category: dict = {}
    by_review_status: dict = {}
    sigmoid_potencies: list = []
    r_squareds: list = []

    for row in all_latest:
        cat_val = row.curve_category.value if hasattr(row.curve_category, 'value') else str(row.curve_category)
        by_category[cat_val] = by_category.get(cat_val, 0) + 1
        rs_val = row.review_status.value if hasattr(row.review_status, 'value') else str(row.review_status)
        by_review_status[rs_val] = by_review_status.get(rs_val, 0) + 1
        if row.curve_category == CurveCategory.SIGMOID and row.potency is not None:
            sigmoid_potencies.append(float(row.potency))
        if row.r_squared is not None:
            r_squareds.append(float(row.r_squared))

    ic50_range = None
    if sigmoid_potencies:
        ic50_range = {"min": min(sigmoid_potencies), "max": max(sigmoid_potencies)}

    mean_r2 = sum(r_squareds) / len(r_squareds) if r_squareds else None

    return DoseResponseSummary(
        total=total,
        by_category=by_category,
        by_review_status=by_review_status,
        ic50_range=ic50_range,
        mean_r_squared=mean_r2,
        fit_in_progress=run.fit_in_progress,
    )


# ── Review ────────────────────────────────────────────────────────────────────

@router.post(
    "/{run_id}/dose-response/results/{result_id}/review",
    summary="Review a single result (approve / reject / flag)",
)
def review_result(
    run_id: uuid.UUID,
    result_id: uuid.UUID,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    from datetime import datetime, timezone
    result = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.id == result_id,
            DoseResponseResult.experiment_run_id == run_id,
            DoseResponseResult.superseded_by.is_(None),
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    result.review_status = body.status
    result.reviewed_by   = current_user.id
    result.reviewed_at   = datetime.now(timezone.utc)
    result.review_notes  = body.notes
    db.commit()
    return {"status": "ok"}


@router.post(
    "/{run_id}/dose-response/results/batch-review",
    summary="Batch-approve / batch-reject all pending results in a category",
)
def batch_review(
    run_id: uuid.UUID,
    body: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Applies status only to 'pending' results in the given category.
    Does NOT overwrite manually-approved or manually-rejected results.
    """
    from datetime import datetime, timezone
    _get_run(run_id, db)

    # Only pending, latest version, matching category
    rows = (
        db.query(DoseResponseResult)
        .filter(
            DoseResponseResult.experiment_run_id == run_id,
            DoseResponseResult.curve_category == body.category,
            DoseResponseResult.review_status == ReviewStatus.pending,
            DoseResponseResult.superseded_by.is_(None),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for row in rows:
        row.review_status = body.status
        row.reviewed_by   = current_user.id
        row.reviewed_at   = now
    db.commit()

    return {"updated": len(rows), "category": body.category, "status": body.status}


# ── Knockout ──────────────────────────────────────────────────────────────────

@router.post(
    "/data/{data_id}/exclude",
    response_model=ExclusionRead,
    summary="Exclude a data point (soft knockout)",
)
def exclude_data_point(
    data_id: uuid.UUID,
    body: ExcludeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """
    Creates an experiment_data_exclusions row.
    Unique constraint prevents double-exclusion.
    Reverse by calling DELETE /data/{data_id}/exclude.
    """
    data_row = (
        db.query(ExperimentData)
        .join(ExperimentRun, ExperimentData.experiment_run_id == ExperimentRun.id)
        .filter(ExperimentData.id == data_id)
        .first()
    )
    if not data_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment data not found")

    existing = (
        db.query(ExperimentDataExclusion)
        .filter(ExperimentDataExclusion.experiment_data_id == data_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data point is already excluded.",
        )

    exclusion = ExperimentDataExclusion(
        experiment_data_id=data_id,
        excluded_by=current_user.id,
        reason=body.reason,
        client_id=current_user.client_id,
    )
    db.add(exclusion)
    db.commit()
    db.refresh(exclusion)
    return ExclusionRead.from_orm(exclusion)


@router.delete(
    "/data/{data_id}/exclude",
    summary="Un-exclude a data point (reverse knockout)",
)
def unexclude_data_point(
    data_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
):
    """Deletes the exclusion row. Hard reversal — no soft-delete."""
    data_row = (
        db.query(ExperimentData)
        .join(ExperimentRun, ExperimentData.experiment_run_id == ExperimentRun.id)
        .filter(ExperimentData.id == data_id)
        .first()
    )
    if not data_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment data not found")

    exclusion = (
        db.query(ExperimentDataExclusion)
        .filter(ExperimentDataExclusion.experiment_data_id == data_id)
        .first()
    )
    if not exclusion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This data point has no active exclusion.",
        )

    db.delete(exclusion)
    db.commit()
    return {"status": "ok"}
