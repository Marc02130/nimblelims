# NimbleLIMS - Laboratory Information Management System

A modern, API-first LIMS built specifically for BioTech and Pharma startups. NimbleLIMS provides the **core foundation for lab operations**: track samples (receive, status, lineage), record **requested analysis** in the asked-for lake (a later look-up — not a Test, not the click after receive), and enter results (capture and review). Purpose-built for small R&D teams with basic LIMS needs, featuring role-based access, CRO partner isolation, and an extensible platform that supports optional enhancements (dose-response analysis, ELN experiment tracking, instrument data import) when customer requirements emerge. Powered by FastAPI, React, and PostgreSQL.

**How to run the lab path:** [manuals/HOWTO.md](manuals/HOWTO.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Marc Breneiser

## Architecture

This project uses a four-container Docker setup:

- **Database (PostgreSQL 15+)**: Data persistence with Row-Level Security
- **Backend (FastAPI + Python 3.10+)**: RESTful API with JWT authentication and RBAC
- **Frontend (React 18+)**: Modern web interface with TypeScript
- **R Calculator (Plumber API)**: Optional microservice for dose-response curve fitting (4PL model, IC50, SVG generation) — shipped enhancement, not MVP

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nimblelims
   ```

2. **Start the services**
   ```bash
   docker-compose up -d --build
   ```
   
   This will automatically:
   - Start the database container
   - Wait for database to be ready
   - Run Alembic migrations (creates all tables, roles, permissions, and admin user)
   - Start the backend API server
   - Start the frontend web server

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database: localhost:5432 (local compose only — **S12:** production uses `docker-compose.prod.yml` which does **not** publish Postgres)

4. **Login with admin credentials**
   - Username: `admin`
   - Password: `admin123`
   - **⚠️ IMPORTANT**: Change the default password immediately after first login!
   - See [manuals/admin-setup.md](manuals/admin-setup.md) for detailed security instructions

5. **Run migrations (if needed)**
   ```bash
   docker exec lims-backend python run_migrations.py
   ```
   This ensures all migrations are applied, including the latest `batch:read` permission.

## Test Data and Scenarios

NimbleLIMS includes comprehensive BioTech/Pharma test data for UAT and automated testing. See **[UAT_Scripts/test-data-scenarios.md](UAT_Scripts/test-data-scenarios.md)** for the full catalog.

### Quick Start with Test Data

The test dataset is automatically loaded when running database migrations:

```bash
# Docker environment (recommended)
sudo docker compose up -d --build

# Database migrations apply automatically on startup
```

### What's Included

- **2 clients** (NovaBio Therapeutics, PharmaTest CRO) with RLS isolation
- **8 users** across 4 roles: admin, lab techs, managers, client
  - Default logins: `admin/admin123`, `lab-tech/labtech123`, `alice-tech/alice123`, `bob-tech/bob123`, etc.
- **6 projects** (mAb PK study, CAR-T in-process, plasmid lot release, CRO services)
- **7 samples** spanning full lifecycle (Received → Available → Testing Complete → Reviewed)
- **Parent/aliquot chains**, **QC samples**, **batches**, **tests**, **results**
- **Edge cases**: depleted parent (50µL remaining), QC blanks, zero results

### Using Test Data

**For UAT**: Login with any test user and explore realistic lab data:
```
alice-tech / alice123    → Lab Technician (mAb PK project)
bob-tech / bob123        → Lab Technician (CAR-T project)
carol-manager / carol123 → Lab Manager (all NovaBio projects)
```

**For Automated Tests**: Import fixtures from `tests/fixtures/seed_data_fixtures.py`:
```python
from tests.fixtures.seed_data_fixtures import alice_user, mab_pk_sample

def test_sample_access(db_session, alice_user, mab_pk_sample):
    assert mab_pk_sample.created_by == alice_user.id
```

See `backend/tests/test_seed_data_usage_example.py` for example tests.

### Data Scenarios

Full catalog with 10+ scenarios covering:
- Sample lifecycle workflows: receive loop (stay on `/receive`); separately, requested analysis in the lake; separately, results → review
- Multi-user RBAC (project isolation, permission enforcement)
- QC sample handling (blanks, controls)
- Edge cases (depleted parents, zero results, incomplete tests)

See **[test-data-scenarios.md](UAT_Scripts/test-data-scenarios.md)** for details.

---

### Development

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend Development
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
nimblelims/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── routers/        # API route handlers
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   └── core/           # Core utilities (config, security, rbac)
│   ├── models/              # SQLAlchemy database models
│   ├── db/                  # Database migrations
│   │   └── migrations/     # Alembic migration files
│   ├── tests/               # Test files
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile          # Backend container config
│   ├── start.sh            # Startup script (runs migrations)
│   ├── run_migrations.py   # Migration runner
│   ├── run_server.py       # Development server runner
│   └── env.example         # Environment variables template
├── frontend/               # React frontend
│   ├── src/                # Source code
│   ├── public/             # Static assets
│   ├── package.json        # Node.js dependencies
│   ├── Dockerfile          # Frontend container config
│   ├── nginx.conf          # Nginx configuration
│   └── .eslintrc.js        # ESLint configuration
├── db/                     # Database setup
│   ├── Dockerfile          # Database container config
│   └── init.sql            # Database initialization
├── .docs/                  # Documentation root
│   ├── review/             # Review stamps, tech sketches, process, OQs
│   ├── internal/           # Working PRDs, specs, design, ideas (git-tracked)
│   ├── discussions/        # Multi-persona Leadership discussions
│   └── decision-logs/      # Leadership stamps (FW/WO, reorg)
├── services/               # Auxiliary microservices
│   └── r-calculator/       # Plumber R API for curve fitting
│       ├── R/              # Curve fitting, categorization, SVG generation
│       ├── plumber.R       # API routes
│       └── tests/          # R unit tests
├── docker-compose.yml      # Multi-container orchestration
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Features (MVP Scope)

**Note:** This section describes **all implemented features in the codebase**. However, the **MVP release bar** focuses on three core pillars: (1) **track samples** (receive, status, lineage), (2) **requested analysis** (asked-for lake — a later look-up that does **not** assign a Test or start work), and (3) **enter results** (capture and review). Additional features listed below (ELN experiments, dose-response analysis, LimsRuns/parsers, workflow templates, custom fields) are **shipped/in-tree but not the MVP release bar**—they are enhancements that demonstrate platform capability and remain available for users who need them. See [`.docs/internal/prd/nimblelims-prd.md`](.docs/internal/prd/nimblelims-prd.md) for the complete MVP definition.

### Core Workflows for BioTech/Pharma Startups (**MVP Release Bar** + Shipped Enhancements)
- **Compound & Sample Tracking** **(MVP)**: Receive (`/receive`), status management, lineage (aliquots/derivatives), container hierarchy. Non-empty `analysis_ids` on receive → **422**.
- **Requested analysis** **(MVP, P1)**: **Asked-for** (`/asked-for`) records requested analysis + TAT for already-received samples (zero Tests, no execute). A later look-up, not the after-receive step — receive ends on `/receive`. See [manuals/HOWTO.md](manuals/HOWTO.md), [manuals/asked-for.md](manuals/asked-for.md), and `UAT_Scripts/uat-post-receive-work-spine.md`. Classic `/tests` is not the request path.
- **Route / work orders (P2):** A route is TAT + ordered `process_definition[]` and **may have multiple LimsRun analyses**; no analysis or type picker. Asked-for assay matches **any** route that **contains** that analysis (plus first-step type + TAT). Map save **409**s when overlapping TAT, first-step types, **and** LimsRun analysis **sets** all hold. Map save **422**s when process *x* emerging type is not accepted by *x+1* (**map-save only**). Live product SHA **`1572071`**. Signed AC-P2-9..11 history: `9342439`. Deiter Contents click on product `4671ba8` / assignment commit `02fe95f` (`0077`): C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Leadership Confirmed that click; C1/C2 are **not** unsigned. Live AC-P2-C2 on `1572071` is **unsigned** until Tobias (dest-follow in execute txn, emptied-source **422**, same-sample dest container — in code, not QA-clicked; do not teach dest-follow as shipped). Dest mint Hold Pass is a different punch (still Blood, **0 DNA**). Docs Confirm `84d2810` is not a new execute and not the click SHA. Freeze skip **OPEN**. **OQ-WO-6 stays OPEN**. Overall P2 unsigned / not Pass. Hold product merge. Not IC50. Send: [`.docs/discussions/2026-08-30-p2-route-lock.md`](.docs/discussions/2026-08-30-p2-route-lock.md).
- **Results Entry** **(MVP)**: Manual results entry with real-time validation
- **Batch Management** **(MVP + Enhancements)**: Create and manage batches (basic is MVP; cross-project support, automatic QC generation, and sample prioritization are shipped enhancements)
- **Sample Prioritization** **(Shipped, Not MVP)** (US-11): Sort compounds and biological samples by shelf-life expiration and assay deadlines during batch creation
- **Aliquots/Derivatives** **(MVP)**: Create daughter vials, working stocks, or processed samples (e.g., lysates, extracts) with full lineage
- **Bulk Accessioning** **(Shipped, Not MVP)** (US-24): Accession multiple compounds or samples with shared metadata and per-item identifiers
- **Cross-Project Batching** **(Shipped, Not MVP)** (US-26): Batch samples from multiple discovery projects with compatibility validation
- **QC at Batch Creation** **(Shipped, Not MVP)** (US-27): Automatically generate control wells (blanks, spikes, standards) when creating assay batches
- **Batch Results Entry** **(Shipped, Not MVP)** (US-28): Enter plate-reader or instrument results for multiple samples/wells atomically
- **Workflow Templates** **(Shipped, Not MVP)** (US-29): Define reusable protocols (e.g., cell-based assay SOPs) and apply from accessioning, batch, or results entry. Requires config:edit (template CRUD) and workflow:execute (apply template) permissions.

### Dose-Response Analysis **(Shipped, Not MVP)** (BioTech/Pharma Enhancement)
- **Curve Fitting**: Trigger 4-parameter logistic (4PL) curve fitting on dose-response data via R calculator microservice. Supports percent-inhibition normalization using positive/negative control wells.
- **CRO Lifecycle**: Experiment templates support `cro` lifecycle for externally managed experiments with CRO partner ordering workflow.
- **Curve Curator**: Tabbed review UI (`/runs/:id/dose-response`) with category sidebar (Sigmoid, Inactive, Inverse Agonist, Hook Effect, etc.), curve grid with SVG thumbnails, per-compound detail view with Plotly chart, batch approve/reject, and data point knockout (exclude individual wells with reason—critical for screening QC).
- **IC50 Summary**: Dashboard summary of fit results by category and review status; re-fit and reset-in-progress controls.
- **Audit Trail**: Every curve fit is versioned (`fit_version`); superseded results preserved. Data exclusions are soft (reason-tracked), control-well exclusions apply to normalization means.

### LIMS Runs → Structured Results **(Shipped, Not MVP)** (promote-on-publish)
- **Analysis required**: Every LimsRun (e.g., plate reader output, screening campaign) has an **Analysis** from create (no non-reportable path).
- **Import remains flexible JSONB** (`lims_run_data`); parsers/import are analysis-scoped for different instrument vendors.
- **Promote on publish**: Status → `published` maps columns to analytes (name + **aliases** for CRO/instrument vendor column names) and writes **Results** (`raw_result`, `replicate`, `lims_run_id`) only into active Tests from first start of the asked-for analysis. If any cohort Test is missing, WO-7 refuses the whole publish with **422**. Publish-refuse is Tobias-signed Pass on `8cfa2a9` (carol **422** `test_missing`) and remains history on `b005cfe`. A write of `{}` onto Test `99b692d3` is not a freeze-skip Pass (`{}` is ambiguous). Do **not** fold classic `/tests` skip as Pass. `if test: continue` is not a freeze. Classic `/tests` must leave `asked_for_params` NULL, or we need a freeze marker. Until then `{}` is **ambiguous** — a classic default `{}` is the same JSON as a frozen `{}`, so first start cannot tell them apart. Do not teach skip-on-frozen-`{}`. Overall P2 Pass remains unsigned.
- **Conflicts**: Same run updates; other run/manual ownership fails publish with **409** to protect data integrity.
- **Preview**: Publish confirmation dry-runs create/update/conflict/unresolved columns (`GET /v1/lims-runs/{id}/promotion/preview`).
- **Docs**: [manuals/HOWTO.md](manuals/HOWTO.md) · [manuals/lims-runs.md](manuals/lims-runs.md) · [`.docs/internal/ideas/run-results.md`](.docs/internal/ideas/run-results.md).

### Experiment Management **(Shipped, Not MVP)** (ELN-style Process Tracking)
- **Experiments**: Full CRUD for experiments; list/detail UI with tabs (Overview, Sample Executions, Details/Steps, Lineage, Linked Processes). Permission: `experiment:manage` (Administrator, Lab Manager, Lab Technician).
- **Experiment Templates**: `/experiments/templates` — **Basic Info** + **Tables & forms** (`entries[]`: experiment sample metadata, multi-row protocol tables, aliquot/pool steps). **Create field** defines entry columns (`field_definitions` for entity types `experiment_sample_data` / `experiment_data`—not Custom Fields on Sample/Test). Instantiate on experiment create/start. Cohort start: scan/select samples (`StartCohortPanel`); target is accordion-style process → queue dual-list start dialog. Permission: `experiment:manage`.
- **ELN Processes (Phases 1–3)**: Definitions → instances with typed steps (`eln_experiment` \| `lims_run`). APIs: `/v1/eln-process-definitions`, `/v1/eln-processes`, sample journey `GET /v1/samples/{id}/journey`. UI at `/experiments/processes` (Instances + Definitions). Soft advance gates; lazy LimsRun start; run history. Migrations `0047`–`0051`. Distinct from LIMS run checklists under `/v1/processes`. Checklist: [`.docs/review/checklist/experiment-checklist.md`](.docs/review/checklist/experiment-checklist.md).
- **Sidebar**: Dedicated **Experiments** accordion (between Sample Mgmt and Lab Mgmt) with sub-items **All Experiments** and **Experiment Templates** (both require `experiment:manage`).
- **Sample ↔ experiment linking**: Link samples to experiments (roles, processing conditions, replicate); bidirectional UI: experiment detail links to samples (`/samples?highlight=id`); sample detail shows "Participated in these Experiments" with links.
- **Lineage**: Experiment lineage view (template + linked experiment IDs); loading and error states.
- **My Experiments filter**: List page supports `?mine=true` to show only experiments created by the current user.
- **Workflow integration**: Workflow actions `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`; context carries `experiment_id` and `execution_id` for downstream steps.

### Container System **(MVP + Shipped Enhancements)**
- **Container Types** **(MVP)**: Pre-setup by administrators (CRUD via admin interface)
- **Container Instances** **(MVP)**: Created dynamically during workflows (accessioning, aliquoting)
- **Hierarchical Support** **(MVP)**: Parent-child relationships (plates → wells, racks → tubes)
- **Pooled Samples** **(Shipped, Not MVP)**: Multiple samples per container with concentration/amount tracking
- **Units Integration** **(Shipped, Not MVP)**: Concentration and amount with unit conversions

### Configuration Management **(MVP + Shipped Enhancements)**
- **Name Templates**: Configurable entity naming (sample, project, batch, etc.) with placeholders ({SEQ}, {PROJECT}, {CLIENT}/{CLIABV}, {YYYY}, {YY}, seq_padding_digits). {SEQ} is scoped by “name without SEQ” (e.g. per project for samples), so each project gets its own sequence (01, 02, …). Sequence start API (admin interface removed; use API directly).
- **Field Management** (replaces legacy Custom Attributes): Unified admin UI for OOB (built-in/list-backed) + Custom fields per entity. Prefers list-backed fields (source list from central Lists system) for reusability across Samples and Entries/Processes. Validation rules for scalars. OOB fields denoted and editable for rules. Legacy admin UIs for Custom Attributes and Name Templates have been removed from sidebar (routes deprecated).
- **Lists Management**: Full CRUD for lists and list entries via admin interface - create lists, add/edit/delete entries for statuses, assay types, QC types, compound matrices (solvent, buffer, cell media), etc. Empty lists display expand arrows to add entries. Used to back list fields in Field Management.
- **Container Types**: Admin-managed container type definitions (tubes, plates, wells, reservoirs) - CRUD operations for capacity, material, preservatives.
- **Analyses Management**: Create and manage assays (cell viability, binding, ADME panels) with methods, turnaround times, costs, and custom attributes. Features expandable grid rows to view and manage linked analytes (IC50, Emax, AUC, etc.) directly from the main list (CRUD). Available in both Admin section and Lab Mgmt accordion. Used as the opt-in assay for LIMS run promote-on-publish.
- **Analytes Management**: Create and manage measurable endpoints (IC50, % inhibition, Emax, Kd, clearance) with units, data types, **aliases** (instrument/CRO vendor column names for auto-mapping), and custom attributes (CRUD). Available in both Admin section and Lab Mgmt accordion.
- **Analysis-Analyte Linking**: Link/unlink analytes to analyses via expandable detail panels with inline autocomplete search
- **Analysis-Analyte Configuration**: Configure validation rules (data types, ranges, significant figures, required flags)
- **Test Batteries Management**: Group multiple analyses into reusable assay panels (e.g., "ADME Panel", "Kinase Selectivity Panel") with sequence ordering and optional flags (CRUD)
- **Field Management** (Custom Fields UI): See above for OOB+Custom with list-backed preference.
- **Client Projects Management**: Group multiple LIMS projects under client projects for holistic tracking (CRUD)
- **Users Management**: Create and manage users with role assignments (CRUD)
- **Roles & Permissions**: Manage roles and assign permissions (CRUD)
- **Units Management**: Unit definitions with multipliers for conversions
- **Workflow Templates Management** **(Shipped, Not MVP)**: Create, edit, and deactivate workflow templates (JSON steps with actions). Execute templates from the admin list with optional context, or use "Apply Template" on Accessioning (context empty), Batch details (context batch_id), and Results Entry (context batch_id, test_id). Visible only with config:edit (admin) and workflow:execute (apply).

### Security & Access **(MVP)**
- **Authentication**: JWT token-based authentication
- **Authorization**: Role-Based Access Control (RBAC) with 17 granular permissions (sample:create, result:enter, experiment:manage, etc.)
- **Data Isolation**: CRO partner and client-specific data access controls via project_users junction table
- **Row-Level Security**: PostgreSQL RLS policies for data protection at the database level. `FORCE ROW LEVEL SECURITY` ensures enforcement even for table owner role (no bypass on direct DB connections).
- **Samples Access Control**: The `GET /samples` endpoint relies entirely on RLS for access control—no Python-level filtering. Lab Technicians and Lab Managers see samples from projects they have access to via the `project_users` table. CRO partner users see samples from their client's projects. Administrators see all samples.
- **Experiment Engine Isolation**: The 5 flexible experiment engine tables (`lims_runs`, `lims_run_data`, `instrument_parsers`, `robot_worklist_configs`, `sop_parse_jobs`) use client-scoped RLS: users only see rows created by members of their own client organization. Admins see all. Enforced at the database layer regardless of the API code path.

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

## Development Standards

- **Python**: PEP8 compliance with type hints
- **React**: ESLint configuration with TypeScript
- **Database**: Normalized PostgreSQL schema with UUIDs
- **Security**: JWT tokens, bcrypt password hashing, RLS policies

## Environment Variables

Copy `backend/env.example` to `backend/.env` and configure:

- Database connection settings
- JWT secret keys
- Application environment settings

### Optional Environment Variables

- `REQUIRE_QC_FOR_BATCH_TYPES`: Comma-separated list of batch type UUIDs that require QC samples. If a batch type is in this list, QC samples must be provided during batch creation.
- `FAIL_QC_BLOCKS_BATCH`: Set to `true` to block batch completion if QC samples fail validation. Default: `false` (warnings only).
- `R_CALCULATOR_URL`: URL for the R calculator microservice. Default: `http://r-calculator:8000`. Override for local R development or alternative endpoints.

## Health Checks

All containers include health checks:
- Database: PostgreSQL readiness check
- Backend: HTTP endpoint health check
- Frontend: HTTP endpoint health check

## Database Migrations

Alembic migrations run automatically when the backend container starts. The startup script (`backend/start.sh`) waits for the database to be ready, then runs all migrations before starting the server.

**Migrations create:**
- All database tables and indexes
- Initial roles (Administrator, Lab Manager, Lab Technician, CRO Partner / Client)
- Initial permissions (~15 core permissions including `batch:read`, `batch:manage`, `config:edit`, `test:configure`, etc.)
- Default admin user (username: `admin`, password: `admin123`)
- Initial lists and list entries for statuses, types, etc. (normalized to lowercase slug format)
- Seed data: BioTech/Pharma assays (Cell Viability, Dose-Response Screening, Target Binding, Kinase Selectivity Panel, ADME Profiling), analytes (IC50, Emax, Kd, Ki, clearance, permeability, solubility), and assay panels (e.g., 'ADME Panel' battery)

**Manual migration (if needed):**
```bash
docker exec lims-backend python run_migrations.py
```

## Navigation

NimbleLIMS uses a unified sidebar navigation system that provides consistent access to all features:

- **Unified Sidebar**: Persistent left sidebar (240px expanded, 56px collapsed) on all authenticated routes
- **MainNav**: Admin section and sub-links are defined in `frontend/src/components/MainNav.tsx`; the Sidebar uses these for the Admin accordion (Field Management / Lists focus; legacy Name Templates and Custom Attributes links removed).
- **React Router**: All routes are declared in `frontend/src/App.tsx`; admin routes are protected with `hasPermission('config:edit')` (or role-specific permissions)—unauthorized users are redirected to `/dashboard`
- **Collapsible**: Desktop sidebar can be collapsed to icon-only mode with tooltips on hover
- **Permission-Based**: Menu items dynamically shown/hidden based on user roles and permissions
- **Accordion Sections**: Collapsible sections for Sample Management (Receive, Asked-for, Samples, Tests, Containers, Batches, Results), **Experiments** (All Experiments, Experiment Templates — both use `experiment:manage`), Lab Management (Projects, Clients, Client Projects, Analyses, Analytes), and Admin submenu items
- **Responsive**: Permanent drawer on desktop, temporary drawer on mobile
- **State Persistence**: Sidebar collapsed state saved to localStorage
- **Top AppBar**: Dynamic page titles, sidebar toggle, back button for nested routes (e.g. experiment detail → list, admin analysis analytes → analyses), user info, and logout

See [manuals/HOWTO.md](manuals/HOWTO.md) for the lab path. [manuals/navigation.md](manuals/navigation.md) has the full sidebar map (Experiments accordion, templates route, permission gating).

## Documentation

**Published how-tos** are git-tracked under [`manuals/`](manuals/) — start with [HOWTO.md](manuals/HOWTO.md). Review stamps live under [`.docs/review/`](.docs/review/). **Start here:** [`.docs/README.md`](.docs/README.md).

Umbrella PRD, long-form design, ideas, SOP packs, and user stories are git-tracked under [`.docs/internal/`](.docs/internal/). Operator handbooks are git-tracked under [`manuals/`](manuals/). `.docs/manuals/` stays gitignored (vendor PDFs / legacy local manuals).

| Folder | Contents |
|--------|----------|
| [`manuals/`](manuals/) | Git-tracked operator how-tos (`HOWTO.md` plus receive, asked-for, navigation, API, processes, …) |
| [`.docs/internal/`](.docs/internal/) | Git-tracked working PRDs, specs, design, ideas, user stories, SOP packs |
| [`requirements/`](.docs/review/requirements/) | Cycle feature requirements |
| [`checklist/`](.docs/review/checklist/) | Implementation checklists |
| [`open-questions/`](.docs/review/open-questions/) | Cycle/feature gates (block a packet until Decided; not Leadership stamps) |
| [`decision-logs/`](.docs/decision-logs/) | Leadership stamps (FW/WO, reorg, framework) |
| [`development-process/`](.docs/review/development-process/) | Feature development process |
| [`tech-sketch/`](.docs/review/tech-sketch/) | Tech sketches (post-requirements) |
| [`schema-changes/`](.docs/review/schema-changes/) | Per-cycle DB deltas |
| [`lab-ops-review/`](.docs/review/lab-ops-review/), [`ceo-review/`](.docs/review/ceo-review/), [`ui-review/`](.docs/review/ui-review/), [`architecture-review/`](.docs/review/architecture-review/), [`security-review/`](.docs/review/security-review/), [`qa-review/`](.docs/review/qa-review/) | Formal reviews |

UAT scripts: `UAT_Scripts/` — receive `uat-atomic-receive.md`; P1 asked-for `uat-post-receive-work-spine.md` (**P1 Pass** on `c649245`, merged PR 81). Live product SHA **`1572071`**. Signed AC-P2-9..11 history `9342439`. Deiter clicked `0077` at product `4671ba8` / assignment commit `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Leadership Confirmed that click; C1/C2 are **not** unsigned. Docs Confirm `84d2810` is not the click SHA. Live AC-P2-C2 **unsigned** until Tobias. Freeze skip and **OQ-WO-6 stay OPEN**. Overall P2 **unsigned / not Pass**. Hold product merge.

## Support

See [manuals/HOWTO.md](manuals/HOWTO.md), [`.docs/README.md`](.docs/README.md), and [`.docs/review/README.md`](.docs/review/README.md). Operator handbooks: [`manuals/`](manuals/).

---

## Summary — Experiment Management & Navigation Documentation

**Chunk 1 — Experiments core:** CRUD, sidebar Experiments accordion, sample↔experiment linking, lineage, My Experiments filter, workflow actions. **Chunk 2 — Experiment Templates UI:** `ExperimentTemplatesManagement` at `/experiments/templates`, entries authoring (Tables & forms), SOP + instrument CSV upload with Claude extraction (`/v1/sop-parse`), apply job. Templates navigation and route use **`experiment:manage`** (same as All Experiments).

**Key files (frontend):** `frontend/src/pages/ExperimentTemplatesManagement.tsx`, `frontend/src/pages/ExperimentsManagement.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/App.tsx`, `frontend/src/layouts/MainLayout.tsx`, `frontend/src/services/apiService.ts`.

**Key files (backend):** `backend/app/routers/experiments.py`, `backend/app/routers/sop_parse.py`, `backend/app/services/sop_parse_service.py`, `backend/app/services/experiment_service.py`, flexible experiment models/migrations.

**Documentation:** [manuals/HOWTO.md](manuals/HOWTO.md), `.docs/review/checklist/experiment-checklist.md`, [processes.md](manuals/processes.md), [experiments.md](manuals/experiments.md), [lims-runs.md](manuals/lims-runs.md), [navigation.md](manuals/navigation.md), [api-endpoints.md](manuals/api-endpoints.md), [`.docs/internal/design/experiment-planning.md`](.docs/internal/design/experiment-planning.md), `UAT_Scripts/uat-experiment-templates.md`.

**Optional env:** `ANTHROPIC_API_KEY` on the backend for SOP extraction (see `backend/app/core/config.py`).