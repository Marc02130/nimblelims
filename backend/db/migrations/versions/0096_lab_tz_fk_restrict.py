"""Make lab_settings.modified_by ON DELETE RESTRICT.

Revision ID: 0096_lab_tz_fk_restrict
Revises: 0095_lab_settings

0095 already shipped with Postgres's default NO ACTION. Identity foreign keys
in this database are RESTRICT. This replaces only that one constraint.
The revision id stays within alembic_version.version_num (varchar 32).
"""

from alembic import op

revision = "0096_lab_tz_fk_restrict"
down_revision = "0095_lab_settings"
branch_labels = None
depends_on = None

CONSTRAINT = "lab_settings_modified_by_fkey"


def upgrade() -> None:
    op.execute(f"ALTER TABLE lab_settings DROP CONSTRAINT IF EXISTS {CONSTRAINT}")
    op.execute(
        f"ALTER TABLE lab_settings ADD CONSTRAINT {CONSTRAINT} "
        "FOREIGN KEY (modified_by) REFERENCES users(id) ON DELETE RESTRICT"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE lab_settings DROP CONSTRAINT IF EXISTS {CONSTRAINT}")
    op.execute(
        f"ALTER TABLE lab_settings ADD CONSTRAINT {CONSTRAINT} "
        "FOREIGN KEY (modified_by) REFERENCES users(id)"
    )
