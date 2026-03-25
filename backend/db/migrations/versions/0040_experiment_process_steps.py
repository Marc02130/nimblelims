"""Experiment process steps: experiment_processes, process_steps

Revision ID: 0040
Revises: 0039
Create Date: 2026-03-25

Adds process-step tracking within experiment runs:
  - experiment_processes: named sub-processes within a run (e.g. "Sample Prep")
  - process_steps: ordered steps within a process with lifecycle status
    (queued → in_process → complete | failed)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0040'
down_revision = '0039'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # process_step_status enum
    op.execute("""
        CREATE TYPE process_step_status AS ENUM (
            'queued', 'in_process', 'complete', 'failed'
        );
    """)

    # experiment_processes: named sub-process within an experiment_run
    op.create_table(
        'experiment_processes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_run_id'], ['experiment_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_experiment_processes_run_id', 'experiment_processes', ['experiment_run_id'])
    op.create_index('idx_experiment_processes_sort_order', 'experiment_processes', ['experiment_run_id', 'sort_order'])

    # process_steps: ordered steps within an ExperimentProcess
    op.create_table(
        'process_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'status',
            postgresql.ENUM(
                'queued', 'in_process', 'complete', 'failed',
                name='process_step_status',
                create_type=False,
            ),
            nullable=False,
            server_default='queued',
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['process_id'], ['experiment_processes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_process_steps_process_id', 'process_steps', ['process_id'])
    op.create_index('idx_process_steps_sort_order', 'process_steps', ['process_id', 'sort_order'])
    op.create_index('idx_process_steps_status', 'process_steps', ['status'])

    # RLS: reuse has_experiment_access() defined in 0036
    for table in ('experiment_processes', 'process_steps'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING (has_experiment_access());
        """)

    # Audit triggers
    for table in ('experiment_processes', 'process_steps'):
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
    for table in ('process_steps', 'experiment_processes'):
        op.execute(f'DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};')
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')

    op.execute('DROP INDEX IF EXISTS idx_process_steps_status;')
    op.execute('DROP INDEX IF EXISTS idx_process_steps_sort_order;')
    op.execute('DROP INDEX IF EXISTS idx_process_steps_process_id;')
    op.drop_table('process_steps')

    op.execute('DROP INDEX IF EXISTS idx_experiment_processes_sort_order;')
    op.execute('DROP INDEX IF EXISTS idx_experiment_processes_run_id;')
    op.drop_table('experiment_processes')

    op.execute('DROP TYPE IF EXISTS process_step_status;')
