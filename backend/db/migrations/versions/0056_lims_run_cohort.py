"""Add cohort JSONB to lims_runs for queue/start sample selection.

Revision ID: 0056
Revises: 0055
Create Date: 2026-08-10

cohort shape:
  {
    "sample_ids": ["uuid", ...],
    "locked_at": "ISO-8601" | null
  }
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0056'
down_revision = '0055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'lims_runs',
        sa.Column(
            'cohort',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('lims_runs', 'cohort')
