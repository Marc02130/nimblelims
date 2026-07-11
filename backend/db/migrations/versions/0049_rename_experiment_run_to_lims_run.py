"""Rename experiment_runs → lims_runs (and related columns/types)

Revision ID: 0049
Revises: 0048
Create Date: 2026-07-11

Full logical rename for development (no external API consumers yet):
  - table experiment_runs → lims_runs
  - enum experiment_run_status → lims_run_status
  - FK columns experiment_run_id → lims_run_id
  - table experiment_data → lims_run_data
  - table experiment_data_exclusions → lims_run_data_exclusions
  - column experiment_data_id → lims_run_data_id
  - global UNIQUE on lims_runs.name (align with other first-class entities)
"""
from alembic import op

revision = '0049'
down_revision = '0048'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum type ───────────────────────────────────────────────────────────
    op.execute('ALTER TYPE experiment_run_status RENAME TO lims_run_status')

    # ── Primary table ───────────────────────────────────────────────────────
    op.rename_table('experiment_runs', 'lims_runs')

    # Indexes (Postgres renames some with table; recreate named ones we care about)
    op.execute('ALTER INDEX IF EXISTS ix_experiment_runs_name RENAME TO ix_lims_runs_name')
    op.execute('ALTER INDEX IF EXISTS idx_experiment_runs_template_id RENAME TO idx_lims_runs_template_id')
    op.execute('ALTER INDEX IF EXISTS idx_experiment_runs_status RENAME TO idx_lims_runs_status')
    op.execute('ALTER INDEX IF EXISTS idx_experiment_runs_created_by RENAME TO idx_lims_runs_created_by')

    # Global unique name (was per-client only at service layer)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_lims_runs_name'
            ) THEN
                ALTER TABLE lims_runs ADD CONSTRAINT uq_lims_runs_name UNIQUE (name);
            END IF;
        END $$;
    """)

    # RLS policy rename
    op.execute('DROP POLICY IF EXISTS experiment_runs_access ON lims_runs')
    op.execute("""
        CREATE POLICY lims_runs_access ON lims_runs
        FOR ALL
        USING (
            is_admin() OR (
                has_experiment_access() AND
                created_by IN (
                    SELECT u.id FROM users u
                    WHERE u.client_id = (
                        SELECT u2.client_id FROM users u2
                        WHERE u2.id = current_user_id()
                    )
                )
            )
        );
    """)
    op.execute('ALTER TABLE lims_runs ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE lims_runs FORCE ROW LEVEL SECURITY')

    # Triggers (names often include table name)
    op.execute('DROP TRIGGER IF EXISTS experiment_runs_audit_timestamps ON lims_runs')
    op.execute('DROP TRIGGER IF EXISTS experiment_runs_update_modified_at ON lims_runs')
    op.execute("""
        CREATE TRIGGER lims_runs_audit_timestamps
        BEFORE INSERT OR UPDATE ON lims_runs
        FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER lims_runs_update_modified_at
        BEFORE UPDATE ON lims_runs
        FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
    """)

    # ── experiment_data → lims_run_data ─────────────────────────────────────
    op.rename_table('experiment_data', 'lims_run_data')
    op.execute(
        'ALTER TABLE lims_run_data RENAME COLUMN experiment_run_id TO lims_run_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_experiment_data_run_id RENAME TO idx_lims_run_data_run_id'
    )
    op.execute('DROP POLICY IF EXISTS experiment_data_access ON lims_run_data')
    op.execute("""
        CREATE POLICY lims_run_data_access ON lims_run_data
        FOR ALL
        USING (
            is_admin() OR (
                has_experiment_access() AND
                created_by IN (
                    SELECT u.id FROM users u
                    WHERE u.client_id = (
                        SELECT u2.client_id FROM users u2
                        WHERE u2.id = current_user_id()
                    )
                )
            )
        );
    """)
    op.execute('DROP TRIGGER IF EXISTS experiment_data_audit_timestamps ON lims_run_data')
    op.execute('DROP TRIGGER IF EXISTS experiment_data_update_modified_at ON lims_run_data')
    op.execute("""
        CREATE TRIGGER lims_run_data_audit_timestamps
        BEFORE INSERT OR UPDATE ON lims_run_data
        FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER lims_run_data_update_modified_at
        BEFORE UPDATE ON lims_run_data
        FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
    """)

    # ── experiment_processes.experiment_run_id → lims_run_id ────────────────
    op.execute(
        'ALTER TABLE experiment_processes RENAME COLUMN experiment_run_id TO lims_run_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_experiment_processes_run_id '
        'RENAME TO idx_experiment_processes_lims_run_id'
    )

    # ── dose_response_results.experiment_run_id → lims_run_id ───────────────
    op.execute(
        'ALTER TABLE dose_response_results RENAME COLUMN experiment_run_id TO lims_run_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_drr_experiment_run_id RENAME TO idx_drr_lims_run_id'
    )

    # ── experiment_data_exclusions → lims_run_data_exclusions ───────────────
    op.rename_table('experiment_data_exclusions', 'lims_run_data_exclusions')
    op.execute(
        'ALTER TABLE lims_run_data_exclusions '
        'RENAME COLUMN experiment_data_id TO lims_run_data_id'
    )

    # Grants (lims_user)
    for table in (
        'lims_runs',
        'lims_run_data',
        'lims_run_data_exclusions',
    ):
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_user')


def downgrade() -> None:
    op.rename_table('lims_run_data_exclusions', 'experiment_data_exclusions')
    op.execute(
        'ALTER TABLE experiment_data_exclusions '
        'RENAME COLUMN lims_run_data_id TO experiment_data_id'
    )

    op.execute(
        'ALTER TABLE dose_response_results RENAME COLUMN lims_run_id TO experiment_run_id'
    )
    op.execute(
        'ALTER TABLE experiment_processes RENAME COLUMN lims_run_id TO experiment_run_id'
    )

    op.rename_table('lims_run_data', 'experiment_data')
    op.execute(
        'ALTER TABLE experiment_data RENAME COLUMN lims_run_id TO experiment_run_id'
    )

    op.execute('ALTER TABLE lims_runs DROP CONSTRAINT IF EXISTS uq_lims_runs_name')
    op.rename_table('lims_runs', 'experiment_runs')
    op.execute('ALTER TYPE lims_run_status RENAME TO experiment_run_status')
