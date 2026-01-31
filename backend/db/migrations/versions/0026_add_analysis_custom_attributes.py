"""Add custom_attributes column to analyses and analytes tables

Revision ID: 0026
Revises: 0025
Create Date: 2026-01-21

Adds JSONB custom_attributes column to analyses and analytes tables to support
flexible custom field storage. Also adds analyte-specific fields.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '0026'
down_revision = '0025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add custom_attributes to analyses table
    op.add_column('analyses', sa.Column('custom_attributes', JSONB, nullable=True, server_default='{}'))
    
    # Add new columns to analytes table
    op.add_column('analytes', sa.Column('cas_number', sa.String(50), nullable=True))
    op.add_column('analytes', sa.Column('units_default', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('analytes', sa.Column('data_type', sa.String(20), nullable=True))
    op.add_column('analytes', sa.Column('custom_attributes', JSONB, nullable=True, server_default='{}'))
    
    # Add foreign key for units_default -> units.id (if units table exists)
    # Using try/except pattern since units table may not exist in all environments
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'units')"))
    units_exists = result.scalar()
    
    if units_exists:
        op.create_foreign_key(
            'fk_analytes_units_default',
            'analytes',
            'units',
            ['units_default'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # Remove foreign key if it exists
    try:
        op.drop_constraint('fk_analytes_units_default', 'analytes', type_='foreignkey')
    except:
        pass
    
    # Remove columns from analytes
    op.drop_column('analytes', 'custom_attributes')
    op.drop_column('analytes', 'data_type')
    op.drop_column('analytes', 'units_default')
    op.drop_column('analytes', 'cas_number')
    
    # Remove custom_attributes from analyses
    op.drop_column('analyses', 'custom_attributes')
