"""
LIMS run checklists — named sub-checklists within a lims_run.

lims_run_checklists       — e.g. "Sample Prep", "Plate Reading", "Data Review"
lims_run_checklist_steps  — ordered steps (queued → in_process → complete | failed)

Distinct from ELN Processes (eln_processes / eln_process_steps).
"""
import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class LimsRunChecklistStepStatus(str, enum.Enum):
    queued = "queued"
    in_process = "in_process"
    complete = "complete"
    failed = "failed"


VALID_CHECKLIST_STEP_TRANSITIONS: dict[
    LimsRunChecklistStepStatus, set[LimsRunChecklistStepStatus]
] = {
    LimsRunChecklistStepStatus.queued: {
        LimsRunChecklistStepStatus.in_process,
        LimsRunChecklistStepStatus.failed,
    },
    LimsRunChecklistStepStatus.in_process: {
        LimsRunChecklistStepStatus.complete,
        LimsRunChecklistStepStatus.failed,
    },
    LimsRunChecklistStepStatus.complete: set(),
    LimsRunChecklistStepStatus.failed: set(),
}


class LimsRunChecklist(Base):
    """A named checklist group within a LIMS run."""

    __tablename__ = 'lims_run_checklists'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lims_run_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_runs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    lims_run = relationship("LimsRun")
    steps = relationship(
        "LimsRunChecklistStep",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="LimsRunChecklistStep.sort_order",
    )
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])


class LimsRunChecklistStep(Base):
    """One ordered step within a LimsRunChecklist."""

    __tablename__ = 'lims_run_checklist_steps'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('lims_run_checklists.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(
        SAEnum(
            LimsRunChecklistStepStatus,
            name='lims_run_checklist_step_status',
            create_type=False,
        ),
        nullable=False,
        default=LimsRunChecklistStepStatus.queued,
    )
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    checklist = relationship("LimsRunChecklist", back_populates="steps")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[modified_by])
