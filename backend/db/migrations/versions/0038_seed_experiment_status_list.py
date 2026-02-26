"""Seed experiment_status list for experiment status dropdown

Revision ID: 0038
Revises: 0037
Create Date: 2026-02-25

Creates the experiment_status list and entries (Draft, In Progress, Completed, etc.)
required by the experiments UI and experiments.status_id FK.
"""
from alembic import op
import sqlalchemy as sa

revision = '0038'
down_revision = '0037'
branch_labels = None
depends_on = None

# Fixed UUID for experiment_status list (no FK from other migrations)
EXPERIMENT_STATUS_LIST_ID = 'e0000001-0001-0001-0001-000000000001'


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text("""
            INSERT INTO lists (id, name, description, active, created_at, modified_at)
            VALUES (:id, 'experiment_status', 'Experiment status values', true, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """),
        {'id': EXPERIMENT_STATUS_LIST_ID}
    )

    result = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'experiment_status' LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        return
    list_id = str(row[0])

    entries = [
        ('Draft', 'Experiment drafted, not started'),
        ('In Progress', 'Experiment in progress'),
        ('Completed', 'Experiment completed'),
        ('On Hold', 'Experiment on hold'),
        ('Cancelled', 'Experiment cancelled'),
    ]
    for name, description in entries:
        connection.execute(
            sa.text("""
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO NOTHING
            """),
            {'name': name, 'description': description, 'list_id': list_id}
        )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text("DELETE FROM list_entries WHERE list_id = (SELECT id FROM lists WHERE name = 'experiment_status')")
    )
    connection.execute(
        sa.text("DELETE FROM lists WHERE name = 'experiment_status'")
    )
