"""Shared required-reason rules for instrument voids and audited changes.

Void stays at 1000 characters. Schedule, maintenance_tracked, and type
deactivate reasons use 4000. Visible-text (including NBSP / U+2007 as
blank) is the same check for every caller.
"""
from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from app.core.visible_text import has_visible_text

VOID_REASON_MAX = 1000
CHANGE_REASON_MAX = 4000


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
    max_length: int = CHANGE_REASON_MAX,
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
