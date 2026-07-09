"""Add field_definitions table + seed lists/entries/FieldDefs for OOB (using lists, no options in validation_rules).

Revision ID: 0046
Revises: 0045
Create Date: 2026-07-05

Replaces the legacy custom_attributes_config / JSONB pattern for modeled fields (cleanup of options-in-rules).
Supports list-backed fields (data_type='list' + source_list_id -> lists/list_entries) and scalars (validation_rules for min/max etc).
OOB lists/FieldDefs seeded here (specimen_biotype, result_qualifiers etc).
Used by the new /admin/fields endpoint and Field Management UI.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0046'
down_revision = '0045'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create field_definitions table
    op.create_table(
        'field_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('data_type', sa.String(32), nullable=False),
        sa.Column('source_list_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_unique', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('ui_hints', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_materialized_column', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('column_name', sa.String(255), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        # From BaseModel
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['source_list_id'], ['lists.id']),
        sa.ForeignKeyConstraint(['template_id'], ['experiment_templates.id']),
        # process_id FK to 'processes' table omitted for now (ELN processes table not yet in schema)
        # sa.ForeignKeyConstraint(['process_id'], ['processes.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('ix_field_definitions_entity_type', 'field_definitions', ['entity_type'])
    op.create_index('ix_field_definitions_name', 'field_definitions', ['name'])
    op.create_index('ix_field_definitions_source_list_id', 'field_definitions', ['source_list_id'])
    op.create_index('ix_field_definitions_active', 'field_definitions', ['active'])

    # Unique per entity_type + name (for config uniqueness)
    op.create_unique_constraint('uq_field_definitions_entity_type_name', 'field_definitions', ['entity_type', 'name'])

    # Enable RLS
    op.execute("ALTER TABLE field_definitions ENABLE ROW LEVEL SECURITY;")

    # Path 1: add the materialized direct column for OOB specimen_biotype (list-backed)
    # Matches specimen_biotype_id in models/sample.py + FieldDef seeded below.
    # (Must exist for SQLAlchemy mapper / queries on Sample to succeed.)
    op.add_column(
        'samples',
        sa.Column('specimen_biotype_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index('ix_samples_specimen_biotype_id', 'samples', ['specimen_biotype_id'])
    op.create_foreign_key(
        'fk_samples_specimen_biotype_id_list_entries',
        'samples', 'list_entries',
        ['specimen_biotype_id'], ['id']
    )

    # RLS policy: admins full access, others can read active definitions (for form rendering etc.)
    # Note: this table has no client_id; policies are global or admin-only for writes.
    op.execute("""
        CREATE POLICY field_definitions_access ON field_definitions
        FOR ALL
        USING (
            is_admin() OR active = true
        );
    """)

    # Audit triggers (match pattern from 0002 / 0040 etc.)
    op.execute("""
        CREATE TRIGGER field_definitions_audit_timestamps
        BEFORE INSERT OR UPDATE ON field_definitions
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER field_definitions_update_modified_at
        BEFORE UPDATE ON field_definitions
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_at_column();
    """)

    # Note: No client_id on this table; field defs are system-wide or template/process scoped.
    # If per-client needed later, add column + policy.

    # --- Seed lists + entries for OOB list-backed fields (use central lists, NOT options in validation_rules or custom attrs) ---
    # Specimen Biotypes (for specimen_biotype on samples)
    connection = op.get_bind()
    biotype_list_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1'
    existing_biotype = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'specimen_biotypes' LIMIT 1")
    ).fetchone()
    if not existing_biotype:
        connection.execute(
            sa.text("""
                INSERT INTO lists (id, name, description, active, created_at, modified_at)
                VALUES (:id, 'specimen_biotypes', 'Specimen biotype values (list-backed for OOB)', true, NOW(), NOW())
            """),
            {'id': biotype_list_id}
        )
        biotype_entries = [
            {'name': 'B-cell', 'description': 'B-cell biotype'},
            {'name': 'T-cell', 'description': 'T-cell biotype'},
            {'name': 'NK-cell', 'description': 'NK-cell biotype'},
            {'name': 'Monocyte', 'description': 'Monocyte biotype'},
            {'name': 'Granulocyte', 'description': 'Granulocyte biotype'},
            {'name': 'Other', 'description': 'Other biotype'},
        ]
        for entry in biotype_entries:
            connection.execute(
                sa.text("""
                    INSERT INTO list_entries (id, name, description, list_id, active, created_at, modified_at)
                    VALUES (gen_random_uuid(), :name, :description, :list_id, true, NOW(), NOW())
                    ON CONFLICT (list_id, name) DO NOTHING
                """),
                {'name': entry['name'], 'description': entry['description'], 'list_id': biotype_list_id}
            )
    else:
        biotype_list_id = existing_biotype[0]

    # --- Seed FieldDefinition for OOB specimen_biotype (Path 1 direct column, backed by list) ---
    fd_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1'
    existing_fd = connection.execute(
        sa.text("SELECT id FROM field_definitions WHERE entity_type = 'sample' AND name = 'specimen_biotype' LIMIT 1")
    ).fetchone()
    if not existing_fd:
        connection.execute(
            sa.text("""
                INSERT INTO field_definitions (
                    id, entity_type, name, display_name, data_type, source_list_id,
                    is_required, is_unique, default_value, validation_rules, ui_hints,
                    is_materialized_column, column_name, active, description,
                    created_at, modified_at
                ) VALUES (
                    :id, 'sample', 'specimen_biotype', 'Specimen Biotype', 'list', :source_list_id,
                    false, false, NULL, '{}', '{}',
                    true, 'specimen_biotype_id', true, 'Biological type / classification of the specimen',
                    NOW(), NOW()
                )
            """),
            {'id': fd_id, 'source_list_id': biotype_list_id}
        )

    # Result qualifiers list for OOB
    qualifiers_list_id = 'cccccccc-cccc-cccc-cccc-ccccccccccc1'
    existing_qual = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'result_qualifiers' LIMIT 1")
    ).fetchone()
    if not existing_qual:
        connection.execute(
            sa.text("""
                INSERT INTO lists (id, name, description, active, created_at, modified_at)
                VALUES (:id, 'result_qualifiers', 'Result qualifiers / flags (list-backed)', true, NOW(), NOW())
            """),
            {'id': qualifiers_list_id}
        )
        qual_entries = [
            {'name': 'Normal', 'description': ''},
            {'name': 'Above Range', 'description': ''},
            {'name': 'Below Range', 'description': ''},
            {'name': 'Invalid', 'description': ''},
            {'name': 'Pending Review', 'description': ''},
        ]
        for entry in qual_entries:
            connection.execute(
                sa.text("""
                    INSERT INTO list_entries (id, name, description, list_id, active, created_at, modified_at)
                    VALUES (gen_random_uuid(), :name, :description, :list_id, true, NOW(), NOW())
                    ON CONFLICT (list_id, name) DO NOTHING
                """),
                {'name': entry['name'], 'description': entry['description'], 'list_id': qualifiers_list_id}
            )
    else:
        qualifiers_list_id = existing_qual[0]


def downgrade() -> None:
    # Drop audit triggers first (reverse order)
    op.execute("DROP TRIGGER IF EXISTS field_definitions_update_modified_at ON field_definitions;")
    op.execute("DROP TRIGGER IF EXISTS field_definitions_audit_timestamps ON field_definitions;")

    # Clean seeded data first
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM field_definitions WHERE name = 'specimen_biotype'"))
    biotype_list = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'specimen_biotypes' LIMIT 1")
    ).fetchone()
    if biotype_list:
        connection.execute(
            sa.text("DELETE FROM list_entries WHERE list_id = :lid"),
            {'lid': biotype_list[0]}
        )
        connection.execute(
            sa.text("DELETE FROM lists WHERE id = :lid"),
            {'lid': biotype_list[0]}
        )
    qual_list = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'result_qualifiers' LIMIT 1")
    ).fetchone()
    if qual_list:
        connection.execute(
            sa.text("DELETE FROM list_entries WHERE list_id = :lid"),
            {'lid': qual_list[0]}
        )
        connection.execute(
            sa.text("DELETE FROM lists WHERE id = :lid"),
            {'lid': qual_list[0]}
        )

    # Drop the Path1 column we added for specimen_biotype
    op.drop_constraint('fk_samples_specimen_biotype_id_list_entries', 'samples', type_='foreignkey')
    op.drop_index('ix_samples_specimen_biotype_id', table_name='samples')
    op.drop_column('samples', 'specimen_biotype_id')

    op.drop_constraint('uq_field_definitions_entity_type_name', 'field_definitions', type_='unique')
    op.drop_index('ix_field_definitions_active', table_name='field_definitions')
    op.drop_index('ix_field_definitions_source_list_id', table_name='field_definitions')
    op.drop_index('ix_field_definitions_name', table_name='field_definitions')
    op.drop_index('ix_field_definitions_entity_type', table_name='field_definitions')
    op.execute("DROP POLICY IF EXISTS field_definitions_access ON field_definitions;")
    op.execute("ALTER TABLE field_definitions DISABLE ROW LEVEL SECURITY;")
    op.drop_table('field_definitions')
