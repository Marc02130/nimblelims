"""Revoke the migration role's EXECUTE on batch_access_status.

Revision ID: 0101_revoke_probe_execute
Revises: 0100_calendar_dates

0098 creates ``public.batch_access_status(uuid)`` and sets the owner to the
migration role (the database owner). That role stays the owner. PostgreSQL
records the owner's EXECUTE in ``proacl`` when EXECUTE is revoked from
PUBLIC, so the function ACL shows a grant to the owner next to ``lims_app``.

That grant is not ``ALTER DEFAULT PRIVILEGES``. Nothing in this repository
sets a default EXECUTE on future functions. ``0003_rls_policies`` does
``GRANT EXECUTE ON ALL FUNCTIONS`` to the migration role, but that statement
runs before this function exists and does not cover functions created later.
``ensure_lims_app_role.py`` grants EXECUTE on all functions to ``lims_app``
only. It also repeats this revoke after migrations, so a later recreate does
not leave the migration role's EXECUTE in place. ``CREATE OR REPLACE`` keeps
the privilege list, so it does not put the grant back.

This revision only revokes EXECUTE from the migration role and from PUBLIC.
It does not grant, and it does not change the owner.
"""
from alembic import op

revision = "0101_revoke_probe_execute"
down_revision = "0100_calendar_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM PUBLIC;
        REVOKE EXECUTE ON FUNCTION public.batch_access_status(uuid) FROM lims_user; -- pragma: allowlist secret
        """
    )


def downgrade() -> None:
    # No-op. Do not grant EXECUTE back to the migration role.
    pass
