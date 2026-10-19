"""Move app-object ownership to the non-superuser migration role.

Revision ID: 0103_migration_role_owner
Revises: 0102_instant_timestamptz

``lims_migrate`` owns the application objects and is the role that runs
Alembic. It is not a superuser. It is created with ``LOGIN``. An existing
``NOLOGIN`` role is altered to ``LOGIN``. It has ``BYPASSRLS`` because it owns
``SECURITY DEFINER`` functions (including ``batch_access_status``) and
because migration seeds write tables that have ``FORCE ROW LEVEL SECURITY``.
A table owner does not bypass forced row security.

``lims_app`` stays the only runtime role: ``NOSUPERUSER`` and
``NOBYPASSRLS``. ``lims_user`` remains only so earlier grants still have a  # pragma: allowlist secret
target. It is not the migration role. ``EXECUTE`` on
``batch_access_status(uuid)`` is revoked from ``lims_migrate`` and from
``lims_user`` when that role exists. Nothing is dropped.  # pragma: allowlist secret

``ALTER DATABASE`` cannot run inside a function or a transaction block, so
that statement is issued on its own, and only when the actor is a superuser.
A clean volume already creates objects as ``lims_migrate``, so the ownership
loop is a no-op there.

This revision follows ``0102_instant_timestamptz`` (merged in #191) so
Alembic has a single head.

Downgrade does not move ownership back and does not grant ``EXECUTE`` again.
"""
from alembic import op
from sqlalchemy import text

revision = "0103_migration_role_owner"
down_revision = "0102_instant_timestamptz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Commit the role before ALTER DATABASE. The rest of this revision runs
    # in the transaction Alembic opens after the autocommit block.
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            DECLARE
                actor_super boolean;
            BEGIN
                SELECT rolsuper INTO actor_super
                  FROM pg_catalog.pg_roles
                 WHERE rolname = current_user;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_migrate'
                ) THEN
                    IF actor_super IS NOT TRUE THEN
                        RAISE EXCEPTION
                            'lims_migrate must be created by the bootstrap superuser before migrations';
                    END IF;
                    CREATE ROLE lims_migrate
                        NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN BYPASSRLS;
                ELSIF actor_super IS TRUE THEN
                    ALTER ROLE lims_migrate NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN BYPASSRLS;
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                      FROM pg_catalog.pg_roles
                     WHERE rolname = 'lims_migrate'
                       AND rolsuper IS FALSE
                       AND rolbypassrls IS TRUE
                ) THEN
                    RAISE EXCEPTION
                        'lims_migrate must be NOSUPERUSER and BYPASSRLS';
                END IF;
            END $$;
            """
        )
        actor_super = op.get_bind().execute(
            text(
                """
                SELECT rolsuper
                  FROM pg_catalog.pg_roles
                 WHERE rolname = current_user
                """
            )
        ).scalar()
        if actor_super:
            dbname = op.get_bind().execute(text("SELECT current_database()")).scalar()
            if not str(dbname).replace("_", "").isalnum():
                raise RuntimeError("refusing to alter an unexpected database name")
            op.execute(f"ALTER DATABASE {dbname} OWNER TO lims_migrate")

    op.execute(
        """
        DO $$
        DECLARE
            actor_super boolean;
            rec record;
        BEGIN
            SELECT rolsuper INTO actor_super
              FROM pg_catalog.pg_roles
             WHERE rolname = current_user;
            IF actor_super IS NOT TRUE THEN
                RETURN;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'public') THEN
                ALTER SCHEMA public OWNER TO lims_migrate;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'lims') THEN
                ALTER SCHEMA lims OWNER TO lims_migrate;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app') THEN
                ALTER ROLE lims_app NOSUPERUSER NOBYPASSRLS;
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM pg_catalog.pg_roles
                 WHERE rolname = 'lims_user'  -- pragma: allowlist secret
                   AND rolsuper IS FALSE
            ) THEN
                ALTER ROLE lims_user NOSUPERUSER NOBYPASSRLS;  -- pragma: allowlist secret
            END IF;

            FOR rec IN
                SELECT n.nspname, c.relname, c.relkind
                  FROM pg_class c
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname IN ('public', 'lims')
                   AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                   AND c.relowner = (
                       SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user
                   )
                   AND NOT EXISTS (
                       SELECT 1
                         FROM pg_depend d
                        WHERE d.classid = 'pg_class'::regclass
                          AND d.objid = c.oid
                          AND d.deptype = 'e'
                   )
                   AND NOT (
                       c.relkind = 'S'
                       AND EXISTS (
                           SELECT 1
                             FROM pg_depend d
                            WHERE d.classid = 'pg_class'::regclass
                              AND d.objid = c.oid
                              AND d.deptype IN ('a', 'i')
                       )
                   )
            LOOP
                IF rec.relkind = 'S' THEN
                    EXECUTE format(
                        'ALTER SEQUENCE %I.%I OWNER TO lims_migrate',
                        rec.nspname, rec.relname
                    );
                ELSIF rec.relkind = 'v' THEN
                    EXECUTE format(
                        'ALTER VIEW %I.%I OWNER TO lims_migrate',
                        rec.nspname, rec.relname
                    );
                ELSIF rec.relkind = 'm' THEN
                    EXECUTE format(
                        'ALTER MATERIALIZED VIEW %I.%I OWNER TO lims_migrate',
                        rec.nspname, rec.relname
                    );
                ELSIF rec.relkind = 'f' THEN
                    EXECUTE format(
                        'ALTER FOREIGN TABLE %I.%I OWNER TO lims_migrate',
                        rec.nspname, rec.relname
                    );
                ELSE
                    EXECUTE format(
                        'ALTER TABLE %I.%I OWNER TO lims_migrate',
                        rec.nspname, rec.relname
                    );
                END IF;
            END LOOP;

            FOR rec IN
                SELECT n.nspname,
                       p.proname,
                       pg_get_function_identity_arguments(p.oid) AS args
                  FROM pg_proc p
                  JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname IN ('public', 'lims')
                   AND p.prokind = 'f'
                   AND p.proowner = (
                       SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user
                   )
                   AND NOT EXISTS (
                       SELECT 1
                         FROM pg_depend d
                        WHERE d.classid = 'pg_proc'::regclass
                          AND d.objid = p.oid
                          AND d.deptype = 'e'
                   )
            LOOP
                EXECUTE format(
                    'ALTER FUNCTION %I.%I(%s) OWNER TO lims_migrate',
                    rec.nspname, rec.proname, rec.args
                );
            END LOOP;

            FOR rec IN
                SELECT n.nspname, t.typname
                  FROM pg_type t
                  JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE n.nspname IN ('public', 'lims')
                   AND t.typtype IN ('e', 'd')
                   AND t.typowner = (
                       SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user
                   )
                   AND NOT EXISTS (
                       SELECT 1
                         FROM pg_depend d
                        WHERE d.classid = 'pg_type'::regclass
                          AND d.objid = t.oid
                          AND d.deptype = 'e'
                   )
            LOOP
                EXECUTE format(
                    'ALTER TYPE %I.%I OWNER TO lims_migrate',
                    rec.nspname, rec.typname
                );
            END LOOP;

            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE
                    'ALTER DEFAULT PRIVILEGES FOR ROLE lims_migrate IN SCHEMA public '
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lims_app';
                EXECUTE
                    'ALTER DEFAULT PRIVILEGES FOR ROLE lims_migrate IN SCHEMA public '
                    'GRANT USAGE, SELECT ON SEQUENCES TO lims_app';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF current_user = 'lims_migrate'
               AND EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lims_app';
                EXECUTE
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                    'GRANT USAGE, SELECT ON SEQUENCES TO lims_app';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM pg_catalog.pg_roles
                 WHERE rolname = 'lims_app'
                   AND (rolsuper OR rolbypassrls)
            ) THEN
                RAISE EXCEPTION
                    'lims_app must be NOSUPERUSER and NOBYPASSRLS';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM PUBLIC;
        REVOKE EXECUTE ON FUNCTION public.batch_access_status(uuid) FROM lims_migrate;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_user') THEN  -- pragma: allowlist secret
                EXECUTE 'REVOKE EXECUTE ON FUNCTION public.batch_access_status(uuid) FROM lims_user';  -- pragma: allowlist secret
            END IF;
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE 'GRANT EXECUTE ON FUNCTION public.batch_access_status(uuid) TO lims_app';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # No-op. Do not move ownership back and do not grant EXECUTE again.
    pass
