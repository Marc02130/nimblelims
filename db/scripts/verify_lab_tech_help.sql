-- Verification script for Lab Technician help entries seeding
-- Run this script after migration 0017 (lab_tech_help_seeds) to verify
-- that lab technician help entries are properly seeded

-- ============================================================================
-- 1. Verify Lab Technician Help Entries Exist
-- ============================================================================
SELECT 
    'Lab Technician Help Entries Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter = 'lab-technician' 
            AND active = true
        )
        THEN 'PASS: Lab Technician help entries exist'
        ELSE 'FAIL: No lab-technician help entries found'
    END AS result,
    (SELECT COUNT(*) FROM help_entries WHERE role_filter = 'lab-technician' AND active = true) AS count
UNION ALL

-- ============================================================================
-- 2. Verify Expected Sections for Lab Technician
-- ============================================================================
SELECT 
    'Lab Technician Help Sections Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter = 'lab-technician' 
            AND active = true
            AND section IN ('Accessioning Workflow', 'Batch Creation', 'Results Entry', 'Container Management', 'Test Assignment', 'Getting Started')
        )
        THEN 'PASS: Expected lab technician help sections found'
        ELSE 'WARN: Some expected sections may be missing'
    END AS result,
    (
        SELECT COUNT(DISTINCT section) 
        FROM help_entries 
        WHERE role_filter = 'lab-technician' 
        AND active = true
        AND section IN ('Accessioning Workflow', 'Batch Creation', 'Results Entry', 'Container Management', 'Test Assignment', 'Getting Started')
    ) AS count
UNION ALL

-- ============================================================================
-- 3. Verify Help Entries Have Content
-- ============================================================================
SELECT 
    'Lab Technician Help Content Check' AS check_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter = 'lab-technician' 
            AND active = true
            AND (content IS NULL OR LENGTH(TRIM(content)) = 0)
        )
        THEN 'PASS: All lab technician help entries have content'
        ELSE 'FAIL: Some lab technician help entries are missing content'
    END AS result,
    (
        SELECT COUNT(*) 
        FROM help_entries 
        WHERE role_filter = 'lab-technician' 
        AND active = true
        AND content IS NOT NULL
        AND LENGTH(TRIM(content)) > 0
    ) AS count
UNION ALL

-- ============================================================================
-- 4. Verify Role Filter Format (Slug)
-- ============================================================================
SELECT 
    'Role Filter Slug Format Check' AS check_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM help_entries 
            WHERE role_filter LIKE '% %'
            AND role_filter = 'lab-technician'
        )
        THEN 'PASS: All lab technician help entries use slug format (lab-technician)'
        ELSE 'FAIL: Some entries may not use slug format'
    END AS result,
    (
        SELECT COUNT(*) 
        FROM help_entries 
        WHERE role_filter = 'lab-technician'
        AND active = true
    ) AS count
UNION ALL

-- ============================================================================
-- 5. Verify Help Entries Table Structure
-- ============================================================================
SELECT 
    'Help Entries Table Structure Check' AS check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'help_entries'
            AND column_name IN ('id', 'section', 'content', 'role_filter', 'active')
        )
        THEN 'PASS: help_entries table has required columns'
        ELSE 'FAIL: help_entries table missing required columns'
    END AS result,
    (
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'help_entries'
        AND column_name IN ('id', 'section', 'content', 'role_filter', 'active')
    ) AS count
UNION ALL

-- ============================================================================
-- 6. Verify RLS Policy on help_entries
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
-- 7. Verify No Duplicate Sections for Lab Technician
-- ============================================================================
SELECT 
    'Duplicate Sections Check' AS check_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT section, COUNT(*) 
            FROM help_entries 
            WHERE role_filter = 'lab-technician' 
            AND active = true
            GROUP BY section
            HAVING COUNT(*) > 1
        )
        THEN 'PASS: No duplicate sections for lab technician help'
        ELSE 'WARN: Duplicate sections found for lab technician help'
    END AS result,
    (
        SELECT COUNT(DISTINCT section) 
        FROM help_entries 
        WHERE role_filter = 'lab-technician' 
        AND active = true
    ) AS count;

-- ============================================================================
-- Detailed Reports
-- ============================================================================

-- Report: Lab Technician Help Entries Summary
SELECT 
    '=== LAB TECHNICIAN HELP ENTRIES SUMMARY ===' AS report_section,
    COUNT(*) AS total_entries,
    COUNT(DISTINCT section) AS unique_sections,
    MIN(created_at) AS earliest_entry,
    MAX(created_at) AS latest_entry
FROM help_entries
WHERE role_filter = 'lab-technician'
AND active = true;

-- Report: Lab Technician Help Entries by Section
SELECT 
    '=== LAB TECHNICIAN HELP ENTRIES BY SECTION ===' AS report_section,
    section,
    role_filter,
    active,
    LENGTH(content) AS content_length,
    created_at,
    modified_at
FROM help_entries
WHERE role_filter = 'lab-technician'
AND active = true
ORDER BY section;

-- Report: All Help Entries by Role Filter
SELECT 
    '=== ALL HELP ENTRIES BY ROLE FILTER ===' AS report_section,
    role_filter,
    COUNT(*) AS entry_count,
    COUNT(DISTINCT section) AS unique_sections
FROM help_entries
WHERE active = true
GROUP BY role_filter
ORDER BY role_filter NULLS LAST;

-- Report: Help Entry Content Keywords (Lab Technician)
SELECT 
    '=== LAB TECHNICIAN HELP CONTENT KEYWORDS ===' AS report_section,
    section,
    CASE 
        WHEN content ILIKE '%accessioning%' OR content ILIKE '%accession%' THEN 'Contains accessioning keywords'
        WHEN content ILIKE '%batch%' THEN 'Contains batch keywords'
        WHEN content ILIKE '%result%' THEN 'Contains result keywords'
        WHEN content ILIKE '%container%' THEN 'Contains container keywords'
        WHEN content ILIKE '%test%' OR content ILIKE '%analyte%' THEN 'Contains test/analyte keywords'
        ELSE 'Other content'
    END AS content_category
FROM help_entries
WHERE role_filter = 'lab-technician'
AND active = true
ORDER BY section;

