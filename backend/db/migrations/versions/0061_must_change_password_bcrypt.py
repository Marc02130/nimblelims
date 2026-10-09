"""P0b security: must_change_password on the original persona seeds.

Revision ID: 0061
Revises: 0060
Create Date: 2026-08-20

- ADD users.must_change_password
- Mark admin, lab-manager, lab-tech, and client must_change_password=true

The legacy SHA256 → bcrypt rehash loop was removed. Fresh databases insert
``!seed-locked`` (see 0004, 0013, and 0058), which is neither bcrypt nor
64-hex, so there is no published digest left to match. Databases that
already applied an older 0061 keep their bcrypt hashes; this file does not
re-run. A leftover 64-hex hash still upgrades on the next successful login
in ``verify_password`` / ``needs_rehash``. Set a real password with
``python seed_dev_passwords.py --apply`` (env var, or printed once).
"""
from alembic import op
import sqlalchemy as sa

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

# Well-known persona seeds (dev/demo/UAT). Passwords are not stored here.
SEED_USERNAMES = (
    "admin",
    "lab-manager",
    "lab-tech",
    "client",
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    connection = op.get_bind()

    # Persona seeds must change password on first login (Q2/Q7).
    # A fresh database still cannot log in: the hash is the locked marker
    # until seed_dev_passwords.py --apply replaces it.
    connection.execute(
        sa.text(
            """
            UPDATE users
            SET must_change_password = true
            WHERE username IN ('admin', 'lab-manager', 'lab-tech', 'client')
            """
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
