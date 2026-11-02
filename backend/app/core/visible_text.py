"""Treat tab/newline/other whitespace-only strings as blank."""
from __future__ import annotations

import re

_VISIBLE = re.compile(r"\S")


def has_visible_text(value: str | None) -> bool:
    return bool(value) and _VISIBLE.search(value) is not None
