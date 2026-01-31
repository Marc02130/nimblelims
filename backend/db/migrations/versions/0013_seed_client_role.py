"""Seed Client role and sample client user

Revision ID: 0013
Revises: 0012
Create Date: 2025-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if Client role exists, if not create it
    # Note: Client role should already exist from migration 0004,
    # but we check for idempotency
    client_role_result = connection.execute(
        sa.text("""
            SELECT id FROM roles WHERE name = 'Client'
        """)
    ).fetchone()
    
    if client_role_result:
        client_role_id = client_role_result[0]
    else:
        # Create Client role if it doesn't exist
        client_role_id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'
        connection.execute(
            sa.text("""
                INSERT INTO roles (id, name, description, active, created_at, modified_at)
                VALUES (:id, 'Client', 'Read-only access for client users', true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {'id': client_role_id}
        )
    
    # Get permission IDs for Client role permissions
    # Try to use: sample:read, test:read, result:read, project:read, batch:read
    # If some don't exist, fall back to: test:assign, result:review, project:manage
    permissions_to_assign = []
    
    # Check which permissions exist and add them
    permission_checks = [
        ('sample:read', None),  # Required, should exist
        ('test:read', 'test:assign'),  # Preferred: test:read, fallback: test:assign
        ('result:read', 'result:review'),  # Preferred: result:read, fallback: result:review
        ('project:read', 'project:manage'),  # Preferred: project:read, fallback: project:manage
        ('batch:read', None)  # Required, should exist
    ]
    
    for preferred, fallback in permission_checks:
        # Check if preferred permission exists
        perm_check = connection.execute(
            sa.text("SELECT id FROM permissions WHERE name = :perm_name"),
            {'perm_name': preferred}
        ).fetchone()
        
        if perm_check:
            permissions_to_assign.append(preferred)
        elif fallback:
            # Check if fallback exists
            fallback_check = connection.execute(
                sa.text("SELECT id FROM permissions WHERE name = :perm_name"),
                {'perm_name': fallback}
            ).fetchone()
            if fallback_check:
                permissions_to_assign.append(fallback)
    
    # Assign permissions to Client role
    for perm_name in permissions_to_assign:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :role_id, p.id
                FROM permissions p
                WHERE p.name = :perm_name
                AND NOT EXISTS (
                    SELECT 1 FROM role_permissions rp
                    WHERE rp.role_id = :role_id
                    AND rp.permission_id = p.id
                )
            """),
            {'role_id': client_role_id, 'perm_name': perm_name}
        )
    
    # Get first client ID (assuming a client exists from prior migration)
    # Default to System client if no other client exists
    client_result = connection.execute(
        sa.text("""
            SELECT id FROM clients 
            WHERE active = true 
            ORDER BY created_at ASC 
            LIMIT 1
        """)
    ).fetchone()
    
    if not client_result:
        # Fallback to System client if no other client exists
        client_id = '00000000-0000-0000-0000-000000000001'
    else:
        client_id = client_result[0]
    
    # Create sample client user with SHA256 password hash (matches backend security.py)
    # Password: client123
    # SHA256 hash: 186474c1f2c2f735a54c2cf82ee8e87f2a5cd30940e280029363fecedfc5328c
    connection.execute(
        sa.text("""
            INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active, created_at, modified_at)
            VALUES (
                gen_random_uuid(),
                'Client User',
                'client',
                'client@example.com',
                '186474c1f2c2f735a54c2cf82ee8e87f2a5cd30940e280029363fecedfc5328c',
                :role_id,
                :client_id,
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (username) DO NOTHING
        """),
        {'role_id': client_role_id, 'client_id': client_id}
    )
    
    # Update projects_access RLS policy to include client_id filtering for Client role users
    # Drop existing policy first
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    
    # Recreate policy with explicit client_id check for Client role
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() 
            OR has_project_access(id)
            OR (
                -- Client role users can access projects where client_id matches their client_id
                EXISTS (
                    SELECT 1 FROM users u
                    JOIN roles r ON u.role_id = r.id
                    WHERE u.id = current_user_id()
                    AND r.name = 'Client'
                    AND u.client_id IS NOT NULL
                    AND projects.client_id = u.client_id
                )
            )
        );
    """)


def downgrade() -> None:
    connection = op.get_bind()
    
    # Remove client user
    connection.execute(
        sa.text("""
            DELETE FROM users WHERE username = 'client'
        """)
    )
    
    # Remove permissions from Client role
    # Get Client role ID
    client_role_result = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'Client'")
    ).fetchone()
    
    if client_role_result:
        client_role_id = client_role_result[0]
        # Remove all permissions that might have been assigned
        # Check for both preferred and fallback permissions
        permissions_to_remove = [
            'sample:read',
            'test:read',
            'test:assign',
            'result:read',
            'result:review',
            'project:read',
            'project:manage',
            'batch:read'
        ]
        
        for perm_name in permissions_to_remove:
            connection.execute(
                sa.text("""
                    DELETE FROM role_permissions
                    WHERE role_id = :role_id
                    AND permission_id = (SELECT id FROM permissions WHERE name = :perm_name)
                """),
                {'role_id': client_role_id, 'perm_name': perm_name}
            )
    
    # Restore original projects_access policy
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() OR has_project_access(id)
        );
    """)

