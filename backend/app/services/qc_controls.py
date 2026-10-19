"""Positive and negative controls are a code on the sample's QC type.

``samples.qc_type`` points at a ``list_entries`` row. The display ``name``
is lab-editable ('Positive Control' in the seed, anything after a rename).
The stable designation is ``list_entries.code``: ``positive`` or ``negative``.
"""
from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.list import ListEntry

POSITIVE = "positive"
NEGATIVE = "negative"
CONTROL_CODES = frozenset({POSITIVE, NEGATIVE})


def control_code(entry: Optional[ListEntry]) -> Optional[str]:
    """``positive``, ``negative``, or None. A missing entry is not a control."""
    if entry is None:
        return None
    code = entry.code
    if code is None:
        return None
    if code in CONTROL_CODES:
        return code
    return None


def codes_for_qc_types(db: Session, qc_type_ids: Iterable[Optional[UUID]]) -> dict:
    """Map QC-type ids to their control code. Ids with no code are omitted."""
    ids = [qc_id for qc_id in qc_type_ids if qc_id is not None]
    if not ids:
        return {}
    rows = db.query(ListEntry).filter(ListEntry.id.in_(ids)).all()
    coded = {}
    for row in rows:
        code = control_code(row)
        if code is None:
            continue
        coded[row.id] = code
    return coded


def missing_control(kind: str) -> HTTPException:
    """422 when a fit has no wells for one control role."""
    if kind == POSITIVE:
        code = "missing_positive_control"
        message = (
            "No positive control wells were found. "
            "Set the sample QC type code to 'positive'. The display name is not used."
        )
    elif kind == NEGATIVE:
        code = "missing_negative_control"
        message = (
            "No negative control wells were found. "
            "Set the sample QC type code to 'negative'. The display name is not used."
        )
    else:
        raise ValueError(f"unknown control kind {kind!r}")
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": code, "message": message},
    )
