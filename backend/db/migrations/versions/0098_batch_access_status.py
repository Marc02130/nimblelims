"""Probe whether the session may see a batch, without returning the owner.

Revision ID: 0098_batch_access_status
Revises: 0097_list_entry_code

``batches`` is FORCE ROW LEVEL SECURITY, so ``lims_app`` cannot tell a missing
batch from one that belongs to another client. This function runs as the
migration role, which must bypass row security, and returns only
``not_found``, ``forbidden``, or ``visible``. It reads ``app.current_user_id``
the same way ``current_user_id()`` does. It does not take a client id and it
does not return one.

Visibility matches ``batches_access``: an administrator, or a sample in the
batch whose project passes ``has_project_access``. An inactive row is
``not_found``, same as the routes that filter ``active``.

``EXECUTE`` is revoked from ``PUBLIC`` and from the function owner. It is
granted only to ``lims_app``. Revoking ``PUBLIC`` is what writes the owner's
privilege into the function ACL; this block removes that entry at creation
so recreating the function does not leave it behind.
"""
from alembic import op

revision = "0098_batch_access_status"
down_revision = "0097_list_entry_code"
branch_labels = None
depends_on = None

CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION public.batch_access_status(p_batch_id uuid)
RETURNS text
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    batch_exists boolean;
    caller_can_see boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM public.batches AS b
        WHERE b.id = p_batch_id
          AND b.active IS TRUE
    ) INTO batch_exists;

    IF NOT batch_exists THEN
        RETURN 'not_found';
    END IF;

    SELECT (
        public.is_admin()
        OR EXISTS (
            SELECT 1
            FROM public.batch_containers AS bc
            JOIN public.containers AS c ON bc.container_id = c.id
            JOIN public.contents AS ct ON c.id = ct.container_id
            JOIN public.samples AS s ON ct.sample_id = s.id
            WHERE bc.batch_id = p_batch_id
              AND public.has_project_access(s.project_id)
        )
    ) INTO caller_can_see;

    IF caller_can_see THEN
        RETURN 'visible';
    END IF;
    RETURN 'forbidden';
END;
$$;
"""


def upgrade() -> None:
    op.execute(CREATE_FUNCTION)
    op.execute(
        """
        DO $$
        DECLARE
            owner_name text := current_user;
            bypass boolean;
        BEGIN
            SELECT rolsuper OR rolbypassrls
              INTO bypass
              FROM pg_catalog.pg_roles
             WHERE rolname = owner_name;
            IF bypass IS NOT TRUE THEN
                RAISE EXCEPTION
                    'batch_access_status owner % must bypass row security',
                    owner_name;
            END IF;
            EXECUTE format(
                'ALTER FUNCTION public.batch_access_status(uuid) OWNER TO %I',
                owner_name
            );
            EXECUTE 'REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM PUBLIC';
            EXECUTE format(
                'REVOKE EXECUTE ON FUNCTION public.batch_access_status(uuid) FROM %I',
                owner_name
            );
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE 'GRANT EXECUTE ON FUNCTION public.batch_access_status(uuid) TO lims_app';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.batch_access_status(uuid)")
