"""P2: Route matches LIMS Run analyses in the chain, not a map analysis field.

Revision ID: 0076
Revises: 0075
Create Date: 2026-08-30

A route is an ordered process list. Assignment requires:
- sample type on the first process's first experiment / LIMS Run
- asked-for analysis equal to a LIMS Run analysis somewhere in the route

Drop gist exclude on (analysis_id, sample_type_id, tat_range). Overlap is
application-side: TAT && first-step types && LIMS-run analysis sets.
routing_map.analysis_id stays as a display hint (first LIMS Run analysis).
"""

from alembic import op

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE routing_map DROP CONSTRAINT IF EXISTS routing_map_tat_excl")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE routing_map ADD CONSTRAINT routing_map_tat_excl
        EXCLUDE USING gist (
            analysis_id WITH =,
            sample_type_id WITH =,
            tat_range WITH &&
        ) WHERE (active)
        """
    )
