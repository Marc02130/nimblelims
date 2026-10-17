"""Allow a routing-map turnaround minimum of 0 days.

Revision ID: 0094_routing_map_tat_min_zero
Revises: 0093_asked_for_tat_days_zero

A same-day asked-for (tat_days 0) matches a map whose range includes 0.
The lower bound of routing_map.tat_range may be 0. A negative bound is refused.

This revision only adds or replaces the check constraint
routing_map_tat_lower_chk. It does not drop tables, columns, or the schema catalog.
"""

from alembic import op
import sqlalchemy as sa


revision = "0094_routing_map_tat_min_zero"
down_revision = "0093_asked_for_tat_days_zero"
branch_labels = None
depends_on = None

CK = "routing_map_tat_lower_chk"
TABLE = "routing_map"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(f"ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS {CK}"))
    op.create_check_constraint(CK, TABLE, "lower(tat_range) >= 0")


def downgrade() -> None:
    op.drop_constraint(CK, TABLE, type_="check")
