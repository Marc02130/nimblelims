"""Add initial data for NimbleLims

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-01 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create connection for data insertion
    connection = op.get_bind()
    
    # Insert initial lists
    lists_data = [
        {'id': '11111111-1111-1111-1111-111111111111', 'name': 'Sample Status', 'description': 'Sample status values'},
        {'id': '22222222-2222-2222-2222-222222222222', 'name': 'Test Status', 'description': 'Test status values'},
        {'id': '33333333-3333-3333-3333-333333333333', 'name': 'Project Status', 'description': 'Project status values'},
        {'id': '44444444-4444-4444-4444-444444444444', 'name': 'Batch Status', 'description': 'Batch status values'},
        {'id': '55555555-5555-5555-5555-555555555555', 'name': 'Sample Types', 'description': 'Sample type values'},
        {'id': '66666666-6666-6666-6666-666666666666', 'name': 'Matrix Types', 'description': 'Matrix type values'},
        {'id': '77777777-7777-7777-7777-777777777777', 'name': 'QC Types', 'description': 'QC type values'},
        {'id': '88888888-8888-8888-8888-888888888888', 'name': 'Unit Types', 'description': 'Unit type values'},
        {'id': '99999999-9999-9999-9999-999999999999', 'name': 'Contact Types', 'description': 'Contact method types'},
    ]
    
    for list_data in lists_data:
        connection.execute(
            sa.text("""
                INSERT INTO lists (id, name, description, active, created_at, modified_at)
                VALUES (:id, :name, :description, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            list_data
        )
    
    # Insert list entries
    list_entries_data = [
        # Sample Status
        {'list_id': '11111111-1111-1111-1111-111111111111', 'name': 'Received', 'description': 'Sample received'},
        {'list_id': '11111111-1111-1111-1111-111111111111', 'name': 'Available for Testing', 'description': 'Ready for testing'},
        {'list_id': '11111111-1111-1111-1111-111111111111', 'name': 'Testing Complete', 'description': 'Testing finished'},
        {'list_id': '11111111-1111-1111-1111-111111111111', 'name': 'Reviewed', 'description': 'Results reviewed'},
        {'list_id': '11111111-1111-1111-1111-111111111111', 'name': 'Reported', 'description': 'Results reported'},
        
        # Test Status
        {'list_id': '22222222-2222-2222-2222-222222222222', 'name': 'In Process', 'description': 'Test in progress'},
        {'list_id': '22222222-2222-2222-2222-222222222222', 'name': 'In Analysis', 'description': 'Under analysis'},
        {'list_id': '22222222-2222-2222-2222-222222222222', 'name': 'Complete', 'description': 'Test completed'},
        
        # Project Status
        {'list_id': '33333333-3333-3333-3333-333333333333', 'name': 'Active', 'description': 'Project active'},
        {'list_id': '33333333-3333-3333-3333-333333333333', 'name': 'Completed', 'description': 'Project completed'},
        {'list_id': '33333333-3333-3333-3333-333333333333', 'name': 'On Hold', 'description': 'Project on hold'},
        
        # Batch Status
        {'list_id': '44444444-4444-4444-4444-444444444444', 'name': 'Created', 'description': 'Batch created'},
        {'list_id': '44444444-4444-4444-4444-444444444444', 'name': 'In Process', 'description': 'Batch in process'},
        {'list_id': '44444444-4444-4444-4444-444444444444', 'name': 'Completed', 'description': 'Batch completed'},
        
        # Sample Types
        {'list_id': '55555555-5555-5555-5555-555555555555', 'name': 'Blood', 'description': 'Blood sample'},
        {'list_id': '55555555-5555-5555-5555-555555555555', 'name': 'Urine', 'description': 'Urine sample'},
        {'list_id': '55555555-5555-5555-5555-555555555555', 'name': 'Tissue', 'description': 'Tissue sample'},
        {'list_id': '55555555-5555-5555-5555-555555555555', 'name': 'Water', 'description': 'Water sample'},
        
        # Matrix Types
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Sludge', 'description':  'Sludge'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Ground Water', 'description': 'Ground Water'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Surface Water', 'description': 'Surface Water'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Soil', 'description': 'Soil'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Air', 'description': 'Air'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Drinking Water', 'description': 'Drinking Water'},
        
        # QC Types
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Sample', 'description': 'Regular sample'},
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Positive Control', 'description': 'Positive control'},
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Negative Control', 'description': 'Negative control'},
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Matrix Spike', 'description': 'Matrix spike'},
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Duplicate', 'description': 'Duplicate sample'},
        {'list_id': '77777777-7777-7777-7777-777777777777', 'name': 'Blank', 'description': 'Blank sample'},
        
        # Unit Types
        {'list_id': '88888888-8888-8888-8888-888888888888', 'name': 'concentration', 'description': 'Concentration units'},
        {'list_id': '88888888-8888-8888-8888-888888888888', 'name': 'mass', 'description': 'Mass units'},
        {'list_id': '88888888-8888-8888-8888-888888888888', 'name': 'volume', 'description': 'Volume units'},
        {'list_id': '88888888-8888-8888-8888-888888888888', 'name': 'molar', 'description': 'Molar units'},
        
        # Contact Types
        {'list_id': '99999999-9999-9999-9999-999999999999', 'name': 'Email', 'description': 'Email address'},
        {'list_id': '99999999-9999-9999-9999-999999999999', 'name': 'Phone', 'description': 'Phone number'},
        {'list_id': '99999999-9999-9999-9999-999999999999', 'name': 'Mobile', 'description': 'Mobile phone'},
    ]
    
    for entry_data in list_entries_data:
        connection.execute(
            sa.text("""
                INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id)
                VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :list_id)
                ON CONFLICT (list_id, name) DO NOTHING
            """),
            entry_data
        )
    
    # Insert roles
    roles_data = [
        {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'name': 'Administrator', 'description': 'System administrator'},
        {'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'name': 'Lab Manager', 'description': 'Laboratory manager'},
        {'id': 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'name': 'Lab Technician', 'description': 'Laboratory technician'},
        {'id': 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'name': 'Client', 'description': 'Client user'},
    ]
    
    for role_data in roles_data:
        connection.execute(
            sa.text("""
                INSERT INTO roles (id, name, description, active, created_at, modified_at)
                VALUES (:id, :name, :description, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            role_data
        )
    
    # Insert permissions
    permissions_data = [
        {'id': 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'name': 'user:manage', 'description': 'Manage users'},
        {'id': 'ffffffff-ffff-ffff-ffff-ffffffffffff', 'name': 'role:manage', 'description': 'Manage roles'},
        {'id': 'a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0', 'name': 'config:edit', 'description': 'Edit configuration'},
        {'id': 'b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0', 'name': 'project:manage', 'description': 'Manage projects'},
        {'id': 'c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0', 'name': 'sample:create', 'description': 'Create samples'},
        {'id': 'd0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0', 'name': 'sample:read', 'description': 'Read samples'},
        {'id': 'e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0', 'name': 'sample:update', 'description': 'Update samples'},
        {'id': 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'name': 'test:assign', 'description': 'Assign tests'},
        {'id': 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'name': 'test:update', 'description': 'Update tests'},
        {'id': 'b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1', 'name': 'result:enter', 'description': 'Enter results'},
        {'id': 'c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1', 'name': 'result:review', 'description': 'Review results'},
        {'id': 'd1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1', 'name': 'batch:manage', 'description': 'Manage batches'},
        {'id': 'e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1', 'name': 'batch:read', 'description': 'Read batches'},
    ]
    
    for perm_data in permissions_data:
        connection.execute(
            sa.text("""
                INSERT INTO permissions (id, name, description, active, created_at, modified_at)
                VALUES (:id, :name, :description, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            perm_data
        )
    
    # Insert role-permission mappings
    role_permissions_data = [
        # Administrator gets all permissions
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ffffffff-ffff-ffff-ffff-ffffffffffff'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'd0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'd1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1'),
        
        # Lab Manager permissions
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'd0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1'),  # batch:read
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'd1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1'),
        
        # Lab Technician permissions
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'd0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'd1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1'),
        
        # Client permissions
        ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'd0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0'),
    ]
    
    for role_id, perm_id in role_permissions_data:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:role_id, :perm_id)
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {'role_id': role_id, 'perm_id': perm_id}
        )
    
    # Insert base units
    units_data = [
        {'name': 'g/L', 'description': 'Grams per liter', 'multiplier': 1.0, 'type': 'concentration'},
        {'name': 'mg/L', 'description': 'Milligrams per liter', 'multiplier': 0.001, 'type': 'concentration'},
        {'name': 'µg/L', 'description': 'Micrograms per liter', 'multiplier': 0.000001, 'type': 'concentration'},
        {'name': 'g', 'description': 'Grams', 'multiplier': 1.0, 'type': 'mass'},
        {'name': 'mg', 'description': 'Milligrams', 'multiplier': 0.001, 'type': 'mass'},
        {'name': 'µg', 'description': 'Micrograms', 'multiplier': 0.000001, 'type': 'mass'},
        {'name': 'L', 'description': 'Liters', 'multiplier': 1.0, 'type': 'volume'},
        {'name': 'mL', 'description': 'Milliliters', 'multiplier': 0.001, 'type': 'volume'},
        {'name': 'µL', 'description': 'Microliters', 'multiplier': 0.000001, 'type': 'volume'},
        {'name': 'mol/L', 'description': 'Moles per liter', 'multiplier': 1.0, 'type': 'molar'},
        {'name': 'mmol/L', 'description': 'Millimoles per liter', 'multiplier': 0.001, 'type': 'molar'},
    ]
    
    for unit_data in units_data:
        # Get the unit type ID
        result = connection.execute(
            sa.text("""
                SELECT id FROM list_entries 
                WHERE list_id = '88888888-8888-8888-8888-888888888888' 
                AND name = :type_name
            """),
            {'type_name': unit_data['type']}
        ).fetchone()
        
        if result:
            connection.execute(
                sa.text("""
                    INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type)
                    VALUES (gen_random_uuid(), :name, :description, true, NOW(), NOW(), :multiplier, :type_id)
                    ON CONFLICT (name) DO NOTHING
                """),
                {
                    'name': unit_data['name'],
                    'description': unit_data['description'],
                    'multiplier': unit_data['multiplier'],
                    'type_id': result[0]
                }
            )
    
    # Create a default client for the admin user
    connection.execute(
        sa.text("""
            INSERT INTO clients (id, name, description, active, created_at, modified_at, billing_info) 
            VALUES ('00000000-0000-0000-0000-000000000001', 'System', 'System client for admin users', true, NOW(), NOW(), '{}')
            ON CONFLICT (id) DO NOTHING
        """)
    )
    
    # Create initial admin user
    # Use ON CONFLICT on username to handle re-runs
    connection.execute(
        sa.text("""
            INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active, created_at, modified_at) 
            VALUES ('00000000-0000-0000-0000-000000000001', 'System Administrator', 'admin', 'admin@lims.example.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '00000000-0000-0000-0000-000000000001', true, NOW(), NOW())
            ON CONFLICT (username) DO NOTHING
        """)
    )
    
    # Create lab-manager user
    connection.execute(
        sa.text("""
            INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active, created_at, modified_at) 
            VALUES ('00000000-0000-0000-0000-000000000002', 'Lab Manager', 'lab-manager', 'lab-manager@lims.example.com', '7dd63afe29407aa45af7fdd4388b71195b552688c2750abd42bdf3b231c13b69', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '00000000-0000-0000-0000-000000000001', true, NOW(), NOW())
            ON CONFLICT (username) DO NOTHING
        """)
    )
    
    # Create lab-tech user
    connection.execute(
        sa.text("""
            INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active, created_at, modified_at) 
            VALUES ('00000000-0000-0000-0000-000000000003', 'Lab Technician', 'lab-tech', 'lab-tech@lims.example.com', 'd81968c60a8a41bdafcb3c5825bf8bc4a76dccc932d673e3f9a7b71ce4538596', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '00000000-0000-0000-0000-000000000001', true, NOW(), NOW())
            ON CONFLICT (username) DO NOTHING
        """)
    )


def downgrade() -> None:
    # Delete all data in reverse order
    connection = op.get_bind()
    
    connection.execute(sa.text("DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000003'"))  # lab-tech
    connection.execute(sa.text("DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000002'"))  # lab-manager
    connection.execute(sa.text("DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000001'"))  # admin
    connection.execute(sa.text("DELETE FROM clients WHERE id = '00000000-0000-0000-0000-000000000001'"))
    connection.execute(sa.text("DELETE FROM role_permissions"))
    connection.execute(sa.text("DELETE FROM permissions"))
    connection.execute(sa.text("DELETE FROM roles"))
    connection.execute(sa.text("DELETE FROM units"))
    connection.execute(sa.text("DELETE FROM list_entries"))
    connection.execute(sa.text("DELETE FROM lists"))
