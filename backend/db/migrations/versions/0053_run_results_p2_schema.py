"""P2 run-results: lims_run_id + replicate on results; drop name

Revision ID: 0053
Revises: 0052
Create Date: 2026-07-11

- Drop results.name (and uniqueness) — results are not named entities
- Add results.lims_run_id (lineage for promote / conflict rules)
- Add results.replicate INT (default 1) for multi-row same analyte
- Unique (test_id, analyte_id, replicate) for conflict identity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0053'
down_revision = '0052'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Drop name uniqueness + column ---
    # Constraint name from 0001 UniqueConstraint('name') is typically results_name_key
    conn = op.get_bind()
    insp = sa.inspect(conn)
    uniques = {u['name']: u for u in insp.get_unique_constraints('results')}
    if 'results_name_key' in uniques:
        op.drop_constraint('results_name_key', 'results', type_='unique')
    elif 'uq_results_name' in uniques:
        op.drop_constraint('uq_results_name', 'results', type_='unique')
    else:
        # Fallback: find unique constraint that only covers name
        for u in insp.get_unique_constraints('results'):
            cols = u.get('column_names') or []
            if cols == ['name'] or set(cols) == {'name'}:
                op.drop_constraint(u['name'], 'results', type_='unique')
                break

    # Indexes that might exist on name
    indexes = {i['name'] for i in insp.get_indexes('results')}
    for idx_name in ('ix_results_name', 'results_name_idx'):
        if idx_name in indexes:
            op.drop_index(idx_name, table_name='results')

    op.drop_column('results', 'name')

    # --- Lineage + replicate ---
    op.add_column(
        'results',
        sa.Column('lims_run_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_results_lims_run_id',
        'results',
        'lims_runs',
        ['lims_run_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_results_lims_run_id', 'results', ['lims_run_id'])

    op.add_column(
        'results',
        sa.Column('replicate', sa.Integer(), nullable=False, server_default='1'),
    )

    # Backfill distinct replicates for any duplicate (test_id, analyte_id) groups
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY test_id, analyte_id
                       ORDER BY created_at NULLS LAST, id
                   ) AS rn
            FROM results
            WHERE active IS DISTINCT FROM false
        )
        UPDATE results r
        SET replicate = ranked.rn
        FROM ranked
        WHERE r.id = ranked.id
        """
    )

    op.create_unique_constraint(
        'uq_results_test_analyte_replicate',
        'results',
        ['test_id', 'analyte_id', 'replicate'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_results_test_analyte_replicate', 'results', type_='unique')
    op.drop_column('results', 'replicate')
    op.drop_index('ix_results_lims_run_id', table_name='results')
    op.drop_constraint('fk_results_lims_run_id', 'results', type_='foreignkey')
    op.drop_column('results', 'lims_run_id')

    op.add_column(
        'results',
        sa.Column('name', sa.String(255), nullable=True),
    )
    # Restore unique names with synthetic values
    op.execute(
        """
        UPDATE results
        SET name = 'result-' || id::text
        WHERE name IS NULL
        """
    )
    op.alter_column('results', 'name', nullable=False)
    op.create_unique_constraint('results_name_key', 'results', ['name'])
