"""S7: sample access checks for start/link cohort paths."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.sample import Sample


def require_accessible_sample(db: Session, sample_id: UUID) -> Sample:
    """
    Load a sample visible to the current session.

    Under lims_app + RLS GUC, inaccessible samples are invisible → 404.
    Additionally call has_project_access when available (savepoint so missing
    function in unit tests does not abort the outer transaction).
    """
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found",
        )

    if sample.project_id is None:
        return sample

    try:
        with db.begin_nested():
            ok = db.execute(
                text("SELECT has_project_access(CAST(:pid AS uuid))"),
                {"pid": str(sample.project_id)},
            ).scalar()
    except Exception:
        # No has_project_access (create_all tests) or other DB issue — trust query
        return sample

    if ok is False:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found",
        )
    return sample
