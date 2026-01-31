"""Add test batteries to NimbleLims schema

Revision ID: 0009
Revises: 0008
Create Date: 2025-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create test_batteries table
    op.create_table('test_batteries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create battery_analyses junction table
    op.create_table('battery_analyses',
        sa.Column('battery_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('optional', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['battery_id'], ['test_batteries.id'], ),
        sa.PrimaryKeyConstraint('battery_id', 'analysis_id')
    )
    
    # Create indexes for performance
    # Index on battery_id in battery_analyses for efficient lookups
    op.create_index('idx_battery_analyses_battery_id', 'battery_analyses', ['battery_id'])
    
    # Composite index on (battery_id, analysis_id) for efficient lookups
    # Note: Primary key already provides uniqueness, so this is for query performance
    op.create_index('idx_battery_analyses_battery_analysis', 'battery_analyses', ['battery_id', 'analysis_id'])
    
    # Index on sequence for ordering queries
    op.create_index('idx_battery_analyses_sequence', 'battery_analyses', ['battery_id', 'sequence'])
    
    # Index on test_batteries name for lookups
    op.create_index('idx_test_batteries_name', 'test_batteries', ['name'])
    
def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_battery_analyses_sequence', table_name='battery_analyses')
    op.drop_index('idx_battery_analyses_battery_analysis', table_name='battery_analyses')
    op.drop_index('idx_battery_analyses_battery_id', table_name='battery_analyses')
    op.drop_index('idx_test_batteries_name', table_name='test_batteries')
    
    # Drop junction table first (due to foreign key constraints)
    op.drop_table('battery_analyses')
    
    # Drop main table
    op.drop_table('test_batteries')

