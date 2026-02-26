"""Experiment Management Chunk 1: experiments, templates, details, sample_executions

Revision ID: 0036
Revises: 0035
Create Date: 2026-02-25

Creates experiment_templates, experiments, experiment_details,
experiment_sample_executions with proper FKs, indexes (including
sample_id + experiment_id), constraints, and custom_attributes JSONB.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0036'
down_revision = '0035'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # experiment_templates: reusable experiment definitions
    op.create_table(
        'experiment_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('template_definition', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_experiment_templates_name'),
    )
    op.create_index('idx_experiment_templates_active', 'experiment_templates', ['active'])
    op.execute(
        'CREATE INDEX idx_experiment_templates_template_definition_gin '
        'ON experiment_templates USING GIN (template_definition);'
    )
    op.execute(
        'CREATE INDEX idx_experiment_templates_custom_attributes_gin '
        'ON experiment_templates USING GIN (custom_attributes);'
    )

    # experiments: a run of an experiment
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id']),
        sa.ForeignKeyConstraint(['status_id'], ['list_entries.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_experiments_name'),
    )
    op.create_index('idx_experiments_template_id', 'experiments', ['experiment_template_id'])
    op.create_index('idx_experiments_status_id', 'experiments', ['status_id'])
    op.create_index('idx_experiments_created_by', 'experiments', ['created_by'])
    op.execute(
        'CREATE INDEX idx_experiments_custom_attributes_gin '
        'ON experiments USING GIN (custom_attributes);'
    )

    # experiment_details: key-value / structured details per experiment
    op.create_table(
        'experiment_details',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('detail_type', sa.String(255), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_experiment_details_experiment_id', 'experiment_details', ['experiment_id'])
    op.create_index('idx_experiment_details_detail_type', 'experiment_details', ['detail_type'])
    op.execute(
        'CREATE INDEX idx_experiment_details_content_gin '
        'ON experiment_details USING GIN (content);'
    )

    # experiment_sample_executions: rich junction experiment <-> sample
    op.create_table(
        'experiment_sample_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_in_experiment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_conditions', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('replicate_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('test_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('custom_attributes', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id']),
        sa.ForeignKeyConstraint(['role_in_experiment_id'], ['list_entries.id']),
        sa.ForeignKeyConstraint(['test_id'], ['tests.id']),
        sa.ForeignKeyConstraint(['result_id'], ['results.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'experiment_id',
            'sample_id',
            'replicate_number',
            name='uq_experiment_sample_execution_experiment_sample_replicate',
        ),
    )
    op.create_index(
        'idx_experiment_sample_executions_sample_experiment',
        'experiment_sample_executions',
        ['sample_id', 'experiment_id'],
    )
    op.create_index('idx_experiment_sample_executions_experiment_id', 'experiment_sample_executions', ['experiment_id'])
    op.create_index('idx_experiment_sample_executions_sample_id', 'experiment_sample_executions', ['sample_id'])
    op.create_index('idx_experiment_sample_executions_test_id', 'experiment_sample_executions', ['test_id'])
    op.create_index('idx_experiment_sample_executions_result_id', 'experiment_sample_executions', ['result_id'])
    op.execute(
        'CREATE INDEX idx_experiment_sample_executions_processing_conditions_gin '
        'ON experiment_sample_executions USING GIN (processing_conditions);'
    )
    op.execute(
        'CREATE INDEX idx_experiment_sample_executions_custom_attributes_gin '
        'ON experiment_sample_executions USING GIN (custom_attributes);'
    )

    # RLS (match project pattern for workflow-like tables)
    op.execute('ALTER TABLE experiment_templates ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiment_details ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiment_sample_executions ENABLE ROW LEVEL SECURITY;')

    op.execute("""
        CREATE OR REPLACE FUNCTION has_experiment_access()
        RETURNS BOOLEAN AS $$
        DECLARE
            user_role_name TEXT;
        BEGIN
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            SELECT r.name INTO user_role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = current_user_id();
            RETURN user_role_name IN ('Administrator', 'Lab Manager', 'Lab Technician');
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute("""
        CREATE POLICY experiment_templates_access ON experiment_templates
        FOR ALL
        USING (has_experiment_access());
    """)
    op.execute("""
        CREATE POLICY experiments_access ON experiments
        FOR ALL
        USING (has_experiment_access());
    """)
    op.execute("""
        CREATE POLICY experiment_details_access ON experiment_details
        FOR ALL
        USING (has_experiment_access());
    """)
    op.execute("""
        CREATE POLICY experiment_sample_executions_access ON experiment_sample_executions
        FOR ALL
        USING (has_experiment_access());
    """)

    # Audit triggers
    for table in ('experiment_templates', 'experiments', 'experiment_details', 'experiment_sample_executions'):
        op.execute(f"""
            CREATE TRIGGER {table}_audit_timestamps
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_audit_timestamps();
        """)
        op.execute(f"""
            CREATE TRIGGER {table}_update_modified_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_modified_at_column();
        """)


def downgrade() -> None:
    # Drop audit triggers (table names with underscores)
    for table in ('experiment_sample_executions', 'experiment_details', 'experiments', 'experiment_templates'):
        op.execute(f'DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};')

    # Drop RLS policies and helper
    op.execute('DROP POLICY IF EXISTS experiment_sample_executions_access ON experiment_sample_executions;')
    op.execute('DROP POLICY IF EXISTS experiment_details_access ON experiment_details;')
    op.execute('DROP POLICY IF EXISTS experiments_access ON experiments;')
    op.execute('DROP POLICY IF EXISTS experiment_templates_access ON experiment_templates;')
    op.execute('DROP FUNCTION IF EXISTS has_experiment_access();')

    op.execute('ALTER TABLE experiment_sample_executions DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiment_details DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiments DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE experiment_templates DISABLE ROW LEVEL SECURITY;')

    # Drop indexes then tables (reverse order of creation)
    op.execute('DROP INDEX IF EXISTS idx_experiment_sample_executions_custom_attributes_gin;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_sample_executions_processing_conditions_gin;')
    op.drop_index('idx_experiment_sample_executions_result_id', table_name='experiment_sample_executions')
    op.drop_index('idx_experiment_sample_executions_test_id', table_name='experiment_sample_executions')
    op.drop_index('idx_experiment_sample_executions_sample_id', table_name='experiment_sample_executions')
    op.drop_index('idx_experiment_sample_executions_experiment_id', table_name='experiment_sample_executions')
    op.drop_index('idx_experiment_sample_executions_sample_experiment', table_name='experiment_sample_executions')
    op.drop_table('experiment_sample_executions')

    op.execute('DROP INDEX IF EXISTS idx_experiment_details_content_gin;')
    op.drop_index('idx_experiment_details_detail_type', table_name='experiment_details')
    op.drop_index('idx_experiment_details_experiment_id', table_name='experiment_details')
    op.drop_table('experiment_details')

    op.execute('DROP INDEX IF EXISTS idx_experiments_custom_attributes_gin;')
    op.drop_index('idx_experiments_created_by', table_name='experiments')
    op.drop_index('idx_experiments_status_id', table_name='experiments')
    op.drop_index('idx_experiments_template_id', table_name='experiments')
    op.drop_table('experiments')

    op.execute('DROP INDEX IF EXISTS idx_experiment_templates_custom_attributes_gin;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_templates_template_definition_gin;')
    op.drop_index('idx_experiment_templates_active', table_name='experiment_templates')
    op.drop_table('experiment_templates')
