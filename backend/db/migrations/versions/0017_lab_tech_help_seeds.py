"""Seed Lab Technician help entries

Revision ID: 0017
Revises: 0016
Create Date: 2025-01-03 18:00:00.000000

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
    """Seed help entries for Lab Technician role."""
    connection = op.get_bind()
    
    # Lab Technician help entries based on Technical Document Section 3.1
    # and workflow-accessioning-to-reporting.md
    # Note: Using role_filter='lab-technician' slug format as requested.
    # Note: Current RLS policy matches by role name (r.name = help_entries.role_filter).
    # If slug format is used, RLS policy may need updating to support slug matching.
    lab_tech_help_entries = [
        {
            'section': 'Accessioning Workflow',
            'content': (
                'Step-by-step guide to sample accessioning:\n\n'
                '1. Enter sample details: name (unique), description, due date, '
                'received date, sample type, matrix, storage temperature, and project.\n'
                '2. Assign container: Select container type from admin-preconfigured types, '
                'enter container name/barcode (unique), set position for plate-based containers.\n'
                '3. Assign tests: Choose individual analyses or test battery. '
                'System automatically creates tests for all analyses in battery.\n'
                '4. Review and submit: Validate all information before submission.\n\n'
                'Bulk tip (US-24): Enable bulk mode for multiple samples. '
                'Enter common fields once, then unique fields per sample in table format. '
                'Auto-naming available with prefix and start number.\n\n'
                'Requires permission: sample:create'
            ),
            'role_filter': 'lab-technician'
        },
        {
            'section': 'Batch Creation',
            'content': (
                'Create batches to group samples for testing:\n\n'
                '1. Select containers: Choose containers from available samples. '
                'All samples in selected containers must share compatible analyses.\n'
                '2. Set batch details: Enter batch type (optional), start date, and notes.\n'
                '3. Validate compatibility: System checks that all samples have compatible '
                'test assignments before batch creation.\n'
                '4. QC requirements: System may require QC samples based on batch type '
                'configuration. QC samples are created automatically in the same transaction.\n\n'
                'Batch status flow: Created → In Process → Completed. '
                'Batch end_date is set automatically when all tests are complete.\n\n'
                'Requires permission: batch:create'
            ),
            'role_filter': 'lab-technician'
        },
        {
            'section': 'Results Entry',
            'content': (
                'Enter test results for samples in a batch:\n\n'
                'Single-test entry:\n'
                '1. Select batch and test from Results Management.\n'
                '2. System loads all analytes configured for the selected test.\n'
                '3. Enter results: For each sample, enter raw_result, reported_result, '
                'and qualifiers (if applicable).\n'
                '4. Save: System validates all results and creates result records.\n\n'
                'Batch results entry (US-28):\n'
                '1. Select batch from Results Management.\n'
                '2. Use tabular interface: Rows = samples, Columns = analytes.\n'
                '3. Enter results directly in table cells with real-time validation.\n'
                '4. Submit: All results saved atomically. Test status updates to "Complete" '
                'when all analytes entered. Batch status auto-updates to "Completed" when '
                'all tests are complete.\n\n'
                'Validation: Required fields, numeric ranges, significant figures. '
                'QC validation checks for missing results and out-of-range values.\n\n'
                'Requires permission: result:create'
            ),
            'role_filter': 'lab-technician'
        },
        {
            'section': 'Container Management',
            'content': (
                'Manage sample containers:\n\n'
                'Container types are pre-configured by administrators. '
                'During accessioning, select a container type and create the container instance.\n\n'
                'Container details:\n'
                '- Name/barcode: Unique identifier (required)\n'
                '- Position: Row and column for plate-based containers\n'
                '- Concentration and amount: Optional with units\n'
                '- Parent container: Optional for hierarchical relationships\n\n'
                'Containers are created dynamically during sample accessioning. '
                'Samples are always received in a container, which must be specified during accessioning.\n\n'
                'Requires permission: container:create'
            ),
            'role_filter': 'lab-technician'
        },
        {
            'section': 'Test Assignment',
            'content': (
                'Assign tests to samples during accessioning:\n\n'
                'Options:\n'
                '1. Individual analyses: Select one or more analyses from available list. '
                'Each analysis creates a separate test instance with status "In Process".\n'
                '2. Test battery: Select a pre-configured test battery. '
                'System automatically creates tests for all analyses in battery, ordered by sequence.\n'
                '3. Combined: Assign both battery and individual analyses. '
                'System prevents duplicate test creation if analysis already exists from battery.\n\n'
                'Test status flow: In Process → In Analysis → Complete\n\n'
                'After assignment, tests are ready for results entry. '
                'Tests can be viewed and managed in the Tests section.\n\n'
                'Requires permission: test:create'
            ),
            'role_filter': 'lab-technician'
        },
        {
            'section': 'Getting Started',
            'content': (
                'Welcome to NimbleLIMS! As a Lab Technician, you can:\n\n'
                '- Accession samples: Receive and register new samples with test assignments\n'
                '- Create batches: Group samples for efficient testing workflows\n'
                '- Enter results: Record test results for samples in batches\n'
                '- Manage containers: Track sample storage and location\n\n'
                'Start by accessing the Dashboard for an overview of your work. '
                'Use the navigation menu to access different sections. '
                'Each workflow requires specific permissions - contact your Lab Manager '
                'if you need additional access.\n\n'
                'For detailed instructions, see the specific help sections for each workflow.'
            ),
            'role_filter': 'lab-technician'
        }
    ]
    
    # Insert help entries with idempotency (ON CONFLICT DO NOTHING)
    # Using section + role_filter as unique identifier for conflict detection
    for entry in lab_tech_help_entries:
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
    """Remove Lab Technician help entries."""
    connection = op.get_bind()
    
    # Delete all help entries with role_filter = 'lab-technician'
    connection.execute(
        sa.text("""
            DELETE FROM help_entries
            WHERE role_filter = 'lab-technician'
        """)
    )

