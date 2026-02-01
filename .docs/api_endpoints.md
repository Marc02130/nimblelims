# API Endpoints Reference

## Client Data Isolation

**Important:** All endpoints enforce client data isolation at both the database (RLS) and API layers:

### System Client Users (Lab Employees)
- Users with `client_id = System client ID` (`00000000-0000-0000-0000-000000000001`) have **full access** to all data
- This includes Lab Technicians, Lab Managers, and any other lab employees
- No client_id restrictions apply

### Regular Client Users
- Users with a specific `client_id` can only access data where `project.client_id = user.client_id`
- API layer validates this in create/update operations
- Returns `403 Forbidden` if attempting to access/modify data from other clients

### Administrators
- Administrators have full access to all data regardless of client_id

### Implementation Details
- **List endpoints (GET)**: RLS policies automatically filter results - no Python-level filtering needed
- **Create/Update endpoints (POST/PATCH)**: API layer validates `project.client_id` matches `user.client_id` (unless System/Admin)
- **RLS Policies**: Enforce access at database level using `has_project_access()` function
- **Error Response**: `403 Forbidden` with message "Access denied: insufficient client permissions"

### Access Control Flow
1. User authenticates → `get_current_user()` sets `app.current_user_id` session variable
2. RLS policies evaluate using `current_user_id()` function
3. `has_project_access()` checks:
   - If user is Administrator → return TRUE
   - If `user.client_id == System_client_id` → return TRUE (full access)
   - If `project.client_id == user.client_id` → return TRUE
   - Fallback to `project_users` junction for granular grants
4. API layer adds explicit validation for create/update operations

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
- `custom.{attr_name}` (optional, any): Filter by custom attribute (e.g., `?custom.ph_level=7.5`)
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

**Access Control:**
- Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
- No Python-level filtering is applied - RLS automatically filters samples based on project access
- **System client users (lab employees)**: See all samples (full access)
- **Client users**: See samples from projects where `project.client_id = user.client_id`
- **Administrators**: See all samples
- The RLS policy `samples_access` uses `has_project_access(project_id)` to determine visibility
- **Create/Update operations**: API layer validates `project.client_id` matches `user.client_id` (unless System/Admin)

**Note:** Empty string query parameters are automatically converted to `None`.

### POST /samples
Create a new sample.

**Requires:** `sample:create` permission

**Client Isolation:**
- Non-System/Admin users can only create samples for projects where `project.client_id = user.client_id`
- Returns `403 Forbidden` if attempting to create sample for another client's project

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
  "assigned_tests": ["uuid1", "uuid2"],
  "custom_attributes": {
    "ph_level": 7.5,
    "color": "blue"
  }
}
```

**Note:** `custom_attributes` are validated against active configurations for 'samples' entity type.

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

### GET /samples/{id}
Get a specific sample by ID.

**Requires:** `sample:read` permission

**Response:** Sample object with all fields

### PATCH /samples/{id}
Partially update a sample (edit mode).

**Requires:** `sample:update` permission

**Request (all fields optional, partial update):**
```json
{
  "name": "SAMPLE-001-UPDATED",
  "description": "Updated description",
  "status": "uuid",
  "custom_attributes": {
    "ph_level": 7.2,
    "notes": "Sample appears normal"
  }
}
```

**Example: Update sample status to 'Reviewed'**
```json
{
  "status": "reviewed-status-uuid"
}
```

**Response:** Updated sample object

**Features:**
- Partial updates: Only send fields that need to change
- Custom attributes validation: Validated against active configurations for 'samples' entity type
- Audit fields: Automatically updates `modified_at` and `modified_by` with current user and timestamp
- Atomic transaction: All updates succeed or fail together
- RLS enforcement: User must have access to sample's project (enforced by RLS policies)

**Error Responses:**
- `404`: Sample not found
- `403`: Permission denied (no `sample:update` permission) or RLS denies access
- `422`: Validation error (invalid data, custom attributes don't match config)

## Tests

### GET /tests
List tests with filtering and pagination.

**Query Parameters:**
- `sample_id` (optional, UUID): Filter by sample ID
- `analysis_id` (optional, UUID): Filter by analysis ID
- `status` (optional, UUID): Filter by status ID
- `technician_id` (optional, UUID): Filter by technician ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** Authentication (scoped by user access via RLS)

**Access Control:**
- Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
- **System client users**: See all tests (full access)
- **Client users**: See tests for samples from their client's projects
- **Administrators**: See all tests
- RLS policy `tests_access` uses `has_project_access()` via sample's project

**Response:**
```json
{
  "tests": [...],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### GET /tests/{id}
Get a specific test by ID.

**Requires:** Authentication (scoped by user access via RLS)

**Response:** Test object with all fields

### PATCH /tests/{id}
Partially update a test (edit mode).

**Requires:** `test:update` permission

**Request (all fields optional, partial update):**
```json
{
  "status": "uuid",
  "technician_id": "uuid",
  "test_date": "2025-01-15T10:00:00",
  "custom_attributes": {
    "instrument": "GC-MS-001",
    "run_number": "2025-001"
  }
}
```

**Example: Update test status to 'Complete'**
```json
{
  "status": "complete-status-uuid"
}
```

**Example: Update technician assignment**
```json
{
  "technician_id": "technician-uuid",
  "test_date": "2025-01-15T10:00:00"
}
```

**Response:** Updated test object

**Features:**
- Partial updates: Only send fields that need to change
- Custom attributes validation: Validated against active configurations for 'tests' entity type
- Audit fields: Automatically updates `modified_at` and `modified_by` with current user and timestamp
- Atomic transaction: All updates succeed or fail together
- RLS enforcement: User must have access to test's sample's project (enforced by RLS policies)

**Error Responses:**
- `404`: Test not found
- `403`: Permission denied (no `test:update` permission) or RLS denies access
- `422`: Validation error (invalid data, custom attributes don't match config)

## Containers

### GET /containers
List containers with filtering and pagination.

**Query Parameters:**
- `type_id` (optional, UUID): Filter by container type ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** `sample:read` permission (containers link to samples)

**Response:**
```json
{
  "containers": [...],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### GET /containers/{id}
Get a specific container by ID.

**Requires:** `sample:read` permission

**Response:** Container object with all fields

### PATCH /containers/{id}
Partially update a container (edit mode).

**Requires:** `sample:update` permission (since containers link to samples)

**Request (all fields optional, partial update):**
```json
{
  "name": "CONTAINER-001-UPDATED",
  "type_id": "uuid",
  "concentration": 15.5,
  "concentration_units": "uuid",
  "custom_attributes": {
    "storage_location": "Freezer A-1"
  }
}
```

**Example: Update container name and concentration**
```json
{
  "name": "CONTAINER-001-UPDATED",
  "concentration": 15.5,
  "concentration_units": "unit-uuid"
}
```

**Response:** Updated container object

**Features:**
- Partial updates: Only send fields that need to change
- Custom attributes validation: Validated against active configurations for 'containers' entity type
- Audit fields: Automatically updates `modified_at` and `modified_by` with current user and timestamp
- Atomic transaction: All updates succeed or fail together
- Container type validation: Validates that `type_id` exists and is active

**Error Responses:**
- `404`: Container not found
- `403`: Permission denied (no `sample:update` permission) or RLS denies access
- `400`: Invalid container type ID or parent container ID
- `422`: Validation error (invalid data, custom attributes don't match config)

## Projects

### GET /projects
List projects accessible to the current user with optional filtering and pagination.

**Access Control:**
- Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
- No Python-level filtering is applied - RLS automatically filters projects based on `projects_access` policy
- Administrators see all projects
- Lab Technicians and Lab Managers see all active projects (per RLS policy in migration 0024)
- Client users see only projects for their client_id (RLS enforced)
- Lab users with project_users entries see those specific projects (via `has_project_access` function)
- The session variable `app.current_user_id` is set via `set_current_user_id()` in `get_current_user()` dependency

**Query Parameters:**
- `status` (optional, UUID): Filter by status ID
- `client_id` (optional, UUID): Filter by client ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10, max=100): Page size

**Response:**
```json
{
  "projects": [
    {
      "id": "uuid",
      "name": "Project Name",
      "description": "Project description",
      "start_date": "2025-01-01T00:00:00Z",
      "client_id": "uuid",
      "client_project_id": "uuid",
      "status": "uuid",
      "active": true,
      "created_at": "2025-01-01T00:00:00Z",
      "modified_at": "2025-01-01T00:00:00Z",
      "client": {
        "id": "uuid",
        "name": "Client Name"
      },
      "client_project": {
        "id": "uuid",
        "name": "Client Project Name"
      },
      "custom_attributes": {}
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### GET /projects/{id}
Get a single project by ID.

**Access Control:** 
- RLS enforced via `projects_access` policy
- **System client users**: See all projects (full access)
- **Client users**: See projects where `project.client_id = user.client_id`
- **Administrators**: See all projects
- Returns 404 if project not found or user doesn't have access

**Response:** Project object (same structure as in list response)

### POST /projects
Create a new project.

**Requires:** `project:manage` permission

**Client Isolation:**
- Non-System/Admin users can only create projects for their own client (`project.client_id = user.client_id`)
- Returns `403 Forbidden` if attempting to create project for another client

**Request:**
```json
{
  "name": "Project Name",
  "description": "Project description",
  "start_date": "2025-01-01T00:00:00Z",
  "client_id": "uuid",
  "client_project_id": "uuid",
  "status": "uuid",
  "custom_attributes": {
    "contract_number": "CONTRACT-123"
  }
}
```

**Note:** 
- `name` is optional - if not provided, auto-generated using client name + timestamp
- `client_project_id` is optional - if provided, must belong to the specified `client_id`
- `custom_attributes` are validated against active configurations for 'projects' entity type
- Sets audit fields (`created_by`, `modified_by`)

**Response:** 201 Created with project object

### PATCH /projects/{id}
Update a project (partial update).

**Requires:** `project:manage` permission

**Client Isolation:**
- Non-System/Admin users can only update projects where `project.client_id = user.client_id`
- If updating `client_id`, the new `client_id` must match `user.client_id` (unless System/Admin)
- Returns `403 Forbidden` if attempting to update another client's project

**Request:** (all fields optional)
```json
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "start_date": "2025-01-02T00:00:00Z",
  "client_id": "uuid",
  "client_project_id": "uuid",
  "status": "uuid",
  "active": false,
  "custom_attributes": {
    "contract_number": "CONTRACT-456"
  }
}
```

**Note:**
- Validates `client_project_id` belongs to `client_id` if both provided
- Updates audit fields (`modified_by`, `modified_at`)
- Custom attributes validated against active configurations

**Response:** Updated project object

### DELETE /projects/{id}
Soft delete a project (sets active=false).

**Requires:** `project:manage` permission

**Response:** 204 No Content

**Note:** Updates audit fields (`modified_by`, `modified_at`)

## Batches

### GET /batches
List batches with filtering and pagination.

**Query Parameters:**
- `status` (optional, UUID): Filter by batch status ID
- `type` (optional, UUID): Filter by batch type ID
- `custom.{attr_name}` (optional, any): Filter by custom attribute (e.g., `?custom.instrument_serial=INST-12345`)
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** `batch:read` permission

**Access Control:**
- Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
- **System client users**: See all batches (full access)
- **Client users**: See batches containing samples from their client's projects
- **Administrators**: See all batches
- RLS policy `batches_access` uses `has_project_access()` via containers → contents → samples → projects chain

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

**Client Isolation:**
- Non-System/Admin users can only create batches with containers from their own client's projects
- API validates access to all projects in the batch before creation
- Returns `403 Forbidden` if attempting to create batch with containers from another client's projects

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
  ],
  "custom_attributes": {
    "instrument_serial": "INST-12345"
  }
}
```

**Features:**
- **Cross-Project Batching (US-26)**: Auto-detects when containers are from multiple projects. Validates compatibility (shared analyses) and RLS access.
- **QC at Batch Creation (US-27)**: Auto-generates QC samples/containers atomically within batch transaction. QC samples inherit properties from first sample.

**Note:** `custom_attributes` are validated against active configurations for 'batches' entity type.

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
- `custom.{attr_name}` (optional, any): Filter by custom attribute (e.g., `?custom.reviewer_notes=Looks good`)
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Requires:** `result:read` permission

**Access Control:**
- Access control is enforced entirely by Row-Level Security (RLS) policies at the database level
- **System client users**: See all results (full access)
- **Client users**: See results for tests from their client's projects
- **Administrators**: See all results
- RLS policy `results_access` uses `has_project_access()` via test → sample → project chain

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
  "calculated_result": null,
  "custom_attributes": {
    "reviewer_notes": "Looks good"
  }
}
```

**Note:** `custom_attributes` are validated against active configurations for 'results' entity type.

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

### GET /lists
Get all active lists with their entries.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "sample_status",
    "description": "Sample status values",
    "active": true,
    "created_at": "2024-01-01T00:00:00",
    "modified_at": "2024-01-01T00:00:00",
    "entries": [
      {
        "id": "uuid",
        "name": "Received",
        "description": "Sample received",
        "active": true,
        "created_at": "2024-01-01T00:00:00",
        "modified_at": "2024-01-01T00:00:00",
        "list_id": "uuid"
      }
    ]
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

### POST /lists
Create a new list.

**Requires:** `config:edit` permission

**Request:**
```json
{
  "name": "custom_list",
  "description": "A custom list for specific workflow"
}
```

**Response:** 201 Created
```json
{
  "id": "uuid",
  "name": "custom_list",
  "description": "A custom list for specific workflow",
  "active": true,
  "created_at": "2024-01-01T00:00:00",
  "modified_at": "2024-01-01T00:00:00",
  "entries": []
}
```

**Error Responses:**
- `400`: List with same name already exists
- `403`: User lacks `config:edit` permission

### PATCH /lists/{list_id}
Update an existing list.

**Requires:** `config:edit` permission

**Path Parameters:**
- `list_id` (UUID): The list ID

**Request (all fields optional):**
```json
{
  "name": "updated_list_name",
  "description": "Updated description",
  "active": false
}
```

**Response:** Updated list object

**Error Responses:**
- `404`: List not found
- `400`: List with new name already exists
- `403`: User lacks `config:edit` permission

### DELETE /lists/{list_id}
Soft-delete a list (sets active=false).

**Requires:** `config:edit` permission

**Path Parameters:**
- `list_id` (UUID): The list ID

**Response:** 204 No Content

**Error Responses:**
- `404`: List not found
- `403`: User lacks `config:edit` permission

**Note:** Soft delete - list is marked inactive but not removed from database.

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

## Analyses

### GET /analyses
List analyses with optional filtering, search, and pagination.

**Query Parameters:**
- `search` (optional, string): Search by name or method (case-insensitive)
- `active` (optional, boolean): Filter by active status (default: only active for non-admin users)
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10, max=100): Page size

**Response:**
```json
{
  "analyses": [
    {
      "id": "uuid",
      "name": "EPA 8080",
      "description": "Organochlorine pesticides analysis",
      "method": "EPA 8080",
      "turnaround_time": 5,
      "cost": 100.00,
      "shelf_life": 14,
      "active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "modified_at": "2026-01-01T00:00:00Z",
      "created_by": "uuid",
      "modified_by": "uuid",
      "custom_attributes": {},
      "analytes": [
        {"id": "uuid", "name": "Aldrin", "description": "Organochlorine pesticide"}
      ]
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### GET /analyses/{id}
Get a single analysis by ID with linked analytes.

**Response:** AnalysisResponse (same structure as in list response)

**Error Responses:**
- `404`: Analysis not found

### POST /analyses
Create a new analysis.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request:**
```json
{
  "name": "pH Measurement",
  "description": "pH analysis",
  "method": "Electrometric",
  "turnaround_time": 1,
  "cost": 10.00,
  "shelf_life": 30,
  "custom_attributes": {
    "instrument_type": "meter"
  }
}
```

**Note:** 
- `name` is optional - auto-generated if not provided
- `method` is required

**Response:** AnalysisResponse (HTTP 201 Created)

**Error Responses:**
- `400`: Analysis name already exists

### PATCH /analyses/{id}
Update an analysis (partial update).

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request (all fields optional):**
```json
{
  "name": "Updated Analysis Name",
  "method": "Updated Method",
  "turnaround_time": 7,
  "cost": 150.00,
  "active": false,
  "custom_attributes": {"notes": "Updated"}
}
```

**Response:** Updated AnalysisResponse

**Error Responses:**
- `404`: Analysis not found
- `400`: Analysis name already exists (if changing name)

### DELETE /analyses/{id}
Soft-delete an analysis (sets active=false).

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Response:** HTTP 204 No Content

**Error Responses:**
- `404`: Analysis not found
- `400`: Cannot delete - active tests reference this analysis

### GET /analyses/{id}/analytes
Get all analytes linked to an analysis.

**Response:**
```json
[
  {"id": "uuid", "name": "pH", "description": "pH value"}
]
```

### POST /analyses/{id}/analytes
Link analytes to an analysis.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request:**
```json
{
  "analyte_ids": ["uuid1", "uuid2"]
}
```

**Note:** Idempotent - skips analytes already linked. Validates analyte IDs exist and are active.

**Response:** List of all linked analytes (HTTP 201 Created)

**Error Responses:**
- `404`: Analysis not found
- `400`: Invalid or inactive analyte IDs

### PUT /analyses/{id}/analytes
Replace all analyte assignments for an analysis (full replacement).

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request:**
```json
{
  "analyte_ids": ["uuid1", "uuid2"]
}
```

**Response:** List of linked analytes

### DELETE /analyses/{id}/analytes/{analyte_id}
Unlink a single analyte from an analysis.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Response:** HTTP 204 No Content

**Error Responses:**
- `404`: Analysis not found or analyte not linked to this analysis

### GET /analyses/{id}/analyte-rules
Get all validation rules for analytes in an analysis.

**Response:**
```json
[
  {
    "analyte_id": "uuid",
    "analyte_name": "pH",
    "data_type": "numeric",
    "list_id": null,
    "high_value": 14.0,
    "low_value": 0.0,
    "significant_figures": 2,
    "calculation": null,
    "reported_name": null,
    "display_order": 1,
    "is_required": true,
    "default_value": null
  }
]
```

### POST /analyses/{id}/analyte-rules
Create a validation rule for an analyte in an analysis.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request:**
```json
{
  "analyte_id": "uuid",
  "data_type": "numeric",
  "high_value": 14.0,
  "low_value": 0.0,
  "significant_figures": 2,
  "is_required": true
}
```

**Response:** AnalyteRuleResponse (HTTP 201 Created)

**Error Responses:**
- `404`: Analysis not found
- `400`: Analyte rule already exists, invalid analyte_id, or low_value > high_value

### PATCH /analyses/{id}/analyte-rules/{analyte_id}
Update a validation rule for an analyte.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

### DELETE /analyses/{id}/analyte-rules/{analyte_id}
Delete a validation rule for an analyte.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

## Analytes

### GET /analytes
List analytes with optional filtering, search, and pagination.

**Query Parameters:**
- `search` (optional, string): Search by name or CAS number (case-insensitive)
- `active` (optional, boolean): Filter by active status (default: only active for non-admin users)
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10, max=100): Page size

**Response:**
```json
{
  "analytes": [
    {
      "id": "uuid",
      "name": "pH",
      "description": "pH value",
      "cas_number": null,
      "units_default": "uuid",
      "data_type": "numeric",
      "active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "modified_at": "2026-01-01T00:00:00Z",
      "created_by": "uuid",
      "modified_by": "uuid",
      "custom_attributes": {}
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### GET /analytes/{id}
Get a single analyte by ID.

**Response:** AnalyteResponse (same structure as in list response)

**Error Responses:**
- `404`: Analyte not found

### POST /analytes
Create a new analyte.

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request:**
```json
{
  "name": "pH",
  "description": "pH value",
  "cas_number": "7732-18-5",
  "units_default": "uuid",
  "data_type": "numeric",
  "custom_attributes": {}
}
```

**Note:** 
- `name` is required and must be unique
- `data_type` options: `numeric`, `text`, `date`, `boolean`
- `units_default` must reference a valid, active unit

**Response:** AnalyteResponse (HTTP 201 Created)

**Error Responses:**
- `400`: Analyte name already exists or invalid units_default

### PATCH /analytes/{id}
Update an analyte (partial update).

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Request (all fields optional):**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "cas_number": "7732-18-5",
  "units_default": "uuid",
  "data_type": "text",
  "active": false,
  "custom_attributes": {"notes": "Updated"}
}
```

**Response:** Updated AnalyteResponse

**Error Responses:**
- `404`: Analyte not found
- `400`: Analyte name already exists (if changing name) or invalid units_default

### DELETE /analytes/{id}
Soft-delete an analyte (sets active=false).

**Requires:** `config:edit`, `test:configure`, or `analysis:manage` permission

**Response:** HTTP 204 No Content

**Error Responses:**
- `404`: Analyte not found
- `400`: Cannot delete - analyses reference this analyte

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

**Access Control:**
- **Administrators**: See all client projects
- **System client users (lab employees)**: See all active client projects (enforced by RLS, for sample creation workflows)
- **Client users**: See only client projects matching their `client_id` (enforced by RLS)
- RLS policy `client_projects_access` automatically filters based on client_id

**Implementation Note:** 
For Lab Technician and Lab Manager roles, the endpoint uses `func.count()` directly instead of `query.count()` to avoid SQLAlchemy subquery wrapping that can interfere with RLS evaluation. This ensures PostgreSQL RLS policies are properly applied at the database level.

**Requires:** `project:manage` permission

### POST /client-projects
Create a new client project.

**Requires:** `project:manage` permission

**Client Isolation:**
- Non-System/Admin users can only create client projects for their own client (`client_project.client_id = user.client_id`)
- Returns `403 Forbidden` if attempting to create client project for another client

**Request:**
```json
{
  "name": "Client Project Name",
  "description": "Description",
  "client_id": "uuid",
  "custom_attributes": {
    "contract_number": "CONTRACT-123"
  }
}
```

**Note:** `custom_attributes` are validated against active configurations for 'client_projects' entity type.

### GET /client-projects/{id}
Get client project details.

**Requires:** `project:manage` permission

### PATCH /client-projects/{id}
Update a client project.

**Requires:** `project:manage` permission

### DELETE /client-projects/{id}
Soft-delete a client project.

**Requires:** `project:manage` permission

## Custom Attributes Configuration

### GET /admin/custom-attributes
List custom attribute configurations with filtering and pagination.

**Requires:** `config:edit` permission

**Query Parameters:**
- `entity_type` (optional, string): Filter by entity type (e.g., 'samples', 'tests', 'results', 'projects', 'client_projects', 'batches')
- `active` (optional, boolean, default=true): Filter by active status
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Response:**
```json
{
  "configs": [
    {
      "id": "uuid",
      "entity_type": "samples",
      "attr_name": "ph_level",
      "data_type": "number",
      "validation_rules": {"min": 0, "max": 14},
      "description": "pH level of the sample",
      "active": true,
      "created_at": "2025-12-29T00:00:00Z",
      "created_by": "uuid",
      "modified_at": "2025-12-29T00:00:00Z",
      "modified_by": "uuid"
    }
  ],
  "total": 10,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### POST /admin/custom-attributes
Create a new custom attribute configuration.

**Requires:** `config:edit` permission

**Request:**
```json
{
  "entity_type": "samples",
  "attr_name": "ph_level",
  "data_type": "number",
  "validation_rules": {"min": 0, "max": 14},
  "description": "pH level of the sample"
}
```

**Response:** 201 Created with configuration object

**Validation:**
- `entity_type` must be one of: samples, tests, results, projects, client_projects, batches
- `attr_name` must be unique within entity_type
- `data_type` must be one of: text, number, date, boolean, select
- `validation_rules` must match data_type:
  - Text: `max_length`, `min_length` (integers)
  - Number: `min`, `max` (numbers)
  - Select: `options` (array of strings)
  - Date/Boolean: no specific rules required

### GET /admin/custom-attributes/{id}
Get a specific custom attribute configuration by ID.

**Requires:** `config:edit` permission

**Response:** Configuration object

### PATCH /admin/custom-attributes/{id}
Update an existing custom attribute configuration.

**Requires:** `config:edit` permission

**Request:** Partial update (all fields optional except those being updated)
```json
{
  "data_type": "text",
  "validation_rules": {"max_length": 100},
  "description": "Updated description",
  "active": false
}
```

**Response:** Updated configuration object

**Note:** If `attr_name` or `entity_type` is updated, uniqueness is re-checked.

### DELETE /admin/custom-attributes/{id}
Soft-delete a custom attribute configuration (sets active=false).

**Requires:** `config:edit` permission

**Response:** 204 No Content

**Note:** Existing data retains custom attributes, but new data cannot use inactive configs.

## Custom Attributes in Entity Endpoints

All entity create/update endpoints support `custom_attributes` in the request body:

### Samples
- **POST /samples**: Accepts `custom_attributes` object
- **PATCH /samples/{id}**: Accepts `custom_attributes` object
- **GET /samples**: Supports filtering via `?custom.attr_name=value`

**Example:**
```json
{
  "name": "SAMPLE-001",
  "custom_attributes": {
    "ph_level": 7.5,
    "color": "blue"
  }
}
```

### Tests
- **POST /tests**: Accepts `custom_attributes` object
- **PATCH /tests/{id}**: Accepts `custom_attributes` object
- **GET /tests**: Supports filtering via `?custom.attr_name=value`

### Results
- **POST /results**: Accepts `custom_attributes` object
- **PATCH /results/{id}**: Accepts `custom_attributes` object
- **GET /results**: Supports filtering via `?custom.attr_name=value`

### Projects
- Projects are read-only (no create/update endpoints), but custom_attributes are stored and returned in GET responses

### Client Projects
- **POST /client-projects**: Accepts `custom_attributes` object
- **PATCH /client-projects/{id}**: Accepts `custom_attributes` object

### Batches
- **POST /batches**: Accepts `custom_attributes` object
- **PATCH /batches/{id}**: Accepts `custom_attributes` object

**Validation:**
- All custom_attributes are validated server-side against active configurations
- Returns 400 Bad Request with detailed error message if validation fails
- Unknown attributes (not in config) are rejected
- Values must match data_type and validation_rules

**Querying:**
- List endpoints support filtering: `?custom.attr_name=value`
- Multiple custom filters: `?custom.attr1=value1&custom.attr2=value2`
- Uses PostgreSQL JSONB `@>` operator for efficient querying

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
- `config:edit` - Edit system configuration (lists, container types, analyses, analytes, custom attributes)

**Note**: The code references `test:configure` permission in analyses, analytes, and test batteries endpoints, but this permission is not currently in the database. These endpoints use `require_any_permission(["config:edit", "test:configure"])`, which effectively requires `config:edit` permission.

See `.docs/lims_mvp_prd.md` for complete permission list.

## Help Endpoints

### GET /help
Get help entries filtered by current user's role.

**Query Parameters:**
- `role` (optional, string): Filter by role (admins only). Accepts role name or slug (case-insensitive). Examples: 'Lab Technician', 'lab-technician', 'Lab Manager', 'lab-manager', 'Administrator', 'administrator', 'Client'. Defaults to current user's role.
- `section` (optional, string): Filter by section name.
- `page` (optional, int): Page number (default: 1)
- `size` (optional, int): Page size (default: 10, max: 100)
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10): Page size

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "help_entries": [
    {
      "id": "uuid",
      "section": "Viewing Projects",
      "content": "Step-by-step guide to access your samples and results...",
      "role_filter": "Client",
      "active": true,
      "created_at": "2025-01-03T12:00:00",
      "modified_at": "2025-01-03T12:00:00"
    }
  ],
  "total": 4,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

**Access Control:**
- Users see entries where `role_filter` matches their role OR `role_filter` is NULL (public)
- Users with `config:edit` permission see ALL entries when no `role` parameter is provided (for Help Management page)
- Users with `config:edit` permission can filter by any role using `?role=` parameter
- RLS enforces filtering at database level for users without `config:edit` permission

**Example:**
```bash
# Client user sees Client and public help
GET /help
Authorization: Bearer <client_token>

# Lab Technician user sees lab-technician and public help
GET /help
Authorization: Bearer <lab_technician_token>
# Backend automatically converts "Lab Technician" role name to "lab-technician" slug

# Lab Manager user sees lab-manager and public help
GET /help
Authorization: Bearer <lab_manager_token>
# Backend automatically converts "Lab Manager" role name to "lab-manager" slug

# Admin can filter by role (supports both role name and slug, case-insensitive)
GET /help?role=Client
Authorization: Bearer <admin_token>

GET /help?role=lab-technician
Authorization: Bearer <admin_token>

GET /help?role=lab-manager
Authorization: Bearer <admin_token>

GET /help?role=Lab Manager
Authorization: Bearer <admin_token>

GET /help?role=Lab Technician
Authorization: Bearer <admin_token>
# All above queries return same results (role name normalized to slug)

# Administrator filtering for administrator help
GET /help?role=administrator
Authorization: Bearer <admin_token>

GET /help?role=Administrator
Authorization: Bearer <admin_token>
# Both return administrator help entries

# Administrator with config:edit permission sees all entries (for Help Management)
GET /help
Authorization: Bearer <admin_token_with_config_edit>
# Returns ALL help entries (no role filtering applied)

# Filter by section
GET /help?section=Viewing Projects
Authorization: Bearer <client_token>

GET /help?section=Accessioning Workflow
Authorization: Bearer <lab_technician_token>

GET /help?section=Results Review
Authorization: Bearer <lab_manager_token>

GET /help?section=User Management
Authorization: Bearer <admin_token>
```

### GET /help/contextual
Get contextual help for a specific section.

**Query Parameters:**
- `section` (required, string): Section name for contextual help

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "uuid",
  "section": "Viewing Projects",
  "content": "Step-by-step guide to access your samples and results...",
  "role_filter": "Client",
  "active": true,
  "created_at": "2025-01-03T12:00:00",
  "modified_at": "2025-01-03T12:00:00"
}
```

**Access Control:**
- Returns help entry filtered by user's role
- Returns 404 if no matching help entry found

**Example:**
```bash
# Client user accessing contextual help
GET /help/contextual?section=Viewing Projects
Authorization: Bearer <client_token>

# Lab Technician accessing contextual help
GET /help/contextual?section=Accessioning Workflow
Authorization: Bearer <lab_technician_token>

# Lab Manager accessing contextual help
GET /help/contextual?section=Results Review
Authorization: Bearer <lab_manager_token>

GET /help/contextual?section=Batch Management
Authorization: Bearer <lab_manager_token>

# Administrator accessing contextual help
GET /help/contextual?section=User Management
Authorization: Bearer <admin_token>

GET /help/contextual?section=EAV Configuration
Authorization: Bearer <admin_token>

# Lab Technician user accessing contextual help
GET /help/contextual?section=Accessioning Workflow
Authorization: Bearer <lab_technician_token>
# Backend converts "Lab Technician" role to "lab-technician" slug for filtering
```

### POST /help/admin/help
Create a new help entry.

**Requires:** `config:edit` permission

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
- `section` (required, string): Section name (e.g., "User Management", "EAV Configuration")
- `content` (required, string): Help content text
- `role_filter` (optional, string | null): Role name or slug (e.g., "lab-technician", "lab-manager", "administrator", "client"). Will be validated against existing roles and normalized to slug format. Use null for public help entries.

**Validation:**
- `role_filter` must match an existing role (validated against roles table)
- `role_filter` is normalized to slug format (case-insensitive)
- Returns 400 if `role_filter` doesn't match any existing role

**Request:**
```json
{
  "section": "Viewing Samples",
  "content": "Learn how to view and filter your samples...",
  "role_filter": "Client"
}
```

**Response:**
```json
{
  "id": "uuid",
  "section": "Viewing Samples",
  "content": "Learn how to view and filter your samples...",
  "role_filter": "Client",
  "active": true,
  "created_at": "2025-01-03T12:00:00",
  "modified_at": "2025-01-03T12:00:00"
}
```

**Example:**
```bash
# Create Client help entry
POST /help/admin/help
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "Understanding Statuses",
  "content": "Sample statuses indicate the current state of your samples...",
  "role_filter": "Client"
}

# Create Lab Technician help entry (role_filter normalized to slug format)
POST /help/admin/help
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "Accessioning Workflow",
  "content": "Step-by-step guide to sample accessioning:\n\n1. Enter sample details...",
  "role_filter": "Lab Technician"
}
# Backend normalizes "Lab Technician" to "lab-technician" slug format

# Create public help entry
POST /help/admin/help
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "Getting Started",
  "content": "Welcome to NimbleLIMS!",
  "role_filter": null
}

# Create administrator help entry
POST /help/admin/help
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "User Management",
  "content": "Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.",
  "role_filter": "administrator"
}

# Create help entry with role name (normalized to slug)
POST /help/admin/help
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "EAV Configuration",
  "content": "Configure custom attributes using Entity-Attribute-Value (EAV) model.",
  "role_filter": "Administrator"
}
# Backend normalizes "Administrator" to "administrator" slug format
```

### PATCH /help/admin/help/{id}
Update a help entry (partial update).

**Requires:** `config:edit` permission

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `id` (required, UUID): Help entry ID

**Request Body (all fields optional):**
- `section` (optional, string): Section name
- `content` (optional, string): Help content text
- `role_filter` (optional, string | null): Role name or slug. Will be validated against existing roles and normalized to slug format.
- `active` (optional, boolean): Active status (for deactivating entries)

**Validation:**
- `role_filter` must match an existing role if provided (validated against roles table)
- `role_filter` is normalized to slug format (case-insensitive)
- Returns 400 if `role_filter` doesn't match any existing role
- Returns 404 if help entry not found

**Request:**
```json
{
  "content": "Updated help content...",
  "active": true
}
```

**Response:** Updated help entry object

**Example:**
```bash
PATCH /help/admin/help/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "content": "Updated content with more details..."
}

# Update multiple fields
PATCH /help/admin/help/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "section": "Updated Section Name",
  "content": "Updated content with more details.",
  "role_filter": "lab-manager"
}

# Deactivate help entry
PATCH /help/admin/help/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "active": false
}

# Update role_filter (validated against existing roles)
PATCH /help/admin/help/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "role_filter": "Administrator"
}
# Backend normalizes to "administrator" slug format
```

### DELETE /help/admin/help/{id}
Soft delete a help entry (sets active=false).

**Requires:** `config:edit` permission

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `id` (required, UUID): Help entry ID

**Response:**
- 204 No Content on success
- 404 Not Found if help entry doesn't exist
- 403 Forbidden if user lacks config:edit permission

**Note:** This is a soft delete operation. The help entry is marked as inactive (active=false) but not removed from the database. Inactive entries are not returned by GET /help endpoints.

**Response:** 204 No Content

**Example:**
```bash
DELETE /help/admin/help/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <admin_token>
```

---

## Admin - Name Templates

Name templates define how auto-generated entity names (e.g. sample, project, batch) are built. Placeholders: `{SEQ}` (padded by `seq_padding_digits`), `{YYYY}`, `{YY}`, `{MM}`, `{DD}`, `{YYYYMMDD}`, `{CLIENT}` (client abbreviation when set, else client name), `{BATCH}` (batch name), `{PROJECT}` (project name; e.g. when generating sample names). See `backend/app/core/name_generation.py` and `.docs/ids-and-configuration.md`.

### GET /admin/name-templates
List name templates with filtering and pagination.

**Requires:** `get_current_user`; full list for admins, active-only for others.

**Query Parameters:**
- `entity_type` (optional): Filter by entity type (sample, project, batch, analysis, container)
- `active` (optional, bool): Filter by active status
- `page` (optional, int, default=1)
- `size` (optional, int, default=10)

**Response:** `{ templates, total, page, size, pages }` — each template includes `id`, `entity_type`, `template`, `description`, `active`, `seq_padding_digits`, `created_at`, `modified_at`.

### POST /admin/name-templates
Create a new name template.

**Requires:** `config:edit` permission

**Request:** `{ entity_type, template, description?, active?, seq_padding_digits? }` — `seq_padding_digits` (int, default 1) controls zero-padding for `{SEQ}` (e.g. 3 → 001, 010, 100).

### PATCH /admin/name-templates/{template_id}
Update a name template.

**Requires:** `config:edit` permission

**Request:** `{ entity_type?, template?, description?, active?, seq_padding_digits? }`

### DELETE /admin/name-templates/{template_id}
Soft-delete a name template (sets active=false).

**Requires:** `config:edit` permission

### GET /admin/name-templates/preview
Preview a generated name without consuming a sequence value.

**Query Parameters:** `entity_type` (required), `client_id?`, `reference_date?` (YYYY-MM-DD)

**Response:** `{ preview: string }`

---

## Admin - Sequences (Name Template SEQ)

Set the starting value for an entity type's name sequence (used by `{SEQ}` in name templates).

### POST /admin/sequences/{entity_type}/start
Set the next value for the sequence `name_template_seq_{entity_type}`.

**Requires:** `config:edit` permission

**Path Parameters:**
- `entity_type` (required): One of `sample`, `project`, `batch`, `analysis`, `container`

**Request:**
```json
{
  "start_value": 100
}
```
- `start_value` (int, required, >= 1): The next `nextval()` for this sequence will return this value.

**Response:** `{ entity_type, start_value, message }`

**Example:** `POST /admin/sequences/sample/start` with `{ "start_value": 100 }` — next generated sample name using `{SEQ}` will use 100 (then 101, 102, …).

