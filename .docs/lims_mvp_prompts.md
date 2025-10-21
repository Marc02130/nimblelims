### Overview of Prompts for Cursor Implementation

Based on our ongoing planning discussions, the attached documents (PRD, User Stories, and Technical Document) provide a comprehensive blueprint for the LIMS MVP. To align with the iterative approach and the sprint-based roadmap in the User Stories document, I've structured the prompts for Cursor below. Each prompt is self-contained, references the relevant sections from the documents, and focuses on one major aspect or sprint to allow for incremental development. This ensures we can refine and test each part before moving on.

These prompts emphasize:
- **API-first design**: All backend logic via FastAPI endpoints.
- **Tech stack**: PostgreSQL (schema with RLS, triggers), Python (FastAPI, SQLAlchemy, PyJWT, passlib[bcrypt]), React (with Axios, React Router, Material-UI).
- **Best practices**: PEP8 for Python, ESLint for React; unit/integration tests; Docker containerization (three containers: DB, backend, frontend).
- **Security**: JWT auth, RBAC with ~15 permissions, RLS for data isolation.
- **Iteration**: Build in layers, starting with data model and auth.

Use these prompts sequentially in Cursor, copying them directly into the editor's AI prompt interface. After each, review the generated code, commit to version control (e.g., Git), and we can discuss refinements here before proceeding.

#### Prompt 1: Project Setup and Docker Configuration
"Create the initial project structure for the LIMS MVP based on the Technical Document (sections 1.3, 2.1, 7.2). Include:
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
"Implement the PostgreSQL database schema for the LIMS MVP core tables as detailed in the Technical Document (section 3) and PRD (section 7.1), focusing on Sprint 1 user stories (US-1, US-5, US-7, US-12). Use SQL scripts for creation.
- Include standard fields on all tables: id (UUID PK), name (varchar unique), description (text), active (boolean default true), created_at (timestamp default NOW()), created_by (UUID FK users.id), modified_at (timestamp), modified_by (UUID FK users.id).
- Key tables: users (with username unique, password_hash, email unique, role_id FK roles.id, client_id FK clients.id nullable, last_login), roles, samples (due_date, received_date, report_date, sample_type FK list_entries.id, status FK, matrix FK, temperature numeric, parent_sample_id FK samples.id nullable, project_id FK projects.id, qc_type FK nullable), containers (row int default 1, column int default 1, concentration numeric, concentration_units FK units.id, amount numeric, amount_units FK units.id, type_id FK container_types.id, parent_container_id FK containers.id nullable), contents (container_id FK, sample_id FK, concentration numeric, concentration_units FK, amount numeric, amount_units FK; unique container_id+sample_id), container_types (capacity numeric, material varchar, dimensions varchar, preservative varchar), tests (sample_id FK, analysis_id FK analyses.id, status FK, review_date nullable, test_date nullable, technician_id FK users.id), analyses (method varchar, turnaround_time int, cost numeric), projects (start_date, client_id FK, status FK), clients (billing_info JSONB default '{}'), list_entries (list_id FK lists.id), lists, units (multiplier numeric, type FK list_entries.id).
- Indexes: On all FKs; unique on names.
- Triggers: For audit fields (e.g., BEFORE INSERT/UPDATE set created_at/modified_at).
- RLS: Basic policies, e.g., on samples: ENABLE ROW LEVEL SECURITY; CREATE POLICY user_access ON samples USING (project_id IN (SELECT project_id FROM project_users WHERE user_id = current_setting('app.current_user_id')::UUID));
- Use Alembic for migrations in backend/db/migrations.
Reference User Stories for fields like qc_type. Ensure normalized schema with cascades where appropriate."

#### Prompt 3: Backend Authentication and User Management (US-12)
"Implement the backend authentication for the LIMS MVP using FastAPI, based on Technical Document (section 4.1) and User Stories (US-12, US-13).
- Setup: app/main.py with FastAPI app; routers for auth.
- Dependencies: SQLAlchemy ORM models from schema (users, roles, permissions, role_permissions); session dependency.
- Endpoints: POST /auth/login (body: username, password; verify with bcrypt, return JWT with user_id, role, permissions); POST /auth/verify-email (body: email, token; stub for now).
- JWT: Use PyJWT; encode/decode with secret; validate in dependencies.
- RBAC: Define ~15 permissions (e.g., 'sample:create', 'result:enter') in DB; load user permissions from role_permissions.
- Security: Dependency for current_user; set current_user_id in DB session for RLS.
- Tests: Pytest for login success/failure, token validation.
Follow PEP8; include Pydantic schemas for requests/responses."

#### Prompt 4: Backend Endpoints for Samples, Containers, and Tests (Sprint 1: US-1, US-5, US-7)
"Build FastAPI backend endpoints for samples, containers, and tests in the LIMS MVP, aligning with Technical Document (section 4.2) and User Stories (US-1, US-5, US-7).
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
"Create the React frontend setup and authentication components for the LIMS MVP, based on Technical Document (section 5) and User Stories (US-12).
- Setup: Create React app with React Router, Axios (for API calls to backend at http://localhost:8000), Material-UI for styling; state management with Context API (for user/session).
- Components: Login form (username/password, call POST /auth/login, store JWT in localStorage); Email verification modal (POST /auth/verify-email).
- Routing: Protected routes with auth check (decode JWT).
- UI: Responsive; Formik/Yup for validation.
- Tests: Jest for components.
Follow ESLint; include axios interceptors for JWT headers."

#### Prompt 6: Frontend Components for Sample Accessioning and Management (Sprint 1: US-1, US-5, US-7)
"Implement React frontend components for sample accessioning, container management, and test assignment in the LIMS MVP, per User Stories (US-1, US-5, US-7) and Technical Document (section 5.1).
- Components: Accessioning form (multi-step wizard: fields like due_date, sample_type; optional double-entry; assign tests; submit to POST /samples then /tests); Container assignment (select type, add contents); Dashboard view (list samples filtered by status/project).
- Integration: Axios calls to backend endpoints; real-time validation.
- State: Use Context for user data; handle loading/errors.
- UI: Material-UI forms/tables; accessibility with ARIA.
- Tests: Jest for form submission, rendering.
Ensure alignment with workflows in PRD section 5.1."

#### Prompt 7: Backend and DB for Aliquots, Pooling, Results, Batches (Sprint 2: US-3, US-6, US-9, US-11)
"Extend the FastAPI backend and Postgres schema for aliquots/derivatives, pooling, results entry, and batches in the LIMS MVP, based on User Stories (Sprint 2) and Technical Document (sections 3,4).
- Schema additions: Batches (type FK, status FK, dates); batch_containers (batch_id FK, container_id FK, position, notes); results (test_id FK, analyte_id FK analytes.id, raw_result, reported_result, qualifiers FK, calculated_result nullable, entry_date, entered_by FK).
- Endpoints: POST /samples/aliquot or /derivative (with parent_id, inherit properties); POST /contents (for pooling, compute volumes using units multipliers); POST /batches (create, add containers via /batch-containers); POST /results (batch-based, validate per analysis_analytes).
- Logic: Conversions (e.g., volume = amount / concentration, normalized via multipliers); update statuses.
- RBAC: Permissions like 'sample:create', 'result:enter'.
- Tests: Pytest for calculations, creations.
Update Alembic migrations."

#### Prompt 8: Frontend for Aliquots, Batches, and Results (Sprint 2)
"Add React components for aliquots/derivatives, batches, and results entry in the LIMS MVP frontend, aligning with User Stories (Sprint 2) and Technical Document (section 5).
- Components: Aliquot/Derivative creation form (select parent, submit to POST /samples/...); Batch view (create batch, add containers, grid for plates/wells); Results entry table (select batch/test, enter per analyte, validation).
- Integration: Axios to new endpoints; handle pooling calculations display.
- UI: Tables for batches; real-time updates.
- Tests: Jest for workflows."

#### Prompt 9: Backend RBAC, Data Isolation, and Configurations (Sprint 3: US-13, US-14, US-15, US-16)
"Implement full RBAC, data isolation, and configurations in the FastAPI backend for LIMS MVP, per User Stories (Sprint 3) and Technical Document (sections 3.2,4.3).
- Schema: Permissions, role_permissions; project_users (project_id FK, user_id FK, access_level FK, granted_at, granted_by FK); update RLS policies for all tables (e.g., using current_user_id).
- Endpoints: CRUD /roles, /permissions, /lists, /units (admin-only); all queries filter by user context (e.g., client_id).
- RBAC: Dependency injection for permission checks; load permissions on login.
- Configurations: Manage lists/list_entries, units with multipliers/types.
- Tests: Pytest for access denials, configs."

#### Prompt 10: Frontend for Security and Configurations (Sprint 3)
"Extend React frontend for RBAC management and configurations in LIMS MVP, based on User Stories (Sprint 3).
- Components: Admin dashboard for roles/permissions CRUD; Config forms for lists/units.
- Integration: Role-based views (e.g., client sees only own projects); Axios with permission checks.
- UI: Conditional rendering based on user role."

#### Prompt 11: Backend and Frontend for Statuses, QC, Reviews (Sprint 4: US-2, US-4, US-8, US-10)
"Complete backend and frontend for status management, QC handling, and reviews in LIMS MVP, per User Stories (Sprint 4).
- Backend: PATCH endpoints for statuses (samples/tests); include qc_type in samples; PATCH /tests/{id}/review.
- Frontend: Update forms/views for statuses, QC flags, review workflows.
- Tests: Full coverage."

#### Prompt 12: Testing, Deployment, and Polish
"Add testing and finalize deployment for LIMS MVP, based on Technical Document (section 7).
- Tests: Pytest (backend unit/integration), Jest (frontend), Cypress (E2E).
- Deployment: Update docker-compose for prod; CI/CD stubs in GitHub Actions.
- Polish: Error handling, logging (Sentry stub), migrations."

Once you've run these in Cursor and have the code base, we can resume here to summarize decisions or refine based on any issues. What's one specific aspect you'd like to clarify or adjust before proceeding to implementation?