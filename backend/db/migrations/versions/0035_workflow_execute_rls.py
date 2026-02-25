"""Extend RLS for workflow:execute permission

Revision ID: 0035
Revises: 0034
Create Date: 2026-02-24

Adds has_workflow_execute() and updates workflow_instances RLS policy
so that users with workflow:execute permission can INSERT and access
instances (in addition to is_admin and created_by).
"""
from alembic import op

revision = '0035'
down_revision = '0034'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Function: true if current user's role has workflow:execute permission
    op.execute("""
        CREATE OR REPLACE FUNCTION has_workflow_execute()
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS (
                SELECT 1
                FROM users u
                JOIN role_permissions rp ON rp.role_id = u.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE u.id = current_user_id()
                AND p.name = 'workflow:execute'
                AND p.active = true
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Extend workflow_instances policy: allow access if admin, creator, or has workflow:execute
    op.execute("DROP POLICY IF EXISTS workflow_instances_access ON workflow_instances;")
    op.execute("""
        CREATE POLICY workflow_instances_access ON workflow_instances
        FOR ALL
        USING (
            is_admin()
            OR created_by = current_user_id()
            OR has_workflow_execute()
        );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workflow_instances_access ON workflow_instances;")
    op.execute("""
        CREATE POLICY workflow_instances_access ON workflow_instances
        FOR ALL
        USING (
            is_admin() OR created_by = current_user_id()
        );
    """)
    op.execute("DROP FUNCTION IF EXISTS has_workflow_execute();")
