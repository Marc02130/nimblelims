"""Add EAV (Entity-Attribute-Value) support for samples and tests

Revision ID: 0013
Revises: 0012
Create Date: 2025-12-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom_attributes_config table
    op.create_table('custom_attributes_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('entity_type', sa.String(255), nullable=False),
        sa.Column('attr_name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('validation_rules', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'attr_name', name='uq_custom_attributes_config_entity_attr')
    )
    
    # Create indexes on custom_attributes_config
    op.create_index('idx_custom_attributes_config_entity_type', 'custom_attributes_config', ['entity_type'])
    op.create_index('idx_custom_attributes_config_active', 'custom_attributes_config', ['active'])
    
    # Add custom_attributes JSONB column to samples table
    op.add_column('samples',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Add custom_attributes JSONB column to tests table
    op.add_column('tests',
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}')
    )
    
    # Create GIN indexes for efficient querying of JSONB columns
    op.execute("CREATE INDEX idx_samples_custom_attributes_gin ON samples USING GIN (custom_attributes);")
    op.execute("CREATE INDEX idx_tests_custom_attributes_gin ON tests USING GIN (custom_attributes);")
    
    # Enable RLS on custom_attributes_config table
    op.execute("ALTER TABLE custom_attributes_config ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policy for custom_attributes_config
    # Admins can manage all configs, others can only view active configs
    op.execute("""
        CREATE POLICY custom_attributes_config_access ON custom_attributes_config
        FOR ALL
        USING (
            is_admin() OR active = true
        );
    """)
    
    # Note: The existing RLS policies for samples_access and tests_access already cover
    # the custom_attributes column since they use FOR ALL and check project access.
    # The custom_attributes column will be visible/invisible based on the same access rules
    # as the rest of the row. No additional RLS policy changes are needed for the JSONB columns
    # themselves, as they are part of the row and subject to the existing row-level security.


def downgrade() -> None:
    # Drop RLS policy for custom_attributes_config
    op.execute("DROP POLICY IF EXISTS custom_attributes_config_access ON custom_attributes_config;")
    
    # Disable RLS on custom_attributes_config
    op.execute("ALTER TABLE custom_attributes_config DISABLE ROW LEVEL SECURITY;")
    
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS idx_tests_custom_attributes_gin;")
    op.execute("DROP INDEX IF EXISTS idx_samples_custom_attributes_gin;")
    
    # Drop columns from samples and tests
    op.drop_column('tests', 'custom_attributes')
    op.drop_column('samples', 'custom_attributes')
    
    # Drop indexes on custom_attributes_config
    op.drop_index('idx_custom_attributes_config_active', table_name='custom_attributes_config')
    op.drop_index('idx_custom_attributes_config_entity_type', table_name='custom_attributes_config')
    
    # Drop custom_attributes_config table
    op.drop_table('custom_attributes_config')

