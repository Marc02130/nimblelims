"""Make samples.matrix nullable (matrix being dropped from intake).

Revision ID: 0070
Revises: 0069
Create Date: 2026-08-27

Atomic receive and product direction use sample_type as the intake identity
attribute. Matrix remains on the column for legacy rows but is no longer
required at receive.
"""

from alembic import op
import sqlalchemy as sa

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "samples",
        "matrix",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    # Backfill NULLs before restoring NOT NULL so downgrade does not fail.
    op.execute(
        """
        UPDATE samples
           SET matrix = (
               SELECT le.id
                 FROM list_entries le
                 JOIN lists l ON l.id = le.list_id
                WHERE l.name IN ('matrix_types', 'Matrix')
                ORDER BY le.name
                LIMIT 1
           )
         WHERE matrix IS NULL
        """
    )
    op.alter_column(
        "samples",
        "matrix",
        existing_type=sa.UUID(),
        nullable=False,
    )
