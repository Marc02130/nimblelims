"""Shared reason rules: DB CHECKs for every user-entered reason.

Revision ID: 0121_shared_reason_rules
Revises: 0120_void_reason_4000

Every user-entered reason uses the void rules: trimmed 1-4000, with
space/tab/CR/LF, NBSP (U+00A0) and FIGURE SPACE (U+2007) as blank.
ZWSP (U+200B) and BOM (U+FEFF) stay visible.

* lims_runs.status_reason (fail / reject run) — new CHECK, nullable.
* result_acceptances.reason (accept value) — new CHECK, required.
* lims_run_data_exclusions.reason (data-point exclusion) — new CHECK,
  nullable.
* lims_run_type_substitutions.reason — 0120 CHECK replaced so the
  whitespace set matches void (adds NBSP / U+2007).

0120 and earlier are not edited. Upgrade refuses with table and row
counts if a stored reason already breaks the rule (same choice as
0117: fix the row first, no NOT VALID). Nothing is rewritten or
deleted. Downgrade drops the three new CHECKs and restores the 0120
substitution CHECK; both only loosen, so downgrade has no preflight.
"""

from __future__ import annotations

from alembic import op

revision = "0121_shared_reason_rules"
down_revision = "0120_void_reason_4000"
branch_labels = None
depends_on = None

_WS = r"E' \t\r\n' || U&'\00A0' || U&'\2007'"
_0118_WS = r"E' \t\r\n'"


def _len_ok(column: str, ws: str = _WS) -> str:
    return (
        f"({column} ~ '\\S' AND "
        f"char_length(btrim({column}, {ws})) BETWEEN 1 AND 4000)"
    )


def _nullable(column: str) -> str:
    return f"({column} IS NULL OR {_len_ok(column)})"


CHECKS = (
    (
        "lims_runs",
        "status_reason",
        "ck_lims_runs_status_reason",
        _nullable("status_reason"),
    ),
    (
        "result_acceptances",
        "reason",
        "ck_result_acceptances_reason",
        _len_ok("reason"),
    ),
    (
        "lims_run_data_exclusions",
        "reason",
        "ck_lims_run_data_exclusions_reason",
        _nullable("reason"),
    ),
    (
        "lims_run_type_substitutions",
        "reason",
        "ck_lims_run_type_substitutions_reason",
        _len_ok("reason"),
    ),
)
_0120_SUBST_REASON_LEN = _len_ok("reason", _0118_WS)


def _replace_check(table: str, name: str, expr: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})")


def refuse_bad_reasons(conn=None) -> None:
    """Abort upgrade with table+count rather than a bare CHECK failure."""
    bind = conn if conn is not None else op.get_bind()
    bad = []
    for table, column, _name, expr in CHECKS:
        count = bind.exec_driver_sql(
            f"SELECT count(*) FROM {table} WHERE NOT {expr}"
        ).scalar()
        if count:
            bad.append(f"{table}.{column}={count}")
    if bad:
        raise RuntimeError("0121 refuses CHECK: " + ", ".join(bad))


def upgrade() -> None:
    refuse_bad_reasons()
    for table, _column, name, expr in CHECKS:
        _replace_check(table, name, expr)


def downgrade() -> None:
    for table, _column, name, _expr in CHECKS:
        if table == "lims_run_type_substitutions":
            _replace_check(table, name, _0120_SUBST_REASON_LEN)
        else:
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
