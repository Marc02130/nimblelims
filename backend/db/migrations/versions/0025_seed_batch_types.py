"""Seed batch types list and entries

Revision ID: 0025
Revises: 0024
Create Date: 2026-01-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0025'
down_revision = '0024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add batch types list and seed entries."""
    connection = op.get_bind()
    
    # Check if batch_types list already exists (normalized name from migration 0007)
    list_result = connection.execute(
        sa.text("""
            SELECT id FROM lists 
            WHERE name = 'batch_types' OR name = 'Batch Types'
        """)
    ).fetchone()
    
    if list_result:
        list_id = list_result[0]
    else:
        # Create batch_types list with normalized name (migration 0007 normalizes to lowercase slug)
        list_id = 'aaaaaaaa-0000-0000-0000-000000000001'
        connection.execute(
            sa.text("""
                INSERT INTO lists (id, name, description, active, created_at, modified_at)
                VALUES (:id, 'batch_types', 'Batch type values for categorizing batches', true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {'id': list_id}
        )
    
    # Insert batch type entries
    batch_types = [
        {
            'name': 'Preparation',
            'description': 'For initial sample handling steps like homogenization or aliquoting. QC often required: blanks, duplicates.',
            'short_name': 'Prep'
        },
        {
            'name': 'Extraction',
            'description': 'For solvent-based extractions (e.g., EPA methods). QC: matrix spikes, surrogates.',
            'short_name': None
        },
        {
            'name': 'Cleanup',
            'description': 'For post-extraction purification (e.g., column cleanup). QC: blanks.',
            'short_name': None
        },
        {
            'name': 'Analysis',
            'description': 'For instrument runs (e.g., GC-MS, HPLC). QC: calibration checks, controls.',
            'short_name': None
        },
        {
            'name': 'Screening',
            'description': 'For preliminary tests (e.g., qualitative checks). Minimal QC.',
            'short_name': None
        },
        {
            'name': 'Confirmation',
            'description': 'For secondary verification tests. QC: duplicates.',
            'short_name': None
        },
        {
            'name': 'QC Only',
            'description': 'For batches dedicated to quality control samples. No standard samples; all QC.',
            'short_name': None
        },
        {
            'name': 'Custom',
            'description': 'A catch-all for lab-specific processes (admins can rename/refine).',
            'short_name': None
        },
    ]
    
    for batch_type in batch_types:
        connection.execute(
            sa.text("""
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO UPDATE
                SET description = EXCLUDED.description, modified_at = NOW()
            """),
            {
                'name': batch_type['name'],
                'description': batch_type['description'],
                'list_id': list_id
            }
        )


def downgrade() -> None:
    """Remove batch types entries and list."""
    connection = op.get_bind()
    
    # Find batch_types list
    list_result = connection.execute(
        sa.text("""
            SELECT id FROM lists 
            WHERE name = 'batch_types' OR name = 'Batch Types'
        """)
    ).fetchone()
    
    if list_result:
        list_id = list_result[0]
        # Delete entries
        connection.execute(
            sa.text("DELETE FROM list_entries WHERE list_id = :list_id"),
            {'list_id': list_id}
        )
        # Optionally delete the list (commented out to preserve structure)
        # connection.execute(
        #     sa.text("DELETE FROM lists WHERE id = :list_id"),
        #     {'list_id': list_id}
        # )
