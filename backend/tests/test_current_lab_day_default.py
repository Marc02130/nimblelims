"""results.entry_date defaults to the lab calendar day."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from models.lab_setting import LAB_SETTINGS_ID

BEFORE = "0103_migration_role_owner"
REVISION = "0104_current_lab_day"
BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = BACKEND / "db" / "migrations" / "versions" / "0104_current_lab_day.py"
CLOCK = "2026-10-20T01:00:00Z"
NY_DAY = date(2026, 10, 19)
UTC_DAY = date(2026, 10, 20)
FN = "public.current_lab_day()"


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _bind_urls(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    return url, previous_database, previous_migrate


def _restore_urls(url, previous_database, previous_migrate) -> None:
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    if previous_database is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database
    if previous_migrate is None:
        os.environ.pop("MIGRATE_DATABASE_URL", None)
    else:
        os.environ["MIGRATE_DATABASE_URL"] = previous_migrate


def _set_clock(conn) -> None:
    conn.execute(
        text("SELECT set_config('lims.as_of', :clock, true)"),
        {"clock": CLOCK},
    )


def _seed_parents(conn):
    row = conn.execute(
        text("SELECT test_id, analyte_id, entered_by FROM results LIMIT 1")
    ).one_or_none()
    if row is None:
        raise AssertionError("results has no rows to copy parents from")
    return row


def _insert_omitting_entry_date(conn, parents):
    replicate = conn.execute(
        text(
            "SELECT COALESCE(MAX(replicate), 0) + 1000 "
            "FROM results WHERE test_id = :test_id AND analyte_id = :analyte_id"
        ),
        {"test_id": parents.test_id, "analyte_id": parents.analyte_id},
    ).scalar()
    return conn.execute(
        text(
            """
            INSERT INTO results (id, test_id, analyte_id, entered_by, replicate, active)
            VALUES (gen_random_uuid(), :test_id, :analyte_id, :entered_by, :replicate, true)
            RETURNING entry_date
            """
        ),
        {
            "test_id": parents.test_id,
            "analyte_id": parents.analyte_id,
            "entered_by": parents.entered_by,
            "replicate": replicate,
        },
    ).scalar()


def test_revision_follows_the_migration_role_owner() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_mig_0104_current_lab_day", MIGRATION)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    assert mig.revision == REVISION
    assert mig.down_revision == BEFORE
    source = MIGRATION.read_text()
    assert "GRANT" not in source
    assert "REVOKE" not in source
    assert "UPDATE " not in source
    assert "DELETE " not in source


def test_omitted_entry_date_stores_the_lab_day(migrated_engine) -> None:
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(
                text("UPDATE lab_settings SET timezone = 'America/New_York' WHERE id = :id"),
                {"id": str(LAB_SETTINGS_ID)},
            )
            _set_clock(conn)
            can_execute = conn.execute(
                text("SELECT has_function_privilege('lims_app', :fn, 'EXECUTE')"),
                {"fn": FN},
            ).scalar()
            if can_execute is not True:
                raise AssertionError(
                    "lims_app cannot EXECUTE public.current_lab_day(). "
                    "Stop. Do not add a GRANT."
                )
            can_select = conn.execute(
                text("SELECT has_table_privilege('lims_app', 'public.lab_settings', 'SELECT')")
            ).scalar()
            if can_select is not True:
                raise AssertionError(
                    "lims_app cannot SELECT lab_settings. Stop. Do not add a GRANT."
                )
            conn.execute(text("SET ROLE lims_app"))
            seen = conn.execute(text("SELECT public.current_lab_day()")).scalar()
            conn.execute(text("RESET ROLE"))
            assert seen == NY_DAY
            stored = _insert_omitting_entry_date(conn, _seed_parents(conn))
            assert stored == NY_DAY
        finally:
            trans.rollback()


def test_blank_or_missing_lab_settings_use_utc(migrated_engine) -> None:
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        try:
            _set_clock(conn)
            conn.execute(
                text("UPDATE lab_settings SET timezone = '' WHERE id = :id"),
                {"id": str(LAB_SETTINGS_ID)},
            )
            assert conn.execute(text("SELECT public.current_lab_day()")).scalar() == UTC_DAY
            conn.execute(
                text("UPDATE lab_settings SET timezone = NULL WHERE id = :id"),
                {"id": str(LAB_SETTINGS_ID)},
            )
            assert conn.execute(text("SELECT public.current_lab_day()")).scalar() == UTC_DAY
            conn.execute(
                text("DELETE FROM lab_settings WHERE id = :id"),
                {"id": str(LAB_SETTINGS_ID)},
            )
            assert conn.execute(text("SELECT public.current_lab_day()")).scalar() == UTC_DAY
        finally:
            trans.rollback()


def test_downgrade_restores_current_date(migrated_engine) -> None:
    url, previous_database, previous_migrate = _bind_urls(migrated_engine)
    cfg = _config(url)
    try:
        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            default = conn.execute(
                text(
                    """
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'results'
                      AND column_name = 'entry_date'
                    """
                )
            ).scalar()
            present = conn.execute(
                text("SELECT to_regprocedure('public.current_lab_day()')")
            ).scalar()
        assert default is not None
        assert "CURRENT_DATE" in default.upper()
        assert "current_lab_day" not in default
        assert present is None
    finally:
        command.upgrade(cfg, "head")
        _restore_urls(url, previous_database, previous_migrate)
        with migrated_engine.connect() as conn:
            default = conn.execute(
                text(
                    """
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'results'
                      AND column_name = 'entry_date'
                    """
                )
            ).scalar()
            present = conn.execute(
                text("SELECT to_regprocedure('public.current_lab_day()')")
            ).scalar()
        assert default is not None
        assert "current_lab_day" in default
        assert present is not None
