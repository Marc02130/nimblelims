"""Allow asked-for turnaround time of 0 days.

Revision ID: 0093_asked_for_tat_days_zero
Revises: 0092_concentration_unit_scales

asked_for.tat_days was constrained to tat_days > 0. Same-day work is a
valid request, so 0 is stored. A negative value is still refused.
"""

from alembic import op


revision = "0093_asked_for_tat_days_zero"
down_revision = "0092_concentration_unit_scales"
branch_labels = None
depends_on = None

CK = "asked_for_tat_days_chk"
TABLE = "asked_for"


def upgrade() -> None:
    op.drop_constraint(CK, TABLE, type_="check")
    op.create_check_constraint(CK, TABLE, "tat_days >= 0")


def downgrade() -> None:
    op.drop_constraint(CK, TABLE, type_="check")
    op.create_check_constraint(CK, TABLE, "tat_days > 0")
