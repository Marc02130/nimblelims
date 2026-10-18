"""The lab's calendar date.

The zone lives on ``lab_settings``. ``LAB_TIMEZONE`` seeds that row only when
it is empty. After that the saved value wins. There is no UTC default.

Importing this module does not touch the database, so Alembic can run before
the table exists. The API process checks the setting at startup, after
migrations.
"""
import os
from datetime import date, datetime, timezone, tzinfo
from typing import Optional
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
