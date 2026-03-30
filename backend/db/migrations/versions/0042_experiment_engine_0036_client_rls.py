"""Client-scoped RLS for experiment engine tables from migration 0036

Revision ID: 0042
Revises: 0041
Create Date: 2026-03-29

Closes the client isolation gap left by migration 0036, which added 4 tables
with only role-only `has_experiment_access()` policies and no FORCE ROW LEVEL
SECURITY:

  - experiment_templates
  - experiments
  - experiment_details
  - experiment_sample_executions

Migration 0041 applied client-scoped RLS to the 5 tables from migration 0039.
This migration applies the identical pattern to the remaining 4 tables from 0036.

Before (migration 0036):
    USING (has_experiment_access())
    → Any Lab Tech at ANY client org can read ALL data across ALL orgs

After:
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
    )
    → Users only see rows created by members of their own client organization.
    → Admins retain full visibility across all clients.

Indexes added:
    idx_experiment_templates_created_by       — missing, needed for RLS subquery
    idx_experiment_details_created_by         — missing, needed for RLS subquery
    idx_experiment_sample_executions_created_by — missing, needed for RLS subquery

    experiments already has idx_experiments_created_by (from migration 0036).

Downgrade restores the role-only has_experiment_access() policies and removes
FORCE ROW LEVEL SECURITY. The three added indexes are also dropped on downgrade.
"""
from alembic import op

revision = '0042'
down_revision = '0041'
branch_labels = None
depends_on = None

# All four tables from migration 0036 that need client-scoped RLS.
# All four have a created_by → users.id FK column.
_TABLES = (
    'experiment_templates',
    'experiments',
    'experiment_details',
    'experiment_sample_executions',
)

# Three of the four tables need a new created_by index.
# experiments already has idx_experiments_created_by from migration 0036.
_TABLES_NEEDING_INDEX = (
    'experiment_templates',
    'experiment_details',
    'experiment_sample_executions',
)

# Policy USING clause shared by all 4 tables.
# Pattern mirrors migration 0041 exactly.
#
# Breakdown:
#   is_admin()              → Administrators always have full access
#   has_experiment_access() → Must have at least Lab Technician role
#   created_by IN (...)     → Row must belong to current user's client org
#
# NULL created_by: the IN subquery returns FALSE for NULL, so NULL-created rows
# are only visible to admins. In practice the API always populates created_by
# from the authenticated user (verified: ExperimentService._user_id() returns
# current_user.id for all four tables).
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
    # Add created_by indexes on tables that lack them.
    # Must come before the policy change so the new RLS subquery is efficient
    # from the first request after migration.
    for table in _TABLES_NEEDING_INDEX:
        op.execute(
            f'CREATE INDEX IF NOT EXISTS idx_{table}_created_by ON {table} (created_by);'
        )

    for table in _TABLES:
        # Drop the role-only policy created in migration 0036
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')

        # Create client-scoped replacement
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING ({_CLIENT_POLICY});
        """)

        # Ensure RLS applies even to the table owner (e.g. the postgres role
        # used by the migration runner). Without FORCE, the table owner bypasses
        # RLS entirely on direct connections — defeating the isolation guarantee.
        # Pattern mirrors migration 0041.
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')


def downgrade() -> None:
    for table in _TABLES:
        # Restore the role-only policy from migration 0036
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')

        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING (has_experiment_access());
        """)

        # Revert FORCE — restore the pre-0042 state where owner bypass was
        # not explicitly prevented (matching migration 0036's behaviour).
        op.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;')

    # Drop the indexes added in upgrade.
    # experiments index is NOT dropped — it predates this migration (0036).
    for table in _TABLES_NEEDING_INDEX:
        op.execute(f'DROP INDEX IF EXISTS idx_{table}_created_by;')
