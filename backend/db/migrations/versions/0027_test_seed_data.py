"""Add seed data for BioTech/Pharma startup assays: Cell Viability, Binding Affinity, ADME Panel

Revision ID: 0027
Revises: 0026
Create Date: 2025-12-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0027'
down_revision = '0026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create connection for data insertion
    connection = op.get_bind()

    # Resolve unit IDs (µM, nM, %, cells/mL from migration 0004)
    um_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'µM' LIMIT 1")
    ).fetchone()
    um_id = str(um_row[0]) if um_row else None

    nm_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'nM' LIMIT 1")
    ).fetchone()
    nm_id = str(nm_row[0]) if nm_row else None

    percent_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = '%' LIMIT 1")
    ).fetchone()
    percent_id = str(percent_row[0]) if percent_row else None

    cells_ml_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'cells/mL' LIMIT 1")
    ).fetchone()
    cells_ml_id = str(cells_ml_row[0]) if cells_ml_row else None

    # Seed analytes for BioTech/Pharma assays
    analytes_data = [
        # Cell Viability Assay
        {'id': 'a0000001-a000-a000-a000-a00000000001', 'name': 'Cell Viability (%)', 'description': 'Percent viable cells (ATP luminescence or MTT)', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        {'id': 'a0000002-a000-a000-a000-a00000000002', 'name': 'IC50', 'description': 'Half-maximal inhibitory concentration', 'cas_number': None, 'units_default': um_id, 'data_type': 'numeric'},
        {'id': 'a0000003-a000-a000-a000-a00000000003', 'name': 'Emax', 'description': 'Maximum effect / % inhibition at highest dose', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        
        # Binding Affinity Assay
        {'id': 'a0000004-a000-a000-a000-a00000000004', 'name': 'Kd', 'description': 'Dissociation constant (binding affinity)', 'cas_number': None, 'units_default': nm_id, 'data_type': 'numeric'},
        {'id': 'a0000005-a000-a000-a000-a00000000005', 'name': 'Bmax', 'description': 'Maximum binding capacity', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        
        # Kinase Activity Assay
        {'id': 'a0000006-a000-a000-a000-a00000000006', 'name': 'Kinase Inhibition (%)', 'description': 'Percent kinase activity inhibition', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        {'id': 'a0000007-a000-a000-a000-a00000000007', 'name': 'Ki', 'description': 'Inhibitor constant', 'cas_number': None, 'units_default': nm_id, 'data_type': 'numeric'},
        
        # ADME Panel
        {'id': 'a0000008-a000-a000-a000-a00000000008', 'name': 'Clearance', 'description': 'Metabolic clearance rate (µL/min/mg protein)', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        {'id': 'a0000009-a000-a000-a000-a00000000009', 'name': 'Permeability', 'description': 'Caco-2 permeability (nm/s)', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        {'id': 'a0000010-a000-a000-a000-a00000000010', 'name': 'Plasma Protein Binding (%)', 'description': 'Percent bound to plasma proteins', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        {'id': 'a0000011-a000-a000-a000-a00000000011', 'name': 'Solubility', 'description': 'Aqueous solubility (µg/mL)', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        
        # Cell Count / Seeding
        {'id': 'a0000012-a000-a000-a000-a00000000012', 'name': 'Cell Count', 'description': 'Initial cell seeding density', 'cas_number': None, 'units_default': cells_ml_id, 'data_type': 'numeric'},
    ]

    for analyte in analytes_data:
        connection.execute(
            sa.text("""
                INSERT INTO analytes (id, name, description, active, created_at, modified_at, cas_number, units_default, data_type, custom_attributes)
                VALUES (:id, :name, :description, true, NOW(), NOW(), :cas_number, :units_default, :data_type, '{}')
                ON CONFLICT (id) DO NOTHING
            """),
            analyte
        )

    # Seed analyses for BioTech/Pharma workflows
    analyses_data = [
        {'id': 'b0000001-b000-b000-b000-b00000000001', 'name': 'Cell Viability Assay (ATP)', 'description': 'CellTiter-Glo luminescent cell viability', 'method': 'ATP luminescence (96-well plate reader)', 'turnaround_time': 1, 'cost': 50.00, 'shelf_life': None},
        {'id': 'b0000002-b000-b000-b000-b00000000002', 'name': 'Dose-Response Screening', 'description': '10-point dose-response for IC50 determination', 'method': '384-well dose-response with curve fitting', 'turnaround_time': 2, 'cost': 120.00, 'shelf_life': None},
        {'id': 'b0000003-b000-b000-b000-b00000000003', 'name': 'Target Binding Assay', 'description': 'Fluorescence polarization binding assay', 'method': 'FP or SPR for Kd determination', 'turnaround_time': 3, 'cost': 200.00, 'shelf_life': None},
        {'id': 'b0000004-b000-b000-b000-b00000000004', 'name': 'Kinase Selectivity Panel', 'description': 'Multi-kinase inhibition profiling', 'method': 'Radiometric or HTRF kinase assay', 'turnaround_time': 5, 'cost': 350.00, 'shelf_life': None},
        {'id': 'b0000005-b000-b000-b000-b00000000005', 'name': 'ADME Profiling', 'description': 'In vitro ADME panel (clearance, permeability, solubility)', 'method': 'Liver microsome stability + Caco-2', 'turnaround_time': 7, 'cost': 450.00, 'shelf_life': None},
    ]

    for analysis in analyses_data:
        connection.execute(
            sa.text("""
                INSERT INTO analyses (id, name, description, method, turnaround_time, cost, shelf_life, active, created_at, modified_at, custom_attributes)
                VALUES (:id, :name, :description, :method, :turnaround_time, :cost, :shelf_life, true, NOW(), NOW(), '{}')
                ON CONFLICT (id) DO NOTHING
            """),
            analysis
        )

    # Seed analysis_analytes (link analytes to assays with validation rules)
    analysis_analytes_data = [
        # Cell Viability Assay
        {'analysis_id': 'b0000001-b000-b000-b000-b00000000001', 'analyte_id': 'a0000012-a000-a000-a000-a00000000012', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': 1, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000001-b000-b000-b000-b00000000001', 'analyte_id': 'a0000001-a000-a000-a000-a00000000001', 'data_type': 'numeric', 'list_id': None, 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 2, 'is_required': True, 'default_value': None},
        
        # Dose-Response Screening
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000002-a000-a000-a000-a00000000002', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': 1, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000003-a000-a000-a000-a00000000003', 'data_type': 'numeric', 'list_id': None, 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 2, 'is_required': False, 'default_value': None},
        
        # Target Binding Assay
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000004-a000-a000-a000-a00000000004', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': 1, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000005-a000-a000-a000-a00000000005', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': 2, 'is_required': False, 'default_value': None},
        
        # Kinase Selectivity Panel
        {'analysis_id': 'b0000004-b000-b000-b000-b00000000004', 'analyte_id': 'a0000006-a000-a000-a000-a00000000006', 'data_type': 'numeric', 'list_id': None, 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 1, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000004-b000-b000-b000-b00000000004', 'analyte_id': 'a0000007-a000-a000-a000-a00000000007', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': 2, 'is_required': False, 'default_value': None},
        
        # ADME Profiling
        {'analysis_id': 'b0000005-b000-b000-b000-b00000000005', 'analyte_id': 'a0000008-a000-a000-a000-a00000000008', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 1, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000005-b000-b000-b000-b00000000005', 'analyte_id': 'a0000009-a000-a000-a000-a00000000009', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 2, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000005-b000-b000-b000-b00000000005', 'analyte_id': 'a0000010-a000-a000-a000-a00000000010', 'data_type': 'numeric', 'list_id': None, 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 3, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000005-b000-b000-b000-b00000000005', 'analyte_id': 'a0000011-a000-a000-a000-a00000000011', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 2, 'calculation': None, 'reported_name': None, 'display_order': 4, 'is_required': True, 'default_value': None},
    ]

    for junction in analysis_analytes_data:
        connection.execute(
            sa.text("""
                INSERT INTO analysis_analytes (analysis_id, analyte_id, data_type, list_id, high_value, low_value, significant_figures, calculation, reported_name, display_order, is_required, default_value)
                VALUES (:analysis_id, :analyte_id, :data_type, :list_id, :high_value, :low_value, :significant_figures, :calculation, :reported_name, :display_order, :is_required, :default_value)
                ON CONFLICT (analysis_id, analyte_id) DO NOTHING
            """),
            junction
        )

    # Create 'ADME Panel' test battery
    # This battery groups ADME profiling assays commonly run together for early-stage compound characterization
    battery_data = {
        'id': 'c0000001-c000-c000-c000-c00000000001',
        'name': 'ADME Panel',
        'description': 'Complete ADME profiling panel for drug discovery (clearance, permeability, solubility, plasma protein binding)',
        'active': True
    }
    
    connection.execute(
        sa.text("""
            INSERT INTO test_batteries (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, :active, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        battery_data
    )
    
    # Link ADME Profiling analysis to the battery
    battery_analysis_data = [{
        'battery_id': 'c0000001-c000-c000-c000-c00000000001',
        'analysis_id': 'b0000005-b000-b000-b000-b00000000005',
        'sequence': 1,
        'optional': False
    }]

    for battery_analysis in battery_analysis_data:
        connection.execute(
            sa.text("""
                INSERT INTO battery_analyses (battery_id, analysis_id, sequence, optional)
                VALUES (:battery_id, :analysis_id, :sequence, :optional)
                ON CONFLICT (battery_id, analysis_id) DO NOTHING
            """),
            battery_analysis
        )



def downgrade() -> None:
    # Remove seeded data in reverse order
    connection = op.get_bind()

    analysis_ids = (
        "'b0000001-b000-b000-b000-b00000000001', 'b0000002-b000-b000-b000-b00000000002', "
        "'b0000003-b000-b000-b000-b00000000003', 'b0000004-b000-b000-b000-b00000000004', "
        "'b0000005-b000-b000-b000-b00000000005'"
    )
    connection.execute(sa.text(f"DELETE FROM analysis_analytes WHERE analysis_id IN ({analysis_ids})"))

    connection.execute(sa.text(f"DELETE FROM analyses WHERE id IN ({analysis_ids})"))

    analyte_ids = (
        "'a0000001-a000-a000-a000-a00000000001', 'a0000002-a000-a000-a000-a00000000002', "
        "'a0000003-a000-a000-a000-a00000000003', 'a0000004-a000-a000-a000-a00000000004', "
        "'a0000005-a000-a000-a000-a00000000005', 'a0000006-a000-a000-a000-a00000000006', "
        "'a0000007-a000-a000-a000-a00000000007', 'a0000008-a000-a000-a000-a00000000008', "
        "'a0000009-a000-a000-a000-a00000000009', 'a0000010-a000-a000-a000-a00000000010', "
        "'a0000011-a000-a000-a000-a00000000011', 'a0000012-a000-a000-a000-a00000000012'"
    )
    connection.execute(sa.text(f"DELETE FROM analytes WHERE id IN ({analyte_ids})"))

    # Delete battery_analyses junctions
    connection.execute(
        sa.text("DELETE FROM battery_analyses WHERE battery_id = 'c0000001-c000-c000-c000-c00000000001'")
    )
    
    # Delete test batteries
    connection.execute(
        sa.text("DELETE FROM test_batteries WHERE id = 'c0000001-c000-c000-c000-c00000000001'")
    )
