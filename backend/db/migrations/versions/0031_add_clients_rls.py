"""Add RLS policy for clients table

Revision ID: 0031
Revises: 0030
Create Date: 2026-01-25 20:00:00.000000

Adds Row-Level Security (RLS) policy to the clients table so that:
- Administrators: see all clients
- System client users (lab employees): see all clients
- Regular client users: see only their own client record

This ensures client users cannot see other clients' information.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0031'
down_revision = '0030'
branch_labels = None
depends_on = None

# System client ID (hardcoded for consistency)
SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    # Enable RLS on clients table
    op.execute("ALTER TABLE clients ENABLE ROW LEVEL SECURITY;")
    
    # Create clients_access policy
    op.execute("""
        CREATE POLICY clients_access ON clients
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID
            )
            OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = clients.id
            )
        );
    """)


def downgrade() -> None:
    # Drop the policy
    op.execute("DROP POLICY IF EXISTS clients_access ON clients;")
    
    # Disable RLS on clients table
    op.execute("ALTER TABLE clients DISABLE ROW LEVEL SECURITY;")
