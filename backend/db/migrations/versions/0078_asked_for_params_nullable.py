"""Allow tests.asked_for_params NULL (classic /tests freeze skip).

Revision ID: 0078
Revises: 0077
Create Date: 2026-08-31

NULL = not frozen yet. First LimsRun start writes the asked-for snapshot.
{} after first start = locked empty. Classic POST /tests must leave NULL
(no server default). Do not rewrite existing {} rows to NULL.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "tests",
        "asked_for_params",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=None,
        existing_server_default=sa.text("'{}'::jsonb"),
    )


def downgrade() -> None:
    op.execute(
        "UPDATE tests SET asked_for_params = '{}'::jsonb "
        "WHERE asked_for_params IS NULL"
    )
    op.alter_column(
        "tests",
        "asked_for_params",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
