"""P1 asked-for lake: analysis_param_defs + asked_for.

Revision ID: 0072
Revises: 0071
Create Date: 2026-08-28

Two tables only. No routing_map, no work_orders, no routed_work_order_id FK.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_param_defs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("data_type", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column(
            "required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("source_list_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("allowed_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "modified_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "data_type IN ('number', 'int', 'text', 'bool')",
            name="analysis_param_defs_data_type_chk",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["source_list_id"], ["lists.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["modified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "key", name="uq_analysis_param_defs_key"),
    )
    op.create_index(
        "ix_analysis_param_defs_analysis_id",
        "analysis_param_defs",
        ["analysis_id"],
    )

    op.create_table(
        "asked_for",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tat_days", sa.Integer(), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "modified_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('requested', 'routed', 'cancelled')",
            name="asked_for_status_chk",
        ),
        sa.CheckConstraint("tat_days > 0", name="asked_for_tat_days_chk"),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["modified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asked_for_sample_id", "asked_for", ["sample_id"])
    op.create_index("ix_asked_for_status", "asked_for", ["status"])
    op.create_index(
        "uq_asked_for_open",
        "asked_for",
        ["sample_id", "analysis_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    op.execute("ALTER TABLE analysis_param_defs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY analysis_param_defs_access
        ON analysis_param_defs
        FOR ALL
        USING (is_admin() OR current_user_id() IS NOT NULL)
        WITH CHECK (is_admin() OR current_user_id() IS NOT NULL)
        """
    )
    op.execute("ALTER TABLE analysis_param_defs FORCE ROW LEVEL SECURITY")

    op.execute("ALTER TABLE asked_for ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY asked_for_access
        ON asked_for
        FOR ALL
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = asked_for.sample_id
                  AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = asked_for.sample_id
                  AND has_project_access(s.project_id)
            )
        )
        """
    )
    op.execute("ALTER TABLE asked_for FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON analysis_param_defs TO lims_app;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON asked_for TO lims_app;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON analysis_param_defs TO lims_user;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON asked_for TO lims_user;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS asked_for_access ON asked_for")
    op.drop_index("uq_asked_for_open", table_name="asked_for")
    op.drop_index("ix_asked_for_status", table_name="asked_for")
    op.drop_index("ix_asked_for_sample_id", table_name="asked_for")
    op.drop_table("asked_for")
    op.execute("DROP POLICY IF EXISTS analysis_param_defs_access ON analysis_param_defs")
    op.drop_index("ix_analysis_param_defs_analysis_id", table_name="analysis_param_defs")
    op.drop_table("analysis_param_defs")
