"""Rename experiment_processes/process_steps → lims_run_checklists/steps

Revision ID: 0050
Revises: 0049
Create Date: 2026-07-11

Run-internal checklists (not ELN processes):
  - experiment_processes → lims_run_checklists
  - process_steps → lims_run_checklist_steps
  - process_id → checklist_id
  - process_step_status → lims_run_checklist_step_status
"""
from alembic import op

revision = '0050'
down_revision = '0049'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        'ALTER TYPE process_step_status RENAME TO lims_run_checklist_step_status'
    )

    op.rename_table('experiment_processes', 'lims_run_checklists')
    op.execute(
        'ALTER INDEX IF EXISTS idx_experiment_processes_lims_run_id '
        'RENAME TO idx_lims_run_checklists_lims_run_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_experiment_processes_run_id '
        'RENAME TO idx_lims_run_checklists_lims_run_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_experiment_processes_sort_order '
        'RENAME TO idx_lims_run_checklists_sort_order'
    )

    op.execute('DROP POLICY IF EXISTS experiment_processes_access ON lims_run_checklists')
    op.execute("""
        CREATE POLICY lims_run_checklists_access ON lims_run_checklists
        FOR ALL
        USING (has_experiment_access());
    """)
    op.execute('DROP TRIGGER IF EXISTS experiment_processes_audit_timestamps ON lims_run_checklists')
    op.execute('DROP TRIGGER IF EXISTS experiment_processes_update_modified_at ON lims_run_checklists')
    op.execute("""
        CREATE TRIGGER lims_run_checklists_audit_timestamps
        BEFORE INSERT OR UPDATE ON lims_run_checklists
        FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER lims_run_checklists_update_modified_at
        BEFORE UPDATE ON lims_run_checklists
        FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
    """)

    op.rename_table('process_steps', 'lims_run_checklist_steps')
    op.execute(
        'ALTER TABLE lims_run_checklist_steps RENAME COLUMN process_id TO checklist_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_process_steps_process_id '
        'RENAME TO idx_lims_run_checklist_steps_checklist_id'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_process_steps_sort_order '
        'RENAME TO idx_lims_run_checklist_steps_sort_order'
    )
    op.execute(
        'ALTER INDEX IF EXISTS idx_process_steps_status '
        'RENAME TO idx_lims_run_checklist_steps_status'
    )

    op.execute('DROP POLICY IF EXISTS process_steps_access ON lims_run_checklist_steps')
    op.execute("""
        CREATE POLICY lims_run_checklist_steps_access ON lims_run_checklist_steps
        FOR ALL
        USING (has_experiment_access());
    """)
    op.execute('DROP TRIGGER IF EXISTS process_steps_audit_timestamps ON lims_run_checklist_steps')
    op.execute('DROP TRIGGER IF EXISTS process_steps_update_modified_at ON lims_run_checklist_steps')
    op.execute("""
        CREATE TRIGGER lims_run_checklist_steps_audit_timestamps
        BEFORE INSERT OR UPDATE ON lims_run_checklist_steps
        FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER lims_run_checklist_steps_update_modified_at
        BEFORE UPDATE ON lims_run_checklist_steps
        FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
    """)

    for table in ('lims_run_checklists', 'lims_run_checklist_steps'):
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_user')


def downgrade() -> None:
    op.rename_table('lims_run_checklist_steps', 'process_steps')
    op.execute(
        'ALTER TABLE process_steps RENAME COLUMN checklist_id TO process_id'
    )
    op.rename_table('lims_run_checklists', 'experiment_processes')
    op.execute(
        'ALTER TYPE lims_run_checklist_step_status RENAME TO process_step_status'
    )
