-- LIMS MVP Database Setup Script
-- This script creates the complete database schema for the LIMS MVP
-- Run this script to set up the database manually without Alembic

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if it doesn't exist (run as superuser)
-- SELECT 'CREATE DATABASE lims_db'
-- WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lims_db')\gexec

-- Connect to the lims_db database
-- \c lims_db;

-- =============================================
-- CORE TABLES
-- =============================================

-- Lists table (referenced by many other tables)
CREATE TABLE lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID
);

-- List entries table
CREATE TABLE list_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    list_id UUID NOT NULL REFERENCES lists(id)
);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID
);

-- Role permissions junction table
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id),
    permission_id UUID REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- Clients table
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    billing_info JSONB DEFAULT '{}'
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id),
    client_id UUID REFERENCES clients(id),
    last_login TIMESTAMP
);

-- Locations table
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    client_id UUID NOT NULL REFERENCES clients(id),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(255) DEFAULT 'US',
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    type UUID REFERENCES list_entries(id)
);

-- People table
CREATE TABLE people (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    role UUID REFERENCES list_entries(id)
);

-- People locations junction table
CREATE TABLE people_locations (
    person_id UUID REFERENCES people(id),
    location_id UUID REFERENCES locations(id),
    primary BOOLEAN DEFAULT FALSE,
    notes TEXT,
    PRIMARY KEY (person_id, location_id)
);

-- Contact methods table
CREATE TABLE contact_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(id),
    type UUID NOT NULL REFERENCES list_entries(id),
    value VARCHAR(255) NOT NULL,
    description TEXT,
    primary BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    start_date TIMESTAMP NOT NULL,
    client_id UUID NOT NULL REFERENCES clients(id),
    status UUID NOT NULL REFERENCES list_entries(id)
);

-- Project users junction table
CREATE TABLE project_users (
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    access_level UUID REFERENCES list_entries(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (project_id, user_id)
);

-- Units table
CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    multiplier NUMERIC(20, 10),
    type UUID NOT NULL REFERENCES list_entries(id)
);

-- Container types table
CREATE TABLE container_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    capacity NUMERIC(10, 3),
    material VARCHAR(255),
    dimensions VARCHAR(50),
    preservative VARCHAR(255)
);

-- Containers table
CREATE TABLE containers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    row INTEGER DEFAULT 1,
    column INTEGER DEFAULT 1,
    concentration NUMERIC(15, 6),
    concentration_units UUID REFERENCES units(id),
    amount NUMERIC(15, 6),
    amount_units UUID REFERENCES units(id),
    type_id UUID NOT NULL REFERENCES container_types(id),
    parent_container_id UUID REFERENCES containers(id)
);

-- Samples table
CREATE TABLE samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    due_date TIMESTAMP,
    received_date TIMESTAMP,
    report_date TIMESTAMP,
    sample_type UUID NOT NULL REFERENCES list_entries(id),
    status UUID NOT NULL REFERENCES list_entries(id),
    matrix UUID NOT NULL REFERENCES list_entries(id),
    temperature NUMERIC(10, 2),
    parent_sample_id UUID REFERENCES samples(id),
    project_id UUID NOT NULL REFERENCES projects(id),
    qc_type UUID REFERENCES list_entries(id)
);

-- Contents junction table
CREATE TABLE contents (
    container_id UUID REFERENCES containers(id),
    sample_id UUID REFERENCES samples(id),
    concentration NUMERIC(15, 6),
    concentration_units UUID REFERENCES units(id),
    amount NUMERIC(15, 6),
    amount_units UUID REFERENCES units(id),
    PRIMARY KEY (container_id, sample_id)
);

-- Analyses table
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    method VARCHAR(255),
    turnaround_time INTEGER,
    cost NUMERIC(10, 2)
);

-- Analytes table
CREATE TABLE analytes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID
);

-- Analysis analytes junction table
CREATE TABLE analysis_analytes (
    analysis_id UUID REFERENCES analyses(id),
    analyte_id UUID REFERENCES analytes(id),
    data_type VARCHAR(50),
    list_id UUID REFERENCES lists(id),
    high_value NUMERIC(15, 6),
    low_value NUMERIC(15, 6),
    significant_figures INTEGER,
    calculation TEXT,
    reported_name VARCHAR(255),
    display_order INTEGER,
    is_required BOOLEAN DEFAULT FALSE,
    default_value VARCHAR(255),
    PRIMARY KEY (analysis_id, analyte_id)
);

-- Tests table
CREATE TABLE tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    sample_id UUID NOT NULL REFERENCES samples(id),
    analysis_id UUID NOT NULL REFERENCES analyses(id),
    status UUID NOT NULL REFERENCES list_entries(id),
    review_date TIMESTAMP,
    test_date TIMESTAMP,
    technician_id UUID REFERENCES users(id)
);

-- Results table
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    test_id UUID NOT NULL REFERENCES tests(id),
    analyte_id UUID NOT NULL REFERENCES analytes(id),
    raw_result VARCHAR(255),
    reported_result VARCHAR(255),
    qualifiers UUID REFERENCES list_entries(id),
    calculated_result VARCHAR(255),
    entry_date TIMESTAMP DEFAULT NOW(),
    entered_by UUID NOT NULL REFERENCES users(id)
);

-- Batches table
CREATE TABLE batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    modified_at TIMESTAMP DEFAULT NOW(),
    modified_by UUID,
    type UUID REFERENCES list_entries(id),
    status UUID NOT NULL REFERENCES list_entries(id),
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

-- Batch containers junction table
CREATE TABLE batch_containers (
    batch_id UUID REFERENCES batches(id),
    container_id UUID REFERENCES containers(id),
    position VARCHAR(50),
    notes TEXT,
    PRIMARY KEY (batch_id, container_id)
);

-- =============================================
-- AUDIT TRIGGERS
-- =============================================

-- Function to update modified_at
CREATE OR REPLACE FUNCTION update_modified_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to set created_at and modified_at
CREATE OR REPLACE FUNCTION set_audit_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.created_at = NOW();
        NEW.modified_at = NOW();
    ELSIF TG_OP = 'UPDATE' THEN
        NEW.modified_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with audit fields
DO $$
DECLARE
    table_name TEXT;
    tables_with_audit TEXT[] := ARRAY[
        'lists', 'list_entries', 'roles', 'permissions', 'clients', 'users',
        'locations', 'people', 'projects', 'units', 'container_types', 'containers',
        'samples', 'analyses', 'analytes', 'tests', 'results', 'batches'
    ];
BEGIN
    FOREACH table_name IN ARRAY tables_with_audit
    LOOP
        EXECUTE format('
            CREATE TRIGGER %I_audit_timestamps
            BEFORE INSERT OR UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION set_audit_timestamps();
        ', table_name, table_name);
        
        EXECUTE format('
            CREATE TRIGGER %I_update_modified_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_modified_at_column();
        ', table_name, table_name);
    END LOOP;
END $$;

-- =============================================
-- ROW LEVEL SECURITY
-- =============================================

-- Enable RLS on key tables
ALTER TABLE samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE results ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE containers ENABLE ROW LEVEL SECURITY;

-- Function to get current user ID
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS UUID AS $$
BEGIN
    RETURN COALESCE(
        current_setting('app.current_user_id', true)::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is admin
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

-- Function to check if user has access to project
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Admin users can access all projects
    IF is_admin() THEN
        RETURN TRUE;
    END IF;
    
    -- Check if user has direct access to project
    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
        AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policies
CREATE POLICY samples_access ON samples
    FOR ALL
    USING (is_admin() OR has_project_access(project_id));

CREATE POLICY tests_access ON tests
    FOR ALL
    USING (
        is_admin() OR EXISTS (
            SELECT 1 FROM samples s
            WHERE s.id = tests.sample_id
            AND has_project_access(s.project_id)
        )
    );

CREATE POLICY results_access ON results
    FOR ALL
    USING (
        is_admin() OR EXISTS (
            SELECT 1 FROM tests t
            JOIN samples s ON t.sample_id = s.id
            WHERE t.id = results.test_id
            AND has_project_access(s.project_id)
        )
    );

CREATE POLICY projects_access ON projects
    FOR ALL
    USING (is_admin() OR has_project_access(id));

CREATE POLICY batches_access ON batches
    FOR ALL
    USING (
        is_admin() OR EXISTS (
            SELECT 1 FROM batch_containers bc
            JOIN containers c ON bc.container_id = c.id
            JOIN contents ct ON c.id = ct.container_id
            JOIN samples s ON ct.sample_id = s.id
            WHERE bc.batch_id = batches.id
            AND has_project_access(s.project_id)
        )
    );

CREATE POLICY containers_access ON containers
    FOR ALL
    USING (
        is_admin() OR EXISTS (
            SELECT 1 FROM contents c
            JOIN samples s ON c.sample_id = s.id
            WHERE c.container_id = containers.id
            AND has_project_access(s.project_id)
        )
    );

-- =============================================
-- INDEXES
-- =============================================

-- Foreign key indexes
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_client_id ON users(client_id);
CREATE INDEX idx_projects_client_id ON projects(client_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_project_users_project_id ON project_users(project_id);
CREATE INDEX idx_project_users_user_id ON project_users(user_id);
CREATE INDEX idx_samples_project_id ON samples(project_id);
CREATE INDEX idx_samples_sample_type ON samples(sample_type);
CREATE INDEX idx_samples_status ON samples(status);
CREATE INDEX idx_samples_matrix ON samples(matrix);
CREATE INDEX idx_samples_qc_type ON samples(qc_type);
CREATE INDEX idx_samples_parent_sample_id ON samples(parent_sample_id);
CREATE INDEX idx_containers_type_id ON containers(type_id);
CREATE INDEX idx_containers_parent_container_id ON containers(parent_container_id);
CREATE INDEX idx_containers_concentration_units ON containers(concentration_units);
CREATE INDEX idx_containers_amount_units ON containers(amount_units);
CREATE INDEX idx_contents_container_id ON contents(container_id);
CREATE INDEX idx_contents_sample_id ON contents(sample_id);
CREATE INDEX idx_contents_concentration_units ON contents(concentration_units);
CREATE INDEX idx_contents_amount_units ON contents(amount_units);
CREATE INDEX idx_tests_sample_id ON tests(sample_id);
CREATE INDEX idx_tests_analysis_id ON tests(analysis_id);
CREATE INDEX idx_tests_status ON tests(status);
CREATE INDEX idx_tests_technician_id ON tests(technician_id);
CREATE INDEX idx_results_test_id ON results(test_id);
CREATE INDEX idx_results_analyte_id ON results(analyte_id);
CREATE INDEX idx_results_entered_by ON results(entered_by);
CREATE INDEX idx_results_qualifiers ON results(qualifiers);
CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_type ON batches(type);
CREATE INDEX idx_batch_containers_batch_id ON batch_containers(batch_id);
CREATE INDEX idx_batch_containers_container_id ON batch_containers(container_id);
CREATE INDEX idx_analysis_analytes_analysis_id ON analysis_analytes(analysis_id);
CREATE INDEX idx_analysis_analytes_analyte_id ON analysis_analytes(analyte_id);
CREATE INDEX idx_analysis_analytes_list_id ON analysis_analytes(list_id);
CREATE INDEX idx_list_entries_list_id ON list_entries(list_id);
CREATE INDEX idx_units_type ON units(type);
CREATE INDEX idx_locations_client_id ON locations(client_id);
CREATE INDEX idx_locations_type ON locations(type);
CREATE INDEX idx_people_locations_person_id ON people_locations(person_id);
CREATE INDEX idx_people_locations_location_id ON people_locations(location_id);
CREATE INDEX idx_contact_methods_person_id ON contact_methods(person_id);
CREATE INDEX idx_contact_methods_type ON contact_methods(type);

-- Composite indexes for common queries
CREATE INDEX idx_samples_project_status ON samples(project_id, status);
CREATE INDEX idx_samples_project_sample_type ON samples(project_id, sample_type);
CREATE INDEX idx_samples_project_qc_type ON samples(project_id, qc_type);
CREATE INDEX idx_tests_sample_status ON tests(sample_id, status);
CREATE INDEX idx_tests_analysis_status ON tests(analysis_id, status);
CREATE INDEX idx_results_test_analyte ON results(test_id, analyte_id);
CREATE INDEX idx_batches_status_type ON batches(status, type);
CREATE INDEX idx_containers_type_parent ON containers(type_id, parent_container_id);
CREATE INDEX idx_projects_client_status ON projects(client_id, status);
CREATE INDEX idx_users_role_client ON users(role_id, client_id);

-- =============================================
-- GRANT PERMISSIONS
-- =============================================

-- Grant necessary permissions to lims_user
GRANT USAGE ON SCHEMA public TO lims_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lims_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lims_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO lims_user;

-- =============================================
-- INITIAL DATA
-- =============================================

-- Insert initial lists
INSERT INTO lists (id, name, description, active, created_at, modified_at) VALUES
('11111111-1111-1111-1111-111111111111', 'Sample Status', 'Sample status values', true, NOW(), NOW()),
('22222222-2222-2222-2222-222222222222', 'Test Status', 'Test status values', true, NOW(), NOW()),
('33333333-3333-3333-3333-333333333333', 'Project Status', 'Project status values', true, NOW(), NOW()),
('44444444-4444-4444-4444-444444444444', 'Batch Status', 'Batch status values', true, NOW(), NOW()),
('55555555-5555-5555-5555-555555555555', 'Sample Types', 'Sample type values', true, NOW(), NOW()),
('66666666-6666-6666-6666-666666666666', 'Matrix Types', 'Matrix type values', true, NOW(), NOW()),
('77777777-7777-7777-7777-777777777777', 'QC Types', 'QC type values', true, NOW(), NOW()),
('88888888-8888-8888-8888-888888888888', 'Unit Types', 'Unit type values', true, NOW(), NOW()),
('99999999-9999-9999-9999-999999999999', 'Contact Types', 'Contact method types', true, NOW(), NOW());

-- Insert list entries
INSERT INTO list_entries (id, name, description, active, created_at, modified_at, list_id) VALUES
-- Sample Status
(gen_random_uuid(), 'Received', 'Sample received', true, NOW(), NOW(), '11111111-1111-1111-1111-111111111111'),
(gen_random_uuid(), 'Available for Testing', 'Ready for testing', true, NOW(), NOW(), '11111111-1111-1111-1111-111111111111'),
(gen_random_uuid(), 'Testing Complete', 'Testing finished', true, NOW(), NOW(), '11111111-1111-1111-1111-111111111111'),
(gen_random_uuid(), 'Reviewed', 'Results reviewed', true, NOW(), NOW(), '11111111-1111-1111-1111-111111111111'),
(gen_random_uuid(), 'Reported', 'Results reported', true, NOW(), NOW(), '11111111-1111-1111-1111-111111111111'),

-- Test Status
(gen_random_uuid(), 'In Process', 'Test in progress', true, NOW(), NOW(), '22222222-2222-2222-2222-222222222222'),
(gen_random_uuid(), 'In Analysis', 'Under analysis', true, NOW(), NOW(), '22222222-2222-2222-2222-222222222222'),
(gen_random_uuid(), 'Complete', 'Test completed', true, NOW(), NOW(), '22222222-2222-2222-2222-222222222222'),

-- Project Status
(gen_random_uuid(), 'Active', 'Project active', true, NOW(), NOW(), '33333333-3333-3333-3333-333333333333'),
(gen_random_uuid(), 'Completed', 'Project completed', true, NOW(), NOW(), '33333333-3333-3333-3333-333333333333'),
(gen_random_uuid(), 'On Hold', 'Project on hold', true, NOW(), NOW(), '33333333-3333-3333-3333-333333333333'),

-- Batch Status
(gen_random_uuid(), 'Created', 'Batch created', true, NOW(), NOW(), '44444444-4444-4444-4444-444444444444'),
(gen_random_uuid(), 'In Process', 'Batch in process', true, NOW(), NOW(), '44444444-4444-4444-4444-444444444444'),
(gen_random_uuid(), 'Completed', 'Batch completed', true, NOW(), NOW(), '44444444-4444-4444-4444-444444444444'),

-- Sample Types
(gen_random_uuid(), 'Blood', 'Blood sample', true, NOW(), NOW(), '55555555-5555-5555-5555-555555555555'),
(gen_random_uuid(), 'Urine', 'Urine sample', true, NOW(), NOW(), '55555555-5555-5555-5555-555555555555'),
(gen_random_uuid(), 'Tissue', 'Tissue sample', true, NOW(), NOW(), '55555555-5555-5555-5555-555555555555'),
(gen_random_uuid(), 'Water', 'Water sample', true, NOW(), NOW(), '55555555-5555-5555-5555-555555555555'),

-- Matrix Types
(gen_random_uuid(), 'Human', 'Human matrix', true, NOW(), NOW(), '66666666-6666-6666-6666-666666666666'),
(gen_random_uuid(), 'Environmental', 'Environmental matrix', true, NOW(), NOW(), '66666666-6666-6666-6666-666666666666'),
(gen_random_uuid(), 'Food', 'Food matrix', true, NOW(), NOW(), '66666666-6666-6666-6666-666666666666'),

-- QC Types
(gen_random_uuid(), 'Sample', 'Regular sample', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),
(gen_random_uuid(), 'Positive Control', 'Positive control', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),
(gen_random_uuid(), 'Negative Control', 'Negative control', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),
(gen_random_uuid(), 'Matrix Spike', 'Matrix spike', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),
(gen_random_uuid(), 'Duplicate', 'Duplicate sample', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),
(gen_random_uuid(), 'Blank', 'Blank sample', true, NOW(), NOW(), '77777777-7777-7777-7777-777777777777'),

-- Unit Types
(gen_random_uuid(), 'concentration', 'Concentration units', true, NOW(), NOW(), '88888888-8888-8888-8888-888888888888'),
(gen_random_uuid(), 'mass', 'Mass units', true, NOW(), NOW(), '88888888-8888-8888-8888-888888888888'),
(gen_random_uuid(), 'volume', 'Volume units', true, NOW(), NOW(), '88888888-8888-8888-8888-888888888888'),
(gen_random_uuid(), 'molar', 'Molar units', true, NOW(), NOW(), '88888888-8888-8888-8888-888888888888'),

-- Contact Types
(gen_random_uuid(), 'Email', 'Email address', true, NOW(), NOW(), '99999999-9999-9999-9999-999999999999'),
(gen_random_uuid(), 'Phone', 'Phone number', true, NOW(), NOW(), '99999999-9999-9999-9999-999999999999'),
(gen_random_uuid(), 'Mobile', 'Mobile phone', true, NOW(), NOW(), '99999999-9999-9999-9999-999999999999');

-- Insert roles
INSERT INTO roles (id, name, description, active, created_at, modified_at) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Administrator', 'System administrator', true, NOW(), NOW()),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Lab Manager', 'Laboratory manager', true, NOW(), NOW()),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Lab Technician', 'Laboratory technician', true, NOW(), NOW()),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Client', 'Client user', true, NOW(), NOW());

-- Insert permissions
INSERT INTO permissions (id, name, description, active, created_at, modified_at) VALUES
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'user:manage', 'Manage users', true, NOW(), NOW()),
('ffffffff-ffff-ffff-ffff-ffffffffffff', 'role:manage', 'Manage roles', true, NOW(), NOW()),
('gggggggg-gggg-gggg-gggg-gggggggggggg', 'config:edit', 'Edit configuration', true, NOW(), NOW()),
('hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh', 'project:manage', 'Manage projects', true, NOW(), NOW()),
('iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii', 'sample:create', 'Create samples', true, NOW(), NOW()),
('jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj', 'sample:read', 'Read samples', true, NOW(), NOW()),
('kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk', 'sample:update', 'Update samples', true, NOW(), NOW()),
('llllllll-llll-llll-llll-llllllllllll', 'test:assign', 'Assign tests', true, NOW(), NOW()),
('mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm', 'test:update', 'Update tests', true, NOW(), NOW()),
('nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn', 'result:enter', 'Enter results', true, NOW(), NOW()),
('oooooooo-oooo-oooo-oooo-oooooooooooo', 'result:review', 'Review results', true, NOW(), NOW()),
('pppppppp-pppp-pppp-pppp-pppppppppppp', 'batch:manage', 'Manage batches', true, NOW(), NOW());

-- Insert role-permission mappings
INSERT INTO role_permissions (role_id, permission_id) VALUES
-- Administrator gets all permissions
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

-- Lab Manager permissions
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'llllllll-llll-llll-llll-llllllllllll'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'oooooooo-oooo-oooo-oooo-oooooooooooo'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'pppppppp-pppp-pppp-pppp-pppppppppppp'),

-- Lab Technician permissions
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'iiiiiiii-iiii-iiii-iiii-iiiiiiiiiiii'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'kkkkkkkk-kkkk-kkkk-kkkk-kkkkkkkkkkkk'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'llllllll-llll-llll-llll-llllllllllll'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'mmmmmmmm-mmmm-mmmm-mmmm-mmmmmmmmmmmm'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'nnnnnnnn-nnnn-nnnn-nnnn-nnnnnnnnnnnn'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'pppppppp-pppp-pppp-pppp-pppppppppppp'),

-- Client permissions
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'jjjjjjjj-jjjj-jjjj-jjjj-jjjjjjjjjjjj');

-- Insert base units
INSERT INTO units (id, name, description, active, created_at, modified_at, multiplier, type) VALUES
(gen_random_uuid(), 'g/L', 'Grams per liter', true, NOW(), NOW(), 1.0, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'concentration')),
(gen_random_uuid(), 'mg/L', 'Milligrams per liter', true, NOW(), NOW(), 0.001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'concentration')),
(gen_random_uuid(), 'µg/L', 'Micrograms per liter', true, NOW(), NOW(), 0.000001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'concentration')),
(gen_random_uuid(), 'g', 'Grams', true, NOW(), NOW(), 1.0, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'mass')),
(gen_random_uuid(), 'mg', 'Milligrams', true, NOW(), NOW(), 0.001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'mass')),
(gen_random_uuid(), 'µg', 'Micrograms', true, NOW(), NOW(), 0.000001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'mass')),
(gen_random_uuid(), 'L', 'Liters', true, NOW(), NOW(), 1.0, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'volume')),
(gen_random_uuid(), 'mL', 'Milliliters', true, NOW(), NOW(), 0.001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'volume')),
(gen_random_uuid(), 'µL', 'Microliters', true, NOW(), NOW(), 0.000001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'volume')),
(gen_random_uuid(), 'mol/L', 'Moles per liter', true, NOW(), NOW(), 1.0, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'molar')),
(gen_random_uuid(), 'mmol/L', 'Millimoles per liter', true, NOW(), NOW(), 0.001, (SELECT id FROM list_entries WHERE list_id = '88888888-8888-8888-8888-888888888888' AND name = 'molar'));

-- =============================================
-- COMPLETION MESSAGE
-- =============================================

SELECT 'LIMS MVP Database Setup Complete!' as message;
