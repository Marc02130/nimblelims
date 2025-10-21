"""Add Row Level Security policies

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-01 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on key tables
    rls_tables = [
        'samples', 'tests', 'results', 'projects', 'batches', 'containers'
    ]
    
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    
    # Create function to get current user ID
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN COALESCE(
                current_setting('app.current_user_id', true)::UUID,
                '00000000-0000-0000-0000-000000000000'::UUID
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create function to check if user is admin
    op.execute("""
        CREATE OR REPLACE FUNCTION is_admin()
        RETURNS BOOLEAN AS $$
        DECLARE
            user_role_name TEXT;
        BEGIN
            SELECT r.name INTO user_role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = current_user_id();
            
            RETURN user_role_name = 'Administrator';
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create function to check if user has access to project
    op.execute("""
        CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
        RETURNS BOOLEAN AS $$
        BEGIN
            -- Admin users can access all projects
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Check if user has direct access to project
            RETURN EXISTS (
                SELECT 1 FROM project_users pu
                WHERE pu.project_id = project_uuid
                AND pu.user_id = current_user_id()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Samples RLS policy
    op.execute("""
        CREATE POLICY samples_access ON samples
        FOR ALL
        USING (
            is_admin() OR has_project_access(project_id)
        );
    """)
    
    # Tests RLS policy
    op.execute("""
        CREATE POLICY tests_access ON tests
        FOR ALL
        USING (
            is_admin() OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = tests.sample_id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Results RLS policy
    op.execute("""
        CREATE POLICY results_access ON results
        FOR ALL
        USING (
            is_admin() OR EXISTS (
                SELECT 1 FROM tests t
                JOIN samples s ON t.sample_id = s.id
                WHERE t.id = results.test_id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Projects RLS policy
    op.execute("""
        CREATE POLICY projects_access ON projects
        FOR ALL
        USING (
            is_admin() OR has_project_access(id)
        );
    """)
    
    # Batches RLS policy
    op.execute("""
        CREATE POLICY batches_access ON batches
        FOR ALL
        USING (
            is_admin() OR EXISTS (
                SELECT 1 FROM batch_containers bc
                JOIN containers c ON bc.container_id = c.id
                JOIN contents ct ON c.id = ct.container_id
                JOIN samples s ON ct.sample_id = s.id
                WHERE bc.batch_id = batches.id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Containers RLS policy
    op.execute("""
        CREATE POLICY containers_access ON containers
        FOR ALL
        USING (
            is_admin() OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
    """)
    
    # Grant necessary permissions
    op.execute("""
        GRANT USAGE ON SCHEMA public TO lims_user;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lims_user;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lims_user;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO lims_user;
    """)


def downgrade() -> None:
    # Drop RLS policies
    policies = [
        'samples_access', 'tests_access', 'results_access', 
        'projects_access', 'batches_access', 'containers_access'
    ]
    
    for policy in policies:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {policy.split('_')[0]};")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS current_user_id();")
    op.execute("DROP FUNCTION IF EXISTS is_admin();")
    op.execute("DROP FUNCTION IF EXISTS has_project_access(UUID);")
    
    # Disable RLS
    rls_tables = [
        'samples', 'tests', 'results', 'projects', 'batches', 'containers'
    ]
    
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
