"""Seed a Configuration Editor persona for the L-2 two-user test.

Revision ID: 0088_seed_config_editor
Revises: 0087_agent_step_states

Role "Configuration Editor" holds config:edit plus the read permissions the
Configuring agent screens need, and NOT schema:edit / layout:edit / role:manage /
user:manage. User 'config-editor' is in it. Its password is the locked marker
(login fails) until ``python seed_dev_passwords.py --apply`` sets
DEV_SEED_CONFIG_EDITOR_PASSWORD, like every other seed persona.
"""

import sqlalchemy as sa
from alembic import op

revision = "0088_seed_config_editor"
down_revision = "0087_agent_step_states"
branch_labels = None
depends_on = None

ROLE_ID = "abababab-abab-abab-abab-abababababab"
USER_ID = "00000000-0000-0000-0000-000000000010"
CLIENT_ID = "00000000-0000-0000-0000-000000000001"
PERMISSIONS = (
    "config:edit",
    "sample:read",
    "test:read",
    "result:read",
    "project:read",
    "batch:read",
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (id, name, description, active, created_at, modified_at)
            VALUES (:id, 'Configuration Editor',
                    'config:edit without schema:edit (Configuring agent L-2 test)',
                    true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": ROLE_ID},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT :role_id, p.id FROM permissions p WHERE p.name = ANY(:names)
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ),
        {"role_id": ROLE_ID, "names": list(PERMISSIONS)},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, name, username, email, password_hash, role_id,
                               client_id, active, created_at, modified_at)
            VALUES (:id, 'Configuration Editor', 'config-editor',
                    'config-editor@lims.example.com', '!seed-locked', :role_id,
                    :client_id, true, NOW(), NOW())
            ON CONFLICT (username) DO NOTHING
            """
        ),
        {"id": USER_ID, "role_id": ROLE_ID, "client_id": CLIENT_ID},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": USER_ID})
    conn.execute(sa.text("DELETE FROM role_permissions WHERE role_id = :id"), {"id": ROLE_ID})
    conn.execute(sa.text("DELETE FROM roles WHERE id = :id"), {"id": ROLE_ID})
