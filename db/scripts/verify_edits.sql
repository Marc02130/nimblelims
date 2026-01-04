-- Verification Script: Sample/Test/Container Editing
-- Purpose: Verify that audit fields (modified_at, modified_by) are updated correctly after PATCH operations
-- Version: 2.0 (Added editing for samples/tests/containers)

-- Check indexes exist for efficient editing queries
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('samples', 'tests', 'containers')
    AND indexname LIKE '%modified%'
ORDER BY tablename, indexname;

-- Verify sample edit audit fields
-- Expected: modified_at and modified_by should be updated after PATCH /samples/{id}
SELECT 
    s.id,
    s.name,
    s.created_at,
    s.created_by,
    s.modified_at,
    s.modified_by,
    CASE 
        WHEN s.modified_at > s.created_at THEN 'PASS: modified_at updated'
        WHEN s.modified_at = s.created_at THEN 'CHECK: modified_at not updated (may be new record)'
        ELSE 'FAIL: modified_at before created_at'
    END AS audit_check,
    u1.username AS created_by_username,
    u2.username AS modified_by_username
FROM samples s
LEFT JOIN users u1 ON s.created_by = u1.id
LEFT JOIN users u2 ON s.modified_by = u2.id
WHERE s.active = true
ORDER BY s.modified_at DESC
LIMIT 10;

-- Verify test edit audit fields
-- Expected: modified_at and modified_by should be updated after PATCH /tests/{id}
SELECT 
    t.id,
    t.name,
    t.created_at,
    t.created_by,
    t.modified_at,
    t.modified_by,
    CASE 
        WHEN t.modified_at > t.created_at THEN 'PASS: modified_at updated'
        WHEN t.modified_at = t.created_at THEN 'CHECK: modified_at not updated (may be new record)'
        ELSE 'FAIL: modified_at before created_at'
    END AS audit_check,
    u1.username AS created_by_username,
    u2.username AS modified_by_username
FROM tests t
LEFT JOIN users u1 ON t.created_by = u1.id
LEFT JOIN users u2 ON t.modified_by = u2.id
WHERE t.active = true
ORDER BY t.modified_at DESC
LIMIT 10;

-- Verify container edit audit fields
-- Expected: modified_at and modified_by should be updated after PATCH /containers/{id}
SELECT 
    c.id,
    c.name,
    c.created_at,
    c.created_by,
    c.modified_at,
    c.modified_by,
    CASE 
        WHEN c.modified_at > c.created_at THEN 'PASS: modified_at updated'
        WHEN c.modified_at = c.created_at THEN 'CHECK: modified_at not updated (may be new record)'
        ELSE 'FAIL: modified_at before created_at'
    END AS audit_check,
    u1.username AS created_by_username,
    u2.username AS modified_by_username
FROM containers c
LEFT JOIN users u1 ON c.created_by = u1.id
LEFT JOIN users u2 ON c.modified_by = u2.id
WHERE c.active = true
ORDER BY c.modified_at DESC
LIMIT 10;

-- Verify test:update permission exists
-- Expected: Permission should exist for test editing
SELECT 
    id,
    name,
    description,
    active,
    created_at
FROM permissions
WHERE name = 'test:update'
    AND active = true;

-- Count samples/tests/containers with recent modifications (last 24 hours)
-- Useful for verifying edit operations are working
SELECT 
    'samples' AS entity_type,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN modified_at > NOW() - INTERVAL '24 hours' THEN 1 END) AS modified_last_24h,
    COUNT(CASE WHEN modified_at > created_at THEN 1 END) AS ever_modified
FROM samples
WHERE active = true

UNION ALL

SELECT 
    'tests' AS entity_type,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN modified_at > NOW() - INTERVAL '24 hours' THEN 1 END) AS modified_last_24h,
    COUNT(CASE WHEN modified_at > created_at THEN 1 END) AS ever_modified
FROM tests
WHERE active = true

UNION ALL

SELECT 
    'containers' AS entity_type,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN modified_at > NOW() - INTERVAL '24 hours' THEN 1 END) AS modified_last_24h,
    COUNT(CASE WHEN modified_at > created_at THEN 1 END) AS ever_modified
FROM containers
WHERE active = true;

-- Verify custom attributes can be updated
-- Expected: Samples/tests/containers with custom_attributes should be updatable
SELECT 
    'samples' AS entity_type,
    COUNT(*) AS total_with_custom_attrs,
    COUNT(CASE WHEN custom_attributes IS NOT NULL AND jsonb_typeof(custom_attributes) = 'object' THEN 1 END) AS valid_jsonb
FROM samples
WHERE active = true
    AND custom_attributes IS NOT NULL

UNION ALL

SELECT 
    'tests' AS entity_type,
    COUNT(*) AS total_with_custom_attrs,
    COUNT(CASE WHEN custom_attributes IS NOT NULL AND jsonb_typeof(custom_attributes) = 'object' THEN 1 END) AS valid_jsonb
FROM tests
WHERE active = true
    AND custom_attributes IS NOT NULL

UNION ALL

SELECT 
    'containers' AS entity_type,
    COUNT(*) AS total_with_custom_attrs,
    COUNT(CASE WHEN custom_attributes IS NOT NULL AND jsonb_typeof(custom_attributes) = 'object' THEN 1 END) AS valid_jsonb
FROM containers
WHERE active = true
    AND custom_attributes IS NOT NULL;

-- Summary: Overall edit support verification
SELECT 
    'Edit Support Verification Summary' AS summary,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'samples' AND indexname LIKE '%modified%') AS sample_indexes,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'tests' AND indexname LIKE '%modified%') AS test_indexes,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'containers' AND indexname LIKE '%modified%') AS container_indexes,
    (SELECT COUNT(*) FROM permissions WHERE name = 'test:update' AND active = true) AS test_update_permission_exists;

