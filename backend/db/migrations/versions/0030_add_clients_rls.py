"""Add RLS policy for clients table

Revision ID: 0030
Revises: 0029
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
revision = '0030'
down_revision = '0029'
branch_labels = None
depends_on = None

# System client ID (hardcoded for consistency)
SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    # Enable RLS on clients (not in 0029's list). Without this, the policy has no effect.
    op.execute("ALTER TABLE clients ENABLE ROW LEVEL SECURITY;")
    # Create a more explicit and restrictive policy
    # The key is to use a single condition that explicitly checks:
    # 1. Is the user an admin? → allow all
    # 2. Is the user a system client user? → allow all
    # 3. Is the user's client_id equal to this client's id? → allow only this row
    # 4. Otherwise → deny (implicit, as no condition matches)
    op.execute("""
        CREATE POLICY clients_access ON clients
        FOR ALL
        USING (
            -- Case 1: Administrators see all clients
            is_admin() = true
            OR
            -- Case 2: System client users (lab employees) see all clients
            (
                EXISTS (
                    SELECT 1 FROM users u
                    WHERE u.id = current_user_id()
                    AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID
                )
            )
            OR
            -- Case 3: Regular client users see ONLY their own client record
            -- This condition is evaluated per-row, so it will only match
            -- the row where clients.id equals the user's client_id
            (
                EXISTS (
                    SELECT 1 FROM users u
                    WHERE u.id = current_user_id()
                    AND u.client_id IS NOT NULL
                    AND u.client_id != '00000000-0000-0000-0000-000000000001'::UUID
                    AND u.client_id = clients.id
                )
            )
        );
    """)

    # Force RLS so the table owner (lims_user) is also subject to RLS; otherwise the app would see all rows.
    op.execute("ALTER TABLE clients FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    # Drop the policy
    op.execute("DROP POLICY IF EXISTS clients_access ON clients;")
    
    # Disable RLS on clients table
    op.execute("ALTER TABLE clients DISABLE ROW LEVEL SECURITY;")
