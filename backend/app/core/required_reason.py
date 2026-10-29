"""Shared required-reason rules for instrument voids and audited changes.

All required reasons (void, schedule, maintenance_tracked, type
deactivate) share one max of 4000 characters (Marc 2026-10-29).
Visible-text (including NBSP / U+2007 as blank) is the same check for
every caller.
"""
from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from app.core.visible_text import has_visible_text

REASON_MAX = 4000
VOID_REASON_MAX = REASON_MAX
CHANGE_REASON_MAX = REASON_MAX


def refuse_reason(code: str, message: str) -> NoReturn:
    raise HTTPException(status_code=422, detail={"code": code, "message": message})


def optional_reason(value: str | None) -> str | None:
    """Whitespace-only (including Unicode spaces) becomes null."""
    if value is None or not has_visible_text(value):
        return None
    return value.strip()


def require_reason(
    value: str | None,
    *,
    code: str,
    message: str,
    max_length: int = REASON_MAX,
) -> str:
    if not has_visible_text(value):
        refuse_reason(code, message)
    text = (value or "").strip()
    if len(text) > max_length:
        refuse_reason(
            code,
            f"Reason must be at most {max_length} characters.",
        )
    return text
