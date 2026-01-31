"""Add Laboratory QC system project for batch QC samples

Revision ID: 0025
Revises: 0024
Create Date: 2026-01-21

This migration creates a system-level "Laboratory QC" project that all batch QC samples
will be associated with. This ensures QC samples are batch-level controls shared across
all client projects in a batch, rather than being tied to individual client projects.

The project uses a well-known UUID for easy reference in application code.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0025'
down_revision = '0024'
branch_labels = None
depends_on = None

# Well-known UUID for the Laboratory QC project
LAB_QC_PROJECT_ID = '00000000-0000-0000-0000-000000000002'
SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    connection = op.get_bind()
    
    # Ensure System client exists (should already exist from 0004_initial_data.py)
    connection.execute(
        sa.text("""
            INSERT INTO clients (id, name, description, active, created_at, modified_at, billing_info)
            VALUES (:client_id, 'System', 'System client for internal operations', true, NOW(), NOW(), '{}')
            ON CONFLICT (id) DO NOTHING
        """),
        {'client_id': SYSTEM_CLIENT_ID}
    )
    
    # Get or create the "Active" project status
    # First try to find existing Active status in Project Status list
    active_status_result = connection.execute(
        sa.text("""
            SELECT le.id FROM list_entries le
            JOIN lists l ON le.list_id = l.id
            WHERE LOWER(l.name) LIKE '%project%status%' AND LOWER(le.name) = 'active'
            LIMIT 1
        """)
    ).fetchone()
    
    if active_status_result:
        active_status_id = active_status_result[0]
    else:
        # Fallback: get any project status entry
        any_status_result = connection.execute(
            sa.text("""
                SELECT le.id FROM list_entries le
                JOIN lists l ON le.list_id = l.id
                WHERE LOWER(l.name) LIKE '%project%status%'
                LIMIT 1
            """)
        ).fetchone()
        
        if any_status_result:
            active_status_id = any_status_result[0]
        else:
            # Create project status list and Active entry if none exist
            connection.execute(
                sa.text("""
                    INSERT INTO lists (id, name, description, active, created_at, modified_at)
                    VALUES ('33333333-3333-3333-3333-333333333333', 'Project Status', 'Project status values', true, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """)
            )
            connection.execute(
                sa.text("""
                    INSERT INTO list_entries (id, name, description, list_id, active, created_at, modified_at)
                    VALUES (gen_random_uuid(), 'Active', 'Project active', '33333333-3333-3333-3333-333333333333', true, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """)
            )
            # Now get it
            active_status_result = connection.execute(
                sa.text("""
                    SELECT id FROM list_entries WHERE list_id = '33333333-3333-3333-3333-333333333333' AND name = 'Active' LIMIT 1
                """)
            ).fetchone()
            active_status_id = active_status_result[0] if active_status_result else None
    
    if not active_status_id:
        raise Exception("Could not find or create Active project status")
    
    # Create the Laboratory QC project
    connection.execute(
        sa.text("""
            INSERT INTO projects (
                id, name, description, client_id, status, 
                start_date, active, created_at, modified_at
            )
            VALUES (
                :project_id,
                'Laboratory QC',
                'System project for batch QC samples. All QC samples created during batch creation are associated with this project to serve as batch-level quality controls shared across all client projects in the batch.',
                :client_id,
                :status_id,
                NOW(),
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                active = true
        """),
        {
            'project_id': LAB_QC_PROJECT_ID,
            'client_id': SYSTEM_CLIENT_ID,
            'status_id': active_status_id
        }
    )
    
    # Add a QC sample type if not exists
    connection.execute(
        sa.text("""
            INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
            SELECT 
                gen_random_uuid(),
                'QC',
                'Quality Control sample',
                true,
                NOW(),
                NOW(),
                l.id
            FROM lists l
            WHERE l.name = 'Sample Types'
            AND NOT EXISTS (
                SELECT 1 FROM list_entries le 
                WHERE le.list_id = l.id AND le.name = 'QC'
            )
        """)
    )


def downgrade() -> None:
    connection = op.get_bind()
    
    # Note: We don't delete the project as it may have QC samples associated with it
    # Instead, we just mark it as inactive
    connection.execute(
        sa.text("""
            UPDATE projects SET active = false WHERE id = :project_id
        """),
        {'project_id': LAB_QC_PROJECT_ID}
    )
