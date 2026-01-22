### Overview of Prompts for Cursor Implementation

Based on our ongoing planning discussions, the attached documents (PRD, User Stories, and Technical Document) provide a comprehensive blueprint for the NimbleLims. To align with the iterative approach and the sprint-based roadmap in the User Stories document, I've structured the prompts for Cursor below. Each prompt is self-contained, references the relevant sections from the documents, and focuses on one major aspect or sprint to allow for incremental development. This ensures we can refine and test each part before moving on.

These prompts emphasize:
- **API-first design**: All backend logic via FastAPI endpoints.
- **Tech stack**: PostgreSQL (schema with RLS, triggers), Python (FastAPI, SQLAlchemy, PyJWT, passlib[bcrypt]), React (with Axios, React Router, Material-UI).
- **Best practices**: PEP8 for Python, ESLint for React; unit/integration tests; Docker containerization (three containers: DB, backend, frontend).
- **Security**: JWT auth, RBAC with ~15 permissions, RLS for data isolation.
- **Iteration**: Build in layers, starting with data model and auth.

Use these prompts sequentially in Cursor, copying them directly into the editor's AI prompt interface. After each, review the generated code, commit to version control (e.g., Git), and we can discuss refinements here before proceeding.

#### Prompt 1: Project Setup and Docker Configuration
"Create the initial project structure for the NimbleLims based on the Technical Document (sections 1.3, 2.1, 7.2). Include:
- Root folder with subfolders: backend (Python/FastAPI), frontend (React), db (Postgres migrations/scripts).
- Docker setup with three containers: 
  - DB: PostgreSQL 15+ (official image, persistent volume for data, env vars for credentials).
  - Backend: Python 3.10+ (install deps like fastapi, uvicorn, sqlalchemy, psycopg2, pyjwt, passlib[bcrypt] via requirements.txt; expose port 8000; depend on DB).
  - Frontend: React 18+ (Node.js 18+; build with npm, serve via Nginx or Node; expose port 3000).
- docker-compose.yml: Define services, networks, volumes, dependencies (backend waits for DB); include healthchecks.
- .gitignore: Standard ignores for Python/Node.
- README.md: Brief setup instructions.
Ensure PEP8 and ESLint compliance in planning. Do not implement any code yet beyond setup files."

#### Prompt 2: Database Schema Implementation (Core Tables for Sprint 1)
"Implement the PostgreSQL database schema for the NimbleLims core tables as detailed in the Technical Document (section 3) and PRD (section 7.1), focusing on Sprint 1 user stories (US-1, US-5, US-7, US-12). Use SQL scripts for creation.
- Include standard fields on all tables: id (UUID PK), name (varchar unique), description (text), active (boolean default true), created_at (timestamp default NOW()), created_by (UUID FK users.id), modified_at (timestamp), modified_by (UUID FK users.id).
- Key tables: users (with username unique, password_hash, email unique, role_id FK roles.id, client_id FK clients.id nullable, last_login), roles, samples (due_date, received_date, report_date, sample_type FK list_entries.id, status FK, matrix FK, temperature numeric, parent_sample_id FK samples.id nullable, project_id FK projects.id, qc_type FK nullable), containers (row int default 1, column int default 1, concentration numeric, concentration_units FK units.id, amount numeric, amount_units FK units.id, type_id FK container_types.id, parent_container_id FK containers.id nullable), contents (container_id FK, sample_id FK, concentration numeric, concentration_units FK, amount numeric, amount_units FK; unique container_id+sample_id), container_types (capacity numeric, material varchar, dimensions varchar, preservative varchar), tests (sample_id FK, analysis_id FK analyses.id, status FK, review_date nullable, test_date nullable, technician_id FK users.id), analyses (method varchar, turnaround_time int, cost numeric), projects (start_date, client_id FK, status FK), clients (billing_info JSONB default '{}'), list_entries (list_id FK lists.id), lists, units (multiplier numeric, type FK list_entries.id).
- Indexes: On all FKs; unique on names.
- Triggers: For audit fields (e.g., BEFORE INSERT/UPDATE set created_at/modified_at).
- RLS: Basic policies, e.g., on samples: ENABLE ROW LEVEL SECURITY; CREATE POLICY user_access ON samples USING (project_id IN (SELECT project_id FROM project_users WHERE user_id = current_setting('app.current_user_id')::UUID));
- Use Alembic for migrations in backend/db/migrations.
Reference User Stories for fields like qc_type. Ensure normalized schema with cascades where appropriate."

#### Prompt 3: Backend Authentication and User Management (US-12)
"Implement the backend authentication for the NimbleLims using FastAPI, based on Technical Document (section 4.1) and User Stories (US-12, US-13).
- Setup: app/main.py with FastAPI app; routers for auth.
- Dependencies: SQLAlchemy ORM models from schema (users, roles, permissions, role_permissions); session dependency.
- Endpoints: POST /auth/login (body: username, password; verify with bcrypt, return JWT with user_id, role, permissions); POST /auth/verify-email (body: email, token; stub for now).
- JWT: Use PyJWT; encode/decode with secret; validate in dependencies.
- RBAC: Define ~15 permissions (e.g., 'sample:create', 'result:enter') in DB; load user permissions from role_permissions.
- Security: Dependency for current_user; set current_user_id in DB session for RLS.
- Tests: Pytest for login success/failure, token validation.
Follow PEP8; include Pydantic schemas for requests/responses."

#### Prompt 4: Backend Endpoints for Samples, Containers, and Tests (Sprint 1: US-1, US-5, US-7)
"Build FastAPI backend endpoints for samples, containers, and tests in the NimbleLims, aligning with Technical Document (section 4.2) and User Stories (US-1, US-5, US-7).
- Models: SQLAlchemy for samples, containers, contents, tests, etc.
- Endpoints:
  - Samples: GET /samples (filtered by project_id, status; scoped by user); POST /samples (create with accessioning data, validate fields); PATCH /samples/{id} (update status/container).
  - Containers: POST /containers (create with type, parent); POST /contents (link sample to container with concentration/amount/units).
  - Tests: POST /tests (assign analysis to sample, set status 'In Process').
- Validation: Pydantic for bodies; custom for required fields (e.g., due_date).
- RBAC: Dependencies like @requires_permission('sample:create').
- Logic: On create, set audit fields; handle hierarchies in containers.
- Tests: Pytest for CRUD, validation errors.
Ensure API-first; JSON responses; HTTP error handling."

#### Prompt 5: Frontend Setup and Auth Components (US-12)
"Create the React frontend setup and authentication components for the NimbleLims, based on Technical Document (section 5) and User Stories (US-12).
- Setup: Create React app with React Router, Axios (for API calls to backend at http://localhost:8000), Material-UI for styling; state management with Context API (for user/session).
- Components: Login form (username/password, call POST /auth/login, store JWT in localStorage); Email verification modal (POST /auth/verify-email).
- Routing: Protected routes with auth check (decode JWT).
- UI: Responsive; Formik/Yup for validation.
- Tests: Jest for components.
Follow ESLint; include axios interceptors for JWT headers."

#### Prompt 6: Frontend Components for Sample Accessioning and Management (Sprint 1: US-1, US-5, US-7)
"Implement React frontend components for sample accessioning, container management, and test assignment in the NimbleLims, per User Stories (US-1, US-5, US-7) and Technical Document (section 5.1).
- Components: Accessioning form (multi-step wizard: fields like due_date, sample_type; optional double-entry; assign tests; submit to POST /samples then /tests); Container assignment (select type, add contents); Dashboard view (list samples filtered by status/project).
- Integration: Axios calls to backend endpoints; real-time validation.
- State: Use Context for user data; handle loading/errors.
- UI: Material-UI forms/tables; accessibility with ARIA.
- Tests: Jest for form submission, rendering.
Ensure alignment with workflows in PRD section 5.1."

#### Prompt 7: Backend and DB for Aliquots, Pooling, Results, Batches (Sprint 2: US-3, US-6, US-9, US-11)
"Extend the FastAPI backend and Postgres schema for aliquots/derivatives, pooling, results entry, and batches in the NimbleLims, based on User Stories (Sprint 2) and Technical Document (sections 3,4).
- Schema additions: Batches (type FK, status FK, dates); batch_containers (batch_id FK, container_id FK, position, notes); results (test_id FK, analyte_id FK analytes.id, raw_result, reported_result, qualifiers FK, calculated_result nullable, entry_date, entered_by FK).
- Endpoints: POST /samples/aliquot or /derivative (with parent_id, inherit properties); POST /contents (for pooling, compute volumes using units multipliers); POST /batches (create, add containers via /batch-containers); POST /results (batch-based, validate per analysis_analytes).
- Logic: Conversions (e.g., volume = amount / concentration, normalized via multipliers); update statuses.
- RBAC: Permissions like 'sample:create', 'result:enter'.
- Tests: Pytest for calculations, creations.
Update Alembic migrations."

#### Prompt 8: Frontend for Aliquots, Batches, and Results (Sprint 2)
"Add React components for aliquots/derivatives, batches, and results entry in the NimbleLims frontend, aligning with User Stories (Sprint 2) and Technical Document (section 5).
- Components: Aliquot/Derivative creation form (select parent, submit to POST /samples/...); Batch view (create batch, add containers, grid for plates/wells); Results entry table (select batch/test, enter per analyte, validation).
- Integration: Axios to new endpoints; handle pooling calculations display.
- UI: Tables for batches; real-time updates.
- Tests: Jest for workflows."

#### Prompt 9: Backend RBAC, Data Isolation, and Configurations (Sprint 3: US-13, US-14, US-15, US-16)
"Implement full RBAC, data isolation, and configurations in the FastAPI backend for NimbleLims, per User Stories (Sprint 3) and Technical Document (sections 3.2,4.3).
- Schema: Permissions, role_permissions; project_users (project_id FK, user_id FK, access_level FK, granted_at, granted_by FK); update RLS policies for all tables (e.g., using current_user_id).
- Endpoints: CRUD /roles, /permissions, /lists, /units (admin-only); all queries filter by user context (e.g., client_id).
- RBAC: Dependency injection for permission checks; load permissions on login.
- Configurations: Manage lists/list_entries, units with multipliers/types.
- Tests: Pytest for access denials, configs."

#### Prompt 10: Frontend for Security and Configurations (Sprint 3)
"Extend React frontend for RBAC management and configurations in NimbleLims, based on User Stories (Sprint 3).
- Components: Admin dashboard for roles/permissions CRUD; Config forms for lists/units.
- Integration: Role-based views (e.g., client sees only own projects); Axios with permission checks.
- UI: Conditional rendering based on user role."

#### Prompt 11: Backend and Frontend for Statuses, QC, Reviews (Sprint 4: US-2, US-4, US-8, US-10)
"Complete backend and frontend for status management, QC handling, and reviews in NimbleLims, per User Stories (Sprint 4).
- Backend: PATCH endpoints for statuses (samples/tests); include qc_type in samples; PATCH /tests/{id}/review.
- Frontend: Update forms/views for statuses, QC flags, review workflows.
- Tests: Full coverage."

#### Prompt 12: Testing, Deployment, and Polish
"Add testing and finalize deployment for NimbleLims, based on Technical Document (section 7).
- Tests: Pytest (backend unit/integration), Jest (frontend), Cypress (E2E).
- Deployment: Update docker-compose for prod; CI/CD stubs in GitHub Actions.
- Polish: Error handling, logging (Sentry stub), migrations."

Once you've run these in Cursor and have the code base, we can resume here to summarize decisions or refine based on any issues. What's one specific aspect you'd like to clarify or adjust before proceeding to implementation?





# Admin Prompts
Thank you for confirming the refinements in our Version 1.6 summary—this gives us a strong foundation to move forward with the admin functionality planning. With container handling locked in (admin pre-setup for types, dynamic instances during workflows) and lists set for full editable CRUD, we can now outline the Cursor prompts to generate the admin web pages. This aligns with the updated "lims_mvp_tech.md" (Version 1.3), where we've enhanced the frontend components (Section 5.1) and API endpoints (Section 4.2) to support these features.
To keep our iteration focused, I'll provide the prompts below, structured sequentially for use in Cursor. Each one is self-contained, references the tech doc and related files (e.g., "lists.md", "containers.md"), and emphasizes RBAC (config:edit permission), Material-UI for UI, Axios for API calls, and separation from workflows like accessioning or results. They generate full files/components to adhere to our code style planning.
If these prompts meet your needs, you can copy-paste them directly into Cursor's AI interface. After generation, we can discuss testing or integration details in the next iteration.

Cursor Prompt 1: Admin Dashboard and Routing
"Extend the React frontend for the NimbleLims by adding an admin dashboard section, based on the Technical Document (Version 1.3, sections 4.2, 5.1) and User Stories (US-13, US-15). Focus on admin-only configuration for lists and container types.

Setup: Add protected /admin route in React Router; use Context API to check for admin role/permission (config:edit) from JWT decode; redirect non-admins.
Components: Create AdminDashboard.tsx as the entry point with sidebar navigation (Material-UI Drawer) linking to Lists Management and Container Types Management.
UI: Responsive layout; AppBar with logout and user role display; overview cards for quick stats (e.g., number of lists, container types).
Integration: Axios interceptors for JWT; global error handling with Alerts.
RBAC: All admin routes require config:edit; 403 handling.
Tests: Jest for rendering, navigation, and permission checks.
Files: Generate full code for src/pages/AdminDashboard.tsx, and update src/App.tsx for routing.
Follow ESLint; ensure no workflow ties (e.g., no accessioning components)."

Cursor Prompt 2: Lists Management Page
"Implement the React frontend component for full editable lists management in the NimbleLims admin section, per lists.md (CRUD for lists and entries with normalized naming) and Technical Document (Version 1.3, section 4.2 for endpoints).

Component: Create ListsManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing all lists (columns: name, description, entry count); buttons for create/edit/delete lists.
Forms: Dialogs for new/edit list (fields: name, description; auto-normalize to slug); nested grid/dialog for entries per list (name, description; CRUD with uniqueness validation).
Integration: Axios calls to GET /lists (fetch), POST/PATCH/DELETE /lists/{id}, GET/POST/PATCH/DELETE /lists/{list_name}/entries; handle soft deletes (active flag), 404/400 errors, and loading states.
Validation: Formik/Yup for unique names; confirm deletes to avoid data impacts.
UI: Search/filter in grid; expandable rows for entries.
RBAC: Restricted to config:edit; view-only fallback if lacking permission.
Tests: Jest for CRUD flows, form validation, API mocks.
Files: Generate full code for src/pages/admin/ListsManagement.tsx and helpers (e.g., ListFormDialog.tsx, EntryFormDialog.tsx).
Ensure separation: Changes apply system-wide but no real-time workflow updates in MVP."

Cursor Prompt 3: Container Types Management Page
"Add a React frontend component for managing container types in the NimbleLims admin section, per containers.md (pre-setup types with fields: name, description, capacity, material, dimensions, preservative) and Technical Document (Version 1.3, section 4.2 for endpoints).

Component: Create ContainerTypesManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing types (columns for all fields); CRUD buttons.
Forms: Dialog for new/edit type (fields as documented; validation: unique name, positive capacity, required material/dimensions).
Integration: Axios to GET /containers/types (fetch), POST /containers/types, PATCH /containers/types/{id}, DELETE /containers/types/{id} (soft delete); handle errors and loading.
Validation: Formik/Yup for constraints; confirm deletes if type is referenced (backend check).
UI: Edit/delete icons per row; search/filter.
RBAC: Requires config:edit; error alerts for unauthorized.
Tests: Jest for CRUD, validation, grid interactions.
Files: Generate full code for src/pages/admin/ContainerTypesManagement.tsx and helpers (e.g., ContainerTypeForm.tsx).
Clarify: Types pre-setup here for use in dynamic instance creation (e.g., during accessioning); no instance management in MVP admin."

Cursor Prompt 4: Accessioning Integration for Container Specification
"Refine the React frontend accessioning form in the NimbleLims to require container specification during sample receipt, based on accessioning_workflow.md, containers.md, and Technical Document (Version 1.3, section 6).

Component: Update SampleDetailsStep.tsx and AccessioningForm.tsx; add required section for container: dropdown of pre-setup types (fetch via GET /containers/types), fields for new instance (name/barcode, row/column, concentration/amount/units from GET /units).
Flow: On submit, POST /containers (create instance), POST /contents (link sample), POST /samples; no pre-existing instances.
Validation: Ensure type exists; positive values; Formik/Yup.
UI: Material-UI Select for types; conditional fields for instance details.
Tests: Jest for form updates, submission sequence.
Files: Generate full updated code for src/components/accessioning/SampleDetailsStep.tsx and src/pages/AccessioningForm.tsx.
Reinforce: No results/approval here; keep separate from admin configs."

Prompt 5: User Management Page
"Add a React frontend component for managing users in the NimbleLims admin section, per the Technical Document (Version 1.4, sections 3.1, 4.2 for users table/endpoints) and User Stories (US-13).

Component: Create UsersManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing users (columns: username, email, role, client_id, last_login); CRUD buttons.
Forms: Dialog for new/edit user (fields: username, email, password (on create), role_id dropdown from GET /roles, client_id dropdown from GET /clients); handle password hashing via backend.
Integration: Axios to GET /users (fetch with filters), POST /users, PATCH /users/{id}, DELETE /users/{id} (soft delete); include role assignment via /users/{id}/roles.
Validation: Formik/Yup for uniqueness (username/email), required fields; confirm deletes if user has active assignments.
UI: Search/filter in grid; edit/delete icons per row; loading/error states.
RBAC: Requires user:manage or config:edit; error if unauthorized.
Tests: Jest for CRUD flows, form validation, API mocks.
Files: Generate full code for src/pages/admin/UsersManagement.tsx and helpers (e.g., UserFormDialog.tsx).
Clarify: Integrate with admin dashboard navigation; no self-demotion checks in frontend (handle backend)."

Prompt 6: Role and Permission Management Page
"Implement a React frontend component for managing roles and permissions in the NimbleLims admin section, aligning with the Technical Document (Version 1.4, sections 3.1, 4.2 for roles/permissions tables/endpoints) and User Stories (US-13).

Component: Create RolesManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing roles (columns: name, description, permission count); CRUD buttons, with nested view for permissions.
Forms: Dialog for new/edit role (fields: name, description); checkbox list for permissions (fetch via GET /permissions, assign via role_permissions junction).
Integration: Axios calls to GET /roles (fetch), POST/PATCH/DELETE /roles/{id}, GET /permissions, POST/PATCH/DELETE /permissions/{id}; manage assignments with /roles/{id}/permissions.
Validation: Formik/Yup for unique role names; confirm deletes if role is assigned to users.
UI: Expandable rows for permission details; search/filter; loading states.
RBAC: Restricted to user:manage or config:edit; view-only if lacking full access.
Tests: Jest for CRUD, permission assignment, grid interactions.
Files: Generate full code for src/pages/admin/RolesManagement.tsx and helpers (e.g., RoleFormDialog.tsx, PermissionSelector.tsx).
Ensure separation: No direct ties to workflows; preview role impacts before save."

Prompt 7: Analyses Management Page
"Add a React frontend component for managing analyses (tests) in the NimbleLims admin section, per the Technical Document (Version 1.5, sections 3.1, 4.2 for analyses table/endpoints) and User Stories (US-7, US-15).

Component: Create AnalysesManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing analyses (columns: name, method, turnaround_time, cost, analyte count); CRUD buttons.
Forms: Dialog for new/edit analysis (fields: name, method, turnaround_time (days, positive int), cost (numeric >=0)); nested section for assigning analytes via multi-select (fetch from GET /analytes).
Integration: Axios to GET /analyses (fetch active), POST /analyses, PATCH /analyses/{id}, DELETE /analyses/{id} (soft delete); manage analytes with POST/PATCH/DELETE /analyses/{id}/analytes.
Validation: Formik/Yup for uniqueness (name), required fields; confirm deletes if referenced in tests.
UI: Search/filter in grid; expandable rows for analyte details; loading/error states.
RBAC: Requires config:edit or test:configure; error if unauthorized.
Tests: Jest for CRUD flows, form validation, API mocks.
Files: Generate full code for src/pages/admin/AnalysesManagement.tsx and helpers (e.g., AnalysisFormDialog.tsx).
Clarify: Integrate with admin dashboard navigation; seeded data (e.g., pH, EPA 8080) appears on load; no direct workflow ties."

Prompt 8: Analytes Management Page
"Implement a React frontend component for managing analytes in the NimbleLims admin section, aligning with the Technical Document (Version 1.5, sections 3.1, 4.2 for analytes table/endpoints) and User Stories (US-9, US-15).

Component: Create AnalytesManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing analytes (columns: name, description); CRUD buttons.
Forms: Dialog for new/edit analyte (fields: name, description); keep simple as rules are set in analysis_analytes junctions.
Integration: Axios calls to GET /analytes (fetch), POST /analytes, PATCH /analytes/{id}, DELETE /analytes/{id} (soft delete); handle 404/400 errors.
Validation: Formik/Yup for unique names; confirm deletes if referenced in analyses.
UI: Search/filter in grid; loading states.
RBAC: Restricted to config:edit or test:configure; view-only fallback.
Tests: Jest for CRUD, validation, grid interactions.
Files: Generate full code for src/pages/admin/AnalytesManagement.tsx and helpers (e.g., AnalyteFormDialog.tsx).
Ensure separation: Analytes reusable across analyses; seeded examples (e.g., pH, Aldrin) load initially."

Prompt 9: Analysis Analytes Configuration (Junction Management)
"Add a React frontend component for configuring analysis-analytes relationships in the NimbleLims admin section, based on the Technical Document (Version 1.5, sections 3.1, 4.2 for analysis_analytes junction) and User Stories (US-9).

Component: Create AnalysisAnalytesConfig.tsx under src/pages/admin/; accessible from AnalysesManagement (e.g., via expandable row or link); Material-UI DataGrid for listing analytes per analysis (columns: analyte_name, data_type, high/low, sig_figs, is_required).
Forms: Dialog for adding/editing junction (fields: analyte_id dropdown from GET /analytes, data_type (from lists), high/low (numeric), sig_figs (int >0), is_required (bool), optional calculation/reported_name).
Integration: Axios to GET /analyses/{id}/analytes, POST /analyses/{id}/analytes, PATCH /analyses/{id}/analytes/{analyte_id}, DELETE /analyses/{id}/analytes/{analyte_id}.
Validation: Formik/Yup for ranges (e.g., low <= high), required fields; backend handles uniqueness.
UI: Per-analysis view; edit/delete icons; search/filter.
RBAC: Requires config:edit or test:configure.
Tests: Jest for junction CRUD, validation.
Files: Generate full code for src/pages/admin/AnalysisAnalytesConfig.tsx and helpers (e.g., AnalyteRuleForm.tsx).
Note: Units/lists integration for measurements; seeded junctions (e.g., pH rules) appear on load."

Prompt 10: Schema Modifications (New Migration File)
"Generate a new Alembic migration file for adding test batteries to the NimbleLims schema, per the Technical Document (Version 1.8, section 3.1 refinements) and considerations (new test_batteries table with name, description, active, audit fields; battery_analyses junction with battery_id, analysis_id, sequence/order int, optional flag bool).

Migration: Name it 0010_add_test_batteries.py; revises 0009; include upgrade() to create tables with UUID PKs, FKs (to analyses.id with RESTRICT delete), unique constraints (battery name), and indexes (on battery_id in tests table, composite on battery_analyses).
Downgrade: Drop tables/junction in reverse.
Seeding: Include basic seed data in upgrade() (e.g., battery 'EPA 8080 Full' grouping prep and analytical analyses from 0009, with sequence and optional prep flag).
Files: Generate the full migration code for backend/db/migrations/versions/0010_add_test_batteries.py.
Follow Alembic best practices; ensure no disruptions to existing tables like analyses or tests."

Prompt 11: Backend Functionality (Models, Schemas, Routers)
"Implement backend functionality for test batteries in the NimbleLims, based on the Technical Document (Version 1.8, sections 3.1, 4.2) and new schema from migration 0010.

Models: Add TestBattery and BatteryAnalysis models in backend/models/test_battery.py (inherit BaseModel; TestBattery with name unique, description; BatteryAnalysis with sequence int >=1, is_optional bool default False).
Schemas: Create Pydantic schemas in backend/app/schemas/test_battery.py (e.g., TestBatteryCreate, TestBatteryResponse, BatteryAnalysisCreate with validations like unique analyses per battery).
Routers: Add router in backend/app/routers/test_batteries.py with endpoints: GET /test-batteries (list active, filter by name), POST /test-batteries (create, require config:edit), PATCH/DELETE /test-batteries/{id} (update/soft delete, check references), and sub-routes for /test-batteries/{id}/analyses (CRUD junction with sequence/optional).
Integration: Add optional battery_id to Test model/schema; update accessioning router (samples.py) to handle battery assignment (auto-create sequenced tests).
RBAC: Dependency checks for test:configure or config:edit.
Files: Generate full code for backend/models/test_battery.py, backend/app/schemas/test_battery.py, backend/app/routers/test_batteries.py; minor updates to test.py and samples.py for integration.
Ensure API-first; handle errors like 409 for referenced deletes."

Prompt 12: Admin Page for Test Batteries
"Create the React frontend admin page for managing test batteries in the NimbleLims, aligning with the Technical Document (Version 1.8, section 5.1) and User Stories (US-15, US-7 for assignment integration).

Component: Create TestBatteriesManagement.tsx under src/pages/admin/; Material-UI DataGrid for listing batteries (columns: name, description, analysis count); CRUD buttons, with expandable rows for analyses.
Forms: Dialog for new/edit battery (fields: name unique, description); nested multi-select for analyses (fetch GET /analyses), with sequence input (int) and optional toggle (bool) per analysis.
Integration: Axios to GET /test-batteries (fetch), POST/PATCH/DELETE /test-batteries/{id}, and /test-batteries/{id}/analyses for junctions; handle loading/errors.
Validation: Formik/Yup for uniqueness, at least one analysis, sequence >0; confirm deletes if referenced.
UI: Drag-and-drop for sequence reordering; search/filter; integrate with dashboard navigation.
RBAC: Requires config:edit or test:configure; view-only fallback.
Tests: Jest for CRUD, validation, interactions.
Files: Generate full code for src/pages/admin/TestBatteriesManagement.tsx and helpers (e.g., BatteryFormDialog.tsx, AnalysisSelector.tsx).
Note: Seeded batteries (e.g., EPA 8080 Full) load initially; no direct accessioning here—separate workflow pulls from these configs."





# Docker Secrets:  not iplemented
Prompt 1: Update docker-compose.yml for Secrets Support
"Refine the docker-compose.yml file in the NimbleLims project root to add support for Docker secrets, based on the Technical Document (Sections 7.2 and 2.1 for security). Keep compatibility with .env files for local development.

Add a top-level 'secrets' section defining external secrets: db_password, jwt_secret_key (mark as external: true for Swarm compatibility).
In the db service: Reference db_password as a secret (e.g., environment: POSTGRES_PASSWORD_FILE=/run/secrets/db_password).
In the backend service: Mount secrets as files (e.g., secrets: - db_password, - jwt_secret_key; then in environment, use DATABASE_URL with a placeholder, but prepare for file-based reading in code).
Keep existing env_file: .env for dev fallback; add comments explaining dev vs. prod usage (e.g., 'For production, use Docker secrets and remove env_file').
Include a new docker-compose.prod.yml file that overrides to use secrets only (no env_file), with services depending on secrets.
Ensure healthchecks and dependencies remain intact; no changes to frontend (as it doesn't handle sensitive creds directly).
Update README.md to include instructions: For dev, use docker-compose up; for prod simulation, docker swarm init, create secrets, then docker stack deploy -c docker-compose.prod.yml lims.
Do not alter existing files beyond these; ensure YAML formatting is valid."

Prompt 2: Adjust Backend to Read Credentials from Secret Files
"Update the backend code in the NimbleLims to read credentials from Docker secret files when available, falling back to environment variables for dev, aligning with Technical Document (Section 2.1 for security) and PRD (Section 6.1).

In backend/app/config.py (or create if missing): Add logic to load secrets like DB_PASSWORD and JWT_SECRET_KEY—check for files like '/run/secrets/db_password' and read if exists (e.g., using with open() as f: value = f.read().strip()), else os.environ.get().
Construct DATABASE_URL dynamically: f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'.
Update main.py or dependencies to use this config; ensure JWT setup (PyJWT) pulls from the loaded JWT_SECRET_KEY.
Handle errors gracefully (e.g., raise ValueError if neither file nor env var is set).
Add a note in requirements.txt if any new deps are needed (none expected).
Tests: Add a simple pytest in backend/tests/test_config.py to mock file/env loading scenarios.
Generate full code for updated/new files: config.py, and patches to main.py."

Prompt 3: Update DB Initialization and Migrations for Secret Compatibility
"Enhance the db service and migrations in the NimbleLims to work with secret files for credentials, per Technical Document (Section 7.2).

In db/Dockerfile (or update if using official image): No major changes needed, but ensure entrypoint can handle _FILE suffixes (Postgres supports POSTGRES_PASSWORD_FILE).
In backend/db/migrations (Alembic): Ensure init scripts or env.py load DB creds via the new config.py from Prompt 2.
Update start.sh in backend (if exists) to wait for DB using the dynamic URL.
Add logging in backend to confirm credential source (e.g., 'Loaded DB_PASSWORD from secret file' or 'from env').
Generate full code for any updated files, like env.py in migrations."

# Sprint 5
## Prompt 25: Database Schema Enhancements for Client Projects and Bulk Support
"Based on the Post-MVP Technical Document (sections 2.2 and 6) and US-25 in Post-MVP User Stories, implement schema changes for client projects using Alembic migrations in the LIMS project.
In backend/migrations/versions/, create a new migration file (e.g., 0012_add_client_projects.py) to:

Create client_projects table: id (UUID PK default uuid_generate_v4()), name (String unique not null), description (Text nullable), client_id (UUID FK to clients.id not null), active (Boolean default True), created_at (TIMESTAMP default now()), created_by (UUID FK to users.id), modified_at (TIMESTAMP), modified_by (UUID FK to users.id).
Add client_project_id column to projects table (UUID FK to client_projects.id nullable).
Add client_sample_id column to samples table (String unique nullable).
Add indexes: unique on client_projects.name, FK indexes.
In upgrade(): Use op.create_table, op.add_column.
In downgrade(): Reverse operations.

Update backend/models/project.py and backend/models/sample.py to include new fields/relationships (e.g., projects.client_project = relationship('ClientProject')).
Ensure RLS policies in schema_dump are extended: Update projects_access to check via client_projects if client_project_id is set.
No data seeding yet—handle in later prompt.
Generate full code for the migration file and model updates."

## Prompt 26: Backend API for Client Projects CRUD
"Implement CRUD endpoints for client projects as per US-25 in Post-MVP User Stories and Post-MVP PRD (section 4.2), using FastAPI in the LIMS backend.
In backend/app/routers/client_projects.py (create if missing):

Import dependencies: db session, current_user, schemas (new ClientProjectCreate, ClientProjectUpdate, ClientProjectResponse).
GET /client-projects: List all accessible (filter by client_id for non-admins via RLS; paginate with query params page/size).
POST /client-projects: Create (require project:manage; set audit fields).
GET /client-projects/{id}: Read one (404 if not found).
PATCH /client-projects/{id}: Update (partial; audit modified).
DELETE /client-projects/{id}: Soft-delete (set active=False).
Schemas in backend/app/schemas/client_project.py: Pydantic models with validators (e.g., name 1-255 unique).

In main.py, include_router for client_projects.
Add tests in backend/tests/test_client_projects.py: Cover CRUD, permissions, RLS.
Reference MVP security (JWT, RBAC).
Generate full code for routers/client_projects.py, schemas/client_project.py, and test file."

## Prompt 27: Frontend UI for Client Project Management
"Develop React components for client project management based on US-25 in Post-MVP User Stories and Post-MVP PRD (section 4.2).
In frontend/src/pages/ClientProjects.tsx: List view with MUI DataGrid (columns: name, description, client name via join, status); filters by client_id; buttons for create/edit/delete (modals).
In frontend/src/components/client-projects/ClientProjectForm.tsx: Formik form for CRUD (fields: name, description, client_id dropdown from /clients, status from lists).
Update apiService.ts: Add methods like getClientProjects(filters), createClientProject(data), etc.
Integrate with UserContext for permissions (project:manage).
Add navigation in App.tsx or sidebar.
Tests in ClientProjects.test.tsx: Render, interactions, API mocks.
Generate full code for new pages/components, apiService updates, and tests."

## Prompt 28: Bulk Accessioning Backend API
"Implement bulk accessioning endpoint as per US-24 in Post-MVP User Stories and Post-MVP Technical Document (section 3).
In backend/app/routers/samples.py: Add POST /samples/bulk-accession.

Schema: BulkSampleAccessioningRequest (common: SampleAccessioningRequest fields; uniques: list of dicts with name, client_sample_id, container_name, overrides).
Processing: Validate permissions/project access; loop in transaction to create samples/containers/contents/tests (use bulk_insert for efficiency); auto-name if option provided.
Response: List of SampleResponse.
Error: 400 for duplicates/invalids; rollback.
Update existing accession_sample to share logic where possible.
Tests in test_samples.py: Add bulk scenarios.
Generate full code for endpoint, schema, and tests."

## Prompt 29: Bulk Accessioning Frontend UI
"Enhance accessioning UI for bulk mode based on US-24 in Post-MVP User Stories and Post-MVP PRD (section 4.1).
In frontend/src/pages/AccessioningForm.tsx: Add bulk toggle; common fields section; unique table (MUI DataGrid editable, add/remove rows).
Update SampleDetailsStep.tsx and TestAssignmentStep.tsx for bulk (Formik arrays for uniques).
In apiService.ts: Add bulkAccessionSamples(data) calling /samples/bulk-accession.
ReviewStep.tsx: Summary table for bulk.
Tests in AccessioningForm.test.tsx: Bulk mode interactions.
Generate full code for updated pages/components and tests."
Prompt 30: Integration and Workflow Updates for Sprint 5
"Integrate Sprint 5 features (bulk accessioning, client projects) into workflows, per Post-MVP PRD (section 4) and User Stories.
Update backend/app/routers/samples.py accession to optionally link client_project_id.
Enhance frontend accessioning to include client project dropdown (fetch from /client-projects).
Add docs updates: In workflow-accessioning-to-reporting.md, add Variation 5: Bulk Accessioning; update Stage 1 for client projects.
Tests: End-to-end for bulk with client projects.
Generate full code for integrations, doc patches, and tests."

# Sprint 6
## Prompt 31: Backend API Enhancements for Cross-Project Batching
"Implement cross-project batching as per US-26 in Post-MVP User Stories and Post-MVP Technical Document (section 3, Batch Enhancements).
In backend/app/routers/batches.py: Update POST /batches to accept list of container_ids (cross-project); validate compatibility (e.g., query tests for shared analysis_id like 'EPA Method 8080 Prep').

Add dependency to check RLS-accessible projects via has_project_access.
If incompatible, raise 400 with details.
Option for split: If provided (e.g., divergent_analyses list), create sub-batches (future: child_batch_id FK, but stub for now).
Schema: Update BatchCreate to include cross_project flag or auto-detect.
Response: BatchResponse with included containers.

Add tests in backend/tests/test_batches.py: Cross-project creation, compatibility validation, RLS denial.
Generate full code for updated router, schema, and tests."

## Prompt 32: Backend API for QC Addition at Batch Creation
"Add QC sample creation during batching per US-27 in Post-MVP User Stories and Post-MVP Technical Document (section 3).
In backend/app/routers/batches.py: Enhance POST /batches with qc_additions list (each: qc_type UUID, optional notes).

For each, auto-create QC sample/container (inherit project_id from first sample or batch-level; set qc_type).
Link to batch via batch_containers.
Configurable requirement: Env var REQUIRE_QC_FOR_BATCH_TYPES (list of type UUIDs); enforce if matches.
Transaction: Atomic with batch creation.
Schema: Add qc_additions to BatchCreate (list of dicts: qc_type, notes).

Update tests in test_batches.py: QC creation scenarios, requirement enforcement.
Generate full code for updated endpoint, schema, and tests."

## Prompt 33: Frontend UI for Cross-Project Batching
"Enhance batch creation UI for cross-project support based on US-26 in Post-MVP User Stories.
In frontend/src/pages/BatchManagement.tsx (create if missing) or ResultsManagement.tsx: Add search/filter for containers across projects (dropdown or Autocomplete fetching from /containers?project_ids=multiple via query).

Validate compatibility on add (API call to /batches/validate-compatibility with container_ids; return errors).
Split option: Button to create sub-batches (modal with divergent steps).
Use UserContext for accessible projects.

Update apiService.ts: Add validateBatchCompatibility(data), createBatch with cross-project support.
Tests in BatchManagement.test.tsx: Multi-project selection, validation.
Generate full code for updated pages/components, apiService, and tests."

## Prompt 34: Frontend UI for QC Addition at Batch Creation
"Add QC integration to batch UI per US-27 in Post-MVP User Stories.
In frontend/src/components/batches/BatchForm.tsx (create if missing): Add QC section (dropdown for qc_type from /lists/qc_types/entries; add multiple via '+ Add QC' button; fields: type, notes).

Auto-generate on submit (include in createBatch payload).
Required toggle based on batch_type (fetch config or client-side check).
Display in batch view with highlights.

Update apiService.ts: Enhance createBatch to include qc_additions.
Tests: QC addition, requirement validation.
Generate full code for new/updated components, apiService, and tests."

## Prompt 35: Integration and Workflow Updates for Sprint 6
"Integrate Sprint 6 features (cross-project batching, QC at batch) into overall system, per Post-MVP PRD (section 4.3) and User Stories.
Update backend/app/routers/batches.py to handle QC in transaction (create samples/containers, link).
Enhance frontend batch creation to combine cross-project and QC (e.g., suggest QC based on batch size/type).
Doc updates: In workflow-accessioning-to-reporting.md, enhance Stage 2 for cross-project and QC; add notes to technical doc for API/validation.
Tests: End-to-end for batch with cross-project/QC.
Generate full code for integrations, doc patches, and tests."

# Sprint 7
## Prompt 36: Backend API for Batch Results Entry
"Implement batch results entry endpoint as per US-28 in Post-MVP User Stories and Post-MVP Technical Document (section 3, Batch Results).
In backend/app/routers/results.py (create if missing): Add POST /results/batch.

Schema: BatchResultsEntryRequest (batch_id UUID, results list: each with test_id, analyte_results dict (analyte_id: value, qualifiers, notes)).
Processing: Validate permissions (result:enter); fetch batch tests/analytes; create/update results in transaction; run validations (data type, range, sig figs from analysis_analytes); update test statuses to 'Complete' if all analytes entered; QC checks (e.g., flag/block if failing, configurable via env FAIL_QC_BLOCKS_BATCH=true/false).
Response: Updated batch with results.
Error: 400 for invalids (details per row); rollback.

Add dependency for batch access (batch:read).
Tests in backend/tests/test_results.py: Bulk entry, validation, QC block/flag, status updates.
Generate full code for router, schema, and tests."

## Prompt 37: Frontend UI for Batch Results Entry
"Develop batch results entry UI based on US-28 in Post-MVP User Stories and Post-MVP PRD (section 4.4).
In frontend/src/components/results/ResultsEntryTable.tsx: Enhance to bulk mode (tabular MUI DataGrid: rows=tests/samples from batch, columns=analytes; editable cells with auto-fill for commons).

Fetch analytes via getAnalysisAnalytes; real-time validation (inline errors for range/type).
QC rows highlighted; submit button with confirmation (call /results/batch).
Configurable QC handling: Alert/block on fail.

Update BatchResultsView.tsx: Toggle for bulk entry; status updates post-submit.
apiService.ts: Add enterBatchResults(batchId, data).
Tests in ResultsEntryTable.test.tsx: Editing, validation, submit.
Generate full code for updated components, apiService, and tests."

## Prompt 38: Integration and Workflow Updates for Sprint 7
"Integrate Sprint 7 feature (batch results entry) into system, per Post-MVP PRD (section 4.4) and US-28.
Update backend/app/routers/results.py to tie into batch statuses (e.g., set batch to 'Completed' if all tests done).
Enhance frontend ResultsManagement.tsx to link batch entry with prior features (e.g., show QC flags from Sprint 6).
Doc updates: In workflow-accessioning-to-reporting.md, enhance Stage 3 for batch entry variation; update technical doc for API/validation.
Tests: End-to-end for batch results with QC/validation.
Generate full code for integrations, doc patches, and tests."

# Navigation update
## Prompt A: Create Unified Sidebar Component
"Implement the unified persistent sidebar for the NimbleLims frontend, based on navigation.md (Sections 1-5) and ui-accessioning-to-reporting.md (Component Architecture). Replace the top Navbar with a single left sidebar using Material-UI Drawer (permanent on desktop, temporary on mobile).

Component: frontend/src/components/Sidebar.tsx
Structure: Use MUI List with Subheader for sections. For submenus (e.g., Admin), use Accordion for collapsible style.
Sections:
'Core Features': Items like Dashboard (/dashboard, DashboardIcon), Accessioning (/accessioning, ScienceIcon) – pull from existing Navbar items, permission-gated.
'Admin' (accordion): Sub-items like Overview (/admin), Lists Management (/admin/lists), etc. – from existing Admin Sidebar items.

Visuals: Active highlighting, icons, exact/prefix matching for active states.
Include Logo at top (clickable to /dashboard), User Menu at bottom (username/role, Logout).
No code yet for routes/layouts – focus on Sidebar.tsx.
Ensure responsive (width: 240px desktop, full-screen mobile), ARIA labels for accessibility, and ESLint compliance. Generate full code for Sidebar.tsx only."

## Prompt B: Integrate Sidebar with Routes and Layout
"Integrate the unified sidebar into the NimbleLims routes and layout, based on navigation.md (Section 3: Route Structure) and the new Sidebar.tsx from previous prompt.

Create: frontend/src/layouts/MainLayout.tsx – Wraps all routes with Sidebar (left) and main content (right, using Box with padding).
Update App.tsx or index: Use MainLayout for all paths (remove separate Navbar/AdminDashboard layouts).
Routes: Update to single layout – e.g., /dashboard, /accessioning in Core; /admin/* under Admin accordion.
Permission-Gating: Use hasPermission() from UserContext to show/hide items (e.g., Admin section only if config:edit).
Programmatic Navigation: Preserve useNavigate() for clicks.
Handle layout switch: No more navbar-to-sidebar toggle; sidebar always present (hidden on mobile until toggled via hamburger in top AppBar).
Include top AppBar: Minimal – title, back button (for nested routes), user info, mobile toggle.
Generate full code for MainLayout.tsx, updates to App.tsx/routes, and any Sidebar.tsx refinements."

## Prompt C: Add Responsiveness and Tests
"Enhance the unified sidebar with responsiveness and add tests, per navigation.md (Section 7: Responsive Design) and best practices.

In Sidebar.tsx/MainLayout.tsx: Use MUI useMediaQuery for breakpoints (<600px: temporary Drawer with overlay; >=600px: permanent).
Mobile: Add hamburger icon in AppBar to toggle sidebar.
Tests: Create Sidebar.test.tsx (render, snapshot, click navigation, permission hiding) and MainLayout.test.tsx (layout rendering, responsiveness via mocked media queries).
Edge Cases: No items if no permissions; accordion collapse/expand; active states on nested routes.
Generate full code for updates to Sidebar.tsx/MainLayout.tsx and new test files."

## Prompt D: Update Documentation and Refinements
"Update navigation.md to reflect the unified sidebar, based on the implemented changes.

Add 'Refinements' section: Describe shift to single sidebar, accordion for submenus, pros (consistency), and future (breadcrumbs, command palette).
Revise Sections 1-3: Replace hybrid descriptions with unified (e.g., Structure as vertical Drawer with sections).
Ensure alignment with permission-based visibility (Section 4).
Minor: Add notes on accordion usage for Admin.
Generate full updated content for navigation.md."

# Sprint 8
## Prompt 1: Database Schema Updates for EAV (Migration)
"Update the PostgreSQL database schema for NimbleLIMS to incorporate EAV as per planning refinements, focusing on samples and tests tables initially (extend to results, projects, client_projects, batches in a follow-up). Reference nimblelims_tech.md (Section 3: Data Model) and schema_dump_20251228.sql for alignment.
Create a new Alembic migration script in backend/alembic/versions/ (e.g., 0012_add_eav.py):

New table: custom_attributes_config (id UUID PK, entity_type str NOT NULL e.g. 'samples', attr_name str NOT NULL unique per entity, data_type str NOT NULL e.g. 'text/number/date/boolean/select', validation_rules JSONB default {}, description text, active bool default true, created_at/modified_at timestamp default NOW(), created_by/modified_by UUID FK to users).
Unique constraint: entity_type + attr_name.
Add custom_attributes JSONB default {} to: samples, tests (with GIN index for querying).
Extend RLS policies: Update samples_access, tests_access (etc.) to include custom_attributes visibility, ensuring is_admin() or has_project_access() checks apply.
Seed initial data: None for now—admins will create via UI.
Downgrade: Drop column, table, indexes.

Generate the full migration script (upgrade/downgrade functions) and update env.py if needed for auto-detection. Ensure compatibility with existing transactions (technical-accessioning-to-reporting.md). No code beyond migration files."

## Prompt 2: Backend Models, Schemas, and Routers for EAV
"Implement backend support for EAV in NimbleLIMS, building on the migration from previous prompt. Reference nimblelims_tech.md (Section 3.3: Models/Schemas) and api_endpoints.md for CRUD patterns.

Models: In backend/app/models/, add CustomAttributeConfig (SQLAlchemy ORM with fields from migration). Update Sample and Test models to include custom_attributes: Column(JSONB, default=dict).
Schemas: In backend/app/schemas/, add CustomAttributeConfigCreate/Update/Response (Pydantic, with validators for data_type enum and validation_rules dict). Update SampleCreate/SampleResponse etc. to include custom_attributes: dict[str, Any] = Field(default_factory=dict), with custom validator to check against configs.
Routers: In backend/app/routers/admin.py (or new custom_attributes.py), add CRUD endpoints:
GET /admin/custom-attributes: List with filters (entity_type), pagination.
POST /admin/custom-attributes: Create, require 'config:edit' via dependency.
GET /admin/custom-attributes/{id}
PATCH /admin/custom-attributes/{id}: Update, active toggle.
DELETE /admin/custom-attributes/{id}: Soft-delete (set active=False).

Validation: In create/update entity endpoints (e.g., POST /samples), fetch configs for entity_type and validate custom_attributes keys/values match (raise 400 with details).
Querying: Add custom_attributes filters to list endpoints (e.g., ?custom.ph_level=7.0 using JSONB ops in SQLAlchemy).

Generate full code for new/updated files: models/custom_attributes_config.py, schemas/custom_attributes_config.py, routers/admin.py (or new), and patches to sample/test files. Include PEP8 compliance and basic unit tests in backend/tests/test_custom_attributes.py (e.g., validation failures)."

## Prompt 3: Admin UI for Managing Custom Fields
"Create frontend components for EAV management in NimbleLIMS admin section, per ui-accessioning-to-reporting.md (Component Architecture) and nimblelims_prompts.md (Admin prompts). Gate via hasPermission('config:edit') from UserContext.

New Page: CustomFieldsManagement.tsx in frontend/src/pages/admin/ (table listing by entity_type, MUI DataGrid with columns: attr_name, data_type, description, active; filters for entity_type).
CRUD Dialogs: Add/Edit dialogs (Formik/Yup) with fields: entity_type Select (hardcoded options: 'samples', 'tests', etc.), attr_name TextField (unique check via API), data_type Select ('text', 'number', 'date', 'boolean', 'select'), validation_rules JSON editor (e.g., MUI TextField multiline for dict string), description TextField.
API Integration: Use apiService for CRUD (e.g., getCustomAttributes(filters), createCustomAttribute(data)).
Sidebar: Update Sidebar.tsx to add 'Custom Fields' under Admin accordion, linking to /admin/custom-fields.

Generate full code for: pages/admin/CustomFieldsManagement.tsx, components/admin/CustomFieldDialog.tsx (for CRUD), services/apiService.ts updates (new methods), and Sidebar.tsx refinements. Ensure responsive design (MUI useMediaQuery) and ESLint compliance. Add tests in CustomFieldsManagement.test.tsx (render, form validation, API mocks)."

## Prompt 4: Integrate EAV into Core Workflows (Forms and Views)
"Integrate EAV into existing NimbleLIMS workflows for samples and tests, per workflow-accessioning-to-reporting.md (Stage 1: Accessioning, Stage 3: Results Entry) and ui-accessioning-to-reporting.md (AccessioningForm.tsx, ResultsEntryTable.tsx).

Forms: In SampleDetailsStep.tsx, fetch configs for 'samples' via apiService.getCustomAttributes('samples'), dynamically render fields (e.g., TextField for text, NumberField for number) in a 'Custom Fields' section; include in Formik values/submit.
Views: In ResultsEntryTable.tsx, add dynamic columns for test custom_attributes (fetch configs for 'tests', render in table rows).
Bulk Mode: In AccessioningForm.tsx, extend unique fields table to include custom columns if defined.
Validation: Real-time Yup validation based on rules (e.g., min/max for numbers); server-side fallback.

Generate full code updates for: components/accessioning/SampleDetailsStep.tsx, results/ResultsEntryTable.tsx, pages/AccessioningForm.tsx. Add error handling (alerts) and tests (e.g., dynamic field rendering). Ensure alignment with RBAC—no edit if lacking permissions."

## Prompt 5: Expand EAV to Remaining Tables
"Expand EAV implementation to results, projects, client_projects, and batches in NimbleLIMS, building on previous prompts.

Migration Update: New Alembic script (0013_expand_eav.py) to add custom_attributes JSONB (with GIN index) to these tables; extend RLS policies accordingly.
Models/Schemas/Routers: Update respective files to include custom_attributes; extend validation in create/update endpoints.
UI: Update CustomFieldsManagement.tsx to support new entity_types; integrate dynamic fields into relevant forms/views (e.g., ResultsManagement.tsx for results, project management pages if exist).

Generate full code for the new migration, model/schema/router updates, and UI refinements. Include integration tests for cross-entity validation."

## Prompt 6: Update Documentation for EAV
"Update NimbleLIMS documentation to reflect EAV integration, based on implemented changes.

nimblelims_tech.md: Add Section 3.5: EAV Model (describe tables, JSONB usage, indexes); update API Endpoints (new /admin/custom-attributes); add to Security (RLS extensions) and Testing.
ui-accessioning-to-reporting.md: Add to Component Architecture (CustomFieldsManagement.tsx); describe dynamic rendering in forms.
workflow-accessioning-to-reporting.md: Update Steps (e.g., Sample Details Entry includes custom fields section).
nimblelims_prd.md: Post-MVP Section 4.5: Custom Fields (functional reqs, e.g., admin definition, validation).
api_endpoints.md: Add EAV CRUD details.

Generate full updated content for each file, maintaining version history (e.g., Version 1.5: Added EAV for configurability)."

# Help
## Client
### Prompt 1: Database Migration for Client Role and User Seeding
"Implement an Alembic migration for seeding the Client role and a sample client user in NimbleLIMS, based on Technical Document (Section 3.1) and schema_dump20260103.sql. Focus on post-MVP enhancements.

Migration File: Create 0014_seed_client_role.py in backend/db/migrations.
Role: Insert into roles: name='Client', description='Read-only access for client users'.
Permissions: Assign to role_permissions: sample:read, test:read (view assigned tests), result:read (view results), project:read (view own projects), batch:read (view batches if relevant). Use existing 17 permissions; no new ones.
User: Insert into users: username='client_user', password_hash=bcrypt('clientpass123'), email='client@example.com', role_id=(Client role ID), client_id=(assume seeded client ID from prior migration, e.g., first client).
RLS: Update projects_access policy to include client_id filtering for Client role users.
Up/Down Functions: Standard Alembic; ensure idempotent (check if exists before insert).
Dependencies: Run after 0013 (EAV expansion).

Generate the full migration file code, ensuring PEP8. Do not implement other code yet."

### Prompt 2: Backend API for Role-Filtered Help
"Add backend API endpoints for role-filtered help content in NimbleLIMS, per ui-accessioning-to-reporting.md (Help Components) and nimblelims_prd.md (Post-MVP 4.6).

New Table: help_entries (id UUID PK, section varchar, content text, role_filter varchar (e.g., 'Client'), active bool, audit fields).
Migration: Create 0015_help_entries.py to add table and seed initial entries (e.g., for Client: section='Viewing Projects', content='Step-by-step guide to access your samples and results.').
Routers: In backend/app/routers/help.py (new file), add:
GET /help: List entries, filter by ?role= (use current_user.role from dependency), pagination.
GET /help/contextual?section=: Return specific help, filtered by role.
POST/PATCH/DELETE /admin/help: CRUD for admins (require config:edit).

Schemas: HelpEntryCreate, HelpEntryResponse with Pydantic.
Security: RLS on help_entries: Users see only matching role_filter or public (role_filter=NULL).

Generate full code for: migrations/0015_help_entries.py, models/help_entries.py, schemas/help.py, routers/help.py. Include basic tests in tests/test_help.py (e.g., role filtering)."

### Prompt 3: Frontend UI for Client-Specific Help
"Implement client-specific help in the NimbleLIMS frontend, based on ui-accessioning-to-reporting.md and workflow-accessioning-to-reporting.md. Gate via UserContext.role === 'Client'.

New Components: ClientHelpSection.tsx (simplified FAQ list, e.g., accordions for 'Viewing Samples', 'Understanding Statuses'); integrate into HelpPage.tsx with conditional rendering.
Tooltips: Update components like ResultsManagement.tsx to add client-friendly tooltips (e.g., 'This shows your test results—contact your lab for questions.').
API Integration: Update apiService.ts with getHelp(filters) using ?role=client; fetch on HelpPage load.
Sidebar: Add 'Help' link visible to all, but content filters by role.
Simplicity: For clients, limit to 3-5 key topics; use plain language, no jargon.

Generate full code for: pages/HelpPage.tsx (updates), components/help/ClientHelpSection.tsx, services/apiService.ts (updates). Ensure responsive (MUI), ESLint compliance, and tests in HelpPage.test.tsx (role-based rendering)."

### Prompt 4: Integration Testing and Doc Updates
"Add integration tests and update documentation for client help and role in NimbleLIMS.

Tests: In backend/tests/test_help.py and frontend/tests/HelpPage.test.tsx, add scenarios: Client user sees filtered help; non-client sees general; unauthorized access denied.
Docs: Update nimblelims_tech.md (Section 2.2: Add help flow); ui-accessioning-to-reporting.md (Add ClientHelpSection); api_endpoints.md (Add /help endpoints with examples).
Seeding Verification: Add script in db/scripts/verify_seeding.sql to check Client role/user.

Generate full code for test files and updated doc content (maintain version history, e.g., Version 1.6: Added client help)."

## Tech
### Prompt 1: Database Migration for Lab Tech Help Seeding
"Extend the help_entries table in NimbleLIMS with Lab Technician seeds, based on Technical Document (Section 3.1) and schema_dump20260103.sql (existing 'lab technician' role). This is post-MVP; use role_filter='lab-technician' slug.

Migration File: Create 0017_lab_tech_help_seeds.py in backend/db/migrations (follows 0016_help_entries).
Entries: Seed 4–6 items (e.g., section='Accessioning Workflow', content='Step-by-step: Enter details, assign tests/batteries, handle aliquots. Bulk tip (US-24): Use for multiples. Requires sample:create.'; role_filter='lab-technician').
Idempotency: ON CONFLICT DO NOTHING.
RLS: No changes; uses existing policy.
Up/Down: Standard Alembic; downgrade deletes by role_filter.

Generate the full migration file code, ensuring PEP8."

### Prompt 2: Backend API for Lab Tech-Filtered Help
"Update backend API for Lab Tech help in NimbleLIMS, per ui-accessioning-to-reporting.md and workflow-accessioning-to-reporting.md. Build on help_entries from 0016/0017.

Routers: Update backend/app/routers/help.py (full file):
Filter GET /help and /help/contextual by ?role=lab-technician (case-insensitive, derive from current_user.role.name.lower().replace(' ', '-')).
Add Technician examples in docstrings.

Schemas: Reuse HelpEntry.
Tests: Add to tests/test_help.py (filtering, content).

Generate full code for routers/help.py (updates) and tests/test_help.py (extensions)."

### Prompt 3: Frontend UI for Lab Tech-Specific Help
"Implement Lab Tech help in frontend, based on ui-accessioning-to-reporting.md. Gate by UserContext.role === 'lab-technician'.

Components: LabTechHelpSection.tsx (accordions; reusable with Client; ARIA labels).
Updates: HelpPage.tsx (conditional); tooltips in accessioning/SampleDetailsStep.tsx ('QC: Blank—US-4') and results/ResultsEntryTable.tsx ('Analytes: Rules').
API: apiService.ts update for ?role=lab-technician.
Sidebar: Role-specific.

Generate full code for components/help/LabTechHelpSection.tsx, pages/HelpPage.tsx (updates), components/accessioning/SampleDetailsStep.tsx (updates), components/results/ResultsEntryTable.tsx (updates), apiService.ts (updates). Ensure MUI responsive, ESLint, ARIA, tests in HelpPage.test.tsx."

### Prompt 4: Integration Testing and Doc Updates
"Add tests and docs for Lab Tech help.

Tests: Extend test_help.py and HelpPage.test.tsx (scenarios: filtering 'lab-technician', ARIA, RLS-denied).
Docs: Update nimblelims_tech.md (Section 2.2: Tech flow); ui-accessioning-to-reporting.md (Add LabTechHelpSection); api_endpoints.md (Tech examples).
Verification: Add db/scripts/verify_lab_tech_help.sql.

Generate full code for test updates and doc content (Version 1.7: Added lab tech help)."

## Manager
### Prompt 1: Database Migration for Lab Manager Help Seeding
"Extend help_entries table with Lab Manager seeds in NimbleLIMS, per Technical Document (Section 3.1) and schema_dump20260103.sql (existing 'Lab Manager' role). Post-MVP; use role_filter='lab-manager' slug.

Migration File: Create 0018_lab_manager_help_seeds.py in backend/db/migrations (follows 0017_lab_tech_help_seeds).
Entries: Seed 4–6 items (e.g., section='Results Review', content='Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.'; role_filter='lab-manager'; cover batches, projects).
Idempotency: ON CONFLICT DO NOTHING.
RLS: No changes.
Up/Down: Standard Alembic; downgrade deletes by role_filter.

Generate full migration file code, ensuring PEP8."

### Prompt 2: Backend API for Lab Manager-Filtered Help
"Update backend API for Lab Manager help in NimbleLIMS, per ui-accessioning-to-reporting.md and workflow-accessioning-to-reporting.md. Build on help_entries from prior migrations.

Routers: Update backend/app/routers/help.py (full file):
Filter GET /help and /help/contextual by ?role=lab-manager (case-insensitive, from current_user.role.name.lower().replace(' ', '-')).
Add Manager examples in docstrings.

Schemas: Reuse HelpEntry.
Tests: Add to tests/test_help.py (filtering, content).

Generate full code for routers/help.py (updates) and tests/test_help.py (extensions). Ensure client/Technician compatibility."

### Prompt 3: Frontend UI for Lab Manager-Specific Help
"Implement Lab Manager help in frontend, based on ui-accessioning-to-reporting.md. Gate by UserContext.role === 'lab-manager'.

Components: LabManagerHelpSection.tsx (accordions; reusable with prior; ARIA labels; tips like 'Batch Management: Cross-project (US-25)', 'Review Workflow: Approvals (US-11)').
Updates: HelpPage.tsx (conditional); tooltips in ResultsManagement.tsx ('Review results: Use result:review') and BatchResultsView.tsx ('QC at batch: US-27').
API: apiService.ts update for ?role=lab-manager.
Sidebar: Role-specific.

Generate full code for components/help/LabManagerHelpSection.tsx, pages/HelpPage.tsx (updates), components/results/ResultsManagement.tsx (updates), components/results/BatchResultsView.tsx (updates), apiService.ts (updates). Ensure MUI responsive, ESLint, ARIA, tests in HelpPage.test.tsx."

### Prompt 4: Integration Testing and Doc Updates
"Add tests and docs for Lab Manager help in NimbleLIMS.

Tests: Extend test_help.py and HelpPage.test.tsx (scenarios: 'lab-manager' filtering, ARIA, RLS-denied).
Docs: Update nimblelims_tech.md (Section 2.2: Manager flow); ui-accessioning-to-reporting.md (Add LabManagerHelpSection); api_endpoints.md (Manager examples).
Verification: Add db/scripts/verify_lab_manager_help.sql.

Generate full code for test updates and doc content (Version 1.8: Added lab manager help)."

## Admin
### Prompt 1: Database Migration for Admin Help Seeding
"Extend help_entries table with Admin seeds in NimbleLIMS, per Technical Document (Section 3.1) and schema_dump20260103.sql (existing 'Administrator' role). Post-MVP; use role_filter='administrator' slug.

Migration File: Create 0019_admin_help_seeds.py in backend/db/migrations (follows 0018_lab_manager_help_seeds).
Entries: Seed 4–6 items (e.g., section='User Management', content='Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.'; role_filter='administrator'; cover EAV editing, RLS).
Idempotency: ON CONFLICT DO NOTHING.
RLS: No changes.
Up/Down: Standard Alembic; downgrade deletes by role_filter.

Generate full migration file code, ensuring PEP8."

### Prompt 2: Backend API for Admin-Filtered Help and CRUD
"Update backend API for Admin help and add CRUD for help_entries in NimbleLIMS, per ui-accessioning-to-reporting.md. Build on help_entries; require config:edit for edits.

Routers: Update backend/app/routers/help.py (full file):
Filter GET /help and /help/contextual by ?role=administrator.
Add POST/PATCH/DELETE /admin/help/{id} (CRUD; RBAC: config:edit; validate role_filter against existing roles).
Add examples in docstrings.

Schemas: Add HelpEntryCreate/Update with validation.
Tests: Add to tests/test_help.py (CRUD, filtering).

Generate full code for routers/help.py (updates), schemas/help.py (additions), tests/test_help.py (extensions). Ensure compatibility with other roles."

### Prompt 3: Frontend UI for Admin-Specific Help and Editing
"Implement Admin help and editing UI in frontend, based on ui-accessioning-to-reporting.md. Gate by UserContext.role === 'administrator'.

Components: AdminHelpSection.tsx (accordions; reusable; tips like 'Custom Attributes: Edit configs (post-MVP EAV)'); HelpManagement.tsx (CRUD table for help_entries; filter by role; Formik forms; config:edit gate).
Updates: HelpPage.tsx (conditional, with edit button to HelpManagement); tooltips in admin/CustomFieldsManagement.tsx ('Edit help: Use config:edit').
API: apiService.ts update for ?role=administrator and /admin/help CRUD.
Sidebar: Add 'Help Management' for admins.

Generate full code for components/help/AdminHelpSection.tsx, pages/admin/HelpManagement.tsx, pages/HelpPage.tsx (updates), components/admin/CustomFieldsManagement.tsx (updates), apiService.ts (updates). Ensure MUI responsive, ESLint, ARIA, tests in HelpPage.test.tsx and HelpManagement.test.tsx."

### Prompt 4: Integration Testing and Doc Updates
"Add tests and docs for Admin help/editing in NimbleLIMS.

Tests: Extend test_help.py (CRUD, RBAC) and add HelpManagement.test.tsx (editing, config:edit denial).
Docs: Update nimblelims_tech.md (Section 2.2: Admin flow with CRUD); ui-accessioning-to-reporting.md (Add HelpManagement); api_endpoints.md (CRUD details).
Verification: Add db/scripts/verify_admin_help.sql.

Generate full code for test updates and doc content (Version 1.9: Added admin help with editing)."

# Navigation Update
## Prompt 1: Create New Clients Management Page
"Implement the ClientsManagement page for NimbleLIMS in the frontend, based on ui-accessioning-to-reporting.md (Component Architecture) and nimblelims_tech.md (Section 2.1, frontend with React/MUI). This page handles CRUD for clients (organizations) and is accessible via /clients.

Use MUI DataGrid for listing clients (columns: name, description, active, created_at; with filtering/sorting/pagination).
Include Add/Edit dialogs (Formik/Yup) with fields: name (required, unique), description (optional), active (toggle).
API Integration: Use apiService for CRUD (getClients(filters), createClient(data), updateClient(id, data), deleteClient(id) - soft-delete via active=false).
Gate access with hasPermission('project:manage') from UserContext; redirect to dashboard if lacking.
Responsive: Use MUI Grid/useMediaQuery for layout adaptations (e.g., 1-column on mobile).

Generate full code for: pages/ClientsManagement.tsx, components/clients/ClientDialog.tsx (for CRUD), and services/apiService.ts updates (new methods). Ensure ESLint compliance and add tests in ClientsManagement.test.tsx (render, form validation, API mocks with MSW). Reference User Stories (US-25) for client project grouping context, but do not implement client projects here."

## Prompt 2: Update Sidebar to Add Client Accordion Section
"Update the Sidebar component in NimbleLIMS to add a new 'Client' accordion section, based on navigation.md (Unified Sidebar Architecture, Accordion Usage) and ui-accessioning-to-reporting.md (Sidebar.tsx props). This section is collapsible like Admin and requires 'project:manage' permission to view.

Structure: Add Accordion below Core Features, with header 'Client' and SettingsApplicationsIcon (or similar).
Sub-items (nested List):
'Clients' linking to /clients (PeopleIcon, highlights on /clients routes).
'Client Projects' linking to /client-projects (ViewListIcon, highlights on /client-projects routes) - move this from Core Features section.

Behavior: Auto-expands on /clients or /client-projects routes; manual toggle; active state (primary color icon) on any client route.
Permission: Hide entire accordion if lacking 'project:manage'.
Nested styling: Indent sub-items (pl: 4) for hierarchy.
Accessibility: ARIA labels for accordion and items.

Generate full updated code for: components/Sidebar.tsx. Include refinements to remove 'Client Projects' from Core Features. Add tests in Sidebar.test.tsx for accordion rendering, expansion, and permission hiding. Ensure responsive variants (permanent/temporary) remain unchanged."

## Prompt 3: Make Entire Sidebar Collapsible on Desktop
"Enhance the MainLayout and Sidebar in NimbleLIMS to make the entire sidebar collapsible on desktop, based on navigation.md (Unified Sidebar Navigation, MainLayout.tsx) and nimblelims_tech.md (responsive design). Retain permanent drawer on desktop (>=600px) and temporary on mobile, but add a collapse toggle.

In MainLayout.tsx: Add state for sidebarCollapsed (boolean, default false); toggle button in AppBar (e.g., ChevronLeftIcon when expanded, ChevronRightIcon when collapsed, next to hamburger on mobile).
In Sidebar.tsx: Support collapsed prop; when collapsed, use MUI Drawer miniVariant (show icons only, reduced width ~56px; tooltips on hover for items).
Behavior: Toggle persists across routes (use localStorage or context); auto-expand on item click if collapsed; accordions (Admin, Client) collapse when sidebar collapses.
Mobile: Toggle acts as open/close for temporary drawer (existing behavior).
Accessibility: ARIA labels for toggle button (e.g., 'Collapse sidebar'); focus management on toggle.

Generate full updated code for: layouts/MainLayout.tsx (state, toggle button, pass collapsed prop to Sidebar) and components/Sidebar.tsx (handle collapsed: conditional rendering for text/labels, mini width). Add tests in MainLayout.test.tsx for toggle functionality and responsive states. Ensure integration with UserContext for permissions."

# Add edit to accessioning 
## Prompt 1: Database Migration for Edit Support (Audit Indexes and Permissions)
"Extend the PostgreSQL database schema for NimbleLIMS to support editing of samples, tests, and containers, based on Technical Document (section 3) and User Stories (US-1, US-7, US-5). Focus on adding indexes for efficient editing and ensuring 'test:update' permission exists.
Migration File: Create 0020_edit_support.py in backend/db/migrations (follows 0019_admin_help_seeds).

Add indexes: On modified_at and modified_by in samples, tests, containers (if not present).
Seed 'test:update' permission if missing (name='test:update', description='Update existing tests').
Idempotency: ON CONFLICT DO NOTHING for permission seeding.
RLS: No changes (leverages existing policies for access during edits).
Up/Down: Standard Alembic; downgrade drops indexes if added.

Generate full migration file code, ensuring PEP8."

## Prompt 2: Backend API for Sample/Test/Container Editing
"Implement backend API endpoints for editing samples, tests, and containers in NimbleLIMS, based on api_endpoints.md and Technical Document (section 4.1, 5). Build on existing schemas; require appropriate update permissions.
Routers: Update/add in backend/app/routers/samples.py, tests.py, containers.py (full files if new):

PATCH /samples/{id}: Partial update (e.g., name, description, status, custom_attributes); validate custom attributes; update audit fields; return updated sample.
PATCH /tests/{id}: Partial update (e.g., status, technician_id); RBAC: test:update.
PATCH /containers/{id}: Partial update (e.g., name, type_id, concentration); RBAC: sample:update (since containers link to samples).
For all: 404 if not found; 403 if no access (via RLS); atomic transaction.
Add examples in docstrings (e.g., update sample status to 'Reviewed').

Schemas: Add SampleUpdate, TestUpdate, ContainerUpdate (partial, optional fields with validation).
Tests: Add to tests/test_samples.py, test_tests.py, test_containers.py (scenarios: successful update, permission denial, invalid data, RLS-denied).
Generate full code for routers/samples.py (updates), routers/tests.py (new/full), routers/containers.py (updates), schemas/samples.py (additions), schemas/tests.py (additions), schemas/containers.py (additions), and test files (extensions). Ensure compatibility with existing create endpoints."

## Prompt 3: Frontend UI for Sample/Test/Container Editing and Management Pages
"Implement editing UI for samples, tests, and containers in frontend, based on ui-accessioning-to-reporting.md and workflow-accessioning-to-reporting.md. Reuse/modify existing forms for both create/edit modes; add management list pages for browsing and navigating to edits.
Components:

SampleForm.tsx: Reuse/modify AccessioningForm.tsx to handle edit mode (if id prop, fetch via GET /samples/{id}, pre-fill, use PATCH; simplify wizard for edits by skipping creation-only steps like initial test assignment).
TestForm.tsx (new): Reusable form for test details (status, technician); handles create/edit modes.
ContainerForm.tsx (new): Reusable form for container details (name, type, concentration); handles create/edit modes.
Management Pages: SamplesManagement.tsx (MUI DataGrid list of samples with edit buttons linking to /samples/{id}), TestsManagement.tsx (similar for tests), ContainersManagement.tsx (similar for containers, enhances existing /containers).
Updates: apiService.ts for PATCH endpoints and GET /{entity}/{id}.
Custom Fields: Ensure dynamic rendering/validation in forms for edits (reuse CustomAttributeField.tsx).
Tooltips/Help: Add contextual tooltips in forms (e.g., 'Edit status: Requires sample:update permission').

Navigation Updates: Update components/Sidebar.tsx (full file) to add/enhance Core Features:

Add 'Samples' (/samples) if missing; 'Tests' (/tests).
Enhance 'Containers' (/containers) with list/edit support.
Auto-expand accordions for /samples/, /tests/ routes.
Permission-gating: Show based on sample:update, test:update.

Routes: Update App.tsx or routes file to add /samples, /samples/{id}, /tests, /tests/{id}, /containers/{id}.
Generate full code for components/samples/SampleForm.tsx (updates to AccessioningForm), components/tests/TestForm.tsx (new), components/containers/ContainerForm.tsx (new), pages/SamplesManagement.tsx (new), pages/TestsManagement.tsx (new), pages/ContainersManagement.tsx (updates), apiService.ts (updates), components/Sidebar.tsx (updates). Ensure MUI responsive, ESLint, ARIA (e.g., aria-labels for edit buttons), tests in SamplesManagement.test.tsx (new), etc."

## Prompt 4: Integration Testing and Doc Updates
"Add tests and docs for sample/test/container editing in NimbleLIMS.
Tests: Extend test_samples.py, test_tests.py, test_containers.py (PATCH scenarios, RBAC, audit updates); add SamplesManagement.test.tsx, TestsManagement.test.tsx, ContainersManagement.test.tsx (list rendering, edit navigation, form modes, ARIA, permission hiding).
Docs: Update nimblelims_tech.md (Section 2.2: Add edit flows); ui-accessioning-to-reporting.md (Add SampleForm, management pages); api_endpoints.md (Add PATCH details with examples); navigation.md (Update Structure table with new/enhanced items like 'Samples', 'Tests'); workflow-accessioning-to-reporting.md (Add edit stages post-accessioning).
Verification: Add db/scripts/verify_edits.sql (check audit fields after update).
Generate full code for test updates and doc content (Version 2.0: Added editing for samples/tests/containers)."

# UAT Scripts
## Prompt 1: UAT for Single Sample Accessioning (US-1, US-5, US-7)
"Generate short UAT scripts for single sample accessioning in NimbleLIMS, based on User Stories (US-1, US-5, US-7), PRD (Section 3.1 Sample Tracking), workflow-accessioning-to-reporting.md (Stage 1), ui-accessioning-to-reporting.md (AccessioningForm.tsx), and technical-accessioning-to-reporting.md (POST /samples/accession). Create 2-3 focused test cases: one happy path (full accessioning with container and test assignment), one with double-entry validation, one error case (invalid project access via RLS). Each script: Preconditions (e.g., logged in as Lab Technician with sample:create), steps (UI navigation, field entry), expected results (e.g., sample status 'Received', audit fields set), pass/fail. Use Markdown tables; reference docs inline. Output as uat-sample-accessioning.md."

## Prompt 2: UAT for Sample Status Management and Editing (US-2, Post-MVP Editing)
"Generate short UAT scripts for sample status management and editing in NimbleLIMS, based on User Stories (US-2), workflow-accessioning-to-reporting.md (Stage 1.5), ui-accessioning-to-reporting.md (SamplesManagement.tsx, SampleForm.tsx), technical-accessioning-to-reporting.md (PATCH /samples/{id}), and schema (samples table with status FK, custom_attributes JSONB). Create 2-3 focused test cases: one status update (e.g., to 'Available for Testing'), one edit with custom attributes (validation success/fail), one RLS denial (non-project user). Each script: Preconditions (e.g., sample exists, sample:update permission), steps (navigate to /samples, edit dialog), expected results (audit updated, RLS 403 error), pass/fail. Use Markdown tables; reference docs. Output as uat-sample-status-editing.md."

## Prompt 3: UAT for Aliquots/Derivatives and QC Handling (US-3, US-4)
"Generate short UAT scripts for aliquots/derivatives creation and QC handling in NimbleLIMS, based on User Stories (US-3, US-4), PRD (Section 3.1 QC Integration), workflow-accessioning-to-reporting.md (Variation 1), ui-accessioning-to-reporting.md (AliquotDerivativeDialog.tsx), and schema (samples.parent_sample_id, qc_type FK). Create 2-3 focused test cases: one aliquot creation (inherit project), one derivative with new type, one QC flag in batch view. Each script: Preconditions (parent sample exists), steps (dialog open, field entry), expected results (linked records, inheritance), pass/fail. Use Markdown tables; reference docs. Output as uat-aliquots-qc.md."

## Prompt 4: UAT for Container Management and Editing (US-5, Post-MVP Editing)
"Generate short UAT scripts for container management and editing in NimbleLIMS, based on User Stories (US-5), PRD (Section 3.1 Containers), ui-accessioning-to-reporting.md (ContainerManagement.tsx, ContainerForm.tsx), technical-accessioning-to-reporting.md (PATCH /containers/{id}), and schema (containers table with type_id FK, contents junction). Create 2-3 focused test cases: one hierarchical creation (plate with wells), one edit (update concentration), one pooling via contents. Each script: Preconditions (container_types exist), steps (navigate to /containers, form submit), expected results (volume calculated, RLS access), pass/fail. Use Markdown tables; reference docs. Output as uat-container-management.md."

## Prompt 5: UAT for Test Ordering and Status Management (US-7, US-8, US-12)
"Generate short UAT scripts for test ordering and status management in NimbleLIMS, based on User Stories (US-7, US-8, US-12), PRD (Section 3.1 Test Ordering), workflow-accessioning-to-reporting.md (Stage 1 Test Assignment), ui-accessioning-to-reporting.md (TestAssignmentStep.tsx, TestsManagement.tsx, TestForm.tsx), and technical-accessioning-to-reporting.md (POST /tests). Create 2-3 focused test cases: one assignment during accessioning, one status update/edit (to 'In Analysis'), one battery assignment (sequence order). Each script: Preconditions (analyses exist), steps (select battery_id), expected results (tests created with 'In Process'), pass/fail. Use Markdown tables; reference docs. Output as uat-test-ordering.md."

## Prompt 6: UAT for Batch Creation and Management (US-9, US-10, US-26, US-27)
"Generate short UAT scripts for batch creation and management in NimbleLIMS, based on User Stories (US-9, US-10, US-26, US-27), PRD (Section 3.1 Batches/Plates), workflow-accessioning-to-reporting.md (Stage 2), ui-accessioning-to-reporting.md (ResultsManagement.tsx), and technical-accessioning-to-reporting.md (POST /batches). Create 2-3 focused test cases: one basic batch (add containers), one cross-project with compatibility check, one with QC addition. Each script: Preconditions (samples available), steps (select containers), expected results (status 'Created', QC auto-generated), pass/fail. Use Markdown tables; reference docs. Output as uat-batch-management.md."

## Prompt 7: UAT for Results Entry and Review (US-11, US-28)
"Generate short UAT scripts for results entry and review in NimbleLIMS, based on User Stories (US-11, US-28), PRD (Section 3.1 Results Entry), workflow-accessioning-to-reporting.md (Stages 3-4), ui-accessioning-to-reporting.md (ResultsEntryTable.tsx), and technical-accessioning-to-reporting.md (POST /results/batch). Create 2-3 focused test cases: one batch entry (analyte validation), one review (status to 'Complete'), one QC failure flag. Each script: Preconditions (test in 'In Analysis'), steps (tabular entry), expected results (statuses updated, validation errors), pass/fail. Use Markdown tables; reference docs. Output as uat-results-entry-review.md."

## Prompt 8: UAT for Reporting and Project Management (US-2, US-13, US-25)
"Generate short UAT scripts for reporting and project management in NimbleLIMS, based on User Stories (US-2, US-13, US-25), PRD (Section 3.1 Reporting), workflow-accessioning-to-reporting.md (Stage 5), and schema (projects table with client_project_id). Create 2-3 focused test cases: one sample reporting (status 'Reported'), one client project grouping, one access via project_users. Each script: Preconditions (sample 'Reviewed'), steps (update status), expected results (report_date set, aggregation), pass/fail. Use Markdown tables; reference docs. Output as uat-reporting-projects.md."

## Prompt 9: UAT for Security and RBAC (US-12, US-14, US-15)
"Generate short UAT scripts for security and RBAC in NimbleLIMS, based on User Stories (US-12, US-14, US-15), PRD (Section 3.1 Security), technical-accessioning-to-reporting.md (RLS policies), and schema (role_permissions). Create 2-3 focused test cases: one login/logout (JWT), one permission denial (e.g., no sample:create), one client isolation (RLS on projects). Each script: Preconditions (roles seeded), steps (attempt action), expected results (403 errors, isolated data), pass/fail. Use Markdown tables; reference docs. Output as uat-security-rbac.md."

## Prompt 10: UAT for Configurations and Custom Fields (US-16 to US-23, Post-MVP EAV)
"Generate short UAT scripts for configurations and custom fields in NimbleLIMS, based on User Stories (US-16 to US-23, Post-MVP Custom Fields), PRD (Section 4.5 Custom Fields), ui-accessioning-to-reporting.md (CustomFieldsManagement.tsx), technical-accessioning-to-reporting.md (custom_attributes_config table), and api_endpoints.md (CRUD /admin/custom-attributes). Create 2-3 focused test cases: one list editing (statuses), one custom field creation (for samples), one usage/validation in form. Each script: Preconditions (config:edit permission), steps (admin UI), expected results (dynamic rendering, querying), pass/fail. Use Markdown tables; reference docs. Output as uat-configurations-custom.md."

## Prompt 11: UAT for Bulk Accessioning and Enhancements (US-24, US-28)
"Generate short UAT scripts for bulk accessioning and enhancements in NimbleLIMS, based on User Stories (US-24, US-28), post-MVP PRD (Sections 4.1, 4.4), and api_endpoints.md (POST /samples/bulk-accession). Create 2-3 focused test cases: one bulk with uniques (5 samples), one with auto-naming, one batch results entry. Each script: Preconditions (common fields valid), steps (toggle bulk mode), expected results (atomic creation, QC checks), pass/fail. Use Markdown tables; reference docs. Output as uat-bulk-enhancements.md."

## Prompt 12: UAT for Help System (Client, Lab Tech, Lab Manager, Admin)
"Generate short UAT scripts for the help system in NimbleLIMS, based on User Stories (implied in configs), ui-accessioning-to-reporting.md (HelpPage.tsx, role sections), api_endpoints.md (GET /help), and navigation.md (/help route). Create 2-3 focused test cases: one role-filtered view (Client accordion), one CRUD as admin (create/update/delete entry), one contextual tooltip check. Each script: Preconditions (help entries seeded), steps (navigate to /help), expected results (filtered content, ARIA labels), pass/fail. Use Markdown tables; reference docs. Output as uat-help-system.md."

## Prompt 13: UAT for Navigation and UI Responsiveness
"Generate short UAT scripts for navigation and UI responsiveness in NimbleLIMS, based on navigation.md (unified sidebar, accordions), ui-accessioning-to-reporting.md (responsive adaptations), and PRD (Section 5.4 Usability). Create 2-3 focused test cases: one sidebar navigation (permission gating, auto-expand), one mobile drawer, one accessibility (keyboard nav, ARIA). Each script: Preconditions (logged in), steps (resize browser), expected results (no layout breaks, tooltips), pass/fail. Use Markdown tables; reference docs. Output as uat-navigation-ui.md."

# Prompts for Configurable Names/IDs
## Prompt A: Database Schema and Migration for Configurable Name Templates
"Based on the NimbleLIMS planning documents (PRD Section 5.3 for configurations, Technical Document Section 2.1 for data models, and User Stories US-1 for sample accessioning), add support for admin-configurable name/ID templates for entities like samples, projects, batches, analyses, and containers. Templates should use placeholders (e.g., '{CLIENT}-{YYYYMMDD}-{SEQ}', where SEQ is an auto-incrementing sequence per entity type, YYYYMMDD is date, CLIENT is from linked client).
Create a new table 'name_templates' with columns: id (UUID), entity_type (str, e.g., 'sample', 'project'), template (str), description (text), active (bool, default true), created_at/by, modified_at/by. Unique constraint on entity_type for active templates.
Add a sequence column or use PostgreSQL sequences for SEQ per entity_type.
Generate an Alembic migration script (revision '0023', down_revision '0022') to create this table, add indexes (e.g., idx_name_templates_entity_type), enable RLS (admins can manage all, others view active), and seed initial templates (e.g., for sample: 'SAMPLE-{YYYY}-{SEQ}', for project: 'PROJ-{CLIENT}-{YYYYMMDD}-{SEQ}').
Update existing models (e.g., in backend/models/) to reference this during creation. Ensure idempotency in seeds.
Output as: migration file (0023_configurable_names.py), updated schema_dump.sql snippet for the new table/RLS, and any model changes. No frontend yet."

## Prompt B: API Endpoints for Configurable Names
"Extend the NimbleLIMS backend based on the new name_templates table from previous prompt (Technical Document Section 3.1 for APIs, api_endpoints.md for patterns). Add admin endpoints for managing templates: GET /admin/name-templates (list with filters), POST /admin/name-templates (create with validation for placeholders), PATCH /admin/name-templates/{id} (update), DELETE /admin/name-templates/{id} (soft delete via active=false).
Require config:edit permission (from 0004_initial_data.py).
Integrate auto-generation into create endpoints: For POST /samples, /projects, /batches, etc., if name is not provided, fetch active template for entity_type, replace placeholders (e.g., SEQ via DB sequence, CLIENT from client_id, date from received_date or NOW()), and generate unique name. If template missing, fallback to UUID.
Handle sequences transactionally to avoid gaps.
Add validation: Ensure generated names are unique (retry with next SEQ if conflict).
Update schemas (e.g., SampleCreate to make name optional).
Output as: updated routers/admin.py with new endpoints, core/name_generator.py for logic, schemas/name_template.py, and tests/test_name_templates.py with cases for generation and uniqueness."

## Prompt C: UI for Configurable Names Management
"Update the NimbleLIMS frontend for configurable names based on new API endpoints (ui-accessioning-to-reporting.md for admin components, navigation.md for Admin accordion). Add a new admin page CustomNamesManagement.tsx under Admin > Configurations (or similar), with DataGrid for listing templates (columns: entity_type, template, description, active), and dialogs for create/edit (fields: entity_type select from allowed types, template text with placeholder examples, description).
Use MUI components, Formik/Yup for validation (e.g., template must include {SEQ} for uniqueness).
In accessioning forms (e.g., AccessioningForm.tsx, SampleDetailsStep.tsx), make name field optional with a toggle for 'Auto-Generate Name' (default on), showing preview based on template and current form values (fetch template via GET /admin/name-templates?entity_type=sample).
For bulk mode, apply to all uniques.
Output as: new CustomNamesManagement.tsx (full file), updates to AccessioningForm.tsx (full file with changes), and integration in MainLayout.tsx for nav."
Prompts for Project/Client Projects/Client Re-Work

## Prompt D: Database Migration for Project Auto-Creation Re-Work
"Refine the NimbleLIMS schema for project auto-creation during accessioning, based on recent planning (workflow-accessioning-to-reporting.md Stage 1, User Stories US-1/US-25, migrations like 0011_add_client_projects.py). Ensure projects.client_id is required (alter if needed), projects.client_project_id optional but encouraged.
No new tables, but add indexes if missing (e.g., idx_projects_client_id).
Generate Alembic migration (revision '0024', down_revision '0023') for any alterations, and update RLS policies (e.g., in projects_access and client_projects_access from 0022_fix_client_projects_rls.py) to allow auto-creation checks.
Seed example data if needed (e.g., link existing projects to clients).
Output as: migration file (0024_project_rework.py), updated schema_dump.sql snippets for RLS/policies."

## Prompt E: API Updates for Auto-Creation and Selection
"Implement backend changes for project auto-creation in accessioning (api_endpoints.md POST /samples/accession, Technical Document Section 3.1). Update endpoint to: Require client_id (fetch accessible via RLS), then optional client_project_id (validated against client).
If no project_id provided, auto-create project: name via template (from new name_templates), client_id from selection, client_project_id if provided, status default 'Active', created_by current user.
Assign new project_id to sample(s). Transactional for bulk.
Add cascading fetch: GET /client-projects?client_id={id} for filtering.
Enforce permissions: sample:create implies project:create if auto.
Update schemas: SampleAccessioningRequest add client_id (required), client_project_id (optional), make project_id optional.
Handle errors: 403 if client inaccessible, 400 if invalid linkage.
Output as: updated routers/samples.py, schemas/sample.py, and tests/test_accessioning.py with auto-creation cases."

## Prompt F: UI Updates for Client Selection and Auto-Creation
"Revamp the accessioning UI for client-first selection and project auto-creation (ui-accessioning-to-reporting.md SampleDetailsStep.tsx, AccessioningForm.tsx full file provided). In SampleDetailsStep: Add MUI Select/Autocomplete for client_id (fetch via apiService.get('/clients')), onChange fetch and filter client_project_id options (apiService.get('/client-projects', { params: { client_id } }))).
Remove project_id field/dropdown entirely.
In form schema (Yup), make client_id required, client_project_id optional.
In ReviewStep, display 'Project: Auto-Created' with preview name (if templates integrated, fetch preview via API).
For bulk mode, share client/client_project across uniques.
Add tooltips/help for cascade (e.g., 'Select client to filter projects').
Ensure RBAC: Clients pre-select their client_id (from UserContext).
Output as: updated AccessioningForm.tsx (full file), SampleDetailsStep.tsx (full file), ReviewStep.tsx (full file with preview), and any context updates."

# Navigation update and projects
## Prompt A: Update Navigation Documentation
"Update the NimbleLIMS navigation documentation based on recent planning refinements (navigation.md full structure, ui-accessioning-to-reporting.md for component architecture). Incorporate:

New 'Lab Mgmt' accordion (header: 'Lab Mgmt' with tooltip 'Lab Management'; requires project:manage permission; auto-expands on related routes).
Sub-items under 'Lab Mgmt': 'Projects' (route: /projects, icon: Folder, tooltip: 'Internal Projects' for core NimbleLIMS projects list/edit), 'Clients' (route: /clients, icon: People), 'Client Proj' (route: /client-projects, icon: ViewList, tooltip: 'Client Projects' for groupings).
Integrate with existing structure: Place after 'Sample Mgmt' accordion; maintain Core Features (Dashboard, Help) at top.
Update sections on accordion behavior, RBAC (e.g., project:manage for visibility), mobile adaptations, and future enhancements.
Ensure brevity principles: Headers <10 chars where possible, with ARIA labels/tooltips for accessibility.
Reference User Stories US-25 for client projects distinction. Output as: updated navigation.md (full file)."

## Prompt B: Update Sidebar and MainLayout Components
"Implement frontend navigation updates for NimbleLIMS using React/MUI, based on refined navigation.md. Include:

In Sidebar.tsx: Add 'Lab Mgmt' Accordion (expanded state managed via useState/useEffect for route matching; icon: SettingsApplications or similar; permission: project:manage via UserContext).
Sub-items: 'Projects' (ListItem to /projects, tooltip: 'Internal Projects'), 'Clients' (ListItem to /clients), 'Client Proj' (ListItem to /client-projects, tooltip: 'Client Projects'); use ListItemButton with icons, tooltips (MUI Tooltip), and active states (primary color on match).
Shortened labels with tooltips (e.g., 'Projects' aria-label='Internal Projects', 'Client Proj' aria-label='Client Projects'); indent sub-items (pl: 4).
Integrate with existing accordions (e.g., Sample Mgmt); ensure collapsed mode shows icons/tooltips only.
In MainLayout.tsx: Update route matching for auto-expand (e.g., if location.pathname.startsWith('/projects') || '/clients' || '/client-projects', expand Lab Mgmt).
Responsive: Permanent drawer on desktop, temporary on mobile; persist collapse state in localStorage.
RBAC: Hide accordion if !hasPermission('project:manage').
Ensure ESLint compliance; use TypeScript. Output as: updated Sidebar.tsx (full file), MainLayout.tsx (full file with changes)."

## Prompt C: Database and API for Internal Projects (If Needed; Assumes Existing Schema)
"Refine the NimbleLIMS backend for internal projects management, aligning with Technical Document Section 3 (projects table) and User Stories US-25 (distinction from client_projects). No schema changes needed (use existing projects table with client_project_id FK).

Add/ensure API endpoints: GET /projects (list with filters: status, client_id; pagination; RLS via projects_access policy), GET /projects/{id}, POST /projects (create with name, status, client_id, client_project_id optional), PATCH /projects/{id} (partial update), DELETE /projects/{id} (soft delete via active=false).
RBAC: Require project:manage for create/update/delete; read via RLS (has_project_access or admin).
Integration: Link to samples/tests via project_id; validate client_project_id if provided.
Use SQLAlchemy for queries; Pydantic schemas: ProjectBase, ProjectCreate, ProjectResponse (include custom_attributes if configured).
Output as: updated routers/projects.py (full file, assuming existing router), schemas/project.py (full file), and tests/test_projects.py (new cases for list/edit)."

## Prompt D: UI for Internal Projects Management
"Create the frontend UI for internal projects management in NimbleLIMS, based on ui-accessioning-to-reporting.md (page components like SamplesManagement.tsx) and navigation.md (new route /projects under Lab Mgmt).

New page: ProjectsManagement.tsx (route: /projects; MUI DataGrid for list: columns id, name, status, client_id, client_project_id, created_at; filters via GridToolbar).
Edit/Create: Dialogs with Formik/Yup (fields: name unique, status select from list_entries, client_id autocomplete from /clients, client_project_id from /client-projects?client_id={selected}; custom_attributes dynamic via CustomAttributeField.tsx).
RBAC: Page visible with project:manage (hide/edit buttons accordingly); use apiService for CRUD (/projects endpoints).
Integration: Link to related samples (e.g., button to /samples?project_id={id}); tooltips for guidance (e.g., 'Internal Projects: Core lab tracking units').
Responsive: DataGrid with horizontal scroll on mobile; use useMemo for configs.
Ensure ESLint/TypeScript compliance. Output as: new ProjectsManagement.tsx (full file), updates to apiService.ts (add project methods), and integration in App.tsx for routing (changes only)."


# Batch by test changes
## Prompt 1: Database Schema Updates for Prioritization Fields
"Refine the NimbleLIMS PostgreSQL schema to support sample prioritization based on expiration and due dates, referencing schema_dump.sql (samples/analyses/projects tables), nimblelims_tech.md (Section 3 Data Model), and nimblelims_user.md (US-11 for batches).

Add to samples: date_sampled (datetime optional, for expiration calc).
Add to analyses: shelf_life (integer optional, days for expiration = date_sampled + shelf_life).
Add to projects: due_date (datetime optional, for project-level turnaround; samples inherit if due_date null).
RLS: No changes needed, as access remains via has_project_access.
Indexes: Add on samples.date_sampled and analyses.shelf_life for query perf.
Migrations: Alembic script to add columns with defaults (null).
Output as: Updated schema_ddl.sql (full file with new columns), Alembic migration script (new file: migration_prioritization_fields.py)."

## Prompt 2: API and Backend Updates for Prioritization Logic
"Implement backend updates for sample prioritization in NimbleLIMS, based on api_endpoints.md (Samples/Batches sections), technical-accessioning-to-reporting.md (API Endpoints), and batches.md (Batch creation with QC).

Update GET /samples/eligible?test_ids=uuid1,uuid2: Compute days_until_expiration = (samples.date_sampled + analyses.shelf_life - now()).days (via SQLAlchemy interval); days_until_due = (coalesce(samples.due_date, projects.due_date) - now()).days; sort results by days_until_expiration ASC NULLS LAST, then days_until_due ASC NULLS LAST; include these fields in response; flag negatives (expired/overdue) with a boolean/warning message.
Update POST /batches/validate-compatibility: Add checks for expired samples (warn if any days_until_expiration < 0: 'Expired samples cannot be tested validly').
Schemas: Update EligibleSamplesResponse to include days_until_expiration (int nullable), days_until_due (int nullable), is_expired (bool).
Handle inheritance: Use coalesce for due_date (sample > project).
RBAC: No changes.
Output as: Updated routers/samples.py (add eligible endpoint logic), routers/batches.py (validation updates), schemas/sample.py (full file with changes)."

## Prompt 3: Frontend UI Updates for Prioritization Display
"Update the NimbleLIMS frontend to display and sort by sample prioritization, referencing ui-accessioning-to-reporting.md (BatchFormEnhanced.tsx), workflow-accessioning-to-reporting.md (Batch flow), and navigation.md (Batches).

In BatchFormEnhanced.tsx (Step 2: Eligible samples DataGrid): Add columns for days_until_expiration, days_until_due; default sort by days_until_expiration ASC, then days_until_due ASC; highlight negatives (red text/cell) with tooltip 'Expired: Testing invalid' or 'Overdue'.
On step change, call /batches/validate-compatibility and show warnings (MUI Alert) for expired/overdue samples.
apiService: Update getEligibleSamples to parse new fields; add sorting params if needed (but handle server-side).
Accessibility: ARIA labels for sorted columns (e.g., 'Sorted by expiration priority').
Output as: Updated components/batches/BatchFormEnhanced.tsx (full file), services/apiService.ts (method updates)."

## Prompt 4: Documentation and Testing Updates
"Update docs and add tests for sample prioritization in NimbleLIMS, aligning with nimblelims_user.md (US-11/26/27), batches.md (Overview/API), and nimblelims_tech.md (Workflows).

Docs: In batches.md, add Prioritization section (explain calcs, sorting); update US-11 in nimblelims_user.md (add criteria: prioritize by expiration > due, flag expired).
Tests: Pytest for eligible endpoint (mock dates, assert sorting/flags); Jest for UI (render DataGrid with priorities, check highlights/tooltips).
Output as: Updated batches.md (full file), nimblelims_user.md (US sections only), new tests/test_samples.py (eligible/prioritization cases)."

# Analysis Management
## Prompt 1 – Backend foundation: Analyses & Analytes CRUD endpoints

Implement complete CRUD API support for Analyses and Analytes in NimbleLIMS backend (FastAPI + SQLAlchemy), aligning with the existing style in routers/projects.py, routers/samples.py etc.

Requirements:

1. Analyses (table already exists: analyses)
   • Fields: id, name (unique), method (varchar), turnaround_time (int days), cost (numeric nullable), description (text nullable), active (bool), custom_attributes (jsonb), audit fields
   • Endpoints (router: /analyses):
     • GET    /analyses              → list with ?search= & ?active=true & pagination
     • GET    /analyses/{id}
     • POST   /analyses              → create (name unique, method required)
     • PATCH  /analyses/{id}         → partial update
     • DELETE /analyses/{id}         → soft delete (active=false)

2. Analytes (table already exists: analytes)
   • Fields: id, name (unique), cas_number (varchar nullable), units_default (FK units.id nullable), data_type (enum: numeric/text/date/boolean), description (text), active (bool), custom_attributes (jsonb), audit fields

   • Endpoints (router: /analytes):
     • GET    /analytes              → list + ?search= & ?active=true & pagination
     • GET    /analytes/{id}
     • POST   /analytes              → create (name unique)
     • PATCH  /analytes/{id}         → partial update
     • DELETE /analytes/{id}         → soft delete (active=false)

3. Analysis-Analyte relationship (junction table analysis_analytes already exists)
   • Add endpoints under /analyses/{analysis_id}/analytes
     • GET    /analyses/{analysis_id}/analytes          → list linked analytes
     • POST   /analyses/{analysis_id}/analytes          → link existing analyte(s)  { "analyte_ids": ["uuid1", "uuid2"] }
     • DELETE /analyses/{analysis_id}/analytes/{analyte_id} → unlink one

4. Use existing patterns:
   • Pydantic schemas: AnalysisBase, AnalysisCreate, AnalysisUpdate, AnalysisResponse (include linked analytes in Response if small)
   • RBAC: require_permission("analysis:manage") for create/update/delete
   • RLS: assume analyses & analytes are global / admin-only → no project-based RLS needed
   • Audit: set created_by / modified_by automatically

5. Add basic search (ilike on name + method / cas_number)

Output full files (replace or append as needed):
• routers/analyses.py          (complete router)
• routers/analytes.py          (complete router)
• schemas/analysis.py          (all schemas)
• schemas/analyte.py           (all schemas)
• dependencies.py              (add analysis:manage permission check if missing)

## Prompt 2 – Navigation updates (add menu items under Lab Mgmt)

Update the NimbleLIMS sidebar navigation to include Analyses and Analytes management pages under the "Lab Mgmt" accordion (which already contains Clients, Int Projs, Client Projs).

Follow the exact style from navigation.md and Sidebar.tsx:

• Add two new ListItemButton entries inside the Lab Mgmt Accordion → after "Client Projs"
  - "Analyses"   → route: /analyses    icon: Biotech     tooltip: "Analysis Methods"
  - "Analytes"   → route: /analytes    icon: Science     tooltip: "Measurable Analytes"

• Permission: show both items only if user has "analysis:manage" permission (use hasPermission from UserContext)

• Auto-expand "Lab Mgmt" accordion when location.pathname starts with "/analyses" or "/analytes"

• Keep labels short ("Analyses", "Analytes") + tooltip for clarity

• Update active route highlighting (primary color when matched)

Output full updated files:
• components/Sidebar.tsx                 (complete file with changes)
• layouts/MainLayout.tsx                 (only changes related to auto-expand logic)

## Prompt 3 – Analyses management page (list + create/edit dialog)

Create the Analyses management page for NimbleLIMS frontend (React + MUI + TypeScript).

Page: src/pages/AnalysesManagement.tsx
Route: /analyses (add to App.tsx routing)

Features (mirror SamplesManagement.tsx style):

• MUI DataGrid (premium if licensed, else free)
  Columns: name, method, turnaround_time (days), cost, active (chip), created_at
  Features: sort, filter (Toolbar), pagination, search on name/method

• FAB (+) → opens Create Dialog
• Edit icon per row → opens Edit Dialog (pre-filled)

• Dialog (Formik + Yup):
  Fields:
  - name            (required, unique check via API on blur if possible)
  - method          (required)
  - turnaround_time (number, min 0)
  - cost            (number, min 0, nullable)
  - description     (multiline)
  - active          (switch)
  - Custom attributes (dynamic via CustomAttributeField.tsx — entity_type="analyses")

• RBAC: hide FAB & edit buttons if !hasPermission("analysis:manage")

• API integration via apiService.ts:
  - getAnalyses(params)
  - createAnalysis(data)
  - updateAnalysis(id, data)

• Loading state, error snackbar, success toast

• Responsive: horizontal scroll on mobile

Output:
• pages/AnalysesManagement.tsx          (full new file)
• services/apiService.ts                (append new methods: getAnalyses, createAnalysis, updateAnalysis)
• App.tsx                               (only routing changes)

## Prompt 4 – Analytes management page (similar structure)

Create the Analytes management page for NimbleLIMS (very similar to AnalysesManagement.tsx).

Page: src/pages/AnalytesManagement.tsx
Route: /analytes

Features:

• MUI DataGrid
  Columns: name, cas_number, units_default (name from units), data_type (chip: Numeric/Text/Date/Boolean), active, created_at

• Create / Edit Dialog (Formik + Yup):
  - name            (required, unique)
  - cas_number      (optional)
  - units_default   (Autocomplete – fetch from /units)
  - data_type       (Select: numeric | text | date | boolean)
  - description     (multiline)
  - active          (switch)
  - Custom attributes (entity_type="analytes")

• RBAC: analysis:manage controls visibility of create/edit

• apiService methods needed:
  - getAnalytes(params)
  - createAnalyte(data)
  - updateAnalyte(id, data)

Output:
• pages/AnalytesManagement.tsx          (full new file)
• services/apiService.ts                (append getAnalytes, createAnalyte, updateAnalyte)
• App.tsx                               (routing changes only)

## Prompt 5 – Optional: Link analytes to analysis (nice-to-have next step)

Add the ability to manage which analytes belong to each analysis (many-to-many via analysis_analytes junction).

Enhance AnalysesManagement.tsx:

When editing an Analysis, add a new tab or expandable section "Linked Analytes"

• MUI DataGrid showing currently linked analytes (name, cas_number, data_type)
• Button "Add Analyte" → Autocomplete search from all analytes (GET /analytes?search=)
• Remove icon per row → unlink

API calls:
• POST   /analyses/{id}/analytes       { "analyte_ids": [...] }
• DELETE /analyses/{id}/analytes/{analyteId}

Backend already has these endpoints from earlier prompt.

Frontend:
• Use apiService.createAnalysisAnalytes(analysisId, {analyte_ids})
• apiService.deleteAnalysisAnalyte(analysisId, analyteId)

Output: updated AnalysesManagement.tsx (full file with analyte linking section)

# Client Isolation
## Prompt 1: Schema Update for System Client Handling
"Based on the NimbleLIMS Technical Document (Section 3: Security and RBAC) and schema in schema_ddl.sql, enhance the database schema to support a 'System' client for lab employees. Ensure all users require a non-null client_id for better integrity.
Steps:

Add a CHECK constraint to users table: client_id NOT NULL (to prevent forgotten assignments).
Update seed data in migrations to include a 'System' client (name: 'System', active: true) if not already present.
Set lab employee users (e.g., admin, lab-manager, lab-tech) to have client_id referencing the System client.
For client users, client_id references their specific client.
No changes to projects.client_id—projects still belong to specific clients, but access logic will special-case System.

Output:

Updated db/migrations/versions/xxxx_add_system_client.py (full Alembic migration file with up/down functions).
Updated schema_ddl.sql (full file with new CHECK).
Note: Run this after existing migrations to avoid conflicts."

## Prompt 2: Enhance RLS Policies for Client Isolation
"Implement enhanced Row-Level Security (RLS) policies to limit data access for client users to only their own data, using the System client for lab employees. Reference Technical Document (Section 3: RLS Policies) and PRD (Section 3.1: Data Isolation). Assume System client exists (from prior migration).
Key Logic in has_project_access function:

Get current_user.client_id.
If user.client_id == System_client_id (hardcode or query by name='System'), return TRUE (full access for lab staff).
Else (regular client), check if project.client_id == user.client_id.
Fallback to project_users junction for granular grants (e.g., lab staff assigned to specific projects, though System should cover most).
Apply to policies: projects_access, samples_access, tests_access, results_access, client_projects_access, batches_access.
For containers_access: Via samples (since containers link to samples.projects).
Enable RLS on all relevant tables if not already.

Output:

Updated schema_functions.sql (full file with modified has_project_access).
Updated schema_rls.sql (full file with CREATE POLICY statements).
Updated db/migrations/versions/xxxx_enhance_rls_for_clients.py (full Alembic file to apply policies)."

## Prompt 3: API Endpoint Adjustments for Access Control
"Update FastAPI endpoints to enforce client data isolation at the API layer, complementing RLS. Based on api_endpoints.md and Technical Document (Section 4: API Endpoints). With System client, ensure queries for non-System clients auto-filter via RLS (no Python changes needed), but add permission checks.
Steps:

In routers (e.g., projects.py, samples.py), use depends(get_current_user) to fetch user.
For list endpoints (GET /projects, /samples, etc.), rely on RLS for filtering—no manual SQL filters.
Add explicit checks: If user.role != 'Administrator' and user.client_id != System_client_id, ensure no broad access (but RLS handles this).
For create/update (POST/PATCH), validate project.client_id matches user.client_id if not System/Admin.
Error: 403 if mismatch.
Update schemas to include client_id validation where needed.

Output:

Updated backend/app/routers/projects.py (full file with checks).
Updated backend/app/routers/samples.py (full file).
Similarly for tests.py, results.py, client_projects.py, batches.py (full files).
Updated api_endpoints.md (full file with new notes on isolation)."

## Prompt 4: Frontend UI Adjustments for Visibility
"Modify React frontend to respect client data isolation, ensuring client users only see their data in UI components. Reference ui-accessioning-to-reporting.md and navigation.md. With System client, lab users (System client_id) see all; clients see only theirs.
Steps:

In apiService.ts, add client_id to query params for list fetches if user.client_id != System (but rely on backend RLS).
In pages like ProjectsManagement.tsx, SamplesManagement.tsx: Use UserContext to check if user.client_id is System; if not, display filtered DataGrid (API returns filtered).
Hide admin/lab mgmt sections for non-System clients via permission gating (already in Sidebar.tsx).
Add loading/error states for access denied.
Update UAT scripts to test: Client sees only their projects/samples.

Output:

Updated frontend/src/services/apiService.ts (full file with conditional params).
Updated frontend/src/pages/ProjectsManagement.tsx (full file).
Updated frontend/src/pages/SamplesManagement.tsx (full file).
Similarly for other management pages (full files).
Updated uat-security-rbac.md (full file with new test cases for client isolation)."