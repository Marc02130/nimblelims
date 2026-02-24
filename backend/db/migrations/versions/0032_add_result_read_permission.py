"""add_result_read_permission

Revision ID: 0032
Revises: 0031
Create Date: 2026-02-25

Adds the missing result:read permission and assigns it to
Administrator, Lab Manager, Lab Technician, and Client roles.
Also assigns existing result:update and result:delete permissions
to the Administrator role.
"""
from alembic import op
import sqlalchemy as sa

revision = '0032'
down_revision = '0031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # Create result:read permission
    connection.execute(
        sa.text("""
            INSERT INTO permissions (id, name, description, active, created_at, modified_at)
            VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """),
        {'name': 'result:read', 'description': 'Read results'}
    )

    # Assign result:read to Administrator, Lab Manager, Lab Technician, Client
    for role_name in ['Administrator', 'Lab Manager', 'Lab Technician', 'Client']:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = 'result:read'
                ON CONFLICT DO NOTHING
            """),
            {'role_name': role_name}
        )

    # Assign result:update to Administrator and Lab Manager
    for role_name in ['Administrator', 'Lab Manager']:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = 'result:update'
                ON CONFLICT DO NOTHING
            """),
            {'role_name': role_name}
        )

    # Assign result:delete to Administrator
    connection.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'Administrator' AND p.name = 'result:delete'
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE name = 'result:read')
        """)
    )

    connection.execute(
        sa.text("DELETE FROM permissions WHERE name = 'result:read'")
    )
