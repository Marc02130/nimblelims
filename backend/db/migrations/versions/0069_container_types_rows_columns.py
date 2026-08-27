"""Replace container_types.dimensions with rows/columns.

Revision ID: 0069
Revises: 0068
Create Date: 2026-08-27

Single-element vessels are rows=1 AND columns=1. Plates are grids (e.g. 8×12).
Backfill: pure grid strings like ``1x1`` / ``8x12`` parse to ints; everything
else (physical sizes with units, null) defaults to 1×1.
"""

from alembic import op
import sqlalchemy as sa

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("container_types", sa.Column("rows", sa.Integer(), nullable=True))
    op.add_column("container_types", sa.Column("columns", sa.Integer(), nullable=True))

    # Pure grid dims only (digits x digits, no units). Else leave null → 1×1.
    # Physical sizes like '15x100mm' do not match and become 1×1.
    op.execute(
        sa.text(
            r"""
            UPDATE container_types
               SET rows = CAST(
                       (regexp_match(lower(trim(dimensions)), '^([0-9]+)[[:space:]]*[x×][[:space:]]*([0-9]+)$'))[1]
                       AS INTEGER
                   ),
                   columns = CAST(
                       (regexp_match(lower(trim(dimensions)), '^([0-9]+)[[:space:]]*[x×][[:space:]]*([0-9]+)$'))[2]
                       AS INTEGER
                   )
             WHERE dimensions IS NOT NULL
               AND trim(dimensions) <> ''
               AND lower(trim(dimensions)) ~ '^[0-9]+[[:space:]]*[x×][[:space:]]*[0-9]+$'
            """
        )
    )
    op.execute("UPDATE container_types SET rows = 1 WHERE rows IS NULL")
    op.execute("UPDATE container_types SET columns = 1 WHERE columns IS NULL")

    op.alter_column("container_types", "rows", nullable=False)
    op.alter_column("container_types", "columns", nullable=False)
    op.create_check_constraint(
        "ck_container_types_rows_positive",
        "container_types",
        "rows >= 1",
    )
    op.create_check_constraint(
        "ck_container_types_columns_positive",
        "container_types",
        "columns >= 1",
    )
    op.drop_column("container_types", "dimensions")


def downgrade() -> None:
    op.add_column(
        "container_types",
        sa.Column("dimensions", sa.String(length=50), nullable=True),
    )
    op.execute(
        """
        UPDATE container_types
           SET dimensions = rows::text || 'x' || columns::text
        """
    )
    op.drop_constraint("ck_container_types_rows_positive", "container_types", type_="check")
    op.drop_constraint("ck_container_types_columns_positive", "container_types", type_="check")
    op.drop_column("container_types", "columns")
    op.drop_column("container_types", "rows")
