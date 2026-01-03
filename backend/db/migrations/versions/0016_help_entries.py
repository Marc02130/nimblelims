"""Add help_entries table for role-filtered help content

Revision ID: 0016
Revises: 0015
Create Date: 2025-01-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create help_entries table
    # Note: name column is NOT unique (unlike other BaseModel tables) since help entries can share sections
    op.create_table('help_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),  # Required by BaseModel, will use section value (not unique)
        sa.Column('description', sa.Text, nullable=True),  # Required by BaseModel
        sa.Column('section', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('role_filter', sa.String(255), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        # Note: No unique constraint on name - help entries can have same section/name
    )
    
    # Create indexes
    op.create_index('idx_help_entries_section', 'help_entries', ['section'])
    op.create_index('idx_help_entries_role_filter', 'help_entries', ['role_filter'])
    op.create_index('idx_help_entries_active', 'help_entries', ['active'])
    
    # Enable RLS on help_entries table
    op.execute("ALTER TABLE help_entries ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policy for help_entries
    # Users see entries where role_filter matches their role OR role_filter is NULL (public)
    # Admins can see all active entries
    op.execute("""
        CREATE POLICY help_entries_access ON help_entries
        FOR ALL
        USING (
            active = true
            AND (
                is_admin()
                OR role_filter IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM users u
                    JOIN roles r ON u.role_id = r.id
                    WHERE u.id = current_user_id()
                    AND r.name = help_entries.role_filter
                )
            )
        );
    """)
    
    # Seed initial help entries for Client role
    connection = op.get_bind()
    
    # Get Client role ID for seeding
    client_role_result = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'Client'")
    ).fetchone()
    
    if client_role_result:
        # Seed Client help entries
        client_help_entries = [
            {
                'section': 'Viewing Projects',
                'content': 'Step-by-step guide to access your samples and results. Navigate to the Projects section to view all projects associated with your client account. Click on a project to see detailed information including samples, tests, and results.',
                'role_filter': 'Client'
            },
            {
                'section': 'Viewing Samples',
                'content': 'Learn how to view and filter your samples. In the Samples section, you can see all samples associated with your projects. Use the filters to search by sample name, status, or date range. Click on a sample to view detailed information including test assignments and results.',
                'role_filter': 'Client'
            },
            {
                'section': 'Viewing Results',
                'content': 'Understand how to access and interpret your test results. Results are organized by test and sample. Navigate to the Results section to view all completed tests. Each result shows the analyte name, value, units, and any qualifiers. Results are automatically updated as tests are completed.',
                'role_filter': 'Client'
            },
            {
                'section': 'Getting Started',
                'content': 'Welcome to NimbleLIMS! This system allows you to view your laboratory samples, tests, and results. Start by exploring the Dashboard to see an overview of your projects and samples. Use the navigation menu to access different sections of the system.',
                'role_filter': None  # Public help
            }
        ]
        
        for entry in client_help_entries:
            # Set name and description from section for BaseModel compatibility
            entry_with_base = {
                'name': entry['section'],  # Use section as name
                'description': entry['content'][:255] if len(entry['content']) > 255 else entry['content'],  # Truncate for description
                **entry
            }
            connection.execute(
                sa.text("""
                    INSERT INTO help_entries (name, description, section, content, role_filter, active, created_at, modified_at)
                    VALUES (:name, :description, :section, :content, :role_filter, true, NOW(), NOW())
                """),
                entry_with_base
            )


def downgrade() -> None:
    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS help_entries_access ON help_entries;")
    
    # Disable RLS
    op.execute("ALTER TABLE help_entries DISABLE ROW LEVEL SECURITY;")
    
    # Drop indexes
    op.drop_index('idx_help_entries_active', table_name='help_entries')
    op.drop_index('idx_help_entries_role_filter', table_name='help_entries')
    op.drop_index('idx_help_entries_section', table_name='help_entries')
    
    # Drop table (unique constraint will be dropped with table)
    op.drop_table('help_entries')

