"""Lab-day columns are SQL date. Naive non-midnight values keep their date part.

F12 reads a naive clock as lab-zone wall time. That disagrees with the earlier
reading that seeded ``utcnow()`` values are UTC wall time. The backfill uses
``col::date`` for midnight and non-midnight rows. It does not apply
``((col AT TIME ZONE 'UTC') AT TIME ZONE lab_zone)::date``.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core import lab_time
from app.core.lab_time import current_lab_day
from app.schemas.project import ProjectCreate, ProjectUpdate

BEFORE = "0099_batch_update_qualifiers"


def test_current_lab_day_is_the_previous_evening_in_new_york(monkeypatch):
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 3, 30, tzinfo=timezone.utc)
    )
    lab_time.remember_lab_zone("America/New_York")
    assert current_lab_day() == date(2026, 10, 18)


def test_project_start_and_due_normalize_to_the_lab_day(monkeypatch):
    monkeypatch.setattr(
        lab_time, "_utcnow", lambda: datetime(2026, 10, 19, 3, 30, tzinfo=timezone.utc)
    )
    lab_time.remember_lab_zone("America/New_York")
    client_id = uuid4()
    status_id = uuid4()
    created = ProjectCreate(
        start_date=datetime(2026, 10, 19, 3, 30, tzinfo=timezone.utc),
        due_date=datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc),
        client_id=client_id,
        status=status_id,
    )
    assert created.start_date == datetime(2026, 10, 18, 0, 0)
    assert created.start_date.tzinfo is None
    assert created.due_date == datetime(2026, 10, 20, 0, 0)
    assert created.due_date.tzinfo is None
    updated = ProjectUpdate(
        start_date=datetime(2026, 1, 15, 15, 0),
        due_date="2026-02-02",
    )
    assert updated.start_date == datetime(2026, 1, 15, 0, 0)
    assert updated.due_date == datetime(2026, 2, 2, 0, 0)


def test_calendar_backfill_keeps_the_naive_date_part(migrated_engine):
    """Midnight and 02:00 both become that calendar date. Downgrade is midnight."""
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "db/migrations")
    cfg.set_main_option("sqlalchemy.url", url)
    previous = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            sample_id = conn.execute(text("SELECT id FROM samples LIMIT 1")).scalar()
            if sample_id is None:
                raise AssertionError("samples has no rows to backfill")
            conn.execute(
                text(
                    "UPDATE samples SET received_date = :midnight, due_date = :evening "
                    "WHERE id = :id"
                ),
                {
                    "midnight": datetime(2026, 10, 19, 0, 0),
                    "evening": datetime(2026, 10, 19, 2, 0),
                    "id": sample_id,
                },
            )
            conn.commit()
        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT received_date, due_date FROM samples WHERE id = :id"
                ),
                {"id": sample_id},
            ).one()
            assert row.received_date == date(2026, 10, 19)
            assert row.due_date == date(2026, 10, 19)
            data_type = conn.execute(
                text(
                    """
                    SELECT data_type FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'samples'
                      AND column_name = 'received_date'
                    """
                )
            ).scalar()
            assert data_type == "date"
        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT received_date, due_date FROM samples WHERE id = :id"
                ),
                {"id": sample_id},
            ).one()
            assert row.received_date == datetime(2026, 10, 19, 0, 0)
            assert row.due_date == datetime(2026, 10, 19, 0, 0)
            assert row.received_date.tzinfo is None
    finally:
        command.upgrade(cfg, "head")
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate
