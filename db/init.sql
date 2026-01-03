-- NimbleLims Database Initialization Script
-- This script sets up the initial database structure and configurations
-- Note: This script runs automatically when the container is first created
-- The database and user are already created by POSTGRES_* environment variables

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS lims;

-- Set search path
SET search_path TO lims, public;

-- Database schema and data will be created by Alembic migrations
