"""P1 data-parsers: rename to data_parsers, versioning, M2M, imports

Revision ID: 0055
Revises: 0054
Create Date: 2026-07-20

- DELETE legacy template-scoped instrument_parsers (pre-release)
- RENAME instrument_parsers → data_parsers
- DROP experiment_template_id; ADD instrument/cro XOR, version_group, version, active
- parser_analyses, parser_setup_files, lims_run_imports
- lims_run_data.import_id
- lims_runs.analysis_id: app-required (nullable kept if empty analyses table)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0055'
down_revision = '0054'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Pre-release: drop legacy template-scoped parsers
    op.execute("DELETE FROM instrument_parsers")

    op.rename_table('instrument_parsers', 'data_parsers')

    # Drop old template index/FK
    op.execute("DROP INDEX IF EXISTS idx_instrument_parsers_template_id")
    op.execute("DROP INDEX IF EXISTS idx_instrument_parsers_config_gin")
    # Recreate gin on new name later

    # Drop experiment_template_id FK + column
    insp = sa.inspect(conn)
    fks = insp.get_foreign_keys('data_parsers')
    for fk in fks:
        cols = fk.get('constrained_columns') or []
        if cols == ['experiment_template_id'] or 'experiment_template_id' in cols:
            op.drop_constraint(fk['name'], 'data_parsers', type_='foreignkey')
            break
    op.drop_column('data_parsers', 'experiment_template_id')

    op.add_column(
        'data_parsers',
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'data_parsers',
        sa.Column('cro_source_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'data_parsers',
        sa.Column('version_group_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'data_parsers',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'data_parsers',
        sa.Column('active', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.create_foreign_key(
        'fk_data_parsers_instrument_id',
        'data_parsers', 'instruments',
        ['instrument_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_data_parsers_cro_source_id',
        'data_parsers', 'cro_sources',
        ['cro_source_id'], ['id'],
    )

    # Empty table after delete — version_group_id still needs NOT NULL for future rows
    op.alter_column('data_parsers', 'version_group_id', nullable=False)
    op.alter_column('data_parsers', 'version', server_default=None)
    op.alter_column('data_parsers', 'active', server_default=None)

    op.create_check_constraint(
        'ck_data_parsers_source_xor',
        'data_parsers',
        '(instrument_id IS NOT NULL AND cro_source_id IS NULL) OR '
        '(instrument_id IS NULL AND cro_source_id IS NOT NULL)',
    )
    op.create_unique_constraint(
        'uq_data_parsers_version_group_version',
        'data_parsers',
        ['version_group_id', 'version'],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_data_parsers_one_active_per_group "
        "ON data_parsers (version_group_id) WHERE active = true"
    )
    op.create_index('ix_data_parsers_instrument_id', 'data_parsers', ['instrument_id'])
    op.create_index('ix_data_parsers_cro_source_id', 'data_parsers', ['cro_source_id'])
    op.create_index('ix_data_parsers_version_group_id', 'data_parsers', ['version_group_id'])
    op.execute(
        'CREATE INDEX idx_data_parsers_config_gin ON data_parsers USING GIN (parser_config)'
    )

    # parser_analyses
    op.create_table(
        'parser_analyses',
        sa.Column('parser_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['parser_id'], ['data_parsers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parser_id', 'analysis_id'),
    )
    op.create_index('ix_parser_analyses_analysis_id', 'parser_analyses', ['analysis_id'])

    # parser_setup_files
    op.create_table(
        'parser_setup_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parser_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('content_type', sa.String(128), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('example', 'test', 'edge_fixture')",
            name='ck_parser_setup_files_role',
        ),
        sa.ForeignKeyConstraint(['parser_id'], ['data_parsers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_parser_setup_files_parser_id', 'parser_setup_files', ['parser_id'])

    # lims_run_imports
    op.create_table(
        'lims_run_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lims_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cro_source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parser_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(512), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('imported_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            '(instrument_id IS NOT NULL AND cro_source_id IS NULL) OR '
            '(instrument_id IS NULL AND cro_source_id IS NOT NULL)',
            name='ck_lims_run_imports_source_xor',
        ),
        sa.ForeignKeyConstraint(['lims_run_id'], ['lims_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id']),
        sa.ForeignKeyConstraint(['cro_source_id'], ['cro_sources.id']),
        sa.ForeignKeyConstraint(['parser_id'], ['data_parsers.id']),
        sa.ForeignKeyConstraint(['imported_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lims_run_imports_lims_run_id', 'lims_run_imports', ['lims_run_id'])
    op.create_index('ix_lims_run_imports_parser_id', 'lims_run_imports', ['parser_id'])

    op.add_column(
        'lims_run_data',
        sa.Column('import_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_lims_run_data_import_id',
        'lims_run_data', 'lims_run_imports',
        ['import_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_lims_run_data_import_id', 'lims_run_data', ['import_id'])

    # RLS for new config tables (lab-global)
    for table in ('data_parsers', 'parser_analyses', 'parser_setup_files'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL
            USING (is_admin() OR true);
        """)
    # lims_run_imports: follow run access via is_admin OR true for pre-release simplicity
    # (runs already have client RLS; imports are child of runs accessed via API)
    op.execute("ALTER TABLE lims_run_imports ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY lims_run_imports_access ON lims_run_imports
        FOR ALL
        USING (is_admin() OR true);
    """)


def downgrade() -> None:
    op.drop_constraint('fk_lims_run_data_import_id', 'lims_run_data', type_='foreignkey')
    op.drop_index('ix_lims_run_data_import_id', 'lims_run_data')
    op.drop_column('lims_run_data', 'import_id')

    op.execute("DROP POLICY IF EXISTS lims_run_imports_access ON lims_run_imports")
    op.drop_table('lims_run_imports')

    op.execute("DROP POLICY IF EXISTS parser_setup_files_access ON parser_setup_files")
    op.drop_table('parser_setup_files')

    op.execute("DROP POLICY IF EXISTS parser_analyses_access ON parser_analyses")
    op.drop_table('parser_analyses')

    op.execute("DROP POLICY IF EXISTS data_parsers_access ON data_parsers")
    op.execute("DROP INDEX IF EXISTS idx_data_parsers_config_gin")
    op.execute("DROP INDEX IF EXISTS uq_data_parsers_one_active_per_group")
    op.drop_constraint('uq_data_parsers_version_group_version', 'data_parsers', type_='unique')
    op.drop_constraint('ck_data_parsers_source_xor', 'data_parsers', type_='check')
    op.drop_constraint('fk_data_parsers_instrument_id', 'data_parsers', type_='foreignkey')
    op.drop_constraint('fk_data_parsers_cro_source_id', 'data_parsers', type_='foreignkey')
    op.drop_column('data_parsers', 'instrument_id')
    op.drop_column('data_parsers', 'cro_source_id')
    op.drop_column('data_parsers', 'version_group_id')
    op.drop_column('data_parsers', 'version')
    op.drop_column('data_parsers', 'active')

    op.add_column(
        'data_parsers',
        sa.Column('experiment_template_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.rename_table('data_parsers', 'instrument_parsers')
