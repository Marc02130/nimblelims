--
-- PostgreSQL database dump
--

\restrict hHarTGLBbfyk2VER7ZMIgboTQe6RwIEMnYh8GwpZyGhDjMreI5EDfNpnFNesLVf

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP POLICY IF EXISTS tests_access ON public.tests;
DROP POLICY IF EXISTS samples_access ON public.samples;
DROP POLICY IF EXISTS results_access ON public.results;
DROP POLICY IF EXISTS projects_access ON public.projects;
DROP POLICY IF EXISTS name_templates_access ON public.name_templates;
DROP POLICY IF EXISTS help_entries_access ON public.help_entries;
DROP POLICY IF EXISTS custom_attributes_config_access ON public.custom_attributes_config;
DROP POLICY IF EXISTS containers_access ON public.containers;
DROP POLICY IF EXISTS client_projects_access ON public.client_projects;
DROP POLICY IF EXISTS batches_access ON public.batches;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_client_id_fkey;
ALTER TABLE IF EXISTS ONLY public.units DROP CONSTRAINT IF EXISTS units_type_fkey;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_technician_id_fkey;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_status_fkey;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_sample_id_fkey;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_analysis_id_fkey;
ALTER TABLE IF EXISTS ONLY public.test_batteries DROP CONSTRAINT IF EXISTS test_batteries_modified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.test_batteries DROP CONSTRAINT IF EXISTS test_batteries_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_status_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_sample_type_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_qc_type_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_parent_sample_id_fkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_matrix_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_permission_id_fkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_test_id_fkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_qualifiers_fkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_entered_by_fkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_analyte_id_fkey;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_status_fkey;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_client_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_client_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_users DROP CONSTRAINT IF EXISTS project_users_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_users DROP CONSTRAINT IF EXISTS project_users_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_users DROP CONSTRAINT IF EXISTS project_users_granted_by_fkey;
ALTER TABLE IF EXISTS ONLY public.project_users DROP CONSTRAINT IF EXISTS project_users_access_level_fkey;
ALTER TABLE IF EXISTS ONLY public.people DROP CONSTRAINT IF EXISTS people_role_fkey;
ALTER TABLE IF EXISTS ONLY public.people_locations DROP CONSTRAINT IF EXISTS people_locations_person_id_fkey;
ALTER TABLE IF EXISTS ONLY public.people_locations DROP CONSTRAINT IF EXISTS people_locations_location_id_fkey;
ALTER TABLE IF EXISTS ONLY public.name_templates DROP CONSTRAINT IF EXISTS name_templates_modified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.name_templates DROP CONSTRAINT IF EXISTS name_templates_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.locations DROP CONSTRAINT IF EXISTS locations_type_fkey;
ALTER TABLE IF EXISTS ONLY public.locations DROP CONSTRAINT IF EXISTS locations_client_id_fkey;
ALTER TABLE IF EXISTS ONLY public.list_entries DROP CONSTRAINT IF EXISTS list_entries_list_id_fkey;
ALTER TABLE IF EXISTS ONLY public.help_entries DROP CONSTRAINT IF EXISTS help_entries_modified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.help_entries DROP CONSTRAINT IF EXISTS help_entries_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.analytes DROP CONSTRAINT IF EXISTS fk_analytes_units_default;
ALTER TABLE IF EXISTS ONLY public.custom_attributes_config DROP CONSTRAINT IF EXISTS custom_attributes_config_modified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.custom_attributes_config DROP CONSTRAINT IF EXISTS custom_attributes_config_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.contents DROP CONSTRAINT IF EXISTS contents_sample_id_fkey;
ALTER TABLE IF EXISTS ONLY public.contents DROP CONSTRAINT IF EXISTS contents_container_id_fkey;
ALTER TABLE IF EXISTS ONLY public.contents DROP CONSTRAINT IF EXISTS contents_concentration_units_fkey;
ALTER TABLE IF EXISTS ONLY public.contents DROP CONSTRAINT IF EXISTS contents_amount_units_fkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_type_id_fkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_parent_container_id_fkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_concentration_units_fkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_amount_units_fkey;
ALTER TABLE IF EXISTS ONLY public.contact_methods DROP CONSTRAINT IF EXISTS contact_methods_type_fkey;
ALTER TABLE IF EXISTS ONLY public.contact_methods DROP CONSTRAINT IF EXISTS contact_methods_person_id_fkey;
ALTER TABLE IF EXISTS ONLY public.client_projects DROP CONSTRAINT IF EXISTS client_projects_modified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.client_projects DROP CONSTRAINT IF EXISTS client_projects_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.client_projects DROP CONSTRAINT IF EXISTS client_projects_client_id_fkey;
ALTER TABLE IF EXISTS ONLY public.battery_analyses DROP CONSTRAINT IF EXISTS battery_analyses_battery_id_fkey;
ALTER TABLE IF EXISTS ONLY public.battery_analyses DROP CONSTRAINT IF EXISTS battery_analyses_analysis_id_fkey;
ALTER TABLE IF EXISTS ONLY public.batches DROP CONSTRAINT IF EXISTS batches_type_fkey;
ALTER TABLE IF EXISTS ONLY public.batches DROP CONSTRAINT IF EXISTS batches_status_fkey;
ALTER TABLE IF EXISTS ONLY public.batch_containers DROP CONSTRAINT IF EXISTS batch_containers_container_id_fkey;
ALTER TABLE IF EXISTS ONLY public.batch_containers DROP CONSTRAINT IF EXISTS batch_containers_batch_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_analytes DROP CONSTRAINT IF EXISTS analysis_analytes_list_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_analytes DROP CONSTRAINT IF EXISTS analysis_analytes_analyte_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_analytes DROP CONSTRAINT IF EXISTS analysis_analytes_analysis_id_fkey;
DROP TRIGGER IF EXISTS users_update_modified_at ON public.users;
DROP TRIGGER IF EXISTS users_audit_timestamps ON public.users;
DROP TRIGGER IF EXISTS units_update_modified_at ON public.units;
DROP TRIGGER IF EXISTS units_audit_timestamps ON public.units;
DROP TRIGGER IF EXISTS tests_update_modified_at ON public.tests;
DROP TRIGGER IF EXISTS tests_audit_timestamps ON public.tests;
DROP TRIGGER IF EXISTS samples_update_modified_at ON public.samples;
DROP TRIGGER IF EXISTS samples_audit_timestamps ON public.samples;
DROP TRIGGER IF EXISTS roles_update_modified_at ON public.roles;
DROP TRIGGER IF EXISTS roles_audit_timestamps ON public.roles;
DROP TRIGGER IF EXISTS results_update_modified_at ON public.results;
DROP TRIGGER IF EXISTS results_audit_timestamps ON public.results;
DROP TRIGGER IF EXISTS projects_update_modified_at ON public.projects;
DROP TRIGGER IF EXISTS projects_audit_timestamps ON public.projects;
DROP TRIGGER IF EXISTS permissions_update_modified_at ON public.permissions;
DROP TRIGGER IF EXISTS permissions_audit_timestamps ON public.permissions;
DROP TRIGGER IF EXISTS people_update_modified_at ON public.people;
DROP TRIGGER IF EXISTS people_audit_timestamps ON public.people;
DROP TRIGGER IF EXISTS name_templates_update_modified_at ON public.name_templates;
DROP TRIGGER IF EXISTS name_templates_audit_timestamps ON public.name_templates;
DROP TRIGGER IF EXISTS locations_update_modified_at ON public.locations;
DROP TRIGGER IF EXISTS locations_audit_timestamps ON public.locations;
DROP TRIGGER IF EXISTS lists_update_modified_at ON public.lists;
DROP TRIGGER IF EXISTS lists_audit_timestamps ON public.lists;
DROP TRIGGER IF EXISTS list_entries_update_modified_at ON public.list_entries;
DROP TRIGGER IF EXISTS list_entries_audit_timestamps ON public.list_entries;
DROP TRIGGER IF EXISTS containers_update_modified_at ON public.containers;
DROP TRIGGER IF EXISTS containers_audit_timestamps ON public.containers;
DROP TRIGGER IF EXISTS container_types_update_modified_at ON public.container_types;
DROP TRIGGER IF EXISTS container_types_audit_timestamps ON public.container_types;
DROP TRIGGER IF EXISTS clients_update_modified_at ON public.clients;
DROP TRIGGER IF EXISTS clients_audit_timestamps ON public.clients;
DROP TRIGGER IF EXISTS batches_update_modified_at ON public.batches;
DROP TRIGGER IF EXISTS batches_audit_timestamps ON public.batches;
DROP TRIGGER IF EXISTS analytes_update_modified_at ON public.analytes;
DROP TRIGGER IF EXISTS analytes_audit_timestamps ON public.analytes;
DROP TRIGGER IF EXISTS analyses_update_modified_at ON public.analyses;
DROP TRIGGER IF EXISTS analyses_audit_timestamps ON public.analyses;
DROP INDEX IF EXISTS public.idx_users_username_unique;
DROP INDEX IF EXISTS public.idx_users_role_id_client_id;
DROP INDEX IF EXISTS public.idx_users_role_id;
DROP INDEX IF EXISTS public.idx_users_modified_by;
DROP INDEX IF EXISTS public.idx_users_email_unique;
DROP INDEX IF EXISTS public.idx_users_created_by;
DROP INDEX IF EXISTS public.idx_users_client_id;
DROP INDEX IF EXISTS public.idx_units_type;
DROP INDEX IF EXISTS public.idx_units_name_unique;
DROP INDEX IF EXISTS public.idx_tests_technician_id;
DROP INDEX IF EXISTS public.idx_tests_status;
DROP INDEX IF EXISTS public.idx_tests_sample_id_status;
DROP INDEX IF EXISTS public.idx_tests_sample_id_active;
DROP INDEX IF EXISTS public.idx_tests_sample_id;
DROP INDEX IF EXISTS public.idx_tests_modified_by;
DROP INDEX IF EXISTS public.idx_tests_modified_at;
DROP INDEX IF EXISTS public.idx_tests_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_tests_created_by;
DROP INDEX IF EXISTS public.idx_tests_analysis_id_status;
DROP INDEX IF EXISTS public.idx_tests_analysis_id;
DROP INDEX IF EXISTS public.idx_test_batteries_name;
DROP INDEX IF EXISTS public.idx_samples_status;
DROP INDEX IF EXISTS public.idx_samples_sample_type;
DROP INDEX IF EXISTS public.idx_samples_qc_type;
DROP INDEX IF EXISTS public.idx_samples_project_id_status;
DROP INDEX IF EXISTS public.idx_samples_project_id_sample_type;
DROP INDEX IF EXISTS public.idx_samples_project_id_qc_type;
DROP INDEX IF EXISTS public.idx_samples_project_id_active;
DROP INDEX IF EXISTS public.idx_samples_project_id;
DROP INDEX IF EXISTS public.idx_samples_prioritization;
DROP INDEX IF EXISTS public.idx_samples_parent_sample_id;
DROP INDEX IF EXISTS public.idx_samples_name_unique;
DROP INDEX IF EXISTS public.idx_samples_modified_by;
DROP INDEX IF EXISTS public.idx_samples_modified_at;
DROP INDEX IF EXISTS public.idx_samples_matrix;
DROP INDEX IF EXISTS public.idx_samples_date_sampled;
DROP INDEX IF EXISTS public.idx_samples_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_samples_created_by;
DROP INDEX IF EXISTS public.idx_samples_client_sample_id;
DROP INDEX IF EXISTS public.idx_results_test_id_analyte_id;
DROP INDEX IF EXISTS public.idx_results_test_id_active;
DROP INDEX IF EXISTS public.idx_results_test_id;
DROP INDEX IF EXISTS public.idx_results_qualifiers;
DROP INDEX IF EXISTS public.idx_results_modified_by;
DROP INDEX IF EXISTS public.idx_results_entered_by;
DROP INDEX IF EXISTS public.idx_results_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_results_created_by;
DROP INDEX IF EXISTS public.idx_results_analyte_id;
DROP INDEX IF EXISTS public.idx_projects_status;
DROP INDEX IF EXISTS public.idx_projects_name_unique;
DROP INDEX IF EXISTS public.idx_projects_due_date;
DROP INDEX IF EXISTS public.idx_projects_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_projects_client_project_id;
DROP INDEX IF EXISTS public.idx_projects_client_id_status;
DROP INDEX IF EXISTS public.idx_projects_client_id;
DROP INDEX IF EXISTS public.idx_project_users_user_id;
DROP INDEX IF EXISTS public.idx_project_users_project_id;
DROP INDEX IF EXISTS public.idx_people_locations_person_id;
DROP INDEX IF EXISTS public.idx_people_locations_location_id;
DROP INDEX IF EXISTS public.idx_name_templates_entity_type_active_unique;
DROP INDEX IF EXISTS public.idx_name_templates_entity_type;
DROP INDEX IF EXISTS public.idx_locations_type;
DROP INDEX IF EXISTS public.idx_locations_client_id;
DROP INDEX IF EXISTS public.idx_lists_name_unique;
DROP INDEX IF EXISTS public.idx_list_entries_list_id_name_unique;
DROP INDEX IF EXISTS public.idx_list_entries_list_id;
DROP INDEX IF EXISTS public.idx_help_entries_section;
DROP INDEX IF EXISTS public.idx_help_entries_role_filter;
DROP INDEX IF EXISTS public.idx_help_entries_active;
DROP INDEX IF EXISTS public.idx_custom_attributes_config_entity_type;
DROP INDEX IF EXISTS public.idx_custom_attributes_config_active;
DROP INDEX IF EXISTS public.idx_contents_sample_id;
DROP INDEX IF EXISTS public.idx_contents_container_id;
DROP INDEX IF EXISTS public.idx_contents_concentration_units;
DROP INDEX IF EXISTS public.idx_contents_amount_units;
DROP INDEX IF EXISTS public.idx_containers_type_id_parent_container_id;
DROP INDEX IF EXISTS public.idx_containers_type_id_active;
DROP INDEX IF EXISTS public.idx_containers_type_id;
DROP INDEX IF EXISTS public.idx_containers_parent_container_id;
DROP INDEX IF EXISTS public.idx_containers_name_unique;
DROP INDEX IF EXISTS public.idx_containers_modified_by;
DROP INDEX IF EXISTS public.idx_containers_modified_at;
DROP INDEX IF EXISTS public.idx_containers_concentration_units;
DROP INDEX IF EXISTS public.idx_containers_amount_units;
DROP INDEX IF EXISTS public.idx_contact_methods_type;
DROP INDEX IF EXISTS public.idx_contact_methods_person_id;
DROP INDEX IF EXISTS public.idx_clients_name_unique;
DROP INDEX IF EXISTS public.idx_client_projects_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_client_projects_client_id;
DROP INDEX IF EXISTS public.idx_battery_analyses_sequence;
DROP INDEX IF EXISTS public.idx_battery_analyses_battery_id;
DROP INDEX IF EXISTS public.idx_battery_analyses_battery_analysis;
DROP INDEX IF EXISTS public.idx_batches_type;
DROP INDEX IF EXISTS public.idx_batches_status_type;
DROP INDEX IF EXISTS public.idx_batches_status_active;
DROP INDEX IF EXISTS public.idx_batches_status;
DROP INDEX IF EXISTS public.idx_batches_name_unique;
DROP INDEX IF EXISTS public.idx_batches_custom_attributes_gin;
DROP INDEX IF EXISTS public.idx_batch_containers_container_id;
DROP INDEX IF EXISTS public.idx_batch_containers_batch_id;
DROP INDEX IF EXISTS public.idx_analytes_name_unique;
DROP INDEX IF EXISTS public.idx_analysis_analytes_list_id;
DROP INDEX IF EXISTS public.idx_analysis_analytes_analyte_id;
DROP INDEX IF EXISTS public.idx_analysis_analytes_analysis_id;
DROP INDEX IF EXISTS public.idx_analyses_shelf_life;
DROP INDEX IF EXISTS public.idx_analyses_name_unique;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_name_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.custom_attributes_config DROP CONSTRAINT IF EXISTS uq_custom_attributes_config_entity_attr;
ALTER TABLE IF EXISTS ONLY public.units DROP CONSTRAINT IF EXISTS units_pkey;
ALTER TABLE IF EXISTS ONLY public.units DROP CONSTRAINT IF EXISTS units_name_key;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_pkey;
ALTER TABLE IF EXISTS ONLY public.tests DROP CONSTRAINT IF EXISTS tests_name_key;
ALTER TABLE IF EXISTS ONLY public.test_batteries DROP CONSTRAINT IF EXISTS test_batteries_pkey;
ALTER TABLE IF EXISTS ONLY public.test_batteries DROP CONSTRAINT IF EXISTS test_batteries_name_key;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_pkey;
ALTER TABLE IF EXISTS ONLY public.samples DROP CONSTRAINT IF EXISTS samples_name_key;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_name_key;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_pkey;
ALTER TABLE IF EXISTS ONLY public.results DROP CONSTRAINT IF EXISTS results_name_key;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_pkey;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_name_key;
ALTER TABLE IF EXISTS ONLY public.project_users DROP CONSTRAINT IF EXISTS project_users_pkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_name_key;
ALTER TABLE IF EXISTS ONLY public.people DROP CONSTRAINT IF EXISTS people_pkey;
ALTER TABLE IF EXISTS ONLY public.people DROP CONSTRAINT IF EXISTS people_name_key;
ALTER TABLE IF EXISTS ONLY public.people_locations DROP CONSTRAINT IF EXISTS people_locations_pkey;
ALTER TABLE IF EXISTS ONLY public.name_templates DROP CONSTRAINT IF EXISTS name_templates_pkey;
ALTER TABLE IF EXISTS ONLY public.locations DROP CONSTRAINT IF EXISTS locations_pkey;
ALTER TABLE IF EXISTS ONLY public.locations DROP CONSTRAINT IF EXISTS locations_name_key;
ALTER TABLE IF EXISTS ONLY public.lists DROP CONSTRAINT IF EXISTS lists_pkey;
ALTER TABLE IF EXISTS ONLY public.lists DROP CONSTRAINT IF EXISTS lists_name_key;
ALTER TABLE IF EXISTS ONLY public.list_entries DROP CONSTRAINT IF EXISTS list_entries_pkey;
ALTER TABLE IF EXISTS ONLY public.list_entries DROP CONSTRAINT IF EXISTS list_entries_list_id_name_key;
ALTER TABLE IF EXISTS ONLY public.help_entries DROP CONSTRAINT IF EXISTS help_entries_pkey;
ALTER TABLE IF EXISTS ONLY public.custom_attributes_config DROP CONSTRAINT IF EXISTS custom_attributes_config_pkey;
ALTER TABLE IF EXISTS ONLY public.contents DROP CONSTRAINT IF EXISTS contents_pkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_pkey;
ALTER TABLE IF EXISTS ONLY public.containers DROP CONSTRAINT IF EXISTS containers_name_key;
ALTER TABLE IF EXISTS ONLY public.container_types DROP CONSTRAINT IF EXISTS container_types_pkey;
ALTER TABLE IF EXISTS ONLY public.container_types DROP CONSTRAINT IF EXISTS container_types_name_key;
ALTER TABLE IF EXISTS ONLY public.contact_methods DROP CONSTRAINT IF EXISTS contact_methods_pkey;
ALTER TABLE IF EXISTS ONLY public.clients DROP CONSTRAINT IF EXISTS clients_pkey;
ALTER TABLE IF EXISTS ONLY public.clients DROP CONSTRAINT IF EXISTS clients_name_key;
ALTER TABLE IF EXISTS ONLY public.client_projects DROP CONSTRAINT IF EXISTS client_projects_pkey;
ALTER TABLE IF EXISTS ONLY public.client_projects DROP CONSTRAINT IF EXISTS client_projects_name_key;
ALTER TABLE IF EXISTS ONLY public.battery_analyses DROP CONSTRAINT IF EXISTS battery_analyses_pkey;
ALTER TABLE IF EXISTS ONLY public.batches DROP CONSTRAINT IF EXISTS batches_pkey;
ALTER TABLE IF EXISTS ONLY public.batches DROP CONSTRAINT IF EXISTS batches_name_key;
ALTER TABLE IF EXISTS ONLY public.batch_containers DROP CONSTRAINT IF EXISTS batch_containers_pkey;
ALTER TABLE IF EXISTS ONLY public.analytes DROP CONSTRAINT IF EXISTS analytes_pkey;
ALTER TABLE IF EXISTS ONLY public.analytes DROP CONSTRAINT IF EXISTS analytes_name_key;
ALTER TABLE IF EXISTS ONLY public.analysis_analytes DROP CONSTRAINT IF EXISTS analysis_analytes_pkey;
ALTER TABLE IF EXISTS ONLY public.analyses DROP CONSTRAINT IF EXISTS analyses_pkey;
ALTER TABLE IF EXISTS ONLY public.analyses DROP CONSTRAINT IF EXISTS analyses_name_key;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.units;
DROP TABLE IF EXISTS public.tests;
DROP TABLE IF EXISTS public.test_batteries;
DROP TABLE IF EXISTS public.samples;
DROP TABLE IF EXISTS public.roles;
DROP TABLE IF EXISTS public.role_permissions;
DROP TABLE IF EXISTS public.results;
DROP TABLE IF EXISTS public.projects;
DROP TABLE IF EXISTS public.project_users;
DROP TABLE IF EXISTS public.permissions;
DROP TABLE IF EXISTS public.people_locations;
DROP TABLE IF EXISTS public.people;
DROP TABLE IF EXISTS public.name_templates;
DROP SEQUENCE IF EXISTS public.name_template_seq_sample;
DROP SEQUENCE IF EXISTS public.name_template_seq_project;
DROP SEQUENCE IF EXISTS public.name_template_seq_container;
DROP SEQUENCE IF EXISTS public.name_template_seq_batch;
DROP SEQUENCE IF EXISTS public.name_template_seq_analysis;
DROP TABLE IF EXISTS public.locations;
DROP TABLE IF EXISTS public.lists;
DROP TABLE IF EXISTS public.list_entries;
DROP TABLE IF EXISTS public.help_entries;
DROP TABLE IF EXISTS public.custom_attributes_config;
DROP TABLE IF EXISTS public.contents;
DROP TABLE IF EXISTS public.containers;
DROP TABLE IF EXISTS public.container_types;
DROP TABLE IF EXISTS public.contact_methods;
DROP TABLE IF EXISTS public.clients;
DROP TABLE IF EXISTS public.client_projects;
DROP TABLE IF EXISTS public.battery_analyses;
DROP TABLE IF EXISTS public.batches;
DROP TABLE IF EXISTS public.batch_containers;
DROP TABLE IF EXISTS public.analytes;
DROP TABLE IF EXISTS public.analysis_analytes;
DROP TABLE IF EXISTS public.analyses;
DROP TABLE IF EXISTS public.alembic_version;
DROP FUNCTION IF EXISTS public.update_modified_at_column();
DROP FUNCTION IF EXISTS public.set_audit_timestamps();
DROP FUNCTION IF EXISTS public.is_admin();
DROP FUNCTION IF EXISTS public.has_project_access(project_uuid uuid);
DROP FUNCTION IF EXISTS public.current_user_id();
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP SCHEMA IF EXISTS lims;
--
-- Name: lims; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA lims;


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: current_user_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.current_user_id() RETURNS uuid
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        BEGIN
            RETURN COALESCE(
                current_setting('app.current_user_id', true)::UUID,
                '00000000-0000-0000-0000-000000000000'::UUID
            );
        END;
        $$;


--
-- Name: has_project_access(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.has_project_access(project_uuid uuid) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        DECLARE
            project_client_project_id UUID;
            project_client_id UUID;
            user_client_id UUID;
        BEGIN
            -- Admin users can access all projects
            IF is_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Get the project's client_project_id and client_id
            SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
            FROM projects p
            WHERE p.id = project_uuid;
            
            -- If project has a client_project_id, check access via client_projects
            IF project_client_project_id IS NOT NULL THEN
                -- Get user's client_id
                SELECT u.client_id INTO user_client_id
                FROM users u
                WHERE u.id = current_user_id();
                
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
            
            -- Fall back to direct project access check (for lab technicians or direct grants)
            RETURN EXISTS (
                SELECT 1 FROM project_users pu
                WHERE pu.project_id = project_uuid
                AND pu.user_id = current_user_id()
            );
        END;
        $$;


--
-- Name: is_admin(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.is_admin() RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        DECLARE
            user_role_name TEXT;
        BEGIN
            SELECT r.name INTO user_role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = current_user_id();
            
            RETURN user_role_name = 'Administrator';
        END;
        $$;


--
-- Name: set_audit_timestamps(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_audit_timestamps() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                NEW.created_at = NOW();
                NEW.modified_at = NOW();
            ELSIF TG_OP = 'UPDATE' THEN
                NEW.modified_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: update_modified_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_modified_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.modified_at = NOW();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analyses (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    method character varying(255),
    turnaround_time integer,
    cost numeric(10,2),
    shelf_life integer,
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: analysis_analytes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_analytes (
    analysis_id uuid NOT NULL,
    analyte_id uuid NOT NULL,
    data_type character varying(50),
    list_id uuid,
    high_value numeric(15,6),
    low_value numeric(15,6),
    significant_figures integer,
    calculation text,
    reported_name character varying(255),
    display_order integer,
    is_required boolean DEFAULT false NOT NULL,
    default_value character varying(255)
);


--
-- Name: analytes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analytes (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    cas_number character varying(50),
    units_default uuid,
    data_type character varying(20),
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: batch_containers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch_containers (
    batch_id uuid NOT NULL,
    container_id uuid NOT NULL,
    "position" character varying(50),
    notes text
);


--
-- Name: batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batches (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    type uuid,
    status uuid NOT NULL,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: battery_analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.battery_analyses (
    battery_id uuid NOT NULL,
    analysis_id uuid NOT NULL,
    sequence integer DEFAULT 0 NOT NULL,
    optional boolean DEFAULT false NOT NULL
);


--
-- Name: client_projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_projects (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    client_id uuid NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: clients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clients (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    billing_info jsonb NOT NULL
);


--
-- Name: contact_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_methods (
    id uuid NOT NULL,
    person_id uuid NOT NULL,
    type uuid NOT NULL,
    value character varying(255) NOT NULL,
    description text,
    "primary" boolean NOT NULL,
    verified boolean NOT NULL
);


--
-- Name: container_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.container_types (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    capacity numeric(10,3),
    material character varying(255),
    dimensions character varying(50),
    preservative character varying(255)
);


--
-- Name: containers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.containers (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    "row" integer NOT NULL,
    "column" integer NOT NULL,
    concentration numeric(15,6),
    concentration_units uuid,
    amount numeric(15,6),
    amount_units uuid,
    type_id uuid NOT NULL,
    parent_container_id uuid
);


--
-- Name: contents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contents (
    container_id uuid NOT NULL,
    sample_id uuid NOT NULL,
    concentration numeric(15,6),
    concentration_units uuid,
    amount numeric(15,6),
    amount_units uuid
);


--
-- Name: custom_attributes_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.custom_attributes_config (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    entity_type character varying(255) NOT NULL,
    attr_name character varying(255) NOT NULL,
    data_type character varying(50) NOT NULL,
    validation_rules jsonb DEFAULT '{}'::jsonb,
    description text,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: help_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_entries (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    section character varying(255) NOT NULL,
    content text NOT NULL,
    role_filter character varying(255),
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: list_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.list_entries (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    list_id uuid NOT NULL
);


--
-- Name: lists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lists (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    client_id uuid NOT NULL,
    address_line1 character varying(255) NOT NULL,
    address_line2 character varying(255),
    city character varying(255) NOT NULL,
    state character varying(255) NOT NULL,
    postal_code character varying(20) NOT NULL,
    country character varying(255) NOT NULL,
    latitude numeric(10,8),
    longitude numeric(11,8),
    type uuid
);


--
-- Name: name_template_seq_analysis; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.name_template_seq_analysis
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: name_template_seq_batch; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.name_template_seq_batch
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: name_template_seq_container; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.name_template_seq_container
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: name_template_seq_project; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.name_template_seq_project
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: name_template_seq_sample; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.name_template_seq_sample
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: name_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.name_templates (
    id uuid NOT NULL,
    entity_type character varying(50) NOT NULL,
    template character varying(500) NOT NULL,
    description text,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    title character varying(255),
    role uuid
);


--
-- Name: people_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people_locations (
    person_id uuid NOT NULL,
    location_id uuid NOT NULL,
    "primary" boolean NOT NULL,
    notes text
);


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: project_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_users (
    project_id uuid NOT NULL,
    user_id uuid NOT NULL,
    access_level uuid,
    granted_at timestamp without time zone DEFAULT now() NOT NULL,
    granted_by uuid
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    start_date timestamp without time zone NOT NULL,
    client_id uuid NOT NULL,
    status uuid NOT NULL,
    client_project_id uuid,
    custom_attributes jsonb DEFAULT '{}'::jsonb,
    due_date timestamp without time zone
);


--
-- Name: results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.results (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    test_id uuid NOT NULL,
    analyte_id uuid NOT NULL,
    raw_result character varying(255),
    reported_result character varying(255),
    qualifiers uuid,
    calculated_result character varying(255),
    entry_date timestamp without time zone DEFAULT now() NOT NULL,
    entered_by uuid NOT NULL,
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.samples (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    due_date timestamp without time zone,
    received_date timestamp without time zone,
    report_date timestamp without time zone,
    sample_type uuid NOT NULL,
    status uuid NOT NULL,
    matrix uuid NOT NULL,
    temperature numeric(10,2),
    parent_sample_id uuid,
    project_id uuid NOT NULL,
    qc_type uuid,
    client_sample_id character varying(255),
    custom_attributes jsonb DEFAULT '{}'::jsonb,
    date_sampled timestamp without time zone
);


--
-- Name: test_batteries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_batteries (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid
);


--
-- Name: tests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tests (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    sample_id uuid NOT NULL,
    analysis_id uuid NOT NULL,
    status uuid NOT NULL,
    review_date timestamp without time zone,
    test_date timestamp without time zone,
    technician_id uuid,
    custom_attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: units; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.units (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    multiplier numeric(20,10),
    type uuid NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    modified_at timestamp without time zone DEFAULT now() NOT NULL,
    modified_by uuid,
    username character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    role_id uuid NOT NULL,
    client_id uuid NOT NULL,
    last_login timestamp without time zone,
    CONSTRAINT users_client_id_not_null_check CHECK (client_id IS NOT NULL)
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: analyses analyses_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_name_key UNIQUE (name);


--
-- Name: analyses analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_pkey PRIMARY KEY (id);


--
-- Name: analysis_analytes analysis_analytes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_analytes
    ADD CONSTRAINT analysis_analytes_pkey PRIMARY KEY (analysis_id, analyte_id);


--
-- Name: analytes analytes_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytes
    ADD CONSTRAINT analytes_name_key UNIQUE (name);


--
-- Name: analytes analytes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytes
    ADD CONSTRAINT analytes_pkey PRIMARY KEY (id);


--
-- Name: batch_containers batch_containers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_containers
    ADD CONSTRAINT batch_containers_pkey PRIMARY KEY (batch_id, container_id);


--
-- Name: batches batches_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_name_key UNIQUE (name);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (id);


--
-- Name: battery_analyses battery_analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.battery_analyses
    ADD CONSTRAINT battery_analyses_pkey PRIMARY KEY (battery_id, analysis_id);


--
-- Name: client_projects client_projects_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_projects
    ADD CONSTRAINT client_projects_name_key UNIQUE (name);


--
-- Name: client_projects client_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_projects
    ADD CONSTRAINT client_projects_pkey PRIMARY KEY (id);


--
-- Name: clients clients_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_name_key UNIQUE (name);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: contact_methods contact_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_methods
    ADD CONSTRAINT contact_methods_pkey PRIMARY KEY (id);


--
-- Name: container_types container_types_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.container_types
    ADD CONSTRAINT container_types_name_key UNIQUE (name);


--
-- Name: container_types container_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.container_types
    ADD CONSTRAINT container_types_pkey PRIMARY KEY (id);


--
-- Name: containers containers_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_name_key UNIQUE (name);


--
-- Name: containers containers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_pkey PRIMARY KEY (id);


--
-- Name: contents contents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_pkey PRIMARY KEY (container_id, sample_id);


--
-- Name: custom_attributes_config custom_attributes_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_attributes_config
    ADD CONSTRAINT custom_attributes_config_pkey PRIMARY KEY (id);


--
-- Name: help_entries help_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_entries
    ADD CONSTRAINT help_entries_pkey PRIMARY KEY (id);


--
-- Name: list_entries list_entries_list_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.list_entries
    ADD CONSTRAINT list_entries_list_id_name_key UNIQUE (list_id, name);


--
-- Name: list_entries list_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.list_entries
    ADD CONSTRAINT list_entries_pkey PRIMARY KEY (id);


--
-- Name: lists lists_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lists
    ADD CONSTRAINT lists_name_key UNIQUE (name);


--
-- Name: lists lists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lists
    ADD CONSTRAINT lists_pkey PRIMARY KEY (id);


--
-- Name: locations locations_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_name_key UNIQUE (name);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: name_templates name_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.name_templates
    ADD CONSTRAINT name_templates_pkey PRIMARY KEY (id);


--
-- Name: people_locations people_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_locations
    ADD CONSTRAINT people_locations_pkey PRIMARY KEY (person_id, location_id);


--
-- Name: people people_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_name_key UNIQUE (name);


--
-- Name: people people_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_key UNIQUE (name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: project_users project_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_users
    ADD CONSTRAINT project_users_pkey PRIMARY KEY (project_id, user_id);


--
-- Name: projects projects_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_name_key UNIQUE (name);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: results results_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_name_key UNIQUE (name);


--
-- Name: results results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: samples samples_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_name_key UNIQUE (name);


--
-- Name: samples samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_pkey PRIMARY KEY (id);


--
-- Name: test_batteries test_batteries_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_batteries
    ADD CONSTRAINT test_batteries_name_key UNIQUE (name);


--
-- Name: test_batteries test_batteries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_batteries
    ADD CONSTRAINT test_batteries_pkey PRIMARY KEY (id);


--
-- Name: tests tests_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_name_key UNIQUE (name);


--
-- Name: tests tests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_pkey PRIMARY KEY (id);


--
-- Name: units units_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_name_key UNIQUE (name);


--
-- Name: units units_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_pkey PRIMARY KEY (id);


--
-- Name: custom_attributes_config uq_custom_attributes_config_entity_attr; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_attributes_config
    ADD CONSTRAINT uq_custom_attributes_config_entity_attr UNIQUE (entity_type, attr_name);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_name_key UNIQUE (name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: users users_client_id_not_null_check; Type: CHECK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_client_id_not_null_check CHECK (client_id IS NOT NULL);


--
-- Name: idx_analyses_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_analyses_name_unique ON public.analyses USING btree (name);


--
-- Name: idx_analyses_shelf_life; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analyses_shelf_life ON public.analyses USING btree (shelf_life) WHERE (shelf_life IS NOT NULL);


--
-- Name: idx_analysis_analytes_analysis_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_analytes_analysis_id ON public.analysis_analytes USING btree (analysis_id);


--
-- Name: idx_analysis_analytes_analyte_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_analytes_analyte_id ON public.analysis_analytes USING btree (analyte_id);


--
-- Name: idx_analysis_analytes_list_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_analytes_list_id ON public.analysis_analytes USING btree (list_id);


--
-- Name: idx_analytes_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_analytes_name_unique ON public.analytes USING btree (name);


--
-- Name: idx_batch_containers_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batch_containers_batch_id ON public.batch_containers USING btree (batch_id);


--
-- Name: idx_batch_containers_container_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batch_containers_container_id ON public.batch_containers USING btree (container_id);


--
-- Name: idx_batches_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batches_custom_attributes_gin ON public.batches USING gin (custom_attributes);


--
-- Name: idx_batches_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_batches_name_unique ON public.batches USING btree (name);


--
-- Name: idx_batches_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batches_status ON public.batches USING btree (status);


--
-- Name: idx_batches_status_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batches_status_active ON public.batches USING btree (status) WHERE (active = true);


--
-- Name: idx_batches_status_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batches_status_type ON public.batches USING btree (status, type);


--
-- Name: idx_batches_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batches_type ON public.batches USING btree (type);


--
-- Name: idx_battery_analyses_battery_analysis; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_battery_analyses_battery_analysis ON public.battery_analyses USING btree (battery_id, analysis_id);


--
-- Name: idx_battery_analyses_battery_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_battery_analyses_battery_id ON public.battery_analyses USING btree (battery_id);


--
-- Name: idx_battery_analyses_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_battery_analyses_sequence ON public.battery_analyses USING btree (battery_id, sequence);


--
-- Name: idx_client_projects_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_client_projects_client_id ON public.client_projects USING btree (client_id);


--
-- Name: idx_client_projects_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_client_projects_custom_attributes_gin ON public.client_projects USING gin (custom_attributes);


--
-- Name: idx_clients_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_clients_name_unique ON public.clients USING btree (name);


--
-- Name: idx_contact_methods_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_methods_person_id ON public.contact_methods USING btree (person_id);


--
-- Name: idx_contact_methods_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_methods_type ON public.contact_methods USING btree (type);


--
-- Name: idx_containers_amount_units; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_amount_units ON public.containers USING btree (amount_units);


--
-- Name: idx_containers_concentration_units; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_concentration_units ON public.containers USING btree (concentration_units);


--
-- Name: idx_containers_modified_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_modified_at ON public.containers USING btree (modified_at);


--
-- Name: idx_containers_modified_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_modified_by ON public.containers USING btree (modified_by);


--
-- Name: idx_containers_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_containers_name_unique ON public.containers USING btree (name);


--
-- Name: idx_containers_parent_container_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_parent_container_id ON public.containers USING btree (parent_container_id);


--
-- Name: idx_containers_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_type_id ON public.containers USING btree (type_id);


--
-- Name: idx_containers_type_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_type_id_active ON public.containers USING btree (type_id) WHERE (active = true);


--
-- Name: idx_containers_type_id_parent_container_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_containers_type_id_parent_container_id ON public.containers USING btree (type_id, parent_container_id);


--
-- Name: idx_contents_amount_units; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contents_amount_units ON public.contents USING btree (amount_units);


--
-- Name: idx_contents_concentration_units; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contents_concentration_units ON public.contents USING btree (concentration_units);


--
-- Name: idx_contents_container_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contents_container_id ON public.contents USING btree (container_id);


--
-- Name: idx_contents_sample_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contents_sample_id ON public.contents USING btree (sample_id);


--
-- Name: idx_custom_attributes_config_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_custom_attributes_config_active ON public.custom_attributes_config USING btree (active);


--
-- Name: idx_custom_attributes_config_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_custom_attributes_config_entity_type ON public.custom_attributes_config USING btree (entity_type);


--
-- Name: idx_help_entries_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_help_entries_active ON public.help_entries USING btree (active);


--
-- Name: idx_help_entries_role_filter; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_help_entries_role_filter ON public.help_entries USING btree (role_filter);


--
-- Name: idx_help_entries_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_help_entries_section ON public.help_entries USING btree (section);


--
-- Name: idx_list_entries_list_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_list_entries_list_id ON public.list_entries USING btree (list_id);


--
-- Name: idx_list_entries_list_id_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_list_entries_list_id_name_unique ON public.list_entries USING btree (list_id, name);


--
-- Name: idx_lists_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_lists_name_unique ON public.lists USING btree (name);


--
-- Name: idx_locations_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_client_id ON public.locations USING btree (client_id);


--
-- Name: idx_locations_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_type ON public.locations USING btree (type);


--
-- Name: idx_name_templates_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_name_templates_entity_type ON public.name_templates USING btree (entity_type);


--
-- Name: idx_name_templates_entity_type_active_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_name_templates_entity_type_active_unique ON public.name_templates USING btree (entity_type) WHERE (active = true);


--
-- Name: idx_people_locations_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_people_locations_location_id ON public.people_locations USING btree (location_id);


--
-- Name: idx_people_locations_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_people_locations_person_id ON public.people_locations USING btree (person_id);


--
-- Name: idx_project_users_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_users_project_id ON public.project_users USING btree (project_id);


--
-- Name: idx_project_users_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_users_user_id ON public.project_users USING btree (user_id);


--
-- Name: idx_projects_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_client_id ON public.projects USING btree (client_id);


--
-- Name: idx_projects_client_id_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_client_id_status ON public.projects USING btree (client_id, status);


--
-- Name: idx_projects_client_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_client_project_id ON public.projects USING btree (client_project_id);


--
-- Name: idx_projects_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_custom_attributes_gin ON public.projects USING gin (custom_attributes);


--
-- Name: idx_projects_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_due_date ON public.projects USING btree (due_date) WHERE (due_date IS NOT NULL);


--
-- Name: idx_projects_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_projects_name_unique ON public.projects USING btree (name);


--
-- Name: idx_projects_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_status ON public.projects USING btree (status);


--
-- Name: idx_results_analyte_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_analyte_id ON public.results USING btree (analyte_id);


--
-- Name: idx_results_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_created_by ON public.results USING btree (created_by);


--
-- Name: idx_results_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_custom_attributes_gin ON public.results USING gin (custom_attributes);


--
-- Name: idx_results_entered_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_entered_by ON public.results USING btree (entered_by);


--
-- Name: idx_results_modified_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_modified_by ON public.results USING btree (modified_by);


--
-- Name: idx_results_qualifiers; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_qualifiers ON public.results USING btree (qualifiers);


--
-- Name: idx_results_test_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_test_id ON public.results USING btree (test_id);


--
-- Name: idx_results_test_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_test_id_active ON public.results USING btree (test_id) WHERE (active = true);


--
-- Name: idx_results_test_id_analyte_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_results_test_id_analyte_id ON public.results USING btree (test_id, analyte_id);


--
-- Name: idx_samples_client_sample_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_samples_client_sample_id ON public.samples USING btree (client_sample_id);


--
-- Name: idx_samples_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_created_by ON public.samples USING btree (created_by);


--
-- Name: idx_samples_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_custom_attributes_gin ON public.samples USING gin (custom_attributes);


--
-- Name: idx_samples_date_sampled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_date_sampled ON public.samples USING btree (date_sampled) WHERE (date_sampled IS NOT NULL);


--
-- Name: idx_samples_matrix; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_matrix ON public.samples USING btree (matrix);


--
-- Name: idx_samples_modified_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_modified_at ON public.samples USING btree (modified_at);


--
-- Name: idx_samples_modified_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_modified_by ON public.samples USING btree (modified_by);


--
-- Name: idx_samples_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_samples_name_unique ON public.samples USING btree (name);


--
-- Name: idx_samples_parent_sample_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_parent_sample_id ON public.samples USING btree (parent_sample_id);


--
-- Name: idx_samples_prioritization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_prioritization ON public.samples USING btree (project_id, due_date, date_sampled) WHERE (active = true);


--
-- Name: idx_samples_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_project_id ON public.samples USING btree (project_id);


--
-- Name: idx_samples_project_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_project_id_active ON public.samples USING btree (project_id) WHERE (active = true);


--
-- Name: idx_samples_project_id_qc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_project_id_qc_type ON public.samples USING btree (project_id, qc_type);


--
-- Name: idx_samples_project_id_sample_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_project_id_sample_type ON public.samples USING btree (project_id, sample_type);


--
-- Name: idx_samples_project_id_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_project_id_status ON public.samples USING btree (project_id, status);


--
-- Name: idx_samples_qc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_qc_type ON public.samples USING btree (qc_type);


--
-- Name: idx_samples_sample_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_sample_type ON public.samples USING btree (sample_type);


--
-- Name: idx_samples_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_status ON public.samples USING btree (status);


--
-- Name: idx_test_batteries_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_test_batteries_name ON public.test_batteries USING btree (name);


--
-- Name: idx_tests_analysis_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_analysis_id ON public.tests USING btree (analysis_id);


--
-- Name: idx_tests_analysis_id_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_analysis_id_status ON public.tests USING btree (analysis_id, status);


--
-- Name: idx_tests_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_created_by ON public.tests USING btree (created_by);


--
-- Name: idx_tests_custom_attributes_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_custom_attributes_gin ON public.tests USING gin (custom_attributes);


--
-- Name: idx_tests_modified_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_modified_at ON public.tests USING btree (modified_at);


--
-- Name: idx_tests_modified_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_modified_by ON public.tests USING btree (modified_by);


--
-- Name: idx_tests_sample_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_sample_id ON public.tests USING btree (sample_id);


--
-- Name: idx_tests_sample_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_sample_id_active ON public.tests USING btree (sample_id) WHERE (active = true);


--
-- Name: idx_tests_sample_id_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_sample_id_status ON public.tests USING btree (sample_id, status);


--
-- Name: idx_tests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_status ON public.tests USING btree (status);


--
-- Name: idx_tests_technician_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tests_technician_id ON public.tests USING btree (technician_id);


--
-- Name: idx_units_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_units_name_unique ON public.units USING btree (name);


--
-- Name: idx_units_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_units_type ON public.units USING btree (type);


--
-- Name: idx_users_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_client_id ON public.users USING btree (client_id);


--
-- Name: idx_users_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_created_by ON public.users USING btree (created_by);


--
-- Name: idx_users_email_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_users_email_unique ON public.users USING btree (email);


--
-- Name: idx_users_modified_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_modified_by ON public.users USING btree (modified_by);


--
-- Name: idx_users_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role_id ON public.users USING btree (role_id);


--
-- Name: idx_users_role_id_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role_id_client_id ON public.users USING btree (role_id, client_id);


--
-- Name: idx_users_username_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_users_username_unique ON public.users USING btree (username);


--
-- Name: analyses analyses_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER analyses_audit_timestamps BEFORE INSERT OR UPDATE ON public.analyses FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: analyses analyses_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER analyses_update_modified_at BEFORE UPDATE ON public.analyses FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: analytes analytes_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER analytes_audit_timestamps BEFORE INSERT OR UPDATE ON public.analytes FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: analytes analytes_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER analytes_update_modified_at BEFORE UPDATE ON public.analytes FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: batches batches_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER batches_audit_timestamps BEFORE INSERT OR UPDATE ON public.batches FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: batches batches_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER batches_update_modified_at BEFORE UPDATE ON public.batches FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: clients clients_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER clients_audit_timestamps BEFORE INSERT OR UPDATE ON public.clients FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: clients clients_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER clients_update_modified_at BEFORE UPDATE ON public.clients FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: container_types container_types_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER container_types_audit_timestamps BEFORE INSERT OR UPDATE ON public.container_types FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: container_types container_types_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER container_types_update_modified_at BEFORE UPDATE ON public.container_types FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: containers containers_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER containers_audit_timestamps BEFORE INSERT OR UPDATE ON public.containers FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: containers containers_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER containers_update_modified_at BEFORE UPDATE ON public.containers FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: list_entries list_entries_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER list_entries_audit_timestamps BEFORE INSERT OR UPDATE ON public.list_entries FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: list_entries list_entries_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER list_entries_update_modified_at BEFORE UPDATE ON public.list_entries FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: lists lists_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lists_audit_timestamps BEFORE INSERT OR UPDATE ON public.lists FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: lists lists_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lists_update_modified_at BEFORE UPDATE ON public.lists FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: locations locations_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER locations_audit_timestamps BEFORE INSERT OR UPDATE ON public.locations FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: locations locations_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER locations_update_modified_at BEFORE UPDATE ON public.locations FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: name_templates name_templates_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER name_templates_audit_timestamps BEFORE INSERT OR UPDATE ON public.name_templates FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: name_templates name_templates_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER name_templates_update_modified_at BEFORE UPDATE ON public.name_templates FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: people people_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER people_audit_timestamps BEFORE INSERT OR UPDATE ON public.people FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: people people_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER people_update_modified_at BEFORE UPDATE ON public.people FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: permissions permissions_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER permissions_audit_timestamps BEFORE INSERT OR UPDATE ON public.permissions FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: permissions permissions_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER permissions_update_modified_at BEFORE UPDATE ON public.permissions FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: projects projects_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER projects_audit_timestamps BEFORE INSERT OR UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: projects projects_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER projects_update_modified_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: results results_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER results_audit_timestamps BEFORE INSERT OR UPDATE ON public.results FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: results results_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER results_update_modified_at BEFORE UPDATE ON public.results FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: roles roles_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER roles_audit_timestamps BEFORE INSERT OR UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: roles roles_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER roles_update_modified_at BEFORE UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: samples samples_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER samples_audit_timestamps BEFORE INSERT OR UPDATE ON public.samples FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: samples samples_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER samples_update_modified_at BEFORE UPDATE ON public.samples FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: tests tests_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tests_audit_timestamps BEFORE INSERT OR UPDATE ON public.tests FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: tests tests_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tests_update_modified_at BEFORE UPDATE ON public.tests FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: units units_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER units_audit_timestamps BEFORE INSERT OR UPDATE ON public.units FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: units units_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER units_update_modified_at BEFORE UPDATE ON public.units FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: users users_audit_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_audit_timestamps BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_audit_timestamps();


--
-- Name: users users_update_modified_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_update_modified_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_modified_at_column();


--
-- Name: analysis_analytes analysis_analytes_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_analytes
    ADD CONSTRAINT analysis_analytes_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.analyses(id);


--
-- Name: analysis_analytes analysis_analytes_analyte_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_analytes
    ADD CONSTRAINT analysis_analytes_analyte_id_fkey FOREIGN KEY (analyte_id) REFERENCES public.analytes(id);


--
-- Name: analysis_analytes analysis_analytes_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_analytes
    ADD CONSTRAINT analysis_analytes_list_id_fkey FOREIGN KEY (list_id) REFERENCES public.lists(id);


--
-- Name: batch_containers batch_containers_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_containers
    ADD CONSTRAINT batch_containers_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(id);


--
-- Name: batch_containers batch_containers_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_containers
    ADD CONSTRAINT batch_containers_container_id_fkey FOREIGN KEY (container_id) REFERENCES public.containers(id);


--
-- Name: batches batches_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_status_fkey FOREIGN KEY (status) REFERENCES public.list_entries(id);


--
-- Name: batches batches_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_type_fkey FOREIGN KEY (type) REFERENCES public.list_entries(id);


--
-- Name: battery_analyses battery_analyses_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.battery_analyses
    ADD CONSTRAINT battery_analyses_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.analyses(id) ON DELETE RESTRICT;


--
-- Name: battery_analyses battery_analyses_battery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.battery_analyses
    ADD CONSTRAINT battery_analyses_battery_id_fkey FOREIGN KEY (battery_id) REFERENCES public.test_batteries(id);


--
-- Name: client_projects client_projects_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_projects
    ADD CONSTRAINT client_projects_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: client_projects client_projects_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_projects
    ADD CONSTRAINT client_projects_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: client_projects client_projects_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_projects
    ADD CONSTRAINT client_projects_modified_by_fkey FOREIGN KEY (modified_by) REFERENCES public.users(id);


--
-- Name: contact_methods contact_methods_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_methods
    ADD CONSTRAINT contact_methods_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.people(id);


--
-- Name: contact_methods contact_methods_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_methods
    ADD CONSTRAINT contact_methods_type_fkey FOREIGN KEY (type) REFERENCES public.list_entries(id);


--
-- Name: containers containers_amount_units_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_amount_units_fkey FOREIGN KEY (amount_units) REFERENCES public.units(id);


--
-- Name: containers containers_concentration_units_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_concentration_units_fkey FOREIGN KEY (concentration_units) REFERENCES public.units(id);


--
-- Name: containers containers_parent_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_parent_container_id_fkey FOREIGN KEY (parent_container_id) REFERENCES public.containers(id);


--
-- Name: containers containers_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.containers
    ADD CONSTRAINT containers_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.container_types(id);


--
-- Name: contents contents_amount_units_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_amount_units_fkey FOREIGN KEY (amount_units) REFERENCES public.units(id);


--
-- Name: contents contents_concentration_units_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_concentration_units_fkey FOREIGN KEY (concentration_units) REFERENCES public.units(id);


--
-- Name: contents contents_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_container_id_fkey FOREIGN KEY (container_id) REFERENCES public.containers(id);


--
-- Name: contents contents_sample_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES public.samples(id);


--
-- Name: custom_attributes_config custom_attributes_config_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_attributes_config
    ADD CONSTRAINT custom_attributes_config_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: custom_attributes_config custom_attributes_config_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_attributes_config
    ADD CONSTRAINT custom_attributes_config_modified_by_fkey FOREIGN KEY (modified_by) REFERENCES public.users(id);


--
-- Name: analytes fk_analytes_units_default; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytes
    ADD CONSTRAINT fk_analytes_units_default FOREIGN KEY (units_default) REFERENCES public.units(id) ON DELETE SET NULL;


--
-- Name: help_entries help_entries_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_entries
    ADD CONSTRAINT help_entries_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: help_entries help_entries_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_entries
    ADD CONSTRAINT help_entries_modified_by_fkey FOREIGN KEY (modified_by) REFERENCES public.users(id);


--
-- Name: list_entries list_entries_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.list_entries
    ADD CONSTRAINT list_entries_list_id_fkey FOREIGN KEY (list_id) REFERENCES public.lists(id);


--
-- Name: locations locations_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: locations locations_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_type_fkey FOREIGN KEY (type) REFERENCES public.list_entries(id);


--
-- Name: name_templates name_templates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.name_templates
    ADD CONSTRAINT name_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: name_templates name_templates_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.name_templates
    ADD CONSTRAINT name_templates_modified_by_fkey FOREIGN KEY (modified_by) REFERENCES public.users(id);


--
-- Name: people_locations people_locations_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_locations
    ADD CONSTRAINT people_locations_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: people_locations people_locations_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_locations
    ADD CONSTRAINT people_locations_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.people(id);


--
-- Name: people people_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_role_fkey FOREIGN KEY (role) REFERENCES public.list_entries(id);


--
-- Name: project_users project_users_access_level_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_users
    ADD CONSTRAINT project_users_access_level_fkey FOREIGN KEY (access_level) REFERENCES public.list_entries(id);


--
-- Name: project_users project_users_granted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_users
    ADD CONSTRAINT project_users_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.users(id);


--
-- Name: project_users project_users_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_users
    ADD CONSTRAINT project_users_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_users project_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_users
    ADD CONSTRAINT project_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: projects projects_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: projects projects_client_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_client_project_id_fkey FOREIGN KEY (client_project_id) REFERENCES public.client_projects(id);


--
-- Name: projects projects_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_status_fkey FOREIGN KEY (status) REFERENCES public.list_entries(id);


--
-- Name: results results_analyte_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_analyte_id_fkey FOREIGN KEY (analyte_id) REFERENCES public.analytes(id);


--
-- Name: results results_entered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_entered_by_fkey FOREIGN KEY (entered_by) REFERENCES public.users(id);


--
-- Name: results results_qualifiers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_qualifiers_fkey FOREIGN KEY (qualifiers) REFERENCES public.list_entries(id);


--
-- Name: results results_test_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id);


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id);


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: samples samples_matrix_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_matrix_fkey FOREIGN KEY (matrix) REFERENCES public.list_entries(id);


--
-- Name: samples samples_parent_sample_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_parent_sample_id_fkey FOREIGN KEY (parent_sample_id) REFERENCES public.samples(id);


--
-- Name: samples samples_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: samples samples_qc_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_qc_type_fkey FOREIGN KEY (qc_type) REFERENCES public.list_entries(id);


--
-- Name: samples samples_sample_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_sample_type_fkey FOREIGN KEY (sample_type) REFERENCES public.list_entries(id);


--
-- Name: samples samples_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_status_fkey FOREIGN KEY (status) REFERENCES public.list_entries(id);


--
-- Name: test_batteries test_batteries_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_batteries
    ADD CONSTRAINT test_batteries_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: test_batteries test_batteries_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_batteries
    ADD CONSTRAINT test_batteries_modified_by_fkey FOREIGN KEY (modified_by) REFERENCES public.users(id);


--
-- Name: tests tests_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.analyses(id);


--
-- Name: tests tests_sample_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES public.samples(id);


--
-- Name: tests tests_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_status_fkey FOREIGN KEY (status) REFERENCES public.list_entries(id);


--
-- Name: tests tests_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.users(id);


--
-- Name: units units_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_type_fkey FOREIGN KEY (type) REFERENCES public.list_entries(id);


--
-- Name: users users_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: batches; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.batches ENABLE ROW LEVEL SECURITY;

--
-- Name: batches batches_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY batches_access ON public.batches USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM (((public.batch_containers bc
     JOIN public.containers c ON ((bc.container_id = c.id)))
     JOIN public.contents ct ON ((c.id = ct.container_id)))
     JOIN public.samples s ON ((ct.sample_id = s.id)))
  WHERE ((bc.batch_id = batches.id) AND public.has_project_access(s.project_id))))));


--
-- Name: client_projects; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.client_projects ENABLE ROW LEVEL SECURITY;

--
-- Name: client_projects client_projects_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY client_projects_access ON public.client_projects USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM public.users u
  WHERE ((u.id = public.current_user_id()) AND (u.client_id = client_projects.client_id)))) OR (EXISTS ( SELECT 1
   FROM (public.users u
     JOIN public.roles r ON ((u.role_id = r.id)))
  WHERE ((u.id = public.current_user_id()) AND ((r.name)::text = ANY ((ARRAY['Lab Technician'::character varying, 'Lab Manager'::character varying])::text[])) AND (client_projects.active = true))))));


--
-- Name: containers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.containers ENABLE ROW LEVEL SECURITY;

--
-- Name: containers containers_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY containers_access ON public.containers USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM (public.contents c
     JOIN public.samples s ON ((c.sample_id = s.id)))
  WHERE ((c.container_id = containers.id) AND public.has_project_access(s.project_id))))));


--
-- Name: custom_attributes_config; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.custom_attributes_config ENABLE ROW LEVEL SECURITY;

--
-- Name: custom_attributes_config custom_attributes_config_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY custom_attributes_config_access ON public.custom_attributes_config USING ((public.is_admin() OR (active = true)));


--
-- Name: help_entries; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.help_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: help_entries help_entries_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY help_entries_access ON public.help_entries USING (((active = true) AND (public.is_admin() OR (role_filter IS NULL) OR (EXISTS ( SELECT 1
   FROM (public.users u
     JOIN public.roles r ON ((u.role_id = r.id)))
  WHERE ((u.id = public.current_user_id()) AND ((r.name)::text = (help_entries.role_filter)::text)))))));


--
-- Name: name_templates; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.name_templates ENABLE ROW LEVEL SECURITY;

--
-- Name: name_templates name_templates_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY name_templates_access ON public.name_templates USING ((public.is_admin() OR (active = true)));


--
-- Name: projects; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

--
-- Name: projects projects_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY projects_access ON public.projects USING ((public.is_admin() OR public.has_project_access(id) OR (EXISTS ( SELECT 1
   FROM (public.users u
     JOIN public.roles r ON ((u.role_id = r.id)))
  WHERE ((u.id = public.current_user_id()) AND ((r.name)::text = 'Client'::text) AND (u.client_id IS NOT NULL) AND (projects.client_id = u.client_id)))) OR (EXISTS ( SELECT 1
   FROM (public.users u
     JOIN public.roles r ON ((u.role_id = r.id)))
  WHERE ((u.id = public.current_user_id()) AND ((r.name)::text = ANY ((ARRAY['Lab Technician'::character varying, 'Lab Manager'::character varying])::text[])) AND (projects.active = true))))));


--
-- Name: results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.results ENABLE ROW LEVEL SECURITY;

--
-- Name: results results_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY results_access ON public.results USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM (public.tests t
     JOIN public.samples s ON ((t.sample_id = s.id)))
  WHERE ((t.id = results.test_id) AND public.has_project_access(s.project_id))))));


--
-- Name: samples; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.samples ENABLE ROW LEVEL SECURITY;

--
-- Name: samples samples_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY samples_access ON public.samples USING ((public.is_admin() OR public.has_project_access(project_id)));


--
-- Name: tests; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.tests ENABLE ROW LEVEL SECURITY;

--
-- Name: tests tests_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tests_access ON public.tests USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM public.samples s
  WHERE ((s.id = tests.sample_id) AND public.has_project_access(s.project_id))))));


--
-- PostgreSQL database dump complete
--

\unrestrict hHarTGLBbfyk2VER7ZMIgboTQe6RwIEMnYh8GwpZyGhDjMreI5EDfNpnFNesLVf

