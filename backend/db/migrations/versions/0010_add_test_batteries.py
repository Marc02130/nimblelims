"""Add test batteries to NimbleLims schema

Revision ID: 0010
Revises: 0009
Create Date: 2025-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
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
    
    # Seed initial test battery data
    connection = op.get_bind()
    
    # Create 'EPA 8080 Full' battery
    # This battery groups the EPA Method 8080 analytical analysis
    # Note: Prep analyses can be added to batteries via admin interface
    battery_data = {
        'id': 'c0000001-c000-c000-c000-c00000000001',
        'name': 'EPA 8080 Full',
        'description': 'Complete EPA Method 8080 test battery for Organochlorine Pesticides and PCBs',
        'active': True
    }
    
    connection.execute(
        sa.text("""
            INSERT INTO test_batteries (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, :active, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        battery_data
    )
    
    # Link EPA Method 8080 analysis to the battery
    # Using the analysis ID from migration 0009: 'b0000002-b000-b000-b000-b00000000002'
    battery_analysis_data = [{
        'battery_id': 'c0000001-c000-c000-c000-c00000000001',
        'analysis_id': 'b0000002-b000-b000-b000-b00000000002',
        'sequence': 2,
        'optional': False
    }, {
        'battery_id': 'c0000001-c000-c000-c000-c00000000001',
        'analysis_id': 'b0000002-b000-b000-b000-b00000000004',
        'sequence': 1,
        'optional': False
    }]

    for battery_analysis in battery_analysis_data:
        connection.execute(
            sa.text("""
                INSERT INTO battery_analyses (battery_id, analysis_id, sequence, optional)
                VALUES (:battery_id, :analysis_id, :sequence, :optional)
                ON CONFLICT (battery_id, analysis_id) DO NOTHING
            """),
            battery_analysis
        )


def downgrade() -> None:
    # Remove seed data first
    connection = op.get_bind()
    
    # Delete battery_analyses junctions
    connection.execute(
        sa.text("DELETE FROM battery_analyses WHERE battery_id = 'c0000001-c000-c000-c000-c00000000001'")
    )
    
    # Delete test batteries
    connection.execute(
        sa.text("DELETE FROM test_batteries WHERE id = 'c0000001-c000-c000-c000-c00000000001'")
    )
    
    # Drop indexes
    op.drop_index('idx_battery_analyses_sequence', table_name='battery_analyses')
    op.drop_index('idx_battery_analyses_battery_analysis', table_name='battery_analyses')
    op.drop_index('idx_battery_analyses_battery_id', table_name='battery_analyses')
    op.drop_index('idx_test_batteries_name', table_name='test_batteries')
    
    # Drop junction table first (due to foreign key constraints)
    op.drop_table('battery_analyses')
    
    # Drop main table
    op.drop_table('test_batteries')

