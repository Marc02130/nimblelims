--
-- PostgreSQL database dump
--

\restrict E7duE09XQKoCgbOGT4EX7mIvNxmz78bXWeQVhGFSsBifLgOedDcxPwfJ9g5ht1b

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
DROP INDEX IF EXISTS public.idx_samples_created_by;
DROP INDEX IF EXISTS public.idx_samples_client_sample_id;
DROP INDEX IF EXISTS public.idx_results_test_id_analyte_id;
DROP INDEX IF EXISTS public.idx_results_test_id_active;
DROP INDEX IF EXISTS public.idx_results_test_id;
DROP INDEX IF EXISTS public.idx_results_qualifiers;
DROP INDEX IF EXISTS public.idx_results_modified_by;
DROP INDEX IF EXISTS public.idx_results_entered_by;
DROP INDEX IF EXISTS public.idx_results_created_by;
DROP INDEX IF EXISTS public.idx_results_analyte_id;
DROP INDEX IF EXISTS public.idx_projects_status;
DROP INDEX IF EXISTS public.idx_projects_name_unique;
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
DROP INDEX IF EXISTS public.idx_client_projects_client_id;
DROP INDEX IF EXISTS public.idx_battery_analyses_sequence;
DROP INDEX IF EXISTS public.idx_battery_analyses_battery_id;
DROP INDEX IF EXISTS public.idx_battery_analyses_battery_analysis;
DROP INDEX IF EXISTS public.idx_batches_type;
DROP INDEX IF EXISTS public.idx_batches_status_type;
DROP INDEX IF EXISTS public.idx_batches_status_active;
DROP INDEX IF EXISTS public.idx_batches_status;
DROP INDEX IF EXISTS public.idx_batches_name_unique;
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
    end_date timestamp without time zone
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
    modified_by uuid
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
    client_project_id uuid
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
    entered_by uuid NOT NULL
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
    client_sample_id character varying(255)
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
    technician_id uuid
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
0012
\.


--
-- Data for Name: analyses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analyses (id, name, description, active, created_at, created_by, modified_at, modified_by, method, turnaround_time, cost) FROM stdin;
b0000001-b000-b000-b000-b00000000001	pH Measurement	\N	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	Electrometric	1	10.00
b0000002-b000-b000-b000-b00000000002	EPA Method 8080	\N	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	GC/ECD for Organochlorine Pesticides and PCBs	7	150.00
b0000003-b000-b000-b000-b00000000003	Total Coliform Enumeration	\N	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	Colilert or Membrane Filtration	2	50.00
b0000002-b000-b000-b000-b00000000004	EPA Method 8080 Prep	\N	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	Sample Extractionfor Organochlorine Pesticides and PCBs	7	25.00
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
a0000001-a000-a000-a000-a00000000001	pH	pH value	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000002-a000-a000-a000-a00000000002	Aldrin	Organochlorine pesticide	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000003-a000-a000-a000-a00000000003	DDT	Organochlorine pesticide	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000004-a000-a000-a000-a00000000004	PCB-1016	Polychlorinated biphenyl	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000005-a000-a000-a000-a00000000005	Total Coliforms	Coliform bacteria count	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000006-a000-a000-a000-a00000000006	E. coli	Escherichia coli count	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0000004-a000-a000-a000-a00000000005	Initial Volume	Sample volume extracted	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
\.


--
-- Data for Name: batch_containers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batch_containers (batch_id, container_id, "position", notes) FROM stdin;
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batches (id, name, description, active, created_at, created_by, modified_at, modified_by, type, status, start_date, end_date) FROM stdin;
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

COPY public.client_projects (id, name, description, client_id, active, created_at, created_by, modified_at, modified_by) FROM stdin;
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clients (id, name, description, active, created_at, created_by, modified_at, modified_by, billing_info) FROM stdin;
00000000-0000-0000-0000-000000000001	System	System client for admin users	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	{}
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
-- Data for Name: list_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.list_entries (id, name, description, active, created_at, created_by, modified_at, modified_by, list_id) FROM stdin;
ce3cf258-637e-4bad-ab48-202385b69d32	Received	Sample received	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	11111111-1111-1111-1111-111111111111
199b0438-e132-429f-92fe-f678006912c0	Available for Testing	Ready for testing	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	11111111-1111-1111-1111-111111111111
fc31f2d3-5507-4220-9c06-92921e78ba92	Testing Complete	Testing finished	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	11111111-1111-1111-1111-111111111111
ca78ad87-7a87-427f-b7db-3136287e9ddf	Reviewed	Results reviewed	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	11111111-1111-1111-1111-111111111111
a0e242a8-bb74-419a-bca1-aaf1d15ac7fe	Reported	Results reported	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	11111111-1111-1111-1111-111111111111
6bd1ea61-c124-417a-ae6a-76c052af1ffb	In Process	Test in progress	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	22222222-2222-2222-2222-222222222222
470c1f38-d466-4fec-82cb-2e4928b00793	In Analysis	Under analysis	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	22222222-2222-2222-2222-222222222222
050bd10b-bd2b-4b5f-9d10-f1d17f2d68fe	Complete	Test completed	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	22222222-2222-2222-2222-222222222222
00dc13c8-8070-4bd8-851f-3f7a863251de	Active	Project active	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	33333333-3333-3333-3333-333333333333
ab94d3b6-6dff-4d7c-8ced-ca5548b9cf31	Completed	Project completed	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	33333333-3333-3333-3333-333333333333
49c81677-e109-415f-a7eb-11343a2db363	On Hold	Project on hold	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	33333333-3333-3333-3333-333333333333
9f3ab8ca-e99b-4789-be01-5b5141769b85	Created	Batch created	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	44444444-4444-4444-4444-444444444444
b97bb095-3c4b-44e6-930a-8012399652be	In Process	Batch in process	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	44444444-4444-4444-4444-444444444444
1bf86869-e1eb-4172-86d1-f85afaf0e1f6	Completed	Batch completed	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	44444444-4444-4444-4444-444444444444
1627dd23-c4d1-45b8-a755-c9fb3b399d39	Blood	Blood sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	55555555-5555-5555-5555-555555555555
509c6ba1-35f4-4bf8-b40a-67258a64bc7d	Urine	Urine sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	55555555-5555-5555-5555-555555555555
855f1b4c-c499-448d-891b-11af8eb9807d	Tissue	Tissue sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	55555555-5555-5555-5555-555555555555
a4ec5c54-6a8f-48a4-aca3-5ff4182aef5e	Water	Water sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	55555555-5555-5555-5555-555555555555
867a7485-6e27-4d4a-9aea-b6ae82eff6d4	Human	Human matrix	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	66666666-6666-6666-6666-666666666666
aed5f677-ba3c-4838-8a6a-1badb771388e	Environmental	Environmental matrix	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	66666666-6666-6666-6666-666666666666
b7921ee7-cf8a-4aab-8683-57e5bb38f5c8	Food	Food matrix	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	66666666-6666-6666-6666-666666666666
2de61690-36ca-46e0-bf31-936fc1f804a7	Sample	Regular sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
891ff5c1-6e7b-454d-bef8-5eb1d4a16843	Positive Control	Positive control	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
7f9f14de-d764-4842-b9fa-41759dee3b47	Negative Control	Negative control	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
a387b37d-9b80-4b36-9c7b-506c2f1a7306	Matrix Spike	Matrix spike	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
15f19053-7674-477f-93b0-e53b3e00e89e	Duplicate	Duplicate sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
f5d78649-eb7b-4cc5-97b3-04a65190f267	Blank	Blank sample	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	77777777-7777-7777-7777-777777777777
6cbb60b6-7708-4b23-83e1-98aa054b7852	concentration	Concentration units	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	88888888-8888-8888-8888-888888888888
5460a872-0673-4a1c-b64b-1405ce8579cc	mass	Mass units	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	88888888-8888-8888-8888-888888888888
84931478-edb9-431c-b964-64c25f9840d3	volume	Volume units	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	88888888-8888-8888-8888-888888888888
16126a88-e075-4682-97f0-caac6f4fbef7	molar	Molar units	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	88888888-8888-8888-8888-888888888888
f8c8cdc5-a869-45de-8dcc-1bd96232d3da	Email	Email address	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	99999999-9999-9999-9999-999999999999
6e81ede1-d7f3-44b7-af8a-f189d13e43b6	Phone	Phone number	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	99999999-9999-9999-9999-999999999999
00e2c448-c009-4cb0-898f-e2e97d50e436	Mobile	Mobile phone	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	99999999-9999-9999-9999-999999999999
\.


--
-- Data for Name: lists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lists (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
11111111-1111-1111-1111-111111111111	sample_status	Sample status values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
22222222-2222-2222-2222-222222222222	test_status	Test status values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
33333333-3333-3333-3333-333333333333	project_status	Project status values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
44444444-4444-4444-4444-444444444444	batch_status	Batch status values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
55555555-5555-5555-5555-555555555555	sample_types	Sample type values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
66666666-6666-6666-6666-666666666666	matrix_types	Matrix type values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
77777777-7777-7777-7777-777777777777	qc_types	QC type values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
88888888-8888-8888-8888-888888888888	unit_types	Unit type values	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
99999999-9999-9999-9999-999999999999	contact_types	Contact method types	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
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
eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee	user:manage	Manage users	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
ffffffff-ffff-ffff-ffff-ffffffffffff	role:manage	Manage roles	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0	config:edit	Edit configuration	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0	project:manage	Manage projects	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0	sample:create	Create samples	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0	sample:read	Read samples	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0	sample:update	Update samples	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0	test:assign	Assign tests	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1	test:update	Update tests	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1	result:enter	Enter results	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1	result:review	Review results	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1	batch:manage	Manage batches	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1	batch:read	Read batches	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
e58297d6-2ac8-4fd3-812b-d377cc58a299	result:update	Update results	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
e505b2c4-08f2-4855-a5a0-fff7f4249b8f	result:delete	Delete results	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
ec18805b-02eb-40df-92b6-a31a479f21fe	batch:update	Update batches	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
cd59cff8-e1ba-44af-92ba-3e3a5b92f9ee	batch:delete	Delete batches	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
\.


--
-- Data for Name: project_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_users (project_id, user_id, access_level, granted_at, granted_by) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.projects (id, name, description, active, created_at, created_by, modified_at, modified_by, start_date, client_id, status, client_project_id) FROM stdin;
\.


--
-- Data for Name: results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.results (id, name, description, active, created_at, created_by, modified_at, modified_by, test_id, analyte_id, raw_result, reported_result, qualifiers, calculated_result, entry_date, entered_by) FROM stdin;
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
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.roles (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	Administrator	System administrator	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb	Lab Manager	Laboratory manager	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
cccccccc-cccc-cccc-cccc-cccccccccccc	Lab Technician	Laboratory technician	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
dddddddd-dddd-dddd-dddd-dddddddddddd	Client	Client user	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
\.


--
-- Data for Name: samples; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.samples (id, name, description, active, created_at, created_by, modified_at, modified_by, due_date, received_date, report_date, sample_type, status, matrix, temperature, parent_sample_id, project_id, qc_type, client_sample_id) FROM stdin;
\.


--
-- Data for Name: test_batteries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.test_batteries (id, name, description, active, created_at, created_by, modified_at, modified_by) FROM stdin;
c0000001-c000-c000-c000-c00000000001	EPA 8080 Full	Complete EPA Method 8080 test battery for Organochlorine Pesticides and PCBs	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N
\.


--
-- Data for Name: tests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tests (id, name, description, active, created_at, created_by, modified_at, modified_by, sample_id, analysis_id, status, review_date, test_date, technician_id) FROM stdin;
\.


--
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.units (id, name, description, active, created_at, created_by, modified_at, modified_by, multiplier, type) FROM stdin;
9da7b8d9-d828-423b-86f3-91f475a31be9	g/L	Grams per liter	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	1.0000000000	6cbb60b6-7708-4b23-83e1-98aa054b7852
4c9f6a26-dbd0-4b19-8dc7-3fbf1c0f71b5	mg/L	Milligrams per liter	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0010000000	6cbb60b6-7708-4b23-83e1-98aa054b7852
f5735a9e-e243-48dc-a025-373e5e999974	µg/L	Micrograms per liter	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0000010000	6cbb60b6-7708-4b23-83e1-98aa054b7852
fd44640c-3c79-46cb-aa2e-111d3bac26a4	g	Grams	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	1.0000000000	5460a872-0673-4a1c-b64b-1405ce8579cc
6746a198-6a13-4ee1-9c6f-a6fce0bd3625	mg	Milligrams	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0010000000	5460a872-0673-4a1c-b64b-1405ce8579cc
d20ee8d0-be43-40a4-a476-c192835bfd0b	µg	Micrograms	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0000010000	5460a872-0673-4a1c-b64b-1405ce8579cc
f9a2c662-66c7-4e7d-bc07-42067e7a5931	L	Liters	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	1.0000000000	84931478-edb9-431c-b964-64c25f9840d3
9f9887fd-1dc7-41c0-b54a-881bcc42caf2	mL	Milliliters	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0010000000	84931478-edb9-431c-b964-64c25f9840d3
3e2bab77-489b-4981-9afe-06ddfc4be369	µL	Microliters	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0000010000	84931478-edb9-431c-b964-64c25f9840d3
176f49db-2ea0-44f8-9e35-2d8d9c5b2545	mol/L	Moles per liter	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	1.0000000000	16126a88-e075-4682-97f0-caac6f4fbef7
18ef8146-4055-427a-88b8-e25cabb95473	mmol/L	Millimoles per liter	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:39.478317	\N	0.0010000000	16126a88-e075-4682-97f0-caac6f4fbef7
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, name, description, active, created_at, created_by, modified_at, modified_by, username, password_hash, email, role_id, client_id, last_login) FROM stdin;
00000000-0000-0000-0000-000000000001	System Administrator	\N	t	2025-12-28 19:21:39.478317	\N	2025-12-28 19:21:53.50371	\N	admin	240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9	admin@lims.local	aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa	00000000-0000-0000-0000-000000000001	2025-12-28 19:21:53.50371
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
-- Name: projects; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

--
-- Name: projects projects_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY projects_access ON public.projects USING ((public.is_admin() OR public.has_project_access(id)));


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

\unrestrict E7duE09XQKoCgbOGT4EX7mIvNxmz78bXWeQVhGFSsBifLgOedDcxPwfJ9g5ht1b

