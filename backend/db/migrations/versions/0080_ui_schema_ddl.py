"""UI schema DDL registries, schema:edit, schema_apply functions.

Revision ID: 0080
Revises: 0079
Create Date: 2026-09-23

Hybrid apply (Brief OQ-4): lims_app loses CREATE on public. Physical DDL
runs via SECURITY DEFINER functions owned by schema_apply. Registries are
tenant-scoped with FORCE RLS (OQ-5). schema:edit / layout:edit on Admin only.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None

SYSTEM_CLIENT_ID = "00000000-0000-0000-0000-000000000001"

REGISTRY_TABLES = (
    "schema_tables",
    "schema_columns",
    "schema_layouts",
    "schema_layout_fields",
    "schema_privileges",
    "schema_changes",
    "ui_schema_ddl_log",
)


def _client_rls(table: str) -> str:
    return f"""
        ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
        CREATE POLICY {table}_access ON {table} FOR ALL
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM users current_user_row
                WHERE current_user_row.id = current_user_id()
                  AND (
                    current_user_row.client_id = '{SYSTEM_CLIENT_ID}'::uuid
                    OR current_user_row.client_id = {table}.client_id
                  )
            )
        )
        WITH CHECK (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM users current_user_row
                WHERE current_user_row.id = current_user_id()
                  AND (
                    current_user_row.client_id = '{SYSTEM_CLIENT_ID}'::uuid
                    OR current_user_row.client_id = {table}.client_id
                  )
            )
        );
        ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
    """


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'schema_apply') THEN
                CREATE ROLE schema_apply NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
            END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE, CREATE ON SCHEMA public TO schema_apply")
    # REFERENCES only — schema_apply must not SELECT lab rows (Brief OQ-4).
    op.execute("GRANT REFERENCES ON TABLE clients, users, list_entries TO schema_apply")

    connection = op.get_bind()
    for name, desc in (
        ("schema:edit", "CREATE/ALTER schema registries and physical DDL"),
        ("layout:edit", "Edit role × screen layout membership (no DDL)"),
    ):
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, name, description, active, created_at, modified_at)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": name, "description": desc},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = 'Administrator' AND p.name = :name
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"name": name},
        )

    op.create_table(
        "schema_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("physical_name", sa.String(63), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.CheckConstraint("kind IN ('core', 'ui')", name="schema_tables_kind_chk"),
        sa.CheckConstraint("status IN ('active', 'deprecated')", name="schema_tables_status_chk"),
        sa.UniqueConstraint("client_id", "physical_name", name="uq_schema_tables_client_physical"),
    )
    op.create_index("ix_schema_tables_client", "schema_tables", ["client_id"])

    op.create_table(
        "schema_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_tables.id"), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("physical_name", sa.String(63), nullable=False),
        sa.Column("data_type", sa.String(32), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lists.id"), nullable=True),
        sa.Column("sop_hint", sa.String(32), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("is_platform", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_identity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.CheckConstraint(
            "data_type IN ('text','numeric','integer','boolean','date','timestamptz','list')",
            name="schema_columns_type_chk",
        ),
        sa.CheckConstraint("status IN ('active', 'deprecated')", name="schema_columns_status_chk"),
        sa.CheckConstraint(
            "sop_hint IS NULL OR sop_hint IN ('barcode','container','parent','sample_type')",
            name="schema_columns_sop_hint_chk",
        ),
        sa.UniqueConstraint("table_id", "physical_name", name="uq_schema_columns_table_physical"),
    )
    op.create_index("ix_schema_columns_table", "schema_columns", ["table_id"])

    op.create_table(
        "schema_layouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("screen_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("client_id", "role_id", "screen_key", name="uq_schema_layouts_role_screen"),
    )

    op.create_table(
        "schema_layout_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("layout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_layouts.id"), nullable=False),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_columns.id"), nullable=False),
        sa.Column("section", sa.String(128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("layout_id", "column_id", name="uq_schema_layout_fields_membership"),
    )

    op.create_table(
        "schema_privileges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_tables.id"), nullable=False),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_columns.id"), nullable=True),
        sa.Column("access", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.CheckConstraint(
            "access IN ('read','write','none','inherit')",
            name="schema_privileges_access_chk",
        ),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_schema_privileges_grain
        ON schema_privileges (client_id, role_id, table_id, column_id)
        NULLS NOT DISTINCT
        """
    )

    op.create_table(
        "schema_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("op", sa.String(32), nullable=False),
        sa.Column("table_physical", sa.String(63), nullable=False),
        sa.Column("column_physical", sa.String(63), nullable=True),
        sa.Column("before_status", sa.String(32), nullable=True),
        sa.Column("after_status", sa.String(32), nullable=True),
        sa.Column("definition_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ui_schema_ddl_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("change_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schema_changes.id"), nullable=True),
        sa.Column("op", sa.String(32), nullable=False),
        sa.Column("table_physical", sa.String(63), nullable=False),
        sa.Column("column_physical", sa.String(63), nullable=True),
        sa.Column("pg_type", sa.String(32), nullable=True),
        sa.Column("nullable", sa.Boolean(), nullable=True),
        sa.Column("list_fk", sa.Boolean(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ui_schema_ddl_log_seq", "ui_schema_ddl_log", ["seq"])

    for table in REGISTRY_TABLES:
        op.execute(_client_rls(table))
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                    GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_app;
                END IF;
            END $$;
            """
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION ui_schema_ensure_sequence(p_name text)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            IF p_name !~ '^name_template_seq_[a-z0-9_]+$' THEN
                RAISE EXCEPTION 'invalid sequence name';
            END IF;
            EXECUTE format(
                'CREATE SEQUENCE IF NOT EXISTS %I START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1',
                p_name
            );
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO lims_app', p_name);
            END IF;
        END;
        $$;

        CREATE OR REPLACE FUNCTION ui_schema_create_table(p_physical text)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            pol text;
        BEGIN
            IF p_physical !~ '^(x|lab)_[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'invalid table name';
            END IF;
            IF to_regclass('public.' || p_physical) IS NOT NULL THEN
                RAISE EXCEPTION 'table exists';
            END IF;
            EXECUTE format(
                'CREATE TABLE public.%I (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    client_id uuid NOT NULL REFERENCES clients(id),
                    created_at timestamptz NOT NULL DEFAULT now(),
                    created_by uuid REFERENCES users(id),
                    modified_at timestamptz NOT NULL DEFAULT now(),
                    modified_by uuid REFERENCES users(id),
                    active boolean NOT NULL DEFAULT true
                )',
                p_physical
            );
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', p_physical);
            EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', p_physical);
            pol := left(p_physical, 50) || '_tenant';
            EXECUTE format(
                'CREATE POLICY %I ON public.%I FOR ALL
                 USING (
                    is_admin()
                    OR EXISTS (
                        SELECT 1 FROM users u
                        WHERE u.id = current_user_id()
                          AND (
                            u.client_id = %L::uuid
                            OR u.client_id = %I.client_id
                          )
                    )
                 )
                 WITH CHECK (
                    is_admin()
                    OR EXISTS (
                        SELECT 1 FROM users u
                        WHERE u.id = current_user_id()
                          AND (
                            u.client_id = %L::uuid
                            OR u.client_id = %I.client_id
                          )
                    )
                 )',
                pol,
                p_physical,
                '00000000-0000-0000-0000-000000000001',
                p_physical,
                '00000000-0000-0000-0000-000000000001',
                p_physical
            );
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                EXECUTE format(
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO lims_app',
                    p_physical
                );
            END IF;
        END;
        $$;

        CREATE OR REPLACE FUNCTION ui_schema_add_column(
            p_table text,
            p_column text,
            p_pg_type text,
            p_nullable boolean,
            p_list_fk boolean
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            ddl text;
        BEGIN
            IF p_table <> 'samples' AND p_table !~ '^(x|lab)_[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'table not allow-listed';
            END IF;
            IF p_column !~ '^[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'invalid column name';
            END IF;
            IF p_pg_type NOT IN ('text','numeric','integer','boolean','date','timestamptz','uuid') THEN
                RAISE EXCEPTION 'type not allow-listed';
            END IF;
            IF to_regclass('public.' || p_table) IS NULL THEN
                RAISE EXCEPTION 'table missing';
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = p_table AND column_name = p_column
            ) THEN
                RAISE EXCEPTION 'column exists';
            END IF;
            ddl := format('ALTER TABLE public.%I ADD COLUMN %I %s', p_table, p_column, p_pg_type);
            IF NOT p_nullable THEN
                ddl := ddl || ' NOT NULL';
            END IF;
            IF p_list_fk THEN
                ddl := ddl || ' REFERENCES list_entries(id)';
            END IF;
            EXECUTE ddl;
            IF p_table <> 'samples' THEN
                EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', p_table);
            END IF;
        END;
        $$;

        CREATE OR REPLACE FUNCTION ui_schema_drop_column(p_table text, p_column text)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            IF p_table <> 'samples' AND p_table !~ '^(x|lab)_[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'table not allow-listed';
            END IF;
            IF p_column !~ '^[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'invalid column name';
            END IF;
            EXECUTE format('ALTER TABLE public.%I DROP COLUMN IF EXISTS %I', p_table, p_column);
        END;
        $$;

        CREATE OR REPLACE FUNCTION ui_schema_drop_table(p_physical text)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            IF p_physical !~ '^(x|lab)_[a-z][a-z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'invalid table name';
            END IF;
            EXECUTE format('DROP TABLE IF EXISTS public.%I', p_physical);
        END;
        $$;
        """
    )

    for fn in (
        "ui_schema_ensure_sequence(text)",
        "ui_schema_create_table(text)",
        "ui_schema_add_column(text,text,text,boolean,boolean)",
        "ui_schema_drop_column(text,text)",
        "ui_schema_drop_table(text)",
    ):
        op.execute(f"ALTER FUNCTION {fn} OWNER TO schema_apply")
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                    GRANT EXECUTE ON FUNCTION {fn} TO lims_app;
                END IF;
            END $$;
            """
        )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                ALTER DEFAULT PRIVILEGES FOR ROLE schema_apply IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lims_app;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                REVOKE CREATE ON SCHEMA public FROM lims_app;
                GRANT USAGE ON SCHEMA public TO lims_app;
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
                GRANT USAGE, CREATE ON SCHEMA public TO lims_app;
            END IF;
        END $$;
        """
    )
    for fn in (
        "ui_schema_drop_table(text)",
        "ui_schema_drop_column(text,text)",
        "ui_schema_add_column(text,text,text,boolean,boolean)",
        "ui_schema_create_table(text)",
        "ui_schema_ensure_sequence(text)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    for table in reversed(REGISTRY_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE name IN ('schema:edit', 'layout:edit')
            )
            """
        )
    )
    connection.execute(
        sa.text("DELETE FROM permissions WHERE name IN ('schema:edit', 'layout:edit')")
    )
