"""
Flexible experiment engine models (Phase 1).

experiment_runs      — lifecycle-managed instances of experiment_templates
                       status: draft → running → complete → published | failed
experiment_data      — JSONB result rows from instrument imports, per run
instrument_parsers   — AI-learned column-mapping config for instrument output files
robot_worklist_configs — source/dest/volume config for liquid handling robot worklists
sop_parse_jobs       — tracks async Claude API SOP extraction jobs

These tables are additive; the existing experiments/experiment_templates schema
is left intact.
"""
import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ExperimentRunStatus(str, enum.Enum):
    """6-state lifecycle for an experiment run.

    Status diagram:
        draft ──► running ──► complete ──► published
          │                       │
          └───────────────────────┴──► failed
    """
    draft = "draft"
    running = "running"
    complete = "complete"
    published = "published"
    failed = "failed"


# Valid forward transitions (service layer enforces these)
VALID_TRANSITIONS: dict[ExperimentRunStatus, set[ExperimentRunStatus]] = {
    ExperimentRunStatus.draft:     {ExperimentRunStatus.running, ExperimentRunStatus.failed},
    ExperimentRunStatus.running:   {ExperimentRunStatus.complete, ExperimentRunStatus.failed},
    ExperimentRunStatus.complete:  {ExperimentRunStatus.published, ExperimentRunStatus.failed},
    ExperimentRunStatus.published: set(),   # terminal
    ExperimentRunStatus.failed:    set(),   # terminal
}


class SopParseJobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class ExperimentRun(Base):
    """
    A single run of an experiment_template.

    Status lifecycle:
        draft → running  (started_at set)
        running → complete (completed_at set)
        complete → published (published_at set; requires experiment:publish permission)
        any → failed

    Worklist generation: disabled unless template has robot_worklist_config
    Data import: only allowed when status == 'running'
    """
    __tablename__ = 'experiment_runs'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # name is unique per client (enforced at the service layer via get_by_name_for_client),
    # NOT globally unique — two client orgs may use identical run names.
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id'),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(ExperimentRunStatus, name='experiment_run_status', create_type=False),
        nullable=False,
        default=ExperimentRunStatus.draft,
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_template = relationship("ExperimentTemplate")
    data_rows = relationship(
        "ExperimentData",
        back_populates="experiment_run",
        cascade="all, delete-orphan",
    )
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class ExperimentData(Base):
    """
    One row of instrument data imported into an experiment run.

    container_id → the plate/rack Container the well belongs to.
    well_position → e.g. "A1", "B12".
    sample_id → resolved via Contents at import time; null if well not in Contents.
    row_data (JSONB) → the raw instrument columns after parser_config mapping.
    """
    __tablename__ = 'experiment_data'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_runs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    container_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('containers.id'),
        nullable=True,
        index=True,
    )
    well_position = Column(String(10), nullable=True)
    sample_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('samples.id'),
        nullable=True,
        index=True,
    )
    row_data = Column(JSONB, nullable=False, server_default='{}')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_run = relationship("ExperimentRun", back_populates="data_rows")
    container = relationship("Container")
    sample = relationship("Sample")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class InstrumentParser(Base):
    """
    AI-learned column-mapping config for an instrument output format.

    parser_config schema (JSONB):
    {
      "columns": [
        {"source_col": "Well", "field_name": "well_position", "data_type": "string"},
        {"source_col": "RFU", "field_name": "rfu_value", "data_type": "float", "unit": "RFU"}
      ],
      "well_col": "Well",   // which column identifies the well position
      "skip_rows": 2        // header rows to skip before data starts
    }
    """
    __tablename__ = 'instrument_parsers'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parser_config = Column(JSONB, nullable=False, server_default='{}')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_template = relationship("ExperimentTemplate")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class RobotWorklistConfig(Base):
    """
    Source/dest/volume mapping config for generating robot worklist CSV files.

    worklist_config schema (JSONB):
    {
      "steps": [
        {
          "step": 1,
          "source_plate": "Rack1",
          "source_well_col": "source_well",
          "dest_plate": "Plate1",
          "dest_well_col": "dest_well",
          "volume_col": "transfer_volume_ul",
          "mandatory_review": true
        }
      ]
    }
    Export: generic CSV with columns source_well, dest_well, volume (µL).
    Hamilton-specific format deferred (see TODOS.md).
    """
    __tablename__ = 'robot_worklist_configs'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    worklist_config = Column(JSONB, nullable=False, server_default='{}')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_template = relationship("ExperimentTemplate")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class SopParseJob(Base):
    """
    Tracks an async Claude API SOP extraction job.

    Flow:
        POST /sop-parse → create job (status=pending), kick off background task
        Background task → status=processing → calls Claude API
        Success → status=complete, result=<extracted JSONB>
        Failure → status=failed, error_message=<reason>
        GET /sop-parse/:id → poll status

    result schema (JSONB) — set on complete:
    {
      "template_definition": {...},
      "parser_config": {...},
      "worklist_config": {...}
    }
    """
    __tablename__ = 'sop_parse_jobs'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id'),
        nullable=True,
        index=True,
    )
    status = Column(
        SAEnum(SopParseJobStatus, name='sop_parse_job_status', create_type=False),
        nullable=False,
        default=SopParseJobStatus.pending,
    )
    sop_filename = Column(String(512), nullable=True)
    instrument_filename = Column(String(512), nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_template = relationship("ExperimentTemplate")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])
