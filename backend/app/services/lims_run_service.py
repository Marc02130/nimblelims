"""
LimsRunService — business logic for lims_runs lifecycle.

Standard lifecycle (lifecycle_type='standard'):
    draft → running       (PATCH /start)
    running → complete    (PATCH /review)   [labeled "Ready for Review" in UI]
    complete → published  (PATCH /complete) [requires experiment:publish]
    any non-terminal → canceled  (PATCH /cancel)

CRO lifecycle (lifecycle_type='cro'):
    draft → ordered              (PATCH /order)
    ordered → running            (PATCH /start)
    running → results_received   (PATCH /results-received)
    results_received → complete  (PATCH /review)
    complete → published         (PATCH /complete) [requires experiment:publish]
    any non-terminal → canceled  (PATCH /cancel)

Data import is allowed when status is 'running' OR 'results_received'.
Worklist export and data import are also handled here.
"""
from __future__ import annotations

import csv
import io
import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.flexible_experiment_repository import (
    LimsRunDataRepository,
    LimsRunRepository,
    RobotWorklistConfigRepository,
    InstrumentParserRepository,
)
from app.schemas.flexible_experiment import (
    LimsRunCreate,
    LimsRunUpdate,
    LimsRunDataRow,
    ImportDataResponse,
    LimsRunDataRead,
)
from models.flexible_experiment import (
    LimsRun,
    LimsRunStatus,
    LimsRunData,
    VALID_TRANSITIONS,
    LIFECYCLE_TRANSITIONS,
)
from models.user import User


class LimsRunService:
    """
    Business logic for lims_runs.

    Data import: only allowed when run.status == 'running'.
    Status transitions: validated against VALID_TRANSITIONS.
    Publish transition: caller must verify experiment:publish permission before calling
    transition_to_published() — the service does not check permissions internally.
    mandatory_review enforcement: service layer blocks worklist export if
    template.template_definition['mandatory_review_count'] > 0.
    """

    def __init__(self, db: Session, current_user: Optional[User] = None) -> None:
        self.db = db
        self.current_user = current_user
        self.run_repo = LimsRunRepository(db)
        self.data_repo = LimsRunDataRepository(db)
        self.worklist_repo = RobotWorklistConfigRepository(db)
        self.parser_repo = InstrumentParserRepository(db)

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects) -> None:
        self.db.flush()
        for obj in objects:
            if obj is not None:
                self.db.refresh(obj)
        self.db.commit()

    # ---------- CRUD ----------

    def create_run(self, data: LimsRunCreate) -> LimsRun:
        # Global unique name (aligned with other first-class entities)
        if self.run_repo.get_by_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LIMS run '{data.name}' already exists",
            )
        if data.analysis_id is not None:
            self._require_analysis(data.analysis_id)
        run = self.run_repo.create(
            name=data.name,
            experiment_template_id=data.experiment_template_id,
            description=data.description,
            created_by=self._user_id(),
            analysis_id=data.analysis_id,
        )
        self._commit_refresh(run)
        return run

    def _require_analysis(self, analysis_id: uuid.UUID) -> None:
        from models.analysis import Analysis
        exists = self.db.query(Analysis.id).filter(
            Analysis.id == analysis_id,
            Analysis.active == True,  # noqa: E712
        ).first()
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis {analysis_id} not found or inactive",
            )

    def update_run(self, run_id: uuid.UUID, data: LimsRunUpdate) -> LimsRun:
        run = self.get_run(run_id)
        kwargs: dict = {"modified_by": self._user_id()}
        if data.name is not None:
            other = self.run_repo.get_by_name(data.name)
            if other and other.id != run_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"LIMS run '{data.name}' already exists",
                )
            kwargs["name"] = data.name
        if data.description is not None:
            kwargs["description"] = data.description
        if data.clear_analysis:
            kwargs["analysis_id"] = None
        elif data.analysis_id is not None:
            self._require_analysis(data.analysis_id)
            kwargs["analysis_id"] = data.analysis_id
        self.run_repo.update_fields(run, **kwargs)
        self._commit_refresh(run)
        return run

    def get_run(self, run_id: uuid.UUID) -> LimsRun:
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LIMS run not found")
        return run

    def list_runs(
        self,
        template_id: Optional[uuid.UUID] = None,
        status: Optional[LimsRunStatus] = None,
        mine: bool = False,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[LimsRun], int]:
        created_by = self._user_id() if mine else None
        return self.run_repo.list(
            template_id=template_id,
            status=status,
            created_by=created_by,
            page=page,
            size=size,
        )

    # ---------- Status transitions ----------

    def _lifecycle_transitions(self, run: LimsRun) -> dict:
        """Return the correct transitions dict based on the template's lifecycle_type."""
        lifecycle = getattr(run.experiment_template, "lifecycle_type", "standard") or "standard"
        return LIFECYCLE_TRANSITIONS.get(lifecycle, VALID_TRANSITIONS)

    def _transition(self, run: LimsRun, new_status: LimsRunStatus) -> LimsRun:
        current = LimsRunStatus(run.status)
        transitions = self._lifecycle_transitions(run)
        if new_status not in transitions.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{current.value}' to '{new_status.value}'",
            )
        self.run_repo.update_status(run, new_status, self._user_id())
        self._commit_refresh(run)
        return run

    def order_run(self, run_id: uuid.UUID) -> LimsRun:
        """draft → ordered (CRO lifecycle only)"""
        run = self.get_run(run_id)
        return self._transition(run, LimsRunStatus.ordered)

    def start_run(
        self,
        run_id: uuid.UUID,
        *,
        acknowledge_no_analysis: bool = False,
    ) -> LimsRun:
        """
        draft → running (standard) or ordered → running (CRO).

        If analysis_id is null and acknowledge_no_analysis is false, raise 400 with
        a structured detail so the UI can warn and offer associate/create analysis.
        """
        run = self.get_run(run_id)
        if run.analysis_id is None and not acknowledge_no_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "analysis_required_ack",
                    "message": (
                        "No Analysis is associated with this run. Imported data will not be "
                        "written to Tests/Results when published. Associate an analysis, "
                        "create one, or acknowledge to continue without structured results."
                    ),
                    "analysis_id": None,
                },
            )
        return self._transition(run, LimsRunStatus.running)

    def mark_results_received(self, run_id: uuid.UUID) -> LimsRun:
        """running → results_received (CRO lifecycle only)"""
        run = self.get_run(run_id)
        return self._transition(run, LimsRunStatus.results_received)

    def move_to_review(self, run_id: uuid.UUID) -> LimsRun:
        """running → complete (standard) or results_received → complete (CRO)"""
        run = self.get_run(run_id)
        return self._transition(run, LimsRunStatus.complete)

    def publish_run(self, run_id: uuid.UUID) -> LimsRun:
        """
        complete → published. Caller must have verified experiment:publish permission.

        When analysis_id is set, promotes lims_run_data → tests/results in the same
        transaction (P3). Conflicts with other runs abort publish.
        """
        run = self.get_run(run_id)
        current = LimsRunStatus(run.status)
        transitions = self._lifecycle_transitions(run)
        if LimsRunStatus.published not in transitions.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{current.value}' to 'published'",
            )

        from app.services.result_promotion_service import ResultPromotionService

        promo = ResultPromotionService(self.db, current_user=self.current_user)
        # Plan first (may create tests via ensure); apply if analysis set
        if run.analysis_id:
            plan = promo.plan_promotion(run)
            if plan.conflict_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "promotion_conflict",
                        "message": (
                            "Cannot publish: some results already exist from another "
                            "run or manual entry. Resolve conflicts before publishing."
                        ),
                        "conflict_count": plan.conflict_count,
                        "errors": plan.errors[:20],
                        "preview": plan.to_dict(),
                    },
                )
            promo.apply_plan(run, plan)

        self.run_repo.update_status(run, LimsRunStatus.published, self._user_id())
        self._commit_refresh(run)
        return run

    def promotion_preview(self, run_id: uuid.UUID) -> dict:
        """Dry-run of promote-on-publish (no DB writes)."""
        run = self.get_run(run_id)
        from app.services.result_promotion_service import ResultPromotionService

        promo = ResultPromotionService(self.db, current_user=self.current_user)
        plan = promo.plan_promotion(run, dry_run=True)
        return plan.to_dict()

    def cancel_run(self, run_id: uuid.UUID) -> LimsRun:
        """Any non-terminal state → canceled."""
        run = self.get_run(run_id)
        return self._transition(run, LimsRunStatus.canceled)

    # ---------- Data import ----------

    def import_data(
        self,
        run_id: uuid.UUID,
        rows: List[LimsRunDataRow],
    ) -> ImportDataResponse:
        """
        Import instrument data into a running experiment.
        Only allowed when status == 'running'.
        Columns must match the template's parser_config; raises 422 if they don't.
        """
        run = self.get_run(run_id)
        _import_allowed = {LimsRunStatus.running, LimsRunStatus.results_received}
        if run.status not in _import_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data import requires status 'running' or 'results_received'; current status is '{run.status.value}'",
            )

        # Validate parser_config exists on template
        parser = self.parser_repo.get_for_template(run.experiment_template_id)
        if not parser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template has no instrument parser configured. Cannot import data.",
            )

        # Validate row_data columns match expected field names
        expected_fields = {col["field_name"] for col in parser.parser_config.get("columns", [])}
        if expected_fields:
            for i, row in enumerate(rows):
                missing = expected_fields - set(row.row_data.keys())
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Row {i}: missing expected columns: {sorted(missing)}",
                    )

        row_dicts = [
            {
                "container_id": row.container_id,
                "well_position": row.well_position,
                "sample_id": row.sample_id,
                "row_data": row.row_data,
            }
            for row in rows
        ]
        created_rows = self.data_repo.bulk_create(run_id, row_dicts, self._user_id())
        # Flush + commit without per-row refresh (avoids N+1 round-trips).
        # created_rows are already in-memory; created_at will be populated by DB default
        # on flush. The response schema tolerates None for server-set timestamps.
        self.db.flush()
        self.db.commit()

        return ImportDataResponse(
            imported=len(created_rows),
            skipped=0,
            rows=[LimsRunDataRead.model_validate(r) for r in created_rows],
        )

    def get_data_rows(
        self,
        run_id: uuid.UUID,
        page: int = 1,
        size: int = 100,
    ) -> Tuple[List[LimsRunData], int]:
        self.get_run(run_id)  # 404 guard
        return self.data_repo.list_for_run(run_id, page=page, size=size)

    # ---------- Worklist export ----------

    def export_worklist_csv(self, run_id: uuid.UUID) -> str:
        """
        Generate a generic CSV robot worklist (source_well, dest_well, volume).
        Raises 400 if template has no robot_worklist_config.
        Raises 400 if template has unreviewed mandatory fields (mandatory_review_count > 0).
        """
        run = self.get_run(run_id)

        worklist_config = self.worklist_repo.get_for_template(run.experiment_template_id)
        if not worklist_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template has no robot worklist config. Cannot generate worklist.",
            )

        # Enforce mandatory_review at service layer
        template_def = getattr(run.experiment_template, "template_definition", None) or {}
        mandatory_count = template_def.get("mandatory_review_count", 0)
        if mandatory_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Template has {mandatory_count} field(s) requiring scientist review. "
                    "Confirm all mandatory fields before generating the worklist."
                ),
            )

        data_rows = self.data_repo.list_all_for_run(run_id)
        if not data_rows:
            # Empty run: return headers-only CSV
            return "source_well,dest_well,volume\n"

        steps = worklist_config.worklist_config.get("steps", [])
        if not steps:
            return "source_well,dest_well,volume\n"

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["source_well", "dest_well", "volume"])
        writer.writeheader()

        step = steps[0]  # MVP: use first step config
        source_col = step.get("source_well_col", "source_well")
        dest_col = step.get("dest_well_col", "dest_well")
        volume_col = step.get("volume_col", "volume")

        for row in data_rows:
            rd = row.row_data
            writer.writerow({
                "source_well": rd.get(source_col, ""),
                "dest_well": rd.get(dest_col, ""),
                "volume": rd.get(volume_col, ""),
            })

        return output.getvalue()
