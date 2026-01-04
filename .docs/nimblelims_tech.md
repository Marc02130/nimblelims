# Technical Document for NimbleLIMS

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
- Version 1.4: Added test batteries feature (test_batteries table, battery_analyses junction with sequence/optional flags, integration with accessioning workflow) - December 2025.
- Version 1.5: Added EAV (Entity-Attribute-Value) model for configurability - custom attributes support for samples, tests, results, projects, client_projects, and batches (December 2025).
- Version 1.6: Added client help system with role-filtered help content, Client role seeding, and help API endpoints (January 2025).
- Version 1.7: Added lab technician help system with role-filtered help content (lab-technician slug format), LabTechHelpSection component, tooltips in accessioning and results entry, and comprehensive test coverage (January 2025).
- Version 1.8: Added lab manager help system with role-filtered help content (lab-manager slug format), LabManagerHelpSection component, tooltips in results management and batch results view, comprehensive test coverage including ARIA accessibility and RLS enforcement, and verification scripts (January 2025).
- Version 1.9: Added admin help system with role-filtered help content (administrator slug format), AdminHelpSection component, HelpManagement CRUD page for editing help entries (requires config:edit permission), role_filter validation against existing roles, comprehensive test coverage including CRUD and RBAC tests, tooltip in CustomFieldsManagement, and verification scripts (January 2025).
- Version 2.0: Added editing for samples, tests, and containers with PATCH endpoints, management pages (SamplesManagement, TestsManagement, enhanced ContainerManagement), reusable form components (SampleForm, TestForm, ContainerForm), RBAC enforcement (sample:update, test:update permissions), audit field updates (modified_at, modified_by), comprehensive test coverage (backend PATCH scenarios, RBAC, audit updates; frontend list rendering, edit navigation, form modes, ARIA, permission hiding), and database indexes for efficient editing (January 2025).

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
- **Help Flow (Client)**: User accesses /help → Frontend checks user role → If Client, fetches role-filtered help entries via GET /help?role=Client → Backend RLS filters entries by role_filter matching user's role OR role_filter=NULL (public) → Returns filtered help entries → Frontend displays in accordion format via ClientHelpSection component.
- **Help Flow (Lab Technician)**: User accesses /help → Frontend checks user role → If lab-technician, fetches role-filtered help entries via GET /help?role=lab-technician → Backend converts role name "Lab Technician" to slug "lab-technician" → Backend RLS filters entries by role_filter matching slug OR role_filter=NULL (public) → Returns filtered help entries → Frontend displays in accordion format via LabTechHelpSection component with ARIA labels for accessibility.
- **Help Flow (Lab Manager)**: User accesses /help → Frontend checks user role → If Lab Manager or lab-manager, fetches role-filtered help entries via GET /help → Backend converts role name "Lab Manager" to slug "lab-manager" → Backend RLS filters entries by role_filter matching slug OR role_filter=NULL (public) → Returns filtered help entries → Frontend displays in accordion format via LabManagerHelpSection component with ARIA labels for accessibility. Lab Managers see help covering Results Review, Batch Management, Project Management, Quality Control, and Test Assignment Oversight.
- **Help Flow (Administrator)**: User accesses /help → Frontend checks user role → If Administrator, fetches role-filtered help entries via GET /help?role=administrator → Backend RLS filters entries by role_filter matching "administrator" slug OR role_filter=NULL (public) → Returns filtered help entries → Frontend displays in accordion format via AdminHelpSection component with ARIA labels for accessibility. Administrators see help covering User Management, EAV Configuration, Row Level Security (RLS), System Configuration, Data Management, and Getting Started. Administrators with config:edit permission can access Help Management page (/admin/help) for CRUD operations on help entries.
- **Help Flow (Other Roles)**: Non-Client, non-lab-technician, non-lab-manager, and non-administrator users see generic help message without API call.
- **Help Management (Admin CRUD)**: Administrators with config:edit permission can manage help entries via HelpManagement page → Frontend calls GET /help (no role filter) → Backend detects config:edit permission and returns ALL help entries (no role filtering) → Displays help entries in DataGrid with search and role filtering → Create/Edit via HelpEntryDialog (Formik form) → POST /help/admin/help (create), PATCH /help/admin/help/{id} (update), DELETE /help/admin/help/{id} (soft delete) → Backend validates role_filter against existing roles → RBAC enforces config:edit permission for all CRUD operations. Users with config:edit can optionally filter by role using `?role=` parameter to view specific role's help entries.
- **Tooltips**: Lab technicians see contextual tooltips in accessioning (QC: Blank—US-4) and results entry (Analytes: Rules) components. Lab Managers see tooltips in Results Management ("Review results: Use result:review permission") and Batch Results View ("QC at batch: US-27") for workflow guidance. Administrators see tooltip in CustomFieldsManagement ("Edit help: Use config:edit permission to manage help entries in Help Management").
- **Edit Flows (Samples)**: User navigates to `/samples` → Frontend calls GET /samples with pagination → Displays samples in DataGrid → User clicks "Edit" button → Frontend calls GET /samples/{id} → Pre-fills SampleForm with existing data → User modifies fields (name, description, status, custom_attributes) → Frontend validates custom attributes against active configs → User submits → Frontend calls PATCH /samples/{id} → Backend validates permissions (sample:update), checks project access via RLS, validates custom attributes, updates audit fields (modified_at, modified_by) → Returns updated sample → Frontend refreshes list. Edit form supports partial updates (only changed fields sent).
- **Edit Flows (Tests)**: User navigates to `/tests` → Frontend calls GET /tests with pagination → Displays tests in DataGrid → User clicks "Edit" button → Frontend calls GET /tests/{id} → Pre-fills TestForm with existing data → User modifies fields (status, technician_id, custom_attributes) → Frontend validates custom attributes → User submits → Frontend calls PATCH /tests/{id} → Backend validates permissions (test:update), checks project access via RLS, validates custom attributes, updates audit fields → Returns updated test → Frontend refreshes list.
- **Edit Flows (Containers)**: User navigates to `/containers` → Frontend calls GET /containers → Displays containers in DataGrid → User clicks "Edit" button → Frontend calls GET /containers/{id} → Pre-fills ContainerForm with existing data → User modifies fields (name, type_id, concentration, custom_attributes) → User submits → Frontend calls PATCH /containers/{id} → Backend validates permissions (sample:update, since containers link to samples), validates container type exists, updates audit fields → Returns updated container → Frontend refreshes list.

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
  - `battery_id` (FK test_batteries.id, nullable)
  - `status` (FK list_entries.id)
  - `review_date` (timestamp, nullable)
  - `test_date` (timestamp, nullable)
  - `technician_id` (FK users.id)
  - Notes: Optional battery_id links test to a test battery for grouped test assignment.

- **Results**:
  - `test_id` (FK tests.id)
  - `analyte_id` (FK analytes.id)
  - `raw_result` (varchar)
  - `reported_result` (varchar)
  - `qualifiers` (FK list_entries.id, nullable)
  - `calculated_result` (varchar, nullable)
  - `entry_date` (timestamp)
  - `entered_by` (FK users.id)

- **Test_Batteries**:
  - No additional fields beyond standard.
  - Notes: Groups of analyses that can be assigned together during accessioning. Admin-managed via UI/API.

- **Battery_Analyses** (Junction):
  - `battery_id` (FK test_batteries.id)
  - `analysis_id` (FK analyses.id, RESTRICT delete)
  - `sequence` (integer, >= 1, for ordering analyses)
  - `optional` (boolean, default false)
  - Composite primary key (battery_id, analysis_id)
  - Notes: Links analyses to batteries with sequence ordering and optional flag.

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

- **Help_Entries**:
  - `section` (varchar, NOT NULL): Help section name (e.g., 'Viewing Projects')
  - `content` (text, NOT NULL): Help content text
  - `role_filter` (varchar, nullable): Role name for filtering (NULL = public, visible to all roles)
  - Standard audit fields (id, name, description, active, created_at, created_by, modified_at, modified_by)
  - Notes: Role-filtered help content system. Users see entries where role_filter matches their role OR role_filter is NULL (public). RLS enforces filtering at database level. Name field uses section value (not unique).

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

### 3.5 EAV (Entity-Attribute-Value) Model

The EAV model enables administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requirements.

#### 3.5.1 Custom Attributes Configuration Table

- **custom_attributes_config**:
  - `id` (UUID PK)
  - `entity_type` (varchar, NOT NULL): Type of entity (e.g., 'samples', 'tests', 'results', 'projects', 'client_projects', 'batches')
  - `attr_name` (varchar, NOT NULL): Unique attribute name within entity type
  - `data_type` (varchar, NOT NULL): One of 'text', 'number', 'date', 'boolean', 'select'
  - `validation_rules` (JSONB, default '{}'): Validation rules specific to data type:
    - Text: `max_length`, `min_length`
    - Number: `min`, `max`
    - Select: `options` (array of strings)
  - `description` (text, nullable): Human-readable description
  - `active` (boolean, default true): Soft-delete flag
  - Standard audit fields (created_at, created_by, modified_at, modified_by)
  - Unique constraint: (`entity_type`, `attr_name`)

#### 3.5.2 Entity Custom Attributes Storage

The following tables include a `custom_attributes` JSONB column (default '{}'):
- `samples`
- `tests`
- `results`
- `projects`
- `client_projects`
- `batches`

**JSONB Column Structure**:
- Column: `custom_attributes` (JSONB, nullable, server_default='{}')
- Stores key-value pairs where keys match `attr_name` from `custom_attributes_config`
- Values validated against `data_type` and `validation_rules` on create/update

#### 3.5.3 Indexes

- **GIN Indexes**: Created on all `custom_attributes` JSONB columns for efficient querying:
  - `idx_samples_custom_attributes_gin`
  - `idx_tests_custom_attributes_gin`
  - `idx_results_custom_attributes_gin`
  - `idx_projects_custom_attributes_gin`
  - `idx_client_projects_custom_attributes_gin`
  - `idx_batches_custom_attributes_gin`
- **Configuration Table Indexes**:
  - `idx_custom_attributes_config_entity_type` (on `entity_type`)
  - `idx_custom_attributes_config_active` (on `active`)

#### 3.5.4 Querying Custom Attributes

Custom attributes can be queried using PostgreSQL JSONB operators:
- Exact match: `custom_attributes @> '{"attr_name": "value"}'::jsonb`
- Query parameters: `?custom.attr_name=value` (automatically parsed and applied in list endpoints)

**Example Query**:
```sql
SELECT * FROM samples 
WHERE custom_attributes @> '{"ph_level": 7.5}'::jsonb;
```

## 4. API Design

### 4.1 Authentication
- `/auth/login`: POST {username, password} → JWT token.
- `/auth/verify-email`: POST {email, token} → Confirm email.
- All endpoints: Require JWT; decode for user_id/role/permissions.

### 4.2 Key Endpoints
- **Samples**: 
  - GET /samples?project_id=...&status=...: List filtered by user access (query params accept UUIDs, empty strings converted to None).
  - POST /samples: Create sample (requires sample:create).
  - POST /samples/accession: Accession sample with test assignment (requires sample:create). Supports test batteries and individual analyses.
  - PATCH /samples/{id}: Update status/container (requires sample:update).
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
  - POST /analyses: Create analysis (admin, requires config:edit or test:configure).
  - PATCH /analyses/{id}: Update analysis (admin).
  - DELETE /analyses/{id}: Soft-delete analysis (admin).
  - GET /analyses/{id}/analytes: Get analytes for analysis.
  - PUT /analyses/{id}/analytes: Update analyte assignment (admin).
  - GET /analyses/{id}/analyte-rules: Get validation rules for analytes.
  - POST /analyses/{id}/analyte-rules: Create analyte rule (admin).
  - PATCH /analyses/{id}/analyte-rules/{analyte_id}: Update analyte rule (admin).
  - DELETE /analyses/{id}/analyte-rules/{analyte_id}: Delete analyte rule (admin).
- **Analytes**:
  - GET /analytes: List all active analytes.
  - POST /analytes: Create analyte (admin, requires config:edit or test:configure).
  - PATCH /analytes/{id}: Update analyte (admin).
  - DELETE /analytes/{id}: Soft-delete analyte (admin).
- **Test Batteries**:
  - GET /test-batteries: List batteries with filtering (name, pagination).
  - GET /test-batteries/{id}: Get battery with analyses.
  - POST /test-batteries: Create battery (admin, requires config:edit or test:configure).
  - PATCH /test-batteries/{id}: Update battery (admin).
  - DELETE /test-batteries/{id}: Soft-delete battery (admin, 409 if referenced).
  - GET /test-batteries/{id}/analyses: List analyses in battery.
  - POST /test-batteries/{id}/analyses: Add analysis to battery (admin).
  - PATCH /test-batteries/{id}/analyses/{analysis_id}: Update sequence/optional (admin).
  - DELETE /test-batteries/{id}/analyses/{analysis_id}: Remove analysis from battery (admin).
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
- **Users**:
  - GET /users: List users (admin, requires user:manage or config:edit).
  - POST /users: Create user (admin).
  - PATCH /users/{id}: Update user (admin).
  - DELETE /users/{id}: Soft-delete user (admin).
- **Roles**:
  - GET /roles: List roles (admin).
  - POST /roles: Create role (admin).
  - PATCH /roles/{id}: Update role (admin).
  - DELETE /roles/{id}: Soft-delete role (admin).
- **Permissions**:
  - GET /permissions: List all permissions (admin).
- **Custom Attributes Configuration**:
  - GET /admin/custom-attributes: List custom attribute configs with filtering (entity_type, active, pagination). Requires `config:edit` permission.
  - POST /admin/custom-attributes: Create new custom attribute config (requires `config:edit`).
  - GET /admin/custom-attributes/{id}: Get specific config (requires `config:edit`).
  - PATCH /admin/custom-attributes/{id}: Update config (requires `config:edit`).
  - DELETE /admin/custom-attributes/{id}: Soft-delete config (sets active=false, requires `config:edit`).
- **Custom Attributes in Entity Endpoints**:
  - All entity create/update endpoints (samples, tests, results, projects, client_projects, batches) accept `custom_attributes` in request body
  - List endpoints support filtering via query parameters: `?custom.attr_name=value`
  - Validation occurs server-side against active configs for the entity type
- **Help Endpoints**:
  - GET /help: List help entries filtered by current user's role (or ?role= for admins). Supports pagination and section filtering. Returns entries where role_filter matches user's role OR role_filter is NULL (public).
  - GET /help/contextual?section=: Get contextual help for a specific section, filtered by user's role.
  - POST /help/admin/help: Create help entry (requires `config:edit` permission).
  - PATCH /help/admin/help/{id}: Update help entry (requires `config:edit` permission).
  - DELETE /help/admin/help/{id}: Soft-delete help entry (requires `config:edit` permission).
- Error Handling: Standard HTTP codes; JSON {error, detail}.

### 4.3 Validation
- Backend: Use Pydantic for request schemas; custom validators for analyte rules.
- **Custom Attributes Validation**:
  - Server-side validation in `app.core.custom_attributes.validate_custom_attributes()`
  - Validates against active `custom_attributes_config` for entity type
  - Type checking: Ensures values match `data_type` (text, number, date, boolean, select)
  - Rule validation: Applies `validation_rules` (min/max, length, options)
  - Returns 400 error with detailed message if validation fails
  - Unknown attributes (not in config) are rejected
  - Inactive configs are ignored (attributes using inactive configs are rejected)
- Security: Dependency injection in FastAPI for permission checks (e.g., @requires_permission('sample:create')).

## 5. Frontend Implementation

### 5.1 Components
- **Auth**: Login form; email verification modal.
- **Dashboard**: Role-based views (e.g., client sees own projects).
- **Accessioning Form**: Multi-step wizard for sample entry/test assignment, with required container specification (select pre-setup type, create instance dynamically).
- **Batch View**: Select containers; grid for plate wells; result entry table.
- **Admin Section**: Dashboard with links to manage:
  - Lists and list entries (full CRUD)
  - Container types (CRUD)
  - Analyses (CRUD)
  - Analytes (CRUD)
  - Analysis-analyte rules (validation configuration)
  - Test batteries (CRUD with analysis grouping)
  - Custom Fields (CRUD for custom attribute configurations)
  - Users (CRUD)
  - Roles and permissions (CRUD)
  - Restricted to config:edit or specific permissions.
- **Custom Fields Management** (`CustomFieldsManagement.tsx`):
  - Admin page for managing custom attribute configurations
  - DataGrid with filtering by entity_type
  - CRUD dialogs for creating/editing custom fields
  - Supports all entity types: samples, tests, results, projects, client_projects, batches
  - Dynamic field rendering in forms based on configs
- **State Management**: Redux or Context API for user/session data.

### 5.2 UI/UX
- Responsive design; real-time validation (e.g., Formik/Yup).
- Accessibility: ARIA labels; WCAG compliance.

## 6. Workflows Implementation

- **Accessioning**: API sequence: POST /containers (dynamic instance creation), POST /contents (link to sample), POST /samples → POST /tests (individual) or POST /samples with battery_id (auto-creates sequenced tests). Requires specifying pre-setup container type.
- **Aliquots/Derivatives**: POST /samples with parent_id; inherit via backend logic; create new container instance dynamically.
- **Results Entry**: GET /batches/{id}/samples → POST /results with batch context.
- **Pooled Samples**: POST /contents; backend uses units multipliers for conversions (e.g., volume = amount / concentration, normalized to base units).
- **Configurable Workflows**: JSON-based configs in DB (post-MVP expansion).

## 7. Testing and Deployment

### 7.1 Testing
- Unit: Backend endpoints, validators; frontend components.
- Integration: API-DB interactions; auth flows.
- **EAV Testing**:
  - Integration tests in `test_eav_expansion.py`:
    - Custom attribute validation for all entity types
    - Cross-entity querying by custom attributes
    - Inactive config rejection
    - Type and rule validation (min/max, length, options)
  - Frontend tests for `CustomFieldsManagement.tsx`:
    - Dynamic field rendering
    - Form validation
    - API integration
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


# Post-MVP Technical Document for LIMS
## 1. Introduction
### 1.1 Purpose
This document details post-MVP technical enhancements for the LIMS, extending the MVP architecture to support bulk operations, advanced batching, and hierarchical client projects. It builds on the MVP tech stack (PostgreSQL, FastAPI, React) with minimal schema changes for scalability.
### 1.2 Scope
Focus on efficiency features like bulk accessioning and batch results entry, with integrations for cross-project workflows. Post-MVP expansions (e.g., instrument APIs) are noted.
### 1.3 Assumptions

Builds on MVP schema and RLS.
No new permissions; leverages existing 17.

### 1.4 Version History

Version 1.0: Initial post-MVP draft (December 28, 2025).

## 2. System Architecture Enhancements
### 2.1 Backend

New endpoints for bulk/batch operations (e.g., POST /samples/bulk-accession, POST /results/batch).
Transactions: Use SQLAlchemy sessions for atomic multi-record creates/updates.

### 2.2 Database

Add client_projects table: id (UUID PK), name (unique), description, client_id (FK), active, audit fields.
Update projects: Add client_project_id (FK nullable).
Add client_sample_id to samples (varchar unique nullable).
Migrations: Alembic for new tables/FKs.

### 2.3 Frontend

Bulk modes in wizards/tables using Formik arrays and MUI DataGrid.

## 3. API Endpoints Enhancements
Bulk Accessioning

POST /samples/bulk-accession: Accepts common fields + list of uniques; creates multiples atomically.

Client Projects

CRUD /client-projects: Standard operations with RLS via client_id.

Batch Enhancements

POST /batches: Support cross-project container_ids with compatibility validation.
Include qc_additions for auto-QC creation.
- Cross-Project Batching (US-26):
  - Accepts list of container_ids from multiple projects
  - Auto-detects cross-project mode
  - Validates compatibility: checks for shared analyses across all samples
  - RLS access check: uses has_project_access SQL function for all projects
  - Returns 400 error with details if incompatible (projects, analyses, suggestion)
  - Returns 403 error if user lacks access to any project
  - Supports divergent_analyses for future sub-batch creation
- QC at Batch Creation (US-27):
  - Accepts qc_additions list (each: qc_type UUID, optional notes)
  - Auto-generates QC samples/containers atomically within batch transaction
  - QC samples inherit: project_id, sample_type, matrix, temperature, due_date from first sample
  - Creates Contents junction linking QC sample to container
  - Creates BatchContainer junction linking QC container to batch
  - Validates QC type exists and is active
  - Enforces QC requirement if batch type in REQUIRE_QC_FOR_BATCH_TYPES env var
  - All operations wrapped in try/except with rollback on error
- Validation Endpoint:
  - POST /batches/validate-compatibility: Validates container compatibility without creating batch
  - Returns compatibility status with details or error message
  - Useful for frontend pre-validation before submission

Batch Results

POST /results/batch: List of results; updates statuses in transaction.
- US-28: Batch Results Entry endpoint
- Accepts batch_id and list of test results with analyte_results
- Validates permissions (result:enter, batch:read)
- Fetches all tests for samples in batch
- Validates each result against analysis_analytes rules (data type, range, sig figs, required)
- Creates/updates results in transaction
- Updates test statuses to 'Complete' when all analytes entered
- Auto-updates batch status to 'Completed' when all tests complete
- Sets batch end_date when batch completes
- QC validation: Checks QC samples for failures
- Configurable QC blocking via FAIL_QC_BLOCKS_BATCH env var
- Returns updated batch with containers
- Error handling: 400 for validation errors (detailed per row), rollback on error

## 4. Workflow Implementations

Bulk: Loop in transaction for creates.
Cross-Project: Query across accessible projects.
QC at Batch: Auto-create samples with qc_type.
Batch Results: Tabular entry with QC validation (flag/block configurable via env).

## 5. Security

Extend RLS: projects_access checks via client_projects.
No new permissions.

## 6. Testing and Deployment

Add bulk/cross-project tests.
Docker: No changes needed.