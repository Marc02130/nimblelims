-- Schema Functions for NimbleLIMS
-- Contains all database functions used for RLS and access control

-- Function to get current user ID from session variable
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS UUID AS $$
BEGIN
    RETURN COALESCE(
        current_setting('app.current_user_id', true)::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if current user is Administrator
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
DECLARE
    user_role_name TEXT;
BEGIN
    SELECT r.name INTO user_role_name
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE u.id = current_user_id();
    
    RETURN user_role_name = 'Administrator';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enhanced function to check if user has access to a project
-- Based on System client for lab employees and client_id matching for client users
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_client_project_id UUID;
    project_client_id UUID;
    user_client_id UUID;
    system_client_id UUID;
BEGIN
    -- Admin users can access all projects
    IF is_admin() THEN
        RETURN TRUE;
    END IF;
    
    -- Get System client ID (hardcoded for performance, or query by name='System')
    -- System client ID: '00000000-0000-0000-0000-000000000001'
    system_client_id := '00000000-0000-0000-0000-000000000001'::UUID;
    
    -- Get user's client_id
    SELECT u.client_id INTO user_client_id
    FROM users u
    WHERE u.id = current_user_id();
    
    -- If user is associated with System client, grant full access (lab employees)
    IF user_client_id = system_client_id THEN
        RETURN TRUE;
    END IF;
    
    -- Get the project's client_project_id and client_id
    SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
    FROM projects p
    WHERE p.id = project_uuid;
    
    -- If project has a client_project_id, check access via client_projects
    IF project_client_project_id IS NOT NULL THEN
        -- Check if user's client_id matches the client_project's client_id
        IF user_client_id IS NOT NULL THEN
            IF EXISTS (
                SELECT 1 FROM client_projects cp
                WHERE cp.id = project_client_project_id
                AND cp.client_id = user_client_id
            ) THEN
                RETURN TRUE;
            END IF;
        END IF;
    END IF;
    
    -- For regular client users: check if project.client_id matches user.client_id
    IF project_client_id IS NOT NULL AND user_client_id IS NOT NULL THEN
        IF project_client_id = user_client_id THEN
            RETURN TRUE;
        END IF;
    END IF;
    
    -- Fall back to direct project access check (for granular grants via project_users junction)
    -- This allows lab staff to be assigned to specific projects even if not System client
    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
        AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
