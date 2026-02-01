"""Add client abbreviation (CLIABV) for {CLIENT} in naming

Revision ID: 0031
Revises: 0032
Create Date: 2026-01-31 14:00:00.000000

Adds abbreviation column to clients: optional, unique.
Used in name templates as {CLIENT} (e.g. PROJ-{CLIENT}-{SEQ}).
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
        'clients',
        sa.Column('abbreviation', sa.String(50), nullable=True)
    )
    op.create_unique_constraint('uq_clients_abbreviation', 'clients', ['abbreviation'])


def downgrade() -> None:
    op.drop_constraint('uq_clients_abbreviation', 'clients', type_='unique')
    op.drop_column('clients', 'abbreviation')
