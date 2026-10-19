"""The lab's calendar date.

The zone lives on ``lab_settings``. There is no UTC default and no
environment fallback. An empty, blank, or missing timezone fails until an
administrator saves a real IANA name with ``PATCH /v1/lab-settings``.

Importing this module does not touch the database, so Alembic can run before
the table exists. The API starts without a zone so that login and the admin
setup step can run.
"""
import threading
from datetime import date, datetime, timezone, tzinfo
from typing import Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from models.lab_setting import LAB_SETTINGS_ID, LabSetting

UNSET_MESSAGE = "lab timezone not configured: set lab_settings.timezone"
INVALID_TIMEZONE = "invalid_timezone"
LAB_TIMEZONE_INVALID = "lab_timezone_invalid"
LAB_TIMEZONE_UNSET = "lab_timezone_not_configured"
# tzfile leftovers. Some hosts list them in available_timezones() and
# pg_timezone_names, so the two-catalog AND is not enough on its own.
_LEFTOVER_ZONES = frozenset({"Factory", "localtime", "posixrules"})


class LabTimezoneInvalid(RuntimeError):
    """The saved zone is non-blank and not a known IANA name.

    A request that resolves the zone is answered 503 ``lab_timezone_invalid``.
    An administrator can still PATCH /v1/lab-settings.
    """


class LabTimezoneUnset(RuntimeError):
    """No saved IANA zone. An administrator must PATCH /v1/lab-settings."""


def known_zone(name: str) -> tzinfo:
    """Return the IANA zone. Raises ValueError when the name is blank or unknown.

    The name must be in ``zoneinfo.available_timezones()`` and must not
    be a leftover such as ``localtime``, ``posixrules``, or ``Factory``.
    Postgres must still accept the name on PATCH.
    """
    cleaned = name.strip()
    if (
        cleaned == ""
        or cleaned in _LEFTOVER_ZONES
        or cleaned not in available_timezones()
    ):
        raise ValueError(cleaned or "empty")
    try:
        return ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(cleaned) from exc


def postgres_accepts_timezone(db: Session, name: str) -> bool:
    """True when Postgres knows ``name`` and ``AT TIME ZONE`` succeeds."""
    found = db.execute(
        text("SELECT 1 FROM pg_catalog.pg_timezone_names WHERE name = :z"),
        {"z": name},
    ).scalar()
    if found is None:
        return False
    nested = db.begin_nested()
    try:
        db.execute(text("SELECT now() AT TIME ZONE :z"), {"z": name})
    except (ProgrammingError, OperationalError):
        nested.rollback()
        return False
    nested.commit()
    return True


def accept_lab_timezone(db: Session, name: str) -> str:
    """The name to store. Raises ValueError when Python or Postgres rejects it."""
    zone = known_zone(name)
    key = getattr(zone, "key", None) or name.strip()
    if key in _LEFTOVER_ZONES or not postgres_accepts_timezone(db, key):
        raise ValueError(key)
    return key


def clock_date(zone_name: str, now: Optional[datetime] = None) -> date:
    """Calendar date of ``now`` (UTC if naive) in ``zone_name``."""
    zone = known_zone(zone_name)
    moment = _utcnow() if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(zone).date()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _missing_table(exc: Exception) -> RuntimeError:
    return RuntimeError(
        "Lab timezone is not available yet. Run migrations before starting the API. "
        + UNSET_MESSAGE
    )


def ensure_lab_setting(db: Session) -> LabSetting:
    """The singleton row, inserted when the table exists and the row does not."""
    try:
        row = db.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        raise _missing_table(exc) from exc
    if row is not None:
        return row
    try:
        with db.begin_nested():
            row = LabSetting(id=LAB_SETTINGS_ID, timezone=None)
            db.add(row)
            db.flush()
    except IntegrityError:
        row = db.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).one()
    return row


def saved_lab_timezone(db: Session) -> Optional[str]:
    """The non-blank saved value, or None. Does not seed. Does not validate."""
    row = ensure_lab_setting(db)
    stored = "" if row.timezone is None else row.timezone.strip()
    if stored == "":
        return None
    return stored


def lab_timezone_configured(db: Session) -> bool:
    """True when a known IANA zone is saved."""
    try:
        resolve_lab_timezone(db)
    except (LabTimezoneUnset, LabTimezoneInvalid):
        return False
    return True


def resolve_lab_timezone(db: Session, *, commit_seed: bool = False) -> str:
    """The saved zone.

    Does not read ``LAB_TIMEZONE`` and does not write a default. Raises
    ``LabTimezoneUnset`` when the row is missing, blank, or NULL. A non-blank
    saved name that ZoneInfo does not know raises ``LabTimezoneInvalid``.
    ``commit_seed`` is ignored; nothing is seeded.
    """
    del commit_seed
    stored = saved_lab_timezone(db)
    if stored is None:
        raise LabTimezoneUnset(UNSET_MESSAGE)
    try:
        known_zone(stored)
    except ValueError as exc:
        raise LabTimezoneInvalid(
            f"The saved lab timezone {stored!r} is not a known IANA time zone. "
            "Update lab_settings.timezone directly, for example "
            "UPDATE lab_settings SET timezone = 'America/New_York'; "
            "If the API is already up, an administrator can PATCH /v1/lab-settings instead."
        ) from exc
    return stored


def lab_today(db: Session, now: Optional[datetime] = None) -> date:
    """Today on the lab's clock. A naive ``now`` is read as UTC."""
    return clock_date(resolve_lab_timezone(db), now)


def is_naive_midnight(value: datetime) -> bool:
    """True when ``value`` is a date-only calendar day stored as naive midnight.

    The UI saves ``YYYY-MM-DD``. Pydantic parses that as a ``datetime`` at
    00:00:00 with no timezone, and most stored sample dates are the same.
    An aware midnight is a real instant and is not a date-only value.
    ``datetime`` is a ``date`` subclass; callers must check ``datetime`` first.
    """
    if value.tzinfo is not None:
        return False
    return (
        value.hour == 0
        and value.minute == 0
        and value.second == 0
        and value.microsecond == 0
    )


def as_calendar_day(value: Union[date, datetime], zone_name: str) -> date:
    """The calendar day of ``value`` in ``zone_name``.

    A naive datetime is lab-zone wall time, midnight or not, so its calendar
    date is ``value.date()``. An offset-bearing datetime is converted into
    the lab zone. A plain ``date`` is already a calendar day.

    This disagrees with the earlier reading that a naive non-midnight value
    is UTC wall time. ``datetime(2026, 10, 19, 2, 0)`` is 2026-10-19 in the
    lab, not the previous evening in America/New_York. Seeded ``utcnow()``
    rows were written as UTC wall time; the date backfill keeps their date
    part (``col::date``) rather than shifting them with
    ``((col AT TIME ZONE 'UTC') AT TIME ZONE lab_zone)::date``.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date()
        return clock_date(zone_name, value)
    return value


def current_lab_day() -> date:
    """Today on the lab clock. ``current_lab_zone`` must already be published."""
    return clock_date(current_lab_zone())


def days_from_today(
    value: Union[date, datetime],
    zone_name: str,
    now: Optional[datetime] = None,
) -> int:
    """Whole calendar days from the lab's today until ``value``. Negative when past."""
    return (as_calendar_day(value, zone_name) - clock_date(zone_name, now)).days


# Validators run before the route body and have no session. The request's
# get_db publishes the zone first; a corrupt saved zone is remembered so the
# validator can raise it without blocking PATCH /v1/lab-settings.
_publish_lock = threading.Lock()
_published_zone: Optional[str] = None
_published_error: Optional[BaseException] = None


def publish_lab_zone(db: Session) -> None:
    """Remember the zone for this process.

    A missing table, an empty row, or a corrupt saved zone is remembered and
    re-raised by a date validator. This function itself does not raise, so
    authentication and PATCH /v1/lab-settings still run.
    """
    global _published_zone, _published_error
    try:
        name = resolve_lab_timezone(db)
    except (LabTimezoneInvalid, LabTimezoneUnset, RuntimeError) as exc:
        with _publish_lock:
            _published_zone = None
            _published_error = exc
        return
    with _publish_lock:
        _published_zone = name
        _published_error = None


def remember_lab_zone(name: str) -> None:
    """Validators see a zone an administrator just saved."""
    global _published_zone, _published_error
    with _publish_lock:
        _published_zone = name
        _published_error = None


def clear_published_lab_zone() -> None:
    global _published_zone, _published_error
    with _publish_lock:
        _published_zone = None
        _published_error = None


def current_lab_zone() -> str:
    """The zone published for this process, or the error that blocked it."""
    with _publish_lock:
        name = _published_zone
        error = _published_error
    if name is not None:
        return name
    if error is not None:
        raise error
    raise LabTimezoneUnset(
        UNSET_MESSAGE + ". An administrator can PATCH /v1/lab-settings."
    )


def require_lab_timezone_on_startup() -> None:
    """The API starts without a zone. An administrator sets it after login."""
    return
