"""Refine project schema for auto-creation during accessioning

Revision ID: 0022
Revises: 0021
Create Date: 2026-01-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure projects.client_id is NOT NULL (should already be, but verify/alter if needed)
    # Check if there are any NULL values first
    connection = op.get_bind()
    null_client_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM projects WHERE client_id IS NULL")
    ).scalar()
    
    if null_client_count > 0:
        # If there are NULL values, set them to the System client
        system_client_id = connection.execute(
            sa.text("SELECT id FROM clients WHERE name = 'System' LIMIT 1")
        ).scalar()
        
        if system_client_id:
            connection.execute(
                sa.text("UPDATE projects SET client_id = :client_id WHERE client_id IS NULL"),
                {'client_id': system_client_id}
            )
        else:
            # Create System client if it doesn't exist
            connection.execute(
                sa.text("""
                    INSERT INTO clients (id, name, description, active, created_at, modified_at, billing_info)
                    VALUES ('00000000-0000-0000-0000-000000000001', 'System', 'System client for orphaned projects', true, NOW(), NOW(), '{}')
                    ON CONFLICT (id) DO NOTHING
                """)
            )
            system_client_id = '00000000-0000-0000-0000-000000000001'
            connection.execute(
                sa.text("UPDATE projects SET client_id = :client_id WHERE client_id IS NULL"),
                {'client_id': system_client_id}
            )
    
    # Alter column to ensure NOT NULL constraint (idempotent - will fail silently if already NOT NULL)
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE projects ALTER COLUMN client_id SET NOT NULL;
        EXCEPTION
            WHEN OTHERS THEN
                -- Column might already be NOT NULL, ignore error
                NULL;
        END $$;
    """)
    
    # Ensure idx_projects_client_id exists (should already exist from 0005_indexes.py, but verify)
    # Check if index exists
    index_exists = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'projects' 
                AND indexname = 'idx_projects_client_id'
            )
        """)
    ).scalar()
    
    if not index_exists:
        op.create_index('idx_projects_client_id', 'projects', ['client_id'])
    
    # Update has_project_access function to support auto-creation checks
    # Allow lab technicians and managers to check project existence for auto-creation
    op.execute("""
        CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
        RETURNS BOOLEAN AS $$
        DECLARE
            project_client_project_id UUID;
            project_client_id UUID;
            user_client_id UUID;
        BEGIN
            -- Admin users can access all projects
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Get the project's client_project_id and client_id
            SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
            FROM projects p
            WHERE p.id = project_uuid;
            
            -- If project has a client_project_id, check access via client_projects
            IF project_client_project_id IS NOT NULL THEN
                -- Get user's client_id
                SELECT u.client_id INTO user_client_id
                FROM users u
                WHERE u.id = current_user_id();
                
                -- Check if user's client_id matches the client_project's client_id
                IF user_client_id IS NOT NULL THEN
                    IF EXISTS (
                        SELECT 1 FROM client_projects cp
                        WHERE cp.id = project_client_project_id
                        AND cp.client_id = user_client_id
                    ) THEN
                        RETURN TRUE;
                    END IF;
                END IF;
            END IF;
            
            -- Fall back to direct project access check (for lab technicians or direct grants)
            RETURN EXISTS (
                SELECT 1 FROM project_users pu
                WHERE pu.project_id = project_uuid
                AND pu.user_id = current_user_id()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Update projects_access RLS policy to allow auto-creation
    # Drop existing policy
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    
    # Recreate policy with support for auto-creation
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() 
            OR has_project_access(id)
            OR EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id()
                AND r.name = 'Client'
                AND u.client_id IS NOT NULL
                AND projects.client_id = u.client_id
            )
            OR EXISTS (
                -- Allow Lab Technicians and Lab Managers to view projects for auto-creation checks
                SELECT 1 FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id()
                AND r.name IN ('Lab Technician', 'Lab Manager')
                AND projects.active = true
            )
        );
    """)
    
    # Verify client_projects_access policy exists (from 0022)
    # The policy from 0022 already allows Lab Technicians and Lab Managers to view active client_projects
    # This is sufficient for auto-creation - no changes needed
    
    # Seed example data: Link existing projects to clients if they don't have client_project_id
    # This encourages the use of client_project_id
    connection.execute(
        sa.text("""
            -- Update projects to link to client_projects where possible
            -- This is a best-effort linking based on client_id matching
            UPDATE projects p
            SET client_project_id = (
                SELECT cp.id 
                FROM client_projects cp
                WHERE cp.client_id = p.client_id
                AND cp.active = true
                LIMIT 1
            )
            WHERE p.client_project_id IS NULL
            AND EXISTS (
                SELECT 1 FROM client_projects cp
                WHERE cp.client_id = p.client_id
                AND cp.active = true
            )
        """)
    )


def downgrade() -> None:
    # Restore original projects_access policy (without auto-creation support)
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() OR has_project_access(id)
        );
    """)
    
    # Restore original has_project_access function (from 0011)
    op.execute("""
        CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
        RETURNS BOOLEAN AS $$
        DECLARE
            project_client_project_id UUID;
            project_client_id UUID;
            user_client_id UUID;
        BEGIN
            -- Admin users can access all projects
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Get the project's client_project_id and client_id
            SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
            FROM projects p
            WHERE p.id = project_uuid;
            
            -- If project has a client_project_id, check access via client_projects
            IF project_client_project_id IS NOT NULL THEN
                -- Get user's client_id
                SELECT u.client_id INTO user_client_id
                FROM users u
                WHERE u.id = current_user_id();
                
                -- Check if user's client_id matches the client_project's client_id
                IF user_client_id IS NOT NULL THEN
                    IF EXISTS (
                        SELECT 1 FROM client_projects cp
                        WHERE cp.id = project_client_project_id
                        AND cp.client_id = user_client_id
                    ) THEN
                        RETURN TRUE;
                    END IF;
                END IF;
            END IF;
            
            -- Fall back to direct project access check (for lab technicians or direct grants)
            RETURN EXISTS (
                SELECT 1 FROM project_users pu
                WHERE pu.project_id = project_uuid
                AND pu.user_id = current_user_id()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

