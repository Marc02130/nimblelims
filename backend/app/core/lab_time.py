"""The lab's calendar date.

The zone lives on ``lab_settings``. ``LAB_TIMEZONE`` seeds that row only when
it is empty. After that the saved value wins. There is no UTC default.

Importing this module does not touch the database, so Alembic can run before
the table exists. The API process checks the setting at startup, after
migrations.
"""
import os
import threading
from datetime import date, datetime, timezone, tzinfo
from typing import Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from models.lab_setting import LAB_SETTINGS_ID, LabSetting

_EXAMPLE = "Set LAB_TIMEZONE=America/New_York for the first start, or save a zone such as America/New_York."
INVALID_TIMEZONE = "invalid_timezone"
LAB_TIMEZONE_INVALID = "lab_timezone_invalid"


class LabTimezoneInvalid(RuntimeError):
    """The saved zone is non-blank and not a known IANA name.

    Startup still exits, because this is a RuntimeError. A request that
    resolves the zone is answered 503 ``lab_timezone_invalid`` instead.
    """


def env_timezone_name() -> Optional[str]:
    """The first-run seed, or None when the variable is unset or blank."""
    raw = os.getenv("LAB_TIMEZONE")
    name = "" if raw is None else raw.strip()
    if name == "":
        return None
    return name


def known_zone(name: str) -> tzinfo:
    """Return the IANA zone. Raises ValueError when the name is blank or unknown."""
    cleaned = name.strip()
    if cleaned == "":
        raise ValueError("empty")
    try:
        return ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(cleaned) from exc


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
        "LAB_TIMEZONE seeds the setting only after lab_settings exists. "
        + _EXAMPLE
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
    # Parallel requests can all see an empty table. Insert inside a savepoint
    # so the loser of the primary-key race keeps the caller's transaction.
    try:
        with db.begin_nested():
            row = LabSetting(id=LAB_SETTINGS_ID, timezone=None)
            db.add(row)
            db.flush()
    except IntegrityError:
        row = db.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).one()
    return row


def resolve_lab_timezone(db: Session, *, commit_seed: bool = False) -> str:
    """The saved zone, seeding it from ``LAB_TIMEZONE`` when the row is empty.

    Raises RuntimeError when neither source is a valid zone. A non-blank saved
    zone that ZoneInfo does not know raises LabTimezoneInvalid (a RuntimeError).
    A saved value is never replaced by the environment.
    """
    row = ensure_lab_setting(db)
    stored = "" if row.timezone is None else row.timezone.strip()
    if stored == "":
        seed = env_timezone_name()
        if seed is None:
            raise RuntimeError(
                "LAB_TIMEZONE is required until a lab timezone is saved. " + _EXAMPLE
            )
        try:
            known_zone(seed)
        except ValueError as exc:
            raise RuntimeError(
                f"LAB_TIMEZONE {seed!r} is not a known IANA time zone. " + _EXAMPLE
            ) from exc
        row.timezone = seed
        if commit_seed:
            db.commit()
        else:
            db.flush()
        return seed
    try:
        known_zone(stored)
    except ValueError as exc:
        raise LabTimezoneInvalid(
            f"The saved lab timezone {stored!r} is not a known IANA time zone. "
            "Update lab_settings.timezone directly, for example "
            "UPDATE lab_settings SET timezone = 'America/New_York'; "
            "If the API is already up, an administrator can PATCH /v1/lab-settings instead. "
            "LAB_TIMEZONE does not replace a saved value."
        ) from exc
    return stored


def lab_today(db: Session, now: Optional[datetime] = None) -> date:
    """Today on the lab's clock. A naive ``now`` is read as UTC."""
    return clock_date(resolve_lab_timezone(db), now)


def as_calendar_day(value: Union[date, datetime], zone_name: str) -> date:
    """The calendar day of ``value`` in ``zone_name``. A naive datetime is UTC."""
    if isinstance(value, datetime):
        return clock_date(zone_name, value)
    return value


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

    A missing table, an empty row, a bad seed, or a corrupt saved zone is
    remembered and re-raised by a date validator. This function itself does
    not raise, so authentication and PATCH /v1/lab-settings still run.
    """
    global _published_zone, _published_error
    try:
        name = resolve_lab_timezone(db)
    except (LabTimezoneInvalid, RuntimeError) as exc:
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
    raise LabTimezoneInvalid(
        "The lab timezone is not available for this request. "
        "An administrator can PATCH /v1/lab-settings."
    )


def require_lab_timezone_on_startup() -> None:
    """Fail the API process when the lab has no valid zone.

    Tests set ENVIRONMENT=test and build the schema themselves, so they skip
    this. Migrations do not call it.
    """
    if (os.getenv("ENVIRONMENT") or "").strip().lower() == "test":
        return
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        resolve_lab_timezone(db, commit_seed=True)
    finally:
        db.close()
