-- LIMS MVP Database Initialization Script
-- This script sets up the initial database structure and configurations

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE lims_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lims_db')\gexec

-- Connect to the lims_db database
\c lims_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS lims;

-- Set search path
SET search_path TO lims, public;

-- Create initial tables will be handled by Alembic migrations
-- This file serves as a placeholder for any initial setup scripts
