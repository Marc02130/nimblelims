"""Process assignment is sample-in-a-container (Contents).

Revision ID: 0077
Revises: 0076
Create Date: 2026-08-30

eln_process_samples holds a Contents pair (sample + 1x1 container), not a
bare sample. A sample may occupy many vessels; only one container-with-sample
is on a process at a time (active rows).
"""

from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE eln_process_samples
            ADD COLUMN IF NOT EXISTS container_id UUID
            REFERENCES containers(id)
        """
    )
    op.execute(
        """
        UPDATE eln_process_samples ps
        SET container_id = sub.container_id
        FROM (
            SELECT DISTINCT ON (c.sample_id) c.sample_id, c.container_id
            FROM contents c
            ORDER BY c.sample_id, c.container_id
        ) sub
        WHERE ps.sample_id = sub.sample_id
          AND ps.container_id IS NULL
        """
    )
    op.execute("DELETE FROM eln_process_samples WHERE container_id IS NULL")
    op.execute(
        "ALTER TABLE eln_process_samples ALTER COLUMN container_id SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE eln_process_samples "
        "DROP CONSTRAINT IF EXISTS uq_eln_process_samples_process_sample"
    )
    op.execute("DROP INDEX IF EXISTS uq_eln_process_samples_process_sample")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_eln_process_samples_process_container
        ON eln_process_samples (process_id, container_id)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_eln_process_samples_active_sample
        ON eln_process_samples (process_id, sample_id)
        WHERE status <> 'removed'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_eln_process_samples_container_id
        ON eln_process_samples (container_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_eln_process_samples_container_id")
    op.execute("DROP INDEX IF EXISTS uq_eln_process_samples_active_sample")
    op.execute("DROP INDEX IF EXISTS uq_eln_process_samples_process_container")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_eln_process_samples_process_sample
        ON eln_process_samples (process_id, sample_id)
        """
    )
    op.execute("ALTER TABLE eln_process_samples DROP COLUMN IF EXISTS container_id")
