"""Add database indexes for performance

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-01 00:04:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Indexes on foreign keys for better join performance
    foreign_key_indexes = [
        # User-related indexes
        ('users', 'role_id'),
        ('users', 'client_id'),
        
        # Project-related indexes
        ('projects', 'client_id'),
        ('projects', 'status'),
        ('project_users', 'project_id'),
        ('project_users', 'user_id'),
        
        # Sample-related indexes
        ('samples', 'project_id'),
        ('samples', 'sample_type'),
        ('samples', 'status'),
        ('samples', 'matrix'),
        ('samples', 'qc_type'),
        ('samples', 'parent_sample_id'),
        
        # Container-related indexes
        ('containers', 'type_id'),
        ('containers', 'parent_container_id'),
        ('containers', 'concentration_units'),
        ('containers', 'amount_units'),
        ('contents', 'container_id'),
        ('contents', 'sample_id'),
        ('contents', 'concentration_units'),
        ('contents', 'amount_units'),
        
        # Test-related indexes
        ('tests', 'sample_id'),
        ('tests', 'analysis_id'),
        ('tests', 'status'),
        ('tests', 'technician_id'),
        
        # Result-related indexes
        ('results', 'test_id'),
        ('results', 'analyte_id'),
        ('results', 'entered_by'),
        ('results', 'qualifiers'),
        
        # Batch-related indexes
        ('batches', 'status'),
        ('batches', 'type'),
        ('batch_containers', 'batch_id'),
        ('batch_containers', 'container_id'),
        
        # Analysis-related indexes
        ('analysis_analytes', 'analysis_id'),
        ('analysis_analytes', 'analyte_id'),
        ('analysis_analytes', 'list_id'),
        
        # List-related indexes
        ('list_entries', 'list_id'),
        ('units', 'type'),
        
        # Location-related indexes
        ('locations', 'client_id'),
        ('locations', 'type'),
        ('people_locations', 'person_id'),
        ('people_locations', 'location_id'),
        ('contact_methods', 'person_id'),
        ('contact_methods', 'type'),
        
        # Audit field indexes
        ('users', 'created_by'),
        ('users', 'modified_by'),
        ('samples', 'created_by'),
        ('samples', 'modified_by'),
        ('tests', 'created_by'),
        ('tests', 'modified_by'),
        ('results', 'created_by'),
        ('results', 'modified_by'),
    ]
    
    for table, column in foreign_key_indexes:
        index_name = f"idx_{table}_{column}"
        op.create_index(index_name, table, [column])
    
    # Composite indexes for common query patterns
    composite_indexes = [
        # Sample queries by project and status
        ('samples', ['project_id', 'status']),
        ('samples', ['project_id', 'sample_type']),
        ('samples', ['project_id', 'qc_type']),
        
        # Test queries by sample and status
        ('tests', ['sample_id', 'status']),
        ('tests', ['analysis_id', 'status']),
        
        # Result queries by test and analyte
        ('results', ['test_id', 'analyte_id']),
        
        # Batch queries by status and type
        ('batches', ['status', 'type']),
        
        # Container queries by type and parent
        ('containers', ['type_id', 'parent_container_id']),
        
        # Project queries by client and status
        ('projects', ['client_id', 'status']),
        
        # User queries by role and client
        ('users', ['role_id', 'client_id']),
    ]
    
    for table, columns in composite_indexes:
        index_name = f"idx_{table}_{'_'.join(columns)}"
        op.create_index(index_name, table, columns)
    
    # Unique indexes (already handled by unique constraints, but adding for completeness)
    unique_indexes = [
        ('users', 'username'),
        ('users', 'email'),
        ('clients', 'name'),
        ('projects', 'name'),
        ('samples', 'name'),
        ('containers', 'name'),
        ('analyses', 'name'),
        ('analytes', 'name'),
        ('batches', 'name'),
        ('lists', 'name'),
        ('list_entries', 'name'),
        ('units', 'name'),
    ]
    
    for table, column in unique_indexes:
        index_name = f"idx_{table}_{column}_unique"
        op.create_index(index_name, table, [column], unique=True)
    
    # Partial indexes for active records
    partial_indexes = [
        ('samples', 'project_id', 'active = true'),
        ('tests', 'sample_id', 'active = true'),
        ('results', 'test_id', 'active = true'),
        ('batches', 'status', 'active = true'),
        ('containers', 'type_id', 'active = true'),
    ]
    
    for table, column, condition in partial_indexes:
        index_name = f"idx_{table}_{column}_active"
        op.execute(f"CREATE INDEX {index_name} ON {table} ({column}) WHERE {condition}")


def downgrade() -> None:
    # Drop all indexes
    connection = op.get_bind()
    
    # Get all indexes for our tables
    tables = [
        'users', 'roles', 'permissions', 'clients', 'projects', 'project_users',
        'samples', 'containers', 'contents', 'container_types', 'analyses',
        'analytes', 'analysis_analytes', 'tests', 'results', 'batches',
        'batch_containers', 'lists', 'list_entries', 'units', 'locations',
        'people', 'people_locations', 'contact_methods'
    ]
    
    for table in tables:
        # Get indexes for this table
        result = connection.execute(sa.text(f"""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = '{table}' 
            AND indexname LIKE 'idx_%'
        """)).fetchall()
        
        for (index_name,) in result:
            op.drop_index(index_name, table_name=table)
