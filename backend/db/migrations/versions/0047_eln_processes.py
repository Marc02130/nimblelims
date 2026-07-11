"""ELN Processes Phase 1: eln_processes, eln_process_steps, eln_process_samples

Revision ID: 0047
Revises: 0046
Create Date: 2026-07-11

First-class ordered multi-experiment workflows on the ELN side.

Naming deliberately uses eln_* prefixes to avoid collision with LIMS
experiment_processes / process_steps (migration 0040).

Also adds FK field_definitions.process_id → eln_processes.id (column existed
from 0046 without FK because processes table did not exist yet).

RLS: client-scoped via created_by, same pattern as migration 0042.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0047'
down_revision = '0046'
branch_labels = None
depends_on = None

_CLIENT_POLICY = """\
    is_admin() OR (
        has_experiment_access() AND
        created_by IN (
            SELECT u.id FROM users u
            WHERE u.client_id = (
                SELECT u2.client_id FROM users u2
                WHERE u2.id = current_user_id()
            )
        )
    )\
"""

_TABLES = (
    'eln_processes',
    'eln_process_steps',
    'eln_process_samples',
)


def upgrade() -> None:
    # --- eln_processes ---
    op.create_table(
        'eln_processes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['status_id'], ['list_entries.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_eln_processes_name'),
    )
    op.create_index('idx_eln_processes_active', 'eln_processes', ['active'])
    op.create_index('idx_eln_processes_status_id', 'eln_processes', ['status_id'])
    op.create_index('idx_eln_processes_created_by', 'eln_processes', ['created_by'])

    # --- eln_process_steps ---
    op.create_table(
        'eln_process_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['process_id'], ['eln_processes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id']),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('process_id', 'sort_order', name='uq_eln_process_steps_process_sort'),
    )
    op.create_index('idx_eln_process_steps_process_id', 'eln_process_steps', ['process_id'])
    op.create_index('idx_eln_process_steps_template_id', 'eln_process_steps', ['experiment_template_id'])
    op.create_index('idx_eln_process_steps_experiment_id', 'eln_process_steps', ['experiment_id'])
    op.create_index('idx_eln_process_steps_created_by', 'eln_process_steps', ['created_by'])

    # --- eln_process_samples ---
    op.create_table(
        'eln_process_samples',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='assigned'),
        sa.Column('current_step_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['process_id'], ['eln_processes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id']),
        sa.ForeignKeyConstraint(['current_step_id'], ['eln_process_steps.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('process_id', 'sample_id', name='uq_eln_process_samples_process_sample'),
    )
    op.create_index('idx_eln_process_samples_process_id', 'eln_process_samples', ['process_id'])
    op.create_index('idx_eln_process_samples_sample_id', 'eln_process_samples', ['sample_id'])
    op.create_index('idx_eln_process_samples_current_step_id', 'eln_process_samples', ['current_step_id'])
    op.create_index('idx_eln_process_samples_created_by', 'eln_process_samples', ['created_by'])
    op.create_index('idx_eln_process_samples_status', 'eln_process_samples', ['status'])

    # field_definitions.process_id FK (column added in 0046 without FK)
    op.create_foreign_key(
        'fk_field_definitions_process_id_eln_processes',
        'field_definitions',
        'eln_processes',
        ['process_id'],
        ['id'],
    )

    # Audit triggers + RLS for each table
    for table in _TABLES:
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
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING ({_CLIENT_POLICY});
        """)
        # Grant to app role if present (mirrors other migrations)
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_user;')

    # Seed optional list-driven statuses for eln_processes.status_id
    connection = op.get_bind()
    # Fixed UUID unlikely to collide with early seed lists (0000…–cccc… ranges)
    status_list_id = 'e1000000-0000-4000-8000-000000000001'
    existing = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'eln_process_status' LIMIT 1")
    ).fetchone()
    if not existing:
        connection.execute(
            sa.text("""
                INSERT INTO lists (id, name, description, active, created_at, modified_at)
                VALUES (
                    :id,
                    'eln_process_status',
                    'Status values for ELN Processes (optional status_id on eln_processes)',
                    true,
                    NOW(),
                    NOW()
                )
            """),
            {'id': status_list_id},
        )
        for name, desc in (
            ('Draft', 'Process defined but not started'),
            ('In Progress', 'Work is underway'),
            ('On Hold', 'Temporarily paused'),
            ('Completed', 'All steps finished'),
            ('Cancelled', 'Process abandoned'),
        ):
            connection.execute(
                sa.text("""
                    INSERT INTO list_entries (id, name, description, list_id, active, created_at, modified_at)
                    VALUES (gen_random_uuid(), :name, :description, :list_id, true, NOW(), NOW())
                    ON CONFLICT (list_id, name) DO NOTHING
                """),
                {'name': name, 'description': desc, 'list_id': status_list_id},
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM list_entries
            WHERE list_id IN (SELECT id FROM lists WHERE name = 'eln_process_status')
        """)
    )
    connection.execute(sa.text("DELETE FROM lists WHERE name = 'eln_process_status'"))

    op.drop_constraint(
        'fk_field_definitions_process_id_eln_processes',
        'field_definitions',
        type_='foreignkey',
    )
    for table in reversed(_TABLES):
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')
        op.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};')
    op.drop_table('eln_process_samples')
    op.drop_table('eln_process_steps')
    op.drop_table('eln_processes')
