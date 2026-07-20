"""
Flexible experiment engine models (Phase 1).

lims_runs      — lifecycle-managed instances of experiment_templates
                       status: draft → running → complete → published | failed
lims_run_data      — JSONB result rows from instrument imports, per run
data_parsers         — versioned file parse instructions (instrument XOR CRO)
robot_worklist_configs — source/dest/volume config for liquid handling robot worklists
sop_parse_jobs       — tracks async Claude API SOP extraction jobs

These tables are additive; the existing experiments/experiment_templates schema
is left intact.
"""
import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SAEnum, Boolean, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class LimsRunStatus(str, enum.Enum):
    """Lifecycle states for an LIMS run.

    Standard lifecycle (lifecycle_type='standard'):
        draft ──► running ──► complete ──► published
          └──────────────────────┴──► failed | canceled

    CRO lifecycle (lifecycle_type='cro'):
        draft ──► ordered ──► running ──► results_received ──► complete ──► published
          └──────────────────────────────────────┴──► failed | canceled
    """
    draft = "draft"
    ordered = "ordered"                    # CRO: experiment sent to CRO
    running = "running"
    results_received = "results_received"  # CRO: instrument data returned by CRO
    complete = "complete"
    published = "published"
    failed = "failed"
    canceled = "canceled"


# Standard in-house lifecycle
VALID_TRANSITIONS: dict[LimsRunStatus, set[LimsRunStatus]] = {
    LimsRunStatus.draft:            {LimsRunStatus.running, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.running:          {LimsRunStatus.complete, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.complete:         {LimsRunStatus.published, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.published:        set(),
    LimsRunStatus.failed:           set(),
    LimsRunStatus.canceled:         set(),
    LimsRunStatus.ordered:          set(),   # not used in standard
    LimsRunStatus.results_received: set(),   # not used in standard
}

# CRO lifecycle — experiments executed by external Contract Research Organizations
VALID_TRANSITIONS_CRO: dict[LimsRunStatus, set[LimsRunStatus]] = {
    LimsRunStatus.draft:            {LimsRunStatus.ordered, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.ordered:          {LimsRunStatus.running, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.running:          {LimsRunStatus.results_received, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.results_received: {LimsRunStatus.complete, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.complete:         {LimsRunStatus.published, LimsRunStatus.failed, LimsRunStatus.canceled},
    LimsRunStatus.published:        set(),
    LimsRunStatus.failed:           set(),
    LimsRunStatus.canceled:         set(),
}

# Registry — keyed by experiment_templates.lifecycle_type
LIFECYCLE_TRANSITIONS: dict[str, dict[LimsRunStatus, set[LimsRunStatus]]] = {
    "standard": VALID_TRANSITIONS,
    "cro":      VALID_TRANSITIONS_CRO,
}


class SopParseJobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class LimsRun(Base):
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
    __tablename__ = 'lims_runs'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Global unique name (DB constraint uq_lims_runs_name) — same policy as experiments/templates.
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    experiment_template_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_templates.id'),
        nullable=False,
        index=True,
    )
    # Opt-in for promote-on-publish: when set, publish writes tests/results for this analysis
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('analyses.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    status = Column(
        SAEnum(LimsRunStatus, name='lims_run_status', create_type=False),
        nullable=False,
        default=LimsRunStatus.draft,
    )
    fit_in_progress = Column(Boolean, nullable=False, server_default='false', default=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_template = relationship("ExperimentTemplate")
    analysis = relationship("Analysis", foreign_keys=[analysis_id])
    data_rows = relationship(
        "LimsRunData",
        back_populates="lims_run",
        cascade="all, delete-orphan",
    )
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class LimsRunData(Base):
    """
    One row of instrument data imported into an LIMS run.

    container_id → the plate/rack Container the well belongs to.
    well_position → e.g. "A1", "B12".
    sample_id → resolved via Contents at import time; null if well not in Contents.
    row_data (JSONB) → the raw instrument columns after parser_config mapping.
    """
    __tablename__ = 'lims_run_data'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_runs.id', ondelete='CASCADE'),
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
    import_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_run_imports.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    lims_run = relationship("LimsRun", back_populates="data_rows")
    container = relationship("Container")
    sample = relationship("Sample")
    lims_run_import = relationship("LimsRunImport", foreign_keys=[import_id])
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class DataParser(Base):
    """
    Versioned declarative parse instructions for instrument or CRO files.

    Each row is one immutable version. Logical parser = version_group_id.
    Exactly one of instrument_id / cro_source_id. At most one active per group.
    """
    __tablename__ = 'data_parsers'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parser_config = Column(JSONB, nullable=False, server_default='{}')
    instrument_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('instruments.id'),
        nullable=True,
        index=True,
    )
    cro_source_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('cro_sources.id'),
        nullable=True,
        index=True,
    )
    version_group_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    instrument = relationship("Instrument", foreign_keys=[instrument_id])
    cro_source = relationship("CroSource", foreign_keys=[cro_source_id])
    analyses_links = relationship(
        "ParserAnalysis",
        back_populates="parser",
        cascade="all, delete-orphan",
    )
    setup_files = relationship(
        "ParserSetupFile",
        back_populates="parser",
        cascade="all, delete-orphan",
    )
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


# Backward-compatible alias
InstrumentParser = DataParser


class ParserAnalysis(Base):
    """M2M: which analyses a data parser version may serve."""
    __tablename__ = 'parser_analyses'

    parser_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('data_parsers.id', ondelete='CASCADE'),
        primary_key=True,
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('analyses.id', ondelete='CASCADE'),
        primary_key=True,
    )
    is_default = Column(Boolean, nullable=False, default=False)

    parser = relationship("DataParser", back_populates="analyses_links")
    analysis = relationship("Analysis")


class ParserSetupFile(Base):
    """Persisted example / test / edge fixtures for parser setup."""
    __tablename__ = 'parser_setup_files'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parser_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('data_parsers.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
    )
    role = Column(String(32), nullable=False)  # example | test | edge_fixture
    filename = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=True)
    size_bytes = Column(Integer, nullable=False)
    content = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    parser = relationship("DataParser", back_populates="setup_files")
    creator = relationship("User", foreign_keys=[created_by])


class LimsRunImport(Base):
    """One import file/batch on a run — stores version parser_id used."""
    __tablename__ = 'lims_run_imports'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_runs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    instrument_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('instruments.id'),
        nullable=True,
    )
    cro_source_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('cro_sources.id'),
        nullable=True,
    )
    parser_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('data_parsers.id'),
        nullable=False,
        index=True,
    )
    filename = Column(String(512), nullable=True)
    imported_at = Column(DateTime, server_default=func.now(), nullable=False)
    imported_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    lims_run = relationship("LimsRun")
    instrument = relationship("Instrument")
    cro_source = relationship("CroSource")
    parser = relationship("DataParser")
    importer = relationship("User", foreign_keys=[imported_by])


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
