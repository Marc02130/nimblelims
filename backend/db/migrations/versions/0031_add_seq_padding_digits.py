"""Add seq_padding_digits to name_templates

Revision ID: 0031
Revises: 0030
Create Date: 2026-01-31 12:00:00.000000

Adds seq_padding_digits column (integer, default 1) to name_templates.
When generating {SEQ}, the sequence number is padded with leading zeros
to this number of digits (e.g. 3 -> 001, 010, 100). Default 1 means no padding.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0031'
down_revision = '0030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'name_templates',
        sa.Column('seq_padding_digits', sa.Integer(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    op.drop_column('name_templates', 'seq_padding_digits')
