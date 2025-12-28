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

### POST /samples/accession
Accession a new sample with test assignment.

**Requires:** `sample:create` permission

**Request:**
```json
{
  "name": "SAMPLE-001",
  "description": "Sample description",
  "due_date": "2025-12-31T00:00:00",
  "received_date": "2025-12-28T00:00:00",
  "sample_type": "uuid",
  "matrix": "uuid",
  "temperature": 4.0,
  "project_id": "uuid",
  "client_project_id": "uuid",
  "qc_type": "uuid",
  "anomalies": "Notes",
  "battery_id": "uuid",
  "assigned_tests": ["uuid1", "uuid2"]
}
```

**Response:** Sample with created tests

**Note:** This endpoint creates the sample and tests. Containers are created separately via `/containers` and linked via `/contents`.

### POST /samples/bulk-accession
Bulk accession multiple samples with common fields and unique per-sample data (US-24).

**Requires:** `sample:create` permission

**Request:**
```json
{
  "due_date": "2025-12-31T00:00:00",
  "received_date": "2025-12-28T00:00:00",
  "sample_type": "uuid",
  "matrix": "uuid",
  "project_id": "uuid",
  "client_project_id": "uuid",
  "container_type_id": "uuid",
  "qc_type": "uuid",
  "battery_id": "uuid",
  "assigned_tests": ["uuid1"],
  "auto_name_prefix": "SAMPLE-",
  "auto_name_start": 1,
  "uniques": [
    {
      "name": "SAMPLE-001",
      "client_sample_id": "CLIENT-001",
      "container_name": "CONTAINER-001",
      "temperature": 4.0,
      "description": "Description",
      "anomalies": "Notes"
    }
  ]
}
```

**Response:** List of created samples

**Note:** Creates all samples, containers, contents, and tests atomically in a single transaction.

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
Create a new batch with cross-project support and QC sample generation (US-26, US-27).

**Requires:** `batch:manage` permission

**Request:**
```json
{
  "name": "Batch-001",
  "description": "Batch description",
  "type": "uuid",
  "status": "uuid",
  "start_date": "2025-12-28T00:00:00",
  "end_date": null,
  "container_ids": ["uuid1", "uuid2"],
  "cross_project": true,
  "divergent_analyses": ["uuid"],
  "qc_additions": [
    {
      "qc_type": "uuid",
      "notes": "QC notes"
    }
  ]
}
```

**Features:**
- **Cross-Project Batching (US-26)**: Auto-detects when containers are from multiple projects. Validates compatibility (shared analyses) and RLS access.
- **QC at Batch Creation (US-27)**: Auto-generates QC samples/containers atomically within batch transaction. QC samples inherit properties from first sample.

**Response:** Batch with containers

**Error Responses:**
- `400`: Incompatible samples (no shared analyses), QC required but not provided
- `403`: Insufficient project permissions (cross-project access denied)

### POST /batches/validate-compatibility
Validate container compatibility for cross-project batching without creating batch.

**Requires:** `batch:manage` permission

**Request:**
```json
{
  "container_ids": ["uuid1", "uuid2"]
}
```

**Response:**
```json
{
  "compatible": true,
  "details": {
    "projects": ["uuid1", "uuid2"],
    "common_analyses": ["Analysis Name"]
  }
}
```

Or if incompatible:
```json
{
  "compatible": false,
  "error": "Incompatible samples: no shared analyses found",
  "details": {
    "projects": ["uuid1", "uuid2"],
    "analyses": ["Analysis 1", "Analysis 2"],
    "suggestion": "Samples must share at least one common analysis"
  }
}
```

### GET /batches/{id}
Get batch details with containers.

**Requires:** `batch:read` permission

### POST /batches/{id}/containers
Add container to existing batch.

**Requires:** `batch:manage` permission

## Results

### GET /results
List results with filtering and pagination.

**Query Parameters:**
- `test_id` (optional, UUID): Filter by test ID
- `analyte_id` (optional, UUID): Filter by analyte ID
- `entered_by` (optional, UUID): Filter by user who entered results
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** `result:read` permission

### GET /results/{id}
Get a specific result by ID.

**Requires:** `result:read` permission

### POST /results
Enter a single result.

**Requires:** `result:enter` permission

**Request:**
```json
{
  "test_id": "uuid",
  "analyte_id": "uuid",
  "raw_result": "10.5",
  "reported_result": "10.5",
  "qualifiers": "uuid",
  "calculated_result": null
}
```

### POST /results/batch
Enter results for multiple tests/samples in a batch atomically (US-28: Batch Results Entry).

**Requires:** `result:enter` and `batch:read` permissions

**Request:**
```json
{
  "batch_id": "uuid",
  "results": [
    {
      "test_id": "uuid",
      "analyte_results": [
        {
          "analyte_id": "uuid",
          "raw_result": "10.5",
          "reported_result": "10.5",
          "qualifiers": "uuid",
          "notes": "Notes"
        }
      ]
    }
  ]
}
```

**Features:**
- Validates all results against analysis_analytes rules (data type, range, sig figs, required)
- Creates/updates results in transaction
- Updates test statuses to "Complete" when all analytes entered
- Auto-updates batch status to "Completed" when all tests complete
- QC validation: Checks QC samples for failures
- Configurable QC blocking via `FAIL_QC_BLOCKS_BATCH` env var

**Response:** Updated batch with containers

**Error Responses:**
- `400`: Validation errors (detailed per test/analyte), QC failures (if blocking enabled)
- `403`: Insufficient permissions
- `404`: Batch not found

### POST /results/validate
Validate a result before entry.

**Request:**
```json
{
  "test_id": "uuid",
  "analyte_id": "uuid",
  "raw_result": "10.5",
  "reported_result": "10.5"
}
```

**Response:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "significant_figures": 2,
  "data_type": "numeric",
  "high_value": 14.0,
  "low_value": 0.0
}
```

### PATCH /results/{id}
Update a result.

**Requires:** `result:update` permission

### DELETE /results/{id}
Soft-delete a result.

**Requires:** `result:delete` permission

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

### POST /results/batch
Enter results for multiple tests/samples in a batch atomically (US-28: Batch Results Entry).

**Requires:** `result:enter` and `batch:read` permissions

**Request:**
```json
{
  "batch_id": "uuid",
  "results": [
    {
      "test_id": "uuid",
      "analyte_results": [
        {
          "analyte_id": "uuid",
          "raw_result": "10.5",
          "reported_result": "10.5",
          "qualifiers": "uuid",
          "notes": "Notes"
        }
      ]
    }
  ]
}
```

**Features:**
- Validates all results against analysis_analytes rules (data type, range, sig figs, required)
- Creates/updates results in transaction
- Updates test statuses to "Complete" when all analytes entered
- Auto-updates batch status to "Completed" when all tests complete
- QC validation: Checks QC samples for failures
- Configurable QC blocking via `FAIL_QC_BLOCKS_BATCH` env var

**Response:** Updated batch with containers

**Error Responses:**
- `400`: Validation errors (detailed per test/analyte), QC failures (if blocking enabled)
- `403`: Insufficient permissions
- `404`: Batch not found

### POST /results/validate
Validate a result before entry.

**Request:**
```json
{
  "test_id": "uuid",
  "analyte_id": "uuid",
  "raw_result": "10.5",
  "reported_result": "10.5"
}
```

**Response:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "significant_figures": 2,
  "data_type": "numeric",
  "high_value": 14.0,
  "low_value": 0.0
}
```

## Test Batteries

### GET /test-batteries
List test batteries with filtering.

**Query Parameters:**
- `name` (optional, string): Filter by name
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

### GET /test-batteries/{id}
Get battery with analyses.

### POST /test-batteries
Create a new test battery.

**Requires:** `config:edit` or `test:configure` permission

**Request:**
```json
{
  "name": "EPA 8080 Full",
  "description": "Full EPA Method 8080 battery"
}
```

### PATCH /test-batteries/{id}
Update a test battery.

**Requires:** `config:edit` or `test:configure` permission

### DELETE /test-batteries/{id}
Soft-delete a test battery.

**Requires:** `config:edit` or `test:configure` permission

**Note:** Returns 409 Conflict if referenced by any tests.

### GET /test-batteries/{id}/analyses
List analyses in battery with sequence and optional flags.

### POST /test-batteries/{id}/analyses
Add analysis to battery.

**Requires:** `config:edit` or `test:configure` permission

**Request:**
```json
{
  "analysis_id": "uuid",
  "sequence": 1,
  "optional": false
}
```

### PATCH /test-batteries/{id}/analyses/{analysis_id}
Update sequence/optional for analysis in battery.

**Requires:** `config:edit` or `test:configure` permission

### DELETE /test-batteries/{id}/analyses/{analysis_id}
Remove analysis from battery.

**Requires:** `config:edit` or `test:configure` permission

## Client Projects

### GET /client-projects
List client projects accessible to the current user.

**Requires:** `project:manage` permission

### POST /client-projects
Create a new client project.

**Requires:** `project:manage` permission

**Request:**
```json
{
  "name": "Client Project Name",
  "description": "Description",
  "client_id": "uuid"
}
```

### GET /client-projects/{id}
Get client project details.

**Requires:** `project:manage` permission

### PATCH /client-projects/{id}
Update a client project.

**Requires:** `project:manage` permission

### DELETE /client-projects/{id}
Soft-delete a client project.

**Requires:** `project:manage` permission

## Permissions Reference

Endpoints require specific permissions. The system currently has 17 permissions:

**Sample Permissions:**
- `sample:create` - Create samples
- `sample:read` - Read samples
- `sample:update` - Update samples

**Test Permissions:**
- `test:assign` - Assign tests to samples
- `test:update` - Update tests

**Result Permissions:**
- `result:enter` - Enter results
- `result:review` - Review results
- `result:update` - Update results
- `result:delete` - Delete results

**Batch Permissions:**
- `batch:read` - Read batches
- `batch:manage` - Manage batches
- `batch:update` - Update batches
- `batch:delete` - Delete batches

**Project Permissions:**
- `project:manage` - Manage projects

**System Permissions:**
- `user:manage` - Manage users
- `role:manage` - Manage roles
- `config:edit` - Edit system configuration (lists, container types, analyses, analytes)

**Note**: The code references `test:configure` permission in analyses, analytes, and test batteries endpoints, but this permission is not currently in the database. These endpoints use `require_any_permission(["config:edit", "test:configure"])`, which effectively requires `config:edit` permission.

See `.docs/lims_mvp_prd.md` for complete permission list.

