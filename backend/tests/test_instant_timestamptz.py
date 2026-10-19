"""timestamptz migration: values, calendar dates, and naive-write guard.

Lab-day columns are SQL ``date`` before this migration runs. This module
stamps those as dates and stamps instants as naive UTC wall time.
``checks/naive_instants.py`` does not scan ``backend/tests``.
Already-applied migrations are not scanned either.
Every test in this module runs.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, text

import models  # noqa: F401
from app.core.instant_columns import (
    CALENDAR_TIMESTAMP_COLUMNS,
    INSTANT_TIMESTAMP_COLUMNS,
    SQL_DATE_COLUMNS,
)
from checks.naive_instants import scan_tree
from models.base import Base

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
MIGRATION = BACKEND / "db" / "migrations" / "versions" / "0102_instant_timestamptz.py"
BEFORE = "0101_revoke_probe_execute"
NAIVE = datetime(2020, 1, 15, 19, 23)
LAB_DAY = date(2020, 1, 15)
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _imports_app(module_name: str) -> bool:
    return (
        module_name == "app"
        or module_name.startswith("app.")
        or module_name == "models"
        or module_name.startswith("models.")
    )


def _frozen_migration():
    """Load the revision without importing it as application code."""
    spec = importlib.util.spec_from_file_location(
        "migration_0102_instant_timestamptz",
        MIGRATION,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("0102_instant_timestamptz could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_column_lists_are_frozen() -> None:
    """The revision does not import app code. Its lists match the models."""
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _imports_app(alias.name):
                    raise AssertionError(f"migration imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if _imports_app(module_name):
                raise AssertionError(f"migration imports {module_name}")
    frozen = _frozen_migration()
    assert set(frozen.INSTANT_TIMESTAMP_COLUMNS) == set(INSTANT_TIMESTAMP_COLUMNS)
    assert set(frozen.SQL_DATE_COLUMNS) == set(SQL_DATE_COLUMNS)
    assert set(frozen.CALENDAR_TIMESTAMP_COLUMNS) == set(CALENDAR_TIMESTAMP_COLUMNS)
    naive, aware = _model_datetimes()
    assert naive == set(frozen.CALENDAR_TIMESTAMP_COLUMNS)
    assert set(frozen.INSTANT_TIMESTAMP_COLUMNS).isdisjoint(naive)
    assert set(frozen.INSTANT_TIMESTAMP_COLUMNS) <= aware


def _model_datetimes() -> tuple[set[str], set[str]]:
    naive: set[str] = set()
    aware: set[str] = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if not isinstance(column.type, DateTime):
                continue
            qualified = f"{table.name}.{column.name}"
            if column.type.timezone:
                aware.add(qualified)
            else:
                naive.add(qualified)
    return naive, aware


def test_model_datetimes_are_aware_or_calendar() -> None:
    """A new naive DateTime column fails unless it is a known lab day."""
    naive, aware = _model_datetimes()
    assert naive == set(CALENDAR_TIMESTAMP_COLUMNS)
    assert INSTANT_TIMESTAMP_COLUMNS.isdisjoint(naive)
    assert INSTANT_TIMESTAMP_COLUMNS <= aware


def test_server_code_has_no_naive_utc_writes() -> None:
    findings = scan_tree(REPO)
    assert findings == []


def test_instant_columns_round_trip(migrated_engine) -> None:
    """Downgrade, upgrade, downgrade, upgrade. Counts and instants hold."""
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            targets = _stamp_sample(conn)
            conn.commit()
            before_counts = _counts(conn)
            before_triggers = _names(conn, _trigger_sql(), "samples")
            before_indexes = _names(conn, _index_sql(), "samples")
            before_policies = _names(conn, _policy_sql(), "samples")
            before_default = _column_default(conn, "users", "created_at")
            if "samples_audit_timestamps" not in before_triggers:
                raise AssertionError(f"samples audit trigger missing: {before_triggers}")
            if "samples_update_modified_at" not in before_triggers:
                raise AssertionError(f"samples modified_at trigger missing: {before_triggers}")
            if not before_indexes:
                raise AssertionError("samples indexes missing")
            if not before_policies:
                raise AssertionError("samples row level security policies missing")
            if before_default is None:
                raise AssertionError("users.created_at default missing")
            _assert_naive_wall(conn, targets)

        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            assert _counts(conn) == before_counts
            assert _names(conn, _trigger_sql(), "samples") == before_triggers
            assert _names(conn, _index_sql(), "samples") == before_indexes
            assert _names(conn, _policy_sql(), "samples") == before_policies
            assert _column_default(conn, "users", "created_at") == before_default
            _assert_catalog(conn, instants_are_aware=True)
            _assert_upgraded_values(conn, targets)

        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            assert _counts(conn) == before_counts
            assert _names(conn, _trigger_sql(), "samples") == before_triggers
            _assert_catalog(conn, instants_are_aware=False)
            _assert_naive_wall(conn, targets)

        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            assert _counts(conn) == before_counts
            _assert_catalog(conn, instants_are_aware=True)
            _assert_upgraded_values(conn, targets)
    finally:
        os.environ["DATABASE_URL"] = url
        os.environ["MIGRATE_DATABASE_URL"] = url
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate


def _stamp_sample(conn) -> dict:
    """Write one known UTC wall time on a sample of tables. Caller commits."""
    targets = {
        "users": _one_id(conn, "users"),
        "samples": _one_id(conn, "samples"),
        "lims_runs": _one_id(conn, "lims_runs"),
        "results": _one_id(conn, "results"),
    }
    for table in ("users", "samples", "results"):
        if targets[table] is None:
            raise AssertionError(f"{table} has no rows to round-trip")
    conn.execute(
        text("UPDATE users SET last_login = :wall WHERE id = :id"),
        {"wall": NAIVE, "id": targets["users"]},
    )
    conn.execute(
        text(
            "UPDATE samples SET created_at = :wall, received_date = :day WHERE id = :id"
        ),
        {"wall": NAIVE, "day": LAB_DAY, "id": targets["samples"]},
    )
    if targets["lims_runs"] is None:
        # Seed data has samples and results, and no LIMS run. Insert one so
        # started_at is in the value round-trip. The row is counted on both
        # sides of the migration.
        targets["lims_runs"] = conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, experiment_template_id, started_at) "
                "VALUES ("
                "gen_random_uuid(), 'tz-round-trip', 'draft', "
                "(SELECT id FROM experiment_templates LIMIT 1), :wall"
                ") RETURNING id"
            ),
            {"wall": NAIVE},
        ).scalar()
    else:
        conn.execute(
            text("UPDATE lims_runs SET started_at = :wall WHERE id = :id"),
            {"wall": NAIVE, "id": targets["lims_runs"]},
        )
    conn.execute(
        text(
            "UPDATE results SET created_at = :wall, entry_date = :day WHERE id = :id"
        ),
        {"wall": NAIVE, "day": LAB_DAY, "id": targets["results"]},
    )
    return targets


def _assert_naive_wall(conn, targets: dict) -> None:
    _expect_wall(conn, "users", "last_login", targets["users"], aware=False)
    _expect_wall(conn, "samples", "created_at", targets["samples"], aware=False)
    _expect_date(conn, "samples", "received_date", targets["samples"])
    _expect_wall(conn, "lims_runs", "started_at", targets["lims_runs"], aware=False)
    _expect_wall(conn, "results", "created_at", targets["results"], aware=False)
    _expect_date(conn, "results", "entry_date", targets["results"])


def _assert_upgraded_values(conn, targets: dict) -> None:
    _expect_wall(conn, "users", "last_login", targets["users"], aware=True)
    _expect_wall(conn, "samples", "created_at", targets["samples"], aware=True)
    _expect_date(conn, "samples", "received_date", targets["samples"])
    _expect_wall(conn, "lims_runs", "started_at", targets["lims_runs"], aware=True)
    _expect_wall(conn, "results", "created_at", targets["results"], aware=True)
    _expect_date(conn, "results", "entry_date", targets["results"])


def _expect_wall(conn, table: str, column: str, row_id, aware: bool) -> None:
    _ident(table)
    _ident(column)
    value = conn.execute(
        text(f"SELECT {column} FROM {table} WHERE id = :id"),
        {"id": row_id},
    ).scalar()
    if value is None:
        raise AssertionError(f"{table}.{column} is None")
    if aware:
        if value.tzinfo is None:
            raise AssertionError(f"{table}.{column} lost its timezone")
        assert value.astimezone(timezone.utc).replace(tzinfo=None) == NAIVE
    else:
        if value.tzinfo is not None:
            raise AssertionError(f"{table}.{column} gained a timezone")
        assert value == NAIVE


def _expect_date(conn, table: str, column: str, row_id) -> None:
    _ident(table)
    _ident(column)
    value = conn.execute(
        text(f"SELECT {column} FROM {table} WHERE id = :id"),
        {"id": row_id},
    ).scalar()
    if value != LAB_DAY:
        raise AssertionError(f"{table}.{column} is {value!r}, expected {LAB_DAY}")


def _assert_catalog(conn, instants_are_aware: bool) -> None:
    naive = _typed(conn, "timestamp without time zone")
    aware = _typed(conn, "timestamp with time zone")
    dates = _typed(conn, "date")
    assert set(SQL_DATE_COLUMNS) <= dates
    assert set(CALENDAR_TIMESTAMP_COLUMNS) <= naive
    if instants_are_aware:
        assert set(INSTANT_TIMESTAMP_COLUMNS) <= aware
        assert set(INSTANT_TIMESTAMP_COLUMNS).isdisjoint(naive)
    else:
        assert set(INSTANT_TIMESTAMP_COLUMNS) <= naive
        assert naive == set(INSTANT_TIMESTAMP_COLUMNS) | set(CALENDAR_TIMESTAMP_COLUMNS)


def _typed(conn, data_type: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND data_type = :data_type
            """
        ),
        {"data_type": data_type},
    )
    return {f"{table}.{column}" for table, column in rows}


def _counts(conn) -> dict:
    tables = conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ).scalars()
    counts = {}
    for table in tables:
        _ident(table)
        counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    return counts


def _one_id(conn, table: str):
    _ident(table)
    return conn.execute(text(f"SELECT id FROM {table} LIMIT 1")).scalar()


def _names(conn, sql: str, table: str) -> list[str]:
    return list(conn.execute(text(sql), {"table": table}).scalars())


def _trigger_sql() -> str:
    return """
        SELECT t.tgname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = :table
          AND NOT t.tgisinternal
        ORDER BY t.tgname
    """


def _index_sql() -> str:
    return """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = :table
        ORDER BY indexname
    """


def _policy_sql() -> str:
    return """
        SELECT pol.polname
        FROM pg_policy pol
        JOIN pg_class c ON c.oid = pol.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = :table
        ORDER BY pol.polname
    """


def _column_default(conn, table: str, column: str):
    return conn.execute(
        text(
            """
            SELECT column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).scalar()


def _ident(name: str) -> None:
    if _IDENT.fullmatch(name) is None:
        raise AssertionError(f"unexpected identifier {name}")
