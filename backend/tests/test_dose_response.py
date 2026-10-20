"""
Dose-response integration tests (22 cases).

Uses db_session (testcontainers PostgreSQL, create_all schema, per-test rollback).
DoseResponseFitService is tested directly for logic cases; HTTP layer tested via
the `client` fixture for review/exclusion/summary endpoints.

R calculator is always mocked via a MagicMock injected into DoseResponseFitService.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.dose_response_fit import DoseResponseFitService
from models.client import Client
from models.dose_response import CurveCategory, DoseResponseResult, LimsRunDataExclusion, ReviewStatus
from models.experiment import ExperimentTemplate
from models.flexible_experiment import LimsRunData, LimsRun, LimsRunStatus
from models.list import List, ListEntry
from models.project import Project
from models.sample import Sample
from models.template_well import TemplateWellDefinition


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_list_entry(
    db: Session,
    name: str,
    user_id: uuid.UUID,
    code: str | None = None,
) -> ListEntry:
    # list_entries.name is globally unique (BaseModel). Idle-tx tests commit
    # these rows on the shared engine; a hard-coded name then collides with
    # later tests (CI: list_entries_name_key). Control role is ``code``.
    unique = f"{name}_{uuid.uuid4().hex[:8]}"
    lst = List(name=f"list_{unique}", created_by=user_id, modified_by=user_id)
    db.add(lst)
    db.flush()
    entry = ListEntry(
        list_id=lst.id,
        name=unique,
        code=code,
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(entry)
    db.flush()
    return entry


def _make_sample(
    db: Session,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    qc_type_id: uuid.UUID | None,
) -> Sample:
    """Create a minimal Sample row with real ListEntry records for FK-constrained fields."""
    # Project requires a real list_entries.id for status
    proj_status = _make_list_entry(db, f"proj_status_{uuid.uuid4().hex[:8]}", user_id)
    proj = Project(
        name=f"proj_{uuid.uuid4().hex[:6]}",
        client_id=client_id,
        status=proj_status.id,
        start_date=datetime.utcnow(),
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(proj)
    db.flush()

    # Sample requires real list_entries.id for sample_type, status, matrix
    sample_type = _make_list_entry(db, f"stype_{uuid.uuid4().hex[:8]}", user_id)
    sample_status = _make_list_entry(db, f"sstat_{uuid.uuid4().hex[:8]}", user_id)
    sample_matrix = _make_list_entry(db, f"smatx_{uuid.uuid4().hex[:8]}", user_id)

    sample = Sample(
        name=f"s_{uuid.uuid4().hex[:6]}",
        sample_type=sample_type.id,
        status=sample_status.id,
        matrix=sample_matrix.id,
        project_id=proj.id,
        qc_type=qc_type_id,
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(sample)
    db.flush()
    return sample


def _make_template(db: Session, user_id: uuid.UUID, dr_config: dict | None = None) -> ExperimentTemplate:
    cfg = dr_config or {
        "model": "4PL",
        "normalization": "percent_inhibition",
        "result_column": "result",
        "r_squared_threshold": 0.9,
        "inactive_threshold": 20.0,
        "parameter_constraints": {},
    }
    tmpl = ExperimentTemplate(
        name=f"tmpl_{uuid.uuid4().hex[:6]}",
        template_definition={"dose_response_config": cfg},
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(tmpl)
    db.flush()
    return tmpl


def _make_run(
    db: Session,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str = "running",
    fit_in_progress: bool = False,
) -> LimsRun:
    run = LimsRun(
        name=f"run_{uuid.uuid4().hex[:6]}",
        experiment_template_id=template_id,
        status=status,
        fit_in_progress=fit_in_progress,
        created_by=user_id,
    )
    db.add(run)
    db.flush()
    return run


def _make_well(
    db: Session,
    template_id: uuid.UUID,
    client_id: uuid.UUID,
    well_position: str,
    concentration_value: float | None,
    unit: str = "uM",
) -> TemplateWellDefinition:
    wd = TemplateWellDefinition(
        template_id=template_id,
        well_position=well_position,
        concentration_value=Decimal(str(concentration_value)) if concentration_value is not None else None,
        concentration_unit=unit if concentration_value is not None else None,
        client_id=client_id,
    )
    db.add(wd)
    db.flush()
    return wd


def _make_data_row(
    db: Session,
    run_id: uuid.UUID,
    sample_id: uuid.UUID,
    well_position: str,
    signal: float,
    user_id: uuid.UUID,
) -> LimsRunData:
    row = LimsRunData(
        lims_run_id=run_id,
        sample_id=sample_id,
        well_position=well_position,
        row_data={"result": signal},
        created_by=user_id,
    )
    db.add(row)
    db.flush()
    return row


def _sigmoid_r_result(sample_id: uuid.UUID) -> dict:
    return {
        "sample_id": str(sample_id),
        "success": True,
        "curve_category": "SIGMOID",
        "potency": 0.045,
        "potency_type": "IC50",
        "hill_slope": 1.2,
        "top": 100.0,
        "bottom": 0.0,
        "r_squared": 0.97,
        "ci_low_95": 0.030,
        "ci_high_95": 0.065,
        "ci_method": "profiled",
        "quality_flag": "ok",
        "thumbnail_svg": None,
    }


def _cannot_fit_r_result(sample_id: uuid.UUID) -> dict:
    return {
        "sample_id": str(sample_id),
        "success": False,
        "curve_category": "CANNOT_FIT",
        "potency": None,
        "potency_type": "IC50",
        "hill_slope": None,
        "top": None,
        "bottom": None,
        "r_squared": None,
        "ci_low_95": None,
        "ci_high_95": None,
        "ci_method": None,
        "quality_flag": "review_required",
        "thumbnail_svg": None,
    }


# ---------------------------------------------------------------------------
# Shared fixture: full DR setup (template + run + controls + test compound)
# ---------------------------------------------------------------------------

@pytest.fixture
def dr_setup(db_session: Session, test_admin_user, test_org):
    """
    Returns a dict with everything needed for a successful trigger_fit call:
      template, run, pos_sample, neg_sample, test_sample, pos_data, neg_data, test_data
    pos_mean=100, neg_mean=0, test_signal=50 → pct_inh=50.0
    """
    user_id = test_admin_user.id
    client_id = test_org.id

    pos_entry = _make_list_entry(db_session, "positive_control", user_id, code="positive")
    neg_entry = _make_list_entry(db_session, "negative_control", user_id, code="negative")

    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)
    test_sample = _make_sample(db_session, user_id, client_id, None)  # non-control: qc_type=None

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)

    # One well per sample
    _make_well(db_session, tmpl.id, client_id, "A1", 1.0)  # test compound well
    _make_well(db_session, tmpl.id, client_id, "B1", None)  # control — no concentration

    # Data rows: 2 pos controls (signal=100), 2 neg controls (signal=0), 1 test (signal=50)
    pos1 = _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)
    pos2 = _make_data_row(db_session, run.id, pos_sample.id, "B2", 100.0, user_id)
    neg1 = _make_data_row(db_session, run.id, neg_sample.id, "C1", 0.0, user_id)
    neg2 = _make_data_row(db_session, run.id, neg_sample.id, "C2", 0.0, user_id)
    test_data = _make_data_row(db_session, run.id, test_sample.id, "A1", 50.0, user_id)

    return {
        "tmpl": tmpl, "run": run,
        "pos_sample": pos_sample, "neg_sample": neg_sample, "test_sample": test_sample,
        "pos1": pos1, "pos2": pos2, "neg1": neg1, "neg2": neg2, "test_data": test_data,
    }


# ---------------------------------------------------------------------------
# 1. trigger_fit — wrong status (draft) → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_wrong_status_draft(db_session, test_admin_user, test_org):
    tmpl = _make_template(db_session, test_admin_user.id)
    run = _make_run(db_session, tmpl.id, test_admin_user.id, status="draft")

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert "Cannot fit" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. trigger_fit — wrong status (published) → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_wrong_status_published(db_session, test_admin_user, test_org):
    tmpl = _make_template(db_session, test_admin_user.id)
    run = _make_run(db_session, tmpl.id, test_admin_user.id, status="published")

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# 3. trigger_fit — fittable status (running) passes status gate
# ---------------------------------------------------------------------------

def test_trigger_fit_fittable_status_running(db_session, test_admin_user, test_org):
    """Running status passes the status gate; fails later at control validation."""
    tmpl = _make_template(db_session, test_admin_user.id)
    run = _make_run(db_session, tmpl.id, test_admin_user.id, status="running")
    # Insert one data row to pass the no-data check (sample must be real due to FK)
    sample = _make_sample(db_session, test_admin_user.id, test_org.id, None)
    _make_data_row(db_session, run.id, sample.id, "A1", 1.0, test_admin_user.id)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    # Should fail at control validation, not status gate
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") in ("missing_positive_control", "missing_negative_control")


# ---------------------------------------------------------------------------
# 4. trigger_fit — fit_in_progress=True → 409
# ---------------------------------------------------------------------------

def test_trigger_fit_already_in_progress(db_session, test_admin_user, test_org):
    tmpl = _make_template(db_session, test_admin_user.id)
    run = _make_run(db_session, tmpl.id, test_admin_user.id, fit_in_progress=True)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 409
    assert "already in progress" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 5. trigger_fit — R service failure clears fit_in_progress in finally block
# ---------------------------------------------------------------------------

def test_trigger_fit_clears_in_progress_on_r_failure(db_session, test_admin_user, test_org, dr_setup):
    run = dr_setup["run"]
    mock_r = MagicMock()
    mock_r.fit.side_effect = HTTPException(status_code=503, detail="R service unavailable")

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 503

    # fit_in_progress must be cleared
    db_session.expire(run)
    assert run.fit_in_progress is False


# ---------------------------------------------------------------------------
# 6. trigger_fit — no positive controls → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_no_positive_controls(db_session, test_admin_user, test_org):
    user_id = test_admin_user.id
    client_id = test_org.id
    neg_entry = _make_list_entry(db_session, "negative_control", user_id, code="negative")
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 0.0, user_id)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "missing_positive_control"


# ---------------------------------------------------------------------------
# 7. trigger_fit — no negative controls → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_no_negative_controls(db_session, test_admin_user, test_org):
    user_id = test_admin_user.id
    client_id = test_org.id
    pos_entry = _make_list_entry(db_session, "positive_control", user_id, code="positive")
    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "missing_negative_control"


# ---------------------------------------------------------------------------
# 8. trigger_fit — degenerate controls (pos_mean == neg_mean) → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_degenerate_controls(db_session, test_admin_user, test_org):
    user_id = test_admin_user.id
    client_id = test_org.id
    pos_entry = _make_list_entry(db_session, "positive_control", user_id, code="positive")
    neg_entry = _make_list_entry(db_session, "negative_control", user_id, code="negative")
    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    # Both control types have identical signal (100.0)
    _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 100.0, user_id)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert "Cannot normalize" in exc_info.value.detail or "identical" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 9. Normalization math: (signal - neg_mean) / (pos_mean - neg_mean) * 100
# ---------------------------------------------------------------------------

def test_normalization_percent_inhibition_formula(db_session, test_admin_user, test_org, dr_setup):
    """
    pos_mean=100, neg_mean=0, test_signal=50 → pct_inh=50.0
    Verify the value passed to r_client.fit()
    """
    test_sample = dr_setup["test_sample"]
    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(test_sample.id)]

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)
    svc.trigger_fit(dr_setup["run"].id)

    call_args = mock_r.fit.call_args
    compounds = call_args[0][0]
    assert len(compounds) == 1
    # Single averaged point at pct_inh=50.0
    assert abs(compounds[0]["points"][0]["response"] - 50.0) < 0.01


# ---------------------------------------------------------------------------
# 10. Normalization with inverted signal (pos < neg)
# ---------------------------------------------------------------------------

def test_normalization_inverted_signal_direction(db_session, test_admin_user, test_org):
    """
    pos_mean=0, neg_mean=100, test_signal=25
    → pct_inh = (25 - 100) / (0 - 100) * 100 = 75.0
    """
    user_id = test_admin_user.id
    client_id = test_org.id
    pos_entry = _make_list_entry(db_session, "positive_control", user_id, code="positive")
    neg_entry = _make_list_entry(db_session, "negative_control", user_id, code="negative")
    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)
    test_sample = _make_sample(db_session, user_id, client_id, None)

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    _make_well(db_session, tmpl.id, client_id, "A1", 1.0)
    _make_data_row(db_session, run.id, pos_sample.id, "B1", 0.0, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 100.0, user_id)
    _make_data_row(db_session, run.id, test_sample.id, "A1", 25.0, user_id)

    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(test_sample.id)]

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)
    svc.trigger_fit(run.id)

    compounds = mock_r.fit.call_args[0][0]
    assert abs(compounds[0]["points"][0]["response"] - 75.0) < 0.01


# ---------------------------------------------------------------------------
# 11. trigger_refit — creates new version, supersedes old
# ---------------------------------------------------------------------------

def test_refit_creates_new_version(db_session, test_admin_user, test_org, dr_setup):
    test_sample = dr_setup["test_sample"]
    run = dr_setup["run"]
    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(test_sample.id)]

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)

    # Initial fit
    svc.trigger_fit(run.id)
    results_v1 = (
        db_session.query(DoseResponseResult)
        .filter(DoseResponseResult.lims_run_id == run.id)
        .all()
    )
    assert len(results_v1) == 1
    assert results_v1[0].fit_version == 1
    assert results_v1[0].superseded_by is None

    # Refit
    svc.trigger_refit(run.id, test_sample.id)
    all_results = (
        db_session.query(DoseResponseResult)
        .filter(DoseResponseResult.lims_run_id == run.id)
        .order_by(DoseResponseResult.fit_version)
        .all()
    )
    assert len(all_results) == 2
    v1 = next(r for r in all_results if r.fit_version == 1)
    v2 = next(r for r in all_results if r.fit_version == 2)
    assert v1.superseded_by == v2.id
    assert v2.superseded_by is None
    assert v2.review_status == ReviewStatus.pending


def test_whole_run_refit_supersedes_every_live_fit(db_session, test_admin_user, test_org, dr_setup):
    """A fit with no sample filter leaves one live row per compound."""
    user_id = test_admin_user.id
    client_id = test_org.id
    run = dr_setup["run"]
    tmpl = dr_setup["tmpl"]
    first = dr_setup["test_sample"]
    second = _make_sample(db_session, user_id, client_id, None)
    _make_well(db_session, tmpl.id, client_id, "A2", 2.0)
    _make_data_row(db_session, run.id, second.id, "A2", 40.0, user_id)

    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(first.id), _sigmoid_r_result(second.id)]
    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)
    svc.trigger_fit(run.id)

    leftover = DoseResponseResult(
        lims_run_id=run.id,
        sample_id=first.id,
        model="4PL",
        curve_category=CurveCategory.SIGMOID,
        quality_flag="ok",
        fit_version=5,
        client_id=client_id,
    )
    db_session.add(leftover)
    db_session.commit()

    svc.trigger_fit(run.id)
    rows = (
        db_session.query(DoseResponseResult)
        .filter(DoseResponseResult.lims_run_id == run.id)
        .all()
    )
    live = [row for row in rows if row.superseded_by is None]
    assert len(live) == 2
    live_by_sample = {row.sample_id: row for row in live}
    assert set(live_by_sample) == {first.id, second.id}
    assert live_by_sample[first.id].fit_version == 6
    assert live_by_sample[second.id].fit_version == 2
    first_priors = [row for row in rows if row.sample_id == first.id and row.id != live_by_sample[first.id].id]
    assert len(first_priors) == 2
    assert all(row.superseded_by == live_by_sample[first.id].id for row in first_priors)
    second_priors = [row for row in rows if row.sample_id == second.id and row.superseded_by is not None]
    assert len(second_priors) == 1
    assert second_priors[0].superseded_by == live_by_sample[second.id].id


# ---------------------------------------------------------------------------
# 12. trigger_refit — only fits the target compound
# ---------------------------------------------------------------------------

def test_refit_only_fits_target_compound(db_session, test_admin_user, test_org, dr_setup):
    """With two test compounds, refit for one should send only that compound to R."""
    user_id = test_admin_user.id
    client_id = test_org.id
    run = dr_setup["run"]
    tmpl = dr_setup["tmpl"]

    # Add a second test compound
    second_sample = _make_sample(db_session, user_id, client_id, None)
    _make_well(db_session, tmpl.id, client_id, "A2", 2.0)
    _make_data_row(db_session, run.id, second_sample.id, "A2", 40.0, user_id)

    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(dr_setup["test_sample"].id)]

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=mock_r)
    svc.trigger_refit(run.id, dr_setup["test_sample"].id)

    compounds_sent = mock_r.fit.call_args[0][0]
    assert len(compounds_sent) == 1
    assert compounds_sent[0]["sample_id"] == str(dr_setup["test_sample"].id)


# ---------------------------------------------------------------------------
# 13. review_result — sets review fields
# ---------------------------------------------------------------------------

def test_review_result_sets_status(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]
    test_sample = dr_setup["test_sample"]

    # Insert a result row directly
    result = DoseResponseResult(
        lims_run_id=run.id,
        sample_id=test_sample.id,
        model="4PL",
        curve_category=CurveCategory.SIGMOID,
        quality_flag="ok",
        fit_version=1,
        client_id=test_org.id,
    )
    db_session.add(result)
    db_session.commit()

    resp = client.post(
        f"/v1/lims-runs/{run.id}/dose-response/results/{result.id}/review",
        json={"status": "approved", "notes": "looks good"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    db_session.expire(result)
    assert result.review_status == ReviewStatus.approved
    assert result.review_notes == "looks good"
    assert result.reviewed_by == test_admin_user.id


# ---------------------------------------------------------------------------
# 14. review_result — wrong run_id returns 404
# ---------------------------------------------------------------------------

def test_review_result_wrong_run_returns_404(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    test_sample = dr_setup["test_sample"]
    result = DoseResponseResult(
        lims_run_id=dr_setup["run"].id,
        sample_id=test_sample.id,
        model="4PL",
        curve_category=CurveCategory.SIGMOID,
        quality_flag="ok",
        fit_version=1,
        client_id=test_org.id,
    )
    db_session.add(result)
    db_session.commit()

    wrong_run_id = uuid.uuid4()
    resp = client.post(
        f"/v1/lims-runs/{wrong_run_id}/dose-response/results/{result.id}/review",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 15. batch_review — only updates pending rows, not already-reviewed
# ---------------------------------------------------------------------------

def test_batch_review_only_updates_pending(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]
    test_sample = dr_setup["test_sample"]

    def _result(status: ReviewStatus) -> DoseResponseResult:
        r = DoseResponseResult(
            lims_run_id=run.id,
            sample_id=test_sample.id,
            model="4PL",
            curve_category=CurveCategory.SIGMOID,
            quality_flag="ok",
            review_status=status,
            fit_version=1,
            client_id=test_org.id,
        )
        db_session.add(r)
        return r

    pending = _result(ReviewStatus.pending)
    approved = _result(ReviewStatus.approved)
    rejected = _result(ReviewStatus.rejected)
    db_session.commit()

    resp = client.post(
        f"/v1/lims-runs/{run.id}/dose-response/results/batch-review",
        json={"category": "SIGMOID", "status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1  # only the pending one

    db_session.expire_all()
    assert pending.review_status == ReviewStatus.approved
    assert approved.review_status == ReviewStatus.approved  # unchanged
    assert rejected.review_status == ReviewStatus.rejected  # unchanged


# ---------------------------------------------------------------------------
# 16. batch_review — respects category filter
# ---------------------------------------------------------------------------

def test_batch_review_respects_category_filter(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]

    test_sample = dr_setup["test_sample"]
    sigmoid_pending = DoseResponseResult(
        lims_run_id=run.id, sample_id=test_sample.id, model="4PL",
        curve_category=CurveCategory.SIGMOID, quality_flag="ok",
        review_status=ReviewStatus.pending, fit_version=1, client_id=test_org.id,
    )
    inactive_pending = DoseResponseResult(
        lims_run_id=run.id, sample_id=test_sample.id, model="4PL",
        curve_category=CurveCategory.INACTIVE, quality_flag="ok",
        review_status=ReviewStatus.pending, fit_version=1, client_id=test_org.id,
    )
    db_session.add_all([sigmoid_pending, inactive_pending])
    db_session.commit()

    resp = client.post(
        f"/v1/lims-runs/{run.id}/dose-response/results/batch-review",
        json={"category": "SIGMOID", "status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1

    db_session.expire_all()
    assert sigmoid_pending.review_status == ReviewStatus.approved
    assert inactive_pending.review_status == ReviewStatus.pending  # untouched


# ---------------------------------------------------------------------------
# 17. exclude_data_point — creates exclusion row
# ---------------------------------------------------------------------------

def test_exclude_data_point_creates_exclusion(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    data_row = dr_setup["test_data"]

    resp = client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json={"reason": "outlier"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lims_run_data_id"] == str(data_row.id)

    exc = db_session.query(LimsRunDataExclusion).filter_by(lims_run_data_id=data_row.id).first()
    assert exc is not None
    assert exc.reason == "outlier"
    assert exc.client_id == test_org.id


# ---------------------------------------------------------------------------
# 18. exclude_data_point — double exclusion returns 409
# ---------------------------------------------------------------------------

def test_exclude_data_point_double_exclusion_returns_409(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    data_row = dr_setup["test_data"]

    client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json={"reason": "first"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json={"reason": "second"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409
    assert "already excluded" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 19. unexclude_data_point — removes exclusion row
# ---------------------------------------------------------------------------

def test_unexclude_data_point_removes_exclusion(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    data_row = dr_setup["test_data"]

    client.post(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        json={"reason": "test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = client.delete(
        f"/v1/lims-runs/data/{data_row.id}/exclude",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    exc = db_session.query(LimsRunDataExclusion).filter_by(lims_run_data_id=data_row.id).first()
    assert exc is None


# ---------------------------------------------------------------------------
# 20. get_summary — correct category/review aggregation
# ---------------------------------------------------------------------------

def test_get_summary_aggregates_correctly(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]

    test_sample = dr_setup["test_sample"]
    for _ in range(2):
        db_session.add(DoseResponseResult(
            lims_run_id=run.id, sample_id=test_sample.id, model="4PL",
            curve_category=CurveCategory.SIGMOID, potency=Decimal("0.045"), r_squared=Decimal("0.97"),
            quality_flag="ok", review_status=ReviewStatus.approved, fit_version=1, client_id=test_org.id,
        ))
    db_session.add(DoseResponseResult(
        lims_run_id=run.id, sample_id=test_sample.id, model="4PL",
        curve_category=CurveCategory.INACTIVE, quality_flag="ok",
        review_status=ReviewStatus.pending, fit_version=1, client_id=test_org.id,
    ))
    db_session.commit()

    resp = client.get(
        f"/v1/lims-runs/{run.id}/dose-response/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["by_category"]["SIGMOID"] == 2
    assert body["by_category"]["INACTIVE"] == 1
    assert body["by_review_status"]["approved"] == 2
    assert body["by_review_status"]["pending"] == 1
    assert body["last_fit_at"] is not None
    assert body["last_fit_at"].endswith("Z")


# ---------------------------------------------------------------------------
# 21. get_summary — superseded results excluded from totals
# ---------------------------------------------------------------------------

def test_get_summary_excludes_superseded_results(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]

    test_sample = dr_setup["test_sample"]
    active = DoseResponseResult(
        lims_run_id=run.id, sample_id=test_sample.id, model="4PL",
        curve_category=CurveCategory.SIGMOID, quality_flag="ok", fit_version=2, client_id=test_org.id,
    )
    db_session.add(active)
    db_session.flush()

    superseded = DoseResponseResult(
        lims_run_id=run.id, sample_id=active.sample_id, model="4PL",
        curve_category=CurveCategory.SIGMOID, quality_flag="ok",
        fit_version=1, superseded_by=active.id, client_id=test_org.id,
    )
    db_session.add(superseded)
    db_session.commit()

    resp = client.get(
        f"/v1/lims-runs/{run.id}/dose-response/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1  # only the active version


def test_summary_last_fit_at_is_null_without_a_fit(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]
    resp = client.get(
        f"/v1/lims-runs/{run.id}/dose-response/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0
    assert resp.json()["last_fit_at"] is None


def test_summary_last_fit_at_is_the_latest_current_fit(client, db_session, test_admin_user, test_org, admin_token, dr_setup):
    run = dr_setup["run"]
    sample = dr_setup["test_sample"]
    current = DoseResponseResult(
        lims_run_id=run.id,
        sample_id=sample.id,
        model="4PL",
        curve_category=CurveCategory.SIGMOID,
        quality_flag="ok",
        review_status=ReviewStatus.pending,
        fit_version=2,
        client_id=test_org.id,
        fit_triggered_at=datetime(2026, 10, 18, 23, 23, tzinfo=timezone.utc),
    )
    db_session.add(current)
    db_session.flush()
    superseded = DoseResponseResult(
        lims_run_id=run.id,
        sample_id=sample.id,
        model="4PL",
        curve_category=CurveCategory.SIGMOID,
        quality_flag="ok",
        review_status=ReviewStatus.pending,
        fit_version=1,
        superseded_by=current.id,
        client_id=test_org.id,
        fit_triggered_at=datetime(2026, 10, 19, 1, 0, tzinfo=timezone.utc),
    )
    db_session.add(superseded)
    db_session.commit()

    resp = client.get(
        f"/v1/lims-runs/{run.id}/dose-response/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
    assert resp.json()["last_fit_at"] == "2026-10-18T23:23:00Z"


# ---------------------------------------------------------------------------
# 22. mixed concentration units → 422
# ---------------------------------------------------------------------------

def test_trigger_fit_mixed_concentration_units(db_session, test_admin_user, test_org):
    """All template wells must use the same concentration_unit."""
    user_id = test_admin_user.id
    client_id = test_org.id
    pos_entry = _make_list_entry(db_session, "positive_control", user_id, code="positive")
    neg_entry = _make_list_entry(db_session, "negative_control", user_id, code="negative")
    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)
    test_sample1 = _make_sample(db_session, user_id, client_id, None)
    test_sample2 = _make_sample(db_session, user_id, client_id, None)

    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)

    # Two test compound wells with DIFFERENT units
    _make_well(db_session, tmpl.id, client_id, "A1", 1.0, unit="uM")
    _make_well(db_session, tmpl.id, client_id, "A2", 1000.0, unit="nM")

    _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 0.0, user_id)
    _make_data_row(db_session, run.id, test_sample1.id, "A1", 50.0, user_id)
    _make_data_row(db_session, run.id, test_sample2.id, "A2", 60.0, user_id)

    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert "Mixed concentration units" in exc_info.value.detail


def _stock_controls(db: Session, user_id: uuid.UUID):
    """The seed QC list: display names Positive/Negative Control, codes set.

    create_all databases do not run migration 0004, so this inserts those two
    rows. It does not invent a list entry named positive_control.
    """
    lst = List(
        name=f"qc_types_{uuid.uuid4().hex[:6]}",
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(lst)
    db.flush()
    tag = uuid.uuid4().hex[:8]
    positive = ListEntry(
        list_id=lst.id,
        name=f"Positive Control {tag}",
        code="positive",
        created_by=user_id,
        modified_by=user_id,
    )
    negative = ListEntry(
        list_id=lst.id,
        name=f"Negative Control {tag}",
        code="negative",
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(positive)
    db.add(negative)
    db.flush()
    return positive, negative


def _fit_points(db_session, user, org, pos_entry, neg_entry):
    user_id = user.id
    client_id = org.id
    pos_sample = _make_sample(db_session, user_id, client_id, pos_entry.id)
    neg_sample = _make_sample(db_session, user_id, client_id, neg_entry.id)
    test_sample = _make_sample(db_session, user_id, client_id, None)
    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    _make_well(db_session, tmpl.id, client_id, "A1", 1.0)
    _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 0.0, user_id)
    _make_data_row(db_session, run.id, test_sample.id, "A1", 50.0, user_id)
    mock_r = MagicMock()
    mock_r.fit.return_value = [_sigmoid_r_result(test_sample.id)]
    svc = DoseResponseFitService(db_session, user, r_client=mock_r)
    svc.trigger_fit(run.id)
    compounds = mock_r.fit.call_args[0][0]
    return compounds


def test_fit_uses_stock_qc_codes_after_rename(db_session, test_admin_user, test_org):
    positive, negative = _stock_controls(db_session, test_admin_user.id)
    first = _fit_points(db_session, test_admin_user, test_org, positive, negative)
    assert abs(first[0]["points"][0]["response"] - 50.0) < 0.01
    positive.name = "POS CTL"
    negative.name = "NEG CTL"
    db_session.flush()
    second = _fit_points(db_session, test_admin_user, test_org, positive, negative)
    assert abs(second[0]["points"][0]["response"] - 50.0) < 0.01


def test_display_name_positive_control_without_code_is_not_a_control(
    db_session, test_admin_user, test_org
):
    user_id = test_admin_user.id
    named_only = _make_list_entry(db_session, "positive_control", user_id)
    assert named_only.code is None
    _positive, negative = _stock_controls(db_session, user_id)
    pos_sample = _make_sample(db_session, user_id, test_org.id, named_only.id)
    neg_sample = _make_sample(db_session, user_id, test_org.id, negative.id)
    tmpl = _make_template(db_session, user_id)
    run = _make_run(db_session, tmpl.id, user_id)
    _make_data_row(db_session, run.id, pos_sample.id, "B1", 100.0, user_id)
    _make_data_row(db_session, run.id, neg_sample.id, "C1", 0.0, user_id)
    svc = DoseResponseFitService(db_session, test_admin_user, r_client=MagicMock())
    with pytest.raises(HTTPException) as exc_info:
        svc.trigger_fit(run.id)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "missing_positive_control"
    assert "message" in exc_info.value.detail
