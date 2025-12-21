"""Sprint 2 features: aliquots, derivatives, pooling, results, batches

Revision ID: 0006
Revises: 0005
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing tables to match new model structure
    
    # Update batches table - add missing relationships
    op.alter_column('batches', 'type', nullable=True)
    op.alter_column('batches', 'status', nullable=False)
    op.alter_column('batches', 'start_date', nullable=True)
    op.alter_column('batches', 'end_date', nullable=True)
    
    # Update batch_containers table - add missing relationships
    op.alter_column('batch_containers', 'position', nullable=True)
    op.alter_column('batch_containers', 'notes', nullable=True)
    
    # Update results table - add missing relationships
    op.alter_column('results', 'raw_result', nullable=True)
    op.alter_column('results', 'reported_result', nullable=True)
    op.alter_column('results', 'qualifiers', nullable=True)
    op.alter_column('results', 'calculated_result', nullable=True)
    op.alter_column('results', 'entry_date', nullable=False)
    op.alter_column('results', 'entered_by', nullable=False)
    
    # Update analysis_analytes table - add missing relationships
    op.alter_column('analysis_analytes', 'data_type', nullable=True)
    op.alter_column('analysis_analytes', 'list_id', nullable=True)
    op.alter_column('analysis_analytes', 'high_value', nullable=True)
    op.alter_column('analysis_analytes', 'low_value', nullable=True)
    op.alter_column('analysis_analytes', 'significant_figures', nullable=True)
    op.alter_column('analysis_analytes', 'calculation', nullable=True)
    op.alter_column('analysis_analytes', 'reported_name', nullable=True)
    op.alter_column('analysis_analytes', 'display_order', nullable=True)
    op.alter_column('analysis_analytes', 'is_required', nullable=False, server_default='false')
    op.alter_column('analysis_analytes', 'default_value', nullable=True)
    
    # Update containers table - add missing relationships
    op.alter_column('containers', 'concentration', nullable=True)
    op.alter_column('containers', 'concentration_units', nullable=True)
    op.alter_column('containers', 'amount', nullable=True)
    op.alter_column('containers', 'amount_units', nullable=True)
    
    # Update contents table - add missing relationships
    op.alter_column('contents', 'concentration', nullable=True)
    op.alter_column('contents', 'concentration_units', nullable=True)
    op.alter_column('contents', 'amount', nullable=True)
    op.alter_column('contents', 'amount_units', nullable=True)
    
    # Update analyses table - add missing relationships
    op.alter_column('analyses', 'method', nullable=True)
    op.alter_column('analyses', 'turnaround_time', nullable=True)
    op.alter_column('analyses', 'cost', nullable=True)
    
    # Add new permissions for Sprint 2 features
    op.execute("""
        INSERT INTO permissions (id, name, description, active, created_at, modified_at)
        VALUES 
        (gen_random_uuid(), 'result:update', 'Update results', true, NOW(), NOW()),
        (gen_random_uuid(), 'result:delete', 'Delete results', true, NOW(), NOW()),
        (gen_random_uuid(), 'batch:update', 'Update batches', true, NOW(), NOW()),
        (gen_random_uuid(), 'batch:delete', 'Delete batches', true, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    # Remove new permissions
    op.execute("""
        DELETE FROM permissions 
        WHERE name IN ('result:update', 'result:delete', 'batch:update', 'batch:delete');
    """)
    
    # Revert table changes
    op.alter_column('analysis_analytes', 'default_value', nullable=False)
    op.alter_column('analysis_analytes', 'is_required', nullable=True)
    op.alter_column('analysis_analytes', 'display_order', nullable=False)
    op.alter_column('analysis_analytes', 'reported_name', nullable=False)
    op.alter_column('analysis_analytes', 'calculation', nullable=False)
    op.alter_column('analysis_analytes', 'significant_figures', nullable=False)
    op.alter_column('analysis_analytes', 'low_value', nullable=False)
    op.alter_column('analysis_analytes', 'high_value', nullable=False)
    op.alter_column('analysis_analytes', 'list_id', nullable=False)
    op.alter_column('analysis_analytes', 'data_type', nullable=False)
    
    op.alter_column('results', 'entered_by', nullable=True)
    op.alter_column('results', 'entry_date', nullable=True)
    op.alter_column('results', 'calculated_result', nullable=False)
    op.alter_column('results', 'qualifiers', nullable=False)
    op.alter_column('results', 'reported_result', nullable=False)
    op.alter_column('results', 'raw_result', nullable=False)
    
    op.alter_column('batch_containers', 'notes', nullable=False)
    op.alter_column('batch_containers', 'position', nullable=False)
    
    op.alter_column('batches', 'end_date', nullable=False)
    op.alter_column('batches', 'start_date', nullable=False)
    op.alter_column('batches', 'status', nullable=True)
    op.alter_column('batches', 'type', nullable=False)
    
    op.alter_column('contents', 'amount_units', nullable=False)
    op.alter_column('contents', 'amount', nullable=False)
    op.alter_column('contents', 'concentration_units', nullable=False)
    op.alter_column('contents', 'concentration', nullable=False)
    
    op.alter_column('containers', 'amount_units', nullable=False)
    op.alter_column('containers', 'amount', nullable=False)
    op.alter_column('containers', 'concentration_units', nullable=False)
    op.alter_column('containers', 'concentration', nullable=False)
    
    op.alter_column('analyses', 'cost', nullable=False)
    op.alter_column('analyses', 'turnaround_time', nullable=False)
    op.alter_column('analyses', 'method', nullable=False)
