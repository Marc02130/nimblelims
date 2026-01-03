"""Expand EAV (Entity-Attribute-Value) support to results, projects, client_projects, and batches

Revision ID: 0014
Revises: 0013
Create Date: 2025-12-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add custom_attributes JSONB column to results table
    op.add_column('results',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Add custom_attributes JSONB column to projects table
    op.add_column('projects',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Add custom_attributes JSONB column to client_projects table
    op.add_column('client_projects',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Add custom_attributes JSONB column to batches table
    op.add_column('batches',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Create GIN indexes for efficient querying of JSONB columns
    op.execute("CREATE INDEX idx_results_custom_attributes_gin ON results USING GIN (custom_attributes);")
    op.execute("CREATE INDEX idx_projects_custom_attributes_gin ON projects USING GIN (custom_attributes);")
    op.execute("CREATE INDEX idx_client_projects_custom_attributes_gin ON client_projects USING GIN (custom_attributes);")
    op.execute("CREATE INDEX idx_batches_custom_attributes_gin ON batches USING GIN (custom_attributes);")
    
    # Note: The existing RLS policies for results_access, projects_access, client_projects_access, and batches_access
    # already cover the custom_attributes column since they use FOR ALL and check project/client access.
    # The custom_attributes column will be visible/invisible based on the same access rules
    # as the rest of the row. No additional RLS policy changes are needed for the JSONB columns
    # themselves, as they are part of the row and subject to the existing row-level security.


def downgrade() -> None:
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS idx_batches_custom_attributes_gin;")
    op.execute("DROP INDEX IF EXISTS idx_client_projects_custom_attributes_gin;")
    op.execute("DROP INDEX IF EXISTS idx_projects_custom_attributes_gin;")
    op.execute("DROP INDEX IF EXISTS idx_results_custom_attributes_gin;")
    
    # Drop columns from batches, client_projects, projects, and results
    op.drop_column('batches', 'custom_attributes')
    op.drop_column('client_projects', 'custom_attributes')
    op.drop_column('projects', 'custom_attributes')
    op.drop_column('results', 'custom_attributes')

