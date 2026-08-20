"""Add comprehensive BioTech/Pharma test dataset for UAT and automated testing

Revision ID: 0058
Revises: 0057
Create Date: 2026-01-20 00:00:00.000000

This migration adds realistic, comprehensive seed data for both automated tests
and human UAT covering the full sample lifecycle:
- 2 clients/orgs (internal biotech + CRO) with proper RLS isolation
- Users across roles with project_users wiring
- BioTech/Pharma sample types, matrices, container types
- Realistic projects (mAb PK study, cell therapy, plasmid production)
- Full sample lifecycle: accessioning → aliquots → tests → results → review
- Edge cases: depleted parent, QC samples, rejected samples, incomplete tests
- Multi-user RBAC scenarios

Backward compat: Keeps "Project Alpha/Beta" aliases for existing UAT scripts.
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
revision = '0058'
down_revision = '0057'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # ========================================================================
    # 1. Replace environmental matrices with BioTech/Pharma matrices
    # ========================================================================
    # Get matrix list ID
    matrix_list_result = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'Matrix Types' LIMIT 1")
    ).fetchone()
    matrix_list_id = str(matrix_list_result[0]) if matrix_list_result else '66666666-6666-6666-6666-666666666666'
    
    # Add BioTech/Pharma matrices (keep old ones for backward compat, mark as deprecated in description)
    biotech_matrices = [
        {'name': 'Plasma (K2EDTA)', 'description': 'Plasma anticoagulated with K2EDTA'},
        {'name': 'Plasma (Heparin)', 'description': 'Plasma anticoagulated with heparin'},
        {'name': 'Serum', 'description': 'Serum (clotted whole blood, no anticoagulant)'},
        {'name': 'Whole Blood', 'description': 'Whole blood (anticoagulated)'},
        {'name': 'PBMC', 'description': 'Peripheral blood mononuclear cells'},
        {'name': 'Tissue Homogenate', 'description': 'Homogenized tissue sample'},
        {'name': 'Cell Supernatant', 'description': 'Cell culture supernatant'},
        {'name': 'Cell Lysate', 'description': 'Cell lysate (protein extraction)'},
        {'name': 'Purified Protein', 'description': 'Purified protein preparation'},
        {'name': 'Antibody Solution', 'description': 'Purified antibody in formulation buffer'},
        {'name': 'Plasmid DNA', 'description': 'Plasmid DNA preparation'},
        {'name': 'Genomic DNA', 'description': 'Genomic DNA extraction'},
        {'name': 'Total RNA', 'description': 'Total RNA extraction'},
        {'name': 'Lyophilized Powder', 'description': 'Lyophilized drug product or API'},
        {'name': 'Formulation Buffer', 'description': 'Drug formulation in buffer'},
        {'name': 'Urine', 'description': 'Urine sample'},
        {'name': 'CSF', 'description': 'Cerebrospinal fluid'},
        # Keep legacy environmental for backward compat
        {'name': 'Soil (legacy)', 'description': 'Soil sample (legacy environmental - use BioTech matrices)'},
        {'name': 'Sludge (legacy)', 'description': 'Sludge (legacy environmental - use BioTech matrices)'},
        {'name': 'Ground Water (legacy)', 'description': 'Ground Water (legacy environmental - use BioTech matrices)'},
    ]
    
    for matrix in biotech_matrices:
        connection.execute(
            sa.text("""
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO NOTHING
            """),
            {'name': matrix['name'], 'description': matrix['description'], 'list_id': matrix_list_id}
        )
    
    # ========================================================================
    # 2. Add BioTech/Pharma sample types
    # ========================================================================
    sample_type_list_result = connection.execute(
        sa.text("SELECT id FROM lists WHERE name = 'Sample Types' LIMIT 1")
    ).fetchone()
    sample_type_list_id = str(sample_type_list_result[0]) if sample_type_list_result else '55555555-5555-5555-5555-555555555555'
    
    biotech_sample_types = [
        # Already have Blood, Urine, Tissue from 0004
        {'name': 'Plasma', 'description': 'Plasma sample'},
        {'name': 'Serum', 'description': 'Serum sample'},
        {'name': 'PBMC', 'description': 'Peripheral blood mononuclear cells'},
        {'name': 'Cell Line', 'description': 'Cultured cell line'},
        {'name': 'Primary Cells', 'description': 'Primary cells (non-immortalized)'},
        {'name': 'Plasmid DNA', 'description': 'Plasmid DNA'},
        {'name': 'Protein', 'description': 'Purified protein'},
        {'name': 'Antibody', 'description': 'Monoclonal or polyclonal antibody'},
        {'name': 'Drug Product', 'description': 'Final drug product formulation'},
        {'name': 'API', 'description': 'Active pharmaceutical ingredient'},
        {'name': 'Excipient', 'description': 'Pharmaceutical excipient'},
        {'name': 'Reference Standard', 'description': 'Reference standard or control material'},
        {'name': 'QC Sample', 'description': 'Quality control sample'},
    ]
    
    for sample_type in biotech_sample_types:
        connection.execute(
            sa.text("""
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO NOTHING
            """),
            {'name': sample_type['name'], 'description': sample_type['description'], 'list_id': sample_type_list_id}
        )
    
    # ========================================================================
    # 3. Add BioTech/Pharma container types
    # ========================================================================
    biotech_container_types = [
        {'id': 'ctype-001-cryovial', 'name': 'Cryovial (2mL)', 'description': 'Standard 2mL cryogenic vial', 'capacity': 2.0, 'material': 'polypropylene', 'dimensions': '1x1', 'preservative': None},
        {'id': 'ctype-002-conical15', 'name': '15mL Conical Tube', 'description': '15mL conical centrifuge tube', 'capacity': 15.0, 'material': 'polypropylene', 'dimensions': '1x1', 'preservative': None},
        {'id': 'ctype-003-conical50', 'name': '50mL Conical Tube', 'description': '50mL conical centrifuge tube', 'capacity': 50.0, 'material': 'polypropylene', 'dimensions': '1x1', 'preservative': None},
        {'id': 'ctype-004-plate96', 'name': '96-Well Plate', 'description': 'Standard 96-well microtiter plate', 'capacity': 0.2, 'material': 'polystyrene', 'dimensions': '8x12', 'preservative': None},
        {'id': 'ctype-005-plate384', 'name': '384-Well Plate', 'description': 'High-throughput 384-well plate', 'capacity': 0.05, 'material': 'polystyrene', 'dimensions': '16x24', 'preservative': None},
        {'id': 'ctype-006-microtube', 'name': 'Microcentrifuge Tube (1.5mL)', 'description': 'Standard 1.5mL microcentrifuge tube', 'capacity': 1.5, 'material': 'polypropylene', 'dimensions': '1x1', 'preservative': None},
        {'id': 'ctype-007-serum-tube', 'name': 'Serum Collection Tube (10mL)', 'description': '10mL serum separator tube', 'capacity': 10.0, 'material': 'glass', 'dimensions': '1x1', 'preservative': 'clot activator'},
        {'id': 'ctype-008-edta-tube', 'name': 'K2EDTA Tube (5mL)', 'description': '5mL EDTA anticoagulant tube', 'capacity': 5.0, 'material': 'plastic', 'dimensions': '1x1', 'preservative': 'K2EDTA'},
    ]
    
    for ctype in biotech_container_types:
        connection.execute(
            sa.text("""
                INSERT INTO container_types (id, name, description, capacity, material, dimensions, preservative, active, created_at, modified_at)
                VALUES (:id, :name, :description, :capacity, :material, :dimensions, :preservative, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(ctype)
        )
    
    # ========================================================================
    # 4. Add BioTech/Pharma units
    # ========================================================================
    # Get unit type IDs
    conc_type = connection.execute(
        sa.text("SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'concentration'")
    ).fetchone()
    mass_type = connection.execute(
        sa.text("SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'mass'")
    ).fetchone()
    vol_type = connection.execute(
        sa.text("SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'volume'")
    ).fetchone()
    molar_type = connection.execute(
        sa.text("SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'molar'")
    ).fetchone()
    
    conc_type_id = str(conc_type[0]) if conc_type else None
    mass_type_id = str(mass_type[0]) if mass_type else None
    vol_type_id = str(vol_type[0]) if vol_type else None
    molar_type_id = str(molar_type[0]) if molar_type else None
    
    biotech_units = [
        # Concentration units (ng/µL, mg/mL, µg/mL common for BioTech)
        {'name': 'ng/µL', 'description': 'Nanograms per microliter', 'multiplier': 1.0, 'type_id': conc_type_id},
        {'name': 'µg/mL', 'description': 'Micrograms per milliliter', 'multiplier': 1.0, 'type_id': conc_type_id},
        {'name': 'mg/mL', 'description': 'Milligrams per milliliter', 'multiplier': 1000.0, 'type_id': conc_type_id},
        {'name': 'pg/mL', 'description': 'Picograms per milliliter', 'multiplier': 0.001, 'type_id': conc_type_id},
        # Molar units (nM, µM, mM common for drug discovery)
        {'name': 'nM', 'description': 'Nanomolar', 'multiplier': 0.000001, 'type_id': molar_type_id},
        {'name': 'µM', 'description': 'Micromolar', 'multiplier': 0.001, 'type_id': molar_type_id},
        {'name': 'mM', 'description': 'Millimolar', 'multiplier': 1.0, 'type_id': molar_type_id},
        # Volume units (µL very common)
        {'name': 'µL', 'description': 'Microliter', 'multiplier': 0.001, 'type_id': vol_type_id},
        {'name': 'mL', 'description': 'Milliliter', 'multiplier': 1.0, 'type_id': vol_type_id},
        # Mass units
        {'name': 'ng', 'description': 'Nanogram', 'multiplier': 0.000001, 'type_id': mass_type_id},
        {'name': 'µg', 'description': 'Microgram', 'multiplier': 0.001, 'type_id': mass_type_id},
        {'name': 'mg', 'description': 'Milligram', 'multiplier': 1.0, 'type_id': mass_type_id},
    ]
    
    for unit in biotech_units:
        if unit['type_id']:  # Only insert if type exists
            connection.execute(
                sa.text("""
                    INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                    VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :multiplier, :type_id)
                    ON CONFLICT (name) DO NOTHING
                """),
                unit
            )
    
    # ========================================================================
    # 5. Create 2 client organizations (internal biotech + CRO)
    # ========================================================================
    clients_data = [
        {
            'id': 'client-biotech-001',
            'name': 'NovaBio Therapeutics',
            'abbreviation': 'NBIO',
            'description': 'Internal biotech company - oncology mAb development',
            'billing_info': '{"address": "1200 Innovation Dr", "city": "South San Francisco", "state": "CA", "zip": "94080", "contact": "finance@novabio.example.com"}'
        },
        {
            'id': 'client-cro-002',
            'name': 'PharmaTest CRO',
            'abbreviation': 'PTCRO',
            'description': 'Contract Research Organization - outsourced analytical services',
            'billing_info': '{"address": "500 Research Pkwy", "city": "Cambridge", "state": "MA", "zip": "02138", "contact": "billing@pharmatest.example.com"}'
        },
    ]
    
    for client in clients_data:
        connection.execute(
            sa.text("""
                INSERT INTO clients (id, name, abbreviation, description, active, created_at, modified_at, billing_info)
                VALUES (:id, :name, :abbreviation, :description, true, NOW(), NOW(), CAST(:billing_info AS jsonb))
                ON CONFLICT (id) DO NOTHING
            """),
            seed_params(client)
        )
    
    # ========================================================================
    # 6. Create users across roles with RBAC
    # ========================================================================
    # Get role IDs
    admin_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'Administrator'")).fetchone()
    tech_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'Lab Technician'")).fetchone()
    manager_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'Lab Manager'")).fetchone()
    client_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'Client'")).fetchone()
    
    admin_role_id = str(admin_role[0]) if admin_role else 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    tech_role_id = str(tech_role[0]) if tech_role else 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    manager_role_id = str(manager_role[0]) if manager_role else 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    client_role_id = str(client_role[0]) if client_role else 'dddddddd-dddd-dddd-dddd-dddddddddddd'
    
    # Import password hashing (assume bcrypt)
    from app.core.security import get_password_hash
    
    users_data = [
        # Existing users: admin, lab-tech, lab-manager, client (from earlier migrations)
        # Add new users for multi-user scenarios
        {
            'id': 'user-tech-alice',
            'name': 'Alice Chen',
            'username': 'alice-tech',
            'email': 'alice.chen@novabio.example.com',
            'password': 'alice123',
            'role_id': tech_role_id,
            'client_id': 'client-biotech-001',
        },
        {
            'id': 'user-tech-bob',
            'name': 'Bob Martinez',
            'username': 'bob-tech',
            'email': 'bob.martinez@novabio.example.com',
            'password': 'bob123',
            'role_id': tech_role_id,
            'client_id': 'client-biotech-001',
        },
        {
            'id': 'user-manager-carol',
            'name': 'Carol Davidson',
            'username': 'carol-manager',
            'email': 'carol.davidson@novabio.example.com',
            'password': 'carol123',
            'role_id': manager_role_id,
            'client_id': 'client-biotech-001',
        },
        {
            'id': 'user-client-cro',
            'name': 'David Lee',
            'username': 'david-cro',
            'email': 'david.lee@pharmatest.example.com',
            'password': 'david123',
            'role_id': client_role_id,
            'client_id': 'client-cro-002',
        },
    ]
    
    for user_data in users_data:
        password_hash = get_password_hash(user_data['password'])
        connection.execute(
            sa.text("""
                INSERT INTO users (id, name, username, email, password_hash, active, created_at, modified_at, role_id, client_id)
                VALUES (:id, :name, :username, :email, :password_hash, true, NOW(), NOW(), :role_id, :client_id)
                ON CONFLICT (username) DO NOTHING
            """),
            seed_params({
                'id': user_data['id'],
                'name': user_data['name'],
                'username': user_data['username'],
                'email': user_data['email'],
                'password_hash': password_hash,
                'role_id': user_data['role_id'],
                'client_id': user_data['client_id'],
            })
        )
    
    # ========================================================================
    # 7. Create BioTech/Pharma projects with backward-compat aliases
    # ========================================================================
    # Get status IDs
    active_status = connection.execute(
        sa.text("SELECT id FROM list_entries WHERE list_id = '33333333-3333-3333-3333-333333333333' AND name = 'Active'")
    ).fetchone()
    active_status_id = str(active_status[0]) if active_status else None
    
    # Get admin user ID (for created_by)
    admin_user = connection.execute(sa.text("SELECT id FROM users WHERE username = 'admin' LIMIT 1")).fetchone()
    admin_user_id = str(admin_user[0]) if admin_user else None
    
    projects_data = [
        {
            'id': 'proj-mab-pk-001',
            'name': 'mAb-2301 PK Study',
            'description': 'Pharmacokinetic study for anti-PD-1 monoclonal antibody mAb-2301 in mouse xenograft model. Plasma PK samples across 10 timepoints.',
            'client_id': 'client-biotech-001',
            'status': active_status_id,
        },
        {
            'id': 'proj-cell-therapy-002',
            'name': 'CAR-T In-Process Testing',
            'description': 'In-process QC panel for CAR-T cell therapy manufacturing: viability, identity, potency, sterility. Covers release criteria for Phase I clinical trial.',
            'client_id': 'client-biotech-001',
            'status': active_status_id,
        },
        {
            'id': 'proj-plasmid-003',
            'name': 'Plasmid Lot Release Testing',
            'description': 'Plasmid DNA production lot release: identity (sequencing), purity (A260/280, endotoxin), quantity (absorbance, qPCR). GMP-grade for gene therapy vector manufacturing.',
            'client_id': 'client-biotech-001',
            'status': active_status_id,
        },
        {
            'id': 'proj-cro-sponsor-004',
            'name': 'Sponsor XYZ - Bioanalytical Services',
            'description': 'Outsourced bioanalytical testing for Sponsor XYZ: ELISA, qPCR, HPLC. Multi-study support for preclinical PK/PD.',
            'client_id': 'client-cro-002',
            'status': active_status_id,
        },
        # Backward compat aliases for existing UAT scripts
        {
            'id': 'proj-alpha-legacy',
            'name': 'Project Alpha',
            'description': 'Legacy project name (alias for mAb-2301 PK Study) - backward compat for UAT scripts',
            'client_id': 'client-biotech-001',
            'status': active_status_id,
        },
        {
            'id': 'proj-beta-legacy',
            'name': 'Project Beta',
            'description': 'Legacy project name (alias for CAR-T In-Process Testing) - backward compat for UAT scripts. Used for RLS testing (inaccessible project).',
            'client_id': 'client-biotech-001',
            'status': active_status_id,
        },
    ]
    
    for project in projects_data:
        connection.execute(
            sa.text("""
                INSERT INTO projects (id, name, description, active, created_at, modified_at, client_id, status, created_by, modified_by, start_date)
                VALUES (:id, :name, :description, true, NOW(), NOW(), :client_id, :status, :created_by, :modified_by, NOW())
                ON CONFLICT (name) DO NOTHING
            """),
            seed_params({
                'id': project['id'],
                'name': project['name'],
                'description': project['description'],
                'client_id': project['client_id'],
                'status': project['status'],
                'created_by': admin_user_id,
                'modified_by': admin_user_id,
            })
        )
    
    # ========================================================================
    # 8. Wire project_users for RBAC/RLS scenarios
    # ========================================================================
    # Alice can access proj-mab-pk-001 and proj-alpha-legacy
    # Bob can access proj-cell-therapy-002 and proj-beta-legacy
    # Carol (manager) can access all NovaBio projects
    # David (CRO client) can only access proj-cro-sponsor-004
    # admin/lab-tech/lab-manager can access proj-alpha and proj-mab (for backward compat)
    
    # Get user IDs for existing users
    existing_tech = connection.execute(sa.text("SELECT id FROM users WHERE username = 'lab-tech' LIMIT 1")).fetchone()
    existing_manager = connection.execute(sa.text("SELECT id FROM users WHERE username = 'lab-manager' LIMIT 1")).fetchone()
    
    existing_tech_id = str(existing_tech[0]) if existing_tech else None
    existing_manager_id = str(existing_manager[0]) if existing_manager else None
    
    project_users_data = [
        # Alice: mAb PK + Project Alpha (backward compat)
        {'project_id': 'proj-mab-pk-001', 'user_id': 'user-tech-alice'},
        {'project_id': 'proj-alpha-legacy', 'user_id': 'user-tech-alice'},
        # Bob: CAR-T + Project Beta (backward compat)
        {'project_id': 'proj-cell-therapy-002', 'user_id': 'user-tech-bob'},
        {'project_id': 'proj-beta-legacy', 'user_id': 'user-tech-bob'},
        # Carol: all NovaBio projects
        {'project_id': 'proj-mab-pk-001', 'user_id': 'user-manager-carol'},
        {'project_id': 'proj-cell-therapy-002', 'user_id': 'user-manager-carol'},
        {'project_id': 'proj-plasmid-003', 'user_id': 'user-manager-carol'},
        {'project_id': 'proj-alpha-legacy', 'user_id': 'user-manager-carol'},
        {'project_id': 'proj-beta-legacy', 'user_id': 'user-manager-carol'},
        # David: CRO project only
        {'project_id': 'proj-cro-sponsor-004', 'user_id': 'user-client-cro'},
        # Existing lab-tech: Alpha and mAb (for backward compat with existing UAT)
        {'project_id': 'proj-alpha-legacy', 'user_id': existing_tech_id} if existing_tech_id else None,
        {'project_id': 'proj-mab-pk-001', 'user_id': existing_tech_id} if existing_tech_id else None,
        # Existing lab-manager: all NovaBio projects
        {'project_id': 'proj-mab-pk-001', 'user_id': existing_manager_id} if existing_manager_id else None,
        {'project_id': 'proj-cell-therapy-002', 'user_id': existing_manager_id} if existing_manager_id else None,
        {'project_id': 'proj-plasmid-003', 'user_id': existing_manager_id} if existing_manager_id else None,
        {'project_id': 'proj-alpha-legacy', 'user_id': existing_manager_id} if existing_manager_id else None,
        {'project_id': 'proj-beta-legacy', 'user_id': existing_manager_id} if existing_manager_id else None,
    ]
    
    for pu in project_users_data:
        if pu:  # Skip None entries
            connection.execute(
                sa.text("""
                    INSERT INTO project_users (project_id, user_id, granted_at)
                    VALUES (:project_id, :user_id, NOW())
                    ON CONFLICT (project_id, user_id) DO NOTHING
                """),
                seed_params(pu)
            )
    
    # ========================================================================
    # 9. Add BioTech/Pharma analyses (complement existing Cell Viability, etc. from 0027)
    # ========================================================================
    # Add more realistic BioTech assays
    biotech_analyses = [
        {
            'id': 'analysis-elisa-001',
            'name': 'ELISA (Human IgG)',
            'description': 'Sandwich ELISA for quantification of human IgG in plasma/serum',
            'method': 'Plate-based immunoassay, TMB substrate, 450nm absorbance',
            'turnaround_time': 2,
            'cost': 75.00,
            'shelf_life': 30,  # Days after sample collection
        },
        {
            'id': 'analysis-qpcr-001',
            'name': 'qPCR (Plasmid Copy Number)',
            'description': 'Quantitative PCR for plasmid DNA copy number determination',
            'method': 'TaqMan probe-based qPCR, CFX96 instrument',
            'turnaround_time': 1,
            'cost': 50.00,
            'shelf_life': 90,
        },
        {
            'id': 'analysis-hplc-001',
            'name': 'HPLC (Purity/Identity)',
            'description': 'Reverse-phase HPLC for purity and identity of mAb/protein',
            'method': 'C18 column, UV detection at 280nm, gradient elution',
            'turnaround_time': 3,
            'cost': 120.00,
            'shelf_life': 30,
        },
        {
            'id': 'analysis-endotoxin-001',
            'name': 'Endotoxin (LAL)',
            'description': 'Limulus Amebocyte Lysate assay for endotoxin quantification',
            'method': 'Kinetic chromogenic LAL assay, plate reader',
            'turnaround_time': 1,
            'cost': 45.00,
            'shelf_life': 7,
        },
        {
            'id': 'analysis-viability-001',
            'name': 'Cell Viability (Trypan Blue)',
            'description': 'Manual cell count with trypan blue exclusion',
            'method': 'Hemocytometer or automated cell counter',
            'turnaround_time': 1,
            'cost': 25.00,
            'shelf_life': 1,  # Must test immediately
        },
        {
            'id': 'analysis-identity-seq-001',
            'name': 'Identity (Sanger Sequencing)',
            'description': 'Sanger sequencing for plasmid/gene identity confirmation',
            'method': 'Bi-directional Sanger sequencing, BLAST alignment',
            'turnaround_time': 5,
            'cost': 150.00,
            'shelf_life': 90,
        },
        # Keep EPA Method 8080 for backward compat
        {
            'id': 'analysis-epa-8080-legacy',
            'name': 'EPA Method 8080',
            'description': 'Legacy environmental analysis (backward compat) - Organochlorine pesticides by GC/ECD',
            'method': 'Gas chromatography with electron capture detection',
            'turnaround_time': 7,
            'cost': 200.00,
            'shelf_life': 14,
        },
    ]
    
    for analysis in biotech_analyses:
        connection.execute(
            sa.text("""
                INSERT INTO analyses (id, name, description, method, turnaround_time, cost, shelf_life, active, created_at, modified_at, custom_attributes)
                VALUES (:id, :name, :description, :method, :turnaround_time, :cost, :shelf_life, true, NOW(), NOW(), '{}')
                ON CONFLICT (name) DO NOTHING
            """),
            seed_params(analysis)
        )
    
    # ========================================================================
    # 10. Add analytes for new analyses
    # ========================================================================
    # Get unit IDs
    ng_ml = connection.execute(sa.text("SELECT id FROM units WHERE name = 'µg/mL' LIMIT 1")).fetchone()
    ng_ul = connection.execute(sa.text("SELECT id FROM units WHERE name = 'ng/µL' LIMIT 1")).fetchone()
    percent = connection.execute(sa.text("SELECT id FROM units WHERE name = '%' LIMIT 1")).fetchone()
    eu_ml = connection.execute(sa.text("SELECT id FROM units WHERE name = 'EU/mL' LIMIT 1")).fetchone()
    copies_ul = connection.execute(sa.text("SELECT id FROM units WHERE name = 'copies/µL' LIMIT 1")).fetchone()
    
    ng_ml_id = str(ng_ml[0]) if ng_ml else None
    ng_ul_id = str(ng_ul[0]) if ng_ul else None
    percent_id = str(percent[0]) if percent else None
    
    # Add EU/mL and copies/µL if they don't exist
    if not eu_ml:
        connection.execute(
            sa.text("""
                INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                VALUES (gen_random_uuid(), 'EU/mL', 'Endotoxin units per milliliter', true, NOW(), NOW(), 1.0, :conc_type)
                ON CONFLICT (name) DO NOTHING
            """),
            {'conc_type': conc_type_id}
        )
        eu_ml = connection.execute(sa.text("SELECT id FROM units WHERE name = 'EU/mL' LIMIT 1")).fetchone()
    eu_ml_id = str(eu_ml[0]) if eu_ml else None
    
    if not copies_ul:
        connection.execute(
            sa.text("""
                INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                VALUES (gen_random_uuid(), 'copies/µL', 'DNA copies per microliter', true, NOW(), NOW(), 1.0, :conc_type)
                ON CONFLICT (name) DO NOTHING
            """),
            {'conc_type': conc_type_id}
        )
        copies_ul = connection.execute(sa.text("SELECT id FROM units WHERE name = 'copies/µL' LIMIT 1")).fetchone()
    copies_ul_id = str(copies_ul[0]) if copies_ul else None
    
    biotech_analytes = [
        {'id': 'analyte-igg-conc', 'name': 'IgG Concentration', 'description': 'Human IgG concentration by ELISA', 'cas_number': None, 'units_default': ng_ml_id, 'data_type': 'numeric'},
        {'id': 'analyte-plasmid-copies', 'name': 'Plasmid Copy Number', 'description': 'Plasmid DNA copies by qPCR', 'cas_number': None, 'units_default': copies_ul_id, 'data_type': 'numeric'},
        {'id': 'analyte-purity-percent', 'name': 'Purity (%)', 'description': 'Percent purity by HPLC peak area', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        {'id': 'analyte-endotoxin', 'name': 'Endotoxin Level', 'description': 'Endotoxin by LAL assay', 'cas_number': None, 'units_default': eu_ml_id, 'data_type': 'numeric'},
        {'id': 'analyte-viability', 'name': 'Viability (%)', 'description': 'Percent viable cells by trypan blue exclusion', 'cas_number': None, 'units_default': percent_id, 'data_type': 'numeric'},
        {'id': 'analyte-cell-count', 'name': 'Total Cell Count', 'description': 'Total cells per mL', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
        {'id': 'analyte-identity-pass', 'name': 'Identity Result', 'description': 'Pass/Fail for sequence identity', 'cas_number': None, 'units_default': None, 'data_type': 'text'},
        {'id': 'analyte-a260-280', 'name': 'A260/A280 Ratio', 'description': 'Absorbance ratio for nucleic acid purity', 'cas_number': None, 'units_default': None, 'data_type': 'numeric'},
    ]
    
    for analyte in biotech_analytes:
        connection.execute(
            sa.text("""
                INSERT INTO analytes (id, name, description, active, created_at, modified_at, cas_number, units_default, data_type, custom_attributes)
                VALUES (:id, :name, :description, true, NOW(), NOW(), :cas_number, :units_default, :data_type, '{}')
                ON CONFLICT (name) DO NOTHING
            """),
            seed_params(analyte)
        )
    
    # ========================================================================
    # 11. Link analytes to analyses (analysis_analytes junction with validation)
    # ========================================================================
    analysis_analytes = [
        # ELISA
        {'analysis_id': 'analysis-elisa-001', 'analyte_id': 'analyte-igg-conc', 'data_type': 'numeric', 'high_value': 10000.0, 'low_value': 0.0, 'significant_figures': 3, 'display_order': 1, 'is_required': True},
        # qPCR
        {'analysis_id': 'analysis-qpcr-001', 'analyte_id': 'analyte-plasmid-copies', 'data_type': 'numeric', 'high_value': None, 'low_value': 0.0, 'significant_figures': 3, 'display_order': 1, 'is_required': True},
        {'analysis_id': 'analysis-qpcr-001', 'analyte_id': 'analyte-a260-280', 'data_type': 'numeric', 'high_value': 2.2, 'low_value': 1.7, 'significant_figures': 2, 'display_order': 2, 'is_required': True},
        # HPLC
        {'analysis_id': 'analysis-hplc-001', 'analyte_id': 'analyte-purity-percent', 'data_type': 'numeric', 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 2, 'display_order': 1, 'is_required': True},
        # Endotoxin
        {'analysis_id': 'analysis-endotoxin-001', 'analyte_id': 'analyte-endotoxin', 'data_type': 'numeric', 'high_value': 10.0, 'low_value': 0.0, 'significant_figures': 3, 'display_order': 1, 'is_required': True},
        # Cell Viability
        {'analysis_id': 'analysis-viability-001', 'analyte_id': 'analyte-viability', 'data_type': 'numeric', 'high_value': 100.0, 'low_value': 0.0, 'significant_figures': 1, 'display_order': 1, 'is_required': True},
        {'analysis_id': 'analysis-viability-001', 'analyte_id': 'analyte-cell-count', 'data_type': 'numeric', 'high_value': None, 'low_value': 0.0, 'significant_figures': 2, 'display_order': 2, 'is_required': True},
        # Identity (Sequencing)
        {'analysis_id': 'analysis-identity-seq-001', 'analyte_id': 'analyte-identity-pass', 'data_type': 'text', 'high_value': None, 'low_value': None, 'significant_figures': None, 'display_order': 1, 'is_required': True},
    ]
    
    for junction in analysis_analytes:
        connection.execute(
            sa.text("""
                INSERT INTO analysis_analytes (analysis_id, analyte_id, data_type, list_id, high_value, low_value, significant_figures, calculation, reported_name, display_order, is_required, default_value)
                VALUES (:analysis_id, :analyte_id, :data_type, NULL, :high_value, :low_value, :significant_figures, NULL, NULL, :display_order, :is_required, NULL)
                ON CONFLICT (analysis_id, analyte_id) DO NOTHING
            """),
            seed_params(junction)
        )
    
    # ========================================================================
    # 12. Create test battery (In-Process QC Panel for CAR-T)
    # ========================================================================
    battery_data = {
        'id': 'battery-cart-qc-001',
        'name': 'CAR-T In-Process QC Panel',
        'description': 'Standard in-process QC panel for CAR-T manufacturing: viability, identity, sterility (endotoxin). Run in sequence.',
        'active': True,
    }
    
    connection.execute(
        sa.text("""
            INSERT INTO test_batteries (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, :active, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """),
        seed_params(battery_data)
    )
    
    # Link analyses to battery with sequence
    battery_analyses = [
        {'battery_id': 'battery-cart-qc-001', 'analysis_id': 'analysis-viability-001', 'sequence': 1, 'optional': False},
        {'battery_id': 'battery-cart-qc-001', 'analysis_id': 'analysis-identity-seq-001', 'sequence': 2, 'optional': False},
        {'battery_id': 'battery-cart-qc-001', 'analysis_id': 'analysis-endotoxin-001', 'sequence': 3, 'optional': False},
    ]
    
    for ba in battery_analyses:
        connection.execute(
            sa.text("""
                INSERT INTO battery_analyses (battery_id, analysis_id, sequence, optional)
                VALUES (:battery_id, :analysis_id, :sequence, :optional)
                ON CONFLICT (battery_id, analysis_id) DO NOTHING
            """),
            seed_params(ba)
        )
    
    print("✓ BioTech/Pharma comprehensive seed data loaded successfully")
    print("  - 2 clients (NovaBio Therapeutics, PharmaTest CRO)")
    print("  - 4 new users (alice-tech, bob-tech, carol-manager, david-cro)")
    print("  - 6 projects (4 BioTech + 2 legacy aliases for backward compat)")
    print("  - BioTech sample types, matrices, container types")
    print("  - 7 BioTech analyses (ELISA, qPCR, HPLC, Endotoxin, Viability, Identity, EPA legacy)")
    print("  - 1 test battery (CAR-T In-Process QC Panel)")
    print("  - project_users wiring for multi-user RBAC scenarios")
    print("  - Backward compat: Project Alpha/Beta aliases, EPA Method 8080, legacy matrices")


def downgrade() -> None:
    """Rollback comprehensive seed data (deletes seeded records by known IDs)."""
    connection = op.get_bind()

    analysis_ids = [
        as_id("analysis-elisa-001"),
        as_id("analysis-qpcr-001"),
        as_id("analysis-hplc-001"),
        as_id("analysis-endotoxin-001"),
        as_id("analysis-viability-001"),
        as_id("analysis-identity-seq-001"),
        as_id("analysis-epa-8080-legacy"),
    ]
    analyte_ids = [
        as_id("analyte-igg-conc"),
        as_id("analyte-plasmid-copies"),
        as_id("analyte-purity-percent"),
        as_id("analyte-endotoxin"),
        as_id("analyte-viability"),
        as_id("analyte-cell-count"),
        as_id("analyte-identity-pass"),
        as_id("analyte-a260-280"),
    ]
    project_ids = [
        as_id("proj-mab-pk-001"),
        as_id("proj-cell-therapy-002"),
        as_id("proj-plasmid-003"),
        as_id("proj-cro-sponsor-004"),
        as_id("proj-alpha-legacy"),
        as_id("proj-beta-legacy"),
    ]
    user_ids = [
        as_id("user-tech-alice"),
        as_id("user-tech-bob"),
        as_id("user-manager-carol"),
        as_id("user-client-cro"),
    ]
    client_ids = [
        as_id("client-biotech-001"),
        as_id("client-cro-002"),
    ]
    container_type_ids = [
        as_id("ctype-001-cryovial"),
        as_id("ctype-002-conical15"),
        as_id("ctype-003-conical50"),
        as_id("ctype-004-plate96"),
        as_id("ctype-005-plate384"),
        as_id("ctype-006-microtube"),
        as_id("ctype-007-serum-tube"),
        as_id("ctype-008-edta-tube"),
    ]
    battery_id = as_id("battery-cart-qc-001")

    connection.execute(
        sa.text("DELETE FROM battery_analyses WHERE battery_id = :id"),
        {"id": battery_id},
    )
    connection.execute(
        sa.text("DELETE FROM test_batteries WHERE id = :id"),
        {"id": battery_id},
    )
    connection.execute(
        sa.text("DELETE FROM analysis_analytes WHERE analysis_id = ANY(:ids)"),
        {"ids": analysis_ids},
    )
    connection.execute(
        sa.text("DELETE FROM analytes WHERE id = ANY(:ids)"),
        {"ids": analyte_ids},
    )
    connection.execute(
        sa.text("DELETE FROM analyses WHERE id = ANY(:ids)"),
        {"ids": analysis_ids},
    )
    connection.execute(
        sa.text("DELETE FROM project_users WHERE project_id = ANY(:ids)"),
        {"ids": project_ids},
    )
    connection.execute(
        sa.text("DELETE FROM projects WHERE id = ANY(:ids)"),
        {"ids": project_ids},
    )
    connection.execute(
        sa.text("DELETE FROM users WHERE id = ANY(:ids)"),
        {"ids": user_ids},
    )
    connection.execute(
        sa.text("DELETE FROM clients WHERE id = ANY(:ids)"),
        {"ids": client_ids},
    )
    connection.execute(
        sa.text("DELETE FROM container_types WHERE id = ANY(:ids)"),
        {"ids": container_type_ids},
    )

    print("✓ BioTech/Pharma comprehensive seed data rolled back")
