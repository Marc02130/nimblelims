"""Shared 'not in the future' check for schema validators.

Timestamps in this app are stored as naive UTC (``datetime.utcnow()`` /
Postgres ``now()`` in a UTC session). The validators used to compare against
naive *local* ``datetime.now()``, which (a) rejects freshly stored UTC values on
any host west of UTC (e.g. a dev box in America/New_York: SampleResponse fails
to serialize a sample received a minute ago) and (b) raises TypeError for
timezone-aware input such as ``2026-01-01T00:00:00Z``.
"""
from datetime import date, datetime, timezone
from typing import Optional


def is_future(value, *, today: Optional[date] = None) -> bool:
    """True when ``value`` is after the comparison day.

    Datetimes stay on the UTC clock. A calendar date uses ``today`` when the
    caller passes one (the lab's day for a reagent use) and UTC otherwise.
    """
    if value is None:
        return False
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value > datetime.now(timezone.utc)
        return value > datetime.utcnow()
    if today is not None:
        return value > today
    return value > datetime.now(timezone.utc).date()
