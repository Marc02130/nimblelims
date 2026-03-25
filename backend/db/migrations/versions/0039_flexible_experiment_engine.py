"""Flexible experiment engine: experiment_runs, experiment_data, instrument_parsers,
robot_worklist_configs, sop_parse_jobs

Revision ID: 0039
Revises: 0038
Create Date: 2026-03-25

Adds the Phase 1 data model for the AI-driven experiment pipeline:
  - experiment_runs: 6-state lifecycle (draft→running→complete→published→failed)
  - experiment_data: JSONB result rows per run, linked to containers/samples
  - instrument_parsers: column-mapping config learned from example instrument files
  - robot_worklist_configs: source/dest/volume mapping for liquid handling robots
  - sop_parse_jobs: tracks async Claude API extraction jobs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0039'
down_revision = '0038'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # experiment_runs status enum
    op.execute("""
        CREATE TYPE experiment_run_status AS ENUM (
            'draft', 'running', 'complete', 'published', 'failed'
        );
    """)

    # experiment_runs: instances of an experiment_template with lifecycle management
    op.create_table(
        'experiment_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'draft', 'running', 'complete', 'published', 'failed',
                name='experiment_run_status',
                create_type=False,
            ),
            nullable=False,
            server_default='draft',
        ),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_experiment_runs_name'),
    )
    op.create_index('idx_experiment_runs_template_id', 'experiment_runs', ['experiment_template_id'])
    op.create_index('idx_experiment_runs_status', 'experiment_runs', ['status'])
    op.create_index('idx_experiment_runs_created_by', 'experiment_runs', ['created_by'])

    # experiment_data: one row per instrument data point / well result
    op.create_table(
        'experiment_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('well_position', sa.String(10), nullable=True),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('row_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_run_id'], ['experiment_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id']),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_experiment_data_run_id', 'experiment_data', ['experiment_run_id'])
    op.create_index('idx_experiment_data_container_id', 'experiment_data', ['container_id'])
    op.create_index('idx_experiment_data_sample_id', 'experiment_data', ['sample_id'])
    op.execute(
        'CREATE INDEX idx_experiment_data_row_data_gin '
        'ON experiment_data USING GIN (row_data);'
    )

    # instrument_parsers: AI-learned column mapping config for an instrument output format
    op.create_table(
        'instrument_parsers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parser_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_instrument_parsers_template_id', 'instrument_parsers', ['experiment_template_id'])
    op.execute(
        'CREATE INDEX idx_instrument_parsers_config_gin '
        'ON instrument_parsers USING GIN (parser_config);'
    )

    # robot_worklist_configs: source/dest/volume mapping for liquid handling robot worklist export
    op.create_table(
        'robot_worklist_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('worklist_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_robot_worklist_configs_template_id', 'robot_worklist_configs', ['experiment_template_id'])
    op.execute(
        'CREATE INDEX idx_robot_worklist_configs_config_gin '
        'ON robot_worklist_configs USING GIN (worklist_config);'
    )

    # sop_parse_jobs: tracks async Claude API SOP extraction jobs
    op.execute("""
        CREATE TYPE sop_parse_job_status AS ENUM (
            'pending', 'processing', 'complete', 'failed'
        );
    """)
    op.create_table(
        'sop_parse_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'pending', 'processing', 'complete', 'failed',
                name='sop_parse_job_status',
                create_type=False,
            ),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('sop_filename', sa.String(512), nullable=True),
        sa.Column('instrument_filename', sa.String(512), nullable=True),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sop_parse_jobs_template_id', 'sop_parse_jobs', ['experiment_template_id'])
    op.create_index('idx_sop_parse_jobs_status', 'sop_parse_jobs', ['status'])
    op.create_index('idx_sop_parse_jobs_created_by', 'sop_parse_jobs', ['created_by'])

    # RLS: reuse has_experiment_access() defined in 0036
    for table in ('experiment_runs', 'experiment_data', 'instrument_parsers',
                  'robot_worklist_configs', 'sop_parse_jobs'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING (has_experiment_access());
        """)

    # Audit triggers
    for table in ('experiment_runs', 'experiment_data', 'instrument_parsers',
                  'robot_worklist_configs', 'sop_parse_jobs'):
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
    for table in ('sop_parse_jobs', 'robot_worklist_configs', 'instrument_parsers',
                  'experiment_data', 'experiment_runs'):
        op.execute(f'DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};')
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')

    op.execute('DROP INDEX IF EXISTS idx_sop_parse_jobs_created_by;')
    op.execute('DROP INDEX IF EXISTS idx_sop_parse_jobs_status;')
    op.execute('DROP INDEX IF EXISTS idx_sop_parse_jobs_template_id;')
    op.drop_table('sop_parse_jobs')
    op.execute('DROP TYPE IF EXISTS sop_parse_job_status;')

    op.execute('DROP INDEX IF EXISTS idx_robot_worklist_configs_config_gin;')
    op.execute('DROP INDEX IF EXISTS idx_robot_worklist_configs_template_id;')
    op.drop_table('robot_worklist_configs')

    op.execute('DROP INDEX IF EXISTS idx_instrument_parsers_config_gin;')
    op.execute('DROP INDEX IF EXISTS idx_instrument_parsers_template_id;')
    op.drop_table('instrument_parsers')

    op.execute('DROP INDEX IF EXISTS idx_experiment_data_row_data_gin;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_data_sample_id;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_data_container_id;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_data_run_id;')
    op.drop_table('experiment_data')

    op.execute('DROP INDEX IF EXISTS idx_experiment_runs_created_by;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_runs_status;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_runs_template_id;')
    op.drop_table('experiment_runs')
    op.execute('DROP TYPE IF EXISTS experiment_run_status;')
