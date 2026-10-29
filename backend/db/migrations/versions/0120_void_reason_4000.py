"""Raise the void-reason CHECK from 1000 to 4000.

Revision ID: 0120_void_reason_4000
Revises: 0119_instrument_reasons

0117/0118/0119 are not edited. They still create
ck_instrument_events_void_reason at 1000. This revision only replaces
that CHECK. The void trigger does not enforce length; it stays as 0119
left it. No DELETE grants. Upgrade widens the bound and does not
rewrite rows. Downgrade restores 1000 and refuses if any stored
void_reason trims longer than 1000 — it does not truncate or delete.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0120_void_reason_4000"
down_revision = "0119_instrument_reasons"
branch_labels = None
depends_on = None

_WS = r"E' \t\r\n' || U&'\00A0' || U&'\2007'"
_VOID_REASON_LEN = (
    f"(void_reason IS NULL OR (void_reason ~ '\\S' AND "
    f"char_length(btrim(void_reason, {_WS})) BETWEEN 1 AND 4000))"
)
_0119_VOID_REASON_LEN = (
    f"(void_reason IS NULL OR (void_reason ~ '\\S' AND "
    f"char_length(btrim(void_reason, {_WS})) BETWEEN 1 AND 1000))"
)


def _replace_check(table: str, name: str, expr: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})")


def refuse_downgrade_if_long_void_reasons(conn=None) -> None:
    bind = conn if conn is not None else op.get_bind()
    leftover = bind.execute(
        sa.text(
            "SELECT count(*) FROM instrument_maintenance_events "
            f"WHERE void_reason IS NOT NULL "
            f"AND char_length(btrim(void_reason, {_WS})) > 1000"
        )
    ).scalar()
    if leftover:
        raise RuntimeError(
            "0120 downgrade refuses: instrument_maintenance_events.void_reason "
            "longer than 1000 characters exists"
        )


def upgrade() -> None:
    _replace_check(
        "instrument_maintenance_events",
        "ck_instrument_events_void_reason",
        _VOID_REASON_LEN,
    )


def downgrade() -> None:
    refuse_downgrade_if_long_void_reasons()
    _replace_check(
        "instrument_maintenance_events",
        "ck_instrument_events_void_reason",
        _0119_VOID_REASON_LEN,
    )
