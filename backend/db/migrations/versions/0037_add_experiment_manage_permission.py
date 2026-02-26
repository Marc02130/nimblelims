"""Add experiment:manage permission

Revision ID: 0037
Revises: 0036
Create Date: 2026-02-25

Adds experiment:manage permission and assigns it to Administrator,
Lab Manager, and Lab Technician roles (same pattern as batch:manage).
"""
from alembic import op
import sqlalchemy as sa

revision = '0037'
down_revision = '0036'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text("""
            INSERT INTO permissions (id, name, description, active, created_at, modified_at)
            VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """),
        {'name': 'experiment:manage', 'description': 'Manage experiments and experiment templates'}
    )

    for role_name in ['Administrator', 'Lab Manager', 'Lab Technician']:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = 'experiment:manage'
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {'role_name': role_name}
        )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE name = 'experiment:manage')
        """)
    )

    connection.execute(
        sa.text("DELETE FROM permissions WHERE name = 'experiment:manage'")
    )
