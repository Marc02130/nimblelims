# NimbleLIMS - Laboratory Information Management System

A modern, API-first Laboratory Information Management System (LIMS) built with FastAPI, React, and PostgreSQL. NimbleLIMS provides a unified sidebar navigation system for consistent access to all features across the application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Marc Breneiser

## Architecture

This project uses a three-container Docker setup:

- **Database (PostgreSQL 15+)**: Data persistence with Row-Level Security
- **Backend (FastAPI + Python 3.10+)**: RESTful API with JWT authentication and RBAC
- **Frontend (React 18+)**: Modern web interface with TypeScript

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
   - Database: localhost:5432

4. **Login with admin credentials**
   - Username: `admin`
   - Password: `admin123`
   - **⚠️ IMPORTANT**: Change the default password immediately after first login!
   - See [.docs/admin_setup.md](.docs/admin_setup.md) for detailed security instructions

5. **Run migrations (if needed)**
   ```bash
   docker exec lims-backend python run_migrations.py
   ```
   This ensures all migrations are applied, including the latest `batch:read` permission.

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
├── .docs/                  # Documentation
│   ├── admin_setup.md      # Admin user setup guide
│   ├── api_endpoints.md    # Complete API endpoints reference
│   ├── backend-auth.md     # Authentication implementation
│   ├── debug_404_errors.md # Troubleshooting guide for API errors
│   ├── debug_manifest.md  # Manifest debugging guide
│   ├── inspect_containers.md # Container inspection utilities
│   ├── lims_mvp_prd.md     # Product requirements document
│   ├── lims_mvp_tech.md    # Technical specifications
│   ├── lims_mvp_user.md    # User stories
│   ├── lims_mvp_dev_setup.md # Development environment setup
│   ├── accessioning_workflow.md # Sample accessioning process
│   ├── containers.md       # Container management and usage
│   └── lists.md            # Configurable lists system
├── docker-compose.yml      # Multi-container orchestration
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Features (MVP Scope)

### Core Workflows
- **Sample Tracking**: Accessioning (single and bulk), status management, container hierarchy
- **Test Ordering**: Assign individual analyses or test batteries to samples with status tracking
- **Results Entry**: Batch-based results entry with validation and QC checks
- **Batch Management**: Create and manage batches with cross-project support and automatic QC generation
- **Sample Prioritization** (US-11): Sort samples by expiration and due date priority during batch creation
- **Aliquots/Derivatives**: Create child samples with inheritance
- **Bulk Accessioning** (US-24): Accession multiple samples with common fields and unique per-sample data
- **Cross-Project Batching** (US-26): Batch samples from multiple projects with compatibility validation
- **QC at Batch Creation** (US-27): Automatically generate QC samples when creating batches
- **Batch Results Entry** (US-28): Enter results for multiple tests/samples in a batch atomically

### Container System
- **Container Types**: Pre-setup by administrators (CRUD via admin interface)
- **Container Instances**: Created dynamically during workflows (accessioning, aliquoting)
- **Hierarchical Support**: Parent-child relationships (plates → wells, racks → tubes)
- **Pooled Samples**: Multiple samples per container with concentration/amount tracking
- **Units Integration**: Concentration and amount with unit conversions

### Configuration Management
- **Lists Management**: Full CRUD for lists and list entries via admin interface - create new lists, add/edit/delete entries for statuses, types, matrices, QC types, etc. Empty lists display expand arrows to add entries.
- **Container Types**: Admin-managed container type definitions (CRUD operations)
- **Analyses Management**: Create and manage analyses with methods, turnaround times, costs, and custom attributes. Features expandable grid rows to view and manage linked analytes directly from the main list (CRUD). Available in both Admin section and Lab Mgmt accordion.
- **Analytes Management**: Create and manage analytes with CAS numbers, default units, data types, and custom attributes (CRUD). Available in both Admin section and Lab Mgmt accordion.
- **Analysis-Analyte Linking**: Link/unlink analytes to analyses via expandable detail panels with inline autocomplete search
- **Analysis-Analyte Configuration**: Configure validation rules (data types, ranges, significant figures, required flags)
- **Test Batteries Management**: Group multiple analyses into reusable test batteries with sequence ordering and optional flags (CRUD)
- **Custom Fields Management**: Define custom attributes for samples, tests, results, projects, client_projects, and batches without schema changes (CRUD)
- **Client Projects Management**: Group multiple LIMS projects under client projects for holistic tracking (CRUD)
- **Users Management**: Create and manage users with role assignments (CRUD)
- **Roles & Permissions**: Manage roles and assign permissions (CRUD)
- **Units Management**: Unit definitions with multipliers for conversions

### Security & Access
- **Authentication**: JWT token-based authentication
- **Authorization**: Role-Based Access Control (RBAC) with 17 granular permissions
- **Data Isolation**: Client-specific data access controls via project_users junction table
- **Row-Level Security**: PostgreSQL RLS policies for data protection at the database level
- **Samples Access Control**: The `GET /samples` endpoint relies entirely on RLS for access control - no Python-level filtering is applied. Lab Technicians and Lab Managers see samples from projects they have access to via the `project_users` table. Client users see samples from their client's projects. Administrators see all samples.

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

## Health Checks

All containers include health checks:
- Database: PostgreSQL readiness check
- Backend: HTTP endpoint health check
- Frontend: HTTP endpoint health check

## Database Migrations

Alembic migrations run automatically when the backend container starts. The startup script (`backend/start.sh`) waits for the database to be ready, then runs all migrations before starting the server.

**Migrations create:**
- All database tables and indexes
- Initial roles (Administrator, Lab Manager, Lab Technician, Client)
- Initial permissions (~15 core permissions including `batch:read`, `batch:manage`, `config:edit`, `test:configure`, etc.)
- Default admin user (username: `admin`, password: `admin123`)
- Initial lists and list entries for statuses, types, etc. (normalized to lowercase slug format)
- Seed data: analyses, analytes, and test batteries (e.g., 'EPA 8080 Full' battery)

**Manual migration (if needed):**
```bash
docker exec lims-backend python run_migrations.py
```

## Navigation

NimbleLIMS uses a unified sidebar navigation system that provides consistent access to all features:

- **Unified Sidebar**: Persistent left sidebar (240px expanded, 56px collapsed) on all authenticated routes
- **MainNav**: Admin section and sub-links are defined in `frontend/src/components/MainNav.tsx`; the Sidebar uses these for the Admin accordion (including **Name Templates** `/admin/name-templates`, **Custom Attributes** `/admin/custom-attributes`, **Lists** `/admin/lists`)
- **React Router**: All routes are declared in `frontend/src/App.tsx`; admin routes are protected with `hasPermission('config:edit')` (or role-specific permissions)—unauthorized users are redirected to `/dashboard`
- **Collapsible**: Desktop sidebar can be collapsed to icon-only mode with tooltips on hover
- **Permission-Based**: Menu items dynamically shown/hidden based on user roles and permissions
- **Accordion Sections**: Collapsible sections for Sample Management (Accessioning, Samples, Tests, Containers, Batches, Results), Lab Management (Projects, Clients, Client Projects, Analyses, Analytes), and Admin submenu items
- **Responsive**: Permanent drawer on desktop, temporary drawer on mobile
- **State Persistence**: Sidebar collapsed state saved to localStorage
- **Top AppBar**: Dynamic page titles, sidebar toggle, back button for nested routes, user info, and logout

See [`.docs/navigation.md`](.docs/navigation.md) for complete navigation documentation.

## Documentation

Comprehensive documentation is available in the `.docs/` directory:

- **Navigation**: `.docs/navigation.md` - Complete site navigation documentation
- **Product Requirements**: `.docs/nimblelims_prd.md` - Product requirements document
- **Technical Specifications**: `.docs/nimblelims_tech.md` - Technical architecture and implementation details
- **User Stories**: `.docs/nimblelims_user.md` - User stories and acceptance criteria
- **Workflow Documentation**:
  - `.docs/accessioning_workflow.md` - Sample accessioning process and workflow (includes test battery assignment)
  - `.docs/batches.md` - Batch management, QC generation, and sample prioritization
  - `.docs/containers.md` - Container management, usage, and workflows
  - `.docs/lists.md` - Configurable lists system and administration
  - `.docs/technical-accessioning-to-reporting.md` - Technical implementation details for accessioning through reporting
  - `.docs/ui-accessioning-to-reporting.md` - UI components and interactions for accessioning through reporting
  - `.docs/workflow-accessioning-to-reporting.md` - Complete workflow from accessioning through reporting
- **Setup Guides**:
  - `.docs/nimblelims_dev_setup.md` - Development environment setup
  - `.docs/admin_setup.md` - Admin user configuration
- **API Reference**: `.docs/api_endpoints.md` - Complete API endpoints documentation
- **IDs and Configuration**: `.docs/ids-and-configuration.md` - How sample/project IDs and names work, where configuration is stored (name_templates, custom_attributes_config), and flow from configuration through use

## Support

Refer to the technical documentation in `.docs/` for detailed implementation specifications.