--
-- PostgreSQL database dump
--

\restrict aTew83o9pglCOGWtsjY25pr2RcGhKEevDXocaaSc4YbVr2lo0ggpkjuaCQHDpk0

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
0019
\.


--
-- Data for Name: analyses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analyses (id, name, description, active, created_at, created_by, modified_at, modified_by, method, turnaround_time, cost) FROM stdin;
b0000001-b000-b000-b000-b00000000001	pH Measurement	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	Electrometric	1	10.00
b0000002-b000-b000-b000-b00000000002	EPA Method 8080	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	GC/ECD for Organochlorine Pesticides and PCBs	7	150.00
b0000003-b000-b000-b000-b00000000003	Total Coliform Enumeration	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	Colilert or Membrane Filtration	2	50.00
b0000002-b000-b000-b000-b00000000004	EPA Method 8080 Prep	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	Sample Extractionfor Organochlorine Pesticides and PCBs	7	25.00
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
a0000001-a000-a000-a000-a00000000001	pH	pH value	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000002-a000-a000-a000-a00000000002	Aldrin	Organochlorine pesticide	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000003-a000-a000-a000-a00000000003	DDT	Organochlorine pesticide	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000004-a000-a000-a000-a00000000004	PCB-1016	Polychlorinated biphenyl	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000005-a000-a000-a000-a00000000005	Total Coliforms	Coliform bacteria count	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000006-a000-a000-a000-a00000000006	E. coli	Escherichia coli count	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0000004-a000-a000-a000-a00000000005	Initial Volume	Sample volume extracted	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
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
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clients (id, name, description, active, created_at, created_by, modified_at, modified_by, billing_info) FROM stdin;
00000000-0000-0000-0000-000000000001	System	System client for admin users	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	{}
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
\.


--
-- Data for Name: containers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.containers (id, name, description, active, created_at, created_by, modified_at, modified_by, "row", "column", concentration, concentration_units, amount, amount_units, type_id, parent_container_id) FROM stdin;
\.


--
-- Data for Name: contents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contents (container_id, sample_id, concentration, concentration_units, amount, amount_units) FROM stdin;
\.


--
-- Data for Name: custom_attributes_config; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.custom_attributes_config (id, entity_type, attr_name, data_type, validation_rules, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
\.


--
-- Data for Name: help_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.help_entries (id, name, description, section, content, role_filter, active, created_at, created_by, modified_at, modified_by) FROM stdin;
ed0e6148-4037-42ac-a47d-c1ce6b886d8f	Viewing Projects	Step-by-step guide to access your samples and results. Navigate to the Projects section to view all projects associated with your client account. Click on a project to see detailed information including samples, tests, and results.	Viewing Projects	Step-by-step guide to access your samples and results. Navigate to the Projects section to view all projects associated with your client account. Click on a project to see detailed information including samples, tests, and results.	Client	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
2ad05118-3559-47f8-a3e4-9b55546b4edb	Viewing Samples	Learn how to view and filter your samples. In the Samples section, you can see all samples associated with your projects. Use the filters to search by sample name, status, or date range. Click on a sample to view detailed information including test assign	Viewing Samples	Learn how to view and filter your samples. In the Samples section, you can see all samples associated with your projects. Use the filters to search by sample name, status, or date range. Click on a sample to view detailed information including test assignments and results.	Client	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
2c74846a-90c0-426d-a146-179116291e12	Viewing Results	Understand how to access and interpret your test results. Results are organized by test and sample. Navigate to the Results section to view all completed tests. Each result shows the analyte name, value, units, and any qualifiers. Results are automaticall	Viewing Results	Understand how to access and interpret your test results. Results are organized by test and sample. Navigate to the Results section to view all completed tests. Each result shows the analyte name, value, units, and any qualifiers. Results are automatically updated as tests are completed.	Client	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
0f82ba44-ae80-4bf4-9084-ae3922fdb66a	Getting Started	Welcome to NimbleLIMS! This system allows you to view your laboratory samples, tests, and results. Start by exploring the Dashboard to see an overview of your projects and samples. Use the navigation menu to access different sections of the system.	Getting Started	Welcome to NimbleLIMS! This system allows you to view your laboratory samples, tests, and results. Start by exploring the Dashboard to see an overview of your projects and samples. Use the navigation menu to access different sections of the system.	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
d415281d-9b7c-4d00-a460-c412e7a19f19	Accessioning Workflow	Step-by-step guide to sample accessioning:\n\n1. Enter sample details: name (unique), description, due date, received date, sample type, matrix, storage temperature, and project.\n2. Assign container: Select container type from admin-preconfigured types, ent	Accessioning Workflow	Step-by-step guide to sample accessioning:\n\n1. Enter sample details: name (unique), description, due date, received date, sample type, matrix, storage temperature, and project.\n2. Assign container: Select container type from admin-preconfigured types, enter container name/barcode (unique), set position for plate-based containers.\n3. Assign tests: Choose individual analyses or test battery. System automatically creates tests for all analyses in battery.\n4. Review and submit: Validate all information before submission.\n\nBulk tip (US-24): Enable bulk mode for multiple samples. Enter common fields once, then unique fields per sample in table format. Auto-naming available with prefix and start number.\n\nRequires permission: sample:create	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
2836c042-0629-4296-aebe-80b2f0ae283d	Batch Creation	Create batches to group samples for testing:\n\n1. Select containers: Choose containers from available samples. All samples in selected containers must share compatible analyses.\n2. Set batch details: Enter batch type (optional), start date, and notes.\n3. V	Batch Creation	Create batches to group samples for testing:\n\n1. Select containers: Choose containers from available samples. All samples in selected containers must share compatible analyses.\n2. Set batch details: Enter batch type (optional), start date, and notes.\n3. Validate compatibility: System checks that all samples have compatible test assignments before batch creation.\n4. QC requirements: System may require QC samples based on batch type configuration. QC samples are created automatically in the same transaction.\n\nBatch status flow: Created → In Process → Completed. Batch end_date is set automatically when all tests are complete.\n\nRequires permission: batch:create	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
f6e384dc-92bc-42c2-9ce7-0bee6656a440	Results Entry	Enter test results for samples in a batch:\n\nSingle-test entry:\n1. Select batch and test from Results Management.\n2. System loads all analytes configured for the selected test.\n3. Enter results: For each sample, enter raw_result, reported_result, and quali	Results Entry	Enter test results for samples in a batch:\n\nSingle-test entry:\n1. Select batch and test from Results Management.\n2. System loads all analytes configured for the selected test.\n3. Enter results: For each sample, enter raw_result, reported_result, and qualifiers (if applicable).\n4. Save: System validates all results and creates result records.\n\nBatch results entry (US-28):\n1. Select batch from Results Management.\n2. Use tabular interface: Rows = samples, Columns = analytes.\n3. Enter results directly in table cells with real-time validation.\n4. Submit: All results saved atomically. Test status updates to "Complete" when all analytes entered. Batch status auto-updates to "Completed" when all tests are complete.\n\nValidation: Required fields, numeric ranges, significant figures. QC validation checks for missing results and out-of-range values.\n\nRequires permission: result:create	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
94e59332-8585-4501-a9cf-00a170b60ed0	Container Management	Manage sample containers:\n\nContainer types are pre-configured by administrators. During accessioning, select a container type and create the container instance.\n\nContainer details:\n- Name/barcode: Unique identifier (required)\n- Position: Row and column fo	Container Management	Manage sample containers:\n\nContainer types are pre-configured by administrators. During accessioning, select a container type and create the container instance.\n\nContainer details:\n- Name/barcode: Unique identifier (required)\n- Position: Row and column for plate-based containers\n- Concentration and amount: Optional with units\n- Parent container: Optional for hierarchical relationships\n\nContainers are created dynamically during sample accessioning. Samples are always received in a container, which must be specified during accessioning.\n\nRequires permission: container:create	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
3c904cac-7948-48a5-a606-459fc120586e	Test Assignment	Assign tests to samples during accessioning:\n\nOptions:\n1. Individual analyses: Select one or more analyses from available list. Each analysis creates a separate test instance with status "In Process".\n2. Test battery: Select a pre-configured test battery.	Test Assignment	Assign tests to samples during accessioning:\n\nOptions:\n1. Individual analyses: Select one or more analyses from available list. Each analysis creates a separate test instance with status "In Process".\n2. Test battery: Select a pre-configured test battery. System automatically creates tests for all analyses in battery, ordered by sequence.\n3. Combined: Assign both battery and individual analyses. System prevents duplicate test creation if analysis already exists from battery.\n\nTest status flow: In Process → In Analysis → Complete\n\nAfter assignment, tests are ready for results entry. Tests can be viewed and managed in the Tests section.\n\nRequires permission: test:create	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
710e9001-28c7-4a61-a14c-490f77f35706	Getting Started	Welcome to NimbleLIMS! As a Lab Technician, you can:\n\n- Accession samples: Receive and register new samples with test assignments\n- Create batches: Group samples for efficient testing workflows\n- Enter results: Record test results for samples in batches\n-	Getting Started	Welcome to NimbleLIMS! As a Lab Technician, you can:\n\n- Accession samples: Receive and register new samples with test assignments\n- Create batches: Group samples for efficient testing workflows\n- Enter results: Record test results for samples in batches\n- Manage containers: Track sample storage and location\n\nStart by accessing the Dashboard for an overview of your work. Use the navigation menu to access different sections. Each workflow requires specific permissions - contact your Lab Manager if you need additional access.\n\nFor detailed instructions, see the specific help sections for each workflow.	lab-technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
2993ef8c-4678-4ef6-b504-672570be9654	Results Review	Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.\n\nReview workflow:\n1. Access batch view: Navigate to Results Management and select a batch.\n2. Review test results: Check all analytes for each sample in the batch.\n3. V	Results Review	Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.\n\nReview workflow:\n1. Access batch view: Navigate to Results Management and select a batch.\n2. Review test results: Check all analytes for each sample in the batch.\n3. Validate QC: Ensure QC samples meet acceptance criteria. Flag out-of-range values and missing results.\n4. Approve results: Update test status to "Complete" after review. System records review_date automatically.\n5. Flag issues: Document any anomalies or concerns per US-12 requirements. Contact technicians for clarification if needed.\n\nQuality checks:\n- Verify all required analytes have results\n- Check numeric ranges and significant figures\n- Validate qualifiers are appropriate\n- Ensure batch status progression: Created → In Process → Completed\n\nRequires permission: result:review	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
d062bfe5-0489-4422-b0e0-5db9f427bc3c	Batch Management	Oversee batch operations and workflow:\n\nBatch oversight:\n1. Monitor batch status: Track batches from creation through completion. View all batches with filtering by status, type, and date range.\n2. Review batch composition: Check container assignments and	Batch Management	Oversee batch operations and workflow:\n\nBatch oversight:\n1. Monitor batch status: Track batches from creation through completion. View all batches with filtering by status, type, and date range.\n2. Review batch composition: Check container assignments and sample compatibility. Ensure all samples in a batch have compatible test assignments.\n3. Manage batch lifecycle: Update batch status as needed. Status flow: Created → In Process → Completed.\n4. Batch end_date: Automatically set when all tests are complete, but can be manually adjusted if needed.\n\nQC oversight:\n- Verify QC samples are included when required by batch type\n- Review QC results during results review process\n- Ensure compliance with quality standards\n\nBatch operations:\n- Add or remove containers from batches (before testing begins)\n- Update batch notes and metadata\n- View batch history and audit trail\n\nRequires permission: batch:manage	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
043099b4-09a9-4b26-a3ba-ec43110f77bf	Project Management	Manage projects and client relationships:\n\nProject oversight:\n1. View all projects: Access project list with filtering by client, status, and date range.\n2. Monitor project status: Track projects through lifecycle. Status values managed via lists configur	Project Management	Manage projects and client relationships:\n\nProject oversight:\n1. View all projects: Access project list with filtering by client, status, and date range.\n2. Monitor project status: Track projects through lifecycle. Status values managed via lists configuration.\n3. Review project samples: Access all samples associated with a project to monitor progress and completion.\n4. Client project coordination: Link projects to client projects for billing and reporting purposes.\n\nProject operations:\n- Update project status and metadata\n- Assign users to projects with appropriate access levels\n- Review project timeline and deadlines\n- Monitor sample accessioning and testing progress\n\nClient relationships:\n- Coordinate with clients on project requirements\n- Ensure proper data isolation per client\n- Review client project associations\n\nRequires permission: project:manage	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
c4ef602e-877a-4915-b6da-d311b09ee50a	Quality Control	Ensure quality standards and compliance:\n\nQC responsibilities:\n1. Review QC samples: Verify QC samples are created for batches when required by batch type configuration.\n2. Validate QC results: Check that QC results meet acceptance criteria. Flag out-of-r	Quality Control	Ensure quality standards and compliance:\n\nQC responsibilities:\n1. Review QC samples: Verify QC samples are created for batches when required by batch type configuration.\n2. Validate QC results: Check that QC results meet acceptance criteria. Flag out-of-range values and investigate anomalies.\n3. Monitor test accuracy: Review results for consistency and accuracy. Ensure proper use of qualifiers and units.\n4. Compliance checks: Verify adherence to US-12 requirements for issue flagging and documentation.\n\nQuality monitoring:\n- Track QC sample performance over time\n- Identify trends and potential issues\n- Ensure proper documentation of exceptions\n- Coordinate with technicians on quality concerns\n\nIssue management:\n- Flag results that require investigation\n- Document quality issues per US-12\n- Follow up on flagged items until resolution\n- Maintain audit trail of quality actions\n\nRequires permission: result:review	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
4fdb83ed-3807-4b3e-a531-a019fa82fa54	Test Assignment Oversight	Oversee test assignments and configurations:\n\nAssignment oversight:\n1. Review test assignments: Monitor which tests are assigned to samples during accessioning. Ensure appropriate analyses and batteries are used.\n2. Validate test configurations: Verify th	Test Assignment Oversight	Oversee test assignments and configurations:\n\nAssignment oversight:\n1. Review test assignments: Monitor which tests are assigned to samples during accessioning. Ensure appropriate analyses and batteries are used.\n2. Validate test configurations: Verify that test assignments align with project requirements and client specifications.\n3. Monitor test status: Track tests through workflow: In Process → In Analysis → Complete.\n4. Coordinate with technicians: Provide guidance on test assignment decisions and resolve assignment questions.\n\nTest battery management:\n- Review use of pre-configured test batteries\n- Ensure batteries are applied correctly to appropriate sample types\n- Verify battery sequences and optional flags are respected\n\nAnalysis oversight:\n- Monitor which analyses are most frequently used\n- Ensure proper analyte configurations for analyses\n- Coordinate with administrators on analysis configuration needs\n\nRequires permission: test:assign	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
6bd33581-7d52-4703-8ca8-8841432089f3	Getting Started	Welcome to NimbleLIMS! As a Lab Manager, you oversee laboratory operations:\n\nKey responsibilities:\n- Review and approve results: Ensure quality and accuracy of test results\n- Manage batches: Oversee batch workflows and monitor progress\n- Project managemen	Getting Started	Welcome to NimbleLIMS! As a Lab Manager, you oversee laboratory operations:\n\nKey responsibilities:\n- Review and approve results: Ensure quality and accuracy of test results\n- Manage batches: Oversee batch workflows and monitor progress\n- Project management: Coordinate projects and client relationships\n- Quality control: Maintain quality standards and compliance\n- Test oversight: Monitor test assignments and configurations\n\nStart by accessing the Dashboard for an overview of laboratory operations. Use the navigation menu to access different sections. Review pending results in Results Management, monitor active batches, and track project progress.\n\nFor detailed instructions, see the specific help sections for each workflow. Contact your Administrator if you need additional permissions or access.	lab-manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
f39aea14-472b-47d0-b7d0-0ecf68bd39b7	User Management	Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.\n\nUser operations:\n1. Create users: Navigate to Users Management. Enter username, email, name, and assign role. Set password or enable password reset.\n	User Management	Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.\n\nUser operations:\n1. Create users: Navigate to Users Management. Enter username, email, name, and assign role. Set password or enable password reset.\n2. Edit users: Update user details, change roles, modify permissions. Users can be activated or deactivated.\n3. Assign roles: Select appropriate role for each user. Roles determine default permissions and access levels.\n4. Client assignment: For Client role users, assign to specific client for data isolation.\n\nRole management:\n- Create custom roles: Define new roles with specific permission sets\n- Edit roles: Modify role permissions and descriptions\n- Permission assignment: Assign permissions to roles using role:manage permission\n- View role permissions: Review which permissions are assigned to each role\n\nPermissions:\n- user:manage: Required for user CRUD operations\n- role:manage: Required for role and permission management\n- config:edit: Required for system configuration changes\n\nBest practices:\n- Use strong passwords and enable password policies\n- Assign minimal required permissions (principle of least privilege)\n- Regularly review user access and deactivate unused accounts\n- Document role changes and permission modifications	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
4949f5aa-b71d-41e4-a10a-8bce5bae08ca	EAV Configuration	Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\nEAV overview:\nThe EAV model enables administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requiremen	EAV Configuration	Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\nEAV overview:\nThe EAV model enables administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requirements.\n\nCustom attributes configuration:\n1. Access EAV config: Navigate to Custom Attributes Management in admin UI.\n2. Create attribute: Define attribute name, entity type (sample, test, etc.), data type (text, number, date, boolean), and validation rules.\n3. Set visibility: Configure which roles can view and edit custom attributes.\n4. Define defaults: Set default values and required flags as needed.\n\nEntity types supported:\n- Samples: Custom fields for sample metadata\n- Tests: Additional test configuration attributes\n- Results: Extended result data fields\n- Projects: Project-specific custom attributes\n\nEAV editing:\n- Edit existing attributes: Modify data types, validation, and visibility\n- Deactivate attributes: Disable without deleting to preserve historical data\n- View attribute usage: See where custom attributes are used across entities\n- Export/import: Backup and restore custom attribute configurations\n\nData management:\n- Custom attribute values are stored in EAV tables\n- Values are queryable and filterable in admin UI\n- Historical values are preserved for audit purposes\n- Bulk updates supported for custom attribute values\n\nRequires permission: config:edit	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
edb6d123-6a46-4788-b99c-b2008791804c	Row Level Security (RLS)	Manage Row Level Security policies for data isolation:\n\nRLS overview:\nRow Level Security (RLS) ensures users can only access data they are authorized to view. Policies are enforced at the database level for comprehensive security.\n\nRLS policy management:\n	Row Level Security (RLS)	Manage Row Level Security policies for data isolation:\n\nRLS overview:\nRow Level Security (RLS) ensures users can only access data they are authorized to view. Policies are enforced at the database level for comprehensive security.\n\nRLS policy management:\n1. Review policies: Check existing RLS policies on tables (samples, results, projects, etc.). Policies are defined in database migrations.\n2. Policy structure: Policies use USING clauses to filter rows based on user role, project access, and client assignments.\n3. Admin bypass: Administrator role bypasses RLS restrictions to access all data for system administration.\n4. Client isolation: Client users see only data associated with their assigned client_id.\n\nData isolation:\n- Project-based: Users see samples/projects they are assigned to\n- Client-based: Client users see only their client's data\n- Role-based: Different roles have different access levels\n- Cross-project access: Lab Managers can access multiple projects\n\nPolicy configuration:\n- Policies are created via Alembic migrations\n- Use current_user_id() function to identify current user\n- Use is_admin() function to check administrator status\n- Policies apply to SELECT, INSERT, UPDATE, DELETE operations\n\nTesting RLS:\n- Verify policies work correctly for each role\n- Test data isolation between clients\n- Ensure administrators can access all data\n- Validate project-based access restrictions\n\nRequires permission: config:edit (for policy modifications)	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
b28c57d8-03c4-4cc0-8484-325bce3a963f	System Configuration	Manage system-wide configurations and settings:\n\nConfiguration areas:\n1. Container types: Define container types available for sample storage. Configure dimensions, capacity, and position support (for plates).\n2. Analyses: Create and configure analyses wi	System Configuration	Manage system-wide configurations and settings:\n\nConfiguration areas:\n1. Container types: Define container types available for sample storage. Configure dimensions, capacity, and position support (for plates).\n2. Analyses: Create and configure analyses with associated analytes. Set units, significant figures, and validation rules.\n3. Test batteries: Define test batteries with ordered analyses. Configure optional flags and sequences.\n4. Lists: Manage list values for status fields, sample types, matrices, and other enumerated fields.\n5. Units: Configure measurement units and conversion factors.\n\nContainer type management:\n- Create container types: Define new container types with specifications\n- Edit types: Modify container properties and requirements\n- Position support: Enable row/column positions for plate-based containers\n- Capacity settings: Configure maximum samples per container\n\nAnalysis configuration:\n- Create analyses: Define new analyses with name and description\n- Configure analytes: Add analytes to analyses with units and validation\n- Set defaults: Configure default values and required flags\n- Validation rules: Define numeric ranges and format requirements\n\nTest battery setup:\n- Create batteries: Define test batteries with multiple analyses\n- Set sequence: Order analyses within battery\n- Optional flags: Mark analyses as optional in battery\n- Usage tracking: Monitor which batteries are used most frequently\n\nList management:\n- Create lists: Define new list types (status, sample_type, etc.)\n- Add values: Populate lists with allowed values\n- Edit values: Modify existing list entries\n- Deactivate: Remove values without deleting (preserve historical data)\n\nRequires permission: config:edit	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
6d011808-cfe7-4bb0-b0ba-d8d95bd1df7b	Data Management	Oversee data operations and system maintenance:\n\nData oversight:\n1. View all data: As administrator, access all samples, tests, results, and projects regardless of RLS restrictions.\n2. Audit trails: Review created_at, modified_at, created_by, and modified	Data Management	Oversee data operations and system maintenance:\n\nData oversight:\n1. View all data: As administrator, access all samples, tests, results, and projects regardless of RLS restrictions.\n2. Audit trails: Review created_at, modified_at, created_by, and modified_by fields for all entities.\n3. Data integrity: Monitor referential integrity and foreign key relationships.\n4. Bulk operations: Perform bulk updates and data migrations as needed.\n\nProject management:\n- Create projects: Set up new projects with client associations\n- Assign users: Add users to projects with appropriate access\n- Monitor progress: Track sample accessioning and testing progress\n- Update status: Modify project status and metadata\n\nBatch oversight:\n- View all batches: Access batches across all projects\n- Monitor status: Track batch progression and completion\n- Review results: Access all results for quality assurance\n- Resolve issues: Address batch-related problems and errors\n\nUser activity:\n- Monitor logins: Review last_login timestamps\n- Track changes: View audit trails for user actions\n- Identify issues: Detect unusual patterns or errors\n- Support users: Assist with access and permission issues\n\nSystem maintenance:\n- Database migrations: Run Alembic migrations for schema updates\n- Backup operations: Coordinate database backups and restores\n- Performance monitoring: Review query performance and indexes\n- Log analysis: Review application logs for errors and warnings\n\nRequires permission: All permissions (administrator role)	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a1e81ed8-52d2-42da-a2cf-bd0f6f7217e9	Getting Started	Welcome to NimbleLIMS! As an Administrator, you manage the entire system:\n\nKey responsibilities:\n- User and role management: Create users, assign roles, configure permissions\n- System configuration: Set up container types, analyses, test batteries, lists\n	Getting Started	Welcome to NimbleLIMS! As an Administrator, you manage the entire system:\n\nKey responsibilities:\n- User and role management: Create users, assign roles, configure permissions\n- System configuration: Set up container types, analyses, test batteries, lists\n- EAV configuration: Define custom attributes for flexible data modeling\n- RLS oversight: Ensure proper data isolation and security policies\n- Data management: Oversee all projects, samples, tests, and results\n- System maintenance: Perform migrations, backups, and monitoring\n\nStart by accessing the Admin Dashboard for system overview. Use the navigation menu to access different administration sections:\n- Users Management: Create and manage users and roles\n- Custom Attributes: Configure EAV custom attributes\n- System Configuration: Manage analyses, batteries, containers, lists\n- Data Views: Access all data across projects and clients\n\nPermissions:\nAs Administrator, you have all permissions (17 total):\n- Sample operations: sample:create, sample:read, sample:update, sample:delete\n- Test operations: test:assign, test:update\n- Result operations: result:enter, result:review, result:read, result:update, result:delete\n- Batch operations: batch:manage, batch:read, batch:update, batch:delete\n- Project operations: project:manage, project:read\n- System operations: user:manage, role:manage, config:edit\n\nFor detailed instructions, see the specific help sections for each area. Contact system support if you need assistance with advanced configurations.	administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
\.


--
-- Data for Name: list_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.list_entries (id, name, description, active, created_at, created_by, modified_at, modified_by, list_id) FROM stdin;
c7b692f9-ca56-4ce3-8dd2-9a0a5aa999e0	Received	Sample received	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	11111111-1111-1111-1111-111111111111
2d6b4d03-e5e7-426c-8e79-0c94a4c75800	Available for Testing	Ready for testing	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	11111111-1111-1111-1111-111111111111
ab0d1728-e74f-406d-8304-642e8555d25a	Testing Complete	Testing finished	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	11111111-1111-1111-1111-111111111111
4c55c129-7105-42e4-aff6-e885efbe61ef	Reviewed	Results reviewed	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	11111111-1111-1111-1111-111111111111
98629c9d-33b9-4b37-b874-f33489054430	Reported	Results reported	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	11111111-1111-1111-1111-111111111111
f39f0261-bde4-49e0-92e3-abfa9fa57e3f	In Process	Test in progress	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	22222222-2222-2222-2222-222222222222
d0ca0065-4ad1-46c0-99f9-50211f76ee9a	In Analysis	Under analysis	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	22222222-2222-2222-2222-222222222222
3fd29ea4-ce7d-4272-8809-b4224f4ddefd	Complete	Test completed	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	22222222-2222-2222-2222-222222222222
6aa051a1-b771-4358-85f1-82d11a92787e	Active	Project active	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	33333333-3333-3333-3333-333333333333
09cb7514-faf0-41ac-aff9-aea3b93b62e5	Completed	Project completed	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	33333333-3333-3333-3333-333333333333
ceba6d85-d325-48e3-9f8a-a2e5c09aba5e	On Hold	Project on hold	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	33333333-3333-3333-3333-333333333333
957722e5-a62a-4e11-b9f6-54a6e4e602fc	Created	Batch created	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	44444444-4444-4444-4444-444444444444
47fe0914-4429-437e-a29d-ef573a1c0e0c	In Process	Batch in process	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	44444444-4444-4444-4444-444444444444
1460711e-51b2-4110-9c98-b944cabb36f2	Completed	Batch completed	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	44444444-4444-4444-4444-444444444444
1363af1d-72d6-4292-aacf-6b4cdc81fa81	Blood	Blood sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	55555555-5555-5555-5555-555555555555
8901c4ae-cdcf-477c-87e1-e2b03544adba	Urine	Urine sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	55555555-5555-5555-5555-555555555555
38c58b2d-9c0c-483c-889f-bfb4d1865a9f	Tissue	Tissue sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	55555555-5555-5555-5555-555555555555
965d2e12-1a4c-4ef8-b3c0-6db01100a148	Water	Water sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	55555555-5555-5555-5555-555555555555
e25eb519-0bae-4e9f-ba21-7b457cbb1fcb	Human	Human matrix	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	66666666-6666-6666-6666-666666666666
bd4e2cd1-6e50-49d8-bc71-71307656a891	Environmental	Environmental matrix	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	66666666-6666-6666-6666-666666666666
110a7914-d774-4393-801f-362c36d2f21e	Food	Food matrix	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	66666666-6666-6666-6666-666666666666
720a9f45-7765-4007-b16b-fca2a6d73d58	Sample	Regular sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
94e66833-2b8b-4d55-9861-3d95b63e903d	Positive Control	Positive control	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
42eb9cb1-7b98-4760-ba2e-f7bc258f6e79	Negative Control	Negative control	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
664725c2-d577-4757-8271-2be400fbfa36	Matrix Spike	Matrix spike	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
83f80cab-2ef6-4932-8825-86706309c2ad	Duplicate	Duplicate sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
1997b900-f4b8-4960-b7d1-3ccd9b04ecba	Blank	Blank sample	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	77777777-7777-7777-7777-777777777777
c788ad6f-dc2c-4d78-9b9a-8b2db03db501	concentration	Concentration units	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	88888888-8888-8888-8888-888888888888
cfd0f9ab-1e7d-4be9-800b-4404fdfd5985	mass	Mass units	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	88888888-8888-8888-8888-888888888888
f63442fa-77ff-4d76-92c4-ed605b52d39d	volume	Volume units	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	88888888-8888-8888-8888-888888888888
0705d516-235a-4188-bd0d-acf6d40e76cf	molar	Molar units	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	88888888-8888-8888-8888-888888888888
4872cf43-99e7-43dc-ab2c-81e8f8a5510f	Email	Email address	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	99999999-9999-9999-9999-999999999999
e5909b18-990a-41b1-a226-6c15e9566aa9	Phone	Phone number	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	99999999-9999-9999-9999-999999999999
195ce946-6f6a-4e5f-bb37-c93bf2df83e7	Mobile	Mobile phone	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	99999999-9999-9999-9999-999999999999
\.


--
-- Data for Name: lists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lists (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
11111111-1111-1111-1111-111111111111	sample_status	Sample status values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
22222222-2222-2222-2222-222222222222	test_status	Test status values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
33333333-3333-3333-3333-333333333333	project_status	Project status values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
44444444-4444-4444-4444-444444444444	batch_status	Batch status values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
55555555-5555-5555-5555-555555555555	sample_types	Sample type values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
66666666-6666-6666-6666-666666666666	matrix_types	Matrix type values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
77777777-7777-7777-7777-777777777777	qc_types	QC type values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
88888888-8888-8888-8888-888888888888	unit_types	Unit type values	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
99999999-9999-9999-9999-999999999999	contact_types	Contact method types	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
\.


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locations (id, name, description, active, created_at, created_by, modified_at, modified_by, client_id, address_line1, address_line2, city, state, postal_code, country, latitude, longitude, type) FROM stdin;
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
eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee	user:manage	Manage users	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
ffffffff-ffff-ffff-ffff-ffffffffffff	role:manage	Manage roles	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0	config:edit	Edit configuration	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0	project:manage	Manage projects	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0	sample:create	Create samples	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0	sample:read	Read samples	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0	sample:update	Update samples	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0	test:assign	Assign tests	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1	test:update	Update tests	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1	result:enter	Enter results	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1	result:review	Review results	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1	batch:manage	Manage batches	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1	batch:read	Read batches	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
0f3a91e5-1126-435b-a220-ebfb92a7b214	result:update	Update results	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
06331dd3-1c9b-4e08-98f4-3e1de47c2407	result:delete	Delete results	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
eb4543af-b8e9-409f-836d-fa84c363d061	batch:update	Update batches	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
383dc6bb-caef-4407-810d-e1a5234dbce2	batch:delete	Delete batches	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
\.


--
-- Data for Name: project_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_users (project_id, user_id, access_level, granted_at, granted_by) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.projects (id, name, description, active, created_at, created_by, modified_at, modified_by, start_date, client_id, status, client_project_id, custom_attributes) FROM stdin;
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
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	Administrator	System administrator	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	Lab Manager	Laboratory manager	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
cccccccc-cccc-cccc-cccc-cccccccccccc	Lab Technician	Laboratory technician	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
dddddddd-dddd-dddd-dddd-dddddddddddd	Client	Client user	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
\.


--
-- Data for Name: samples; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.samples (id, name, description, active, created_at, created_by, modified_at, modified_by, due_date, received_date, report_date, sample_type, status, matrix, temperature, parent_sample_id, project_id, qc_type, client_sample_id, custom_attributes) FROM stdin;
\.


--
-- Data for Name: test_batteries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.test_batteries (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
c0000001-c000-c000-c000-c00000000001	EPA 8080 Full	Complete EPA Method 8080 test battery for Organochlorine Pesticides and PCBs	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N
\.


--
-- Data for Name: tests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tests (id, name, description, active, created_at, created_by, modified_at, modified_by, sample_id, analysis_id, status, review_date, test_date, technician_id, custom_attributes) FROM stdin;
\.


--
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.units (id, name, description, active, created_at, created_by, modified_at, modified_by, multiplier, type) FROM stdin;
9d882dd1-4308-4fec-8a8a-13404f0f3e55	g/L	Grams per liter	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	1.0000000000	c788ad6f-dc2c-4d78-9b9a-8b2db03db501
0bbaf745-11dd-417b-9b31-c0ad60bf4acd	mg/L	Milligrams per liter	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0010000000	c788ad6f-dc2c-4d78-9b9a-8b2db03db501
b7147128-f542-4dae-ae23-84053bf9c78b	µg/L	Micrograms per liter	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0000010000	c788ad6f-dc2c-4d78-9b9a-8b2db03db501
49b76269-6a7d-4e8a-a973-622ba901634b	g	Grams	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	1.0000000000	cfd0f9ab-1e7d-4be9-800b-4404fdfd5985
90249c37-ca1f-4d08-ae24-7ecd8f213f9f	mg	Milligrams	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0010000000	cfd0f9ab-1e7d-4be9-800b-4404fdfd5985
e6b90140-1e4c-4155-8d03-3de6de9f1262	µg	Micrograms	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0000010000	cfd0f9ab-1e7d-4be9-800b-4404fdfd5985
49e4fbf0-bc4f-4fcd-a857-4819e5bec571	L	Liters	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	1.0000000000	f63442fa-77ff-4d76-92c4-ed605b52d39d
60c2ad4a-259d-45f3-bb0d-aa222560747b	mL	Milliliters	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0010000000	f63442fa-77ff-4d76-92c4-ed605b52d39d
12cde4de-6f3a-4bac-a77b-00b33087339f	µL	Microliters	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0000010000	f63442fa-77ff-4d76-92c4-ed605b52d39d
21407a52-1db7-4d3c-a8d1-dc186a9fc762	mol/L	Moles per liter	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	1.0000000000	0705d516-235a-4188-bd0d-acf6d40e76cf
1b4b2cd1-586e-41af-a54d-40783126a3ad	mmol/L	Millimoles per liter	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	0.0010000000	0705d516-235a-4188-bd0d-acf6d40e76cf
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, name, description, active, created_at, created_by, modified_at, modified_by, username, password_hash, email, role_id, client_id, last_login) FROM stdin;
00000000-0000-0000-0000-000000000002	Lab Manager	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	lab-manager	7dd63afe29407aa45af7fdd4388b71195b552688c2750abd42bdf3b231c13b69	lab-manager@lims.local	bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	00000000-0000-0000-0000-000000000001	\N
00000000-0000-0000-0000-000000000003	Lab Technician	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	lab-tech	d81968c60a8a41bdafcb3c5825bf8bc4a76dccc932d673e3f9a7b71ce4538596	lab-tech@lims.local	cccccccc-cccc-cccc-cccc-cccccccccccc	00000000-0000-0000-0000-000000000001	\N
a4c89373-1430-4d0d-a4d0-36c367421bdf	Client User	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 22:48:56.308924	\N	client	186474c1f2c2f735a54c2cf82ee8e87f2a5cd30940e280029363fecedfc5328c	client@example.com	dddddddd-dddd-dddd-dddd-dddddddddddd	00000000-0000-0000-0000-000000000001	\N
00000000-0000-0000-0000-000000000001	System Administrator	\N	t	2026-01-03 22:48:56.308924	\N	2026-01-03 23:21:47.57885	\N	admin	240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9	admin@lims.local	aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	00000000-0000-0000-0000-000000000001	2026-01-03 23:21:47.57885
\.


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
  WHERE ((u.id = public.current_user_id()) AND (u.client_id = client_projects.client_id))))));


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
-- Name: projects; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

--
-- Name: projects projects_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY projects_access ON public.projects USING ((public.is_admin() OR public.has_project_access(id) OR (EXISTS ( SELECT 1
   FROM (public.users u
     JOIN public.roles r ON ((u.role_id = r.id)))
  WHERE ((u.id = public.current_user_id()) AND ((r.name)::text = 'Client'::text) AND (u.client_id IS NOT NULL) AND (projects.client_id = u.client_id))))));


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

\unrestrict aTew83o9pglCOGWtsjY25pr2RcGhKEevDXocaaSc4YbVr2lo0ggpkjuaCQHDpk0

