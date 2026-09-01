"""P2: WO-7 first-start freeze + work-order route position.

Revision ID: 0075
Revises: 0074
Create Date: 2026-08-29

OQ-WO-3: each started process instance records route position.
Unique (work_order_id, work_order_route_position). Start instantiates
the next pending definition only.

First-start freeze is application-side (_mint_tests_at_start skip on
existing Test). This revision only adds the position column.
"""

from alembic import op
import sqlalchemy as sa

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eln_processes",
        sa.Column("work_order_route_position", sa.Integer(), nullable=True),
    )
    op.create_index(
        "uq_eln_process_wo_route",
        "eln_processes",
        ["work_order_id", "work_order_route_position"],
        unique=True,
        postgresql_where=sa.text("work_order_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_eln_process_wo_route", table_name="eln_processes")
    op.drop_column("eln_processes", "work_order_route_position")
