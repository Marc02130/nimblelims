"""Named asked-for LimsRun slot on routing_map.

Revision ID: 0079
Revises: 0078
Create Date: 2026-09-03

Author-named slot is a FK to a LimsRun step in the map chain. analysis_id
is a denorm of that step. Backfill: exactly one LimsRun in the chain → that
step; otherwise leave null (Route fails closed until admin names it).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "routing_map",
        sa.Column(
            "asked_for_step_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("eln_process_definition_steps.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_routing_map_asked_for_step_id",
        "routing_map",
        ["asked_for_step_id"],
    )
    conn = op.get_bind()
    maps = conn.execute(
        sa.text("SELECT id, process_definition_ids FROM routing_map")
    ).fetchall()
    for row in maps:
        chain = list(row[1] or [])
        if not chain:
            continue
        ordered = []
        for def_id in chain:
            steps = conn.execute(
                sa.text(
                    """
                    SELECT id, process_definition_id, sort_order, analysis_id
                    FROM eln_process_definition_steps
                    WHERE process_definition_id = :did
                      AND step_kind = 'lims_run'
                      AND analysis_id IS NOT NULL
                    ORDER BY sort_order
                    """
                ),
                {"did": def_id},
            ).fetchall()
            ordered.extend(steps)
        if len(ordered) != 1:
            continue
        step_id, analysis_id = ordered[0][0], ordered[0][3]
        conn.execute(
            sa.text(
                """
                UPDATE routing_map
                SET asked_for_step_id = :step_id, analysis_id = :analysis_id
                WHERE id = :id
                """
            ),
            {"step_id": step_id, "analysis_id": analysis_id, "id": row[0]},
        )


def downgrade() -> None:
    op.drop_index("ix_routing_map_asked_for_step_id", table_name="routing_map")
    op.drop_column("routing_map", "asked_for_step_id")
