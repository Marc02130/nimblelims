"""Add initial data for LIMS MVP

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
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Human', 'description': 'Human matrix'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Environmental', 'description': 'Environmental matrix'},
        {'list_id': '66666666-6666-6666-6666-666666666666', 'name': 'Food', 'description': 'Food matrix'},
        
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
            """),
            role_data
        )
    
    # Insert permissions
    permissions_data = [
        {'id': 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'name': 'user:manage', 'description': 'Manage users'},
        {'id': 'ffffffff-ffff-ffff-ffff-ffffffffffff', 'name': 'role:manage', 'description': 'Manage roles'},
        {'id': 'gggggggg-gggg-gggg-gggg-gggggggggggg', 'name': 'config:edit', 'description': 'Edit configuration'},
        {'id': 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh', 'name': 'project:manage', 'description': 'Manage projects'},
        {'id': 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii', 'name': 'sample:create', 'description': 'Create samples'},
        {'id': 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj', 'name': 'sample:read', 'description': 'Read samples'},
        {'id': 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk', 'name': 'sample:update', 'description': 'Update samples'},
        {'id': 'llllllll-llll-llll-llll-llllllllllll', 'name': 'test:assign', 'description': 'Assign tests'},
        {'id': 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm', 'name': 'test:update', 'description': 'Update tests'},
        {'id': 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn', 'name': 'result:enter', 'description': 'Enter results'},
        {'id': 'oooooooo-oooo-oooo-oooo-oooooooooooo', 'name': 'result:review', 'description': 'Review results'},
        {'id': 'pppppppp-pppp-pppp-pppp-pppppppppppp', 'name': 'batch:manage', 'description': 'Manage batches'},
    ]
    
    for perm_data in permissions_data:
        connection.execute(
            sa.text("""
                INSERT INTO permissions (id, name, description, active, created_at, modified_at)
                VALUES (:id, :name, :description, true, NOW(), NOW())
            """),
            perm_data
        )
    
    # Insert role-permission mappings
    role_permissions_data = [
        # Administrator gets all permissions
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ffffffff-ffff-ffff-ffff-ffffffffffff'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'gggggggg-gggg-gggg-gggg-gggggggggggg'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'llllllll-llll-llll-llll-llllllllllll'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'oooooooo-oooo-oooo-oooo-oooooooooooo'),
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'pppppppp-pppp-pppp-pppp-pppppppppppp'),
        
        # Lab Manager permissions
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'llllllll-llll-llll-llll-llllllllllll'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'oooooooo-oooo-oooo-oooo-oooooooooooo'),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'pppppppp-pppp-pppp-pppp-pppppppppppp'),
        
        # Lab Technician permissions
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'llllllll-llll-llll-llll-llllllllllll'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn'),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'pppppppp-pppp-pppp-pppp-pppppppppppp'),
        
        # Client permissions
        ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
    ]
    
    for role_id, perm_id in role_permissions_data:
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:role_id, :perm_id)
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
                """),
                {
                    'name': unit_data['name'],
                    'description': unit_data['description'],
                    'multiplier': unit_data['multiplier'],
                    'type_id': result[0]
                }
            )


def downgrade() -> None:
    # Delete all data in reverse order
    connection = op.get_bind()
    
    connection.execute(sa.text("DELETE FROM role_permissions"))
    connection.execute(sa.text("DELETE FROM permissions"))
    connection.execute(sa.text("DELETE FROM roles"))
    connection.execute(sa.text("DELETE FROM units"))
    connection.execute(sa.text("DELETE FROM list_entries"))
    connection.execute(sa.text("DELETE FROM lists"))
