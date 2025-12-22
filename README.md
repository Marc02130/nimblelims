# NimbleLIMS - Laboratory Information Management System

A modern, API-first Laboratory Information Management System built with FastAPI, React, and PostgreSQL.

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
│   │   ├── models/         # SQLAlchemy models
│   │   └── core/           # Core utilities (config, security)
│   ├── db/                 # Database migrations
│   │   └── migrations/     # Alembic migration files
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile          # Backend container config
│   ├── start.sh            # Startup script (runs migrations)
│   ├── run_migrations.py   # Migration runner
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
│   ├── lims_mvp_prd.md     # Product requirements
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

- **Sample Tracking**: Accessioning, status management, container hierarchy
- **Test Ordering**: Assign analyses to samples with status tracking
- **Results Entry**: Batch-based results entry with validation
- **Batch Management**: Create and manage batches with container tracking
- **Container Management**: Pre-setup container types, dynamic instance creation during workflows
- **Admin Configuration**: Manage container types and lists via admin interface
- **Security**: JWT authentication with Role-Based Access Control (RBAC)
- **Data Isolation**: Client-specific data access controls
- **Configurable Lists**: Dynamic lists for statuses, types, matrices, etc. (editable by admins)
- **Units Management**: Unit conversions with multipliers

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
- Initial permissions (~15 core permissions including `batch:read`, `batch:manage`, etc.)
- Default admin user (username: `admin`, password: `admin123`)
- Initial lists and list entries for statuses, types, etc. (normalized to lowercase slug format)

**Manual migration (if needed):**
```bash
docker exec lims-backend python run_migrations.py
```

## Documentation

Comprehensive documentation is available in the `.docs/` directory:

- **Product Requirements**: `.docs/lims_mvp_prd.md` - Product requirements document
- **Technical Specifications**: `.docs/lims_mvp_tech.md` - Technical architecture and implementation details
- **User Stories**: `.docs/lims_mvp_user.md` - User stories and acceptance criteria
- **Workflow Documentation**:
  - `.docs/accessioning_workflow.md` - Sample accessioning process and workflow
  - `.docs/containers.md` - Container management, usage, and workflows
  - `.docs/lists.md` - Configurable lists system and administration
- **Setup Guides**:
  - `.docs/lims_mvp_dev_setup.md` - Development environment setup
  - `.docs/admin_setup.md` - Admin user configuration
- **API Reference**: `.docs/api_endpoints.md` - Complete API endpoints documentation

## Support

Refer to the technical documentation in `.docs/` for detailed implementation specifications.