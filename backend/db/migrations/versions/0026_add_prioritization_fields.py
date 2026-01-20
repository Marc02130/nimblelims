"""Add sample prioritization fields

Revision ID: 0026
Revises: 0025
Create Date: 2026-01-19 00:00:00.000000

Adds columns to support sample prioritization based on expiration and due dates:
- samples.date_sampled: Optional datetime for when sample was collected (used for expiration calc)
- analyses.shelf_life: Optional integer days for expiration = date_sampled + shelf_life
- projects.due_date: Optional datetime for project-level turnaround (samples inherit if due_date null)

Also adds indexes for query performance on prioritization fields.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0026'
down_revision = '0025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add prioritization columns and indexes."""
    
    # Add date_sampled column to samples table
    # This is when the sample was collected (for expiration calculation)
    op.add_column(
        'samples',
        sa.Column('date_sampled', sa.DateTime(), nullable=True)
    )
    
    # Add shelf_life column to analyses table
    # This is the number of days from date_sampled until expiration
    op.add_column(
        'analyses',
        sa.Column('shelf_life', sa.Integer(), nullable=True)
    )
    
    # Add due_date column to projects table
    # This is project-level turnaround; samples inherit if their due_date is null
    op.add_column(
        'projects',
        sa.Column('due_date', sa.DateTime(), nullable=True)
    )
    
    # Add indexes for prioritization query performance
    # Index on samples.date_sampled for expiration calculations
    op.create_index(
        'idx_samples_date_sampled',
        'samples',
        ['date_sampled'],
        postgresql_where=sa.text('date_sampled IS NOT NULL')
    )
    
    # Index on analyses.shelf_life for filtering by shelf life
    op.create_index(
        'idx_analyses_shelf_life',
        'analyses',
        ['shelf_life'],
        postgresql_where=sa.text('shelf_life IS NOT NULL')
    )
    
    # Index on projects.due_date for project-level prioritization
    op.create_index(
        'idx_projects_due_date',
        'projects',
        ['due_date'],
        postgresql_where=sa.text('due_date IS NOT NULL')
    )
    
    # Composite index for prioritization queries joining samples with dates
    # This helps when sorting/filtering samples by effective due date
    op.create_index(
        'idx_samples_prioritization',
        'samples',
        ['project_id', 'due_date', 'date_sampled'],
        postgresql_where=sa.text('active = true')
    )


def downgrade() -> None:
    """Remove prioritization columns and indexes."""
    
    # Drop indexes first
    op.drop_index('idx_samples_prioritization', table_name='samples')
    op.drop_index('idx_projects_due_date', table_name='projects')
    op.drop_index('idx_analyses_shelf_life', table_name='analyses')
    op.drop_index('idx_samples_date_sampled', table_name='samples')
    
    # Drop columns
    op.drop_column('projects', 'due_date')
    op.drop_column('analyses', 'shelf_life')
    op.drop_column('samples', 'date_sampled')
