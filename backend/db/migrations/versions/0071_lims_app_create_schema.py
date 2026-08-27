"""Allow lims_app to CREATE SEQUENCE for name templates.

Revision ID: 0071
Revises: 0070
Create Date: 2026-08-27

Atomic receive / name generation uses CREATE SEQUENCE IF NOT EXISTS at runtime.
Without CREATE on schema public, that aborts the receive transaction.
"""

from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT USAGE, CREATE ON SCHEMA public TO lims_app;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lims_app;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT USAGE, SELECT ON SEQUENCES TO lims_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                REVOKE CREATE ON SCHEMA public FROM lims_app;
            END IF;
        END $$;
        """
    )
