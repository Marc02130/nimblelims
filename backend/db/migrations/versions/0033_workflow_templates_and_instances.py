"""Add workflow_templates and workflow_instances tables

Revision ID: 0033
Revises: 0032
Create Date: 2026-02-24

Creates workflow_templates (template_definition JSONB: steps with action/params)
and workflow_instances (runtime_state JSONB). Includes indexes, RLS (role-based),
and audit triggers. Extends existing BaseModel-style audit fields.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0033'
down_revision = '0032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # workflow_templates: template definition with steps array (action, params)
    op.create_table(
        'workflow_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('template_definition', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_workflow_templates_name'),
    )

    # workflow_instances: runtime state JSONB, FK to template
    op.create_table(
        'workflow_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('workflow_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('runtime_state', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['workflow_template_id'], ['workflow_templates.id']),
        sa.ForeignKeyConstraint(['status_id'], ['list_entries.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_workflow_instances_name'),
    )

    # Indexes for workflow_templates
    op.create_index('idx_workflow_templates_active', 'workflow_templates', ['active'])
    op.execute('CREATE INDEX idx_workflow_templates_template_definition_gin ON workflow_templates USING GIN (template_definition);')

    # Indexes for workflow_instances
    op.create_index('idx_workflow_instances_template_id', 'workflow_instances', ['workflow_template_id'])
    op.create_index('idx_workflow_instances_status_id', 'workflow_instances', ['status_id'])
    op.create_index('idx_workflow_instances_created_by', 'workflow_instances', ['created_by'])
    op.execute('CREATE INDEX idx_workflow_instances_runtime_state_gin ON workflow_instances USING GIN (runtime_state);')

    # RLS: role-based access
    op.execute("ALTER TABLE workflow_templates ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workflow_instances ENABLE ROW LEVEL SECURITY;")

    # Helper: user has a role that can access workflow templates (admin or lab roles)
    op.execute("""
        CREATE OR REPLACE FUNCTION has_workflow_template_access()
        RETURNS BOOLEAN AS $$
        DECLARE
            user_role_name TEXT;
        BEGIN
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            SELECT r.name INTO user_role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = current_user_id();
            RETURN user_role_name IN ('Administrator', 'Lab Manager', 'Lab Technician');
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute("""
        CREATE POLICY workflow_templates_access ON workflow_templates
        FOR ALL
        USING (has_workflow_template_access());
    """)

    op.execute("""
        CREATE POLICY workflow_instances_access ON workflow_instances
        FOR ALL
        USING (
            is_admin() OR created_by = current_user_id()
        );
    """)

    # Audit triggers
    op.execute("""
        CREATE TRIGGER workflow_templates_audit_timestamps
        BEFORE INSERT OR UPDATE ON workflow_templates
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER workflow_templates_update_modified_at
        BEFORE UPDATE ON workflow_templates
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_at_column();
    """)
    op.execute("""
        CREATE TRIGGER workflow_instances_audit_timestamps
        BEFORE INSERT OR UPDATE ON workflow_instances
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_timestamps();
    """)
    op.execute("""
        CREATE TRIGGER workflow_instances_update_modified_at
        BEFORE UPDATE ON workflow_instances
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_at_column();
    """)


def downgrade() -> None:
    # Drop audit triggers
    op.execute("DROP TRIGGER IF EXISTS workflow_instances_update_modified_at ON workflow_instances;")
    op.execute("DROP TRIGGER IF EXISTS workflow_instances_audit_timestamps ON workflow_instances;")
    op.execute("DROP TRIGGER IF EXISTS workflow_templates_update_modified_at ON workflow_templates;")
    op.execute("DROP TRIGGER IF EXISTS workflow_templates_audit_timestamps ON workflow_templates;")

    # Drop RLS policies and helper
    op.execute("DROP POLICY IF EXISTS workflow_instances_access ON workflow_instances;")
    op.execute("DROP POLICY IF EXISTS workflow_templates_access ON workflow_templates;")
    op.execute("DROP FUNCTION IF EXISTS has_workflow_template_access();")

    op.execute("ALTER TABLE workflow_instances DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workflow_templates DISABLE ROW LEVEL SECURITY;")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_workflow_instances_runtime_state_gin;")
    op.drop_index('idx_workflow_instances_created_by', table_name='workflow_instances')
    op.drop_index('idx_workflow_instances_status_id', table_name='workflow_instances')
    op.drop_index('idx_workflow_instances_template_id', table_name='workflow_instances')
    op.execute("DROP INDEX IF EXISTS idx_workflow_templates_template_definition_gin;")
    op.drop_index('idx_workflow_templates_active', table_name='workflow_templates')

    op.drop_table('workflow_instances')
    op.drop_table('workflow_templates')
