"""Fix client_projects RLS to allow lab technicians and managers

Revision ID: 0022
Revises: 0021
Create Date: 2026-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing policy
    op.execute("DROP POLICY IF EXISTS client_projects_access ON client_projects;")
    
    # Recreate policy to allow:
    # 1. Admins (all client projects)
    # 2. Client users (client projects matching their client_id)
    # 3. Lab Technicians and Lab Managers (all active client projects for sample creation)
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


def downgrade() -> None:
    # Drop the updated policy
    op.execute("DROP POLICY IF EXISTS client_projects_access ON client_projects;")
    
    # Restore original policy (admins and client users only)
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

