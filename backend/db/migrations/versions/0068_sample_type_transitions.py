"""Add client-scoped sample type transition catalog.

Revision ID: 0068
Revises: 0067
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None

SAMPLE_TYPES_LIST_ID = "55555555-5555-5555-5555-555555555555"
SYSTEM_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
DNA_SAMPLE_TYPE_ID = "55555555-5555-4555-8555-555555555501"


def upgrade() -> None:
    op.create_table(
        "sample_type_transitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_sample_type",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column(
            "allowed_dest_sample_type",
            postgresql.UUID(as_uuid=True),
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
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "modified_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "operation IN ('aliquot', 'pool')",
            name="ck_sample_type_transitions_operation",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(
            ["source_sample_type"],
            ["list_entries.id"],
        ),
        sa.ForeignKeyConstraint(
            ["allowed_dest_sample_type"],
            ["list_entries.id"],
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["modified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id",
            "source_sample_type",
            "operation",
            "allowed_dest_sample_type",
            name="uq_sample_type_transitions_client_source_operation_dest",
        ),
    )
    op.create_index(
        "ix_sample_type_transitions_lookup",
        "sample_type_transitions",
        ["client_id", "source_sample_type", "operation"],
    )
    op.create_index(
        "ix_sample_type_transitions_allowed_dest",
        "sample_type_transitions",
        ["allowed_dest_sample_type"],
    )

    op.execute("ALTER TABLE sample_type_transitions ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY sample_type_transitions_access
        ON sample_type_transitions
        FOR ALL
        USING (
            is_admin()
            OR EXISTS (
                SELECT 1
                FROM users current_user_row
                WHERE current_user_row.id = current_user_id()
                  AND (
                    current_user_row.client_id = '{SYSTEM_CLIENT_ID}'::uuid
                    OR current_user_row.client_id = sample_type_transitions.client_id
                  )
            )
        )
        WITH CHECK (
            is_admin()
            OR EXISTS (
                SELECT 1
                FROM users current_user_row
                WHERE current_user_row.id = current_user_id()
                  AND (
                    current_user_row.client_id = '{SYSTEM_CLIENT_ID}'::uuid
                    OR current_user_row.client_id = sample_type_transitions.client_id
                  )
            )
        )
        """)
    op.execute("ALTER TABLE sample_type_transitions FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lims_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON sample_type_transitions TO lims_app;
            END IF;
        END $$;
        """)

    connection = op.get_bind()
    connection.execute(
        sa.text("""
            INSERT INTO list_entries (
                id,
                name,
                description,
                active,
                created_at,
                modified_at,
                list_id
            )
            SELECT
                CAST(:dna_id AS uuid),
                'DNA',
                'Deoxyribonucleic acid',
                true,
                NOW(),
                NOW(),
                CAST(:list_id AS uuid)
            WHERE NOT EXISTS (
                SELECT 1
                FROM list_entries
                WHERE list_id = CAST(:list_id AS uuid)
                  AND name = 'DNA'
            )
            """),
        {
            "list_id": SAMPLE_TYPES_LIST_ID,
            "dna_id": DNA_SAMPLE_TYPE_ID,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO sample_type_transitions (
                client_id,
                source_sample_type,
                operation,
                allowed_dest_sample_type,
                active,
                created_at,
                modified_at
            )
            SELECT
                clients.id,
                source_type.id,
                'aliquot',
                destination_type.id,
                true,
                NOW(),
                NOW()
            FROM clients
            JOIN list_entries source_type
              ON source_type.list_id = CAST(:list_id AS uuid)
             AND source_type.name = 'Blood'
            JOIN list_entries destination_type
              ON destination_type.list_id = CAST(:list_id AS uuid)
             AND destination_type.name = 'DNA'
            ON CONFLICT (
                client_id,
                source_sample_type,
                operation,
                allowed_dest_sample_type
            ) DO NOTHING
            """),
        {"list_id": SAMPLE_TYPES_LIST_ID},
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS sample_type_transitions_access "
        "ON sample_type_transitions"
    )
    op.drop_index(
        "ix_sample_type_transitions_allowed_dest",
        table_name="sample_type_transitions",
    )
    op.drop_index(
        "ix_sample_type_transitions_lookup",
        table_name="sample_type_transitions",
    )
    op.drop_table("sample_type_transitions")
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM list_entries
            WHERE id = CAST(:dna_id AS uuid)
              AND list_id = CAST(:list_id AS uuid)
              AND NOT EXISTS (
                SELECT 1
                FROM samples
                WHERE samples.sample_type = list_entries.id
              )
            """),
        {
            "dna_id": DNA_SAMPLE_TYPE_ID,
            "list_id": SAMPLE_TYPES_LIST_ID,
        },
    )
