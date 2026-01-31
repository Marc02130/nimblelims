"""Add edit support indexes and ensure test:update permission

Revision ID: 0018
Revises: 0017
Create Date: 2025-01-03 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for efficient editing and seed test:update permission."""
    connection = op.get_bind()
    
    # Create indexes on modified_at and modified_by for samples, tests, containers
    # These indexes support efficient queries for edit operations and audit trails
    # Using IF NOT EXISTS for idempotency (indexes may have been created in previous migrations)
    
    # Indexes for samples table
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_samples_modified_at ON samples (modified_at)")
    )
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_samples_modified_by ON samples (modified_by)")
    )
    
    # Indexes for tests table
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_tests_modified_at ON tests (modified_at)")
    )
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_tests_modified_by ON tests (modified_by)")
    )
    
    # Indexes for containers table
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_containers_modified_at ON containers (modified_at)")
    )
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_containers_modified_by ON containers (modified_by)")
    )
    
    # Seed test:update permission if missing (idempotent)
    # Using ON CONFLICT DO NOTHING for idempotency
    # Permission ID from 0004_initial_data.py: 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1'
    connection.execute(
        sa.text("""
            INSERT INTO permissions (id, name, description, active, created_at, modified_at)
            VALUES (
                'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
                'test:update',
                'Update existing tests',
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """)
    )


def downgrade() -> None:
    """Remove edit support indexes."""
    connection = op.get_bind()
    
    # Drop indexes in reverse order using IF EXISTS for safety
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_containers_modified_by")
    )
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_containers_modified_at")
    )
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_tests_modified_by")
    )
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_tests_modified_at")
    )
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_samples_modified_by")
    )
    connection.execute(
        sa.text("DROP INDEX IF EXISTS idx_samples_modified_at")
    )
    
    # Note: We do not remove the test:update permission in downgrade
    # as it may have been added in 0004_initial_data.py and removing it
    # could break existing role-permission mappings

