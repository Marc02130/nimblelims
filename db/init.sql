-- NimbleLims Database Initialization Script
-- This script sets up the initial database structure and configurations
-- Note: This script runs automatically when the container is first created
-- The database and user are already created by POSTGRES_* environment variables

-- Create extensions. vector is not a trusted extension, so the bootstrap
-- superuser creates it here. Alembic's CREATE EXTENSION IF NOT EXISTS then
-- skips it when lims_migrate (not a superuser) runs the migrations.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS lims;

-- Set search path
SET search_path TO lims, public;

-- Database schema and data will be created by Alembic migrations
