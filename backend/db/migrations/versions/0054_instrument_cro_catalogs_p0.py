"""P0 data-parsers: instrument_types, instruments (instances), cro_sources

Revision ID: 0054
Revises: 0053
Create Date: 2026-07-20

Lab-global catalogs for instrument vendor/model types, physical instances,
and CRO export sources. Permission gated in API via config:edit.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0054'
down_revision = '0053'
branch_labels = None
depends_on = None


def _create_catalog_table(name: str, extra_columns: list, extra_fks: list, extra_indexes: list):
    cols = [
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
    ] + extra_columns
    fks = [
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    ] + extra_fks
    op.create_table(name, *cols, *fks)
    op.create_index(f'ix_{name}_active', name, ['active'])
    for idx_name, idx_cols, unique, postgresql_where in extra_indexes:
        if postgresql_where is not None:
            op.create_index(idx_name, name, idx_cols, unique=unique, postgresql_where=postgresql_where)
        else:
            op.create_index(idx_name, name, idx_cols, unique=unique)


def _enable_rls_and_audit(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"""
        CREATE POLICY {table}_access ON {table}
        FOR ALL
        USING (is_admin() OR active = true);
    """)
    op.execute(f"""
        CREATE TRIGGER {table}_audit_timestamps
        BEFORE INSERT OR UPDATE ON {table}
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute(f"""
        CREATE TRIGGER {table}_update_modified_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_at_column();
    """)


def upgrade() -> None:
    _create_catalog_table(
        'instrument_types',
        extra_columns=[
            sa.Column('vendor', sa.String(255), nullable=True),
            sa.Column('model', sa.String(255), nullable=True),
        ],
        extra_fks=[],
        extra_indexes=[
            ('ix_instrument_types_vendor', ['vendor'], False, None),
            ('ix_instrument_types_model', ['model'], False, None),
        ],
    )
    _enable_rls_and_audit('instrument_types')

    _create_catalog_table(
        'instruments',
        extra_columns=[
            sa.Column('instrument_type_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('serial_number', sa.String(255), nullable=True),
        ],
        extra_fks=[
            sa.ForeignKeyConstraint(['instrument_type_id'], ['instrument_types.id']),
        ],
        extra_indexes=[
            ('ix_instruments_instrument_type_id', ['instrument_type_id'], False, None),
            (
                'uq_instruments_type_serial',
                ['instrument_type_id', 'serial_number'],
                True,
                sa.text('serial_number IS NOT NULL'),
            ),
        ],
    )
    _enable_rls_and_audit('instruments')

    _create_catalog_table(
        'cro_sources',
        extra_columns=[
            sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        ],
        extra_fks=[
            sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        ],
        extra_indexes=[
            ('ix_cro_sources_client_id', ['client_id'], False, None),
        ],
    )
    _enable_rls_and_audit('cro_sources')


def downgrade() -> None:
    for table in ('cro_sources', 'instruments', 'instrument_types'):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table};")
        op.drop_table(table)
