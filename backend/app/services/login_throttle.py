"""S15: Postgres-backed login failure lockout."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import (
    LOGIN_MAX_FAILURES,
    LOGIN_LOCKOUT_MINUTES,
    LOGIN_FAILURE_WINDOW_MINUTES,
)


def _max_failures() -> int:
    return LOGIN_MAX_FAILURES


def _lockout_minutes() -> int:
    return LOGIN_LOCKOUT_MINUTES


def _window_minutes() -> int:
    return LOGIN_FAILURE_WINDOW_MINUTES


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


class LoginThrottleService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def check_allowed(self, username: str) -> None:
        """Raise 429 if username is currently locked."""
        key = normalize_username(username)
        if not key:
            return
        row = self.db.execute(
            text(
                """
                SELECT locked_until FROM login_throttle
                WHERE username_normalized = :u
                """
            ),
            {"u": key},
        ).first()
        if not row or row[0] is None:
            return
        locked_until = row[0]
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if locked_until > now:
            retry = int((locked_until - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "login_locked",
                    "message": "Too many failed login attempts. Try again later.",
                    "retry_after_seconds": max(retry, 1),
                },
                headers={"Retry-After": str(max(retry, 1))},
            )
        # Lock expired — clear so next failure starts a fresh window
        self.record_success(username)

    def record_failure(self, username: str) -> Optional[datetime]:
        """
        Increment failure count; lock when threshold reached.
        Returns locked_until if newly locked.
        """
        key = normalize_username(username)
        if not key:
            return None
        now = datetime.now(timezone.utc)
        max_f = _max_failures()
        window = timedelta(minutes=_window_minutes())
        lock_for = timedelta(minutes=_lockout_minutes())

        row = self.db.execute(
            text(
                """
                SELECT failure_count, window_started_at, locked_until
                FROM login_throttle WHERE username_normalized = :u
                """
            ),
            {"u": key},
        ).first()

        if row is None:
            self.db.execute(
                text(
                    """
                    INSERT INTO login_throttle (
                        username_normalized, failure_count, window_started_at,
                        locked_until, updated_at
                    ) VALUES (:u, 1, :now, NULL, :now)
                    """
                ),
                {"u": key, "now": now},
            )
            self.db.flush()
            return None

        failure_count, window_started_at, locked_until = row
        if window_started_at and window_started_at.tzinfo is None:
            window_started_at = window_started_at.replace(tzinfo=timezone.utc)

        if window_started_at and now - window_started_at > window:
            failure_count = 0
            window_started_at = now

        failure_count = int(failure_count or 0) + 1
        new_locked: Optional[datetime] = None
        if failure_count >= max_f:
            new_locked = now + lock_for
            failure_count = 0
            window_started_at = now

        self.db.execute(
            text(
                """
                UPDATE login_throttle SET
                    failure_count = :fc,
                    window_started_at = :ws,
                    locked_until = :lu,
                    updated_at = :now
                WHERE username_normalized = :u
                """
            ),
            {
                "u": key,
                "fc": failure_count,
                "ws": window_started_at or now,
                "lu": new_locked,
                "now": now,
            },
        )
        self.db.flush()
        return new_locked

    def record_success(self, username: str) -> None:
        key = normalize_username(username)
        if not key:
            return
        self.db.execute(
            text("DELETE FROM login_throttle WHERE username_normalized = :u"),
            {"u": key},
        )
        self.db.flush()
