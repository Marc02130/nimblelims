"""P0 atomic-receive lists: Assigned/Pending test status and result qualifiers.

Revision ID: 0060
Revises: 0059
Create Date: 2026-08-20

Docs/seed only. No samples. No parent/child. No product endpoint.
"""
from alembic import op
import sqlalchemy as sa

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None

TEST_STATUS_LIST = "22222222-2222-2222-2222-222222222222"
QUALIFIER_LIST = "aaaa1111-bbbb-4ccc-8ddd-eeeeeeee0001"


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
            VALUES (gen_random_uuid(), 'Assigned/Pending', 'Test assigned, not yet in process', true, NOW(), NOW(), :list_id)
            ON CONFLICT (list_id, name) DO NOTHING
            """
        ),
        {"list_id": TEST_STATUS_LIST},
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO lists (id, name, description, active, created_at, modified_at)
            VALUES (:id, 'Result Qualifiers', 'Result qualifiers for reported values', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": QUALIFIER_LIST},
    )

    for name, desc in (
        ("<LOD", "Below limit of detection"),
        ("ND", "Not detected"),
    ):
        connection.execute(
            sa.text(
                """
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO NOTHING
                """
            ),
            {"name": name, "description": desc, "list_id": QUALIFIER_LIST},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM list_entries WHERE list_id = :list_id AND name IN ('<LOD', 'ND')"
        ),
        {"list_id": QUALIFIER_LIST},
    )
    connection.execute(sa.text("DELETE FROM lists WHERE id = :id"), {"id": QUALIFIER_LIST})
    connection.execute(
        sa.text(
            "DELETE FROM list_entries WHERE list_id = :list_id AND name = 'Assigned/Pending'"
        ),
        {"list_id": TEST_STATUS_LIST},
    )
