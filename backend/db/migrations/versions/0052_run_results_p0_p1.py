"""P0/P1 run-results: analyte aliases + lims_runs.analysis_id

Revision ID: 0052
Revises: 0051
Create Date: 2026-07-11

- analyte_aliases: maintained synonym list per analyte (EtOH, C2H5OH, …)
- lims_runs.analysis_id: opt-in association for promote-on-publish
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0052'
down_revision = '0051'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'analyte_aliases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analyte_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alias', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['analyte_id'], ['analytes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analyte_aliases_analyte_id', 'analyte_aliases', ['analyte_id'])
    # Case-insensitive uniqueness for synonym matching
    op.execute(
        'CREATE UNIQUE INDEX uq_analyte_aliases_alias_lower ON analyte_aliases (lower(alias))'
    )
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON analyte_aliases TO lims_user')

    op.add_column(
        'lims_runs',
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_lims_runs_analysis_id',
        'lims_runs',
        'analyses',
        ['analysis_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_lims_runs_analysis_id', 'lims_runs', ['analysis_id'])


def downgrade() -> None:
    op.drop_index('ix_lims_runs_analysis_id', table_name='lims_runs')
    op.drop_constraint('fk_lims_runs_analysis_id', 'lims_runs', type_='foreignkey')
    op.drop_column('lims_runs', 'analysis_id')
    op.execute('DROP INDEX IF EXISTS uq_analyte_aliases_alias_lower')
    op.drop_index('ix_analyte_aliases_analyte_id', table_name='analyte_aliases')
    op.drop_table('analyte_aliases')
