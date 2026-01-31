# UAT Scripts: Security and RBAC

## Overview

This document contains User Acceptance Testing (UAT) scripts for security and Role-Based Access Control (RBAC) in NimbleLIMS. These scripts validate authentication, authorization, and data isolation as defined in:

- **User Stories**: US-12 (User Authentication), US-13 (Role-Based Access Control), US-14 (Project and Client Data Isolation)
- **PRD**: Section 3.1 (Security and Auth)
- **Technical Document**: `technical-accessioning-to-reporting.md` (RLS policies)
- **Schema**: `role_permissions` junction table, `project_users` junction table, RLS policies

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Roles: Administrator, Lab Manager, Lab Technician, Client
  - Permissions: All 13 core permissions (see Reference Documentation for full list)
  - Role-permission mappings via `role_permissions` junction table
  - At least one user per role with appropriate permissions
  - At least one client user with `client_id` set
  - At least two projects (one accessible to client, one not)
  - At least one sample in accessible project
  - At least one sample in inaccessible project
- Test user accounts:
  - Client user with `client_id` set to specific client (not System), only `sample:read` permission
  - Administrator user (for comparison)
  - Lab Technician user (seeded as `lab-tech` with `client_id = System_client_id`, full lab technician permissions)
  - Lab Manager user (seeded as `lab-manager` with `client_id = System_client_id`)

---

## Test Case 1: Login/Logout - JWT Token Authentication

### Test Case ID
TC-AUTH-LOGIN-001

### Description
Verify user authentication with username/password, JWT token generation, token validation, and logout functionality.

### Preconditions

| Item | Value |
|------|-------|
| **User Account Exists** | At least one user account exists in database:<br>- Username: `testuser`<br>- Password: `testpassword`<br>- Active: `true`<br>- Role assigned with permissions |
| **Database Seeded** | Roles and permissions seeded via migrations |
| **No Active Session** | User not currently logged in |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page (e.g., `/login`) | Login form loads with username and password fields |
| 2 | **Enter Credentials** | |
| 2.1 | Enter username: `testuser` | Field accepts input |
| 2.2 | Enter password: `testpassword` | Field accepts input (password masked) |
| 2.3 | Click "Login" button | Form submits, loading spinner shown |
| 3 | Wait for API response | Success response received |
| 4 | **Verify Login Response** | |
| 4.1 | Verify JWT token received | Response contains `access_token` field (JWT string) |
| 4.2 | Verify user information | Response contains:<br>- `user_id`: UUID<br>- `username`: "testuser"<br>- `email`: user's email<br>- `role`: role name (e.g., "Lab Technician")<br>- `permissions`: array of permission strings |
| 4.3 | Verify token stored | Token stored in `localStorage` (key: "token") |
| 4.4 | Verify token added to API requests | Authorization header set: `Bearer {token}` |
| 5 | **Verify Token Validation** | |
| 5.1 | Make authenticated API call: GET `/auth/me` | API call succeeds (HTTP 200) |
| 5.2 | Verify user information returned | Response contains current user details |
| 5.3 | Verify `last_login` updated | User's `last_login` field updated in database |
| 6 | **Test Logout** | |
| 6.1 | Click "Logout" button or navigate to logout | Logout action triggered |
| 6.2 | Verify token removed | Token removed from `localStorage` |
| 6.3 | Verify API token cleared | Authorization header no longer sent |
| 6.4 | Verify redirect to login | User redirected to login page |
| 6.5 | Attempt authenticated API call: GET `/auth/me` | API call fails (HTTP 401 Unauthorized) |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/auth/login` called with:<br>```json
{
  "username": "testuser",
  "password": "testpassword"
}
``` |
| **Backend Processing** | 1. **User Lookup**:<br>   - Query user by username<br>   - Return 401 if user not found<br>2. **Password Verification**:<br>   - Verify password using bcrypt<br>   - Return 401 if password incorrect<br>3. **Active Check**:<br>   - Verify user is active<br>   - Return 401 if user inactive<br>4. **Permission Retrieval**:<br>   - Get user permissions via `role_permissions` junction<br>   - Query: `SELECT p.name FROM permissions p JOIN role_permissions rp ON p.id = rp.permission_id WHERE rp.role_id = {user.role_id}`<br>5. **JWT Token Creation**:<br>   - Create access token with payload:<br>     - `sub`: user.id (UUID as string)<br>     - `username`: user.username<br>     - `role`: user.role.name<br>     - `permissions`: array of permission strings<br>     - `exp`: expiration timestamp<br>   - Sign with SECRET_KEY using HS256 algorithm<br>6. **Update last_login**:<br>   - Set `user.last_login` = current timestamp<br>   - Commit to database<br>7. **Set RLS Context**:<br>   - Call `set_current_user_id(user.id, db)` for RLS |
| **Login Response** | ```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "testuser",
  "email": "test@example.com",
  "role": "Lab Technician",
  "permissions": ["sample:create", "sample:read", "sample:update", "test:assign", "test:update", "result:enter", "batch:manage", "batch:read"]
}
```<br>- HTTP 200 OK |
| **Token Storage** | - Token stored in browser `localStorage` with key "token"<br>- Token added to all subsequent API requests as: `Authorization: Bearer {token}` |
| **Token Validation** | - GET `/auth/me` endpoint validates token:<br>   - Decode JWT token<br>   - Verify signature with SECRET_KEY<br>   - Check expiration<br>   - Return user information if valid<br>   - Return 401 if invalid/expired |
| **Logout** | - Token removed from `localStorage`<br> - API service clears Authorization header<br> - User redirected to login page<br> - Subsequent API calls return 401 |

### Test Steps - Invalid Credentials (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Invalid Username** | |
| 7.1 | Enter username: `nonexistent` | Field accepts input |
| 7.2 | Enter password: `testpassword` | Field accepts input |
| 7.3 | Click "Login" | Form submits |
| 7.4 | Verify error response | HTTP 401 Unauthorized:<br>- Error message: "Incorrect username or password" |
| 8 | **Test Invalid Password** | |
| 8.1 | Enter username: `testuser` | Field accepts input |
| 8.2 | Enter password: `wrongpassword` | Field accepts input |
| 8.3 | Click "Login" | Form submits |
| 8.4 | Verify error response | HTTP 401 Unauthorized:<br>- Error message: "Incorrect username or password" |
| 9 | **Test Inactive User** | |
| 9.1 | Set user active = false in database | User deactivated |
| 9.2 | Attempt login with valid credentials | Form submits |
| 9.3 | Verify error response | HTTP 401 Unauthorized:<br>- Error message: "User account is inactive" |

### Expected Results - Invalid Credentials

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 401 Unauthorized<br>- Error message: "Incorrect username or password" or "User account is inactive"<br>- Header: `WWW-Authenticate: Bearer`<br>- No token returned |
| **UI Feedback** | - Error message displayed on login form<br>- User remains on login page<br>- No token stored |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Login succeeds with valid credentials | ✓ | ✗ |
| JWT token received in response | ✓ | ✗ |
| Token contains user_id, username, role, permissions | ✓ | ✗ |
| Token stored in localStorage | ✓ | ✗ |
| Token added to API requests | ✓ | ✗ |
| GET /auth/me succeeds with valid token | ✓ | ✗ |
| last_login updated in database | ✓ | ✗ |
| Logout removes token | ✓ | ✗ |
| Invalid credentials return 401 | ✓ | ✗ |
| Inactive user cannot login | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Permission Denial - RBAC Enforcement

### Test Case ID
TC-RBAC-PERMISSION-002

### Description
Verify that users without required permissions are denied access to protected endpoints, with appropriate 403 Forbidden responses.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **User Permissions** | Lab Technician has: `sample:create`, `sample:read`, `sample:update`, `test:assign`, `test:update`, `result:enter`, `batch:manage`, `batch:read`<br>Lab Technician does NOT have: `config:edit`, `result:review`, `user:manage`, `role:manage`, `project:manage` |
| **Role-Permission Mapping** | `role_permissions` junction table configured correctly per migration 0004 |
| **User Logged In** | User successfully authenticated with valid JWT token |
| **List Exists** | At least one list exists for configuration edit test |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician (`lab-tech` user) | User authenticated, token received with Lab Technician permissions |
| 2 | **Verify Route Protection (UI Redirect)** | |
| 2.1 | Navigate directly to `/admin/lists` via URL bar | User is redirected to `/dashboard` (route requires `config:edit`) |
| 2.1a | Navigate directly to `/admin/name-templates` via URL bar (no `config:edit`) | User is redirected to `/dashboard` |
| 2.1b | Navigate directly to `/admin/custom-attributes` via URL bar (no `config:edit`) | User is redirected to `/dashboard` |
| 2.1c | Call POST `/admin/sequences/sample/start` with body `{"start_value": 1}` without admin token | HTTP 401 or 403 (sequence start requires `config:edit`) |
| 2.2 | Navigate directly to `/admin` via URL bar | User is redirected to `/dashboard` |
| 2.3 | Verify sidebar does not show Admin section | Admin accordion not visible (no `config:edit` permission) |
| 3 | **Test Allowed Action (Sample Creation)** | |
| 3.1 | Navigate to accessioning page (`/accessioning`) | Page loads (user has `sample:create` permission) |
| 3.2 | Fill in sample creation form with valid data | Form accepts input |
| 3.3 | Submit the form | Action succeeds (HTTP 201 Created) |
| 3.4 | Verify sample created | Sample appears in samples list |
| 4 | **Test API Permission Denial (Browser DevTools)** | |
| 4.1 | Open browser DevTools (F12) → Network tab | DevTools opens |
| 4.2 | Copy the Authorization header from any successful request | Bearer token obtained |
| 4.3 | Open DevTools Console and run:<br>`fetch('/api/lists', {method: 'POST', headers: {'Authorization': 'Bearer YOUR_TOKEN', 'Content-Type': 'application/json'}, body: JSON.stringify({name: 'test_denied', description: 'test'})}).then(r => console.log(r.status))` | API call made |
| 4.4 | Verify response status | HTTP 403 Forbidden returned |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Route Protection** | - Frontend routes check `hasPermission('config:edit')` before rendering admin pages<br>- Users without permission are automatically redirected to `/dashboard`<br>- No error message shown (seamless redirect) |
| **Sidebar Visibility** | - Admin section hidden from users without `config:edit` permission<br>- Lab Technician sees: Dashboard, Accessioning, Samples, Tests, Containers, Batches, Results, Help |
| **Allowed Action** | - User can access `/accessioning` (requires `sample:create`)<br>- Sample creation succeeds (HTTP 201)<br>- Sample appears in samples list |
| **API Permission Denial** | - Direct API call to POST `/lists` returns HTTP 403<br>- Response body: `{"detail": "Permission 'config:edit' required"}`<br>- Backend correctly blocks unauthorized actions even if UI is bypassed |
| **Backend Processing** | 1. **Token Validation**: JWT verified and decoded<br>2. **Permission Check**: `require_permission("config:edit")` queries user's role permissions<br>3. **Denial**: Permission not found → HTTPException 403 raised |

### Test Steps - Administrator Access (Positive Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Test Administrator Access** | |
| 6.1 | Log in as Administrator | User authenticated |
| 6.2 | Verify Administrator has all permissions | Administrator role has all 13 permissions via `role_permissions` |
| 6.3 | Attempt list creation | Action succeeds (HTTP 201) |
| 6.4 | Verify list created | List record created in database |

### Expected Results - Administrator Access

| Category | Expected Outcome |
|----------|------------------|
| **Administrator Permissions** | - Administrator role has all permissions via `role_permissions` junction<br>- Includes `config:edit` permission |
| **List Creation** | - List creation succeeds<br>- List record created in database |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Lab Technician denied access to config:edit endpoint | ✓ | ✗ |
| HTTP 403 Forbidden returned | ✓ | ✗ |
| Error message is clear and informative | ✓ | ✗ |
| No data created/modified by unauthorized user | ✓ | ✗ |
| Lab Technician can create samples (has sample:create) | ✓ | ✗ |
| Administrator can access all endpoints | ✓ | ✗ |
| Permission check uses role_permissions junction | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Client Isolation - RLS on Projects

### Test Case ID
TC-RLS-CLIENT-ISOLATION-003

### Description
Verify that client users can only access their own projects, samples, and results via Row-Level Security (RLS) policies, with data isolation enforced at the database level.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Client |
| **User client_id** | Client user has `client_id` set (e.g., "Client Alpha" UUID) |
| **User Permissions** | Client user has only `sample:read` permission (per migration 0004) |
| **Projects Exist** | At least two projects exist:<br>- Project Alpha: `client_id` = Client Alpha UUID (accessible)<br>- Project Beta: `client_id` = Client Beta UUID (inaccessible) |
| **Samples Exist** | At least one sample in Project Alpha (accessible)<br>At least one sample in Project Beta (inaccessible) |
| **RLS Enabled** | RLS policies enabled on `samples`, `projects`, `tests`, `results` tables |
| **User Logged In** | Client user successfully authenticated with valid JWT token |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Client user | User authenticated, token received |
| 2 | **Verify Project Access** | |
| 2.1 | Navigate to `/projects` route | Projects list page loads |
| 2.2 | Verify projects displayed | Only Project Alpha visible (client's project)<br>Project Beta NOT visible |
| 2.3 | Click on Project Alpha | Project details view opens |
| 2.4 | Attempt to access Project Beta directly: GET `/projects/{project_beta_uuid}` | API call made |
| 2.5 | Verify access denied | HTTP 403 Forbidden or 404 Not Found (RLS hides record) |
| 3 | **Verify Sample Access** | |
| 3.1 | Navigate to `/samples` route | Samples Management page loads |
| 3.2 | Verify samples displayed | Only samples from Project Alpha visible<br>Samples from Project Beta NOT visible |
| 3.3 | Click on sample from Project Alpha | Sample details view opens |
| 3.4 | Attempt to access sample from Project Beta directly: GET `/samples/{sample_beta_uuid}` | API call made |
| 3.5 | Verify access denied | HTTP 403 Forbidden or 404 Not Found |
| 4 | **Verify RLS Enforcement** | |
| 4.1 | Make API call: GET `/samples` | API call succeeds (HTTP 200) |
| 4.2 | Verify response filtered | Response contains only samples from accessible projects |
| 4.3 | Verify database query | Database query automatically filtered by RLS policy:<br>- `samples_access` policy checks `has_project_access(project_id)`<br>- Policy returns only rows where user has access |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **RLS Policies** | RLS policies enabled on tables:<br>1. **samples_access policy**:<br>   ```sql
   CREATE POLICY samples_access ON samples
   FOR ALL
   USING (
       is_admin() OR has_project_access(project_id)
   );
   ```<br>2. **projects_access policy**:<br>   ```sql
   CREATE POLICY projects_access ON projects
   FOR ALL
   USING (
       is_admin() OR has_project_access(id)
   );
   ```<br>3. **tests_access policy**:<br>   - Checks access via sample's project<br>4. **results_access policy**:<br>   - Checks access via test → sample → project |
| **has_project_access() Function** | Function checks client access with System client support:<br>```sql
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_client_id UUID;
    user_client_id UUID;
    system_client_id UUID;
BEGIN
    -- Admin users can access all projects
    IF is_admin() THEN
        RETURN TRUE;
    END IF;
    
    -- System client ID: '00000000-0000-0000-0000-000000000001'
    system_client_id := '00000000-0000-0000-0000-000000000001'::UUID;
    
    -- Get user's client_id
    SELECT u.client_id INTO user_client_id
    FROM users u
    WHERE u.id = current_user_id();
    
    -- If user is associated with System client, grant full access (lab employees)
    IF user_client_id = system_client_id THEN
        RETURN TRUE;
    END IF;
    
    -- Get the project's client_id
    SELECT p.client_id INTO project_client_id
    FROM projects p
    WHERE p.id = project_uuid;
    
    -- Check if user's client_id matches project's client_id
    IF user_client_id IS NOT NULL AND project_client_id = user_client_id THEN
        RETURN TRUE;
    END IF;
    
    -- Fall back to project_users check (for granular grants)
    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
        AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
``` |
| **Database Queries** | - All queries automatically filtered by RLS:<br>  - `SELECT * FROM samples` → Returns only accessible samples<br>  - `SELECT * FROM projects` → Returns only accessible projects<br>  - `SELECT * FROM tests` → Returns only tests for accessible samples<br>  - `SELECT * FROM results` → Returns only results for accessible tests |
| **API Responses** | - GET `/projects`: Returns only accessible projects<br>- GET `/samples`: Returns only samples from accessible projects<br>- GET `/samples/{id}`: Returns 403 or 404 for inaccessible samples<br>- GET `/tests`: Returns only tests for accessible samples<br>- GET `/results`: Returns only results for accessible tests |
| **UI Display** | - Projects list shows only accessible projects<br>- Samples list shows only accessible samples<br>- Inaccessible data not visible in UI<br>- Direct access attempts show error message |

### Test Steps - Lab Technician Access (Comparison)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5 | **Test Lab Technician Access** | |
| 5.1 | Log in as Lab Technician | User authenticated |
| 5.2 | Verify Lab Technician has project access via `project_users` | Lab Technician has entry in `project_users` junction for Project Alpha |
| 5.3 | Navigate to `/projects` route | Projects list loads |
| 5.4 | Verify projects displayed | Project Alpha visible (via `project_users`)<br>Project Beta NOT visible (no `project_users` entry) |
| 5.5 | Verify RLS enforcement | RLS uses `project_users` check for lab technicians |

### Expected Results - Lab Technician Access

| Category | Expected Outcome |
|----------|------------------|
| **project_users Junction** | - Lab Technician has entry in `project_users` table:<br>  - `project_id` = Project Alpha UUID<br>  - `user_id` = Lab Technician UUID |
| **RLS Access** | - `has_project_access()` function checks `project_users` junction for lab technicians<br>- Lab Technician can access Project Alpha<br>- Lab Technician cannot access Project Beta (no junction entry) |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Client user sees only own projects | ✓ | ✗ |
| Client user sees only own samples | ✓ | ✗ |
| RLS policies enabled on tables | ✓ | ✗ |
| has_project_access() function works correctly | ✓ | ✗ |
| Database queries filtered by RLS | ✓ | ✗ |
| Direct access to inaccessible data returns 403/404 | ✓ | ✗ |
| Lab Technician access via project_users works | ✓ | ✗ |
| Administrator can access all data | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-12 (User Authentication)
- **As any** user
- **I want** to log in with username/password and verify email
- **So that** access is secure
- **Acceptance Criteria**:
  - No default access; admin grants roles/permissions
  - JWT token on login; last_login tracked
  - API: POST `/auth/login`, `/verify-email`

### User Story US-13 (Role-Based Access Control)
- **As an** Administrator
- **I want** to manage roles and granular permissions
- **So that** access is controlled
- **Acceptance Criteria**:
  - 13 permissions seeded via migrations (see Core Permissions below)
  - Roles: Admin (all), Lab Manager (review/manage/create), Lab Technician (create/enter/manage batches), Client (sample:read only)
  - API: CRUD `/roles`, `/permissions` (admin-only)
  - Note: `test:configure` is referenced in code but not yet in database; endpoints use `config:edit` as fallback

### User Story US-14 (Project and Client Data Isolation)
- **As a** Client
- **I want** to view only my projects/samples/results
- **So that** data privacy is maintained
- **Acceptance Criteria**:
  - Project_users junction for access grants
  - Filters: client_id on users; RLS in DB
  - API: All queries scoped by user context

### PRD Section 3.1 (Security and Auth)
- **RBAC**: 17 permissions (e.g., sample:create, result:enter, batch:manage)
- **User auth**: Username/password + email verification
- **Client isolation**: View own projects/samples only; project_users junction for access

### Technical Document (RLS Policies)
- **RLS Enabled Tables**: `samples`, `projects`, `tests`, `results`, `batches`, `client_projects`
- **RLS Functions**:
  - `is_admin()`: Checks if current user is Administrator
  - `has_project_access(project_uuid)`: Checks if user has access to project
    - **System client users** (`client_id = System_client_id`): Always returns TRUE (full access)
    - **Regular client users**: Checks if `user.client_id` matches `project.client_id`
    - **Lab technicians** (with System client): Full access via System client check
    - **Administrators**: Always returns TRUE
    - Falls back to `project_users` junction table for granular grants
- **RLS Policies**:
  - `samples_access`: `is_admin() OR has_project_access(project_id)`
  - `projects_access`: `is_admin() OR has_project_access(id)`
  - `tests_access`: Checks access via sample's project
  - `results_access`: Checks access via test → sample → project
  - `batches_access`: Checks access via batch_containers → containers → contents → samples → projects
  - `containers_access`: Checks access via contents → samples → projects
  - `client_projects_access`: 
    - **Administrators**: All client projects
    - **System client users** (lab employees): All active client projects (for sample creation workflows)
    - **Regular client users**: Client projects matching their `client_id`
- **SQLAlchemy RLS Implementation Note**: 
  - SQLAlchemy's `query.count()` wraps queries in subqueries which can break RLS evaluation
  - For Lab Technician/Manager roles accessing `client_projects`, the implementation uses `func.count()` directly instead of `query.count()` to avoid subquery wrapping
  - This ensures RLS policies are properly evaluated at the database level
- **Client Data Isolation**:
  - **System Client Users** (`client_id = '00000000-0000-0000-0000-000000000001'`): Full access to all data (lab employees)
  - **Regular Client Users**: Only data where `project.client_id = user.client_id`
  - **Administrators**: Full access regardless of client_id
  - **API Layer Validation**: Create/update operations validate `project.client_id` matches `user.client_id` (unless System/Admin)
  - **Frontend**: Conditionally adds `client_id` to query params for non-System clients (though RLS enforces this)
  - **Error Response**: `403 Forbidden` with message "Access denied: insufficient client permissions"
  
- **Samples Endpoint Access Control**:
  - The `GET /samples` endpoint relies entirely on RLS policies for access control
  - No Python-level filtering is applied - RLS automatically filters samples based on `has_project_access(project_id)`
  - **System client users** (lab employees): See all samples (full access)
  - **Client users**: See samples from projects where `project.client_id = user.client_id`
  - **Administrators**: See all samples
  - The session variable `app.current_user_id` is set via `set_current_user_id()` in `get_current_user()` dependency to enable RLS evaluation

### Schema
- **`role_permissions` junction table**:
  - `role_id`: UUID FK to `roles.id` (primary key)
  - `permission_id`: UUID FK to `permissions.id` (primary key)
  - Composite primary key: (role_id, permission_id)
- **`project_users` junction table**:
  - `project_id`: UUID FK to `projects.id` (primary key)
  - `user_id`: UUID FK to `users.id` (primary key)
  - `access_level`: UUID FK to `list_entries.id` (nullable)
  - `granted_at`: DateTime
  - `granted_by`: UUID FK to `users.id` (nullable)
  - Composite primary key: (project_id, user_id)
- **`users` table**:
  - `client_id`: UUID FK to `clients.id` (nullable)
  - `role_id`: UUID FK to `roles.id`
  - `password_hash`: String (bcrypt hashed)
  - `last_login`: DateTime (nullable)
  - `active`: Boolean
- **`roles` table**:
  - `name`: String (unique)
  - `description`: Text (nullable)
- **`permissions` table**:
  - `name`: String (unique)
  - `description`: Text (nullable)

### API Endpoints
- **POST `/auth/login`**: Authenticate user and return JWT token
  - Request: `{username, password}`
  - Response: `{access_token, token_type, user_id, username, email, role, permissions}`
- **GET `/auth/me`**: Get current user information (requires valid token)
- **POST `/samples`**: Create sample (requires `sample:create` permission)
- **GET `/samples`**: List samples (requires `sample:read` permission, filtered by RLS)
- **GET `/projects`**: List projects (requires `project:read` permission, filtered by RLS)

### Core Permissions (13 seeded in migration 0004)
```
user:manage, role:manage, config:edit, project:manage
sample:create, sample:read, sample:update
test:assign, test:update
result:enter, result:review
batch:manage, batch:read
```

### Role-Permission Matrix

| Permission | Administrator | Lab Manager | Lab Technician | Client |
|------------|--------------|-------------|----------------|--------|
| user:manage | ✓ | | | |
| role:manage | ✓ | | | |
| config:edit | ✓ | | | |
| project:manage | ✓ | ✓ | | |
| sample:create | ✓ | ✓ | ✓ | |
| sample:read | ✓ | ✓ | ✓ | ✓ |
| sample:update | ✓ | ✓ | ✓ | |
| test:assign | ✓ | ✓ | ✓ | |
| test:update | ✓ | ✓ | ✓ | |
| result:enter | ✓ | ✓ | ✓ | |
| result:review | ✓ | ✓ | | |
| batch:manage | ✓ | ✓ | ✓ | |
| batch:read | ✓ | ✓ | ✓ | |

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-AUTH-LOGIN-001 | | | | |
| TC-RBAC-PERMISSION-002 | | | | |
| TC-RLS-CLIENT-ISOLATION-003 | | | | |
| TC-RLS-SYSTEM-CLIENT-004 | | | | |
| TC-FRONTEND-CLIENT-ISOLATION-005 | | | | |

---

## Appendix: Sample Test Data

### Seeded Users (from migration 0004)
- `admin` (Administrator, password: `admin123`, all permissions)
- `lab-manager` (Lab Manager, password: `labmanager123`, review/manage permissions)
- `lab-tech` (Lab Technician, password: `labtech123`, create/enter/manage permissions)

### Roles and Permissions Summary
| Role | Permissions |
|------|-------------|
| **Administrator** | All 13 permissions |
| **Lab Manager** | `project:manage`, `sample:create`, `sample:read`, `sample:update`, `test:assign`, `test:update`, `result:enter`, `result:review`, `batch:manage`, `batch:read` |
| **Lab Technician** | `sample:create`, `sample:read`, `sample:update`, `test:assign`, `test:update`, `result:enter`, `batch:manage`, `batch:read` |
| **Client** | `sample:read` only |

### Projects
- `Project Alpha` (`client_id` = Client Alpha UUID)
- `Project Beta` (`client_id` = Client Beta UUID)

### Samples
- `SAMPLE-ALPHA-001` (in Project Alpha, accessible to Client Alpha)
- `SAMPLE-BETA-001` (in Project Beta, not accessible to Client Alpha)

### Key Permissions for Testing
| Permission | Used For | Required By |
|------------|----------|-------------|
| `sample:create` | Creating samples | Accessioning workflow |
| `sample:read` | Viewing samples | All sample views |
| `sample:update` | Editing samples | Sample editing workflow |
| `config:edit` | Lists, custom fields, analyses | Admin configuration |
| `result:enter` | Entering test results | Results entry workflow |
| `result:review` | Reviewing/approving results | Lab Manager review |
| `batch:manage` | Creating/managing batches | Batch workflow |
| `project:manage` | Managing projects | Project configuration |

