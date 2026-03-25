"""
ExperimentProcess and ProcessStep models.

experiment_processes   — named sub-process within an experiment_run (e.g. "Sample Prep",
                         "Plate Reading", "Data Review")
process_steps          — ordered steps within a process
                         status: queued → in_process → complete | failed (terminal)

These tables are additive; the flexible experiment engine schema is left intact.

State diagram for ProcessStep:

    queued ──► in_process ──► complete
      │              │
      └──────────────┴──► failed   (terminal)
"""
import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ProcessStepStatus(str, enum.Enum):
    queued = "queued"
    in_process = "in_process"
    complete = "complete"
    failed = "failed"


# Valid forward transitions (service layer enforces these)
VALID_STEP_TRANSITIONS: dict[ProcessStepStatus, set[ProcessStepStatus]] = {
    ProcessStepStatus.queued:      {ProcessStepStatus.in_process, ProcessStepStatus.failed},
    ProcessStepStatus.in_process:  {ProcessStepStatus.complete, ProcessStepStatus.failed},
    ProcessStepStatus.complete:    set(),   # terminal
    ProcessStepStatus.failed:      set(),   # terminal
}


class ExperimentProcess(Base):
    """
    A named sub-process within an experiment_run.

    Examples: "Sample Preparation", "Plate Reading", "Data Review".
    Each process owns an ordered list of ProcessStep records.

    Lifecycle: determined by the aggregate state of its steps. The process
    itself carries no status column — callers derive status from steps.
    """
    __tablename__ = 'experiment_processes'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_runs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Ordering within a run — lower numbers execute first
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    experiment_run = relationship("ExperimentRun")
    steps = relationship(
        "ProcessStep",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="ProcessStep.sort_order",
    )
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class ProcessStep(Base):
    """
    A single ordered step within an ExperimentProcess.

    Status lifecycle:
        queued      → in_process  (started_at set)
        in_process  → complete    (completed_at set)
        any         → failed      (failed_at set)

    notes — free-text field updated at any time (e.g., technician observations).
    """
    __tablename__ = 'process_steps'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('experiment_processes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(
        SAEnum(ProcessStepStatus, name='process_step_status', create_type=False),
        nullable=False,
        default=ProcessStepStatus.queued,
    )
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    process = relationship("ExperimentProcess", back_populates="steps")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])
