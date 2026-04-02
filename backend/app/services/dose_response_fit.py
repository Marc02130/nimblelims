"""
DoseResponseFitService — orchestrates dose-response curve fitting.

Responsibilities:
  1. Load experiment_data for a run
  2. Identify control wells via experiment_data.sample_id → samples.qc_type
     (NOT via experiment_sample_executions — that table has no well_position)
  3. Validate controls exist and are non-degenerate (pos_mean != neg_mean)
  4. Compute % inhibition per well
  5. Load concentrations from template_well_definitions (not JSONB)
  6. Group by replicate_group, average replicates per concentration level
  7. Apply experiment_data_exclusions (soft knockout)
  8. Enforce 10% knockout rule (warning, not a block)
  9. POST all compounds to r-calculator in one batch (synchronous, 60s timeout)
  10. Write dose_response_results in a single DB transaction
      (all-or-nothing: if any DB write fails, the whole batch is rolled back)

R never touches the database. FastAPI owns data access and normalization.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.r_calculator_client import RCalculatorClient
from models.dose_response import (
    CurveCategory,
    DoseResponseResult,
    ExperimentDataExclusion,
)
from models.flexible_experiment import ExperimentData, ExperimentRun
from models.sample import Sample
from models.template_well import TemplateWellDefinition
from models.user import User

logger = logging.getLogger(__name__)

MAX_KNOCKOUT_PCT = 10.0


class DoseResponseFitService:
    def __init__(
        self,
        db: Session,
        current_user: User,
        r_client: Optional[RCalculatorClient] = None,
    ) -> None:
        self.db = db
        self.current_user = current_user
        self.r_client = r_client or RCalculatorClient()

    # ── Public API ────────────────────────────────────────────────────────────

    def trigger_fit(self, run_id: uuid.UUID) -> Dict:
        """
        Main entry point. Fits all non-control compounds in the run.
        Returns {"fitted": N, "failed": N, "results": [...]}.

        Raises 409 if fit_in_progress for this run.
        Raises 422 if controls are missing or degenerate.
        Raises 503 on R service failure.
        """
        run = self._get_run_or_404(run_id)
        self._check_not_in_progress(run)
        self._set_fit_in_progress(run, True)

        try:
            return self._run_fit(run)
        finally:
            self._set_fit_in_progress(run, False)

    def trigger_refit(self, run_id: uuid.UUID, sample_id: uuid.UUID) -> Dict:
        """Re-fit a single compound after knockout. Creates a new result row."""
        run = self._get_run_or_404(run_id)
        self._check_not_in_progress(run)
        self._set_fit_in_progress(run, True)
        try:
            return self._run_fit(run, sample_id_filter=sample_id)
        finally:
            self._set_fit_in_progress(run, False)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_run_or_404(self, run_id: uuid.UUID) -> ExperimentRun:
        run = self.db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment run not found")
        return run

    def _check_not_in_progress(self, run: ExperimentRun) -> None:
        if run.fit_in_progress:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fit already in progress for this run. Wait for it to complete.",
            )

    def _set_fit_in_progress(self, run: ExperimentRun, value: bool) -> None:
        run.fit_in_progress = value
        self.db.flush()
        self.db.commit()

    def _run_fit(
        self,
        run: ExperimentRun,
        sample_id_filter: Optional[uuid.UUID] = None,
    ) -> Dict:
        # Load all experiment_data for this run
        data_rows = (
            self.db.query(ExperimentData)
            .filter(ExperimentData.experiment_run_id == run.id)
            .all()
        )
        if not data_rows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No data found for this run. Import instrument data first.",
            )

        # Load exclusions (excluded point IDs)
        excluded_data_ids = {
            str(exc.experiment_data_id)
            for exc in self.db.query(ExperimentDataExclusion)
            .join(ExperimentData, ExperimentDataExclusion.experiment_data_id == ExperimentData.id)
            .filter(ExperimentData.experiment_run_id == run.id)
            .all()
        }

        # Load sample QC types for all samples in this run
        sample_ids = {row.sample_id for row in data_rows if row.sample_id}
        samples_by_id: Dict[uuid.UUID, Sample] = {}
        if sample_ids:
            samples = self.db.query(Sample).filter(Sample.id.in_(sample_ids)).all()
            # qc_type is a UUID FK to list_entries — we need the list entry value
            # Load via join to get the actual string value
            from models.list import ListEntry
            for s in samples:
                samples_by_id[s.id] = s

        # Load well definitions (concentrations) from template_well_definitions
        well_defs = (
            self.db.query(TemplateWellDefinition)
            .filter(TemplateWellDefinition.template_id == run.experiment_template_id)
            .all()
        )
        well_def_by_pos: Dict[str, TemplateWellDefinition] = {
            wd.well_position: wd for wd in well_defs
        }

        # Load dose_response_config from template JSONB
        template = run.experiment_template
        template_def = template.template_definition or {}
        dr_config = template_def.get("dose_response_config", {})
        model = dr_config.get("model", "4PL")
        normalization = dr_config.get("normalization", "percent_inhibition")
        r_sq_threshold = dr_config.get("r_squared_threshold", 0.9)
        inactive_threshold = dr_config.get("inactive_threshold", 20.0)
        constraints = dr_config.get("parameter_constraints", {})

        # ── Step 1: Identify control wells via sample.qc_type ─────────────────
        # sample.qc_type is a UUID FK to list_entries. We match by list entry name.
        # Control identification uses experiment_data.sample_id → samples.qc_type → list_entries.name
        from models.list import ListEntry
        qc_list_entries = (
            self.db.query(ListEntry)
            .filter(ListEntry.name.in_(["positive_control", "negative_control"]))
            .all()
        )
        qc_entry_by_id: Dict[uuid.UUID, str] = {e.id: e.name for e in qc_list_entries}

        pos_control_signals: List[float] = []
        neg_control_signals: List[float] = []
        test_data_rows: List[ExperimentData] = []

        result_col = dr_config.get("result_column")

        for row in data_rows:
            if not row.sample_id:
                continue
            sample = samples_by_id.get(row.sample_id)
            if not sample:
                continue

            signal = self._extract_signal(row, result_col)
            if signal is None:
                continue

            qc_name = qc_entry_by_id.get(sample.qc_type)
            if qc_name == "positive_control":
                pos_control_signals.append(signal)
            elif qc_name == "negative_control":
                neg_control_signals.append(signal)
            else:
                test_data_rows.append(row)

        # ── Step 2: Validate controls ──────────────────────────────────────────
        if not pos_control_signals:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No positive_control wells found. Check that control samples have qc_type='positive_control'.",
            )
        if not neg_control_signals:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No negative_control wells found. Check that control samples have qc_type='negative_control'.",
            )

        pos_mean = sum(pos_control_signals) / len(pos_control_signals)
        neg_mean = sum(neg_control_signals) / len(neg_control_signals)

        if pos_mean == neg_mean:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cannot normalize: positive_control mean ({pos_mean:.2f}) equals "
                    f"negative_control mean ({neg_mean:.2f}). Controls have identical signal."
                ),
            )

        logger.info(
            "Controls identified",
            extra={
                "run_id": str(run.id),
                "pos_n": len(pos_control_signals),
                "neg_n": len(neg_control_signals),
                "pos_mean": pos_mean,
                "neg_mean": neg_mean,
            },
        )

        # ── Step 3: Normalize to % inhibition ────────────────────────────────
        # % inhibition = (signal - neg_mean) / (pos_mean - neg_mean) * 100
        def normalize(signal: float) -> float:
            return (signal - neg_mean) / (pos_mean - neg_mean) * 100.0

        # ── Step 4: Group test wells by compound, pair with concentrations ────
        # Group by sample_id → replicate_group (from template_well_definitions)
        # Then group by concentration_value → average replicates
        compound_data: Dict[uuid.UUID, Dict] = defaultdict(lambda: {"points_by_conc": defaultdict(list)})

        for row in test_data_rows:
            if str(row.id) in excluded_data_ids:
                continue
            if sample_id_filter and row.sample_id != sample_id_filter:
                continue

            well_def = well_def_by_pos.get(row.well_position or "")
            if not well_def:
                continue
            if well_def.concentration_value is None:
                continue

            signal = self._extract_signal(row, result_col)
            if signal is None:
                continue

            pct_inh = normalize(signal)
            conc = float(well_def.concentration_value)
            compound_data[row.sample_id]["points_by_conc"][conc].append({
                "response": pct_inh,
                "point_id": str(row.id),
            })
            compound_data[row.sample_id]["replicate_group"] = well_def.replicate_group
            compound_data[row.sample_id]["concentration_unit"] = well_def.concentration_unit

        if not compound_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No test wells with concentration data found after applying exclusions.",
            )

        # ── Step 5: Build compound payloads for R ─────────────────────────────
        r_compounds = []
        warnings = []

        for sid, cdata in compound_data.items():
            points_by_conc = cdata["points_by_conc"]

            # Average replicates per concentration level
            averaged_points = []
            total_reps = 0
            for conc, reps in sorted(points_by_conc.items()):
                total_reps += len(reps)
                avg_response = sum(r["response"] for r in reps) / len(reps)
                averaged_points.append({
                    "conc": conc,
                    "response": avg_response,
                    "point_id": reps[0]["point_id"],  # representative point_id
                })

            # Check excluded replicates for 10% rule
            # Count all reps for this compound (including excluded)
            all_reps_for_compound = sum(
                len(v)
                for row2 in test_data_rows
                if row2.sample_id == sid
                for v in [well_def_by_pos.get(row2.well_position or "")]
                if v and v.concentration_value is not None
                for _ in [True]
            )
            excluded_for_compound = sum(
                1 for row2 in test_data_rows
                if row2.sample_id == sid and str(row2.id) in excluded_data_ids
                and well_def_by_pos.get(row2.well_position or "") is not None
            )
            if all_reps_for_compound > 0:
                knockout_pct = excluded_for_compound / all_reps_for_compound * 100
                if knockout_pct > MAX_KNOCKOUT_PCT:
                    warnings.append({
                        "sample_id": str(sid),
                        "warning": f"{knockout_pct:.1f}% of points excluded (>{MAX_KNOCKOUT_PCT}% threshold)",
                    })

            r_compounds.append({
                "sample_id": str(sid),
                "points": averaged_points,
                "model": model,
                "constraints": constraints,
            })

        r_config = {
            "r_squared_threshold": r_sq_threshold,
            "inactive_threshold": inactive_threshold,
            "concentration_unit": (
                list(compound_data.values())[0].get("concentration_unit", "unknown")
                if compound_data else "unknown"
            ),
        }

        logger.info(
            "Triggering R fit",
            extra={"run_id": str(run.id), "compound_count": len(r_compounds)},
        )

        # ── Step 6: POST to R service ─────────────────────────────────────────
        r_results = self.r_client.fit(r_compounds, r_config)

        # ── Step 7: Write results (all-or-nothing transaction) ────────────────
        fitted = 0
        failed = 0
        result_summaries = []

        now = datetime.now(timezone.utc)
        client_id = self.current_user.client_id

        # Supersede old results for re-fit case
        if sample_id_filter:
            old_results = (
                self.db.query(DoseResponseResult)
                .filter(
                    DoseResponseResult.experiment_run_id == run.id,
                    DoseResponseResult.sample_id == sample_id_filter,
                    DoseResponseResult.superseded_by.is_(None),
                )
                .all()
            )
        else:
            old_results = []

        new_rows = []
        for r_res in r_results:
            sid = uuid.UUID(r_res["sample_id"])
            points_used = len(
                compound_data[sid]["points_by_conc"]
            ) if sid in compound_data else None

            points_excluded = sum(
                1 for row2 in test_data_rows
                if row2.sample_id == sid and str(row2.id) in excluded_data_ids
            )

            # Determine fit_version
            prior = next((o for o in old_results if o.sample_id == sid), None)
            fit_version = (prior.fit_version + 1) if prior else 1

            new_row = DoseResponseResult(
                experiment_run_id = run.id,
                sample_id         = sid,
                model             = model,
                potency           = r_res.get("potency"),
                potency_type      = r_res.get("potency_type") or "IC50",
                hill_slope        = r_res.get("hill_slope"),
                top               = r_res.get("top"),
                bottom            = r_res.get("bottom"),
                r_squared         = r_res.get("r_squared"),
                ci_low_95         = r_res.get("ci_low_95"),
                ci_high_95        = r_res.get("ci_high_95"),
                ci_method         = r_res.get("ci_method"),
                curve_category    = CurveCategory(r_res["curve_category"]),
                quality_flag      = r_res.get("quality_flag", "review_required"),
                points_used       = points_used,
                points_excluded   = points_excluded,
                thumbnail_svg     = r_res.get("thumbnail_svg"),
                fit_version       = fit_version,
                fit_triggered_at  = now,
                fit_triggered_by  = self.current_user.id,
                client_id         = client_id,
            )
            new_rows.append((new_row, prior))

            if r_res.get("success"):
                fitted += 1
            else:
                failed += 1

            result_summaries.append({
                "sample_id":     str(sid),
                "curve_category": r_res["curve_category"],
                "potency":        r_res.get("potency"),
            })

        # Atomic write: add all new rows, link superseded rows
        for new_row, prior in new_rows:
            self.db.add(new_row)
            self.db.flush()  # get new_row.id
            if prior:
                prior.superseded_by = new_row.id

        self.db.commit()

        logger.info(
            "Fit complete",
            extra={
                "run_id": str(run.id),
                "fitted": fitted,
                "failed": failed,
                "warnings": len(warnings),
            },
        )

        return {
            "fitted":   fitted,
            "failed":   failed,
            "warnings": warnings,
            "results":  result_summaries,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_signal(row: ExperimentData, result_col: Optional[str]) -> Optional[float]:
        """Extract the numeric signal from experiment_data.row_data JSONB."""
        if not row.row_data:
            return None
        if result_col and result_col in row.row_data:
            try:
                return float(row.row_data[result_col])
            except (TypeError, ValueError):
                return None
        # Fallback: try common column names
        for key in ("result", "signal", "luminescence", "fluorescence", "absorbance", "value"):
            if key in row.row_data:
                try:
                    return float(row.row_data[key])
                except (TypeError, ValueError):
                    continue
        return None
