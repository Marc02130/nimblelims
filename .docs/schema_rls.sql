-- Row-Level Security (RLS) Policies for NimbleLIMS
-- Implements data isolation: client users see only their own data
-- Lab employees (System client) have full access

-- Enable RLS on all relevant tables
ALTER TABLE samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE results ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE containers ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_projects ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS projects_access ON projects;
DROP POLICY IF EXISTS samples_access ON samples;
DROP POLICY IF EXISTS tests_access ON tests;
DROP POLICY IF EXISTS results_access ON results;
DROP POLICY IF EXISTS batches_access ON batches;
DROP POLICY IF EXISTS containers_access ON containers;
DROP POLICY IF EXISTS client_projects_access ON client_projects;

-- Projects RLS Policy
-- Admins and System client users (lab employees) have full access
-- Client users can only see projects where project.client_id = user.client_id
-- Also allows project_users junction for granular grants
CREATE POLICY projects_access ON projects
FOR ALL
USING (
    is_admin() 
    OR has_project_access(id)
);

-- Samples RLS Policy
-- Access controlled via project access check
-- Client users only see samples from their own projects
CREATE POLICY samples_access ON samples
FOR ALL
USING (
    is_admin() 
    OR has_project_access(project_id)
);

-- Tests RLS Policy
-- Access controlled via sample's project
-- Client users only see tests for samples from their own projects
CREATE POLICY tests_access ON tests
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM samples s
        WHERE s.id = tests.sample_id
        AND has_project_access(s.project_id)
    )
);

-- Results RLS Policy
-- Access controlled via test → sample → project chain
-- Client users only see results for tests from their own projects
CREATE POLICY results_access ON results
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM tests t
        JOIN samples s ON t.sample_id = s.id
        WHERE t.id = results.test_id
        AND has_project_access(s.project_id)
    )
);

-- Batches RLS Policy
-- Access controlled via batch_containers → containers → contents → samples → projects
-- Client users only see batches containing samples from their own projects
CREATE POLICY batches_access ON batches
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM batch_containers bc
        JOIN containers c ON bc.container_id = c.id
        JOIN contents ct ON c.id = ct.container_id
        JOIN samples s ON ct.sample_id = s.id
        WHERE bc.batch_id = batches.id
        AND has_project_access(s.project_id)
    )
);

-- Containers RLS Policy
-- Access controlled via contents → samples → projects
-- Client users only see containers that contain samples from their own projects
CREATE POLICY containers_access ON containers
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM contents c
        JOIN samples s ON c.sample_id = s.id
        WHERE c.container_id = containers.id
        AND has_project_access(s.project_id)
    )
);

-- Client Projects RLS Policy
-- Admins: All client projects
-- System client users (lab employees): All active client projects (for sample creation workflows)
-- Client users: Only client projects matching their client_id
CREATE POLICY client_projects_access ON client_projects
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = client_projects.client_id
    )
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID  -- System client
        AND client_projects.active = true
    )
);
