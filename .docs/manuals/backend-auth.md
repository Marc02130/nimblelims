# NimbleLIMS Authentication Implementation

## Overview

This implementation provides a complete authentication system for the NimbleLIMS based on the technical document and user stories. It includes JWT-based authentication, role-based access control (RBAC), and comprehensive security features.

## Features Implemented

### 1. FastAPI Application Structure
- **Main App**: `app/main.py` - FastAPI application with CORS middleware
- **Database**: `app/database.py` - SQLAlchemy configuration and session management
- **Routers**: `app/routers/auth.py` - Authentication endpoints

### 2. Authentication Endpoints
- **POST /auth/login**: User authentication with username/password (returns `must_change_password`)
- **POST /auth/change-password**: Change password; clears `must_change_password` (Q7)
- **GET /auth/me**: Current user (includes `must_change_password`)
- **POST /auth/verify-email**: Email verification (stub implementation)

### 3. Security Features
- **Password Hashing**: bcrypt (legacy unsalted SHA256 verified once, then upgraded on login)
- **Must change password**: `users.must_change_password` — while true, only change-password / me / logout; other routes **403** `password_change_required`
- **Complexity**: min 12 chars; upper, lower, digit, symbol; ≠ username; ≠ current password
- **JWT Tokens**: PyJWT; claim `pwd_change` when change required. `SECRET_KEY` (alias `JWT_SECRET_KEY`); refuse defaults unless `ALLOW_INSECURE_DEFAULTS` in development/test
- **RBAC**: 17 core permissions for granular access control (with additional permissions added in migrations)
- **Token Validation**: Secure token verification with expiration
- **Bootstrap**: `BOOTSTRAP_ADMIN_PASSWORD` for production admin create; `ALLOW_DEV_SEED_USERS` for local/demo temporary seeds
- **DB roles (P0d)**: runtime `DATABASE_URL` → **`lims_app`** (non-superuser); migrations/ensure → **`MIGRATE_DATABASE_URL`** (owner `lims_user`). `start.sh` runs Alembic then `ensure_lims_app_role.py` (create-once password from `LIMS_APP_PASSWORD`; grants idempotent; rotate only with `ENSURE_LIMS_APP_PASSWORD_ROTATE=true`). RLS GUCs: `app.current_user_id` / `app.client_id` via `set_config(..., true)`

### 4. Core Permissions (17 total)
```
sample:create, sample:read, sample:update
test:assign, test:update
result:enter, result:review, result:update, result:delete
batch:manage, batch:read, batch:update, batch:delete
project:manage
user:manage, role:manage, config:edit
```

**Note**: The code references `test:configure` permission in several places (analyses, analytes, test batteries endpoints), but this permission is not currently created in the database. These endpoints use `require_any_permission(["config:edit", "test:configure"])`, which effectively requires `config:edit` since `test:configure` doesn't exist. Consider adding `test:configure` as a separate permission in a future migration if you want to distinguish test configuration from general configuration editing.

### 5. Database Models
- **User**: Authentication and user information
- **Role**: User roles with permissions
- **Permission**: Granular permissions
- **RolePermission**: Many-to-many relationship

### 6. Pydantic Schemas
- **LoginRequest/Response**: Login endpoint schemas
- **VerifyEmailRequest/Response**: Email verification schemas
- **TokenData**: JWT token payload structure

## Installation and Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` file with:
```
DATABASE_URL=postgresql://lims_user:lims_password@localhost:5432/lims_db
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Database Setup

**Automatic (Recommended):**
When using Docker Compose, migrations run automatically on backend startup via `backend/start.sh`. The script:
1. Waits for the database to be ready
2. Runs `python run_migrations.py` to execute all Alembic migrations
3. Starts the FastAPI server

**Manual (Development):**
```bash
# Run migrations manually
python run_migrations.py
```

**Note:** `Base.metadata.create_all()` is NOT used in production. All schema changes must go through Alembic migrations.

### 4. Run the Server
```bash
python run_server.py
```

## API Usage

### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpassword"}'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "username": "testuser",
  "email": "test@example.com",
  "role": "lab_technician",
  "permissions": ["sample:create", "sample:read", "result:enter"]
}
```

### Using JWT Token
```bash
curl -X GET "http://localhost:8000/samples" \
  -H "Authorization: Bearer your-jwt-token"
```

## Testing

### Run Tests
```bash
pytest tests/ -v
```

### Test Coverage
- Login success/failure scenarios
- JWT token creation and validation
- Password hashing and verification
- Permission system validation
- Email verification (stub)

## Security Features

### 1. Password Security
- bcrypt hashing with salt
- Secure password verification
- No plain text password storage

### 2. JWT Security
- HS256 algorithm for token signing
- Configurable token expiration
- Secure token validation
- Bearer token authentication

### 3. RBAC Implementation
- Granular permission system
- Role-based access control
- Permission dependency injection
- User context for RLS

### 4. Database Security
- Row Level Security (RLS) support
- User context setting for queries
- Audit trail integration
- Secure session management

## Architecture

```
app/
├── main.py              # FastAPI application
├── database.py          # Database configuration
├── core/
│   ├── config.py        # Application configuration
│   └── security.py      # Security utilities
├── models/
│   └── user.py          # User, Role, Permission models
├── schemas/
│   └── auth.py          # Pydantic schemas
└── routers/
    └── auth.py          # Authentication endpoints
```

## Next Steps

1. ✅ **Database Migration**: Alembic migrations run automatically on startup
2. ✅ **Initial Data**: Default roles, permissions, and admin user created by migrations
3. **User Management**: Implement user creation and management UI
4. ✅ **Frontend Integration**: React frontend connected to auth endpoints
5. **Email Service**: Implement actual email verification
6. **Audit Logging**: Add comprehensive audit trails

## Compliance with Requirements

✅ **US-12**: User Authentication - Username/password + email verification  
✅ **US-13**: Role-Based Access Control - 17 permissions via roles  
✅ **Technical Document 4.1**: JWT authentication with security  
✅ **PEP8 Compliance**: Code follows Python standards  
✅ **Pydantic Schemas**: Request/response validation  
✅ **Comprehensive Testing**: pytest test suite included
