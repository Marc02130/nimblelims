"""Add client projects to LIMS schema

Revision ID: 0010
Revises: 0009
Create Date: 2025-12-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create client_projects table
    op.create_table('client_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Add client_project_id column to projects table
    op.add_column('projects', 
        sa.Column('client_project_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'projects_client_project_id_fkey',
        'projects', 'client_projects',
        ['client_project_id'], ['id']
    )
    
    # Add client_sample_id column to samples table
    op.add_column('samples',
        sa.Column('client_sample_id', sa.String(255), nullable=True)
    )
    
    # Create indexes
    # Index on client_projects.client_id for efficient lookups
    op.create_index('idx_client_projects_client_id', 'client_projects', ['client_id'])
    
    # Index on projects.client_project_id for efficient lookups
    op.create_index('idx_projects_client_project_id', 'projects', ['client_project_id'])
    
    # Unique index on samples.client_sample_id (unique nullable)
    op.create_index('idx_samples_client_sample_id', 'samples', ['client_sample_id'], unique=True)
    
    # Update has_project_access function to check via client_projects if client_project_id is set
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
    
    # Enable RLS on client_projects table
    op.execute("ALTER TABLE client_projects ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policy for client_projects
    op.execute("""
        CREATE POLICY client_projects_access ON client_projects
        FOR ALL
        USING (
            is_admin() OR EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id()
                AND u.client_id = client_projects.client_id
            )
        );
    """)


def downgrade() -> None:
    # Drop RLS policy for client_projects
    op.execute("DROP POLICY IF EXISTS client_projects_access ON client_projects;")
    
    # Disable RLS on client_projects
    op.execute("ALTER TABLE client_projects DISABLE ROW LEVEL SECURITY;")
    
    # Restore original has_project_access function
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
    
    # Drop indexes
    op.drop_index('idx_samples_client_sample_id', table_name='samples')
    op.drop_index('idx_projects_client_project_id', table_name='projects')
    op.drop_index('idx_client_projects_client_id', table_name='client_projects')
    
    # Drop columns
    op.drop_column('samples', 'client_sample_id')
    op.drop_constraint('projects_client_project_id_fkey', 'projects', type_='foreignkey')
    op.drop_column('projects', 'client_project_id')
    
    # Drop table
    op.drop_table('client_projects')

