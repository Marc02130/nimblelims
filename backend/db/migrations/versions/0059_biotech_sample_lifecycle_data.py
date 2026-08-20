"""Add populated sample lifecycle data: samples, containers, tests, results, batches

Revision ID: 0059
Revises: 0058
Create Date: 2026-01-20 00:01:00.000000

This migration creates actual sample instances that span the full lifecycle:
- Samples in various statuses (Received → Testing Complete → Reviewed)
- Parent/aliquot/derivative chains
- Containers with contents and positions
- Ordered tests (individual + battery)
- Entered results (some complete, some incomplete)
- Batches with QC samples
- Edge cases: depleted parent, zero remaining volume, rejected sample, canceled test

This data is immediately loadable for UAT and automated tests.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta
import uuid

_SEED_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_ID_KEYS = (
    "id",
    "client_id",
    "project_id",
    "user_id",
    "analysis_id",
    "analyte_id",
    "battery_id",
    "type_id",
    "created_by",
    "modified_by",
    "sample_type",
    "matrix",
    "status",
    "parent_sample_id",
    "container_id",
    "sample_id",
    "technician_id",
    "test_id",
    "batch_id",
    "entered_by",
    "qc_type",
    "concentration_units",
    "amount_units",
)


def as_id(value):
    """Turn a seed slug into a stable UUID; leave real UUIDs alone."""
    if value is None:
        return None
    text = str(value)
    try:
        return str(uuid.UUID(text))
    except ValueError:
        return str(uuid.uuid5(_SEED_NS, f"nimblelims.seed.{text}"))


def seed_params(data):
    """Copy a seed dict, converting slug PK/FK fields to UUIDs."""
    if data is None:
        return None
    out = dict(data)
    for key in _ID_KEYS:
        if key in out and out[key] is not None:
            out[key] = as_id(out[key])
    return out


# revision identifiers, used by Alembic.
revision = '0059'
down_revision = '0058'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Get reference IDs we'll need
    # Users
    alice_user = connection.execute(sa.text("SELECT id FROM users WHERE username = 'alice-tech' LIMIT 1")).fetchone()
    bob_user = connection.execute(sa.text("SELECT id FROM users WHERE username = 'bob-tech' LIMIT 1")).fetchone()
    carol_user = connection.execute(sa.text("SELECT id FROM users WHERE username = 'carol-manager' LIMIT 1")).fetchone()
    admin_user = connection.execute(sa.text("SELECT id FROM users WHERE username = 'admin' LIMIT 1")).fetchone()
    
    alice_id = str(alice_user[0]) if alice_user else None
    bob_id = str(bob_user[0]) if bob_user else None
    carol_id = str(carol_user[0]) if carol_user else None
    admin_id = str(admin_user[0]) if admin_user else None
    
    # Projects
    mab_pk_proj = connection.execute(sa.text("SELECT id FROM projects WHERE name = 'mAb-2301 PK Study' LIMIT 1")).fetchone()
    cart_proj = connection.execute(sa.text("SELECT id FROM projects WHERE name = 'CAR-T In-Process Testing' LIMIT 1")).fetchone()
    plasmid_proj = connection.execute(sa.text("SELECT id FROM projects WHERE name = 'Plasmid Lot Release Testing' LIMIT 1")).fetchone()
    alpha_proj = connection.execute(sa.text("SELECT id FROM projects WHERE name = 'Project Alpha' LIMIT 1")).fetchone()
    
    mab_pk_id = str(mab_pk_proj[0]) if mab_pk_proj else None
    cart_id = str(cart_proj[0]) if cart_proj else None
    plasmid_id = str(plasmid_proj[0]) if plasmid_proj else None
    alpha_id = str(alpha_proj[0]) if alpha_proj else None
    
    # Sample types
    plasma_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Plasma' AND list_id = '55555555-5555-5555-5555-555555555555' LIMIT 1")).fetchone()
    blood_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Blood' AND list_id = '55555555-5555-5555-5555-555555555555' LIMIT 1")).fetchone()
    pbmc_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'PBMC' AND list_id = '55555555-5555-5555-5555-555555555555' LIMIT 1")).fetchone()
    plasmid_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Plasmid DNA' AND list_id = '55555555-5555-5555-5555-555555555555' LIMIT 1")).fetchone()
    
    plasma_type_id = str(plasma_type[0]) if plasma_type else str(blood_type[0]) if blood_type else None
    pbmc_type_id = str(pbmc_type[0]) if pbmc_type else str(blood_type[0]) if blood_type else None
    plasmid_type_id = str(plasmid_type[0]) if plasmid_type else str(blood_type[0]) if blood_type else None
    
    # Matrices
    plasma_matrix = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Plasma (K2EDTA)' AND list_id = '66666666-6666-6666-6666-666666666666' LIMIT 1")).fetchone()
    pbmc_matrix = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'PBMC' AND list_id = '66666666-6666-6666-6666-666666666666' LIMIT 1")).fetchone()
    plasmid_matrix = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Plasmid DNA' AND list_id = '66666666-6666-6666-6666-666666666666' LIMIT 1")).fetchone()
    
    plasma_matrix_id = str(plasma_matrix[0]) if plasma_matrix else None
    pbmc_matrix_id = str(pbmc_matrix[0]) if pbmc_matrix else plasma_matrix_id
    plasmid_matrix_id = str(plasmid_matrix[0]) if plasmid_matrix else plasma_matrix_id
    
    # Statuses
    received_status = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Received' AND list_id = '11111111-1111-1111-1111-111111111111' LIMIT 1")).fetchone()
    available_status = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Available for Testing' AND list_id = '11111111-1111-1111-1111-111111111111' LIMIT 1")).fetchone()
    testing_complete_status = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Testing Complete' AND list_id = '11111111-1111-1111-1111-111111111111' LIMIT 1")).fetchone()
    reviewed_status = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Reviewed' AND list_id = '11111111-1111-1111-1111-111111111111' LIMIT 1")).fetchone()
    
    received_id = str(received_status[0]) if received_status else None
    available_id = str(available_status[0]) if available_status else None
    testing_complete_id = str(testing_complete_status[0]) if testing_complete_status else None
    reviewed_id = str(reviewed_status[0]) if reviewed_status else None
    
    # Test statuses
    test_in_process = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'In Process' AND list_id = '22222222-2222-2222-2222-222222222222' LIMIT 1")).fetchone()
    test_in_analysis = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'In Analysis' AND list_id = '22222222-2222-2222-2222-222222222222' LIMIT 1")).fetchone()
    test_complete = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Complete' AND list_id = '22222222-2222-2222-2222-222222222222' LIMIT 1")).fetchone()
    
    test_in_process_id = str(test_in_process[0]) if test_in_process else None
    test_in_analysis_id = str(test_in_analysis[0]) if test_in_analysis else None
    test_complete_id = str(test_complete[0]) if test_complete else None
    
    # Batch status
    batch_created = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Created' AND list_id = '44444444-4444-4444-4444-444444444444' LIMIT 1")).fetchone()
    batch_in_process = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'In Process' AND list_id = '44444444-4444-4444-4444-444444444444' LIMIT 1")).fetchone()
    batch_completed = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Completed' AND list_id = '44444444-4444-4444-4444-444444444444' LIMIT 1")).fetchone()
    
    batch_created_id = str(batch_created[0]) if batch_created else None
    batch_in_process_id = str(batch_in_process[0]) if batch_in_process else None
    batch_completed_id = str(batch_completed[0]) if batch_completed else None
    
    # QC Types
    qc_sample_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Sample' AND list_id = '77777777-7777-7777-7777-777777777777' LIMIT 1")).fetchone()
    qc_blank_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Blank' AND list_id = '77777777-7777-7777-7777-777777777777' LIMIT 1")).fetchone()
    qc_pos_ctrl_type = connection.execute(sa.text("SELECT id FROM list_entries WHERE name = 'Positive Control' AND list_id = '77777777-7777-7777-7777-777777777777' LIMIT 1")).fetchone()
    
    qc_sample_id = str(qc_sample_type[0]) if qc_sample_type else None
    qc_blank_id = str(qc_blank_type[0]) if qc_blank_type else None
    qc_pos_ctrl_id = str(qc_pos_ctrl_type[0]) if qc_pos_ctrl_type else None
    
    # Container types
    cryovial = connection.execute(sa.text("SELECT id FROM container_types WHERE name = 'Cryovial (2mL)' LIMIT 1")).fetchone()
    conical15 = connection.execute(sa.text("SELECT id FROM container_types WHERE name = '15mL Conical Tube' LIMIT 1")).fetchone()
    plate96 = connection.execute(sa.text("SELECT id FROM container_types WHERE name = '96-Well Plate' LIMIT 1")).fetchone()
    microtube = connection.execute(sa.text("SELECT id FROM container_types WHERE name = 'Microcentrifuge Tube (1.5mL)' LIMIT 1")).fetchone()
    
    cryovial_id = str(cryovial[0]) if cryovial else as_id('ctype-001-cryovial')
    conical15_id = str(conical15[0]) if conical15 else as_id('ctype-002-conical15')
    plate96_id = str(plate96[0]) if plate96 else as_id('ctype-004-plate96')
    microtube_id = str(microtube[0]) if microtube else as_id('ctype-006-microtube')
    
    # Units
    ng_ul = connection.execute(sa.text("SELECT id FROM units WHERE name = 'ng/µL' LIMIT 1")).fetchone()
    ug_ml = connection.execute(sa.text("SELECT id FROM units WHERE name = 'µg/mL' LIMIT 1")).fetchone()
    ul = connection.execute(sa.text("SELECT id FROM units WHERE name = 'µL' LIMIT 1")).fetchone()
    ml = connection.execute(sa.text("SELECT id FROM units WHERE name = 'mL' LIMIT 1")).fetchone()
    
    ng_ul_id = str(ng_ul[0]) if ng_ul else None
    ug_ml_id = str(ug_ml[0]) if ug_ml else None
    ul_id = str(ul[0]) if ul else None
    ml_id = str(ml[0]) if ml else None
    
    # Analyses
    elisa_analysis = connection.execute(sa.text("SELECT id FROM analyses WHERE name = 'ELISA (Human IgG)' LIMIT 1")).fetchone()
    qpcr_analysis = connection.execute(sa.text("SELECT id FROM analyses WHERE name = 'qPCR (Plasmid Copy Number)' LIMIT 1")).fetchone()
    viability_analysis = connection.execute(sa.text("SELECT id FROM analyses WHERE name = 'Cell Viability (Trypan Blue)' LIMIT 1")).fetchone()
    identity_analysis = connection.execute(sa.text("SELECT id FROM analyses WHERE name = 'Identity (Sanger Sequencing)' LIMIT 1")).fetchone()
    
    elisa_id = str(elisa_analysis[0]) if elisa_analysis else as_id('analysis-elisa-001')
    qpcr_id = str(qpcr_analysis[0]) if qpcr_analysis else as_id('analysis-qpcr-001')
    viability_id = str(viability_analysis[0]) if viability_analysis else as_id('analysis-viability-001')
    identity_id = str(identity_analysis[0]) if identity_analysis else as_id('analysis-identity-seq-001')
    
    # Analytes
    igg_conc_analyte = connection.execute(sa.text("SELECT id FROM analytes WHERE name = 'IgG Concentration' LIMIT 1")).fetchone()
    viability_analyte = connection.execute(sa.text("SELECT id FROM analytes WHERE name = 'Viability (%)' LIMIT 1")).fetchone()
    cell_count_analyte = connection.execute(sa.text("SELECT id FROM analytes WHERE name = 'Total Cell Count' LIMIT 1")).fetchone()
    plasmid_copies_analyte = connection.execute(sa.text("SELECT id FROM analytes WHERE name = 'Plasmid Copy Number' LIMIT 1")).fetchone()
    
    igg_conc_analyte_id = str(igg_conc_analyte[0]) if igg_conc_analyte else as_id('analyte-igg-conc')
    viability_analyte_id = str(viability_analyte[0]) if viability_analyte else as_id('analyte-viability')
    cell_count_analyte_id = str(cell_count_analyte[0]) if cell_count_analyte else as_id('analyte-cell-count')
    plasmid_copies_analyte_id = str(plasmid_copies_analyte[0]) if plasmid_copies_analyte else as_id('analyte-plasmid-copies')
    
    # Compute dates
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    one_week_ago = today - timedelta(days=7)
    two_weeks_from_now = today + timedelta(days=14)
    
    # ========================================================================
    # Create containers first (samples will link to them via Contents)
    # ========================================================================
    containers_data = [
        # mAb PK study containers (plasma samples)
        {'id': 'cont-mab-pk-t0', 'name': 'PK-T0-Plasma', 'type_id': cryovial_id, 'row': 1, 'column': 1, 'concentration': 5.2, 'concentration_units': ug_ml_id, 'amount': 500, 'amount_units': ul_id, 'created_by': alice_id},
        {'id': 'cont-mab-pk-t1', 'name': 'PK-T1-Plasma', 'type_id': cryovial_id, 'row': 1, 'column': 2, 'concentration': 12.5, 'concentration_units': ug_ml_id, 'amount': 500, 'amount_units': ul_id, 'created_by': alice_id},
        {'id': 'cont-mab-pk-t2', 'name': 'PK-T2-Plasma', 'type_id': cryovial_id, 'row': 1, 'column': 3, 'concentration': 18.3, 'concentration_units': ug_ml_id, 'amount': 500, 'amount_units': ul_id, 'created_by': alice_id},
        # Aliquot from T0 (depleted parent scenario)
        {'id': 'cont-mab-pk-t0-aliq', 'name': 'PK-T0-Aliquot', 'type_id': microtube_id, 'row': 1, 'column': 1, 'concentration': 5.2, 'concentration_units': ug_ml_id, 'amount': 100, 'amount_units': ul_id, 'created_by': alice_id},
        # CAR-T samples
        {'id': 'cont-cart-batch1', 'name': 'CAR-T-Batch001', 'type_id': conical15_id, 'row': 1, 'column': 1, 'concentration': None, 'concentration_units': None, 'amount': 10, 'amount_units': ml_id, 'created_by': bob_id},
        {'id': 'cont-cart-blank', 'name': 'CAR-T-Blank-QC', 'type_id': microtube_id, 'row': 1, 'column': 1, 'concentration': None, 'concentration_units': None, 'amount': 1, 'amount_units': ml_id, 'created_by': bob_id},
        # Plasmid samples
        {'id': 'cont-plasmid-lot1', 'name': 'Plasmid-Lot-2025-001', 'type_id': microtube_id, 'row': 1, 'column': 1, 'concentration': 250, 'concentration_units': ng_ul_id, 'amount': 200, 'amount_units': ul_id, 'created_by': alice_id},
        # 96-well plate for batch results
        {'id': 'cont-plate96-elisa', 'name': 'ELISA-Plate-20260120', 'type_id': plate96_id, 'row': 8, 'column': 12, 'concentration': None, 'concentration_units': None, 'amount': None, 'amount_units': None, 'created_by': alice_id},
    ]
    
    for cont in containers_data:
        connection.execute(
            sa.text("""
                INSERT INTO containers (id, name, active, created_at, modified_at, type_id, row, "column", concentration, concentration_units, amount, amount_units, created_by, modified_by)
                VALUES (:id, :name, true, NOW(), NOW(), :type_id, :row, :column, :concentration, :concentration_units, :amount, :amount_units, :created_by, :created_by)
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(cont)
        )
    
    # ========================================================================
    # Create samples spanning the full lifecycle
    # ========================================================================
    samples_data = [
        # mAb PK Study samples (plasma at 3 timepoints) - Alice's project
        {
            'id': 'sample-mab-pk-t0',
            'name': 'mAb-2301-PK-T0',
            'description': 'PK timepoint 0 (pre-dose) plasma sample from mouse #101',
            'project_id': mab_pk_id,
            'sample_type': plasma_type_id,
            'matrix': plasma_matrix_id,
            'status': testing_complete_id,  # Results entered, awaiting review
            'received_date': two_days_ago,
            'due_date': two_weeks_from_now,
            'temperature': -80.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': None,
            'created_by': alice_id,
        },
        {
            'id': 'sample-mab-pk-t1',
            'name': 'mAb-2301-PK-T1',
            'description': 'PK timepoint 1 (1hr post-dose) plasma sample from mouse #101',
            'project_id': mab_pk_id,
            'sample_type': plasma_type_id,
            'matrix': plasma_matrix_id,
            'status': available_id,  # Ready for testing
            'received_date': two_days_ago,
            'due_date': two_weeks_from_now,
            'temperature': -80.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': None,
            'created_by': alice_id,
        },
        {
            'id': 'sample-mab-pk-t2',
            'name': 'mAb-2301-PK-T2',
            'description': 'PK timepoint 2 (4hr post-dose) plasma sample from mouse #101',
            'project_id': mab_pk_id,
            'sample_type': plasma_type_id,
            'matrix': plasma_matrix_id,
            'status': received_id,  # Just received
            'received_date': yesterday,
            'due_date': two_weeks_from_now,
            'temperature': -80.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': None,
            'created_by': alice_id,
        },
        # Aliquot from T0 (depleted parent edge case)
        {
            'id': 'sample-mab-pk-t0-aliquot',
            'name': 'mAb-2301-PK-T0-Aliq',
            'description': 'Aliquot from T0 for repeat testing',
            'project_id': mab_pk_id,
            'sample_type': plasma_type_id,
            'matrix': plasma_matrix_id,
            'status': available_id,
            'received_date': two_days_ago,
            'due_date': two_weeks_from_now,
            'temperature': -80.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': 'sample-mab-pk-t0',  # Child of T0
            'created_by': alice_id,
        },
        # CAR-T samples (Bob's project)
        {
            'id': 'sample-cart-batch1',
            'name': 'CAR-T-Batch-001',
            'description': 'CAR-T cell therapy batch 001 for in-process QC',
            'project_id': cart_id,
            'sample_type': pbmc_type_id,
            'matrix': pbmc_matrix_id,
            'status': available_id,
            'received_date': yesterday,
            'due_date': today,  # Short TAT for cell viability
            'temperature': 4.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': None,
            'created_by': bob_id,
        },
        # QC blank for CAR-T batch
        {
            'id': 'sample-cart-blank',
            'name': 'CAR-T-Blank-QC',
            'description': 'Blank QC sample for CAR-T viability assay',
            'project_id': cart_id,
            'sample_type': pbmc_type_id,
            'matrix': pbmc_matrix_id,
            'status': available_id,
            'received_date': yesterday,
            'due_date': today,
            'temperature': 4.0,
            'qc_type': qc_blank_id,  # QC type: Blank
            'parent_sample_id': None,
            'created_by': bob_id,
        },
        # Plasmid sample
        {
            'id': 'sample-plasmid-lot1',
            'name': 'Plasmid-Lot-2025-001',
            'description': 'Plasmid DNA lot 2025-001 for identity and purity testing',
            'project_id': plasmid_id,
            'sample_type': plasmid_type_id,
            'matrix': plasmid_matrix_id,
            'status': reviewed_id,  # Fully reviewed and released
            'received_date': one_week_ago,
            'due_date': two_weeks_from_now,
            'temperature': -20.0,
            'qc_type': qc_sample_id,
            'parent_sample_id': None,
            'created_by': alice_id,
        },
    ]
    
    for sample in samples_data:
        connection.execute(
            sa.text("""
                INSERT INTO samples (id, name, description, active, created_at, modified_at, project_id, sample_type, matrix, status, received_date, due_date, temperature, qc_type, parent_sample_id, created_by, modified_by)
                VALUES (:id, :name, :description, true, :received_date, :received_date, :project_id, :sample_type, :matrix, :status, :received_date, :due_date, :temperature, :qc_type, :parent_sample_id, :created_by, :created_by)
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(sample)
        )
    
    # ========================================================================
    # Link samples to containers via Contents junction
    # ========================================================================
    contents_data = [
        {'container_id': 'cont-mab-pk-t0', 'sample_id': 'sample-mab-pk-t0', 'concentration': 5.2, 'concentration_units': ug_ml_id, 'amount': 50, 'amount_units': ul_id},  # Depleted! Only 50µL left
        {'container_id': 'cont-mab-pk-t1', 'sample_id': 'sample-mab-pk-t1', 'concentration': 12.5, 'concentration_units': ug_ml_id, 'amount': 500, 'amount_units': ul_id},
        {'container_id': 'cont-mab-pk-t2', 'sample_id': 'sample-mab-pk-t2', 'concentration': 18.3, 'concentration_units': ug_ml_id, 'amount': 500, 'amount_units': ul_id},
        {'container_id': 'cont-mab-pk-t0-aliq', 'sample_id': 'sample-mab-pk-t0-aliquot', 'concentration': 5.2, 'concentration_units': ug_ml_id, 'amount': 100, 'amount_units': ul_id},
        {'container_id': 'cont-cart-batch1', 'sample_id': 'sample-cart-batch1', 'concentration': None, 'concentration_units': None, 'amount': 10, 'amount_units': ml_id},
        {'container_id': 'cont-cart-blank', 'sample_id': 'sample-cart-blank', 'concentration': None, 'concentration_units': None, 'amount': 1, 'amount_units': ml_id},
        {'container_id': 'cont-plasmid-lot1', 'sample_id': 'sample-plasmid-lot1', 'concentration': 250, 'concentration_units': ng_ul_id, 'amount': 200, 'amount_units': ul_id},
    ]
    
    for content in contents_data:
        connection.execute(
            sa.text("""
                INSERT INTO contents (container_id, sample_id, concentration, concentration_units, amount, amount_units)
                VALUES (:container_id, :sample_id, :concentration, :concentration_units, :amount, :amount_units)
                ON CONFLICT (container_id, sample_id) DO NOTHING
            """),
            seed_params(content)
        )
    
    # ========================================================================
    # Create tests for samples (individual analyses + battery)
    # ========================================================================
    tests_data = [
        # mAb PK T0: ELISA test (complete with results)
        {
            'id': 'test-mab-pk-t0-elisa',
            'name': 'mAb-2301-PK-T0_ELISA',
            'sample_id': 'sample-mab-pk-t0',
            'analysis_id': elisa_id,
            'status': test_complete_id,
            'technician_id': alice_id,
            'test_date': two_days_ago,
            'review_date': None,
        },
        # mAb PK T1: ELISA test (in analysis, no results yet)
        {
            'id': 'test-mab-pk-t1-elisa',
            'name': 'mAb-2301-PK-T1_ELISA',
            'sample_id': 'sample-mab-pk-t1',
            'analysis_id': elisa_id,
            'status': test_in_analysis_id,
            'technician_id': alice_id,
            'test_date': yesterday,
            'review_date': None,
        },
        # mAb PK T2: ELISA test (just ordered, in process)
        {
            'id': 'test-mab-pk-t2-elisa',
            'name': 'mAb-2301-PK-T2_ELISA',
            'sample_id': 'sample-mab-pk-t2',
            'analysis_id': elisa_id,
            'status': test_in_process_id,
            'technician_id': alice_id,
            'test_date': None,
            'review_date': None,
        },
        # CAR-T: Cell viability test (in analysis)
        {
            'id': 'test-cart-viability',
            'name': 'CAR-T-Batch-001_Viability',
            'sample_id': 'sample-cart-batch1',
            'analysis_id': viability_id,
            'status': test_in_analysis_id,
            'technician_id': bob_id,
            'test_date': yesterday,
            'review_date': None,
        },
        # CAR-T Blank: Viability test (complete)
        {
            'id': 'test-cart-blank-viability',
            'name': 'CAR-T-Blank-QC_Viability',
            'sample_id': 'sample-cart-blank',
            'analysis_id': viability_id,
            'status': test_complete_id,
            'technician_id': bob_id,
            'test_date': yesterday,
            'review_date': None,
        },
        # Plasmid: qPCR test (complete, reviewed)
        {
            'id': 'test-plasmid-qpcr',
            'name': 'Plasmid-Lot-2025-001_qPCR',
            'sample_id': 'sample-plasmid-lot1',
            'analysis_id': qpcr_id,
            'status': test_complete_id,
            'technician_id': alice_id,
            'test_date': one_week_ago,
            'review_date': one_week_ago + timedelta(days=1),
        },
    ]
    
    for test in tests_data:
        connection.execute(
            sa.text("""
                INSERT INTO tests (id, name, active, created_at, modified_at, sample_id, analysis_id, status, technician_id, test_date, review_date, created_by, modified_by)
                VALUES (:id, :name, true, NOW(), NOW(), :sample_id, :analysis_id, :status, :technician_id, :test_date, :review_date, :technician_id, :technician_id)
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(test)
        )
    
    # ========================================================================
    # Create results for completed tests
    # ========================================================================
    results_data = [
        # mAb PK T0 ELISA: IgG concentration result
        {
            'test_id': 'test-mab-pk-t0-elisa',
            'analyte_id': igg_conc_analyte_id,
            'raw_result': '5.18',
            'reported_result': '5.2',
            'qualifiers': None,
            'notes': 'Within expected range for pre-dose timepoint',
            'entered_by': alice_id,
            'entry_date': two_days_ago + timedelta(hours=4),
        },
        # CAR-T Blank QC: Viability = 0% (expected for blank)
        {
            'test_id': 'test-cart-blank-viability',
            'analyte_id': viability_analyte_id,
            'raw_result': '0.0',
            'reported_result': '0',
            'qualifiers': None,
            'notes': 'Blank QC - no cells present',
            'entered_by': bob_id,
            'entry_date': yesterday + timedelta(hours=2),
        },
        # CAR-T Blank QC: Cell count = 0
        {
            'test_id': 'test-cart-blank-viability',
            'analyte_id': cell_count_analyte_id,
            'raw_result': '0',
            'reported_result': '0',
            'qualifiers': None,
            'notes': 'Blank QC - no cells present',
            'entered_by': bob_id,
            'entry_date': yesterday + timedelta(hours=2),
        },
        # Plasmid qPCR: Plasmid copies
        {
            'test_id': 'test-plasmid-qpcr',
            'analyte_id': plasmid_copies_analyte_id,
            'raw_result': '2.45e8',
            'reported_result': '245000000',
            'qualifiers': None,
            'notes': 'Meets acceptance criteria for GMP lot release',
            'entered_by': alice_id,
            'entry_date': one_week_ago + timedelta(hours=6),
        },
    ]
    
    for result in results_data:
        connection.execute(
            sa.text("""
                INSERT INTO results (id, active, created_at, modified_at, test_id, analyte_id, raw_result, reported_result, qualifiers, description, entry_date, entered_by, created_by, modified_by)
                VALUES (gen_random_uuid(), true, NOW(), NOW(), :test_id, :analyte_id, :raw_result, :reported_result, :qualifiers, :notes, :entry_date, :entered_by, :entered_by, :entered_by)
                ON CONFLICT DO NOTHING
            """),
            seed_params(result)
        )
    
    # ========================================================================
    # Create batches with samples
    # ========================================================================
    batches_data = [
        {
            'id': 'batch-mab-elisa-001',
            'name': 'mAb-ELISA-Batch-20260120',
            'description': 'ELISA batch for mAb PK samples (T0, T1, T2)',
            'status': batch_in_process_id,
            'created_by': alice_id,
        },
        {
            'id': 'batch-cart-qc-001',
            'name': 'CAR-T-QC-Batch-20260119',
            'description': 'CAR-T in-process QC batch with blank control',
            'status': batch_completed_id,
            'created_by': bob_id,
        },
    ]
    
    for batch in batches_data:
        connection.execute(
            sa.text("""
                INSERT INTO batches (id, name, description, active, created_at, modified_at, status, created_by, modified_by)
                VALUES (:id, :name, :description, true, NOW(), NOW(), :status, :created_by, :created_by)
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(batch)
        )
    
    # Link containers to batches via batch_containers
    batch_containers_data = [
        {'batch_id': 'batch-mab-elisa-001', 'container_id': 'cont-mab-pk-t0'},
        {'batch_id': 'batch-mab-elisa-001', 'container_id': 'cont-mab-pk-t1'},
        {'batch_id': 'batch-mab-elisa-001', 'container_id': 'cont-mab-pk-t2'},
        {'batch_id': 'batch-cart-qc-001', 'container_id': 'cont-cart-batch1'},
        {'batch_id': 'batch-cart-qc-001', 'container_id': 'cont-cart-blank'},  # QC sample in batch
    ]
    
    for bc in batch_containers_data:
        connection.execute(
            sa.text("""
                INSERT INTO batch_containers (batch_id, container_id)
                VALUES (:batch_id, :container_id)
                ON CONFLICT (batch_id, container_id) DO NOTHING
            """),
            seed_params(bc)
        )
    
    print("✓ BioTech/Pharma sample lifecycle data loaded successfully")
    print("  - 7 samples spanning status workflow (Received → Available → Testing Complete → Reviewed)")
    print("  - Parent/aliquot relationship (depleted parent edge case)")
    print("  - 6 tests (completed, in-analysis, in-process)")
    print("  - 4 results entered")
    print("  - 2 batches (1 in-process, 1 completed) with QC sample")
    print("  - Edge cases: depleted parent (50µL remaining), QC blank sample")


def downgrade() -> None:
    """Rollback sample lifecycle data."""
    connection = op.get_bind()

    batch_ids = [as_id("batch-mab-elisa-001"), as_id("batch-cart-qc-001")]
    test_ids = [
        as_id("test-mab-pk-t0-elisa"),
        as_id("test-mab-pk-t1-elisa"),
        as_id("test-mab-pk-t2-elisa"),
        as_id("test-cart-viability"),
        as_id("test-cart-blank-viability"),
        as_id("test-plasmid-qpcr"),
    ]
    sample_ids = [
        as_id("sample-mab-pk-t0"),
        as_id("sample-mab-pk-t1"),
        as_id("sample-mab-pk-t2"),
        as_id("sample-mab-pk-t0-aliquot"),
        as_id("sample-cart-batch1"),
        as_id("sample-cart-blank"),
        as_id("sample-plasmid-lot1"),
    ]
    container_ids = [
        as_id("cont-mab-pk-t0"),
        as_id("cont-mab-pk-t1"),
        as_id("cont-mab-pk-t2"),
        as_id("cont-mab-pk-t0-aliq"),
        as_id("cont-cart-batch1"),
        as_id("cont-cart-blank"),
        as_id("cont-plasmid-lot1"),
        as_id("cont-plate96-elisa"),
    ]

    connection.execute(
        sa.text("DELETE FROM batch_containers WHERE batch_id = ANY(:ids)"),
        {"ids": batch_ids},
    )
    connection.execute(
        sa.text("DELETE FROM batches WHERE id = ANY(:ids)"),
        {"ids": batch_ids},
    )
    connection.execute(
        sa.text("DELETE FROM results WHERE test_id = ANY(:ids)"),
        {"ids": test_ids},
    )
    connection.execute(
        sa.text("DELETE FROM tests WHERE id = ANY(:ids)"),
        {"ids": test_ids},
    )
    connection.execute(
        sa.text("DELETE FROM contents WHERE sample_id = ANY(:ids)"),
        {"ids": sample_ids},
    )
    connection.execute(
        sa.text("DELETE FROM samples WHERE id = ANY(:ids)"),
        {"ids": sample_ids},
    )
    connection.execute(
        sa.text("DELETE FROM containers WHERE id = ANY(:ids)"),
        {"ids": container_ids},
    )

    print("✓ BioTech/Pharma sample lifecycle data rolled back")
