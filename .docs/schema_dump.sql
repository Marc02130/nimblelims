--
-- PostgreSQL database dump
--

\restrict Z4TPlRAC00dvzwOQSSp9rU5VOUB37LIsnFUFkRvWiwrtWXwhvgnRLgNOlXFWDoM

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
DROP INDEX IF EXISTS public.idx_samples_parent_sample_id;
DROP INDEX IF EXISTS public.idx_samples_name_unique;
DROP INDEX IF EXISTS public.idx_samples_modified_by;
DROP INDEX IF EXISTS public.idx_samples_modified_at;
DROP INDEX IF EXISTS public.idx_samples_matrix;
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
    cost numeric(10,2)
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
    modified_by uuid
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
    custom_attributes jsonb DEFAULT '{}'::jsonb
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
    custom_attributes jsonb DEFAULT '{}'::jsonb
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
    client_id uuid,
    last_login timestamp without time zone
);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
0024
\.


--
-- Data for Name: analyses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analyses (id, name, description, active, created_at, created_by, modified_at, modified_by, method, turnaround_time, cost) FROM stdin;
b0000001-b000-b000-b000-b00000000001	pH Measurement	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	Electrometric	1	10.00
b0000002-b000-b000-b000-b00000000002	EPA Method 8080	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	GC/ECD for Organochlorine Pesticides and PCBs	7	150.00
b0000003-b000-b000-b000-b00000000003	Total Coliform Enumeration	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	Colilert or Membrane Filtration	2	50.00
b0000002-b000-b000-b000-b00000000004	EPA Method 8080 Prep	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	Sample Extractionfor Organochlorine Pesticides and PCBs	7	25.00
\.


--
-- Data for Name: analysis_analytes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analysis_analytes (analysis_id, analyte_id, data_type, list_id, high_value, low_value, significant_figures, calculation, reported_name, display_order, is_required, default_value) FROM stdin;
b0000001-b000-b000-b000-b00000000001	a0000001-a000-a000-a000-a00000000001	numeric	\N	14.000000	0.000000	2	\N	\N	\N	t	\N
b0000002-b000-b000-b000-b00000000002	a0000002-a000-a000-a000-a00000000002	numeric	\N	\N	0.000000	3	\N	\N	\N	t	\N
b0000002-b000-b000-b000-b00000000002	a0000003-a000-a000-a000-a00000000003	numeric	\N	\N	0.000000	3	\N	\N	\N	t	\N
b0000002-b000-b000-b000-b00000000002	a0000004-a000-a000-a000-a00000000004	numeric	\N	\N	0.000000	3	\N	\N	\N	t	\N
b0000002-b000-b000-b000-b00000000004	a0000004-a000-a000-a000-a00000000005	numeric	\N	\N	0.000000	3	\N	\N	\N	t	\N
b0000003-b000-b000-b000-b00000000003	a0000005-a000-a000-a000-a00000000005	count	\N	\N	0.000000	0	\N	\N	\N	t	\N
b0000003-b000-b000-b000-b00000000003	a0000006-a000-a000-a000-a00000000006	count	\N	\N	0.000000	0	\N	\N	\N	t	\N
\.


--
-- Data for Name: analytes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analytes (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
a0000001-a000-a000-a000-a00000000001	pH	pH value	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000002-a000-a000-a000-a00000000002	Aldrin	Organochlorine pesticide	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000003-a000-a000-a000-a00000000003	DDT	Organochlorine pesticide	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000004-a000-a000-a000-a00000000004	PCB-1016	Polychlorinated biphenyl	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000005-a000-a000-a000-a00000000005	Total Coliforms	Coliform bacteria count	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000006-a000-a000-a000-a00000000006	E. coli	Escherichia coli count	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0000004-a000-a000-a000-a00000000005	Initial Volume	Sample volume extracted	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: batch_containers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batch_containers (batch_id, container_id, "position", notes) FROM stdin;
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batches (id, name, description, active, created_at, created_by, modified_at, modified_by, type, status, start_date, end_date, custom_attributes) FROM stdin;
\.


--
-- Data for Name: battery_analyses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.battery_analyses (battery_id, analysis_id, sequence, optional) FROM stdin;
c0000001-c000-c000-c000-c00000000001	b0000002-b000-b000-b000-b00000000002	2	f
c0000001-c000-c000-c000-c00000000001	b0000002-b000-b000-b000-b00000000004	1	f
\.


--
-- Data for Name: client_projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.client_projects (id, name, description, client_id, active, created_at, created_by, modified_at, modified_by, custom_attributes) FROM stdin;
22222222-2222-2222-2222-222222222222	UAT Test Project	Test client project for UAT testing	11111111-1111-1111-1111-111111111111	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	{}
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clients (id, name, description, active, created_at, created_by, modified_at, modified_by, billing_info) FROM stdin;
00000000-0000-0000-0000-000000000001	System	System client for admin users	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	{}
11111111-1111-1111-1111-111111111111	UAT Test Client	Test client for UAT testing	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	{"zip": "12345", "city": "Test City", "state": "TS", "address": "123 Test St"}
\.


--
-- Data for Name: contact_methods; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contact_methods (id, person_id, type, value, description, "primary", verified) FROM stdin;
\.


--
-- Data for Name: container_types; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.container_types (id, name, description, active, created_at, created_by, modified_at, modified_by, capacity, material, dimensions, preservative) FROM stdin;
33333333-3333-3333-3333-333333333333	Test Tube (15mL)	Standard 15mL test tube for UAT testing	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	15.000	polypropylene	15x100mm	\N
\.


--
-- Data for Name: containers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.containers (id, name, description, active, created_at, created_by, modified_at, modified_by, "row", "column", concentration, concentration_units, amount, amount_units, type_id, parent_container_id) FROM stdin;
57bbf8db-f897-4597-828e-1f9724e13686	r4563324	\N	t	2026-01-08 00:46:43.748555	00000000-0000-0000-0000-000000000003	2026-01-08 00:46:43.748555	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
05d65a3d-8778-4249-ac29-477be42acb89	t56785345t6y	\N	t	2026-01-08 01:14:19.254922	00000000-0000-0000-0000-000000000003	2026-01-08 01:14:19.254922	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
a942521e-1ddf-4dee-8c30-dad44e4c4cdf	f586348	\N	t	2026-01-08 01:29:09.376927	00000000-0000-0000-0000-000000000003	2026-01-08 01:29:09.376927	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
49585315-5fc3-4492-b7f0-33e8a2a22cd8	T5647892	\N	t	2026-01-08 01:35:58.343009	00000000-0000-0000-0000-000000000003	2026-01-08 01:35:58.343009	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
537ae759-473c-423d-94fb-147917852377	G56836	\N	t	2026-01-08 01:51:42.85506	00000000-0000-0000-0000-000000000003	2026-01-08 01:51:42.85506	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
b4d3b241-9a04-417b-b808-f76ec89439b7	r57894837	\N	t	2026-01-08 02:04:14.76583	00000000-0000-0000-0000-000000000003	2026-01-08 02:04:14.76583	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
5f5b1d59-5c74-41f9-9832-33cfd5a0bcf9	432423132	\N	t	2026-01-08 02:09:59.350379	00000000-0000-0000-0000-000000000003	2026-01-08 02:09:59.350379	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
387195f7-73a5-4fa1-b855-2bb838bfe01c	5437890754328	\N	t	2026-01-08 02:26:44.884391	00000000-0000-0000-0000-000000000003	2026-01-08 02:26:44.884391	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
48132fcc-91c7-4f03-bff4-a0f2b2e6ed34	f34543	\N	t	2026-01-08 12:30:22.867861	00000000-0000-0000-0000-000000000003	2026-01-08 12:30:22.867861	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
403f611a-31f7-4e0c-9bf5-43cecea8ecb4	43252345-031407	\N	t	2026-01-08 13:47:11.416452	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:11.416452	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
e813118b-2a3e-452a-a15c-5de0542cb4b5	43252345-064712	\N	t	2026-01-08 13:47:44.720295	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:44.720295	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
5d92d5be-95d8-4465-8004-1d7c4f1093bf	43441554-172789	\N	t	2026-01-08 14:06:12.800299	00000000-0000-0000-0000-000000000003	2026-01-08 14:06:12.800299	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
831fe9d6-1f16-4fbd-9068-86905ab3ca03	423543645763-070104	\N	t	2026-01-08 20:11:10.115791	00000000-0000-0000-0000-000000000003	2026-01-08 20:11:10.115791	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
936032ae-001f-4174-b494-dc22f88b5a70	T5674789-331975	\N	t	2026-01-09 19:02:11.984603	00000000-0000-0000-0000-000000000003	2026-01-09 19:02:11.984603	00000000-0000-0000-0000-000000000003	1	1	\N	\N	\N	\N	33333333-3333-3333-3333-333333333333	\N
\.


--
-- Data for Name: contents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contents (container_id, sample_id, concentration, concentration_units, amount, amount_units) FROM stdin;
48132fcc-91c7-4f03-bff4-a0f2b2e6ed34	f522c2ff-4fdb-4787-b4ca-df26ea54136e	\N	\N	\N	\N
403f611a-31f7-4e0c-9bf5-43cecea8ecb4	b74b8b74-d992-4a1a-8edf-2636f26af415	\N	\N	\N	\N
e813118b-2a3e-452a-a15c-5de0542cb4b5	787a114e-63f5-47fa-b335-be05ad9eb84a	\N	\N	\N	\N
5d92d5be-95d8-4465-8004-1d7c4f1093bf	0d6a1ad2-fcc4-46fe-9147-8dfdc212969c	\N	\N	\N	\N
831fe9d6-1f16-4fbd-9068-86905ab3ca03	c0080188-50c6-4453-81bd-0b8f718064b6	\N	\N	\N	\N
936032ae-001f-4174-b494-dc22f88b5a70	60b4451f-2b44-459c-9eee-ec9e2a46cb02	\N	\N	\N	\N
\.


--
-- Data for Name: custom_attributes_config; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.custom_attributes_config (id, entity_type, attr_name, data_type, validation_rules, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
96330c71-4371-4ad5-ab19-3abb836ae998	samples	pH	number	{"max": 14, "min": 0}	pH at receipt	t	2026-01-07 18:04:29.319199	00000000-0000-0000-0000-000000000001	2026-01-07 18:04:44.019727	00000000-0000-0000-0000-000000000001
1fbec6d5-468f-428c-82d4-1f29c44a0eca	samples	Report_Date	date	{"min_date": "2026-01-06"}	Date sample was reported	t	2026-01-07 18:06:14.925554	00000000-0000-0000-0000-000000000001	2026-01-07 18:06:14.925554	00000000-0000-0000-0000-000000000001
3ef7cec4-d256-41c6-85d2-6be74a994910	samples	Sample_Color	text	{"max_length": 12, "min_length": 3}	\N	t	2026-01-08 00:33:58.206775	00000000-0000-0000-0000-000000000001	2026-01-08 00:34:40.226342	00000000-0000-0000-0000-000000000001
\.


--
-- Data for Name: help_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.help_entries (id, name, description, section, content, role_filter, active, created_at, created_by, modified_at, modified_by) FROM stdin;
1f63cb4c-44f2-40e8-a605-98313eb64816	Viewing Projects	Step-by-step guide to access your samples and results. Navigate to the Projects section to view all projects associated with your client account. Click on a project to see detailed information including samples, tests, and results.	Viewing Projects	Step-by-step guide to access your samples and results. Navigate to the Projects section to view all projects associated with your client account. Click on a project to see detailed information including samples, tests, and results.	Client	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
2c0c3bba-f559-4884-a823-d136b62a1778	Viewing Samples	Learn how to view and filter your samples. In the Samples section, you can see all samples associated with your projects. Use the filters to search by sample name, status, or date range. Click on a sample to view detailed information including test assign	Viewing Samples	Learn how to view and filter your samples. In the Samples section, you can see all samples associated with your projects. Use the filters to search by sample name, status, or date range. Click on a sample to view detailed information including test assignments and results.	Client	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
1a6fd982-e5bb-4ff2-bb39-c6a2556a6dfc	Viewing Results	Understand how to access and interpret your test results. Results are organized by test and sample. Navigate to the Results section to view all completed tests. Each result shows the analyte name, value, units, and any qualifiers. Results are automaticall	Viewing Results	Understand how to access and interpret your test results. Results are organized by test and sample. Navigate to the Results section to view all completed tests. Each result shows the analyte name, value, units, and any qualifiers. Results are automatically updated as tests are completed.	Client	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
0df8a0f0-366e-4866-924e-b99c2e4e3277	Getting Started	Welcome to NimbleLIMS! This system allows you to view your laboratory samples, tests, and results. Start by exploring the Dashboard to see an overview of your projects and samples. Use the navigation menu to access different sections of the system.	Getting Started	Welcome to NimbleLIMS! This system allows you to view your laboratory samples, tests, and results. Start by exploring the Dashboard to see an overview of your projects and samples. Use the navigation menu to access different sections of the system.	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
64cbe1a8-76cd-48f9-a280-704ef42e32f3	Accessioning Workflow	Step-by-step guide to sample accessioning:\n\n1. Enter sample details: name (unique), description, due date, received date, sample type, matrix, storage temperature, and project.\n2. Assign container: Select container type from admin-preconfigured types, ent	Accessioning Workflow	Step-by-step guide to sample accessioning:\n\n1. Enter sample details: name (unique), description, due date, received date, sample type, matrix, storage temperature, and project.\n2. Assign container: Select container type from admin-preconfigured types, enter container name/barcode (unique), set position for plate-based containers.\n3. Assign tests: Choose individual analyses or test battery. System automatically creates tests for all analyses in battery.\n4. Review and submit: Validate all information before submission.\n\nBulk tip (US-24): Enable bulk mode for multiple samples. Enter common fields once, then unique fields per sample in table format. Auto-naming available with prefix and start number.\n\nRequires permission: sample:create	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
ba3abd5e-79cf-4574-937e-af4369a69ad0	Batch Creation	Create batches to group samples for testing:\n\n1. Select containers: Choose containers from available samples. All samples in selected containers must share compatible analyses.\n2. Set batch details: Enter batch type (optional), start date, and notes.\n3. V	Batch Creation	Create batches to group samples for testing:\n\n1. Select containers: Choose containers from available samples. All samples in selected containers must share compatible analyses.\n2. Set batch details: Enter batch type (optional), start date, and notes.\n3. Validate compatibility: System checks that all samples have compatible test assignments before batch creation.\n4. QC requirements: System may require QC samples based on batch type configuration. QC samples are created automatically in the same transaction.\n\nBatch status flow: Created → In Process → Completed. Batch end_date is set automatically when all tests are complete.\n\nRequires permission: batch:create	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
eb7a54dd-5a6e-4c2e-9f9a-894e36646569	Results Entry	Enter test results for samples in a batch:\n\nSingle-test entry:\n1. Select batch and test from Results Management.\n2. System loads all analytes configured for the selected test.\n3. Enter results: For each sample, enter raw_result, reported_result, and quali	Results Entry	Enter test results for samples in a batch:\n\nSingle-test entry:\n1. Select batch and test from Results Management.\n2. System loads all analytes configured for the selected test.\n3. Enter results: For each sample, enter raw_result, reported_result, and qualifiers (if applicable).\n4. Save: System validates all results and creates result records.\n\nBatch results entry (US-28):\n1. Select batch from Results Management.\n2. Use tabular interface: Rows = samples, Columns = analytes.\n3. Enter results directly in table cells with real-time validation.\n4. Submit: All results saved atomically. Test status updates to "Complete" when all analytes entered. Batch status auto-updates to "Completed" when all tests are complete.\n\nValidation: Required fields, numeric ranges, significant figures. QC validation checks for missing results and out-of-range values.\n\nRequires permission: result:create	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
5fecb3a5-9274-4bc1-b1e4-d7a111a2231b	Container Management	Manage sample containers:\n\nContainer types are pre-configured by administrators. During accessioning, select a container type and create the container instance.\n\nContainer details:\n- Name/barcode: Unique identifier (required)\n- Position: Row and column fo	Container Management	Manage sample containers:\n\nContainer types are pre-configured by administrators. During accessioning, select a container type and create the container instance.\n\nContainer details:\n- Name/barcode: Unique identifier (required)\n- Position: Row and column for plate-based containers\n- Concentration and amount: Optional with units\n- Parent container: Optional for hierarchical relationships\n\nContainers are created dynamically during sample accessioning. Samples are always received in a container, which must be specified during accessioning.\n\nRequires permission: container:create	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
3650e4cf-a3e7-4ece-904f-dc61cf12c9f6	Test Assignment	Assign tests to samples during accessioning:\n\nOptions:\n1. Individual analyses: Select one or more analyses from available list. Each analysis creates a separate test instance with status "In Process".\n2. Test battery: Select a pre-configured test battery.	Test Assignment	Assign tests to samples during accessioning:\n\nOptions:\n1. Individual analyses: Select one or more analyses from available list. Each analysis creates a separate test instance with status "In Process".\n2. Test battery: Select a pre-configured test battery. System automatically creates tests for all analyses in battery, ordered by sequence.\n3. Combined: Assign both battery and individual analyses. System prevents duplicate test creation if analysis already exists from battery.\n\nTest status flow: In Process → In Analysis → Complete\n\nAfter assignment, tests are ready for results entry. Tests can be viewed and managed in the Tests section.\n\nRequires permission: test:create	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
901613af-13a7-474c-8de0-3d43f3638304	Getting Started	Welcome to NimbleLIMS! As a Lab Technician, you can:\n\n- Accession samples: Receive and register new samples with test assignments\n- Create batches: Group samples for efficient testing workflows\n- Enter results: Record test results for samples in batches\n-	Getting Started	Welcome to NimbleLIMS! As a Lab Technician, you can:\n\n- Accession samples: Receive and register new samples with test assignments\n- Create batches: Group samples for efficient testing workflows\n- Enter results: Record test results for samples in batches\n- Manage containers: Track sample storage and location\n\nStart by accessing the Dashboard for an overview of your work. Use the navigation menu to access different sections. Each workflow requires specific permissions - contact your Lab Manager if you need additional access.\n\nFor detailed instructions, see the specific help sections for each workflow.	lab-technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
e530a8d2-cfdf-41b0-9f29-2019efd388e6	Results Review	Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.\n\nReview workflow:\n1. Access batch view: Navigate to Results Management and select a batch.\n2. Review test results: Check all analytes for each sample in the batch.\n3. V	Results Review	Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.\n\nReview workflow:\n1. Access batch view: Navigate to Results Management and select a batch.\n2. Review test results: Check all analytes for each sample in the batch.\n3. Validate QC: Ensure QC samples meet acceptance criteria. Flag out-of-range values and missing results.\n4. Approve results: Update test status to "Complete" after review. System records review_date automatically.\n5. Flag issues: Document any anomalies or concerns per US-12 requirements. Contact technicians for clarification if needed.\n\nQuality checks:\n- Verify all required analytes have results\n- Check numeric ranges and significant figures\n- Validate qualifiers are appropriate\n- Ensure batch status progression: Created → In Process → Completed\n\nRequires permission: result:review	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
688dff67-1efa-4b85-8278-144303a8a1b6	Batch Management	Oversee batch operations and workflow:\n\nBatch oversight:\n1. Monitor batch status: Track batches from creation through completion. View all batches with filtering by status, type, and date range.\n2. Review batch composition: Check container assignments and	Batch Management	Oversee batch operations and workflow:\n\nBatch oversight:\n1. Monitor batch status: Track batches from creation through completion. View all batches with filtering by status, type, and date range.\n2. Review batch composition: Check container assignments and sample compatibility. Ensure all samples in a batch have compatible test assignments.\n3. Manage batch lifecycle: Update batch status as needed. Status flow: Created → In Process → Completed.\n4. Batch end_date: Automatically set when all tests are complete, but can be manually adjusted if needed.\n\nQC oversight:\n- Verify QC samples are included when required by batch type\n- Review QC results during results review process\n- Ensure compliance with quality standards\n\nBatch operations:\n- Add or remove containers from batches (before testing begins)\n- Update batch notes and metadata\n- View batch history and audit trail\n\nRequires permission: batch:manage	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
cecda76d-cf56-4e88-9ded-f44e1f9add55	Project Management	Manage projects and client relationships:\n\nProject oversight:\n1. View all projects: Access project list with filtering by client, status, and date range.\n2. Monitor project status: Track projects through lifecycle. Status values managed via lists configur	Project Management	Manage projects and client relationships:\n\nProject oversight:\n1. View all projects: Access project list with filtering by client, status, and date range.\n2. Monitor project status: Track projects through lifecycle. Status values managed via lists configuration.\n3. Review project samples: Access all samples associated with a project to monitor progress and completion.\n4. Client project coordination: Link projects to client projects for billing and reporting purposes.\n\nProject operations:\n- Update project status and metadata\n- Assign users to projects with appropriate access levels\n- Review project timeline and deadlines\n- Monitor sample accessioning and testing progress\n\nClient relationships:\n- Coordinate with clients on project requirements\n- Ensure proper data isolation per client\n- Review client project associations\n\nRequires permission: project:manage	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
fd61ad3e-9e55-4e3f-9ad6-5708f61e99c1	Quality Control	Ensure quality standards and compliance:\n\nQC responsibilities:\n1. Review QC samples: Verify QC samples are created for batches when required by batch type configuration.\n2. Validate QC results: Check that QC results meet acceptance criteria. Flag out-of-r	Quality Control	Ensure quality standards and compliance:\n\nQC responsibilities:\n1. Review QC samples: Verify QC samples are created for batches when required by batch type configuration.\n2. Validate QC results: Check that QC results meet acceptance criteria. Flag out-of-range values and investigate anomalies.\n3. Monitor test accuracy: Review results for consistency and accuracy. Ensure proper use of qualifiers and units.\n4. Compliance checks: Verify adherence to US-12 requirements for issue flagging and documentation.\n\nQuality monitoring:\n- Track QC sample performance over time\n- Identify trends and potential issues\n- Ensure proper documentation of exceptions\n- Coordinate with technicians on quality concerns\n\nIssue management:\n- Flag results that require investigation\n- Document quality issues per US-12\n- Follow up on flagged items until resolution\n- Maintain audit trail of quality actions\n\nRequires permission: result:review	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
5b8de012-99a9-41fe-b359-0647649dfff4	Test Assignment Oversight	Oversee test assignments and configurations:\n\nAssignment oversight:\n1. Review test assignments: Monitor which tests are assigned to samples during accessioning. Ensure appropriate analyses and batteries are used.\n2. Validate test configurations: Verify th	Test Assignment Oversight	Oversee test assignments and configurations:\n\nAssignment oversight:\n1. Review test assignments: Monitor which tests are assigned to samples during accessioning. Ensure appropriate analyses and batteries are used.\n2. Validate test configurations: Verify that test assignments align with project requirements and client specifications.\n3. Monitor test status: Track tests through workflow: In Process → In Analysis → Complete.\n4. Coordinate with technicians: Provide guidance on test assignment decisions and resolve assignment questions.\n\nTest battery management:\n- Review use of pre-configured test batteries\n- Ensure batteries are applied correctly to appropriate sample types\n- Verify battery sequences and optional flags are respected\n\nAnalysis oversight:\n- Monitor which analyses are most frequently used\n- Ensure proper analyte configurations for analyses\n- Coordinate with administrators on analysis configuration needs\n\nRequires permission: test:assign	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
48784703-2643-4268-a446-6146c9c8aabb	Getting Started	Welcome to NimbleLIMS! As a Lab Manager, you oversee laboratory operations:\n\nKey responsibilities:\n- Review and approve results: Ensure quality and accuracy of test results\n- Manage batches: Oversee batch workflows and monitor progress\n- Project managemen	Getting Started	Welcome to NimbleLIMS! As a Lab Manager, you oversee laboratory operations:\n\nKey responsibilities:\n- Review and approve results: Ensure quality and accuracy of test results\n- Manage batches: Oversee batch workflows and monitor progress\n- Project management: Coordinate projects and client relationships\n- Quality control: Maintain quality standards and compliance\n- Test oversight: Monitor test assignments and configurations\n\nStart by accessing the Dashboard for an overview of laboratory operations. Use the navigation menu to access different sections. Review pending results in Results Management, monitor active batches, and track project progress.\n\nFor detailed instructions, see the specific help sections for each workflow. Contact your Administrator if you need additional permissions or access.	lab-manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
281ad5da-41bf-4b1a-a327-a54bb30f8880	User Management	Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.\n\nUser operations:\n1. Create users: Navigate to Users Management. Enter username, email, name, and assign role. Set password or enable password reset.\n	User Management	Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.\n\nUser operations:\n1. Create users: Navigate to Users Management. Enter username, email, name, and assign role. Set password or enable password reset.\n2. Edit users: Update user details, change roles, modify permissions. Users can be activated or deactivated.\n3. Assign roles: Select appropriate role for each user. Roles determine default permissions and access levels.\n4. Client assignment: For Client role users, assign to specific client for data isolation.\n\nRole management:\n- Create custom roles: Define new roles with specific permission sets\n- Edit roles: Modify role permissions and descriptions\n- Permission assignment: Assign permissions to roles using role:manage permission\n- View role permissions: Review which permissions are assigned to each role\n\nPermissions:\n- user:manage: Required for user CRUD operations\n- role:manage: Required for role and permission management\n- config:edit: Required for system configuration changes\n\nBest practices:\n- Use strong passwords and enable password policies\n- Assign minimal required permissions (principle of least privilege)\n- Regularly review user access and deactivate unused accounts\n- Document role changes and permission modifications	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
e673ef6f-32cb-4726-a00e-6433ddced43d	EAV Configuration	Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\nEAV overview:\nThe EAV model enables administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requiremen	EAV Configuration	Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\nEAV overview:\nThe EAV model enables administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requirements.\n\nCustom attributes configuration:\n1. Access EAV config: Navigate to Custom Attributes Management in admin UI.\n2. Create attribute: Define attribute name, entity type (sample, test, etc.), data type (text, number, date, boolean), and validation rules.\n3. Set visibility: Configure which roles can view and edit custom attributes.\n4. Define defaults: Set default values and required flags as needed.\n\nEntity types supported:\n- Samples: Custom fields for sample metadata\n- Tests: Additional test configuration attributes\n- Results: Extended result data fields\n- Projects: Project-specific custom attributes\n\nEAV editing:\n- Edit existing attributes: Modify data types, validation, and visibility\n- Deactivate attributes: Disable without deleting to preserve historical data\n- View attribute usage: See where custom attributes are used across entities\n- Export/import: Backup and restore custom attribute configurations\n\nData management:\n- Custom attribute values are stored in EAV tables\n- Values are queryable and filterable in admin UI\n- Historical values are preserved for audit purposes\n- Bulk updates supported for custom attribute values\n\nRequires permission: config:edit	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
48930f1d-5559-4ae0-b307-c8f47d29c110	Row Level Security (RLS)	Manage Row Level Security policies for data isolation:\n\nRLS overview:\nRow Level Security (RLS) ensures users can only access data they are authorized to view. Policies are enforced at the database level for comprehensive security.\n\nRLS policy management:\n	Row Level Security (RLS)	Manage Row Level Security policies for data isolation:\n\nRLS overview:\nRow Level Security (RLS) ensures users can only access data they are authorized to view. Policies are enforced at the database level for comprehensive security.\n\nRLS policy management:\n1. Review policies: Check existing RLS policies on tables (samples, results, projects, etc.). Policies are defined in database migrations.\n2. Policy structure: Policies use USING clauses to filter rows based on user role, project access, and client assignments.\n3. Admin bypass: Administrator role bypasses RLS restrictions to access all data for system administration.\n4. Client isolation: Client users see only data associated with their assigned client_id.\n\nData isolation:\n- Project-based: Users see samples/projects they are assigned to\n- Client-based: Client users see only their client's data\n- Role-based: Different roles have different access levels\n- Cross-project access: Lab Managers can access multiple projects\n\nPolicy configuration:\n- Policies are created via Alembic migrations\n- Use current_user_id() function to identify current user\n- Use is_admin() function to check administrator status\n- Policies apply to SELECT, INSERT, UPDATE, DELETE operations\n\nTesting RLS:\n- Verify policies work correctly for each role\n- Test data isolation between clients\n- Ensure administrators can access all data\n- Validate project-based access restrictions\n\nRequires permission: config:edit (for policy modifications)	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
0efdc4b7-fd1f-4641-885f-8b6884b19cb4	System Configuration	Manage system-wide configurations and settings:\n\nConfiguration areas:\n1. Container types: Define container types available for sample storage. Configure dimensions, capacity, and position support (for plates).\n2. Analyses: Create and configure analyses wi	System Configuration	Manage system-wide configurations and settings:\n\nConfiguration areas:\n1. Container types: Define container types available for sample storage. Configure dimensions, capacity, and position support (for plates).\n2. Analyses: Create and configure analyses with associated analytes. Set units, significant figures, and validation rules.\n3. Test batteries: Define test batteries with ordered analyses. Configure optional flags and sequences.\n4. Lists: Manage list values for status fields, sample types, matrices, and other enumerated fields.\n5. Units: Configure measurement units and conversion factors.\n\nContainer type management:\n- Create container types: Define new container types with specifications\n- Edit types: Modify container properties and requirements\n- Position support: Enable row/column positions for plate-based containers\n- Capacity settings: Configure maximum samples per container\n\nAnalysis configuration:\n- Create analyses: Define new analyses with name and description\n- Configure analytes: Add analytes to analyses with units and validation\n- Set defaults: Configure default values and required flags\n- Validation rules: Define numeric ranges and format requirements\n\nTest battery setup:\n- Create batteries: Define test batteries with multiple analyses\n- Set sequence: Order analyses within battery\n- Optional flags: Mark analyses as optional in battery\n- Usage tracking: Monitor which batteries are used most frequently\n\nList management:\n- Create lists: Define new list types (status, sample_type, etc.)\n- Add values: Populate lists with allowed values\n- Edit values: Modify existing list entries\n- Deactivate: Remove values without deleting (preserve historical data)\n\nRequires permission: config:edit	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
5a4331c7-9580-4ba6-b562-344c043ebc3c	Data Management	Oversee data operations and system maintenance:\n\nData oversight:\n1. View all data: As administrator, access all samples, tests, results, and projects regardless of RLS restrictions.\n2. Audit trails: Review created_at, modified_at, created_by, and modified	Data Management	Oversee data operations and system maintenance:\n\nData oversight:\n1. View all data: As administrator, access all samples, tests, results, and projects regardless of RLS restrictions.\n2. Audit trails: Review created_at, modified_at, created_by, and modified_by fields for all entities.\n3. Data integrity: Monitor referential integrity and foreign key relationships.\n4. Bulk operations: Perform bulk updates and data migrations as needed.\n\nProject management:\n- Create projects: Set up new projects with client associations\n- Assign users: Add users to projects with appropriate access\n- Monitor progress: Track sample accessioning and testing progress\n- Update status: Modify project status and metadata\n\nBatch oversight:\n- View all batches: Access batches across all projects\n- Monitor status: Track batch progression and completion\n- Review results: Access all results for quality assurance\n- Resolve issues: Address batch-related problems and errors\n\nUser activity:\n- Monitor logins: Review last_login timestamps\n- Track changes: View audit trails for user actions\n- Identify issues: Detect unusual patterns or errors\n- Support users: Assist with access and permission issues\n\nSystem maintenance:\n- Database migrations: Run Alembic migrations for schema updates\n- Backup operations: Coordinate database backups and restores\n- Performance monitoring: Review query performance and indexes\n- Log analysis: Review application logs for errors and warnings\n\nRequires permission: All permissions (administrator role)	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
10c06480-5bd0-43e9-a402-3544536c1aed	Getting Started	Welcome to NimbleLIMS! As an Administrator, you manage the entire system:\n\nKey responsibilities:\n- User and role management: Create users, assign roles, configure permissions\n- System configuration: Set up container types, analyses, test batteries, lists\n	Getting Started	Welcome to NimbleLIMS! As an Administrator, you manage the entire system:\n\nKey responsibilities:\n- User and role management: Create users, assign roles, configure permissions\n- System configuration: Set up container types, analyses, test batteries, lists\n- EAV configuration: Define custom attributes for flexible data modeling\n- RLS oversight: Ensure proper data isolation and security policies\n- Data management: Oversee all projects, samples, tests, and results\n- System maintenance: Perform migrations, backups, and monitoring\n\nStart by accessing the Admin Dashboard for system overview. Use the navigation menu to access different administration sections:\n- Users Management: Create and manage users and roles\n- Custom Attributes: Configure EAV custom attributes\n- System Configuration: Manage analyses, batteries, containers, lists\n- Data Views: Access all data across projects and clients\n\nPermissions:\nAs Administrator, you have all permissions (17 total):\n- Sample operations: sample:create, sample:read, sample:update, sample:delete\n- Test operations: test:assign, test:update\n- Result operations: result:enter, result:review, result:read, result:update, result:delete\n- Batch operations: batch:manage, batch:read, batch:update, batch:delete\n- Project operations: project:manage, project:read\n- System operations: user:manage, role:manage, config:edit\n\nFor detailed instructions, see the specific help sections for each area. Contact system support if you need assistance with advanced configurations.	administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: list_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.list_entries (id, name, description, active, created_at, created_by, modified_at, modified_by, list_id) FROM stdin;
4eda49ab-8b3b-4435-957a-7279119c809e	Received	Sample received	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	11111111-1111-1111-1111-111111111111
0d94042f-9efc-491e-aa5f-a44e3d2a0a67	Available for Testing	Ready for testing	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	11111111-1111-1111-1111-111111111111
c10d479a-d475-44ab-841c-4caeedc64253	Testing Complete	Testing finished	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	11111111-1111-1111-1111-111111111111
a0328c79-1882-419f-a939-70ee1ddb0f73	Reviewed	Results reviewed	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	11111111-1111-1111-1111-111111111111
5c174bc7-7f8f-4b8d-9d67-e2d58916604a	Reported	Results reported	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	11111111-1111-1111-1111-111111111111
836c5c46-e5b9-4881-a3b9-2b107d43ccb4	In Process	Test in progress	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	22222222-2222-2222-2222-222222222222
91014ae4-b0fd-4486-81c1-02cfbcee86dd	In Analysis	Under analysis	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	22222222-2222-2222-2222-222222222222
38dc8c12-79b0-4191-9584-19abd774bdae	Complete	Test completed	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	22222222-2222-2222-2222-222222222222
0e16140b-3f31-488c-9f3f-966a2ee78382	Active	Project active	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	33333333-3333-3333-3333-333333333333
eab66e74-8da4-456b-a244-ef5ad92ff4ab	Completed	Project completed	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	33333333-3333-3333-3333-333333333333
5a793d81-42a3-40a2-a800-681199e7fb06	On Hold	Project on hold	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	33333333-3333-3333-3333-333333333333
886f0559-e2de-4f9e-90f2-ccc1fcea1748	Created	Batch created	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	44444444-4444-4444-4444-444444444444
402b622d-2ba8-4c7b-8a14-df9a80fe77e9	In Process	Batch in process	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	44444444-4444-4444-4444-444444444444
881bf26c-7668-48a1-99b9-b15d23a27f11	Completed	Batch completed	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	44444444-4444-4444-4444-444444444444
279e0fbd-ca4e-4d43-9e21-462f312b4d57	Blood	Blood sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	55555555-5555-5555-5555-555555555555
32d06392-b5a9-4fd2-a54e-09f797896d1f	Urine	Urine sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	55555555-5555-5555-5555-555555555555
1f76994d-7ced-43c9-986c-290dfd824bde	Tissue	Tissue sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	55555555-5555-5555-5555-555555555555
adf86f5a-148d-4710-b30c-67a9987adae7	Water	Water sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	55555555-5555-5555-5555-555555555555
6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	Sample	Regular sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
73f89734-bab0-42c0-9ae1-cbcf56a2bff0	Positive Control	Positive control	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
9a0a49cb-56c5-49cb-ba15-96acf980fad6	Negative Control	Negative control	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
37b33b90-e32e-4471-8403-aa8fd8dcebcf	Matrix Spike	Matrix spike	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
e62de745-b3a0-4fc9-b225-212ac46cd9d3	Duplicate	Duplicate sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
2cf410d6-cc26-4aa7-912b-3259732045c4	Blank	Blank sample	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	77777777-7777-7777-7777-777777777777
df6e04f5-0374-46e3-b48e-7a824b4e01f1	concentration	Concentration units	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	88888888-8888-8888-8888-888888888888
fb1611a7-f709-4ae2-b180-dce1bbc20757	mass	Mass units	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	88888888-8888-8888-8888-888888888888
64acadff-c12d-40e4-a66f-1beb215fe73c	volume	Volume units	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	88888888-8888-8888-8888-888888888888
e2377cea-03ef-4d5e-9aeb-9dd6dfe7fb45	molar	Molar units	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	88888888-8888-8888-8888-888888888888
3780532b-014b-4659-9676-d9f5a30e1396	Email	Email address	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	99999999-9999-9999-9999-999999999999
fcc5eea4-c700-4377-b061-e62829886c35	Phone	Phone number	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	99999999-9999-9999-9999-999999999999
bdb50f61-d854-40da-ab60-b820e3460412	Mobile	Mobile phone	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	99999999-9999-9999-9999-999999999999
b5f7f9f3-2c93-4f30-b433-35dc6dfd3c80	Sludge	Sludge	t	2026-01-07 04:47:11.200146	\N	2026-01-07 18:12:05.453141	00000000-0000-0000-0000-000000000001	66666666-6666-6666-6666-666666666666
e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	Ground Water	Ground Water	t	2026-01-07 04:47:11.200146	\N	2026-01-07 18:12:24.8338	00000000-0000-0000-0000-000000000001	66666666-6666-6666-6666-666666666666
a8e36c38-5448-4086-a2db-51cb3db1ffa0	Soil	Soil	t	2026-01-07 04:47:11.200146	\N	2026-01-07 18:12:46.980386	00000000-0000-0000-0000-000000000001	66666666-6666-6666-6666-666666666666
ab295397-7c75-4938-ab11-a850d6c8c02b	Air	Air	t	2026-01-07 18:12:58.650468	00000000-0000-0000-0000-000000000001	2026-01-07 18:12:58.650468	00000000-0000-0000-0000-000000000001	66666666-6666-6666-6666-666666666666
2f43a32d-b7d2-4cfa-b904-0f9af451b3db	Drinking Water	Drinking Water	t	2026-01-07 18:13:22.929973	00000000-0000-0000-0000-000000000001	2026-01-07 18:13:22.929973	00000000-0000-0000-0000-000000000001	66666666-6666-6666-6666-666666666666
dcdbb848-94ab-4da1-9f61-3a560324a7e3	On Hold	Sample is on hold pending additional information	t	2026-01-07 18:03:37.130839	00000000-0000-0000-0000-000000000001	2026-01-08 00:32:41.23008	00000000-0000-0000-0000-000000000001	11111111-1111-1111-1111-111111111111
\.


--
-- Data for Name: lists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lists (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
11111111-1111-1111-1111-111111111111	sample_status	Sample status values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
22222222-2222-2222-2222-222222222222	test_status	Test status values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
33333333-3333-3333-3333-333333333333	project_status	Project status values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
44444444-4444-4444-4444-444444444444	batch_status	Batch status values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
55555555-5555-5555-5555-555555555555	sample_types	Sample type values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
66666666-6666-6666-6666-666666666666	matrix_types	Matrix type values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
77777777-7777-7777-7777-777777777777	qc_types	QC type values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
88888888-8888-8888-8888-888888888888	unit_types	Unit type values	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
99999999-9999-9999-9999-999999999999	contact_types	Contact method types	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locations (id, name, description, active, created_at, created_by, modified_at, modified_by, client_id, address_line1, address_line2, city, state, postal_code, country, latitude, longitude, type) FROM stdin;
\.


--
-- Data for Name: name_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.name_templates (id, entity_type, template, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1	sample	SAMPLE-{YYYY}-{SEQ}	Default sample naming template: SAMPLE-YYYY-SEQ (e.g., SAMPLE-2024-001)	t	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2	project	PROJ-{CLIENT}-{YYYYMMDD}-{SEQ}	Default project naming template: PROJ-CLIENT-YYYYMMDD-SEQ (e.g., PROJ-ACME-20240108-001)	t	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3	batch	BATCH-{YYYYMMDD}-{SEQ}	Default batch naming template: BATCH-YYYYMMDD-SEQ (e.g., BATCH-20240108-001)	t	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4	analysis	ANALYSIS-{SEQ}	Default analysis naming template: ANALYSIS-SEQ (e.g., ANALYSIS-001)	t	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5	container	CONT-{YYYYMMDD}-{SEQ}	Default container naming template: CONT-YYYYMMDD-SEQ (e.g., CONT-20240108-001)	t	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001	2026-01-07 22:59:14.765812	00000000-0000-0000-0000-000000000001
\.


--
-- Data for Name: people; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people (id, name, description, active, created_at, created_by, modified_at, modified_by, first_name, last_name, title, role) FROM stdin;
\.


--
-- Data for Name: people_locations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people_locations (person_id, location_id, "primary", notes) FROM stdin;
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permissions (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee	user:manage	Manage users	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
ffffffff-ffff-ffff-ffff-ffffffffffff	role:manage	Manage roles	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0	config:edit	Edit configuration	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0	project:manage	Manage projects	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0	sample:create	Create samples	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0	sample:read	Read samples	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0	sample:update	Update samples	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0	test:assign	Assign tests	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1	test:update	Update tests	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1	result:enter	Enter results	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1	result:review	Review results	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1	batch:manage	Manage batches	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1	batch:read	Read batches	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
362df237-cdea-4a34-8212-0243e2f354d0	result:update	Update results	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
3c39d00f-b48c-4158-ad55-94655137fcc3	result:delete	Delete results	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
ceb18667-2264-4d04-8d25-2114032eedff	batch:update	Update batches	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
9edc84fa-3a1d-432e-a420-8d8c4b3e85e9	batch:delete	Delete batches	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: project_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_users (project_id, user_id, access_level, granted_at, granted_by) FROM stdin;
7f88b81b-1bf6-4cf8-9ed2-837e1a544d46	00000000-0000-0000-0000-000000000003	\N	2026-01-08 02:04:14.786614	\N
5c33fcc9-11e8-4d9f-bc4a-eed115b80b0e	00000000-0000-0000-0000-000000000003	\N	2026-01-08 02:09:59.369283	\N
898a34e4-64e8-4afa-9d5c-f73c25147e72	00000000-0000-0000-0000-000000000003	\N	2026-01-08 02:26:44.910496	\N
9924ab80-a7ad-4466-a6bf-2fbad8297109	00000000-0000-0000-0000-000000000003	\N	2026-01-08 12:30:22.892709	\N
650170f2-ee3e-4fda-9b89-b02dfedf3a84	00000000-0000-0000-0000-000000000003	\N	2026-01-08 13:47:11.443355	\N
e318bf03-358b-45d7-a712-5e5debefd3ec	00000000-0000-0000-0000-000000000003	\N	2026-01-08 13:47:44.734999	\N
48a9dcd3-7ef3-4a08-9469-150e03b92be3	00000000-0000-0000-0000-000000000003	\N	2026-01-08 14:06:12.824138	\N
7a8d6b5e-097a-4ab2-b12c-18973f68250d	00000000-0000-0000-0000-000000000003	\N	2026-01-08 20:11:10.160515	\N
a4ab490c-704e-4c97-9f02-9a4b110193dd	00000000-0000-0000-0000-000000000003	\N	2026-01-09 19:02:12.00376	\N
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.projects (id, name, description, active, created_at, created_by, modified_at, modified_by, start_date, client_id, status, client_project_id, custom_attributes) FROM stdin;
7f88b81b-1bf6-4cf8-9ed2-837e1a544d46	PROJ-UATTESTCLI-20260108-001	\N	t	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
5c33fcc9-11e8-4d9f-bc4a-eed115b80b0e	PROJ-UATTESTCLI-20260108-002	\N	t	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
898a34e4-64e8-4afa-9d5c-f73c25147e72	PROJ-UATTESTCLI-20260108-003	\N	t	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
9924ab80-a7ad-4466-a6bf-2fbad8297109	PROJ-UATTESTCLI-20260108-004	\N	t	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
650170f2-ee3e-4fda-9b89-b02dfedf3a84	PROJ-UATTESTCLI-20260108-005	\N	t	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
e318bf03-358b-45d7-a712-5e5debefd3ec	PROJ-UATTESTCLI-20260108-006	\N	t	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	\N	{}
48a9dcd3-7ef3-4a08-9469-150e03b92be3	PROJ-UATTESTCLI-20260108-007	\N	t	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
7a8d6b5e-097a-4ab2-b12c-18973f68250d	PROJ-UATTESTCLI-20260108-008	\N	t	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-08 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
a4ab490c-704e-4c97-9f02-9a4b110193dd	PROJ-UATTESTCLI-20260109-009	\N	t	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-09 00:00:00	11111111-1111-1111-1111-111111111111	0e16140b-3f31-488c-9f3f-966a2ee78382	22222222-2222-2222-2222-222222222222	{}
\.


--
-- Data for Name: results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.results (id, name, description, active, created_at, created_by, modified_at, modified_by, test_id, analyte_id, raw_result, reported_result, qualifiers, calculated_result, entry_date, entered_by, custom_attributes) FROM stdin;
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role_permissions (role_id, permission_id) FROM stdin;
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	ffffffff-ffff-ffff-ffff-ffffffffffff
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1
cccccccc-cccc-cccc-cccc-cccccccccccc	c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0
cccccccc-cccc-cccc-cccc-cccccccccccc	d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0
cccccccc-cccc-cccc-cccc-cccccccccccc	e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0
cccccccc-cccc-cccc-cccc-cccccccccccc	f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0
cccccccc-cccc-cccc-cccc-cccccccccccc	a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1
cccccccc-cccc-cccc-cccc-cccccccccccc	b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1
cccccccc-cccc-cccc-cccc-cccccccccccc	d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1
dddddddd-dddd-dddd-dddd-dddddddddddd	d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0
cccccccc-cccc-cccc-cccc-cccccccccccc	e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1
dddddddd-dddd-dddd-dddd-dddddddddddd	f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0
dddddddd-dddd-dddd-dddd-dddddddddddd	c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1
dddddddd-dddd-dddd-dddd-dddddddddddd	b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0
dddddddd-dddd-dddd-dddd-dddddddddddd	e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.roles (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	Administrator	System administrator	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	Lab Manager	Laboratory manager	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
cccccccc-cccc-cccc-cccc-cccccccccccc	Lab Technician	Laboratory technician	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
dddddddd-dddd-dddd-dddd-dddddddddddd	Client	Client user	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: samples; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.samples (id, name, description, active, created_at, created_by, modified_at, modified_by, due_date, received_date, report_date, sample_type, status, matrix, temperature, parent_sample_id, project_id, qc_type, client_sample_id, custom_attributes) FROM stdin;
c13ce838-f3be-43b6-b2e4-ca4cdaef75c1	SAMPLE-2026-001	a test	t	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	2f43a32d-b7d2-4cfa-b904-0f9af451b3db	4.00	\N	7f88b81b-1bf6-4cf8-9ed2-837e1a544d46	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 7, "Report_Date": "2026-01-28", "Sample_Color": "clear"}
44136325-2b0b-4beb-8ae1-25a0d0bb7aee	SAMPLE-2026-002	a test	t	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-31 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	4.00	\N	5c33fcc9-11e8-4d9f-bc4a-eed115b80b0e	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 7, "Report_Date": "2026-01-29", "Sample_Color": "clear"}
4fc7fa84-9ff0-4a95-a9f4-d19763c7c15b	SAMPLE-2026-003	a test	t	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-31 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	4.00	\N	898a34e4-64e8-4afa-9d5c-f73c25147e72	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 7, "Report_Date": "2026-01-08", "Sample_Color": "clear"}
f522c2ff-4fdb-4787-b4ca-df26ea54136e	SAMPLE-2026-004	a test	t	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	2f43a32d-b7d2-4cfa-b904-0f9af451b3db	0.00	\N	9924ab80-a7ad-4466-a6bf-2fbad8297109	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 7, "Report_Date": "2026-01-29", "Sample_Color": "clear"}
b74b8b74-d992-4a1a-8edf-2636f26af415	SAMPLE-2026-005	a test	t	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	32d06392-b5a9-4fd2-a54e-09f797896d1f	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	-1.00	\N	650170f2-ee3e-4fda-9b89-b02dfedf3a84	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 4, "Report_Date": "2026-01-28", "Sample_Color": "green"}
787a114e-63f5-47fa-b335-be05ad9eb84a	SAMPLE-2026-006	a test	t	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	32d06392-b5a9-4fd2-a54e-09f797896d1f	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	-1.00	\N	e318bf03-358b-45d7-a712-5e5debefd3ec	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 4, "Report_Date": "2026-01-28", "Sample_Color": "green"}
0d6a1ad2-fcc4-46fe-9147-8dfdc212969c	SAMPLE-2026-007	a test	t	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	4.00	\N	48a9dcd3-7ef3-4a08-9469-150e03b92be3	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 5, "Report_Date": "2026-01-27", "Sample_Color": "clear"}
c0080188-50c6-4453-81bd-0b8f718064b6	SAMPLE-2026-008	a test	t	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-30 00:00:00	2026-01-08 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	2f43a32d-b7d2-4cfa-b904-0f9af451b3db	4.00	\N	7a8d6b5e-097a-4ab2-b12c-18973f68250d	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 8, "Report_Date": "2026-01-27", "Sample_Color": "green"}
60b4451f-2b44-459c-9eee-ec9e2a46cb02	SAMPLE-2026-009	a test	t	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-31 00:00:00	2026-01-09 00:00:00	\N	adf86f5a-148d-4710-b30c-67a9987adae7	4eda49ab-8b3b-4435-957a-7279119c809e	e0d7ec32-d7ff-4d5c-b32d-1166d3e5ce36	3.00	\N	a4ab490c-704e-4c97-9f02-9a4b110193dd	6566cedb-1e4c-49f1-aedb-7ba5bc0ce3db	\N	{"pH": 5, "Report_Date": "2026-01-16", "Sample_Color": "purple"}
\.


--
-- Data for Name: test_batteries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.test_batteries (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
c0000001-c000-c000-c000-c00000000001	EPA 8080 Full	Complete EPA Method 8080 test battery for Organochlorine Pesticides and PCBs	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N
\.


--
-- Data for Name: tests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tests (id, name, description, active, created_at, created_by, modified_at, modified_by, sample_id, analysis_id, status, review_date, test_date, technician_id, custom_attributes) FROM stdin;
273975c9-d8f0-4878-960c-e16e5a900093	SAMPLE-2026-001_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	c13ce838-f3be-43b6-b2e4-ca4cdaef75c1	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
a5755971-1905-40d1-a418-9471c84e835a	SAMPLE-2026-001_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	2026-01-08 02:04:14.786614	00000000-0000-0000-0000-000000000003	c13ce838-f3be-43b6-b2e4-ca4cdaef75c1	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
37bfaf0c-42c7-490d-841f-34f52c81b2e7	SAMPLE-2026-002_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	44136325-2b0b-4beb-8ae1-25a0d0bb7aee	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
4b79c6c0-56df-4ae6-8320-cf0433c22f27	SAMPLE-2026-002_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	2026-01-08 02:09:59.369283	00000000-0000-0000-0000-000000000003	44136325-2b0b-4beb-8ae1-25a0d0bb7aee	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
ec971518-8eb6-4176-b1ba-d6789051e4be	SAMPLE-2026-003_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	4fc7fa84-9ff0-4a95-a9f4-d19763c7c15b	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
d008fa1a-8a41-4cc7-85d5-7fa28c02c0cb	SAMPLE-2026-003_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	2026-01-08 02:26:44.910496	00000000-0000-0000-0000-000000000003	4fc7fa84-9ff0-4a95-a9f4-d19763c7c15b	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
db9dbbfc-6cab-40b6-95ea-2de4e9a20222	SAMPLE-2026-004_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	f522c2ff-4fdb-4787-b4ca-df26ea54136e	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
405b85fa-962f-4ef2-b7fc-cb285450b172	SAMPLE-2026-004_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	2026-01-08 12:30:22.892709	00000000-0000-0000-0000-000000000003	f522c2ff-4fdb-4787-b4ca-df26ea54136e	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
0d8964b6-380b-465f-b96f-c918f213ac59	SAMPLE-2026-005_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	b74b8b74-d992-4a1a-8edf-2636f26af415	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
26d8553d-e957-4649-aa7b-520a0365c6c9	SAMPLE-2026-005_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:11.443355	00000000-0000-0000-0000-000000000003	b74b8b74-d992-4a1a-8edf-2636f26af415	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
b9a36d5f-6a94-42ca-974a-14244069a1f6	SAMPLE-2026-006_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	787a114e-63f5-47fa-b335-be05ad9eb84a	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
b2139e1f-5ab7-492b-a65e-c96bcd0166b9	SAMPLE-2026-006_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	2026-01-08 13:47:44.734999	00000000-0000-0000-0000-000000000003	787a114e-63f5-47fa-b335-be05ad9eb84a	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
46391361-ab28-44f5-b6c2-bd3f1fb0ba5e	SAMPLE-2026-007_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	0d6a1ad2-fcc4-46fe-9147-8dfdc212969c	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
0345702d-0d41-4e73-b2b7-5f4ba74dc981	SAMPLE-2026-007_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	2026-01-08 14:06:12.824138	00000000-0000-0000-0000-000000000003	0d6a1ad2-fcc4-46fe-9147-8dfdc212969c	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
76e8d20a-5397-4f55-98b0-20c3b2028680	SAMPLE-2026-008_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	c0080188-50c6-4453-81bd-0b8f718064b6	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
117f09d7-fc37-4b3f-983c-1cfe7a655eb2	SAMPLE-2026-008_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	2026-01-08 20:11:10.160515	00000000-0000-0000-0000-000000000003	c0080188-50c6-4453-81bd-0b8f718064b6	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
3b0ee22b-f75a-4d33-b493-1ce28d1e2be7	SAMPLE-2026-009_test_b0000002-b000-b000-b000-b00000000004	\N	t	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	60b4451f-2b44-459c-9eee-ec9e2a46cb02	b0000002-b000-b000-b000-b00000000004	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
27cd2547-62eb-4a67-ab47-ae2901c74a5b	SAMPLE-2026-009_test_b0000002-b000-b000-b000-b00000000002	\N	t	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	2026-01-09 19:02:12.00376	00000000-0000-0000-0000-000000000003	60b4451f-2b44-459c-9eee-ec9e2a46cb02	b0000002-b000-b000-b000-b00000000002	836c5c46-e5b9-4881-a3b9-2b107d43ccb4	\N	\N	00000000-0000-0000-0000-000000000003	{}
\.


--
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.units (id, name, description, active, created_at, created_by, modified_at, modified_by, multiplier, type) FROM stdin;
3f05af92-69d6-4f91-8a8d-5651af968a8f	g/L	Grams per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1.0000000000	df6e04f5-0374-46e3-b48e-7a824b4e01f1
5262acfe-3239-46f1-9287-8412d2be46fd	mg/L	Milligrams per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0010000000	df6e04f5-0374-46e3-b48e-7a824b4e01f1
3c85e73d-c682-4b7f-94b1-da3b991dbaa6	µg/L	Micrograms per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0000010000	df6e04f5-0374-46e3-b48e-7a824b4e01f1
ce66ac80-98e0-4990-9fbe-775ecc15cc83	g	Grams	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1.0000000000	fb1611a7-f709-4ae2-b180-dce1bbc20757
55ab1455-e3dc-4028-94cf-f6b03d4aab29	mg	Milligrams	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0010000000	fb1611a7-f709-4ae2-b180-dce1bbc20757
0668eecb-cb07-490b-ad21-bc9e62606649	µg	Micrograms	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0000010000	fb1611a7-f709-4ae2-b180-dce1bbc20757
60a287d6-55b7-4dd4-a276-5a5e51907bf8	L	Liters	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1.0000000000	64acadff-c12d-40e4-a66f-1beb215fe73c
e3a763c5-3b45-4a35-bc36-9b9716dd13fe	mL	Milliliters	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0010000000	64acadff-c12d-40e4-a66f-1beb215fe73c
1232c9b4-cd05-441b-aad6-7737ba276f27	µL	Microliters	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0000010000	64acadff-c12d-40e4-a66f-1beb215fe73c
1dff71d1-6b36-48b6-a754-0c2c7543b257	mol/L	Moles per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1.0000000000	e2377cea-03ef-4d5e-9aeb-9dd6dfe7fb45
c0ea753c-1065-402f-b0f9-0822e20e5100	mmol/L	Millimoles per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0010000000	e2377cea-03ef-4d5e-9aeb-9dd6dfe7fb45
66876d28-c7dd-4d9a-9593-5d080c516652	ng/L	Nanograms per liter	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0000000010	df6e04f5-0374-46e3-b48e-7a824b4e01f1
178b27fe-fa1a-43b1-9b12-67d536264da4	ppb	Parts per billion	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0010000000	df6e04f5-0374-46e3-b48e-7a824b4e01f1
9963ac35-42a6-4e3b-80ca-6e68001c5576	ppm	Parts per million	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1.0000000000	df6e04f5-0374-46e3-b48e-7a824b4e01f1
906fe307-860f-4315-b393-e654f4896ab3	kg	Kilograms	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	1000.0000000000	fb1611a7-f709-4ae2-b180-dce1bbc20757
600927c7-6502-493b-a219-d2cae65f5bf2	ng	Nanograms	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	0.0000000010	fb1611a7-f709-4ae2-b180-dce1bbc20757
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, name, description, active, created_at, created_by, modified_at, modified_by, username, password_hash, email, role_id, client_id, last_login) FROM stdin;
fb1b4245-52a1-425c-ae78-f732d1be04a1	Client User	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-07 04:47:11.200146	\N	client	186474c1f2c2f735a54c2cf82ee8e87f2a5cd30940e280029363fecedfc5328c	client@example.com	dddddddd-dddd-dddd-dddd-dddddddddddd	00000000-0000-0000-0000-000000000001	\N
00000000-0000-0000-0000-000000000001	System Administrator	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-10 15:55:07.235107	\N	admin	240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9	admin@lims.local	aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	00000000-0000-0000-0000-000000000001	2026-01-10 15:55:07.235107
00000000-0000-0000-0000-000000000003	Lab Technician	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-10 19:23:32.308377	\N	lab-tech	d81968c60a8a41bdafcb3c5825bf8bc4a76dccc932d673e3f9a7b71ce4538596	lab-tech@lims.local	cccccccc-cccc-cccc-cccc-cccccccccccc	00000000-0000-0000-0000-000000000001	2026-01-10 19:23:32.308377
00000000-0000-0000-0000-000000000002	Lab Manager	\N	t	2026-01-07 04:47:11.200146	\N	2026-01-10 19:23:43.392201	\N	lab-manager	7dd63afe29407aa45af7fdd4388b71195b552688c2750abd42bdf3b231c13b69	lab-manager@lims.local	bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	00000000-0000-0000-0000-000000000001	2026-01-10 19:23:43.392201
\.


--
-- Name: name_template_seq_analysis; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.name_template_seq_analysis', 1, false);


--
-- Name: name_template_seq_batch; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.name_template_seq_batch', 1, false);


--
-- Name: name_template_seq_container; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.name_template_seq_container', 1, false);


--
-- Name: name_template_seq_project; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.name_template_seq_project', 9, true);


--
-- Name: name_template_seq_sample; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.name_template_seq_sample', 9, true);


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
-- Name: idx_analyses_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_analyses_name_unique ON public.analyses USING btree (name);


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

\unrestrict Z4TPlRAC00dvzwOQSSp9rU5VOUB37LIsnFUFkRvWiwrtWXwhvgnRLgNOlXFWDoM

