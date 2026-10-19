"""Convert naive UTC instant columns to timestamptz.

Revision ID: 0097_instant_timestamptz
Revises: 0096_lab_tz_fk_restrict

Each converted column is ``timestamp without time zone`` holding a UTC wall
time. ``USING col AT TIME ZONE 'UTC'`` reads that wall time as UTC, so the
instant does not shift. Downgrade writes the UTC wall time back with the same
expression.

Calendar-day columns and SQL ``date`` columns are not altered. Custom-attribute
JSON is not a timestamp column and is not rewritten.

Views, materialized views, rules, and generated columns that depend on a
converted column stop the migration. Indexes, defaults, triggers, and row
level security policies are left in place; Postgres rebuilds a plain index
when the column type changes.
"""

from __future__ import annotations

import re

from alembic import op
from sqlalchemy import text

from app.core.instant_columns import (
    CALENDAR_TIMESTAMP_COLUMNS,
    INSTANT_TIMESTAMP_COLUMNS,
    SQL_DATE_COLUMNS,
)

revision = "0097_instant_timestamptz"
down_revision = "0096_lab_tz_fk_restrict"
branch_labels = None
depends_on = None

_NAIVE = "timestamp without time zone"
_AWARE = "timestamp with time zone"
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def upgrade() -> None:
    conn = op.get_bind()
    _require_expected_types(conn, source=_NAIVE)
    _refuse_unsafe_dependents(conn)
    for qualified in sorted(INSTANT_TIMESTAMP_COLUMNS):
        _alter_instant(conn, qualified, _AWARE)


def downgrade() -> None:
    conn = op.get_bind()
    _require_expected_types(conn, source=_AWARE)
    _refuse_unsafe_dependents(conn)
    for qualified in sorted(INSTANT_TIMESTAMP_COLUMNS):
        _alter_instant(conn, qualified, _NAIVE)


def _require_expected_types(conn, source: str) -> None:
    """Fail before any ALTER when the catalog does not match this revision."""
    naive = _columns_of_type(conn, _NAIVE)
    aware = _columns_of_type(conn, _AWARE)
    dates = _columns_of_type(conn, "date")
    present = naive if source == _NAIVE else aware
    missing = sorted(INSTANT_TIMESTAMP_COLUMNS - present)
    unexpected = sorted(naive - CALENDAR_TIMESTAMP_COLUMNS - INSTANT_TIMESTAMP_COLUMNS)
    calendar_moved = sorted(CALENDAR_TIMESTAMP_COLUMNS - naive)
    dates_moved = sorted(SQL_DATE_COLUMNS - dates)
    problems: list[str] = []
    if missing:
        problems.append(
            "instant columns not "
            + source
            + ": "
            + ", ".join(missing)
        )
    if unexpected:
        problems.append(
            "unexpected timestamp without time zone: " + ", ".join(unexpected)
        )
    if calendar_moved:
        problems.append(
            "calendar columns are not timestamp without time zone: "
            + ", ".join(calendar_moved)
        )
    if dates_moved:
        problems.append("SQL date columns changed: " + ", ".join(dates_moved))
    if problems:
        raise RuntimeError(
            "0097_instant_timestamptz refused to change types. "
            + " ".join(problems)
        )


def _columns_of_type(conn, data_type: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema
             AND t.table_name = c.table_name
            WHERE c.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
              AND c.data_type = :data_type
            """
        ),
        {"data_type": data_type},
    )
    return {f"{table}.{column}" for table, column in rows}


def _refuse_unsafe_dependents(conn) -> None:
    """Stop when a converted column cannot change type without a drop."""
    tables = {name.split(".", 1)[0] for name in INSTANT_TIMESTAMP_COLUMNS}
    blockers: list[str] = []
    view_rows = conn.execute(
        text(
            """
            SELECT source.relname AS table_name,
                   a.attname AS column_name,
                   dependent_ns.nspname AS dep_schema,
                   dependent.relname AS dep_name,
                   dependent.relkind AS dep_kind
            FROM pg_depend d
            JOIN pg_rewrite rw ON d.objid = rw.oid
            JOIN pg_class dependent ON rw.ev_class = dependent.oid
            JOIN pg_namespace dependent_ns ON dependent_ns.oid = dependent.relnamespace
            JOIN pg_class source ON d.refobjid = source.oid
            JOIN pg_namespace source_ns ON source_ns.oid = source.relnamespace
            JOIN pg_attribute a
              ON a.attrelid = source.oid
             AND a.attnum = d.refobjsubid
             AND a.attnum > 0
            WHERE source_ns.nspname = 'public'
              AND dependent.oid <> source.oid
              AND dependent.relkind IN ('v', 'm')
            """
        )
    )
    for table_name, column_name, dep_schema, dep_name, dep_kind in view_rows:
        if table_name not in tables:
            continue
        qualified = f"{table_name}.{column_name}"
        if qualified not in INSTANT_TIMESTAMP_COLUMNS:
            continue
        kind = "materialized view" if dep_kind == "m" else "view"
        blockers.append(
            f"{qualified} is used by {kind} {dep_schema}.{dep_name}"
        )

    rule_rows = conn.execute(
        text(
            """
            SELECT c.relname, r.rulename
            FROM pg_rewrite r
            JOIN pg_class c ON c.oid = r.ev_class
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND r.rulename <> '_RETURN'
            """
        )
    )
    for table_name, rule_name in rule_rows:
        if table_name not in tables:
            continue
        blockers.append(f"{table_name} has rule {rule_name}")

    generated_rows = conn.execute(
        text(
            """
            SELECT c.relname, a.attname
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND a.attgenerated <> ''
              AND NOT a.attisdropped
            """
        )
    )
    for table_name, column_name in generated_rows:
        if table_name not in tables:
            continue
        qualified = f"{table_name}.{column_name}"
        if qualified in INSTANT_TIMESTAMP_COLUMNS:
            blockers.append(f"{qualified} is a generated column")

    if blockers:
        raise RuntimeError(
            "0097_instant_timestamptz stopped. A dependent object would have "
            "to be dropped, and this migration does not drop schema objects: "
            + "; ".join(sorted(blockers))
        )


def _alter_instant(conn, qualified: str, target: str) -> None:
    table, column = qualified.split(".", 1)
    _ident(table)
    _ident(column)
    if target not in (_NAIVE, _AWARE):
        raise RuntimeError(f"unexpected target type {target}")
    conn.execute(
        text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target} "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
    )


def _ident(name: str) -> None:
    if _IDENT.fullmatch(name) is None:
        raise RuntimeError(f"unexpected identifier {name}")
