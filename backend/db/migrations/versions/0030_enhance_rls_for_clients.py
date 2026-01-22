"""Enhance RLS policies for client data isolation

Revision ID: 0030
Revises: 0029
Create Date: 2026-01-22 14:00:00.000000

Enhances Row-Level Security (RLS) policies to limit data access for client users
to only their own data, using the System client for lab employees.

Key Logic:
- System client users (lab employees) have full access to all data
- Regular client users can only access data where project.client_id = user.client_id
- Falls back to project_users junction for granular grants

Based on:
- NimbleLIMS Technical Document Section 3: RLS Policies
- PRD Section 3.1: Data Isolation

Assumes System client exists (from migration 0029).
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
    # Step 1: Update has_project_access function with System client logic
    op.execute("""
        CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
        RETURNS BOOLEAN AS $$
        DECLARE
            project_client_project_id UUID;
            project_client_id UUID;
            user_client_id UUID;
            system_client_id UUID;
        BEGIN
            -- Admin users can access all projects
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Get System client ID (hardcoded for performance)
            system_client_id := '00000000-0000-0000-0000-000000000001'::UUID;
            
            -- Get user's client_id
            SELECT u.client_id INTO user_client_id
            FROM users u
            WHERE u.id = current_user_id();
            
            -- If user is associated with System client, grant full access (lab employees)
            IF user_client_id = system_client_id THEN
                RETURN TRUE;
            END IF;
            
            -- Get the project's client_project_id and client_id
            SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
            FROM projects p
            WHERE p.id = project_uuid;
            
            -- If project has a client_project_id, check access via client_projects
            IF project_client_project_id IS NOT NULL THEN
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
            
            -- For regular client users: check if project.client_id matches user.client_id
            IF project_client_id IS NOT NULL AND user_client_id IS NOT NULL THEN
                IF project_client_id = user_client_id THEN
                    RETURN TRUE;
                END IF;
            END IF;
            
            -- Fall back to direct project access check (for granular grants via project_users junction)
            -- This allows lab staff to be assigned to specific projects even if not System client
            RETURN EXISTS (
                SELECT 1 FROM project_users pu
                WHERE pu.project_id = project_uuid
                AND pu.user_id = current_user_id()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Step 2: Update projects_access policy
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() 
            OR has_project_access(id)
        );
    """)
    
    # Step 3: Update samples_access policy
    op.execute("DROP POLICY IF EXISTS samples_access ON samples;")
    op.execute("""
        CREATE POLICY samples_access ON samples
        FOR ALL
        USING (
            is_admin() 
            OR has_project_access(project_id)
        );
    """)
    
    # Step 4: Update tests_access policy
    op.execute("DROP POLICY IF EXISTS tests_access ON tests;")
    op.execute("""
        CREATE POLICY tests_access ON tests
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = tests.sample_id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Step 5: Update results_access policy
    op.execute("DROP POLICY IF EXISTS results_access ON results;")
    op.execute("""
        CREATE POLICY results_access ON results
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM tests t
                JOIN samples s ON t.sample_id = s.id
                WHERE t.id = results.test_id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Step 6: Update batches_access policy
    op.execute("DROP POLICY IF EXISTS batches_access ON batches;")
    op.execute("""
        CREATE POLICY batches_access ON batches
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM batch_containers bc
                JOIN containers c ON bc.container_id = c.id
                JOIN contents ct ON c.id = ct.container_id
                JOIN samples s ON ct.sample_id = s.id
                WHERE bc.batch_id = batches.id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Step 7: Update containers_access policy
    op.execute("DROP POLICY IF EXISTS containers_access ON containers;")
    op.execute("""
        CREATE POLICY containers_access ON containers
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Step 8: Update client_projects_access policy
    op.execute("DROP POLICY IF EXISTS client_projects_access ON client_projects;")
    op.execute("""
        CREATE POLICY client_projects_access ON client_projects
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = client_projects.client_id
            )
            OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID
                AND client_projects.active = true
            )
        );
    """)
    
    # Step 9: Ensure RLS is enabled on all relevant tables
    rls_tables = [
        'samples', 'tests', 'results', 'projects', 
        'batches', 'containers', 'client_projects'
    ]
    
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    # Restore previous version of has_project_access function (from 0024)
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
    
    # Restore previous policies (from 0024 and 0022)
    op.execute("DROP POLICY IF EXISTS projects_access ON projects;")
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() OR has_project_access(id)
            OR EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id()
                AND r.name = 'Client'
                AND u.client_id IS NOT NULL
                AND projects.client_id = u.client_id
            )
            OR EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id()
                AND r.name IN ('Lab Technician', 'Lab Manager')
                AND projects.active = true
            )
        );
    """)
    
    # Restore client_projects_access policy (from 0022)
    op.execute("DROP POLICY IF EXISTS client_projects_access ON client_projects;")
    op.execute("""
        CREATE POLICY client_projects_access ON client_projects
        FOR ALL
        USING (
            is_admin() 
            OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = client_projects.client_id
            )
            OR EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id()
                AND r.name IN ('Lab Technician', 'Lab Manager')
                AND client_projects.active = true
            )
        );
    """)
    
    # Note: Other policies (samples, tests, results, batches, containers) remain the same
    # as they already use has_project_access, which will work with the downgraded function
