# Technical Document for LIMS MVP

## 1. Introduction

### 1.1 Purpose
This Technical Document provides detailed specifications for implementing the Minimum Viable Product (MVP) of the API-first Laboratory Information Management System (LIMS). It builds on the Product Requirements Document (PRD) by outlining the technical architecture, database schema, API endpoints, frontend components, security implementation, and deployment considerations. This document serves as a blueprint for development in Cursor, ensuring alignment with the planned requirements for sample tracking, test ordering, and results entry.

### 1.2 Scope
The MVP focuses on core functionality using PostgreSQL for data storage, Python (FastAPI with SQLAlchemy) for the backend API, and React for the frontend UI. Emphasis is on a normalized schema, RESTful APIs with JWT authentication, and RBAC enforcement. Post-MVP features like instrument integration or advanced calculations are referenced but not detailed.

### 1.3 Assumptions
- Development follows PEP8 for Python and ESLint for React.
- Environment: Python 3.10+, PostgreSQL 15+, Node.js 18+ for React.
- Testing: Unit/integration tests for backend (pytest), frontend (Jest), and end-to-end (Cypress).
- Deployment: Docker for containerization with three dedicated containers (one for DB, one for backend, one for frontend); potential cloud hosting (e.g., AWS/Heroku) post-MVP.

### 1.4 Version History
- Version 1.0: Initial draft based on planning discussions (October 21, 2025).
- Version 1.1: Added units table and related integrations for measurements (e.g., concentration/amount units).
- Version 1.2: Updated deployment section to specify three Docker containers (DB, backend, frontend) as per refined requirements.

## 2. System Architecture

### 2.1 High-Level Overview
- **Backend**: FastAPI for API server; SQLAlchemy ORM for DB interactions; JWT (PyJWT) for auth.
- **Database**: PostgreSQL with normalized schema; Row-Level Security (RLS) for data isolation.
- **Frontend**: React app with Axios for API calls; React Router for navigation; Material-UI or similar for components.
- **Communication**: RESTful APIs over HTTPS; JSON payloads.
- **Security**: JWT tokens; bcrypt for password hashing; RLS policies in Postgres.
- **Scalability**: UUID primary keys; indexing on foreign keys; async endpoints where applicable.
- **Containerization**: System runs in three Docker containers: one for Postgres DB, one for Python backend (FastAPI), and one for React frontend (served via Node.js or Nginx).

### 2.2 Data Flow
- User authenticates via /auth/login → Receives JWT.
- API requests include JWT in headers; backend validates role/permissions.
- Workflows (e.g., accessioning): Frontend forms submit to API → Backend processes, updates DB → Returns updated data.
- Queries filter by user context (e.g., client_id for clients).

## 3. Database Schema

All tables include standard fields: `id` (UUID PK), `name` (varchar unique), `description` (text), `active` (boolean default true), `created_at` (timestamp), `created_by` (FK users.id), `modified_at` (timestamp), `modified_by` (FK users.id).

### 3.1 Key Tables

- **Samples**:
  - `due_date` (timestamp)
  - `received_date` (timestamp)
  - `report_date` (timestamp)
  - `sample_type` (FK list_entries.id)
  - `status` (FK list_entries.id)
  - `matrix` (FK list_entries.id)
  - `temperature` (numeric)
  - `parent_sample_id` (FK samples.id, nullable)
  - `project_id` (FK projects.id)
  - `qc_type` (FK list_entries.id, nullable)
  - Constraints: Unique name; FK cascades where appropriate.

- **Containers**:
  - `row` (integer default 1)
  - `column` (integer default 1)
  - `concentration` (numeric)
  - `concentration_units` (FK units.id)
  - `amount` (numeric)
  - `amount_units` (FK units.id)
  - `type_id` (FK container_types.id)
  - `parent_container_id` (FK containers.id, nullable for hierarchy)

- **Contents** (Junction):
  - `container_id` (FK containers.id)
  - `sample_id` (FK samples.id)
  - `concentration` (numeric)
  - `concentration_units` (FK units.id)
  - `amount` (numeric)
  - `amount_units` (FK units.id)
  - Unique (container_id, sample_id)

- **Container_Types**:
  - `capacity` (numeric)
  - `material` (varchar)
  - `dimensions` (varchar, e.g., '8x12')
  - `preservative` (varchar)

- **Units**:
  - `multiplier` (numeric; relative to base unit for conversions, e.g., 0.001 for mg relative to g)
  - `type` (FK list_entries.id; e.g., 'concentration', 'mass', 'volume', 'molar')
  - Notes: Base units implied by type (e.g., g/L for concentration, g for mass, L for volume, mol/L for molar). Compound units (e.g., µg/µL) handled as single entries with multiplier.

- **Analyses**:
  - `method` (varchar)
  - `turnaround_time` (integer)
  - `cost` (numeric)

- **Analytes**:
  - `name` (varchar)

- **Analysis_Analytes** (Junction):
  - `analysis_id` (FK analyses.id)
  - `analyte_id` (FK analytes.id)
  - `data_type` (varchar, e.g., 'numeric')
  - `list_id` (FK lists.id, nullable)
  - `high_value` (numeric, nullable)
  - `low_value` (numeric, nullable)
  - `significant_figures` (integer, nullable)
  - `calculation` (text, nullable)
  - `reported_name` (varchar)
  - `display_order` (integer)
  - `is_required` (boolean)
  - `default_value` (varchar, nullable)

- **Tests**:
  - `sample_id` (FK samples.id)
  - `analysis_id` (FK analyses.id)
  - `status` (FK list_entries.id)
  - `review_date` (timestamp, nullable)
  - `test_date` (timestamp, nullable)
  - `technician_id` (FK users.id)

- **Results**:
  - `test_id` (FK tests.id)
  - `analyte_id` (FK analytes.id)
  - `raw_result` (varchar)
  - `reported_result` (varchar)
  - `qualifiers` (FK list_entries.id, nullable)
  - `calculated_result` (varchar, nullable)
  - `entry_date` (timestamp)
  - `entered_by` (FK users.id)

- **Batches**:
  - `type` (FK list_entries.id, nullable)
  - `status` (FK list_entries.id)
  - `start_date` (timestamp, nullable)
  - `end_date` (timestamp, nullable)

- **Batch_Containers** (Junction):
  - `batch_id` (FK batches.id)
  - `container_id` (FK containers.id)
  - `position` (varchar, nullable)
  - `notes` (text, nullable)

- **Projects**:
  - `start_date` (timestamp)
  - `client_id` (FK clients.id)
  - `status` (FK list_entries.id)

- **Project_Users** (Junction):
  - `project_id` (FK projects.id)
  - `user_id` (FK users.id)
  - `access_level` (FK list_entries.id, nullable)
  - `granted_at` (timestamp)
  - `granted_by` (FK users.id)

- **Clients**:
  - `billing_info` (JSONB default '{}')

- **Locations**:
  - `client_id` (FK clients.id)
  - `address_line1` (varchar)
  - `address_line2` (varchar, nullable)
  - `city` (varchar)
  - `state` (varchar)
  - `postal_code` (varchar)
  - `country` (varchar default 'US')
  - `latitude` (numeric, nullable)
  - `longitude` (numeric, nullable)
  - `type` (FK list_entries.id, nullable)

- **People**:
  - `first_name` (varchar)
  - `last_name` (varchar)
  - `title` (varchar, nullable)
  - `role` (FK list_entries.id, nullable)

- **People_Locations** (Junction):
  - `person_id` (FK people.id)
  - `location_id` (FK locations.id)
  - `primary` (boolean default false)
  - `notes` (text, nullable)

- **Contact_Methods**:
  - `person_id` (FK people.id)
  - `type` (FK list_entries.id)
  - `value` (varchar)
  - `description` (text, nullable)
  - `primary` (boolean default false)
  - `verified` (boolean default false)

- **Users**:
  - `username` (varchar unique)
  - `password_hash` (varchar)
  - `email` (varchar unique)
  - `role_id` (FK roles.id)
  - `client_id` (FK clients.id, nullable)
  - `last_login` (timestamp, nullable)

- **Roles**:
  - No additional fields.

- **Permissions**:
  - No additional fields.

- **Role_Permissions** (Junction):
  - `role_id` (FK roles.id)
  - `permission_id` (FK permissions.id)

- **Lists**:
  - No additional fields.

- **List_Entries**:
  - `list_id` (FK lists.id)

### 3.2 Indexes and Constraints
- Indexes: On all FKs (e.g., project_id in samples); unique constraints on names/usernames.
- RLS Policies: e.g., ON samples FOR SELECT USING (project_id IN (SELECT project_id FROM project_users WHERE user_id = current_user_id()));
- Triggers: Auto-populate audit fields (e.g., created_at = NOW()).

## 4. API Design

### 4.1 Authentication
- `/auth/login`: POST {username, password} → JWT token.
- `/auth/verify-email`: POST {email, token} → Confirm email.
- All endpoints: Require JWT; decode for user_id/role/permissions.

### 4.2 Key Endpoints
- **Samples**: 
  - GET /samples?project_id=...&status=...: List filtered by user access.
  - POST /samples: Create with accessioning data.
  - PATCH /samples/{id}: Update status/container.
- **Tests**: 
  - POST /tests: Assign analysis to sample.
  - PATCH /tests/{id}: Update status/review.
- **Results**: 
  - POST /results: Enter batch-based results with validation.
- **Batches**: 
  - POST /batches: Create and add containers.
  - GET /batches/{id}: Retrieve with contents/samples.
- **Units**: 
  - CRUD /units: Manage units with multipliers/types (admin-only).
- **Users/Roles**: Admin-only CRUD for management.
- Error Handling: Standard HTTP codes; JSON {error, detail}.

### 4.3 Validation
- Backend: Use Pydantic for request schemas; custom validators for analyte rules.
- Security: Dependency injection in FastAPI for permission checks (e.g., @requires_permission('sample:create')).

## 5. Frontend Implementation

### 5.1 Components
- **Auth**: Login form; email verification modal.
- **Dashboard**: Role-based views (e.g., client sees own projects).
- **Accessioning Form**: Multi-step wizard for sample entry/test assignment.
- **Batch View**: Select containers; grid for plate wells; result entry table.
- **State Management**: Redux or Context API for user/session data.

### 5.2 UI/UX
- Responsive design; real-time validation (e.g., Formik/Yup).
- Accessibility: ARIA labels; WCAG compliance.

## 6. Workflows Implementation

- **Accessioning**: API sequence: POST /samples → POST /tests.
- **Aliquots/Derivatives**: POST /samples with parent_id; inherit via backend logic.
- **Results Entry**: GET /batches/{id}/samples → POST /results with batch context.
- **Pooled Samples**: POST /contents; backend uses units multipliers for conversions (e.g., volume = amount / concentration, normalized to base units).
- **Configurable Workflows**: JSON-based configs in DB (post-MVP expansion).

## 7. Testing and Deployment

### 7.1 Testing
- Unit: Backend endpoints, validators; frontend components.
- Integration: API-DB interactions; auth flows.
- Security: Penetration testing for RBAC/RLS.

### 7.2 Deployment
- **Containerization**: Use Docker with three separate containers:
  - **DB Container**: Runs PostgreSQL; Dockerfile based on official postgres image. Environment variables for DB credentials; persistent volume for data.
  - **Backend Container**: Runs Python/FastAPI; Dockerfile installs dependencies (e.g., via requirements.txt including fastapi, sqlalchemy, pyjwt, passlib[bcrypt]). Exposes port 8000; depends on DB container for startup.
  - **Frontend Container**: Runs React app; Dockerfile builds with npm/yarn and serves via Node.js or Nginx. Exposes port 3000; static build for production.
- **Orchestration**: Docker Compose for local dev and testing; compose file defines services, networks, volumes, and dependencies (e.g., backend waits for DB).
- **CI/CD**: GitHub Actions for builds/tests; deploy to Docker Hub or similar.
- **Monitoring**: Logging with Sentry; performance metrics.

## 8. Risks and Mitigations
- Data Integrity: Use transactions; backups.
- Performance: Query optimization; caching (Redis post-MVP).
- Schema Evolution: Use Alembic for migrations.

## 9. Appendices
- References: FastAPI docs, SQLAlchemy guide, React best practices, Docker documentation.
- Glossary: Aligns with PRD.