"""Normalize list names to lowercase slug format

Revision ID: 0007
Revises: 0006
Create Date: 2024-12-21 18:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import re

# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def normalize_to_slug(name: str) -> str:
    """Convert a name to lowercase slug format with underscores."""
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and hyphens with underscores
    slug = re.sub(r'[\s\-]+', '_', slug)
    # Remove any other non-alphanumeric characters except underscores
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    # Remove multiple consecutive underscores
    slug = re.sub(r'_+', '_', slug)
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    return slug


def upgrade() -> None:
    """Normalize all list names to lowercase slug format."""
    connection = op.get_bind()
    
    # Get all lists
    result = connection.execute(sa.text("SELECT id, name FROM lists WHERE active = true"))
    lists = result.fetchall()
    
    # Mapping of old names to new names
    name_mapping = {}
    for list_id, old_name in lists:
        new_name = normalize_to_slug(old_name)
        if new_name != old_name:
            name_mapping[old_name] = new_name
            # Update the list name
            connection.execute(
                sa.text("UPDATE lists SET name = :new_name WHERE id = :id"),
                {"new_name": new_name, "id": list_id}
            )
    
    # Log the changes
    if name_mapping:
        print(f"Normalized {len(name_mapping)} list names:")
        for old, new in name_mapping.items():
            print(f"  '{old}' -> '{new}'")


def downgrade() -> None:
    """Revert list names back to original format."""
    connection = op.get_bind()
    
    # Mapping of normalized names back to original names
    # This is the reverse mapping from upgrade()
    reverse_mapping = {
        'sample_status': 'Sample Status',
        'test_status': 'Test Status',
        'project_status': 'Project Status',
        'batch_status': 'Batch Status',
        'sample_types': 'Sample Types',
        'matrix_types': 'Matrix Types',
        'qc_types': 'QC Types',
        'unit_types': 'Unit Types',
        'contact_types': 'Contact Types',
    }
    
    for normalized_name, original_name in reverse_mapping.items():
        connection.execute(
            sa.text("UPDATE lists SET name = :original_name WHERE name = :normalized_name"),
            {"original_name": original_name, "normalized_name": normalized_name}
        )

