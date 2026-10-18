"""The lab's calendar date.

``LAB_TIMEZONE`` is a required IANA name such as ``America/New_York``. The API
refuses to start when it is missing, blank, or unknown. A server fallback date
comes from this zone, never from the host clock, so an evening entry in a lab
west of UTC is not stamped tomorrow.
"""
import os
from datetime import date, datetime, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_SET_IT = (
    "Set LAB_TIMEZONE to an IANA time zone, for example LAB_TIMEZONE=America/New_York."
)


def lab_timezone_name() -> str:
    raw = os.getenv("LAB_TIMEZONE")
    name = "" if raw is None else raw.strip()
    if name == "":
        raise RuntimeError(f"LAB_TIMEZONE is required. {_SET_IT}")
    return name


def lab_zone() -> tzinfo:
    name = lab_timezone_name()
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError(
            f"LAB_TIMEZONE {name!r} is not a known IANA time zone. {_SET_IT}"
        ) from exc


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lab_today(now: Optional[datetime] = None) -> date:
    """Today's date on the lab's clock. A naive ``now`` is read as UTC."""
    moment = _utcnow() if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(lab_zone()).date()
