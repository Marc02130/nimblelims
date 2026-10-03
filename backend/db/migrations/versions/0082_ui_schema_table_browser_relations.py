"""Schema table browser + side-link relations registry.

Revision ID: 0082
Revises: 0081
Create Date: 2026-10-03

Stem ``ui-schema-tables-cleanup``. The Schema screen becomes a table browser
over allow-listed real tables (lab + system reference), so the registry must
describe columns it did not create:

* ``schema_tables.kind`` gains ``system`` (reference tables such as ``lists``).
* ``schema_columns`` gains reflection facts (``is_fk``, ``fk_table``,
  ``is_unique``, ``pg_type``) and ``origin`` (``ui`` vs ``reflected``).
  ``data_type`` accepts ``uuid`` / ``jsonb`` / ``other`` for *reflected* columns
  only; the ADD COLUMN allow-list (P1 types) is unchanged.
* ``schema_relations``: one-to-many / one-to-one side links. Registry only —
  the key is an existing real FK column on the child. No junction tables, no
  DDL from this registry (OQ-16 stands: JSONB is payload, not config).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None

SYSTEM_CLIENT_ID = "00000000-0000-0000-0000-000000000001"


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
    op.drop_constraint("schema_tables_kind_chk", "schema_tables", type_="check")
    op.create_check_constraint(
        "schema_tables_kind_chk",
        "schema_tables",
        "kind IN ('core', 'ui', 'system')",
    )

    op.add_column(
        "schema_columns",
        sa.Column("is_fk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("schema_columns", sa.Column("fk_table", sa.String(63), nullable=True))
    op.add_column(
        "schema_columns",
        sa.Column("is_unique", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("schema_columns", sa.Column("pg_type", sa.String(64), nullable=True))
    op.add_column(
        "schema_columns",
        sa.Column("origin", sa.String(16), nullable=False, server_default="ui"),
    )
    op.create_check_constraint(
        "schema_columns_origin_chk",
        "schema_columns",
        "origin IN ('ui', 'reflected')",
    )
    # Platform/identity rows were seeded by the service for real ORM columns;
    # they are described, not UI-created.
    op.execute(
        "UPDATE schema_columns SET origin = 'reflected' WHERE is_platform OR is_identity"
    )
    op.drop_constraint("schema_columns_type_chk", "schema_columns", type_="check")
    op.create_check_constraint(
        "schema_columns_type_chk",
        "schema_columns",
        "data_type IN ('text','numeric','integer','boolean','date','timestamptz','list',"
        "'uuid','jsonb','other')",
    )

    op.create_table(
        "schema_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "from_table_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("schema_tables.id"),
            nullable=False,
        ),
        sa.Column(
            "to_table_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("schema_tables.id"),
            nullable=False,
        ),
        sa.Column(
            "fk_column_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("schema_columns.id"),
            nullable=False,
        ),
        sa.Column("cardinality", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.CheckConstraint(
            "cardinality IN ('one_to_many', 'one_to_one')",
            name="schema_relations_cardinality_chk",
        ),
        sa.CheckConstraint("status IN ('active', 'deprecated')", name="schema_relations_status_chk"),
        sa.UniqueConstraint("client_id", "fk_column_id", name="uq_schema_relations_fk_column"),
    )
    op.create_index("ix_schema_relations_client", "schema_relations", ["client_id"])
    op.create_index("ix_schema_relations_from", "schema_relations", ["from_table_id"])
    op.create_index("ix_schema_relations_to", "schema_relations", ["to_table_id"])

    op.execute(_client_rls("schema_relations"))
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON schema_relations TO lims_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS schema_relations CASCADE")
    # Rows this revision made describable: reflected non-seeded columns and
    # every system table. Remove dependents first (layout membership, privileges).
    op.execute(
        """
        CREATE TEMP TABLE _gone_cols AS
        SELECT c.id FROM schema_columns c
        JOIN schema_tables t ON t.id = c.table_id
        WHERE t.kind = 'system'
           OR (c.origin = 'reflected' AND NOT (c.is_platform OR c.is_identity))
           OR c.data_type NOT IN ('text','numeric','integer','boolean','date','timestamptz','list');
        DELETE FROM schema_layout_fields WHERE column_id IN (SELECT id FROM _gone_cols);
        DELETE FROM schema_privileges WHERE column_id IN (SELECT id FROM _gone_cols);
        DELETE FROM schema_columns WHERE id IN (SELECT id FROM _gone_cols);
        DROP TABLE _gone_cols;
        DELETE FROM schema_privileges
        WHERE table_id IN (SELECT id FROM schema_tables WHERE kind = 'system');
        """
    )
    op.drop_constraint("schema_columns_type_chk", "schema_columns", type_="check")
    op.create_check_constraint(
        "schema_columns_type_chk",
        "schema_columns",
        "data_type IN ('text','numeric','integer','boolean','date','timestamptz','list')",
    )
    op.drop_constraint("schema_columns_origin_chk", "schema_columns", type_="check")
    op.drop_column("schema_columns", "origin")
    op.drop_column("schema_columns", "pg_type")
    op.drop_column("schema_columns", "is_unique")
    op.drop_column("schema_columns", "fk_table")
    op.drop_column("schema_columns", "is_fk")
    op.execute("DELETE FROM schema_tables WHERE kind = 'system'")
    op.drop_constraint("schema_tables_kind_chk", "schema_tables", type_="check")
    op.create_check_constraint(
        "schema_tables_kind_chk",
        "schema_tables",
        "kind IN ('core', 'ui')",
    )
