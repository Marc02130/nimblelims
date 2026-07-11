"""Phase 2: entries, entry_field_definitions, entry_field_values

Revision ID: 0048
Revises: 0047
Create Date: 2026-07-11

Structured data capture inside Experiments (ELN). Declared on templates via
template_definition['entries'] and instantiated per Experiment.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0048'
down_revision = '0047'
branch_labels = None
depends_on = None

_CLIENT_POLICY = """\
    is_admin() OR (
        has_experiment_access() AND
        created_by IN (
            SELECT u.id FROM users u
            WHERE u.client_id = (
                SELECT u2.client_id FROM users u2
                WHERE u2.id = current_user_id()
            )
        )
    )\
"""

# entry_field_definitions has no created_by — inherit access via parent entry
_ENTRY_CHILD_POLICY = """\
    is_admin() OR (
        has_experiment_access() AND
        entry_id IN (
            SELECT e.id FROM entries e
            WHERE e.created_by IN (
                SELECT u.id FROM users u
                WHERE u.client_id = (
                    SELECT u2.client_id FROM users u2
                    WHERE u2.id = current_user_id()
                )
            )
        )
    )\
"""


def upgrade() -> None:
    op.create_table(
        'entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_step_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('entry_type', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('predefined_entry_key', sa.String(128), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('config', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['process_step_id'], ['eln_process_steps.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_entries_experiment_id', 'entries', ['experiment_id'])
    op.create_index('idx_entries_process_step_id', 'entries', ['process_step_id'])
    op.create_index('idx_entries_entry_type', 'entries', ['entry_type'])
    op.create_index('idx_entries_created_by', 'entries', ['created_by'])
    op.create_index('idx_entries_predefined_key', 'entries', ['predefined_entry_key'])

    op.create_table(
        'entry_field_definitions',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_definition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('write_back_target', sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_definition_id'], ['field_definitions.id']),
        sa.PrimaryKeyConstraint('entry_id', 'field_definition_id'),
    )
    op.create_index(
        'idx_entry_field_definitions_field_id',
        'entry_field_definitions',
        ['field_definition_id'],
    )

    op.create_table(
        'entry_field_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_definition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('value_number', sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column('value_list_entry_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('value_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('value_boolean', sa.Boolean(), nullable=True),
        sa.Column('value_json', postgresql.JSONB(), nullable=True),
        sa.Column('write_back_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('write_back_previous', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_definition_id'], ['field_definitions.id']),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id']),
        sa.ForeignKeyConstraint(['value_list_entry_id'], ['list_entries.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_entry_field_values_entry_id', 'entry_field_values', ['entry_id'])
    op.create_index('idx_entry_field_values_field_id', 'entry_field_values', ['field_definition_id'])
    op.create_index('idx_entry_field_values_sample_id', 'entry_field_values', ['sample_id'])
    op.create_index('idx_entry_field_values_created_by', 'entry_field_values', ['created_by'])

    # Uniqueness: experiment_detail (no sample) vs sample_data (with sample)
    op.execute("""
        CREATE UNIQUE INDEX uq_entry_field_values_no_sample
        ON entry_field_values (entry_id, field_definition_id)
        WHERE sample_id IS NULL;
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_entry_field_values_with_sample
        ON entry_field_values (entry_id, field_definition_id, sample_id)
        WHERE sample_id IS NOT NULL;
    """)

    # Audit + RLS
    for table in ('entries', 'entry_field_values'):
        op.execute(f"""
            CREATE TRIGGER {table}_audit_timestamps
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_audit_timestamps();
        """)
        op.execute(f"""
            CREATE TRIGGER {table}_update_modified_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_modified_at_column();
        """)
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            FOR ALL USING ({_CLIENT_POLICY});
        """)
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_user;')

    op.execute('ALTER TABLE entry_field_definitions ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE entry_field_definitions FORCE ROW LEVEL SECURITY;')
    op.execute(f"""
        CREATE POLICY entry_field_definitions_access ON entry_field_definitions
        FOR ALL USING ({_ENTRY_CHILD_POLICY});
    """)
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON entry_field_definitions TO lims_user;'
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS entry_field_definitions_access ON entry_field_definitions;')
    op.execute('ALTER TABLE entry_field_definitions NO FORCE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE entry_field_definitions DISABLE ROW LEVEL SECURITY;')

    for table in ('entry_field_values', 'entries'):
        op.execute(f'DROP POLICY IF EXISTS {table}_access ON {table};')
        op.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};')
        op.execute(f'DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};')

    op.execute('DROP INDEX IF EXISTS uq_entry_field_values_with_sample;')
    op.execute('DROP INDEX IF EXISTS uq_entry_field_values_no_sample;')
    op.drop_table('entry_field_values')
    op.drop_table('entry_field_definitions')
    op.drop_table('entries')
