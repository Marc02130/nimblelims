"""Refuse an instrument that must not start a run, import, or use."""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.lab_time import current_lab_day
from models.instrument import (
    Instrument,
    InstrumentDowntime,
    InstrumentMaintenanceSchedule,
)

INSTRUMENT_DOWN = "instrument_down"
INSTRUMENT_INACTIVE = "instrument_inactive"
INSTRUMENT_RETIRED = "instrument_retired"
INSTRUMENT_OUT_OF_SERVICE = "instrument_out_of_service"
INSTRUMENT_OVERDUE = "instrument_overdue"
INSTRUMENT_NO_SCHEDULE = "instrument_no_schedule"
INSTRUMENT_AWAITING_FIRST_DUE = "instrument_awaiting_first_due"


def _stop(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": code, "message": message},
    )


def instrument_block_reason(
    db: Session, instrument_id: UUID, today: Optional[date] = None
) -> Optional[dict]:
    """Return the first 422 payload that blocks this instrument, or None.

    populate_existing() picks up a status or active change committed by
    another transaction (for example while import_file was parsing).
    """
    row = db.execute(
        select(Instrument)
        .where(Instrument.id == instrument_id)
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if row is None:
        return {"code": "instrument_not_found", "message": "Instrument not found."}
    label = row.name or "This instrument"
    if row.status == "retired":
        return {
            "code": INSTRUMENT_RETIRED,
            "message": f"{label} is retired and cannot be used.",
        }
    if row.status == "out_of_service":
        return {
            "code": INSTRUMENT_OUT_OF_SERVICE,
            "message": f"{label} is out of service and cannot be used.",
        }
    if row.active is not True:
        return {
            "code": INSTRUMENT_INACTIVE,
            "message": f"{label} is inactive and cannot be used.",
        }
    open_down = (
        db.query(InstrumentDowntime)
        .filter(
            InstrumentDowntime.instrument_id == instrument_id,
            InstrumentDowntime.active.is_(True),
            InstrumentDowntime.ended_at.is_(None),
        )
        .first()
    )
    if open_down is not None:
        return {
            "code": INSTRUMENT_DOWN,
            "message": f"{label} is down and cannot be used.",
        }
    if row.maintenance_tracked is not True:
        return None
    due = today if today is not None else current_lab_day()
    schedules = (
        db.query(InstrumentMaintenanceSchedule)
        .filter(
            InstrumentMaintenanceSchedule.instrument_id == instrument_id,
            InstrumentMaintenanceSchedule.active.is_(True),
        )
        .all()
    )
    if not schedules:
        return {
            "code": INSTRUMENT_NO_SCHEDULE,
            "message": (
                f"{label} is tracked for maintenance but has no active schedule "
                "and cannot be used."
            ),
        }
    awaiting = next(
        (schedule for schedule in schedules if schedule.next_due is None),
        None,
    )
    if awaiting is not None:
        return {
            "code": INSTRUMENT_AWAITING_FIRST_DUE,
            "message": (
                f"{label} is awaiting its first due date and cannot be used. "
                "A lab admin or manager sets it."
            ),
        }
    overdue = next(
        (schedule for schedule in schedules if schedule.next_due is not None and schedule.next_due < due),
        None,
    )
    if overdue is not None:
        due_text = overdue.next_due.isoformat()
        return {
            "code": INSTRUMENT_OVERDUE,
            "message": (
                f"{label} is overdue for calibration or maintenance "
                f"(next due {due_text}) and cannot be used."
            ),
        }
    return None


def refuse_ineligible_instrument(db: Session, instrument_id: UUID) -> Instrument:
    reason = instrument_block_reason(db, instrument_id)
    row = db.get(Instrument, instrument_id)
    if reason is None and row is not None:
        return row
    if reason and reason.get("code") == "instrument_not_found":
        raise HTTPException(status_code=404, detail="Instrument not found")
    raise _stop(reason["code"], reason["message"])
