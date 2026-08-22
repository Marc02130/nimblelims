"""S7 UAT hold: lab staff require project_users (no same-client short-circuit).

Revision ID: 0065
Revises: 0064
Create Date: 2026-08-21

TC-S7-001: alice-tech (NovaBio, not on project_users for CAR-T) must not
GET/start/link Bob's sample. Root cause: has_project_access returned TRUE on
project.client_id = user.client_id before checking project_users.

New rules:
- Admin / System-client users: unchanged (full access)
- Role Client: keep client_projects + same-client project.client_id
- Lab Technician / Lab Manager (and other non-Client): project_users only
"""
from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


NEW_FUNCTION = """
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_client_project_id UUID;
    project_client_id UUID;
    user_client_id UUID;
    user_role TEXT;
    system_client_id UUID;
BEGIN
    IF is_admin() THEN
        RETURN TRUE;
    END IF;

    system_client_id := '00000000-0000-0000-0000-000000000001'::UUID;

    SELECT u.client_id, r.name
      INTO user_client_id, user_role
      FROM users u
      JOIN roles r ON r.id = u.role_id
     WHERE u.id = current_user_id();

    -- Org-wide lab employees on System client
    IF user_client_id = system_client_id THEN
        RETURN TRUE;
    END IF;

    SELECT p.client_project_id, p.client_id
      INTO project_client_project_id, project_client_id
      FROM projects p
     WHERE p.id = project_uuid;

    -- Client-role portal: tenant isolation via client_projects / same client
    IF user_role = 'Client' THEN
        IF project_client_project_id IS NOT NULL AND user_client_id IS NOT NULL THEN
            IF EXISTS (
                SELECT 1 FROM client_projects cp
                WHERE cp.id = project_client_project_id
                  AND cp.client_id = user_client_id
            ) THEN
                RETURN TRUE;
            END IF;
        END IF;

        IF project_client_id IS NOT NULL AND user_client_id IS NOT NULL THEN
            IF project_client_id = user_client_id THEN
                RETURN TRUE;
            END IF;
        END IF;

        RETURN EXISTS (
            SELECT 1 FROM project_users pu
            WHERE pu.project_id = project_uuid
              AND pu.user_id = current_user_id()
        );
    END IF;

    -- Lab Technician / Lab Manager / other: assignment via project_users only
    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
          AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

# Previous body from 0029 (downgrade)
OLD_FUNCTION = """
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_client_project_id UUID;
    project_client_id UUID;
    user_client_id UUID;
    system_client_id UUID;
BEGIN
    IF is_admin() THEN
        RETURN TRUE;
    END IF;

    system_client_id := '00000000-0000-0000-0000-000000000001'::UUID;

    SELECT u.client_id INTO user_client_id
    FROM users u
    WHERE u.id = current_user_id();

    IF user_client_id = system_client_id THEN
        RETURN TRUE;
    END IF;

    SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
    FROM projects p
    WHERE p.id = project_uuid;

    IF project_client_project_id IS NOT NULL THEN
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

    IF project_client_id IS NOT NULL AND user_client_id IS NOT NULL THEN
        IF project_client_id = user_client_id THEN
            RETURN TRUE;
        END IF;
    END IF;

    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
        AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""


def upgrade() -> None:
    op.execute(NEW_FUNCTION)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT EXECUTE ON FUNCTION has_project_access(UUID) TO lims_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(OLD_FUNCTION)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT EXECUTE ON FUNCTION has_project_access(UUID) TO lims_app;
            END IF;
        END $$;
        """
    )
