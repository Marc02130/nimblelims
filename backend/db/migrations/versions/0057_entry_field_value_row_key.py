"""Add row_key to entry_field_values for multi-row experiment_data tables.

Unique indexes:
- free rows: (entry_id, field_definition_id, row_key) WHERE row_key IS NOT NULL
- sample-scoped: (entry_id, field_definition_id, sample_id) WHERE sample_id IS NOT NULL AND row_key IS NULL
- legacy single experiment cell: (entry_id, field_definition_id) WHERE sample_id IS NULL AND row_key IS NULL
"""
from alembic import op
import sqlalchemy as sa


revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entry_field_values",
        sa.Column("row_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "idx_entry_field_values_row_key",
        "entry_field_values",
        ["entry_id", "row_key"],
    )

    # Replace partial uniques to include row_key
    op.execute("DROP INDEX IF EXISTS uq_entry_field_values_no_sample;")
    op.execute("DROP INDEX IF EXISTS uq_entry_field_values_with_sample;")

    op.execute(
        """
        CREATE UNIQUE INDEX uq_entry_field_values_row_key
        ON entry_field_values (entry_id, field_definition_id, row_key)
        WHERE row_key IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_entry_field_values_with_sample
        ON entry_field_values (entry_id, field_definition_id, sample_id)
        WHERE sample_id IS NOT NULL AND row_key IS NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_entry_field_values_no_sample
        ON entry_field_values (entry_id, field_definition_id)
        WHERE sample_id IS NULL AND row_key IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_entry_field_values_row_key;")
    op.execute("DROP INDEX IF EXISTS uq_entry_field_values_with_sample;")
    op.execute("DROP INDEX IF EXISTS uq_entry_field_values_no_sample;")
    op.execute("DROP INDEX IF EXISTS idx_entry_field_values_row_key;")
    op.drop_column("entry_field_values", "row_key")

    op.execute(
        """
        CREATE UNIQUE INDEX uq_entry_field_values_no_sample
        ON entry_field_values (entry_id, field_definition_id)
        WHERE sample_id IS NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_entry_field_values_with_sample
        ON entry_field_values (entry_id, field_definition_id, sample_id)
        WHERE sample_id IS NOT NULL;
        """
    )
