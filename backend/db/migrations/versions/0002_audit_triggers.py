"""Add audit triggers

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create function to update modified_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_modified_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.modified_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create function to set created_at and modified_at
    op.execute("""
        CREATE OR REPLACE FUNCTION set_audit_timestamps()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                NEW.created_at = NOW();
                NEW.modified_at = NOW();
            ELSIF TG_OP = 'UPDATE' THEN
                NEW.modified_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply triggers to all tables with audit fields
    tables_with_audit = [
        'lists', 'list_entries', 'roles', 'permissions', 'clients', 'users',
        'locations', 'people', 'projects', 'units', 'container_types', 'containers',
        'samples', 'analyses', 'analytes', 'tests', 'results', 'batches'
    ]
    
    for table in tables_with_audit:
        # Trigger for INSERT and UPDATE
        op.execute(f"""
            CREATE TRIGGER {table}_audit_timestamps
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_audit_timestamps();
        """)
        
        # Trigger for UPDATE only (for modified_at)
        op.execute(f"""
            CREATE TRIGGER {table}_update_modified_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_modified_at_column();
        """)


def downgrade() -> None:
    # Drop triggers
    tables_with_audit = [
        'lists', 'list_entries', 'roles', 'permissions', 'clients', 'users',
        'locations', 'people', 'projects', 'units', 'container_types', 'containers',
        'samples', 'analyses', 'analytes', 'tests', 'results', 'batches'
    ]
    
    for table in tables_with_audit:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_audit_timestamps ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table};")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_modified_at_column();")
    op.execute("DROP FUNCTION IF EXISTS set_audit_timestamps();")
