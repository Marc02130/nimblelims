"""P2 UAT: lab catalog visibility + experiment:publish seed.

Revision ID: 0074
Revises: 0073
Create Date: 2026-08-29

AC-P2-4 Fail: alice (NovaBio Lab Technician) could not see admin-created
process definitions because 0051 scoped defs/steps to created_by.client_id.
Process definitions are lab SOP catalog (like analyses), not tenant rows.
Lab roles with has_experiment_access() must read them; Client still cannot.

AC-P2-5: experiment:publish was in CORE_PERMISSIONS but never seeded.
Assign to Administrator and Lab Manager (same seat as result:review).
Lab Technician does not publish.
"""

from alembic import op
import sqlalchemy as sa

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

_CATALOG_POLICY = """\
    is_admin() OR has_experiment_access()\
"""

_CLIENT_POLICY = """\
    is_admin() OR (
        has_experiment_access() AND
        created_by IN (
            SELECT u.id FROM users u
            WHERE u.client_id = (
                SELECT u2.client_id FROM users u2
                WHERE u2.id = current_user_id()
            )
        )
    )\
"""


def upgrade() -> None:
    for table in ("eln_process_definitions", "eln_process_definition_steps"):
        op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING ({_CATALOG_POLICY})
            WITH CHECK ({_CATALOG_POLICY})
            """
        )

    op.execute(
        """
        INSERT INTO permissions (id, name, description, active, created_at, modified_at)
        VALUES (
            gen_random_uuid(),
            'experiment:publish',
            'Publish a LimsRun (complete → published)',
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (name) DO NOTHING
        """
    )
    connection = op.get_bind()
    for role_name in ("Administrator", "Lab Manager"):
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = 'experiment:publish'
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_name": role_name},
        )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
            SELECT id FROM permissions WHERE name = 'experiment:publish'
        )
        """
    )
    op.execute("DELETE FROM permissions WHERE name = 'experiment:publish'")

    for table in ("eln_process_definitions", "eln_process_definition_steps"):
        op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING ({_CLIENT_POLICY})
            """
        )
