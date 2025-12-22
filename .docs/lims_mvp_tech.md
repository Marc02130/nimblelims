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
- Version 1.3: Incorporated refinements for containers (admin pre-setup for types, dynamic instance creation during workflows, no pre-created instances in MVP) and lists (full admin-editable CRUD with normalized naming and API support) based on iterative planning (December 21, 2025).

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
  - `type_id` (FK container_types.id; required, must reference existing active type)
  - `parent_container_id` (FK containers.id, nullable for hierarchy)
  - Notes: Instances created dynamically during workflows (e.g., accessioning); no pre-creation in MVP. Samples are always received in a container, which must be specified during accessioning.

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
  - Notes: Pre-setup and managed by admins for standardization; types must exist before container instance creation. Admin can create, edit, and delete container types via admin interface.

- **Units**:
  - `multiplier` (numeric; relative to base unit for conversions, e.g., 0.001 for mg relative to g)
  - `type` (FK list_entries.id; e.g., 'concentration', 'mass', 'volume', 'molar')
  - Notes: Base units implied by type (e.g., g/L for concentration, g for mass, L for volume, mol/L for molar). Compound units (e.g., µg/µL) handled as single entries with multiplier.

- **Lists**:
  - No additional fields beyond standard.
  - Notes: Containers for configurable dropdowns/statuses (e.g., "sample_status", "qc_types"); names normalized to lowercase slug format (e.g., "Sample Status" → sample_status). Admin can create, edit, and delete lists and their entries via admin interface.

- **List_Entries**:
  - `list_id` (FK lists.id)
  - Notes: Individual options within lists; unique names per list; soft deletion via active flag. Admin can manage entries via admin interface.

- **Analyses**:
  - `method` (varchar)
  - `turnaround_time` (integer)
  - `cost` (numeric)

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
  - GET /samples?project_id=...&status=...: List filtered by user access (query params accept UUIDs, empty strings converted to None).
  - POST /samples: Create with accessioning data.
  - PATCH /samples/{id}: Update status/container.
- **Tests**: 
  - POST /tests: Assign analysis to sample.
  - PATCH /tests/{id}: Update status/review.
- **Results**: 
  - POST /results: Enter batch-based results with validation.
- **Batches**: 
  - GET /batches?status=...&type=...: List batches with filtering (requires `batch:read` permission).
  - POST /batches: Create and add containers (requires `batch:manage` permission).
  - GET /batches/{id}: Retrieve with contents/samples.
- **Analyses**:
  - GET /analyses: List all active analyses.
- **Units**: 
  - GET /units: List all active units with multipliers/types.
- **Lists**:
  - GET /lists/{list_name}/entries: Get entries for a list (list names normalized to lowercase slug format, e.g., `sample_status`).
  - GET /lists: Get all lists with their entries.
  - POST /lists: Create new list (admin-only, requires config:edit).
  - PATCH /lists/{id}: Update list (admin-only).
  - DELETE /lists/{id}: Soft-delete list (admin-only).
  - POST /lists/{list_name}/entries: Add entry to list (admin-only).
  - PATCH /lists/{list_name}/entries/{entry_id}: Update entry (admin-only).
  - DELETE /lists/{list_name}/entries/{entry_id}: Soft-delete entry (admin-only).
- **Containers**:
  - GET /containers: List containers.
  - GET /containers/types: Get container types (public lookup).
  - POST /containers/types: Create type (admin-only, config:edit).
  - PATCH /containers/types/{id}: Update type (admin-only).
  - DELETE /containers/types/{id}: Soft-delete type (admin-only).
  - POST /containers: Create instance dynamically (requires sample:create).
  - GET /containers/{id}: Retrieve with hierarchy/contents.
- **Projects**:
  - GET /projects: List projects accessible to user (RBAC enforced).
- **Users/Roles**: Admin-only CRUD for management.
- Error Handling: Standard HTTP codes; JSON {error, detail}.

### 4.3 Validation
- Backend: Use Pydantic for request schemas; custom validators for analyte rules.
- Security: Dependency injection in FastAPI for permission checks (e.g., @requires_permission('sample:create')).

## 5. Frontend Implementation

### 5.1 Components
- **Auth**: Login form; email verification modal.
- **Dashboard**: Role-based views (e.g., client sees own projects).
- **Accessioning Form**: Multi-step wizard for sample entry/test assignment, with required container specification (select pre-setup type, create instance dynamically).
- **Batch View**: Select containers; grid for plate wells; result entry table.
- **Admin Section**: Dashboard with links to manage container types (CRUD) and lists (full CRUD for lists/entries); restricted to config:edit.
- **State Management**: Redux or Context API for user/session data.

### 5.2 UI/UX
- Responsive design; real-time validation (e.g., Formik/Yup).
- Accessibility: ARIA labels; WCAG compliance.

## 6. Workflows Implementation

- **Accessioning**: API sequence: POST /containers (dynamic instance creation), POST /contents (link to sample), POST /samples → POST /tests. Requires specifying pre-setup container type.
- **Aliquots/Derivatives**: POST /samples with parent_id; inherit via backend logic; create new container instance dynamically.
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
