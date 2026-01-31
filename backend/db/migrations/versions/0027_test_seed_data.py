"""Add seed data for initial tests: pH, EPA 8080, Total Coliform

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

    # Resolve µg/L, cfm, ml unit ID (0004 seeds units with gen_random_uuid(), so we look up by name)
    ng_per_l_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'ng/L' LIMIT 1")
    ).fetchone()
    ng_per_l_id = str(ng_per_l_row[0]) if ng_per_l_row else None

    cfm_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'cfu' LIMIT 1")
    ).fetchone()
    cfm_id = str(cfm_row[0]) if cfm_row else None

    ml_row = connection.execute(
        sa.text("SELECT id FROM units WHERE name = 'mL' LIMIT 1")
    ).fetchone()
    ml_id = str(ml_row[0]) if ml_row else None

    # Seed analytes (from schema dump); units_default uses ng/L when present
    analytes_data = [
        {'id': 'a0000001-a000-a000-a000-a00000000001', 'name': 'pH', 'description': 'pH value', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        {'id': 'a0000005-a000-a000-a000-a00000000005', 'name': 'Total Coliforms', 'description': 'Coliform bacteria count', 'cas_number': None, 'units_default': cfm_id, 'data_type': 'numeric'},
        {'id': 'a0000002-a000-a000-a000-a00000000002', 'name': 'Aldrin', 'description': 'Organochlorine pesticide', 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'a0000004-a000-a000-a000-a00000000005', 'name': 'Initial Volume (mL)', 'description': 'Sample volume extracted', 'cas_number': None, 'units_default': ml_id, 'data_type': 'numeric'},
        {'id': 'a0000006-a000-a000-a000-a00000000006', 'name': 'E. coli', 'description': 'Escherichia coli count', 'cas_number': None, 'units_default': cfm_id, 'data_type': 'numeric'},
        {'id': 'a0000003-a000-a000-a000-a00000000003', 'name': 'DDT', 'description': 'Organochlorine pesticide', 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'a0000004-a000-a000-a000-a00000000004', 'name': 'Aroclor-1016', 'description': 'Polychlorinated biphenyl', 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'a29d9fde-b207-480a-80b7-e7130fdd8841', 'name': 'Aroclor-1254', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'd1b0e504-04d5-4142-9031-7d6e894e3771', 'name': 'Aroclor-1242', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': '742ee5ab-b398-41a3-a8c2-c0b4a92d2aa2', 'name': 'Aroclor-1260', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'e956c850-6c4b-48f4-b60e-db791988cfba', 'name': 'Aroclor-1248', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'ec8e95ba-e2db-4b4a-aba3-7544725c4eee', 'name': 'Aroclor-1221', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': 'd408fae9-284c-4bf3-9086-a5937557abad', 'name': 'DDD', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
        {'id': '046d7933-c8ae-48a5-998d-7613c8220d48', 'name': 'DDE', 'description': None, 'cas_number': None, 'units_default': ng_per_l_id, 'data_type': 'numeric'},
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

    # Seed analyses (from schema dump)
    analyses_data = [
        {'id': 'b0000003-b000-b000-b000-b00000000003', 'name': 'Total Coliform Enumeration', 'description': None, 'method': 'Colilert or Membrane Filtration', 'turnaround_time': 2, 'cost': 50.00, 'shelf_life': None},
        {'id': 'b0000002-b000-b000-b000-b00000000004', 'name': 'EPA Method 8080 Prep', 'description': None, 'method': 'Sample Extractionfor Organochlorine Pesticides and PCBs', 'turnaround_time': 7, 'cost': 25.00, 'shelf_life': None},
        {'id': 'b0000001-b000-b000-b000-b00000000001', 'name': 'pH Measurement', 'description': None, 'method': 'Electrometric', 'turnaround_time': 1, 'cost': 10.00, 'shelf_life': None},
        {'id': 'b0000002-b000-b000-b000-b00000000002', 'name': 'EPA Method 8080', 'description': 'test', 'method': 'GC/ECD for Organochlorine PCBs', 'turnaround_time': 14, 'cost': 150.00, 'shelf_life': None},
        {'id': 'aa12ed7f-282b-46bc-80da-d00fe61d59c4', 'name': 'EPA Method 8080 Pest', 'description': None, 'method': 'GC/ECD for Organochlorine Pesticides', 'turnaround_time': 14, 'cost': 180.00, 'shelf_life': None},
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

    # Seed analysis_analytes (from schema dump)
    analysis_analytes_data = [
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a0000004-a000-a000-a000-a00000000004', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000004', 'analyte_id': 'a0000004-a000-a000-a000-a00000000005', 'data_type': 'numeric', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000005-a000-a000-a000-a00000000005', 'data_type': 'count', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 0, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000003-b000-b000-b000-b00000000003', 'analyte_id': 'a0000006-a000-a000-a000-a00000000006', 'data_type': 'count', 'list_id': None, 'high_value': None, 'low_value': 0.0, 'significant_figures': 0, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': True, 'default_value': None},
        {'analysis_id': 'b0000001-b000-b000-b000-b00000000001', 'analyte_id': 'a0000001-a000-a000-a000-a00000000001', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'aa12ed7f-282b-46bc-80da-d00fe61d59c4', 'analyte_id': 'd408fae9-284c-4bf3-9086-a5937557abad', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'aa12ed7f-282b-46bc-80da-d00fe61d59c4', 'analyte_id': 'a0000003-a000-a000-a000-a00000000003', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'aa12ed7f-282b-46bc-80da-d00fe61d59c4', 'analyte_id': '046d7933-c8ae-48a5-998d-7613c8220d48', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'aa12ed7f-282b-46bc-80da-d00fe61d59c4', 'analyte_id': 'a0000002-a000-a000-a000-a00000000002', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'ec8e95ba-e2db-4b4a-aba3-7544725c4eee', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'd1b0e504-04d5-4142-9031-7d6e894e3771', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'e956c850-6c4b-48f4-b60e-db791988cfba', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': 'a29d9fde-b207-480a-80b7-e7130fdd8841', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
        {'analysis_id': 'b0000002-b000-b000-b000-b00000000002', 'analyte_id': '742ee5ab-b398-41a3-a8c2-c0b4a92d2aa2', 'data_type': None, 'list_id': None, 'high_value': None, 'low_value': None, 'significant_figures': None, 'calculation': None, 'reported_name': None, 'display_order': None, 'is_required': False, 'default_value': None},
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

    # Create 'EPA 8080 Full' battery
    # This battery groups the EPA Method 8080 analytical analysis
    # Note: Prep analyses can be added to batteries via admin interface
    battery_data = {
        'id': 'c0000001-c000-c000-c000-c00000000001',
        'name': 'EPA 8080 Full',
        'description': 'Complete EPA Method 8080 test battery for Organochlorine Pesticides and PCBs',
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
    
    # Link EPA Method 8080 analysis to the battery
    # Using the analysis ID from migration 0009: 'b0000002-b000-b000-b000-b00000000002'
    battery_analysis_data = [{
        'battery_id': 'c0000001-c000-c000-c000-c00000000001',
        'analysis_id': 'b0000002-b000-b000-b000-b00000000002',
        'sequence': 2,
        'optional': False
    }, {
        'battery_id': 'c0000001-c000-c000-c000-c00000000001',
        'analysis_id': 'b0000002-b000-b000-b000-b00000000004',
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
    # Remove seeded data in reverse order (matches schema dump IDs)
    connection = op.get_bind()

    analysis_ids = (
        "'b0000001-b000-b000-b000-b00000000001', 'b0000002-b000-b000-b000-b00000000002', "
        "'b0000003-b000-b000-b000-b00000000003', 'b0000002-b000-b000-b000-b00000000004', "
        "'aa12ed7f-282b-46bc-80da-d00fe61d59c4'"
    )
    connection.execute(sa.text(f"DELETE FROM analysis_analytes WHERE analysis_id IN ({analysis_ids})"))

    connection.execute(sa.text(f"DELETE FROM analyses WHERE id IN ({analysis_ids})"))

    analyte_ids = (
        "'a0000001-a000-a000-a000-a00000000001', 'a0000002-a000-a000-a000-a00000000002', "
        "'a0000003-a000-a000-a000-a00000000003', 'a0000004-a000-a000-a000-a00000000004', "
        "'a0000005-a000-a000-a000-a00000000005', 'a0000006-a000-a000-a000-a00000000006', "
        "'a0000004-a000-a000-a000-a00000000005', 'a29d9fde-b207-480a-80b7-e7130fdd8841', "
        "'d1b0e504-04d5-4142-9031-7d6e894e3771', '742ee5ab-b398-41a3-a8c2-c0b4a92d2aa2', "
        "'e956c850-6c4b-48f4-b60e-db791988cfba', 'ec8e95ba-e2db-4b4a-aba3-7544725c4eee', "
        "'d408fae9-284c-4bf3-9086-a5937557abad', '046d7933-c8ae-48a5-998d-7613c8220d48'"
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
    