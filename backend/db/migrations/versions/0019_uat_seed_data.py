"""Add UAT seed data for units, clients, client projects, and container types

Revision ID: 0019
Revises: 0018
Create Date: 2025-01-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add seed data for UAT testing: units, client, client project, container type."""
    connection = op.get_bind()
    
    # Get unit type IDs
    concentration_type_result = connection.execute(
        sa.text("""
            SELECT id FROM list_entries 
            WHERE list_id = '88888888-8888-8888-8888-888888888888' 
            AND name = 'concentration'
        """)
    ).fetchone()
    
    mass_type_result = connection.execute(
        sa.text("""
            SELECT id FROM list_entries 
            WHERE list_id = '88888888-8888-8888-8888-888888888888' 
            AND name = 'mass'
        """)
    ).fetchone()
    
    volume_type_result = connection.execute(
        sa.text("""
            SELECT id FROM list_entries 
            WHERE list_id = '88888888-8888-8888-8888-888888888888' 
            AND name = 'volume'
        """)
    ).fetchone()
    
    # Insert additional concentration units for UAT
    if concentration_type_result:
        concentration_units = [
            {'name': 'ng/L', 'description': 'Nanograms per liter', 'multiplier': 0.000000001, 'type_id': concentration_type_result[0]},
            {'name': 'ppb', 'description': 'Parts per billion', 'multiplier': 0.001, 'type_id': concentration_type_result[0]},
            {'name': 'ppm', 'description': 'Parts per million', 'multiplier': 1.0, 'type_id': concentration_type_result[0]},
        ]
        
        for unit_data in concentration_units:
            connection.execute(
                sa.text("""
                    INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                    VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :multiplier, :type_id)
                    ON CONFLICT (name) DO NOTHING
                """),
                unit_data
            )
    
    # Insert additional amount units (mass and volume) for UAT
    if mass_type_result:
        amount_mass_units = [
            {'name': 'kg', 'description': 'Kilograms', 'multiplier': 1000.0, 'type_id': mass_type_result[0]},
            {'name': 'ng', 'description': 'Nanograms', 'multiplier': 0.000000001, 'type_id': mass_type_result[0]},
        ]
        
        for unit_data in amount_mass_units:
            connection.execute(
                sa.text("""
                    INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                    VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :multiplier, :type_id)
                    ON CONFLICT (name) DO NOTHING
                """),
                unit_data
            )
    
    # Note: µL already exists in 0004_initial_data.py, so we don't add it here
    # Additional volume units can be added here if needed for UAT
    
    # Create UAT test client
    connection.execute(
        sa.text("""
            INSERT INTO clients (id, name, description, active, created_at, modified_at, billing_info) 
            VALUES (
                '11111111-1111-1111-1111-111111111111',
                'UAT Test Client',
                'Test client for UAT testing',
                true,
                NOW(),
                NOW(),
                '{"address": "123 Test St", "city": "Test City", "state": "TS", "zip": "12345"}'
            )
            ON CONFLICT (id) DO NOTHING
        """)
    )
    
    # Create UAT test client project
    connection.execute(
        sa.text("""
            INSERT INTO client_projects (id, name, description, client_id, active, created_at, modified_at)
            VALUES (
                '22222222-2222-2222-2222-222222222222',
                'UAT Test Project',
                'Test client project for UAT testing',
                '11111111-1111-1111-1111-111111111111',
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """)
    )
    
    # Assign the seeded "client" user (from 0013) to UAT Test Client instead of System client.
    # 0013 picks the first client by created_at, which was only System at that time, so the
    # client user incorrectly had client_id = System and could see everything. Fix that here.
    connection.execute(
        sa.text("""
            UPDATE users
            SET client_id = '11111111-1111-1111-1111-111111111111'
            WHERE username = 'client'
            AND client_id = '00000000-0000-0000-0000-000000000001'
        """)
    )
    
    # Create container types
    connection.execute(
        sa.text("""
            INSERT INTO container_types (id, name, description, capacity, material, dimensions, preservative, active, created_at, modified_at)
            VALUES (
                '33333333-3333-3333-3333-333333333333',
                'Test Tube (15mL)',
                'Standard 15mL test tube',
                15.0,
                'polypropylene',
                '15x100mm',
                NULL,
                true,
                NOW(),
                NOW()
            ),(
                '33333333-3333-3333-3333-433333333333',
                '1 Liter Amber Glass Bottle (1L)',
                '1 Liter Amber Glass Bottle',
                1,
                'glass',
                '95x225mm',
                NULL,
                true,
                NOW(),
                NOW()
            ),(
                '33333333-3333-3333-3333-533333333333',
                '1 Plastic Bottle (1L)',
                '1 Plastic Bottle',
                1,
                'HDPE',
                '91x205mm',
                NULL,
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """)
    )


def downgrade() -> None:
    """Remove UAT seed data."""
    connection = op.get_bind()
    
    # Revert "client" user back to System client before removing UAT client (FK)
    connection.execute(
        sa.text("""
            UPDATE users
            SET client_id = '00000000-0000-0000-0000-000000000001'
            WHERE username = 'client'
            AND client_id = '11111111-1111-1111-1111-111111111111'
        """)
    )
    
    # Remove container type
    connection.execute(
        sa.text("DELETE FROM container_types WHERE id in ('33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-433333333333', '33333333-3333-3333-3333-533333333333')")
    )
    
    # Remove client project
    connection.execute(
        sa.text("DELETE FROM client_projects WHERE id = '22222222-2222-2222-2222-222222222222'")
    )
    
    # Remove client
    connection.execute(
        sa.text("DELETE FROM clients WHERE id = '11111111-1111-1111-1111-111111111111'")
    )
    
    # Remove additional units (only the ones we added, not existing ones)
    additional_units = ['ng/L', 'ppb', 'ppm', 'kg', 'ng']
    for unit_name in additional_units:
        connection.execute(
            sa.text("DELETE FROM units WHERE name = :name"),
            {'name': unit_name}
        )

