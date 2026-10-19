"""Shared 'not in the future' check for schema validators.

A future check compares calendar days in the lab timezone. A naive midnight
is a date-only value (``YYYY-MM-DD``, or a row saved that way) and is that
calendar day with no zone shift. Any other datetime, including one with an
offset, is converted into the lab zone. A time that is still today in the
lab is accepted after UTC has rolled to the next day.
"""
from datetime import date, datetime
from typing import Optional

from app.core.lab_time import as_calendar_day, clock_date, current_lab_zone


def is_future(value, *, today: Optional[date] = None) -> bool:
    """True when ``value`` is after the lab's today, or after ``today`` when given.

    A date compared with an explicit ``today`` does not need the lab zone.
    A datetime uses the lab calendar day (naive midnight stays on that day).
    ``None`` is not in the future.
    """
    if value is None:
        return False
    if isinstance(value, datetime):
        zone = current_lab_zone()
        day = today if today is not None else clock_date(zone)
        return as_calendar_day(value, zone) > day
    if today is not None:
        return value > today
    return value > clock_date(current_lab_zone())
