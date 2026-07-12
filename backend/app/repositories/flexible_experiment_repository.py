"""
Repository layer for the flexible experiment engine.
Pure DB access — no business logic, no HTTP exceptions.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from models.flexible_experiment import (
    LimsRun,
    LimsRunStatus,
    LimsRunData,
    InstrumentParser,
    RobotWorklistConfig,
    SopParseJob,
    SopParseJobStatus,
)


class LimsRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, run_id: uuid.UUID) -> Optional[LimsRun]:
        from sqlalchemy.orm import joinedload
        return (
            self.db.query(LimsRun)
            .options(joinedload(LimsRun.experiment_template))
            .filter(LimsRun.id == run_id)
            .first()
        )

    def get_by_name(self, name: str) -> Optional[LimsRun]:
        return self.db.query(LimsRun).filter(LimsRun.name == name).first()

    def list(
        self,
        template_id: Optional[uuid.UUID] = None,
        status: Optional[LimsRunStatus] = None,
        created_by: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[LimsRun], int]:
        q = self.db.query(LimsRun)
        if template_id:
            q = q.filter(LimsRun.experiment_template_id == template_id)
        if status:
            q = q.filter(LimsRun.status == status)
        if created_by:
            q = q.filter(LimsRun.created_by == created_by)
        total = q.count()
        items = q.order_by(LimsRun.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    def create(
        self,
        name: str,
        experiment_template_id: uuid.UUID,
        description: Optional[str],
        created_by: Optional[uuid.UUID],
        analysis_id: Optional[uuid.UUID] = None,
    ) -> LimsRun:
        run = LimsRun(
            name=name,
            description=description,
            experiment_template_id=experiment_template_id,
            analysis_id=analysis_id,
            status=LimsRunStatus.draft,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(run)
        return run

    def update_fields(self, run: LimsRun, **kwargs) -> LimsRun:
        for k, v in kwargs.items():
            if hasattr(run, k):
                setattr(run, k, v)
        self.db.flush()
        return run

    def get_by_name_for_client(self, name: str, client_id: uuid.UUID) -> Optional[LimsRun]:
        """Return the run with `name` that belongs to the given client.

        Multi-tenant boundary: joins through created_by → User.client_id so
        two different orgs can create runs with identical names without collision.

        LimsRun.created_by → User.id → User.client_id
        """
        from models.user import User
        return (
            self.db.query(LimsRun)
            .join(User, LimsRun.created_by == User.id)
            .filter(LimsRun.name == name, User.client_id == client_id)
            .first()
        )

    def update_status(
        self,
        run: LimsRun,
        new_status: LimsRunStatus,
        modified_by: Optional[uuid.UUID],
    ) -> LimsRun:
        from datetime import datetime, timezone
        run.status = new_status
        run.modified_by = modified_by
        if new_status == LimsRunStatus.running and not run.started_at:
            run.started_at = datetime.now(timezone.utc)
        elif new_status == LimsRunStatus.complete and not run.completed_at:
            run.completed_at = datetime.now(timezone.utc)
        elif new_status == LimsRunStatus.published and not run.published_at:
            run.published_at = datetime.now(timezone.utc)
        return run


class LimsRunDataRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_run(
        self,
        run_id: uuid.UUID,
        page: int = 1,
        size: int = 100,
    ) -> Tuple[List[LimsRunData], int]:
        q = (
            self.db.query(LimsRunData)
            .filter(LimsRunData.lims_run_id == run_id)
            .order_by(LimsRunData.created_at)
        )
        total = q.count()
        items = q.offset((page - 1) * size).limit(size).all()
        return items, total

    def list_all_for_run(self, run_id: uuid.UUID) -> List[LimsRunData]:
        """Return all rows without pagination — for worklist export."""
        return (
            self.db.query(LimsRunData)
            .filter(LimsRunData.lims_run_id == run_id)
            .order_by(LimsRunData.created_at)
            .all()
        )

    def bulk_create(
        self,
        run_id: uuid.UUID,
        rows: list[dict],
        created_by: Optional[uuid.UUID],
    ) -> List[LimsRunData]:
        objects = [
            LimsRunData(
                lims_run_id=run_id,
                container_id=row.get("container_id"),
                well_position=row.get("well_position"),
                sample_id=row.get("sample_id"),
                row_data=row["row_data"],
                created_by=created_by,
                modified_by=created_by,
            )
            for row in rows
        ]
        self.db.add_all(objects)
        return objects


class InstrumentParserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_template(self, template_id: uuid.UUID) -> Optional[InstrumentParser]:
        return (
            self.db.query(InstrumentParser)
            .filter(InstrumentParser.experiment_template_id == template_id)
            .first()
        )

    def create(
        self,
        template_id: uuid.UUID,
        name: str,
        description: Optional[str],
        parser_config: dict,
        created_by: Optional[uuid.UUID],
    ) -> InstrumentParser:
        parser = InstrumentParser(
            experiment_template_id=template_id,
            name=name,
            description=description,
            parser_config=parser_config,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(parser)
        return parser

    def update(
        self,
        parser: InstrumentParser,
        parser_config: dict,
        modified_by: Optional[uuid.UUID],
    ) -> InstrumentParser:
        parser.parser_config = parser_config
        parser.modified_by = modified_by
        return parser


class RobotWorklistConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_template(self, template_id: uuid.UUID) -> Optional[RobotWorklistConfig]:
        return (
            self.db.query(RobotWorklistConfig)
            .filter(RobotWorklistConfig.experiment_template_id == template_id)
            .first()
        )

    def create(
        self,
        template_id: uuid.UUID,
        name: str,
        description: Optional[str],
        worklist_config: dict,
        created_by: Optional[uuid.UUID],
    ) -> RobotWorklistConfig:
        config = RobotWorklistConfig(
            experiment_template_id=template_id,
            name=name,
            description=description,
            worklist_config=worklist_config,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(config)
        return config


class SopParseJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, job_id: uuid.UUID) -> Optional[SopParseJob]:
        return self.db.query(SopParseJob).filter(SopParseJob.id == job_id).first()

    def get_pending_for_template(self, template_id: uuid.UUID) -> Optional[SopParseJob]:
        return (
            self.db.query(SopParseJob)
            .filter(
                SopParseJob.experiment_template_id == template_id,
                SopParseJob.status.in_([SopParseJobStatus.pending, SopParseJobStatus.processing]),
            )
            .first()
        )

    def create(
        self,
        sop_filename: Optional[str],
        instrument_filename: Optional[str],
        created_by: Optional[uuid.UUID],
    ) -> SopParseJob:
        job = SopParseJob(
            status=SopParseJobStatus.pending,
            sop_filename=sop_filename,
            instrument_filename=instrument_filename,
            created_by=created_by,
            modified_by=created_by,
        )
        self.db.add(job)
        return job

    def mark_processing(self, job: SopParseJob) -> SopParseJob:
        job.status = SopParseJobStatus.processing
        return job

    def mark_complete(
        self,
        job: SopParseJob,
        result: dict,
        experiment_template_id: Optional[uuid.UUID] = None,
    ) -> SopParseJob:
        job.status = SopParseJobStatus.complete
        job.result = result
        if experiment_template_id:
            job.experiment_template_id = experiment_template_id
        return job

    def mark_failed(self, job: SopParseJob, error_message: str) -> SopParseJob:
        job.status = SopParseJobStatus.failed
        job.error_message = error_message
        return job
