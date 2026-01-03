"""Seed Lab Manager help entries

Revision ID: 0018
Revises: 0017
Create Date: 2025-01-03 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed help entries for Lab Manager role."""
    connection = op.get_bind()
    
    # Lab Manager help entries based on Technical Document Section 3.1
    # and existing 'Lab Manager' role in schema
    # Note: Using role_filter='lab-manager' slug format as requested.
    # Note: Current RLS policy matches by role name (r.name = help_entries.role_filter).
    # If slug format is used, RLS policy may need updating to support slug matching.
    lab_manager_help_entries = [
        {
            'section': 'Results Review',
            'content': (
                'Guide: Approve results, check QC. Use result:review permission. '
                'Flag issues per US-12.\n\n'
                'Review workflow:\n'
                '1. Access batch view: Navigate to Results Management and select a batch.\n'
                '2. Review test results: Check all analytes for each sample in the batch.\n'
                '3. Validate QC: Ensure QC samples meet acceptance criteria. '
                'Flag out-of-range values and missing results.\n'
                '4. Approve results: Update test status to "Complete" after review. '
                'System records review_date automatically.\n'
                '5. Flag issues: Document any anomalies or concerns per US-12 requirements. '
                'Contact technicians for clarification if needed.\n\n'
                'Quality checks:\n'
                '- Verify all required analytes have results\n'
                '- Check numeric ranges and significant figures\n'
                '- Validate qualifiers are appropriate\n'
                '- Ensure batch status progression: Created → In Process → Completed\n\n'
                'Requires permission: result:review'
            ),
            'role_filter': 'lab-manager'
        },
        {
            'section': 'Batch Management',
            'content': (
                'Oversee batch operations and workflow:\n\n'
                'Batch oversight:\n'
                '1. Monitor batch status: Track batches from creation through completion. '
                'View all batches with filtering by status, type, and date range.\n'
                '2. Review batch composition: Check container assignments and sample compatibility. '
                'Ensure all samples in a batch have compatible test assignments.\n'
                '3. Manage batch lifecycle: Update batch status as needed. '
                'Status flow: Created → In Process → Completed.\n'
                '4. Batch end_date: Automatically set when all tests are complete, '
                'but can be manually adjusted if needed.\n\n'
                'QC oversight:\n'
                '- Verify QC samples are included when required by batch type\n'
                '- Review QC results during results review process\n'
                '- Ensure compliance with quality standards\n\n'
                'Batch operations:\n'
                '- Add or remove containers from batches (before testing begins)\n'
                '- Update batch notes and metadata\n'
                '- View batch history and audit trail\n\n'
                'Requires permission: batch:manage'
            ),
            'role_filter': 'lab-manager'
        },
        {
            'section': 'Project Management',
            'content': (
                'Manage projects and client relationships:\n\n'
                'Project oversight:\n'
                '1. View all projects: Access project list with filtering by client, '
                'status, and date range.\n'
                '2. Monitor project status: Track projects through lifecycle. '
                'Status values managed via lists configuration.\n'
                '3. Review project samples: Access all samples associated with a project '
                'to monitor progress and completion.\n'
                '4. Client project coordination: Link projects to client projects for '
                'billing and reporting purposes.\n\n'
                'Project operations:\n'
                '- Update project status and metadata\n'
                '- Assign users to projects with appropriate access levels\n'
                '- Review project timeline and deadlines\n'
                '- Monitor sample accessioning and testing progress\n\n'
                'Client relationships:\n'
                '- Coordinate with clients on project requirements\n'
                '- Ensure proper data isolation per client\n'
                '- Review client project associations\n\n'
                'Requires permission: project:manage'
            ),
            'role_filter': 'lab-manager'
        },
        {
            'section': 'Quality Control',
            'content': (
                'Ensure quality standards and compliance:\n\n'
                'QC responsibilities:\n'
                '1. Review QC samples: Verify QC samples are created for batches '
                'when required by batch type configuration.\n'
                '2. Validate QC results: Check that QC results meet acceptance criteria. '
                'Flag out-of-range values and investigate anomalies.\n'
                '3. Monitor test accuracy: Review results for consistency and accuracy. '
                'Ensure proper use of qualifiers and units.\n'
                '4. Compliance checks: Verify adherence to US-12 requirements for '
                'issue flagging and documentation.\n\n'
                'Quality monitoring:\n'
                '- Track QC sample performance over time\n'
                '- Identify trends and potential issues\n'
                '- Ensure proper documentation of exceptions\n'
                '- Coordinate with technicians on quality concerns\n\n'
                'Issue management:\n'
                '- Flag results that require investigation\n'
                '- Document quality issues per US-12\n'
                '- Follow up on flagged items until resolution\n'
                '- Maintain audit trail of quality actions\n\n'
                'Requires permission: result:review'
            ),
            'role_filter': 'lab-manager'
        },
        {
            'section': 'Test Assignment Oversight',
            'content': (
                'Oversee test assignments and configurations:\n\n'
                'Assignment oversight:\n'
                '1. Review test assignments: Monitor which tests are assigned to samples '
                'during accessioning. Ensure appropriate analyses and batteries are used.\n'
                '2. Validate test configurations: Verify that test assignments align with '
                'project requirements and client specifications.\n'
                '3. Monitor test status: Track tests through workflow: '
                'In Process → In Analysis → Complete.\n'
                '4. Coordinate with technicians: Provide guidance on test assignment '
                'decisions and resolve assignment questions.\n\n'
                'Test battery management:\n'
                '- Review use of pre-configured test batteries\n'
                '- Ensure batteries are applied correctly to appropriate sample types\n'
                '- Verify battery sequences and optional flags are respected\n\n'
                'Analysis oversight:\n'
                '- Monitor which analyses are most frequently used\n'
                '- Ensure proper analyte configurations for analyses\n'
                '- Coordinate with administrators on analysis configuration needs\n\n'
                'Requires permission: test:assign'
            ),
            'role_filter': 'lab-manager'
        },
        {
            'section': 'Getting Started',
            'content': (
                'Welcome to NimbleLIMS! As a Lab Manager, you oversee laboratory operations:\n\n'
                'Key responsibilities:\n'
                '- Review and approve results: Ensure quality and accuracy of test results\n'
                '- Manage batches: Oversee batch workflows and monitor progress\n'
                '- Project management: Coordinate projects and client relationships\n'
                '- Quality control: Maintain quality standards and compliance\n'
                '- Test oversight: Monitor test assignments and configurations\n\n'
                'Start by accessing the Dashboard for an overview of laboratory operations. '
                'Use the navigation menu to access different sections. '
                'Review pending results in Results Management, monitor active batches, '
                'and track project progress.\n\n'
                'For detailed instructions, see the specific help sections for each workflow. '
                'Contact your Administrator if you need additional permissions or access.'
            ),
            'role_filter': 'lab-manager'
        }
    ]
    
    # Insert help entries with idempotency (ON CONFLICT DO NOTHING)
    # Using section + role_filter as unique identifier for conflict detection
    for entry in lab_manager_help_entries:
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
    """Remove Lab Manager help entries."""
    connection = op.get_bind()
    
    # Delete all help entries with role_filter = 'lab-manager'
    connection.execute(
        sa.text("""
            DELETE FROM help_entries
            WHERE role_filter = 'lab-manager'
        """)
    )

