"""Lock leftover instrument_types_legacy: revoke writes and FORCE RLS.

Revision ID: 0112_instrument_legacy_lock
Revises: 0111_instrument_tracking

The leftover table stays. 0103 default privileges granted DELETE/INSERT/UPDATE.
Revoke those. Do not grant anything new. FORCE RLS so lims_app cannot use the
row even with leftover SELECT.
"""

from alembic import op

revision = "0112_instrument_legacy_lock"
down_revision = "0111_instrument_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("REVOKE INSERT, UPDATE, DELETE ON instrument_types_legacy FROM lims_app")
    op.execute("ALTER TABLE instrument_types_legacy ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE instrument_types_legacy FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE instrument_types_legacy NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE instrument_types_legacy DISABLE ROW LEVEL SECURITY")
