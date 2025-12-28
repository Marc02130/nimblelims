# LIMS Backend

FastAPI backend for the Laboratory Information Management System (LIMS) MVP.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

Copyright (c) 2025 Marc Breneiser

## Features

### Core Functionality
- **Sample Management**: CRUD operations for samples with status tracking
- **Test Management**: Assign and track tests with status workflows
- **Results Entry**: Batch-based results entry with validation
- **Batch Management**: Create and manage batches with container tracking
- **Container Management**: Container types (admin-managed) and dynamic instance creation
- **Lists Management**: Configurable lists and entries (admin-editable, full CRUD)
- **Analyses Management**: CRUD operations for analyses (admin-only)
- **Analytes Management**: CRUD operations for analytes (admin-only)
- **Analysis-Analyte Configuration**: Configure validation rules for analytes in analyses (admin-only)
- **Test Batteries Management**: Group analyses into reusable batteries with sequence and optional flags (admin-only)
- **Users Management**: CRUD operations for users (admin-only)
- **Roles & Permissions Management**: CRUD operations for roles and permission assignments (admin-only)
- **Authentication**: JWT-based authentication with RBAC
- **Authorization**: Role-based access control with granular permissions

### API Endpoints

#### Authentication
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user information

#### Samples
- `GET /samples` - List samples with filtering
- `POST /samples` - Create new sample
- `POST /samples/accession` - Accession sample with test assignment (supports client projects, test batteries)
- `POST /samples/bulk-accession` - Bulk accession multiple samples (US-24)
- `GET /samples/{id}` - Get sample details
- `PATCH /samples/{id}` - Update sample
- `PATCH /samples/{id}/status` - Update sample status

#### Tests
- `GET /tests` - List tests
- `POST /tests` - Create test assignment
- `PATCH /tests/{id}` - Update test
- `PATCH /tests/{id}/status` - Update test status

#### Results
- `GET /results` - List results
- `POST /results` - Enter single result
- `POST /results/batch` - Enter batch results (US-28: Batch Results Entry with QC validation)
- `POST /results/validate` - Validate result before entry
- `PATCH /results/{id}` - Update result

#### Batches
- `GET /batches` - List batches
- `POST /batches` - Create batch (supports cross-project batching US-26, QC at creation US-27)
- `POST /batches/validate-compatibility` - Validate container compatibility for cross-project batching
- `GET /batches/{id}` - Get batch details
- `POST /batches/{id}/containers` - Add container to batch

#### Containers
- `GET /containers` - List containers
- `POST /containers` - Create container instance
- `GET /containers/{id}` - Get container with contents
- `GET /containers/types` - Get container types (public)
- `POST /containers/types` - Create container type (admin)
- `PATCH /containers/types/{id}` - Update container type (admin)
- `POST /containers/{id}/contents` - Add sample to container

#### Lists
- `GET /lists` - Get all lists with entries
- `GET /lists/{list_name}/entries` - Get entries for a list
- `POST /lists` - Create list (admin, requires config:edit)
- `PATCH /lists/{id}` - Update list (admin)
- `DELETE /lists/{id}` - Delete list (admin)
- `POST /lists/{list_name}/entries` - Add entry to list (admin)
- `PATCH /lists/{list_name}/entries/{entry_id}` - Update entry (admin)
- `DELETE /lists/{list_name}/entries/{entry_id}` - Delete entry (admin)

#### Analyses
- `GET /analyses` - List all active analyses
- `POST /analyses` - Create analysis (admin, requires config:edit or test:configure)
- `PATCH /analyses/{id}` - Update analysis (admin)
- `DELETE /analyses/{id}` - Delete analysis (admin)
- `GET /analyses/{id}/analytes` - Get analytes for analysis
- `PUT /analyses/{id}/analytes` - Update analyte assignment (admin)
- `GET /analyses/{id}/analyte-rules` - Get validation rules for analytes
- `POST /analyses/{id}/analyte-rules` - Create analyte rule (admin)
- `PATCH /analyses/{id}/analyte-rules/{analyte_id}` - Update analyte rule (admin)
- `DELETE /analyses/{id}/analyte-rules/{analyte_id}` - Delete analyte rule (admin)

#### Analytes
- `GET /analytes` - List all active analytes
- `POST /analytes` - Create analyte (admin, requires config:edit or test:configure)
- `PATCH /analytes/{id}` - Update analyte (admin)
- `DELETE /analytes/{id}` - Delete analyte (admin)

#### Users
- `GET /users` - List users with filtering (admin, requires user:manage or config:edit)
- `POST /users` - Create user (admin)
- `PATCH /users/{id}` - Update user (admin)
- `DELETE /users/{id}` - Delete user (admin)

#### Roles & Permissions
- `GET /roles` - List all active roles
- `POST /roles` - Create role (admin, requires user:manage or config:edit)
- `PATCH /roles/{id}` - Update role (admin)
- `DELETE /roles/{id}` - Delete role (admin)
- `PUT /roles/{id}/permissions` - Update role permissions (admin)
- `GET /permissions` - List all permissions (admin)

#### Test Batteries
- `GET /test-batteries` - List test batteries with filtering (name, pagination)
- `GET /test-batteries/{id}` - Get battery with analyses
- `POST /test-batteries` - Create battery (admin, requires config:edit or test:configure)
- `PATCH /test-batteries/{id}` - Update battery (admin)
- `DELETE /test-batteries/{id}` - Soft-delete battery (admin, 409 if referenced)
- `GET /test-batteries/{id}/analyses` - List analyses in battery
- `POST /test-batteries/{id}/analyses` - Add analysis to battery (admin)
- `PATCH /test-batteries/{id}/analyses/{analysis_id}` - Update sequence/optional (admin)
- `DELETE /test-batteries/{id}/analyses/{analysis_id}` - Remove analysis from battery (admin)

#### Test Batteries
- `GET /test-batteries` - List test batteries with filtering
- `GET /test-batteries/{id}` - Get battery with analyses
- `POST /test-batteries` - Create battery (admin, requires config:edit or test:configure)
- `PATCH /test-batteries/{id}` - Update battery (admin)
- `DELETE /test-batteries/{id}` - Soft-delete battery (admin, 409 if referenced)
- `GET /test-batteries/{id}/analyses` - List analyses in battery
- `POST /test-batteries/{id}/analyses` - Add analysis to battery (admin)
- `PATCH /test-batteries/{id}/analyses/{analysis_id}` - Update sequence/optional (admin)
- `DELETE /test-batteries/{id}/analyses/{analysis_id}` - Remove analysis from battery (admin)

#### Client Projects
- `GET /client-projects` - List client projects
- `POST /client-projects` - Create client project (requires project:manage)
- `GET /client-projects/{id}` - Get client project details
- `PATCH /client-projects/{id}` - Update client project
- `DELETE /client-projects/{id}` - Soft-delete client project

#### Other
- `GET /units` - List units
- `GET /projects` - List accessible projects

## Technical Implementation

### Architecture
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database interactions
- **PostgreSQL** - Database with Row-Level Security (RLS)
- **Alembic** - Database migrations
- **Pydantic** - Data validation and serialization
- **PyJWT** - JWT token handling
- **Passlib** - Password hashing (bcrypt)

### Database
- PostgreSQL 15+ with UUID primary keys
- Normalized schema with foreign key relationships
- Row-Level Security (RLS) for data isolation
- Audit trails on all tables
- Soft deletion via `active` flag

### Security
- JWT token-based authentication
- Role-Based Access Control (RBAC)
- ~15 granular permissions
- Password hashing with bcrypt
- Row-Level Security policies
- Project-based data isolation

### API Design
- RESTful API design
- JSON request/response format
- Standard HTTP status codes
- Comprehensive error handling
- OpenAPI/Swagger documentation at `/docs`

## Development

### Prerequisites
- Python 3.10+
- PostgreSQL 15+
- pip

### Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your database credentials and JWT secret
   ```

4. **Run migrations**
   ```bash
   python run_migrations.py
   ```

5. **Start development server**
   ```bash
   python run_server.py
   # Or use uvicorn directly:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Environment Variables

Required environment variables (see `env.example`):
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret key for JWT token signing
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time

Optional environment variables:
- `REQUIRE_QC_FOR_BATCH_TYPES` - Comma-separated list of batch type UUIDs that require QC samples
- `FAIL_QC_BLOCKS_BATCH` - Set to `true` to block batch completion on QC failures (default: `false`)

### Database Migrations

Migrations are managed with Alembic:

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

Migrations are automatically run on container startup via `start.sh`.

### Testing

Run tests with pytest:

```bash
pytest
pytest tests/test_samples.py  # Run specific test file
pytest -v  # Verbose output
pytest --cov=app  # With coverage
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database connection and session management
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   ├── security.py      # JWT and password hashing
│   │   ├── rbac.py          # Role-based access control
│   │   └── conversions.py  # Unit conversion utilities
│   ├── routers/             # API route handlers
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── samples.py      # Sample management
│   │   ├── tests.py        # Test management
│   │   ├── results.py      # Results entry
│   │   ├── batches.py      # Batch management
│   │   ├── containers.py   # Container management
│   │   ├── lists.py         # Lists management
│   │   └── ...
│   └── schemas/             # Pydantic request/response schemas
├── models/                  # SQLAlchemy database models
├── db/
│   └── migrations/          # Alembic migration files
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── start.sh                # Startup script (runs migrations)
└── run_migrations.py      # Migration runner
```

## Permissions

The system uses granular permissions (17 total):

- `user:manage` - Manage users
- `role:manage` - Manage roles
- `config:edit` - Edit system configuration (lists, container types)
- `project:manage` - Manage projects
- `sample:create` - Create samples
- `sample:read` - Read samples
- `sample:update` - Update samples
- `sample:delete` - Delete samples
- `test:assign` - Assign tests
- `test:update` - Update tests
- `result:enter` - Enter results
- `result:review` - Review results
- `batch:manage` - Manage batches
- `batch:read` - Read batches
- `batch:update` - Update batches
- `batch:delete` - Delete batches
- `sample:delete` - Delete samples

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Error Handling

The API uses standard HTTP status codes:
- `200 OK` - Successful request
- `201 Created` - Resource created
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses follow this format:
```json
{
  "detail": "Error message description"
}
```

## Code Quality

- **PEP8** compliance
- **Type hints** for function parameters and returns
- **Docstrings** for all functions and classes
- **Unit tests** for critical functionality
- **Integration tests** for API endpoints

## Deployment

The backend is containerized using Docker. See the main [README.md](../README.md) for Docker setup instructions.

The `start.sh` script:
1. Waits for database to be ready
2. Runs all Alembic migrations
3. Starts the FastAPI server with uvicorn

## Related Documentation

- [API Endpoints Reference](../.docs/api_endpoints.md)
- [Authentication Implementation](../.docs/backend-auth.md)
- [Technical Specifications](../.docs/lims_mvp_tech.md)
- [Accessioning Workflow](../.docs/accessioning_workflow.md)
- [Container Management](../.docs/containers.md)
- [Lists System](../.docs/lists.md)

