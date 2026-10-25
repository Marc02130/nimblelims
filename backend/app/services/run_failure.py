"""When a LIMS run has already run, and when it counts as failed.

A run with any stored import row has already run. It cannot be canceled; if
something is wrong it is failed (status ``failed`` with a reason). Older runs
that were canceled after import keep their status, but count as failed when a
reviewer accepts one of their values. Nothing is rewritten.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Set

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from models.flexible_experiment import LimsRun, LimsRunData, LimsRunStatus


def has_imported_data(db: Session, run_id: uuid.UUID) -> bool:
    """True when any import attempt stored a row on this run, linked or not."""
    return bool(
        db.execute(select(exists().where(LimsRunData.lims_run_id == run_id))).scalar()
    )


def runs_with_imported_data(db: Session, run_ids: Iterable[uuid.UUID]) -> Set[uuid.UUID]:
    """The subset of ``run_ids`` that have any stored import row, in one query."""
    ids = list(run_ids)
    if not ids:
        return set()
    return set(
        db.execute(
            select(LimsRunData.lims_run_id)
            .where(LimsRunData.lims_run_id.in_(ids))
            .distinct()
        ).scalars()
    )


def _status(run: LimsRun) -> str:
    return run.status.value if hasattr(run.status, "value") else str(run.status)


def counts_as_failed(db: Session, run: LimsRun) -> bool:
    """Failed, or canceled after data was imported (legacy rows)."""
    value = _status(run)
    if value == LimsRunStatus.failed.value:
        return True
    return value == LimsRunStatus.canceled.value and has_imported_data(db, run.id)
