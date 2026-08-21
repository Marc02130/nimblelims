"""Sec9: allow container INSERT for non-admins via created_by.

Revision ID: 0062
Revises: 0061
Create Date: 2026-08-21

containers_access previously required an existing contents→sample project link
for ALL commands (USING only). New empty containers (aliquot dest) have no
contents yet, so Lab Technician INSERT failed under RLS (500). Admins passed
via is_admin().

Fix: USING/WITH CHECK also allow created_by = current_user_id().
"""
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS containers_access ON containers;")
    op.execute(
        """
        CREATE POLICY containers_access ON containers
        FOR ALL
        USING (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1 FROM contents c
                JOIN samples s ON c.sample_id = s.id
                WHERE c.container_id = containers.id
                AND has_project_access(s.project_id)
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS containers_access ON containers;")
    op.execute(
        """
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
        """
    )
