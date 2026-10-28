"""Maintenance, downtime, and instrument use. Nothing is deleted.

Schedule create, edit, and first-due need Administrator or Lab Manager.
Create of events, downtime, and uses is bench work (experiment:manage).
Passing events recompute next_due only after a lab admin or manager has
set the first due date. Edit, void, and un-void of a maintenance event
are Administrator / Lab Manager only. A technician may create an event
and cannot PATCH one.
"""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.core.lab_time import current_lab_day
from app.core.patch_fields import explicit_updates
from app.core.rbac import require_experiment_manage, require_lab_manager
from app.core.security import get_current_user
from app.database import get_db
from app.schemas.instrument_ops import (
    DowntimeCreate,
    DowntimeResponse,
    DowntimeUpdate,
    ExperimentInstrumentAdd,
    ExperimentInstrumentListResponse,
    ExperimentInstrumentStatus,
    InstrumentUseCreate,
    InstrumentUseResponse,
    InstrumentUseUpdate,
    MaintenanceEventCreate,
    MaintenanceEventResponse,
    MaintenanceEventUpdate,
    FirstDueCreate,
    MaintenanceScheduleCreate,
    MaintenanceScheduleResponse,
    MaintenanceScheduleUpdate,
)
from app.services.instrument_eligibility import refuse_ineligible_instrument
from models.entry import PREDEFINED_ENTRY_DEFAULTS, Entry
from models.experiment import Experiment
from models.flexible_experiment import LimsRun
from models.instrument import (
    Instrument,
    InstrumentDowntime,
    InstrumentMaintenanceEvent,
    InstrumentMaintenanceSchedule,
    InstrumentScheduleAudit,
    InstrumentUse,
)
from models.list import List as ListModel, ListEntry
from models.reagent import Vendor
from models.user import User

schedules_router = APIRouter(prefix="/instrument-maintenance-schedules", tags=["instruments"])
events_router = APIRouter(prefix="/instrument-maintenance-events", tags=["instruments"])
downtime_router = APIRouter(prefix="/instrument-downtime", tags=["instruments"])
uses_router = APIRouter(prefix="/instrument-uses", tags=["instruments"])
experiment_instruments_router = APIRouter(prefix="/experiments", tags=["instruments"])

INSTRUMENT_NOT_ON_EXPERIMENT = "instrument_not_on_experiment"
USE_TARGET_REQUIRED = "use_target_required"
VOIDED_USE_STAYS_VOIDED = "voided_use_stays_voided"


def _refuse(code: str, message: str) -> None:
    raise HTTPException(status_code=422, detail={"code": code, "message": message})


def _audit_text(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _schedule_overdue(row: InstrumentMaintenanceSchedule) -> bool:
    if not row.active or row.next_due is None:
        return False
    return row.next_due < current_lab_day()


def _write_schedule_audit(
    db: Session,
    *,
    instrument_id: UUID,
    action: str,
    user: User,
    schedule_id: Optional[UUID] = None,
    event_id: Optional[UUID] = None,
    previous_value=None,
    new_value=None,
    overdue: Optional[bool] = None,
    reason: Optional[str] = None,
) -> None:
    db.add(
        InstrumentScheduleAudit(
            instrument_id=instrument_id,
            schedule_id=schedule_id,
            event_id=event_id,
            action=action,
            previous_value=_audit_text(previous_value),
            new_value=_audit_text(new_value),
            overdue=overdue,
            reason=(reason.strip() if isinstance(reason, str) else reason) or None,
            created_by=user.id,
        )
    )


def _require_http_certificate(url: Optional[str]) -> None:
    if not url:
        return
    if not (url.startswith("http://") or url.startswith("https://")):
        _refuse(
            "certificate_url_invalid",
            "certificate_url must be an http or https URL.",
        )


def _refuse_future_ended_at(ended_at) -> None:
    if ended_at is None:
        return
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    ended = ended_at if getattr(ended_at, "tzinfo", None) else ended_at.replace(tzinfo=timezone.utc)
    if ended > now:
        _refuse("ended_at_in_future", "ended_at cannot be in the future.")


def _commit(db: Session, row, fail: str):
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=fail)


def _list_entry(
    db: Session,
    list_name: str,
    entry_id: UUID,
    label: str,
    *,
    allow_inactive: bool = False,
) -> ListEntry:
    lst = db.query(ListModel).filter(ListModel.name == list_name).first()
    if lst is None:
        raise HTTPException(status_code=500, detail="A required list is not seeded")
    row = (
        db.query(ListEntry)
        .filter(ListEntry.id == entry_id, ListEntry.list_id == lst.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")
    if row.active is not True and not allow_inactive:
        _refuse(
            "list_entry_inactive",
            f"That {label} is inactive and cannot be used.",
        )
    return row


def _require_instrument(db: Session, instrument_id: UUID) -> Instrument:
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return row


def _schedule_out(row: InstrumentMaintenanceSchedule) -> MaintenanceScheduleResponse:
    return MaintenanceScheduleResponse(
        id=row.id,
        instrument_id=row.instrument_id,
        kind_id=row.kind_id,
        interval_days=row.interval_days,
        last_done=row.last_done,
        next_due=row.next_due,
        service_vendor_id=row.service_vendor_id,
        active=row.active,
        created_at=row.created_at,
        modified_at=row.modified_at,
        kind_name=row.kind.name if row.kind else None,
        instrument_name=row.instrument.name if row.instrument else None,
        service_vendor_name=row.service_vendor.name if row.service_vendor else None,
    )


def _schedule_query(db: Session):
    return db.query(InstrumentMaintenanceSchedule).options(
        joinedload(InstrumentMaintenanceSchedule.kind),
        joinedload(InstrumentMaintenanceSchedule.instrument),
        joinedload(InstrumentMaintenanceSchedule.service_vendor),
    )


def recompute_schedule(db: Session, schedule: InstrumentMaintenanceSchedule) -> None:
    """Advance last_done / next_due from events only after first due is set.

    No passing event (voided-only) returns the item to awaiting first due.
    While next_due is null, an event does not set next_due or last_done.
    """
    latest = (
        db.query(InstrumentMaintenanceEvent)
        .filter(
            InstrumentMaintenanceEvent.schedule_id == schedule.id,
            InstrumentMaintenanceEvent.active.is_(True),
            InstrumentMaintenanceEvent.passed.is_(True),
        )
        .order_by(
            InstrumentMaintenanceEvent.performed_on.desc(),
            InstrumentMaintenanceEvent.created_at.desc(),
        )
        .first()
    )
    if latest is None:
        schedule.last_done = None
        schedule.next_due = None
        return
    if schedule.next_due is None:
        return
    schedule.last_done = latest.performed_on
    schedule.next_due = latest.performed_on + timedelta(days=schedule.interval_days)


# -------------------------------------------------------------- schedules ---

@schedules_router.get("", response_model=List[MaintenanceScheduleResponse])
def list_schedules(
    instrument_id: Optional[UUID] = Query(None),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _schedule_query(db)
    if instrument_id:
        q = q.filter(InstrumentMaintenanceSchedule.instrument_id == instrument_id)
    if not include_inactive:
        q = q.filter(InstrumentMaintenanceSchedule.active.is_(True))
    return [_schedule_out(r) for r in q.order_by(InstrumentMaintenanceSchedule.next_due.asc().nulls_last()).all()]


@schedules_router.get("/{schedule_id}", response_model=MaintenanceScheduleResponse)
def get_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _schedule_query(db).filter(InstrumentMaintenanceSchedule.id == schedule_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    return _schedule_out(row)


@schedules_router.post(
    "", response_model=MaintenanceScheduleResponse, status_code=status.HTTP_201_CREATED
)
def create_schedule(
    body: MaintenanceScheduleCreate,
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    _require_instrument(db, body.instrument_id)
    _list_entry(db, "maintenance_types", body.kind_id, "maintenance type")
    if body.service_vendor_id and not db.query(Vendor).filter(Vendor.id == body.service_vendor_id).first():
        raise HTTPException(status_code=400, detail="Invalid service vendor")
    row = InstrumentMaintenanceSchedule(
        **body.model_dump(),
        next_due=None,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    _commit(db, row, "Could not create maintenance schedule")
    return _schedule_out(_schedule_query(db).filter(InstrumentMaintenanceSchedule.id == row.id).first())


@schedules_router.patch("/{schedule_id}", response_model=MaintenanceScheduleResponse)
def update_schedule(
    schedule_id: UUID,
    body: MaintenanceScheduleUpdate,
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    from sqlalchemy.exc import OperationalError
    from app.core.db_errors import LOCK_NOT_AVAILABLE, QUERY_CANCELED, pgcode

    try:
        row = (
            db.query(InstrumentMaintenanceSchedule)
            .filter(InstrumentMaintenanceSchedule.id == schedule_id)
            .with_for_update()
            .first()
        )
    except OperationalError as exc:
        if pgcode(exc) not in (LOCK_NOT_AVAILABLE, QUERY_CANCELED):
            raise
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "schedule_busy",
                "message": (
                    "Another change to this schedule is in progress. "
                    "Wait for it to finish, then try again."
                ),
            },
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    data = explicit_updates(body, row, refuse_null={"active", "interval_days", "kind_id"})
    if "kind_id" in data:
        _list_entry(
            db,
            "maintenance_types",
            data["kind_id"],
            "maintenance type",
            allow_inactive=data["kind_id"] == row.kind_id,
        )
    if "service_vendor_id" in data and data["service_vendor_id"] is not None:
        if not db.query(Vendor).filter(Vendor.id == data["service_vendor_id"]).first():
            raise HTTPException(status_code=400, detail="Invalid service vendor")
    overdue_at_time = _schedule_overdue(row)
    previous_active = row.active
    previous_interval = row.interval_days
    previous_kind = row.kind_id
    previous_vendor = row.service_vendor_id
    for k, v in data.items():
        setattr(row, k, v)
    # A new interval applies from the next passing event. Recomputing now
    # from last_done would clear an overdue block without that event.
    # Deactivating an overdue schedule is allowed (a retired instrument is
    # legitimate). The active flip and any interval change are audited.
    if "active" in data and row.active is not previous_active:
        _write_schedule_audit(
            db,
            instrument_id=row.instrument_id,
            schedule_id=row.id,
            action="schedule_active",
            user=current_user,
            previous_value=previous_active,
            new_value=row.active,
            overdue=overdue_at_time,
        )
    if "interval_days" in data and row.interval_days != previous_interval:
        _write_schedule_audit(
            db,
            instrument_id=row.instrument_id,
            schedule_id=row.id,
            action="schedule_interval",
            user=current_user,
            previous_value=previous_interval,
            new_value=row.interval_days,
            overdue=overdue_at_time,
        )
    if "kind_id" in data and row.kind_id != previous_kind:
        _write_schedule_audit(
            db,
            instrument_id=row.instrument_id,
            schedule_id=row.id,
            action="schedule_kind",
            user=current_user,
            previous_value=previous_kind,
            new_value=row.kind_id,
            overdue=overdue_at_time,
        )
    if "service_vendor_id" in data and row.service_vendor_id != previous_vendor:
        _write_schedule_audit(
            db,
            instrument_id=row.instrument_id,
            schedule_id=row.id,
            action="schedule_vendor",
            user=current_user,
            previous_value=previous_vendor,
            new_value=row.service_vendor_id,
            overdue=overdue_at_time,
        )
    row.modified_by = current_user.id
    _commit(db, row, "Could not update maintenance schedule")
    return _schedule_out(_schedule_query(db).filter(InstrumentMaintenanceSchedule.id == schedule_id).first())


def _lock_schedule(db: Session, schedule_id: UUID) -> InstrumentMaintenanceSchedule:
    from sqlalchemy.exc import OperationalError
    from app.core.db_errors import LOCK_NOT_AVAILABLE, QUERY_CANCELED, pgcode

    try:
        row = (
            db.query(InstrumentMaintenanceSchedule)
            .filter(InstrumentMaintenanceSchedule.id == schedule_id)
            .with_for_update()
            .first()
        )
    except OperationalError as exc:
        if pgcode(exc) not in (LOCK_NOT_AVAILABLE, QUERY_CANCELED):
            raise
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "schedule_busy",
                "message": (
                    "Another change to this schedule is in progress. "
                    "Wait for it to finish, then try again."
                ),
            },
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    return row


@schedules_router.post(
    "/{schedule_id}/first-due",
    response_model=MaintenanceScheduleResponse,
)
def set_first_due(
    schedule_id: UUID,
    body: FirstDueCreate,
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    row = _lock_schedule(db, schedule_id)
    if row.next_due is not None or row.last_done is not None:
        _refuse(
            "first_due_already_set",
            "The first due date is already set.",
        )
    row.next_due = body.next_due
    row.modified_by = current_user.id
    _write_schedule_audit(
        db,
        instrument_id=row.instrument_id,
        schedule_id=row.id,
        action="first_due",
        user=current_user,
        previous_value=None,
        new_value=body.next_due,
        overdue=_schedule_overdue(row),
        reason=body.reason,
    )
    _commit(db, row, "Could not set the first due date")
    return _schedule_out(_schedule_query(db).filter(InstrumentMaintenanceSchedule.id == schedule_id).first())


# ----------------------------------------------------------------- events ---

def _event_out(row: InstrumentMaintenanceEvent) -> MaintenanceEventResponse:
    return MaintenanceEventResponse.model_validate(row)


@events_router.get("", response_model=List[MaintenanceEventResponse])
def list_events(
    instrument_id: Optional[UUID] = Query(None),
    schedule_id: Optional[UUID] = Query(None),
    include_voided: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(InstrumentMaintenanceEvent)
    if instrument_id:
        q = q.filter(InstrumentMaintenanceEvent.instrument_id == instrument_id)
    if schedule_id:
        q = q.filter(InstrumentMaintenanceEvent.schedule_id == schedule_id)
    if not include_voided:
        q = q.filter(InstrumentMaintenanceEvent.active.is_(True))
    return [
        _event_out(r)
        for r in q.order_by(
            InstrumentMaintenanceEvent.performed_on.desc(),
            InstrumentMaintenanceEvent.created_at.desc(),
        ).limit(500).all()
    ]


@events_router.post(
    "", response_model=MaintenanceEventResponse, status_code=status.HTTP_201_CREATED
)
def create_event(
    body: MaintenanceEventCreate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    _require_instrument(db, body.instrument_id)
    if body.performed_on > current_lab_day():
        _refuse(
            "performed_on_in_future",
            f"performed_on {body.performed_on.isoformat()} is after today in the lab timezone.",
        )
    _require_http_certificate(body.certificate_url)
    if body.performed_by_user_id is None and body.performed_by_vendor_id is None:
        raise HTTPException(
            status_code=422,
            detail="Name who performed the work (user or service vendor)",
        )
    if body.performed_by_user_id and not db.query(User).filter(User.id == body.performed_by_user_id).first():
        raise HTTPException(status_code=400, detail="Invalid performed_by_user_id")
    if body.performed_by_vendor_id and not db.query(Vendor).filter(Vendor.id == body.performed_by_vendor_id).first():
        raise HTTPException(status_code=400, detail="Invalid performed_by_vendor_id")
    schedule = None
    if body.schedule_id:
        schedule = (
            db.query(InstrumentMaintenanceSchedule)
            .filter(InstrumentMaintenanceSchedule.id == body.schedule_id)
            .first()
        )
        if schedule is None:
            raise HTTPException(status_code=404, detail="Maintenance schedule not found")
        if schedule.instrument_id != body.instrument_id:
            raise HTTPException(status_code=400, detail="Schedule belongs to a different instrument")
    row = InstrumentMaintenanceEvent(
        **body.model_dump(),
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(row)
    db.flush()
    if schedule is not None and row.passed and row.active:
        recompute_schedule(db, schedule)
        schedule.modified_by = current_user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not record maintenance event")
    db.refresh(row)
    return _event_out(row)


@events_router.patch("/{event_id}", response_model=MaintenanceEventResponse)
def update_event(
    event_id: UUID,
    body: MaintenanceEventUpdate,
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    row = (
        db.query(InstrumentMaintenanceEvent)
        .filter(InstrumentMaintenanceEvent.id == event_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance event not found")
    if row.schedule_id:
        _lock_schedule(db, row.schedule_id)
    data = explicit_updates(body, row, refuse_null={"active"})
    data.pop("reason", None)
    if "certificate_url" in data:
        _require_http_certificate(data["certificate_url"])
    if "active" in data and data["active"] is False and row.active is False:
        _refuse(VOIDED_USE_STAYS_VOIDED, "A voided maintenance event stays voided.")
    voiding = "active" in data and data["active"] is False and row.active is True
    restoring = "active" in data and data["active"] is True and row.active is not True
    if voiding:
        from app.core.visible_text import has_visible_text

        text = (body.reason or "").strip()
        if not has_visible_text(body.reason):
            _refuse(
                "void_reason_required",
                "A reason is required to void a maintenance event.",
            )
        row.void_reason = text
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    db.flush()
    if row.schedule_id:
        schedule = (
            db.query(InstrumentMaintenanceSchedule)
            .filter(InstrumentMaintenanceSchedule.id == row.schedule_id)
            .first()
        )
        if schedule is not None:
            prior_next_due = schedule.next_due
            overdue_at_time = _schedule_overdue(schedule)
            recompute_schedule(db, schedule)
            schedule.modified_by = current_user.id
            if voiding or restoring:
                _write_schedule_audit(
                    db,
                    instrument_id=row.instrument_id,
                    schedule_id=schedule.id,
                    event_id=row.id,
                    action="event_restore" if restoring else "event_void",
                    user=current_user,
                    previous_value=prior_next_due,
                    new_value=schedule.next_due,
                    overdue=overdue_at_time,
                    reason=row.void_reason if voiding else body.reason,
                )
    elif voiding or restoring:
        _write_schedule_audit(
            db,
            instrument_id=row.instrument_id,
            schedule_id=None,
            event_id=row.id,
            action="event_restore" if restoring else "event_void",
            user=current_user,
            previous_value=None,
            new_value=None,
            overdue=None,
            reason=row.void_reason if voiding else body.reason,
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update maintenance event")
    db.refresh(row)
    return _event_out(row)


# --------------------------------------------------------------- downtime ---

def _downtime_out(row: InstrumentDowntime) -> DowntimeResponse:
    return DowntimeResponse(
        id=row.id,
        instrument_id=row.instrument_id,
        started_at=row.started_at,
        ended_at=row.ended_at,
        reason_id=row.reason_id,
        maintenance_event_id=row.maintenance_event_id,
        note=row.note,
        active=row.active,
        created_at=row.created_at,
        modified_at=row.modified_at,
        reason_name=row.reason.name if row.reason else None,
        instrument_name=row.instrument.name if row.instrument else None,
    )


def _downtime_query(db: Session):
    return db.query(InstrumentDowntime).options(
        joinedload(InstrumentDowntime.reason),
        joinedload(InstrumentDowntime.instrument),
    )


@downtime_router.get("", response_model=List[DowntimeResponse])
def list_downtime(
    instrument_id: Optional[UUID] = Query(None),
    open_only: bool = Query(False),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _downtime_query(db)
    if instrument_id:
        q = q.filter(InstrumentDowntime.instrument_id == instrument_id)
    if open_only:
        q = q.filter(InstrumentDowntime.ended_at.is_(None), InstrumentDowntime.active.is_(True))
    if not include_inactive:
        q = q.filter(InstrumentDowntime.active.is_(True))
    return [
        _downtime_out(r)
        for r in q.order_by(InstrumentDowntime.started_at.desc()).limit(500).all()
    ]


@downtime_router.post("", response_model=DowntimeResponse, status_code=status.HTTP_201_CREATED)
def create_downtime(
    body: DowntimeCreate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    _require_instrument(db, body.instrument_id)
    _list_entry(db, "downtime_reasons", body.reason_id, "downtime reason")
    _refuse_future_ended_at(body.ended_at)
    if body.maintenance_event_id:
        ev = (
            db.query(InstrumentMaintenanceEvent)
            .filter(InstrumentMaintenanceEvent.id == body.maintenance_event_id)
            .first()
        )
        if ev is None:
            raise HTTPException(status_code=404, detail="Maintenance event not found")
    row = InstrumentDowntime(
        **body.model_dump(),
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    _commit(db, row, "Could not record downtime")
    return _downtime_out(_downtime_query(db).filter(InstrumentDowntime.id == row.id).first())


def _lock_downtime(db: Session, downtime_id: UUID) -> InstrumentDowntime:
    from sqlalchemy.exc import OperationalError
    from app.core.db_errors import LOCK_NOT_AVAILABLE, QUERY_CANCELED, pgcode

    try:
        row = (
            db.query(InstrumentDowntime)
            .filter(InstrumentDowntime.id == downtime_id)
            .with_for_update()
            .first()
        )
    except OperationalError as exc:
        if pgcode(exc) not in (LOCK_NOT_AVAILABLE, QUERY_CANCELED):
            raise
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "schedule_busy",
                "message": (
                    "Another change to this downtime is in progress. "
                    "Wait for it to finish, then try again."
                ),
            },
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Downtime not found")
    return row


def _schedule_id_for_event(db: Session, event_id: Optional[UUID]) -> Optional[UUID]:
    if event_id is None:
        return None
    event = (
        db.query(InstrumentMaintenanceEvent)
        .filter(InstrumentMaintenanceEvent.id == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Maintenance event not found")
    return event.schedule_id


def _lock_schedules_in_order(db: Session, *schedule_ids: Optional[UUID]) -> None:
    """Lock distinct schedule rows by id so two re-points cannot deadlock."""
    seen = set()
    ordered = []
    for schedule_id in schedule_ids:
        if schedule_id is None or schedule_id in seen:
            continue
        seen.add(schedule_id)
        ordered.append(schedule_id)
    for schedule_id in sorted(ordered, key=lambda value: value.hex):
        _lock_schedule(db, schedule_id)


@downtime_router.patch("/{downtime_id}", response_model=DowntimeResponse)
def update_downtime(
    downtime_id: UUID,
    body: DowntimeUpdate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    row = _lock_downtime(db, downtime_id)
    data = explicit_updates(body, row, refuse_null={"active"})
    if "reason_id" in data:
        _list_entry(
            db,
            "downtime_reasons",
            data["reason_id"],
            "downtime reason",
            allow_inactive=data["reason_id"] == row.reason_id,
        )
    new_event_id = data["maintenance_event_id"] if "maintenance_event_id" in data else row.maintenance_event_id
    old_schedule_id = _schedule_id_for_event(db, row.maintenance_event_id)
    new_schedule_id = (
        _schedule_id_for_event(db, new_event_id)
        if "maintenance_event_id" in data
        else old_schedule_id
    )
    _lock_schedules_in_order(db, old_schedule_id, new_schedule_id)
    for k, v in data.items():
        setattr(row, k, v)
    _refuse_future_ended_at(row.ended_at)
    if row.ended_at is not None and row.started_at is not None and row.ended_at < row.started_at:
        raise HTTPException(status_code=422, detail="ended_at cannot be before started_at")
    row.modified_by = current_user.id
    _commit(db, row, "Could not update downtime")
    return _downtime_out(_downtime_query(db).filter(InstrumentDowntime.id == downtime_id).first())


# ----------------------------------------------------- experiment list ---

def _stored_ids(config: object, key: str) -> List[str]:
    if not isinstance(config, dict):
        return []
    raw_ids = config.get(key)
    if raw_ids is None or not isinstance(raw_ids, list):
        return []
    stored: List[str] = []
    for raw in raw_ids:
        if raw is None:
            continue
        try:
            stored.append(str(UUID(str(raw))))
        except (ValueError, TypeError):
            continue
    return stored


def _instrument_list_response(experiment_id: UUID, entry) -> ExperimentInstrumentListResponse:
    return ExperimentInstrumentListResponse(
        experiment_id=experiment_id,
        entry_id=entry.id,
        allowed_instrument_ids=_stored_ids(entry.config, "allowed_instrument_ids"),
        removed_instrument_ids=_stored_ids(entry.config, "removed_instrument_ids"),
    )


def _instrument_entry_for(db: Session, experiment_id: UUID):
    rows = (
        db.query(Entry)
        .filter(Entry.experiment_id == experiment_id, Entry.active.is_(True))
        .order_by(Entry.sort_order.asc(), Entry.created_at.asc())
        .all()
    )
    for row in rows:
        if row.entry_type == "instrument" or row.predefined_entry_key == "instruments":
            return row
    return None


def save_experiment_instrument(
    db: Session, experiment_id: UUID, instrument_id: UUID, current_user: User
) -> tuple[ExperimentInstrumentListResponse, bool]:
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    refuse_ineligible_instrument(db, instrument_id)
    key = str(instrument_id)
    entry = _instrument_entry_for(db, experiment_id)
    if entry is None:
        decl = PREDEFINED_ENTRY_DEFAULTS["instruments"]
        max_sort = (
            db.query(func.max(Entry.sort_order))
            .filter(Entry.experiment_id == experiment_id, Entry.active.is_(True))
            .scalar()
        )
        sort_order = 0 if max_sort is None else int(max_sort) + 1
        entry = Entry(
            experiment_id=experiment_id,
            entry_type="instrument",
            name=decl["name"],
            description=decl.get("description"),
            predefined_entry_key="instruments",
            sort_order=sort_order,
            config={"allowed_instrument_ids": [key], "status": "draft"},
            active=True,
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        db.add(entry)
        _commit(db, entry, "Could not save the instrument on this experiment")
        return _instrument_list_response(experiment_id, entry), True

    stored = _stored_ids(entry.config, "allowed_instrument_ids")
    removed = _stored_ids(entry.config, "removed_instrument_ids")
    if key in stored:
        return _instrument_list_response(experiment_id, entry), False
    config = dict(entry.config) if isinstance(entry.config, dict) else {}
    if key in removed:
        config["removed_instrument_ids"] = [item for item in removed if item != key]
    config["allowed_instrument_ids"] = stored + [key]
    config.setdefault("status", "draft")
    entry.config = config
    flag_modified(entry, "config")
    entry.modified_by = current_user.id
    _commit(db, entry, "Could not save the instrument on this experiment")
    return _instrument_list_response(experiment_id, entry), True


def remove_experiment_instrument(
    db: Session, experiment_id: UUID, instrument_id: UUID, current_user: User
) -> ExperimentInstrumentListResponse:
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    entry = _instrument_entry_for(db, experiment_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Experiment has no instrument list")
    key = str(instrument_id)
    stored = _stored_ids(entry.config, "allowed_instrument_ids")
    removed = _stored_ids(entry.config, "removed_instrument_ids")
    if key not in stored:
        if key in removed:
            return _instrument_list_response(experiment_id, entry)
        raise HTTPException(status_code=404, detail="Instrument is not on this experiment")
    config = dict(entry.config) if isinstance(entry.config, dict) else {}
    config["allowed_instrument_ids"] = [item for item in stored if item != key]
    if key not in removed:
        config["removed_instrument_ids"] = removed + [key]
    config.setdefault("status", "draft")
    entry.config = config
    flag_modified(entry, "config")
    entry.modified_by = current_user.id
    _commit(db, entry, "Could not remove the instrument from this experiment")
    return _instrument_list_response(experiment_id, entry)


def _instrument_label(db: Session, instrument_id: UUID) -> str:
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if row is not None and row.name:
        return row.name
    return "This instrument"


def _refuse_instrument_not_on_experiment(db: Session, experiment_id: UUID, instrument_id: UUID) -> None:
    entry = _instrument_entry_for(db, experiment_id)
    stored = _stored_ids(entry.config, "allowed_instrument_ids") if entry is not None else []
    if str(instrument_id) in stored:
        return
    label = _instrument_label(db, instrument_id)
    raise HTTPException(
        status_code=422,
        detail={
            "code": INSTRUMENT_NOT_ON_EXPERIMENT,
            "message": f"{label} isn't on this experiment. Add it before recording use.",
        },
    )


@experiment_instruments_router.post(
    "/{experiment_id}/instruments",
    response_model=ExperimentInstrumentListResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_experiment_instrument(
    experiment_id: UUID,
    body: ExperimentInstrumentAdd,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    payload, created = save_experiment_instrument(db, experiment_id, body.instrument_id, current_user)
    if created:
        return payload
    return Response(
        content=payload.model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )


@experiment_instruments_router.patch(
    "/{experiment_id}/instruments",
    response_model=ExperimentInstrumentListResponse,
)
def update_experiment_instrument(
    experiment_id: UUID,
    body: ExperimentInstrumentStatus,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    if body.active is not False:
        _refuse(
            "instrument_remove_required",
            "Set active to false to remove the instrument. Add it again to restore it.",
        )
    return remove_experiment_instrument(db, experiment_id, body.instrument_id, current_user)


# -------------------------------------------------------------------- uses ---

def _slots_for_use(db: Session, body: InstrumentUseCreate):
    from app.services.instrument_slots import slots_from_config, slots_from_template

    if body.experiment_id is not None:
        entry = None
        if body.entry_id is not None:
            entry = (
                db.query(Entry)
                .filter(Entry.id == body.entry_id, Entry.experiment_id == body.experiment_id)
                .first()
            )
        if entry is None:
            entry = _instrument_entry_for(db, body.experiment_id)
        if entry is None:
            return []
        return slots_from_config(entry.config)
    if body.lims_run_id is not None:
        run = db.query(LimsRun).filter(LimsRun.id == body.lims_run_id).first()
        if run is None or run.experiment_template is None:
            return []
        return slots_from_template(run.experiment_template.template_definition)
    return []


def _assert_use_slot(db: Session, body: InstrumentUseCreate) -> None:
    from app.services.instrument_slots import (
        INSTRUMENT_SLOT_NOT_FOUND,
        assert_slot_type_matches_instrument,
    )

    slots = _slots_for_use(db, body)
    if not slots:
        return
    if not body.slot_key:
        _refuse(
            INSTRUMENT_SLOT_NOT_FOUND,
            "This experiment or run uses instrument slots. Send slot_key.",
        )
    slot = next((s for s in slots if str(s.get("key") or "") == body.slot_key), None)
    if slot is None:
        _refuse(
            INSTRUMENT_SLOT_NOT_FOUND,
            f"Instrument slot '{body.slot_key}' is not on this template.",
        )
    assert_slot_type_matches_instrument(db, slot=slot, instrument_id=body.instrument_id)


def _void_previous_slot_pick(db: Session, body: InstrumentUseCreate, user_id: UUID) -> None:
    if not body.slot_key:
        return
    q = db.query(InstrumentUse).filter(
        InstrumentUse.slot_key == body.slot_key,
        InstrumentUse.active.is_(True),
    )
    if body.entry_id is not None:
        q = q.filter(InstrumentUse.entry_id == body.entry_id)
    elif body.experiment_id is not None:
        q = q.filter(InstrumentUse.experiment_id == body.experiment_id)
    elif body.lims_run_id is not None:
        q = q.filter(InstrumentUse.lims_run_id == body.lims_run_id)
    else:
        return
    rows = q.all()
    for old in rows:
        old.active = False
        old.modified_by = user_id
    if rows:
        db.flush()


def _use_out(row: InstrumentUse) -> InstrumentUseResponse:
    out = InstrumentUseResponse.model_validate(row)
    out.instrument_name = row.instrument.name if row.instrument else None
    return out


@uses_router.get("", response_model=List[InstrumentUseResponse])
def list_instrument_uses(
    lims_run_id: Optional[UUID] = Query(None),
    experiment_id: Optional[UUID] = Query(None),
    instrument_id: Optional[UUID] = Query(None),
    include_voided: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(InstrumentUse).options(joinedload(InstrumentUse.instrument))
    if lims_run_id:
        q = q.filter(InstrumentUse.lims_run_id == lims_run_id)
    if experiment_id:
        q = q.filter(InstrumentUse.experiment_id == experiment_id)
    if instrument_id:
        q = q.filter(InstrumentUse.instrument_id == instrument_id)
    if not include_voided:
        q = q.filter(InstrumentUse.active.is_(True))
    return [
        _use_out(r)
        for r in q.order_by(InstrumentUse.used_on.desc(), InstrumentUse.created_at.desc()).limit(500).all()
    ]


@uses_router.post("", response_model=InstrumentUseResponse, status_code=status.HTTP_201_CREATED)
def record_instrument_use(
    body: InstrumentUseCreate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    if body.entry_id is not None and body.lims_run_id is not None:
        _refuse(
            "use_target_conflict",
            "Send entry_id with experiment_id, not with lims_run_id.",
        )
    if body.entry_id is not None and body.experiment_id is None:
        _refuse(
            "entry_experiment_required",
            "entry_id requires experiment_id.",
        )
    if body.lims_run_id is None and body.experiment_id is None:
        _refuse(USE_TARGET_REQUIRED, "Record the use on a LIMS run or an experiment")
    if body.entry_id is not None:
        entry = db.query(Entry).filter(Entry.id == body.entry_id).first()
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        if entry.experiment_id != body.experiment_id:
            _refuse(
                "entry_experiment_mismatch",
                "This entry does not belong to that experiment.",
            )
    if body.lims_run_id is not None and not db.query(LimsRun).filter(LimsRun.id == body.lims_run_id).first():
        raise HTTPException(status_code=404, detail="LIMS run not found")
    if body.experiment_id is not None and not db.query(Experiment).filter(Experiment.id == body.experiment_id).first():
        raise HTTPException(status_code=404, detail="Experiment not found")
    if body.experiment_id is not None:
        _refuse_instrument_not_on_experiment(db, body.experiment_id, body.instrument_id)
    _assert_use_slot(db, body)
    refuse_ineligible_instrument(db, body.instrument_id)
    _void_previous_slot_pick(db, body, current_user.id)
    payload = body.model_dump()
    payload["used_on"] = current_lab_day()
    row = InstrumentUse(
        **payload,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    _commit(db, row, "Could not record instrument use")
    row = (
        db.query(InstrumentUse)
        .options(joinedload(InstrumentUse.instrument))
        .filter(InstrumentUse.id == row.id)
        .first()
    )
    return _use_out(row)


@uses_router.patch("/{use_id}", response_model=InstrumentUseResponse)
def update_instrument_use(
    use_id: UUID,
    body: InstrumentUseUpdate,
    current_user: User = Depends(require_experiment_manage),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentUse).filter(InstrumentUse.id == use_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Instrument use not found")
    data = explicit_updates(body, row, refuse_null={"active"})
    if "active" in data and data["active"] is True and row.active is not True:
        refuse_ineligible_instrument(db, row.instrument_id)
    if "active" in data and data["active"] is False and row.active is False:
        _refuse(VOIDED_USE_STAYS_VOIDED, "A voided use stays voided.")
    for k, v in data.items():
        setattr(row, k, v)
    row.modified_by = current_user.id
    _commit(db, row, "Could not update instrument use")
    row = (
        db.query(InstrumentUse)
        .options(joinedload(InstrumentUse.instrument))
        .filter(InstrumentUse.id == use_id)
        .first()
    )
    return _use_out(row)
