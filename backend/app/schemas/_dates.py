"""Shared 'not in the future' check for schema validators.

Timestamps in this app are stored as naive UTC (``datetime.utcnow()`` /
Postgres ``now()`` in a UTC session). A future check compares calendar days
in the lab timezone. A naive datetime is read as UTC, then converted to that
zone, so a sample received this evening still serializes after UTC has rolled
to the next day.
"""
from datetime import date, datetime
from typing import Optional

from app.core.lab_time import clock_date, current_lab_zone


def is_future(value, *, today: Optional[date] = None) -> bool:
    """True when ``value`` is after the lab's today, or after ``today`` when given.

    A date compared with an explicit ``today`` does not need the lab zone.
    A datetime is converted to the lab zone first. ``None`` is not in the future.
    """
    if value is None:
        return False
    if isinstance(value, datetime):
        zone = current_lab_zone()
        day = today if today is not None else clock_date(zone)
        return clock_date(zone, value) > day
    if today is not None:
        return value > today
    return value > clock_date(current_lab_zone())
