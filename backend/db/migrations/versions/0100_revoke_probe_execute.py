"""Revoke the migration role's EXECUTE on batch_access_status.

Revision ID: 0100_revoke_probe_execute
Revises: 0099_batch_update_qualifiers

0098 creates ``public.batch_access_status(uuid)`` and sets the owner to the
migration role (the database owner). PostgreSQL records that owner's EXECUTE
in ``proacl`` when EXECUTE is revoked from PUBLIC, so the function ACL shows
a grant to the owner next to ``lims_app``.

That grant is not ``ALTER DEFAULT PRIVILEGES``. Nothing in this repository
sets a default EXECUTE on future functions. ``0003_rls_policies`` does
``GRANT EXECUTE ON ALL FUNCTIONS`` to the migration role, but that statement
runs before this function exists and does not cover functions created later.
``ensure_lims_app_role.py`` grants EXECUTE on all functions to ``lims_app``
only. It now also repeats this revoke after migrations, so a later recreate
does not leave the migration role's EXECUTE in place. ``CREATE OR REPLACE``
keeps the privilege list, so it does not put the grant back. ``0098`` also
revokes the owner at creation time.

This revision only revokes. It does not grant.
"""
from alembic import op

revision = "0100_revoke_probe_execute"
down_revision = "0099_batch_update_qualifiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM PUBLIC;
        REVOKE EXECUTE ON FUNCTION public.batch_access_status(uuid) FROM lims_user; -- pragma: allowlist secret
        """
    )
    # No default privilege grants EXECUTE on functions to the migration role.
    # Revoke anyway so one added by hand cannot attach to a recreated function.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_user' -- pragma: allowlist secret
            ) THEN
                EXECUTE $sql$
                    ALTER DEFAULT PRIVILEGES FOR ROLE lims_user IN SCHEMA public -- pragma: allowlist secret
                    REVOKE EXECUTE ON FUNCTIONS FROM lims_user -- pragma: allowlist secret
                $sql$;
                EXECUTE $sql$
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE EXECUTE ON FUNCTIONS FROM lims_user -- pragma: allowlist secret
                $sql$;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # No-op. Do not grant EXECUTE back to the migration role.
    pass
