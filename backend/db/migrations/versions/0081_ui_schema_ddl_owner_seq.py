"""A+B UAT Fail: DDL function owner = samples owner; seq identity.

Revision ID: 0081
Revises: 0080
Create Date: 2026-09-24

A: ui_schema_ddl_log.seq is IDENTITY (already 0080); ORM must not insert NULL.
B: SECURITY DEFINER functions owned by schema_apply cannot ALTER samples
   (owned by migrator). Re-own functions to the samples table owner so
   ADD COLUMN / DROP on samples and CREATE TABLE (same owner) work.
"""

from alembic import op

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None

FUNCS = (
    "ui_schema_ensure_sequence(text)",
    "ui_schema_create_table(text)",
    "ui_schema_add_column(text,text,text,boolean,boolean)",
    "ui_schema_drop_column(text,text)",
    "ui_schema_drop_table(text)",
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            owner_name text;
            fn text;
        BEGIN
            SELECT pg_get_userbyid(c.relowner)
              INTO owner_name
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relname = 'samples';

            IF owner_name IS NULL THEN
                RAISE EXCEPTION 'samples owner not found';
            END IF;

            FOREACH fn IN ARRAY ARRAY[
                'ui_schema_ensure_sequence(text)',
                'ui_schema_create_table(text)',
                'ui_schema_add_column(text,text,text,boolean,boolean)',
                'ui_schema_drop_column(text,text)',
                'ui_schema_drop_table(text)'
            ]
            LOOP
                EXECUTE format('ALTER FUNCTION %s OWNER TO %I', fn, owner_name);
                EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', fn);
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO lims_app', fn);
                END IF;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    for fn in FUNCS:
        op.execute(f"ALTER FUNCTION {fn} OWNER TO schema_apply")
