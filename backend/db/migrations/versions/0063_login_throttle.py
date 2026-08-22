"""S15: login_throttle table for failed-login lockout.

Revision ID: 0063
Revises: 0062
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_throttle",
        sa.Column("username_normalized", sa.String(255), primary_key=True, nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_login_throttle_locked_until",
        "login_throttle",
        ["locked_until"],
    )
    # App role needs access (ensure_lims_app_role also grants ALL TABLES; this is belt)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON login_throttle TO lims_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_login_throttle_locked_until", table_name="login_throttle")
    op.drop_table("login_throttle")
