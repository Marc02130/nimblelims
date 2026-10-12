"""Configuring agent: allow the Step 1 step states in the CHECK constraints.

Revision ID: 0087_agent_step_states
Revises: 0086_configuring_agent_locks

0086 (merged in #154) added the include control and safe rerun, but 0083's
CHECKs still only allow decision pending/accepted/skipped and status
proposed/stopped/applied/failed/skipped. On a migrated database every new run
failed with configuration_steps_decision_chk. This widens them:
decision adds 'included'/'excluded'; status adds 'unchanged'.
Also adds configuration_steps.stop_source: 'api' only when the called API
refused the row during Apply (422/404). Only that marks a stop retryable; gap
text is never trusted (a model can write any gap).
Downgrade maps the new values back to the old ones before narrowing.
"""

from alembic import op

revision = "0087_agent_step_states"
down_revision = "0086_configuring_agent_locks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE configuration_steps ADD COLUMN IF NOT EXISTS stop_source varchar(16);
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_stop_source_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_stop_source_chk
            CHECK (stop_source IS NULL OR stop_source = 'api');
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_decision_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_decision_chk
            CHECK (decision IN ('pending', 'accepted', 'skipped', 'included', 'excluded'));
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_status_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_status_chk
            CHECK (status IN ('proposed', 'stopped', 'applied', 'failed', 'skipped', 'unchanged'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE configuration_steps SET decision = 'accepted' WHERE decision = 'included';
        UPDATE configuration_steps SET decision = 'skipped' WHERE decision = 'excluded';
        UPDATE configuration_steps SET status = 'skipped' WHERE status = 'unchanged';
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_decision_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_decision_chk
            CHECK (decision IN ('pending', 'accepted', 'skipped'));
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_status_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_status_chk
            CHECK (status IN ('proposed', 'stopped', 'applied', 'failed', 'skipped'));
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_stop_source_chk;
        ALTER TABLE configuration_steps DROP COLUMN IF EXISTS stop_source;
        """
    )
