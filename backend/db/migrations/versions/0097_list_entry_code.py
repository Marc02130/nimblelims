"""Add a stable code on list entries for QC control roles.

Revision ID: 0097_list_entry_code
Revises: 0096_lab_tz_fk_restrict

samples.qc_type points at list_entries. The name is the lab's display label
and can be renamed. code is the designation a fit uses: 'positive' or
'negative'. Other entries stay null. Upgrade only adds the column, the
check, the partial unique index, and the seed backfill.
"""
from alembic import op

revision = "0097_list_entry_code"
down_revision = "0096_lab_tz_fk_restrict"
branch_labels = None
depends_on = None

QC_LIST_ID = "77777777-7777-7777-7777-777777777777"


def upgrade() -> None:
    op.execute("ALTER TABLE list_entries ADD COLUMN code VARCHAR(64)")
    op.execute(
        "ALTER TABLE list_entries ADD CONSTRAINT ck_list_entries_code "
        "CHECK (code IS NULL OR code IN ('positive', 'negative'))"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_list_entries_list_id_code "
        "ON list_entries (list_id, code) WHERE code IS NOT NULL"
    )
    # Stock seed names only. A row already renamed before this migration
    # keeps code null until an administrator sets it.
    op.execute(
        f"""
        UPDATE list_entries AS entry
        SET code = 'positive'
        FROM lists
        WHERE entry.list_id = lists.id
          AND entry.code IS NULL
          AND (
            lists.name = 'qc_types'
            OR lists.id = '{QC_LIST_ID}'
          )
          AND lower(entry.name) = 'positive control'
        """
    )
    op.execute(
        f"""
        UPDATE list_entries AS entry
        SET code = 'negative'
        FROM lists
        WHERE entry.list_id = lists.id
          AND entry.code IS NULL
          AND (
            lists.name = 'qc_types'
            OR lists.id = '{QC_LIST_ID}'
          )
          AND lower(entry.name) = 'negative control'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_list_entries_list_id_code")
    op.execute("ALTER TABLE list_entries DROP CONSTRAINT IF EXISTS ck_list_entries_code")
    op.execute("ALTER TABLE list_entries DROP COLUMN IF EXISTS code")
