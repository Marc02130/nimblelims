"""Seed Administrator help entries

Revision ID: 0017
Revises: 0016
Create Date: 2025-01-03 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed help entries for Administrator role."""
    connection = op.get_bind()
    
    # Administrator help entries based on Technical Document (Section 3.1)
    # and existing 'Administrator' role in schema_dump20260103.sql
    # Note: Using role_filter='administrator' slug format as requested.
    # Note: Current RLS policy matches by role name (r.name = help_entries.role_filter).
    # If slug format is used, RLS policy may need updating to support slug matching.
    admin_help_entries = [
        {
            'section': 'User Management',
            'content': (
                'Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). '
                'Use admin UI for configs.\n\n'
                'User operations:\n'
                '1. Create users: Navigate to Users Management. Enter username, email, name, '
                'and assign role. Set password or enable password reset.\n'
                '2. Edit users: Update user details, change roles, modify permissions. '
                'Users can be activated or deactivated.\n'
                '3. Assign roles: Select appropriate role for each user. Roles determine '
                'default permissions and access levels.\n'
                '4. Client assignment: For Client role users, assign to specific client '
                'for data isolation.\n\n'
                'Role management:\n'
                '- Create custom roles: Define new roles with specific permission sets\n'
                '- Edit roles: Modify role permissions and descriptions\n'
                '- Permission assignment: Assign permissions to roles using '
                'role:manage permission\n'
                '- View role permissions: Review which permissions are assigned to each role\n\n'
                'Permissions:\n'
                '- user:manage: Required for user CRUD operations\n'
                '- role:manage: Required for role and permission management\n'
                '- config:edit: Required for system configuration changes\n\n'
                'Best practices:\n'
                '- Use strong passwords and enable password policies\n'
                '- Assign minimal required permissions (principle of least privilege)\n'
                '- Regularly review user access and deactivate unused accounts\n'
                '- Document role changes and permission modifications'
            ),
            'role_filter': 'administrator'
        },
        {
            'section': 'EAV Configuration',
            'content': (
                'Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\n'
                'EAV overview:\n'
                'The EAV model enables administrators to define custom attributes for various '
                'entity types without schema changes, providing flexibility for '
                'laboratory-specific requirements.\n\n'
                'Custom attributes configuration:\n'
                '1. Access EAV config: Navigate to Custom Attributes Management in admin UI.\n'
                '2. Create attribute: Define attribute name, entity type (sample, test, etc.), '
                'data type (text, number, date, boolean), and validation rules.\n'
                '3. Set visibility: Configure which roles can view and edit custom attributes.\n'
                '4. Define defaults: Set default values and required flags as needed.\n\n'
                'Entity types supported:\n'
                '- Samples: Custom fields for sample metadata\n'
                '- Tests: Additional test configuration attributes\n'
                '- Results: Extended result data fields\n'
                '- Projects: Project-specific custom attributes\n\n'
                'EAV editing:\n'
                '- Edit existing attributes: Modify data types, validation, and visibility\n'
                '- Deactivate attributes: Disable without deleting to preserve historical data\n'
                '- View attribute usage: See where custom attributes are used across entities\n'
                '- Export/import: Backup and restore custom attribute configurations\n\n'
                'Data management:\n'
                '- Custom attribute values are stored in EAV tables\n'
                '- Values are queryable and filterable in admin UI\n'
                '- Historical values are preserved for audit purposes\n'
                '- Bulk updates supported for custom attribute values\n\n'
                'Requires permission: config:edit'
            ),
            'role_filter': 'administrator'
        },
        {
            'section': 'Row Level Security (RLS)',
            'content': (
                'Manage Row Level Security policies for data isolation:\n\n'
                'RLS overview:\n'
                'Row Level Security (RLS) ensures users can only access data they are '
                'authorized to view. Policies are enforced at the database level for '
                'comprehensive security.\n\n'
                'RLS policy management:\n'
                '1. Review policies: Check existing RLS policies on tables (samples, results, '
                'projects, etc.). Policies are defined in database migrations.\n'
                '2. Policy structure: Policies use USING clauses to filter rows based on '
                'user role, project access, and client assignments.\n'
                '3. Admin bypass: Administrator role bypasses RLS restrictions to access '
                'all data for system administration.\n'
                '4. Client isolation: Client users see only data associated with their '
                'assigned client_id.\n\n'
                'Data isolation:\n'
                '- Project-based: Users see samples/projects they are assigned to\n'
                '- Client-based: Client users see only their client\'s data\n'
                '- Role-based: Different roles have different access levels\n'
                '- Cross-project access: Lab Managers can access multiple projects\n\n'
                'Policy configuration:\n'
                '- Policies are created via Alembic migrations\n'
                '- Use current_user_id() function to identify current user\n'
                '- Use is_admin() function to check administrator status\n'
                '- Policies apply to SELECT, INSERT, UPDATE, DELETE operations\n\n'
                'Testing RLS:\n'
                '- Verify policies work correctly for each role\n'
                '- Test data isolation between clients\n'
                '- Ensure administrators can access all data\n'
                '- Validate project-based access restrictions\n\n'
                'Requires permission: config:edit (for policy modifications)'
            ),
            'role_filter': 'administrator'
        },
        {
            'section': 'System Configuration',
            'content': (
                'Manage system-wide configurations and settings:\n\n'
                'Configuration areas:\n'
                '1. Container types: Define container types available for sample storage. '
                'Configure dimensions, capacity, and position support (for plates).\n'
                '2. Analyses: Create and configure analyses with associated analytes. '
                'Set units, significant figures, and validation rules.\n'
                '3. Test batteries: Define test batteries with ordered analyses. '
                'Configure optional flags and sequences.\n'
                '4. Lists: Manage list values for status fields, sample types, matrices, '
                'and other enumerated fields.\n'
                '5. Units: Configure measurement units and conversion factors.\n\n'
                'Container type management:\n'
                '- Create container types: Define new container types with specifications\n'
                '- Edit types: Modify container properties and requirements\n'
                '- Position support: Enable row/column positions for plate-based containers\n'
                '- Capacity settings: Configure maximum samples per container\n\n'
                'Analysis configuration:\n'
                '- Create analyses: Define new analyses with name and description\n'
                '- Configure analytes: Add analytes to analyses with units and validation\n'
                '- Set defaults: Configure default values and required flags\n'
                '- Validation rules: Define numeric ranges and format requirements\n\n'
                'Test battery setup:\n'
                '- Create batteries: Define test batteries with multiple analyses\n'
                '- Set sequence: Order analyses within battery\n'
                '- Optional flags: Mark analyses as optional in battery\n'
                '- Usage tracking: Monitor which batteries are used most frequently\n\n'
                'List management:\n'
                '- Create lists: Define new list types (status, sample_type, etc.)\n'
                '- Add values: Populate lists with allowed values\n'
                '- Edit values: Modify existing list entries\n'
                '- Deactivate: Remove values without deleting (preserve historical data)\n\n'
                'Requires permission: config:edit'
            ),
            'role_filter': 'administrator'
        },
        {
            'section': 'Data Management',
            'content': (
                'Oversee data operations and system maintenance:\n\n'
                'Data oversight:\n'
                '1. View all data: As administrator, access all samples, tests, results, '
                'and projects regardless of RLS restrictions.\n'
                '2. Audit trails: Review created_at, modified_at, created_by, and '
                'modified_by fields for all entities.\n'
                '3. Data integrity: Monitor referential integrity and foreign key '
                'relationships.\n'
                '4. Bulk operations: Perform bulk updates and data migrations as needed.\n\n'
                'Project management:\n'
                '- Create projects: Set up new projects with client associations\n'
                '- Assign users: Add users to projects with appropriate access\n'
                '- Monitor progress: Track sample accessioning and testing progress\n'
                '- Update status: Modify project status and metadata\n\n'
                'Batch oversight:\n'
                '- View all batches: Access batches across all projects\n'
                '- Monitor status: Track batch progression and completion\n'
                '- Review results: Access all results for quality assurance\n'
                '- Resolve issues: Address batch-related problems and errors\n\n'
                'User activity:\n'
                '- Monitor logins: Review last_login timestamps\n'
                '- Track changes: View audit trails for user actions\n'
                '- Identify issues: Detect unusual patterns or errors\n'
                '- Support users: Assist with access and permission issues\n\n'
                'System maintenance:\n'
                '- Database migrations: Run Alembic migrations for schema updates\n'
                '- Backup operations: Coordinate database backups and restores\n'
                '- Performance monitoring: Review query performance and indexes\n'
                '- Log analysis: Review application logs for errors and warnings\n\n'
                'Requires permission: All permissions (administrator role)'
            ),
            'role_filter': 'administrator'
        },
        {
            'section': 'Getting Started',
            'content': (
                'Welcome to NimbleLIMS! As an Administrator, you manage the entire system:\n\n'
                'Key responsibilities:\n'
                '- User and role management: Create users, assign roles, configure permissions\n'
                '- System configuration: Set up container types, analyses, test batteries, lists\n'
                '- EAV configuration: Define custom attributes for flexible data modeling\n'
                '- RLS oversight: Ensure proper data isolation and security policies\n'
                '- Data management: Oversee all projects, samples, tests, and results\n'
                '- System maintenance: Perform migrations, backups, and monitoring\n\n'
                'Start by accessing the Admin Dashboard for system overview. '
                'Use the navigation menu to access different administration sections:\n'
                '- Users Management: Create and manage users and roles\n'
                '- Custom Attributes: Configure EAV custom attributes\n'
                '- System Configuration: Manage analyses, batteries, containers, lists\n'
                '- Data Views: Access all data across projects and clients\n\n'
                'Permissions:\n'
                'As Administrator, you have all permissions (17 total):\n'
                '- Sample operations: sample:create, sample:read, sample:update, sample:delete\n'
                '- Test operations: test:assign, test:update\n'
                '- Result operations: result:enter, result:review, result:read, '
                'result:update, result:delete\n'
                '- Batch operations: batch:manage, batch:read, batch:update, batch:delete\n'
                '- Project operations: project:manage, project:read\n'
                '- System operations: user:manage, role:manage, config:edit\n\n'
                'For detailed instructions, see the specific help sections for each area. '
                'Contact system support if you need assistance with advanced configurations.'
            ),
            'role_filter': 'administrator'
        }
    ]
    
    # Insert help entries with idempotency (ON CONFLICT DO NOTHING)
    # Using section + role_filter as unique identifier for conflict detection
    for entry in admin_help_entries:
        # Set name and description from section for BaseModel compatibility
        entry_with_base = {
            'name': entry['section'],  # Use section as name
            'description': entry['content'][:255] if len(entry['content']) > 255 else entry['content'],  # Truncate for description
            **entry
        }
        
        # Insert with idempotency: check if entry already exists
        # Using WHERE NOT EXISTS since there's no unique constraint on (section, role_filter)
        # ON CONFLICT DO NOTHING included as safety net (requires unique constraint to trigger)
        connection.execute(
            sa.text("""
                INSERT INTO help_entries (name, description, section, content, role_filter, active, created_at, modified_at)
                SELECT :name, :description, :section, :content, :role_filter, true, NOW(), NOW()
                WHERE NOT EXISTS (
                    SELECT 1 FROM help_entries
                    WHERE section = :section AND role_filter = :role_filter
                )
                ON CONFLICT DO NOTHING
            """),
            entry_with_base
        )


def downgrade() -> None:
    """Remove Administrator help entries."""
    connection = op.get_bind()
    
    # Delete all help entries with role_filter = 'administrator'
    connection.execute(
        sa.text("""
            DELETE FROM help_entries
            WHERE role_filter = 'administrator'
        """)
    )

