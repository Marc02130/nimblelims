"""The lab's calendar date.

``LAB_TIMEZONE`` (an IANA name such as ``America/New_York``) sets the lab's
clock. Unset means UTC. A server fallback date comes from here, never from the
host clock, so an evening entry in a lab west of UTC is not stamped tomorrow.
"""
import os
from datetime import date, datetime, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def lab_timezone_name() -> str:
    return (os.getenv("LAB_TIMEZONE") or "").strip() or "UTC"


def lab_zone() -> tzinfo:
    name = lab_timezone_name()
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError(f"LAB_TIMEZONE {name!r} is not a known IANA time zone") from exc


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lab_today(now: Optional[datetime] = None) -> date:
    """Today's date on the lab's clock. A naive ``now`` is read as UTC."""
    moment = _utcnow() if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(lab_zone()).date()
