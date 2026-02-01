"""Add configurable name/ID templates for entities

Revision ID: 0021
Revises: 0020
Create Date: 2026-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create name_templates table
    op.create_table('name_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('template', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('seq_padding_digits', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on entity_type for faster lookups
    op.create_index('idx_name_templates_entity_type', 'name_templates', ['entity_type'])
    
    # Create partial unique index to ensure only one active template per entity_type
    op.execute("""
        CREATE UNIQUE INDEX idx_name_templates_entity_type_active_unique 
        ON name_templates (entity_type) 
        WHERE active = true
    """)
    
    # Sequences for {SEQ} are created on first use in name_generation.get_next_sequence()
    # (CREATE SEQUENCE IF NOT EXISTS). Not created here so migrations stay free of sequence lifecycle.
    
    # Enable RLS on name_templates
    op.execute("ALTER TABLE name_templates ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policy: admins can manage all, others can view active templates
    op.execute("""
        CREATE POLICY name_templates_access ON name_templates
        FOR ALL
        USING (
            is_admin() OR active = true
        );
    """)
    
    # Apply audit triggers to name_templates
    op.execute("""
        CREATE TRIGGER name_templates_audit_timestamps
        BEFORE INSERT OR UPDATE ON name_templates
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_timestamps();
    """)
    
    op.execute("""
        CREATE TRIGGER name_templates_update_modified_at
        BEFORE UPDATE ON name_templates
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_at_column();
    """)
    
    # Seed initial templates (idempotent)
    connection = op.get_bind()
    
    # Get admin user ID for created_by/modified_by
    admin_result = connection.execute(
        sa.text("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
    ).fetchone()
    admin_id = admin_result[0] if admin_result else None
    
    initial_templates = [
        {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
            'entity_type': 'sample',
            'template': '{PROJECT}-{SEQ}',
            'description': 'Default sample naming template: PROJECT-SEQ (e.g., PROJECT-001)',
            'seq_padding_digits': 2,
            'active': True
        },
        {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
            'entity_type': 'project',
            'template': '{CLIABV}{YY}{SEQ}',
            'description': 'Default project naming template: CLIABVYY-SEQ (e.g., ACME2400001)',
            'seq_padding_digits': 5,
            'active': True
        },
        {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
            'entity_type': 'batch',
            'template': 'B{YY}{SEQ}',
            'description': 'Default batch naming template: BYYSEQ (e.g., B2400001)',
            'seq_padding_digits': 5,
            'active': True
        },
        {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4',
            'entity_type': 'analysis',
            'template': 'ANALYSIS-{SEQ}',
            'description': 'Default analysis naming template: ANALYSIS-SEQ (e.g., ANALYSIS-0001)',
            'seq_padding_digits': 4,
            'active': True
        },
        {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5',
            'entity_type': 'container',
            'template': '{YYMM}-{SEQ}',
            'description': 'Default container naming template: YYMM-SEQ (e.g., CONT-20240108-001)',
            'seq_padding_digits': 6,
            'active': True
        },
    ]
    
    for template_data in initial_templates:
        connection.execute(
            sa.text("""
                INSERT INTO name_templates (id, entity_type, template, description, seq_padding_digits, active, created_at, modified_at, created_by, modified_by)
                VALUES (:id, :entity_type, :template, :description, :seq_padding_digits, :active, NOW(), NOW(), :created_by, :modified_by)
                ON CONFLICT (id) DO UPDATE SET
                    entity_type = EXCLUDED.entity_type,
                    template = EXCLUDED.template,
                    description = EXCLUDED.description,
                    seq_padding_digits = EXCLUDED.seq_padding_digits,
                    active = EXCLUDED.active,
                    modified_at = NOW(),
                    modified_by = EXCLUDED.modified_by
            """),
            {
                'id': template_data['id'],
                'entity_type': template_data['entity_type'],
                'template': template_data['template'],
                'description': template_data['description'],
                'active': template_data['active'],
                'seq_padding_digits': template_data['seq_padding_digits'],
                'created_by': admin_id,
                'modified_by': admin_id
            }
        )


def downgrade() -> None:
    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS name_templates_access ON name_templates;")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS name_templates_update_modified_at ON name_templates;")
    op.execute("DROP TRIGGER IF EXISTS name_templates_audit_timestamps ON name_templates;")
    
    # Drop indexes
    op.drop_index('idx_name_templates_entity_type_active_unique', table_name='name_templates')
    op.drop_index('idx_name_templates_entity_type', table_name='name_templates')
    
    # Sequences (if any) were created at runtime by name_generation; optionally drop them in downgrade:
    # for entity_type in ('sample', 'project', 'batch', 'analysis', 'container'):
    #     op.execute(f"DROP SEQUENCE IF EXISTS name_template_seq_{entity_type};")
    
    # Drop table
    op.drop_table('name_templates')

