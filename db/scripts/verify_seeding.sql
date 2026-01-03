-- Verification script for Client role and user seeding
-- Run this script after migrations 0015 (seed_client_role) and 0016 (help_entries)
-- to verify that the Client role, permissions, user, and help entries are properly seeded

-- ============================================================================
-- 1. Verify Client Role
-- ============================================================================
SELECT 
    'Client Role Check' AS check_type,
    CASE 
        WHEN EXISTS (SELECT 1 FROM roles WHERE name = 'Client') 
        THEN 'PASS: Client role exists'
        ELSE 'FAIL: Client role not found'
    END AS result,
    (SELECT COUNT(*) FROM roles WHERE name = 'Client') AS count
UNION ALL

-- ============================================================================
-- 2. Verify Client Role Permissions
-- ============================================================================
SELECT 
    'Client Role Permissions Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE r.name = 'Client'
            AND p.name IN ('sample:read', 'batch:read')
        )
        THEN 'PASS: Client role has expected permissions'
        ELSE 'FAIL: Client role missing expected permissions'
    END AS result,
    (
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        WHERE r.name = 'Client'
    ) AS count
UNION ALL

-- ============================================================================
-- 3. Verify Client User
-- ============================================================================
SELECT 
    'Client User Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = 'client'
            AND r.name = 'Client'
        )
        THEN 'PASS: Client user exists with correct role'
        ELSE 'FAIL: Client user not found or incorrect role'
    END AS result,
    (SELECT COUNT(*) FROM users WHERE username = 'client') AS count
UNION ALL

-- ============================================================================
-- 4. Verify Client User has client_id
-- ============================================================================
SELECT 
    'Client User client_id Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = 'client'
            AND r.name = 'Client'
            AND u.client_id IS NOT NULL
        )
        THEN 'PASS: Client user has client_id assigned'
        ELSE 'FAIL: Client user missing client_id'
    END AS result,
    (SELECT COUNT(*) FROM users WHERE username = 'client_user' AND client_id IS NOT NULL) AS count
UNION ALL

-- ============================================================================
-- 5. Verify Help Entries Table Exists
-- ============================================================================
SELECT 
    'Help Entries Table Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'help_entries'
        )
        THEN 'PASS: help_entries table exists'
        ELSE 'FAIL: help_entries table not found'
    END AS result,
    (SELECT COUNT(*) FROM help_entries) AS count
UNION ALL

-- ============================================================================
-- 6. Verify Client Help Entries
-- ============================================================================
SELECT 
    'Client Help Entries Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter = 'Client' 
            AND active = true
        )
        THEN 'PASS: Client help entries exist'
        ELSE 'FAIL: No Client help entries found'
    END AS result,
    (SELECT COUNT(*) FROM help_entries WHERE role_filter = 'Client' AND active = true) AS count
UNION ALL

-- ============================================================================
-- 7. Verify Public Help Entries
-- ============================================================================
SELECT 
    'Public Help Entries Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter IS NULL 
            AND active = true
        )
        THEN 'PASS: Public help entries exist'
        ELSE 'WARN: No public help entries found (optional)'
    END AS result,
    (SELECT COUNT(*) FROM help_entries WHERE role_filter IS NULL AND active = true) AS count
UNION ALL

-- ============================================================================
-- 8. Verify RLS Policy on help_entries
-- ============================================================================
SELECT 
    'RLS Policy Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE tablename = 'help_entries' 
            AND policyname = 'help_entries_access'
        )
        THEN 'PASS: RLS policy exists on help_entries'
        ELSE 'FAIL: RLS policy not found on help_entries'
    END AS result,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'help_entries') AS count
UNION ALL

-- ============================================================================
-- 9. Verify projects_access RLS Policy Updated
-- ============================================================================
SELECT 
    'Projects Access RLS Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE tablename = 'projects' 
            AND policyname = 'projects_access'
            AND definition LIKE '%Client%'
        )
        THEN 'PASS: projects_access policy includes Client role check'
        ELSE 'WARN: projects_access policy may not include Client role check'
    END AS result,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'projects' AND policyname = 'projects_access') AS count;

-- ============================================================================
-- Detailed Reports
-- ============================================================================

-- Report: Client Role Details
SELECT 
    '=== CLIENT ROLE DETAILS ===' AS report_section,
    r.id AS role_id,
    r.name AS role_name,
    r.description,
    r.active,
    COUNT(DISTINCT rp.permission_id) AS permission_count,
    COUNT(DISTINCT u.id) AS user_count
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN users u ON r.id = u.role_id
WHERE r.name = 'Client'
GROUP BY r.id, r.name, r.description, r.active;

-- Report: Client Role Permissions
SELECT 
    '=== CLIENT ROLE PERMISSIONS ===' AS report_section,
    p.name AS permission_name,
    p.description AS permission_description
FROM role_permissions rp
JOIN roles r ON rp.role_id = r.id
JOIN permissions p ON rp.permission_id = p.id
WHERE r.name = 'Client'
ORDER BY p.name;

-- Report: Client User Details
SELECT 
    '=== CLIENT USER DETAILS ===' AS report_section,
    u.id AS user_id,
    u.username,
    u.email,
    u.active,
    r.name AS role_name,
    u.client_id,
    c.name AS client_name
FROM users u
JOIN roles r ON u.role_id = r.id
LEFT JOIN clients c ON u.client_id = c.id
WHERE u.username = 'client'
AND r.name = 'Client';

-- Report: Help Entries Summary
SELECT 
    '=== HELP ENTRIES SUMMARY ===' AS report_section,
    role_filter,
    COUNT(*) AS entry_count,
    COUNT(DISTINCT section) AS unique_sections
FROM help_entries
WHERE active = true
GROUP BY role_filter
ORDER BY role_filter NULLS LAST;

-- Report: Help Entries by Section
SELECT 
    '=== HELP ENTRIES BY SECTION ===' AS report_section,
    section,
    role_filter,
    active,
    LENGTH(content) AS content_length,
    created_at
FROM help_entries
WHERE active = true
ORDER BY role_filter NULLS LAST, section;

