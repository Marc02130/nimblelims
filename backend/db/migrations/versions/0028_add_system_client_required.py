"""Add System client requirement for users

Revision ID: 0028
Revises: 0027
Create Date: 2026-01-22 12:00:00.000000

Enhances database schema to support a 'System' client for lab employees.
Ensures all users require a non-null client_id for better integrity.

Steps:
1. Ensure System client exists (idempotent)
2. Update any users with NULL client_id to System client
3. Add CHECK constraint to prevent NULL client_id
4. Alter column to NOT NULL

Based on NimbleLIMS Technical Document Section 3: Security and RBAC.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0028'
down_revision = '0027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Step 1: Ensure System client exists (idempotent)
    # Check if System client exists
    system_client_result = connection.execute(
        sa.text("""
            SELECT id FROM clients 
            WHERE name = 'System' 
            LIMIT 1
        """)
    ).fetchone()
    
    if not system_client_result:
        # Create System client if it doesn't exist
        connection.execute(
            sa.text("""
                INSERT INTO clients (id, name, description, active, created_at, modified_at, billing_info) 
                VALUES ('00000000-0000-0000-0000-000000000001', 'System', 'System client for lab employees', true, NOW(), NOW(), '{}')
                ON CONFLICT (id) DO NOTHING
            """)
        )
        system_client_id = '00000000-0000-0000-0000-000000000001'
    else:
        system_client_id = system_client_result[0]
    
    # Step 2: Update any users with NULL client_id to System client
    # This ensures all existing users have a client_id before we add the constraint
    null_client_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE client_id IS NULL")
    ).scalar()
    
    if null_client_count > 0:
        connection.execute(
            sa.text("""
                UPDATE users 
                SET client_id = :system_client_id 
                WHERE client_id IS NULL
            """),
            {'system_client_id': system_client_id}
        )
    
    # Step 3: Add CHECK constraint to prevent NULL client_id
    # First, drop the constraint if it exists (for idempotency)
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_not_null_check;
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END $$;
    """)
    
    # Add CHECK constraint
    op.execute("""
        ALTER TABLE users 
        ADD CONSTRAINT users_client_id_not_null_check 
        CHECK (client_id IS NOT NULL)
    """)
    
    # Step 4: Alter column to NOT NULL
    # This is idempotent - will fail silently if already NOT NULL
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE users ALTER COLUMN client_id SET NOT NULL;
        EXCEPTION
            WHEN OTHERS THEN
                -- Column might already be NOT NULL, ignore error
                NULL;
        END $$;
    """)


def downgrade() -> None:
    connection = op.get_bind()
    
    # Remove CHECK constraint
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_not_null_check;
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END $$;
    """)
    
    # Alter column back to nullable
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE users ALTER COLUMN client_id DROP NOT NULL;
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END $$;
    """)
    
    # Note: We do NOT set existing users back to NULL client_id
    # as this would break referential integrity. The System client
    # assignment remains in place even after downgrade.
