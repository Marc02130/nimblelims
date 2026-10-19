"""Shared calendar-day helpers for schema validators.

Lab-day columns are SQL ``date``. Instant columns are
``timestamptz``. A future check compares calendar days in the lab timezone.
A naive midnight is a date-only value (``YYYY-MM-DD``, or a row saved that
way) and is that calendar day with no zone shift. Any other datetime,
including one with an offset, is converted into the lab zone. A time that
is still today in the lab is accepted after UTC has rolled to the next day.

Storage of a calendar value is naive midnight of the lab day, then a SQL
``date``. A naive non-midnight value keeps its own date (lab-zone wall
time). Response models do not call ``store_calendar_day``; a row already
saved is returned as stored.
"""
from datetime import date, datetime
from typing import Optional, Union

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


def store_calendar_day(value: Optional[Union[date, datetime]]):
    """Persist a calendar field as the lab day's naive midnight.

    ``None`` stays ``None``. A plain ``date`` becomes naive midnight of that
    day. A naive ``datetime`` is lab-zone wall time, so midnight and
    non-midnight both become midnight of ``value.date()``. ``datetime`` is a
    ``date`` subclass, so it is checked first. An offset-bearing datetime
    becomes naive midnight of ``as_calendar_day`` in the lab zone. The column
    is SQL ``date``; the time on this midnight is not stored.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            day = value.date()
        else:
            day = as_calendar_day(value, current_lab_zone())
        return datetime(day.year, day.month, day.day)
    return datetime(value.year, value.month, value.day)
