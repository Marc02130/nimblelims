"""Add seed data for initial tests: pH, EPA 8080, Total Coliform

Revision ID: 0009
Revises: 0008
Create Date: 2025-12-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create connection for data insertion
    connection = op.get_bind()
    
    # First, seed analytes if not present (using placeholders; expand as needed)
    analytes_data = [
        {'id': 'a0000001-a000-a000-a000-a00000000001', 'name': 'pH', 'description': 'pH value'},
        {'id': 'a0000002-a000-a000-a000-a00000000002', 'name': 'Aldrin', 'description': 'Organochlorine pesticide'},
        {'id': 'a0000003-a000-a000-a000-a00000000003', 'name': 'DDT', 'description': 'Organochlorine pesticide'},
        {'id': 'a0000004-a000-a000-a000-a00000000004', 'name': 'PCB-1016', 'description': 'Polychlorinated biphenyl'},
        {'id': 'a0000005-a000-a000-a000-a00000000005', 'name': 'Total Coliforms', 'description': 'Coliform bacteria count'},
        {'id': 'a0000006-a000-a000-a000-a00000000006', 'name': 'E. coli', 'description': 'Escherichia coli count'},
    ]
    
    for analyte in analytes_data:
        connection.execute(
            sa.text("""
                INSERT INTO analytes (id, name, description, active, created_at, modified_at)
                VALUES (:id, :name, :description, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            analyte
        )
    
    # Seed analyses
    analyses_data = [
        {'id': 'b0000001-b000-b000-b000-b00000000001', 'name': 'pH Measurement', 'method': 'Electrometric', 'turnaround_time': 1, 'cost': 10.00},
        {'id': 'b0000002-b000-b000-b000-b00000000002', 'name': 'EPA Method 8080', 'method': 'GC/ECD for Organochlorine Pesticides and PCBs', 'turnaround_time': 7, 'cost': 150.00},
        {'id': 'b0000003-b000-b000-b000-b00000000003', 'name': 'Total Coliform Enumeration', 'method': 'Colilert or Membrane Filtration', 'turnaround_time': 2, 'cost': 50.00},
    ]
    
    for analysis in analyses_data:
        connection.execute(
            sa.text("""
                INSERT INTO analyses (id, name, method, turnaround_time, cost, active, created_at, modified_at)
                VALUES (:id, :name, :method, :turnaround_time, :cost, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            analysis
        )
    
    # Seed analysis_analytes junctions with rules
    analysis_analytes_data = [
        # pH
        {'analysis_id': 'b0000001-b000-b000-b000-b00000000001', 'analyte_id': 'a0000001-a000-a000-a000-a00000000001', 
         'data_type': 'numeric', 'high_value': 14.0, 'low_value': 0.0, 'significant_figures': 2, 'is_required': True},
        
        # EPA 8080 (sample analytes)
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000002-a000-a000-a000-a00000000002', 
         'data_type': 'numeric', 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'is_required': True},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000003-a000-a000-a000-a00000000003', 
         'data_type': 'numeric', 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'is_required': True},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000004-a000-a000-a000-a00000000004', 
         'data_type': 'numeric', 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'is_required': True},
        
        # Total Coliform
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000005-a000-a000-a000-a00000000005', 
         'data_type': 'count', 'high_value': None, 'low_value': 0.0, 'significant_figures': 0, 'is_required': True},
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000006-a000-a000-a000-a00000000006', 
         'data_type': 'count', 'high_value': None, 'low_value': 0.0, 'significant_figures': 0, 'is_required': True},
    ]
    
    for junction in analysis_analytes_data:
        connection.execute(
            sa.text("""
                INSERT INTO analysis_analytes (analysis_id, analyte_id, data_type, high_value, low_value, significant_figures, is_required)
                VALUES (:analysis_id, :analyte_id, :data_type, :high_value, :low_value, :significant_figures, :is_required)
                ON CONFLICT (analysis_id, analyte_id) DO NOTHING
            """),
            junction
        )


def downgrade() -> None:
    # Remove seeded data in reverse order
    connection = op.get_bind()
    
    # Delete analysis_analytes junctions
    connection.execute(sa.text("DELETE FROM analysis_analytes WHERE analysis_id IN ('b0000001-b000-b000-b000-b00000000001', 'b0000002-b000-b000-b000-b00000000002', 'b0000003-b000-b000-b000-b00000000003')"))
    
    # Delete analyses
    connection.execute(sa.text("DELETE FROM analyses WHERE id IN ('b0000001-b000-b000-b000-b00000000001', 'b0000002-b000-b000-b000-b00000000002', 'b0000003-b000-b000-b000-b00000000003')"))
    
    # Delete analytes
    connection.execute(sa.text("DELETE FROM analytes WHERE id IN ('a0000001-a000-a000-a000-a00000000001', 'a0000002-a000-a000-a000-a00000000002', 'a0000003-a000-a000-a000-a00000000003', 'a0000004-a000-a000-a000-a00000000004', 'a0000005-a000-a000-a000-a00000000005', 'a0000006-a000-a000-a000-a00000000006')"))