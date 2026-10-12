"""Configuring agent Step 1 locks: audit fields, step dependencies, RESTRICT backstop.

Revision ID: 0086_configuring_agent_locks
Revises: 0085_join_agent_reset

- configuration_runs: confirmed_by / confirmed_at, agent_provider / agent_model
  (D-8: the confirming user is the actor, with run id, provider, and model).
- configuration_steps: depends_on (positions of earlier rows this row needs),
  so Apply can refuse when an included row depends on an excluded stop.
- configuration_items: agent_assisted, agent_provider, agent_model. created_by
  is the confirming user and run_id the run.
- configuration_steps CHECKs widened: decision adds 'included'/'excluded'
  (per-row include control), status adds 'unchanged' (safe-rerun no-op row).
- Identity FKs: every foreign key that points at samples, containers, projects,
  clients, or users and has the default NO ACTION becomes ON DELETE RESTRICT.
  Nothing is deleted (FB-11); this is the database backstop. The one CASCADE in
  that set (password_reset_tokens.user_id, a throwaway token row) is left alone.
"""

from alembic import op

revision = "0086_configuring_agent_locks"
down_revision = "0085_join_agent_reset"
branch_labels = None
depends_on = None

IDENTITY_TABLES = ("samples", "containers", "projects", "clients", "users")

_SWAP = """
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.conname, c.conrelid::regclass AS tbl, pg_get_constraintdef(c.oid) AS def
    FROM pg_constraint c
    WHERE c.contype = 'f'
      AND c.confrelid::regclass::text IN ({tables})
      AND c.confdeltype = '{from_type}'
  LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.tbl, r.conname);
    EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I %s{suffix}', r.tbl, r.conname,
                   regexp_replace(r.def, '\\s+ON DELETE RESTRICT', ''));
  END LOOP;
END $$;
"""


def _tables() -> str:
    return ", ".join(f"'{name}'" for name in IDENTITY_TABLES)


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE configuration_runs
            ADD COLUMN IF NOT EXISTS confirmed_by uuid REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS confirmed_at timestamptz,
            ADD COLUMN IF NOT EXISTS agent_provider varchar(32),
            ADD COLUMN IF NOT EXISTS agent_model varchar(255);
        ALTER TABLE configuration_steps
            ADD COLUMN IF NOT EXISTS depends_on jsonb;
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_decision_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_decision_chk
            CHECK (decision IN ('pending', 'accepted', 'skipped', 'included', 'excluded'));
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_status_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_status_chk
            CHECK (status IN ('proposed', 'stopped', 'applied', 'failed', 'skipped', 'unchanged'));
        ALTER TABLE configuration_items
            ADD COLUMN IF NOT EXISTS agent_assisted boolean NOT NULL DEFAULT true,
            ADD COLUMN IF NOT EXISTS agent_provider varchar(32),
            ADD COLUMN IF NOT EXISTS agent_model varchar(255);
        """
    )
    op.execute(_SWAP.format(tables=_tables(), from_type="a", suffix=" ON DELETE RESTRICT"))


def downgrade() -> None:
    op.execute(_SWAP.format(tables=_tables(), from_type="r", suffix=""))
    op.execute(
        """
        ALTER TABLE configuration_items
            DROP COLUMN IF EXISTS agent_model,
            DROP COLUMN IF EXISTS agent_provider,
            DROP COLUMN IF EXISTS agent_assisted;
        UPDATE configuration_steps SET decision = 'accepted' WHERE decision = 'included';
        UPDATE configuration_steps SET decision = 'skipped' WHERE decision = 'excluded';
        UPDATE configuration_steps SET status = 'skipped' WHERE status = 'unchanged';
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_decision_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_decision_chk
            CHECK (decision IN ('pending', 'accepted', 'skipped'));
        ALTER TABLE configuration_steps DROP CONSTRAINT IF EXISTS configuration_steps_status_chk;
        ALTER TABLE configuration_steps ADD CONSTRAINT configuration_steps_status_chk
            CHECK (status IN ('proposed', 'stopped', 'applied', 'failed', 'skipped'));
        ALTER TABLE configuration_steps DROP COLUMN IF EXISTS depends_on;
        ALTER TABLE configuration_runs
            DROP COLUMN IF EXISTS agent_model,
            DROP COLUMN IF EXISTS agent_provider,
            DROP COLUMN IF EXISTS confirmed_at,
            DROP COLUMN IF EXISTS confirmed_by;
        """
    )
