"""Atomic draw-down of a tracked contents amount.

One UPDATE ... WHERE amount >= transfer so two concurrent draws cannot both
succeed. The contents row stays when the remainder is zero. Nothing is deleted.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models.container import Contents


def debit_contents_amount(
    db: Session,
    source: Contents,
    transfer: Decimal,
    *,
    sample_label: Optional[str] = None,
) -> Decimal:
    """Subtract ``transfer`` from ``source`` and return the remainder.

    Raises 400 ``source_amount_null`` when the vessel has no tracked amount,
    400 ``insufficient_amount`` when the draw is larger than the vessel, and
    503 ``source_busy`` when the row lock times out.
    """
    if transfer <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "amount_required",
                "message": "A positive amount is required so the source vessel can be debited.",
            },
        )
    if source.amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "source_amount_null",
                "message": _null_amount_message(sample_label),
            },
        )
    try:
        remaining = db.execute(
            update(Contents)
            .where(
                Contents.container_id == source.container_id,
                Contents.sample_id == source.sample_id,
                Contents.amount.is_not(None),
                Contents.amount >= transfer,
            )
            .values(amount=Contents.amount - transfer)
            .returning(Contents.amount)
            .execution_options(synchronize_session="fetch")
        ).scalar_one_or_none()
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "source_busy",
                "message": "The source vessel is busy; try again.",
            },
        ) from exc
    if remaining is None:
        current = (
            db.query(Contents.amount)
            .filter(
                Contents.container_id == source.container_id,
                Contents.sample_id == source.sample_id,
            )
            .scalar()
        )
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "source_amount_null",
                    "message": _null_amount_message(sample_label),
                },
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "insufficient_amount",
                "message": (
                    f"Insufficient amount on source contents: have {current}, "
                    f"need {transfer}"
                ),
            },
        )
    return Decimal(remaining)


def _null_amount_message(sample_label: Optional[str]) -> str:
    if sample_label:
        return (
            f"Source contents amount is null for sample {sample_label}; "
            "set a tracked amount before execute"
        )
    return "Source contents amount is null; set a tracked amount before drawing from this vessel."
