"""Unique-constraint violations are a 409 with a plain reason, not a 500 (UAT 67481e9)."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

UNIQUE_VIOLATION = "23505"


def constraint_name(exc: IntegrityError) -> Optional[str]:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)


def is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc, "orig", None), "pgcode", None) == UNIQUE_VIOLATION


def commit_or_409(db: Session, messages: dict[str, str], default: str = "That record already exists.") -> None:
    """Commit; on a unique violation roll back and raise 409 with the message for that constraint."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if not is_unique_violation(exc):
            raise
        raise HTTPException(status.HTTP_409_CONFLICT, messages.get(constraint_name(exc) or "", default)) from exc
