"""Phase 3: ELN process definitions + typed steps + LimsRun history

Revision ID: 0051
Revises: 0050
Create Date: 2026-07-11

- eln_process_definitions / eln_process_definition_steps (first-class, Decision #6)
- eln_processes.process_definition_id
- eln_process_steps.step_kind, execution_mode, current_lims_run_id
- eln_process_step_lims_runs (history junction, Decision #1)
- Backfill ad hoc instances into snapshot definitions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0051'
down_revision = '0050'
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


def upgrade() -> None:
    # ── Definitions ─────────────────────────────────────────────────────────
    op.create_table(
        'eln_process_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_eln_process_definitions_name'),
    )
    op.create_index('idx_eln_process_definitions_active', 'eln_process_definitions', ['active'])
    op.create_index('idx_eln_process_definitions_created_by', 'eln_process_definitions', ['created_by'])

    op.create_table(
        'eln_process_definition_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_definition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_kind', sa.String(32), nullable=False, server_default='eln_experiment'),
        sa.Column('execution_mode', sa.String(32), nullable=False, server_default='eln_experiment'),
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['process_definition_id'],
            ['eln_process_definitions.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['experiment_template_id'], ['experiment_templates.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'process_definition_id',
            'sort_order',
            name='uq_eln_process_definition_steps_sort',
        ),
    )
    op.create_index(
        'idx_eln_process_def_steps_def_id',
        'eln_process_definition_steps',
        ['process_definition_id'],
    )
    op.create_index(
        'idx_eln_process_def_steps_template_id',
        'eln_process_definition_steps',
        ['experiment_template_id'],
    )

    for table in ('eln_process_definitions', 'eln_process_definition_steps'):
        op.execute(f"""
            CREATE TRIGGER {table}_audit_timestamps
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
        """)
        op.execute(f"""
            CREATE TRIGGER {table}_update_modified_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
        """)
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL USING ({_CLIENT_POLICY});
        """)
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_user;')

    # ── Instance: link to definition ────────────────────────────────────────
    op.add_column(
        'eln_processes',
        sa.Column('process_definition_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_eln_processes_process_definition_id',
        'eln_processes',
        'eln_process_definitions',
        ['process_definition_id'],
        ['id'],
    )
    op.create_index(
        'idx_eln_processes_process_definition_id',
        'eln_processes',
        ['process_definition_id'],
    )

    # ── Instance steps: typed fields + current LimsRun ──────────────────────
    op.add_column(
        'eln_process_steps',
        sa.Column('step_kind', sa.String(32), nullable=False, server_default='eln_experiment'),
    )
    op.add_column(
        'eln_process_steps',
        sa.Column('execution_mode', sa.String(32), nullable=False, server_default='eln_experiment'),
    )
    op.add_column(
        'eln_process_steps',
        sa.Column('current_lims_run_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_eln_process_steps_current_lims_run_id',
        'eln_process_steps',
        'lims_runs',
        ['current_lims_run_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'idx_eln_process_steps_current_lims_run_id',
        'eln_process_steps',
        ['current_lims_run_id'],
    )
    # Allow null experiment_id already; template remains required for both kinds

    # ── Run history per process step ────────────────────────────────────────
    op.create_table(
        'eln_process_step_lims_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lims_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['process_step_id'],
            ['eln_process_steps.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['lims_run_id'], ['lims_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'process_step_id',
            'lims_run_id',
            name='uq_eln_process_step_lims_runs',
        ),
    )
    op.create_index(
        'idx_eln_process_step_lims_runs_step',
        'eln_process_step_lims_runs',
        ['process_step_id'],
    )
    op.create_index(
        'idx_eln_process_step_lims_runs_run',
        'eln_process_step_lims_runs',
        ['lims_run_id'],
    )
    op.execute('ALTER TABLE eln_process_step_lims_runs ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE eln_process_step_lims_runs FORCE ROW LEVEL SECURITY;')
    # Access via parent step's process created_by chain is complex; use created_by policy
    op.execute(f"""
        CREATE POLICY eln_process_step_lims_runs_access ON eln_process_step_lims_runs
        FOR ALL USING ({_CLIENT_POLICY});
    """)
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON eln_process_step_lims_runs TO lims_user'
    )

    # ── Backfill: ad hoc processes → snapshot definitions ───────────────────
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
            def_id UUID;
            step_r RECORD;
            def_name TEXT;
            n INT;
        BEGIN
            FOR r IN SELECT * FROM eln_processes WHERE process_definition_id IS NULL
            LOOP
                def_id := gen_random_uuid();
                def_name := r.name;
                n := 0;
                -- Ensure unique definition name
                WHILE EXISTS (SELECT 1 FROM eln_process_definitions WHERE name = def_name) LOOP
                    n := n + 1;
                    def_name := r.name || ' (legacy ' || n::text || ')';
                END LOOP;

                INSERT INTO eln_process_definitions (
                    id, name, description, active, created_at, created_by, modified_at, modified_by
                ) VALUES (
                    def_id,
                    def_name,
                    COALESCE(r.description, '') || E'\\n[Backfilled from ad hoc process instance]',
                    true,
                    COALESCE(r.created_at, NOW()),
                    r.created_by,
                    COALESCE(r.modified_at, NOW()),
                    r.modified_by
                );

                FOR step_r IN
                    SELECT * FROM eln_process_steps
                    WHERE process_id = r.id
                    ORDER BY sort_order
                LOOP
                    INSERT INTO eln_process_definition_steps (
                        id, process_definition_id, step_kind, execution_mode,
                        experiment_template_id, name, sort_order,
                        created_at, created_by, modified_at, modified_by
                    ) VALUES (
                        gen_random_uuid(),
                        def_id,
                        'eln_experiment',
                        'eln_experiment',
                        step_r.experiment_template_id,
                        step_r.name,
                        step_r.sort_order,
                        COALESCE(step_r.created_at, NOW()),
                        step_r.created_by,
                        COALESCE(step_r.modified_at, NOW()),
                        step_r.modified_by
                    );
                END LOOP;

                UPDATE eln_processes SET process_definition_id = def_id WHERE id = r.id;
            END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS eln_process_step_lims_runs CASCADE')
    op.drop_constraint(
        'fk_eln_process_steps_current_lims_run_id',
        'eln_process_steps',
        type_='foreignkey',
    )
    op.drop_column('eln_process_steps', 'current_lims_run_id')
    op.drop_column('eln_process_steps', 'execution_mode')
    op.drop_column('eln_process_steps', 'step_kind')
    op.drop_constraint(
        'fk_eln_processes_process_definition_id',
        'eln_processes',
        type_='foreignkey',
    )
    op.drop_column('eln_processes', 'process_definition_id')
    op.drop_table('eln_process_definition_steps')
    op.drop_table('eln_process_definitions')
