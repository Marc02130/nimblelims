"""CRO lifecycle: ordered/results_received/canceled states + lifecycle_type on templates

Revision ID: 0044
Revises: 0043
Create Date: 2026-04-02

Adds support for two run lifecycle types:
  - standard: draft → running → complete → published | failed | canceled
  - cro:      draft → ordered → running → results_received → complete → published | failed | canceled

Changes:
  - experiment_run_status ENUM: add 'ordered', 'results_received', 'canceled'
  - experiment_runs.canceled_at: timestamp set when run is canceled
  - experiment_templates.lifecycle_type: 'standard' (default) or 'cro'

Note: ALTER TYPE ADD VALUE cannot run inside a transaction (PG < 14).
The enum additions use AUTOCOMMIT mode; the column additions use a separate
transactional block.
"""
from alembic import op
import sqlalchemy as sa

revision = '0044'
down_revision = '0043'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: add enum values outside any transaction ────────────────────────
    # ALTER TYPE ADD VALUE cannot run inside a transaction (PG < 14).
    # Alembic opens an implicit transaction, so we COMMIT it first, run the
    # ALTER TYPE statements (they run in implicit per-statement autocommit), then
    # open a new explicit BEGIN so that the column DDL below runs transactionally.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE experiment_run_status ADD VALUE IF NOT EXISTS 'ordered'"))
    conn.execute(sa.text("ALTER TYPE experiment_run_status ADD VALUE IF NOT EXISTS 'results_received'"))
    conn.execute(sa.text("ALTER TYPE experiment_run_status ADD VALUE IF NOT EXISTS 'canceled'"))
    conn.execute(sa.text("BEGIN"))

    # ── Step 2: column additions (run inside normal transaction) ───────────────
    op.add_column(
        'experiment_runs',
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
    )

    op.add_column(
        'experiment_templates',
        sa.Column(
            'lifecycle_type',
            sa.String(32),
            nullable=False,
            server_default='standard',
        ),
    )
    op.create_index(
        'idx_experiment_templates_lifecycle_type',
        'experiment_templates',
        ['lifecycle_type'],
    )


def downgrade() -> None:
    # Postgres ENUM values cannot be removed — downgrade drops the columns only.
    # The 'ordered', 'results_received', 'canceled' enum values will remain but
    # are inert once lifecycle_type column is gone.
    op.drop_index('idx_experiment_templates_lifecycle_type', 'experiment_templates')
    op.drop_column('experiment_templates', 'lifecycle_type')
    op.drop_column('experiment_runs', 'canceled_at')
