"""Client-scoped RLS for flexible experiment engine tables

Revision ID: 0041
Revises: 0040
Create Date: 2026-03-25

Replaces the role-only RLS policies on the 5 flexible experiment engine tables
with policies that combine role-based access (has_experiment_access) with
client-level tenant isolation (created_by → users.client_id).

Before (migration 0039):
    USING (has_experiment_access())
    → Any Lab Tech/Manager/Admin at ANY client org can read ALL experiment data

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

Tables affected:
    experiment_runs         — direct created_by
    experiment_data         — direct created_by
    instrument_parsers      — direct created_by
    robot_worklist_configs  — direct created_by
    sop_parse_jobs          — direct created_by
"""
from alembic import op

revision = '0041'
down_revision = '0040'
branch_labels = None
depends_on = None

# Tables from migration 0039 that need client-scoped policies.
# All 5 have a created_by → users.id FK column.
_TABLES = (
    'experiment_runs',
    'experiment_data',
    'instrument_parsers',
    'robot_worklist_configs',
    'sop_parse_jobs',
)

# Policy USING clause shared by all 5 tables.
# Pattern mirrors samples/projects/etc. in migration 0003.
#
# Breakdown:
#   is_admin()              → Administrators always have full access
#   has_experiment_access() → Must have at least Lab Technician role
#   created_by IN (...)     → Row must belong to current user's client org
#
# NULL created_by: handled by is_admin() — the IN subquery returns FALSE for
# NULL, so NULL-created rows are only visible to admins, which is acceptable
# (in practice the API always populates created_by from the authenticated user).
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
    for table in _TABLES:
        # Drop the role-only policy created in migration 0039
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
        # Pattern mirrors migration 0030 (clients table).
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')


def downgrade() -> None:
    for table in _TABLES:
        # Restore the role-only policy from migration 0039
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')

        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING (has_experiment_access());
        """)

        # Revert FORCE — restore the pre-0041 state where owner bypass was
        # not explicitly prevented (matching migration 0039's behaviour).
        op.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;')
