-- Verify and fix sample:update permission for Lab Tech and Lab Manager roles
-- Run this script to diagnose and fix the issue where Lab Tech/Manager cannot edit samples
--
-- There are TWO layers of access control for sample editing:
-- 1. Permission-based: User must have 'sample:update' permission (role_permissions table)
-- 2. Project-based: User must have access to the sample's project (project_users table or client match)

-- ============================================================================
-- PART 1: PERMISSION VERIFICATION
-- ============================================================================

-- 1. Show all roles and their permissions
SELECT 
    r.name as role_name,
    r.id as role_id,
    array_agg(p.name ORDER BY p.name) as permissions
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
WHERE r.active = true
GROUP BY r.id, r.name
ORDER BY r.name;

-- 2. Check if sample:update permission exists
SELECT id, name, description, active 
FROM permissions 
WHERE name = 'sample:update';

-- 3. Check which roles have sample:update permission
SELECT 
    r.name as role_name,
    p.name as permission_name
FROM role_permissions rp
JOIN roles r ON rp.role_id = r.id
JOIN permissions p ON rp.permission_id = p.id
WHERE p.name = 'sample:update'
ORDER BY r.name;

-- 4. Fix: Add sample:update permission to Lab Manager if missing
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Lab Manager'),
    (SELECT id FROM permissions WHERE name = 'sample:update')
WHERE NOT EXISTS (
    SELECT 1 FROM role_permissions rp
    JOIN roles r ON rp.role_id = r.id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE r.name = 'Lab Manager' AND p.name = 'sample:update'
);

-- 5. Fix: Add sample:update permission to Lab Technician if missing
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Lab Technician'),
    (SELECT id FROM permissions WHERE name = 'sample:update')
WHERE NOT EXISTS (
    SELECT 1 FROM role_permissions rp
    JOIN roles r ON rp.role_id = r.id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE r.name = 'Lab Technician' AND p.name = 'sample:update'
);

-- ============================================================================
-- PART 2: PROJECT ACCESS VERIFICATION
-- ============================================================================

-- 6. Check users and their client associations
SELECT 
    u.id, 
    u.name as user_name, 
    u.username, 
    r.name as role, 
    u.client_id,
    c.name as client_name
FROM users u
JOIN roles r ON u.role_id = r.id
LEFT JOIN clients c ON u.client_id = c.id
WHERE u.active = true
AND r.name IN ('Lab Manager', 'Lab Technician')
ORDER BY r.name, u.name;

-- 7. Check project_users table - which users have access to which projects
SELECT 
    u.name as user_name,
    r.name as role,
    count(pu.project_id) as projects_with_access
FROM users u
JOIN roles r ON u.role_id = r.id
LEFT JOIN project_users pu ON u.id = pu.user_id
WHERE r.name IN ('Lab Manager', 'Lab Technician')
GROUP BY u.name, r.name
ORDER BY u.name;

-- 8. Check projects and their client associations
SELECT 
    p.id,
    p.name as project_name,
    c.name as client_name,
    cp.name as client_project_name
FROM projects p
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN client_projects cp ON p.client_project_id = cp.id
WHERE p.active = true
ORDER BY p.name;

-- 9. Fix: Grant Lab Manager access to all active projects
INSERT INTO project_users (project_id, user_id)
SELECT p.id, u.id
FROM projects p
CROSS JOIN users u
JOIN roles r ON u.role_id = r.id
WHERE p.active = true
AND r.name = 'Lab Manager'
ON CONFLICT (project_id, user_id) DO NOTHING;

-- 10. Fix: Grant Lab Technician access to all active projects
INSERT INTO project_users (project_id, user_id)
SELECT p.id, u.id
FROM projects p
CROSS JOIN users u
JOIN roles r ON u.role_id = r.id
WHERE p.active = true
AND r.name = 'Lab Technician'
ON CONFLICT (project_id, user_id) DO NOTHING;

-- ============================================================================
-- PART 3: VERIFICATION
-- ============================================================================

-- 11. Verify the fix - show updated permissions for Lab roles
SELECT 
    r.name as role_name,
    array_agg(p.name ORDER BY p.name) as permissions
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
WHERE r.name IN ('Lab Manager', 'Lab Technician')
GROUP BY r.id, r.name
ORDER BY r.name;

-- 12. Verify the fix - show project access counts
SELECT 
    u.name as user_name,
    r.name as role,
    count(pu.project_id) as projects_with_access
FROM users u
JOIN roles r ON u.role_id = r.id
LEFT JOIN project_users pu ON u.id = pu.user_id
WHERE r.name IN ('Lab Manager', 'Lab Technician')
GROUP BY u.name, r.name
ORDER BY u.name;

-- IMPORTANT: After running this script, users must LOG OUT and LOG BACK IN
-- to receive updated permissions in their JWT token!
