"""
ExperimentRunService — business logic for experiment_runs lifecycle.

Status transitions:
    draft → running  (POST /experiment-runs/{id}/start)
    running → complete  (POST /experiment-runs/{id}/review)  [labeled "Ready for Review" in UI]
    complete → published  (POST /experiment-runs/{id}/complete)  [requires experiment:publish]
    any → failed  (implicit on error paths)

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
    ExperimentDataRepository,
    ExperimentRunRepository,
    RobotWorklistConfigRepository,
    InstrumentParserRepository,
)
from app.schemas.flexible_experiment import (
    ExperimentRunCreate,
    ExperimentDataRow,
    ImportDataResponse,
    ExperimentDataRead,
)
from models.flexible_experiment import (
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentData,
    VALID_TRANSITIONS,
)
from models.user import User


class ExperimentRunService:
    """
    Business logic for experiment_runs.

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
        self.run_repo = ExperimentRunRepository(db)
        self.data_repo = ExperimentDataRepository(db)
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

    def create_run(self, data: ExperimentRunCreate) -> ExperimentRun:
        client_id = self.current_user.client_id if self.current_user else None
        if client_id and self.run_repo.get_by_name_for_client(data.name, client_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Experiment run '{data.name}' already exists",
            )
        run = self.run_repo.create(
            name=data.name,
            experiment_template_id=data.experiment_template_id,
            description=data.description,
            created_by=self._user_id(),
        )
        self._commit_refresh(run)
        return run

    def get_run(self, run_id: uuid.UUID) -> ExperimentRun:
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment run not found")
        return run

    def list_runs(
        self,
        template_id: Optional[uuid.UUID] = None,
        status: Optional[ExperimentRunStatus] = None,
        mine: bool = False,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ExperimentRun], int]:
        created_by = self._user_id() if mine else None
        return self.run_repo.list(
            template_id=template_id,
            status=status,
            created_by=created_by,
            page=page,
            size=size,
        )

    # ---------- Status transitions ----------

    def _transition(self, run: ExperimentRun, new_status: ExperimentRunStatus) -> ExperimentRun:
        current = ExperimentRunStatus(run.status)
        if new_status not in VALID_TRANSITIONS.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{current.value}' to '{new_status.value}'",
            )
        self.run_repo.update_status(run, new_status, self._user_id())
        self._commit_refresh(run)
        return run

    def start_run(self, run_id: uuid.UUID) -> ExperimentRun:
        """draft → running"""
        run = self.get_run(run_id)
        return self._transition(run, ExperimentRunStatus.running)

    def move_to_review(self, run_id: uuid.UUID) -> ExperimentRun:
        """running → complete (labeled 'Ready for Review' in the UI)"""
        run = self.get_run(run_id)
        return self._transition(run, ExperimentRunStatus.complete)

    def publish_run(self, run_id: uuid.UUID) -> ExperimentRun:
        """complete → published. Caller must have verified experiment:publish permission."""
        run = self.get_run(run_id)
        return self._transition(run, ExperimentRunStatus.published)

    # ---------- Data import ----------

    def import_data(
        self,
        run_id: uuid.UUID,
        rows: List[ExperimentDataRow],
    ) -> ImportDataResponse:
        """
        Import instrument data into a running experiment.
        Only allowed when status == 'running'.
        Columns must match the template's parser_config; raises 422 if they don't.
        """
        run = self.get_run(run_id)
        if run.status != ExperimentRunStatus.running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data import requires status 'running'; current status is '{run.status.value}'",
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
            rows=[ExperimentDataRead.model_validate(r) for r in created_rows],
        )

    def get_data_rows(self, run_id: uuid.UUID) -> List[ExperimentData]:
        self.get_run(run_id)  # 404 guard
        return self.data_repo.list_for_run(run_id)

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

        data_rows = self.data_repo.list_for_run(run_id)
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
