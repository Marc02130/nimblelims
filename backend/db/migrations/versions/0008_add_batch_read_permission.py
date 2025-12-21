"""add_batch_read_permission

Revision ID: 0008
Revises: 0007
Create Date: 2025-12-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Insert batch:read permission
    connection.execute(
        sa.text("""
            INSERT INTO permissions (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        {
            'id': 'e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1',
            'name': 'batch:read',
            'description': 'Read batches'
        }
    )
    
    # Add batch:read permission to Administrator role
    connection.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'Administrator' AND p.name = 'batch:read'
            ON CONFLICT DO NOTHING
        """)
    )
    
    # Add batch:read permission to Lab Manager role
    connection.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'Lab Manager' AND p.name = 'batch:read'
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    connection = op.get_bind()
    
    # Remove batch:read permission from roles
    connection.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE name = 'batch:read')
        """)
    )
    
    # Remove batch:read permission
    connection.execute(
        sa.text("""
            DELETE FROM permissions WHERE name = 'batch:read'
        """)
    )

