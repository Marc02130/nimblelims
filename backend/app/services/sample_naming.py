"""Child-sample names minted by derivative and pool transfers.

Existing rows are left as they were named. A rename migration is not used:
printed labels and audit history keep the name that was stored, and nothing
queries on the infix.
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4


def minted_child_name(parent_name: Optional[str], infix: str) -> str:
    """Return ``{parent}-{infix}-{token}`` within the 255-character name limit.

    ``infix`` is ``DER`` for a derivative (new sample type) and ``ALQ`` for a
    pool. A blank parent name falls back to ``{infix}-{token}``.
    """
    if parent_name and parent_name.strip():
        token = uuid4().hex[:6]
        suffix = f"-{infix}-{token}"
        stem = parent_name.strip()
        keep = 255 - len(suffix)
        if keep < 1:
            return suffix[-255:]
        return f"{stem[:keep]}{suffix}"
    return f"{infix}-{uuid4().hex[:8]}"
