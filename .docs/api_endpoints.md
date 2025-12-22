# API Endpoints Reference

## Authentication

### POST /auth/login
Login and receive JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

### GET /auth/me
Get current user information.

**Headers:** `Authorization: Bearer <token>`

## Samples

### GET /samples
List samples with filtering and pagination.

**Query Parameters:**
- `project_id` (optional, UUID): Filter by project ID
- `status` (optional, UUID): Filter by status ID
- `qc_type` (optional, UUID): Filter by QC type ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Response:**
```json
{
  "samples": [...],
  "total": 100,
  "page": 1,
  "size": 10,
  "pages": 10
}
```

**Note:** Empty string query parameters are automatically converted to `None`.

### POST /samples
Create a new sample.

**Requires:** `sample:create` permission

## Projects

### GET /projects
List projects accessible to the current user.

**Response:**
```json
[
  {
    "id": "...",
    "name": "...",
    "client": {...}
  }
]
```

**RBAC:**
- Administrators see all projects
- Lab users see projects they have access to via `project_users`
- Client users see only their client's projects

## Batches

### GET /batches
List batches with filtering and pagination.

**Query Parameters:**
- `status` (optional, UUID): Filter by batch status ID
- `type` (optional, UUID): Filter by batch type ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** `batch:read` permission

**Response:**
```json
{
  "batches": [...],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### POST /batches
Create a new batch.

**Requires:** `batch:manage` permission

## Lists

### GET /lists/{list_name}/entries
Get all entries for a specific list.

**Path Parameters:**
- `list_name` (string): Normalized list name (e.g., `sample_status`, `batch_status`)

**Response:**
```json
[
  {
    "id": "...",
    "name": "...",
    "description": "...",
    "active": true
  }
]
```

**Available Lists:**
- `sample_status` - Sample statuses
- `test_status` - Test statuses
- `project_status` - Project statuses
- `batch_status` - Batch statuses
- `sample_types` - Sample types
- `matrix_types` - Matrix types
- `qc_types` - QC types
- `unit_types` - Unit types
- `contact_types` - Contact types

**Note:** List names are normalized to lowercase slug format (e.g., "Sample Status" → `sample_status`).

### GET /lists
Get all lists with their entries.

## Analyses

### GET /analyses
List all active analyses.

**Response:**
```json
[
  {
    "id": "...",
    "name": "...",
    "method": "...",
    "turnaround_time": 5,
    "cost": 100.00
  }
]
```

### POST /analyses
Create a new analysis.

**Requires:** `config:edit` or `test:configure` permission

**Request:**
```json
{
  "name": "pH Measurement",
  "description": "pH analysis",
  "method": "Electrometric",
  "turnaround_time": 1,
  "cost": 10.00
}
```

### PATCH /analyses/{id}
Update an analysis.

**Requires:** `config:edit` or `test:configure` permission

### DELETE /analyses/{id}
Soft-delete an analysis.

**Requires:** `config:edit` or `test:configure` permission

**Note:** Cannot delete if referenced by any tests.

### GET /analyses/{id}/analytes
Get all analytes assigned to an analysis.

### PUT /analyses/{id}/analytes
Update analyte assignment for an analysis.

**Requires:** `config:edit` or `test:configure` permission

**Request:**
```json
{
  "analyte_ids": ["uuid1", "uuid2"]
}
```

### GET /analyses/{id}/analyte-rules
Get all validation rules for analytes in an analysis.

**Response:**
```json
[
  {
    "analyte_id": "...",
    "analyte_name": "pH",
    "data_type": "numeric",
    "high_value": 14.0,
    "low_value": 0.0,
    "significant_figures": 2,
    "is_required": true
  }
]
```

### POST /analyses/{id}/analyte-rules
Create a validation rule for an analyte in an analysis.

**Requires:** `config:edit` or `test:configure` permission

### PATCH /analyses/{id}/analyte-rules/{analyte_id}
Update a validation rule for an analyte.

**Requires:** `config:edit` or `test:configure` permission

### DELETE /analyses/{id}/analyte-rules/{analyte_id}
Delete a validation rule for an analyte.

**Requires:** `config:edit` or `test:configure` permission

## Analytes

### GET /analytes
List all active analytes.

**Response:**
```json
[
  {
    "id": "...",
    "name": "pH",
    "description": "pH value"
  }
]
```

### POST /analytes
Create a new analyte.

**Requires:** `config:edit` or `test:configure` permission

**Request:**
```json
{
  "name": "pH",
  "description": "pH value"
}
```

### PATCH /analytes/{id}
Update an analyte.

**Requires:** `config:edit` or `test:configure` permission

### DELETE /analytes/{id}
Soft-delete an analyte.

**Requires:** `config:edit` or `test:configure` permission

**Note:** Cannot delete if referenced by any analyses.

## Units

### GET /units
List all active units.

**Response:**
```json
[
  {
    "id": "...",
    "name": "g/L",
    "multiplier": 1.0,
    "type": "..."
  }
]
```

## Containers

### GET /containers
List containers with filtering.

**Query Parameters:**
- `type_id` (optional, UUID): Filter by container type
- `parent_id` (optional, UUID): Filter by parent container

### GET /containers/types
Get all container types.

**Response:**
```json
[
  {
    "id": "...",
    "name": "...",
    "capacity": 10.0,
    "material": "..."
  }
]
```

## Common Response Formats

### Paginated List Response
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 10,
  "pages": 10
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

## Authentication

All endpoints (except `/auth/login`) require a JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Users

### GET /users
List all users with optional filtering.

**Requires:** `user:manage` or `config:edit` permission

**Query Parameters:**
- `role_id` (optional, UUID): Filter by role ID
- `client_id` (optional, UUID): Filter by client ID

### POST /users
Create a new user.

**Requires:** `user:manage` or `config:edit` permission

### PATCH /users/{id}
Update a user.

**Requires:** `user:manage` or `config:edit` permission

### DELETE /users/{id}
Soft-delete a user.

**Requires:** `user:manage` or `config:edit` permission

## Roles

### GET /roles
List all active roles.

### POST /roles
Create a new role.

**Requires:** `user:manage` or `config:edit` permission

### PATCH /roles/{id}
Update a role.

**Requires:** `user:manage` or `config:edit` permission

### DELETE /roles/{id}
Soft-delete a role.

**Requires:** `user:manage` or `config:edit` permission

### PUT /roles/{id}/permissions
Update permissions for a role.

**Requires:** `user:manage` or `config:edit` permission

**Request:**
```json
{
  "permission_ids": ["uuid1", "uuid2"]
}
```

## Permissions

### GET /permissions
List all permissions.

**Requires:** `user:manage` or `config:edit` permission

## Permissions Reference

Endpoints require specific permissions:
- `sample:read` - Read samples
- `sample:create` - Create samples
- `sample:update` - Update samples
- `batch:read` - Read batches
- `batch:manage` - Manage batches
- `result:enter` - Enter results
- `result:review` - Review results
- `config:edit` - Edit system configuration (lists, container types, analyses, analytes)
- `test:configure` - Configure tests and analyses
- `user:manage` - Manage users and roles
- And more...

See `.docs/lims_mvp_prd.md` for complete permission list.

