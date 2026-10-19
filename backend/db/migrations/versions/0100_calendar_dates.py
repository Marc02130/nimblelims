"""Store lab-day columns as SQL date.

Revision ID: 0100_calendar_dates
Revises: 0099_batch_update_qualifiers

Midnight and non-midnight values both keep the date part (``col::date``).
A naive timestamp is lab-zone wall time, so that date part is the lab day.
This is not ``((col AT TIME ZONE 'UTC') AT TIME ZONE lab_zone)::date``.
Seeded ``utcnow()`` rows were UTC wall time; shifting them would change the
day in America/New_York, and this migration does not do that.

Downgrade writes midnight. The previous clock time is not restored.
No rows are deleted.

``results.entry_date`` default becomes ``CURRENT_DATE``. Downgrade puts
``now()`` back.
"""

from __future__ import annotations

import re

from alembic import op
from sqlalchemy import text

revision = "0100_calendar_dates"
down_revision = "0099_batch_update_qualifiers"
branch_labels = None
depends_on = None

_COLUMNS = (
    "batches.start_date",
    "batches.end_date",
    "projects.start_date",
    "projects.due_date",
    "samples.due_date",
    "samples.received_date",
    "samples.report_date",
    "samples.date_sampled",
    "tests.review_date",
    "tests.test_date",
    "results.entry_date",
)
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def upgrade() -> None:
    conn = op.get_bind()
    _refuse_unsafe_dependents(conn)
    conn.execute(text("ALTER TABLE results ALTER COLUMN entry_date DROP DEFAULT"))
    for qualified in _COLUMNS:
        _alter(conn, qualified, "date", "{column}::date")
    conn.execute(text("ALTER TABLE results ALTER COLUMN entry_date SET DEFAULT CURRENT_DATE"))


def downgrade() -> None:
    conn = op.get_bind()
    _refuse_unsafe_dependents(conn)
    conn.execute(text("ALTER TABLE results ALTER COLUMN entry_date DROP DEFAULT"))
    for qualified in _COLUMNS:
        _alter(
            conn,
            qualified,
            "timestamp without time zone",
            "{column}::timestamp",
        )
    conn.execute(text("ALTER TABLE results ALTER COLUMN entry_date SET DEFAULT now()"))


def _alter(conn, qualified: str, target: str, using: str) -> None:
    table, column = qualified.split(".", 1)
    _ident(table)
    _ident(column)
    expression = using.format(column=column)
    conn.execute(
        text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target} "
            f"USING {expression}"
        )
    )


def _ident(name: str) -> None:
    if _IDENT.fullmatch(name) is None:
        raise RuntimeError(f"unexpected identifier {name}")


def _refuse_unsafe_dependents(conn) -> None:
    """Stop when a converted column cannot change type without a drop."""
    tables = {name.split(".", 1)[0] for name in _COLUMNS}
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
        qualified = f"{table_name}.{column_name}"
        if qualified not in _COLUMNS:
            continue
        kind = "materialized view" if dep_kind == "m" else "view"
        blockers.append(f"{qualified} is used by {kind} {dep_schema}.{dep_name}")
    if blockers:
        raise RuntimeError(
            "0100_calendar_dates stopped. A dependent object would have "
            "to be dropped, and this migration does not drop schema objects: "
            + "; ".join(sorted(blockers))
        )
