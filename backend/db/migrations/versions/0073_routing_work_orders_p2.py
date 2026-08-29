"""P2 routing map, work_orders, step accepted sample types.

Revision ID: 0073
Revises: 0072
Create Date: 2026-08-28

OQ-WO-4: type gate on process-definition steps (experiment and LimsRun), not analysis.
Qubit is a LimsRun step. No analysis_accepted_sample_types. No blood→Qubit seed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.alter_column(
        "eln_process_definition_steps",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "eln_process_definition_steps",
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_eln_process_definition_steps_analysis_id",
        "eln_process_definition_steps",
        "analyses",
        ["analysis_id"],
        ["id"],
    )
    op.create_index(
        "ix_eln_process_definition_steps_analysis_id",
        "eln_process_definition_steps",
        ["analysis_id"],
    )
    op.create_check_constraint(
        "eln_process_definition_steps_kind_chk",
        "eln_process_definition_steps",
        "(step_kind = 'eln_experiment' AND experiment_template_id IS NOT NULL) "
        "OR (step_kind = 'lims_run' AND "
        "(analysis_id IS NOT NULL OR experiment_template_id IS NOT NULL))",
    )

    op.alter_column(
        "lims_runs",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.alter_column(
        "eln_process_steps",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "eln_process_steps",
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_eln_process_steps_analysis_id",
        "eln_process_steps",
        "analyses",
        ["analysis_id"],
        ["id"],
    )

    op.create_table(
        "eln_process_definition_step_accepted_sample_types",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["eln_process_definition_steps.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["sample_type_id"], ["list_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "step_id",
            "sample_type_id",
            name="uq_step_accepted_sample_type",
        ),
    )
    op.create_index(
        "ix_step_accepted_sample_types_step_id",
        "eln_process_definition_step_accepted_sample_types",
        ["step_id"],
    )

    op.create_table(
        "routing_map",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tat_range", postgresql.INT4RANGE(), nullable=False),
        sa.Column(
            "process_definition_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
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
            "array_length(process_definition_ids, 1) >= 1",
            name="routing_map_chain_chk",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["sample_type_id"], ["list_entries.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["modified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        ALTER TABLE routing_map ADD CONSTRAINT routing_map_tat_excl
        EXCLUDE USING gist (
            analysis_id WITH =,
            sample_type_id WITH =,
            tat_range WITH &&
        ) WHERE (active)
        """
    )

    op.create_table(
        "work_orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("asked_for_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "process_definition_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("process_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "status IN ('queued', 'in_progress', 'completed', 'cancelled')",
            name="work_orders_status_chk",
        ),
        sa.CheckConstraint(
            "array_length(process_definition_ids, 1) >= 1",
            name="work_orders_chain_chk",
        ),
        sa.ForeignKeyConstraint(["asked_for_id"], ["asked_for.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["process_id"], ["eln_processes.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["modified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asked_for_id", name="uq_work_orders_asked_for_id"),
    )
    op.create_index("ix_work_orders_status", "work_orders", ["status"])
    op.create_index("ix_work_orders_sample_id", "work_orders", ["sample_id"])

    op.add_column(
        "asked_for",
        sa.Column("routed_work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_asked_for_routed_work_order_id",
        "asked_for",
        "work_orders",
        ["routed_work_order_id"],
        ["id"],
    )

    op.add_column(
        "eln_processes",
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_eln_processes_work_order_id",
        "eln_processes",
        "work_orders",
        ["work_order_id"],
        ["id"],
    )
    op.create_index(
        "ix_eln_processes_work_order_id",
        "eln_processes",
        ["work_order_id"],
    )

    op.add_column(
        "tests",
        sa.Column(
            "asked_for_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    for table in (
        "routing_map",
        "work_orders",
        "eln_process_definition_step_accepted_sample_types",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY routing_map_access ON routing_map
        FOR ALL
        USING (is_admin() OR current_user_id() IS NOT NULL)
        WITH CHECK (is_admin() OR current_user_id() IS NOT NULL)
        """
    )
    op.execute(
        """
        CREATE POLICY work_orders_access ON work_orders
        FOR ALL
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = work_orders.sample_id
                  AND has_project_access(s.project_id)
            )
        )
        WITH CHECK (
            is_admin()
            OR EXISTS (
                SELECT 1 FROM samples s
                WHERE s.id = work_orders.sample_id
                  AND has_project_access(s.project_id)
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY step_accepted_sample_types_access
        ON eln_process_definition_step_accepted_sample_types
        FOR ALL
        USING (is_admin() OR current_user_id() IS NOT NULL)
        WITH CHECK (is_admin() OR current_user_id() IS NOT NULL)
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON routing_map TO lims_app;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON work_orders TO lims_app;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON eln_process_definition_step_accepted_sample_types TO lims_app;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON routing_map TO lims_user;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON work_orders TO lims_user;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON eln_process_definition_step_accepted_sample_types TO lims_user;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_column("tests", "asked_for_params")
    op.drop_index("ix_eln_processes_work_order_id", table_name="eln_processes")
    op.drop_constraint("fk_eln_processes_work_order_id", "eln_processes", type_="foreignkey")
    op.drop_column("eln_processes", "work_order_id")
    op.drop_constraint("fk_asked_for_routed_work_order_id", "asked_for", type_="foreignkey")
    op.drop_column("asked_for", "routed_work_order_id")
    op.execute("DROP POLICY IF EXISTS work_orders_access ON work_orders")
    op.drop_index("ix_work_orders_sample_id", table_name="work_orders")
    op.drop_index("ix_work_orders_status", table_name="work_orders")
    op.drop_table("work_orders")
    op.execute("DROP POLICY IF EXISTS routing_map_access ON routing_map")
    op.execute("ALTER TABLE routing_map DROP CONSTRAINT IF EXISTS routing_map_tat_excl")
    op.drop_table("routing_map")
    op.execute(
        "DROP POLICY IF EXISTS step_accepted_sample_types_access "
        "ON eln_process_definition_step_accepted_sample_types"
    )
    op.drop_index(
        "ix_step_accepted_sample_types_step_id",
        table_name="eln_process_definition_step_accepted_sample_types",
    )
    op.drop_table("eln_process_definition_step_accepted_sample_types")
    op.drop_constraint(
        "eln_process_definition_steps_kind_chk",
        "eln_process_definition_steps",
        type_="check",
    )
    op.drop_index(
        "ix_eln_process_definition_steps_analysis_id",
        table_name="eln_process_definition_steps",
    )
    op.drop_constraint(
        "fk_eln_process_definition_steps_analysis_id",
        "eln_process_definition_steps",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_eln_process_steps_analysis_id",
        "eln_process_steps",
        type_="foreignkey",
    )
    op.drop_column("eln_process_steps", "analysis_id")
    op.alter_column(
        "eln_process_steps",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("eln_process_definition_steps", "analysis_id")
    op.alter_column(
        "eln_process_definition_steps",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "lims_runs",
        "experiment_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
