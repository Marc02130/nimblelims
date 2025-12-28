# Technical Details: Accessioning Through Reporting

## Overview

This document provides technical implementation details for the accessioning through reporting workflow, including API endpoints, data models, schemas, validation logic, and backend processing.

## Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 15+ with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Authorization**: RBAC with permission-based access control
- **Validation**: Pydantic schemas with custom validators

### Key Components
- **Routers**: FastAPI route handlers in `backend/app/routers/`
- **Models**: SQLAlchemy ORM models in `backend/models/`
- **Schemas**: Pydantic models in `backend/app/schemas/`
- **Security**: RBAC decorators in `backend/app/core/rbac.py`

---

## API Endpoints

### Sample Accessioning

#### POST `/samples/accession`
**Purpose**: Accession a new sample with test assignment.

**Request Schema**: `SampleAccessioningRequest`
```python
{
    "name": str,                    # Required, 1-255 chars, unique
    "description": Optional[str],
    "due_date": datetime,           # Required
    "received_date": datetime,      # Required
    "sample_type": UUID,            # Required, FK to list_entries
    "matrix": UUID,                 # Required, FK to list_entries
    "temperature": Optional[float],  # Validated: -273.15 to 1000
    "project_id": UUID,             # Required
    "client_project_id": Optional[UUID],  # Optional: Client project for grouping
    "qc_type": Optional[UUID],      # FK to list_entries
    "anomalies": Optional[str],
    "double_entry_required": bool,   # Default: False
    "assigned_tests": List[UUID],    # List of analysis IDs (optional)
    "battery_id": Optional[UUID]    # Optional: Test battery ID
}
```

**Response**: `SampleResponse` with created sample data

**Implementation**: `backend/app/routers/samples.py::accession_sample()`

**Processing Steps**:
1. **Access Control Check**
   - Verifies user has `sample:create` permission via `require_sample_create` dependency
   - Checks project access via `project_users` junction table
   - Administrators bypass project checks

2. **Client Project Validation** (if provided)
   - Verifies `client_project_id` exists and is active
   - Validates client project belongs to same client as the project
   - Links project to client project if valid

3. **Status Assignment**
   - Queries `list_entries` for "Received" status (list_id: "sample_status")
   - Raises 400 if status not found

4. **Sample Creation**
   - Creates `Sample` record with all provided data
   - Sets audit fields (`created_by`, `modified_by` to current user)
   - Uses `db.flush()` to get sample ID before committing

5. **Test Assignment**
   - **If `battery_id` provided**:
     - Verifies battery exists and is active
     - Queries `battery_analyses` ordered by `sequence`
     - Creates `Test` record for each analysis in battery
     - Sets `battery_id` on each test
   - **If `assigned_tests` provided**:
     - Checks if test already exists (from battery assignment)
     - Creates `Test` record for each analysis not already assigned
     - Sets `battery_id` to None for individual assignments
   - All tests created with "In Process" status

6. **Transaction Commit**
   - Commits all changes in single transaction
   - Returns sample with created tests

**Note**: This endpoint does NOT create containers. The frontend creates containers separately via `/containers` and links them via `/contents`. This allows for more granular error handling and step-by-step progress.

**Error Handling**:
- 400: Invalid data, missing status, battery not found, invalid client project
- 403: Insufficient project permissions
- 500: Database errors

---

#### POST `/samples/bulk-accession`
**Purpose**: Bulk accession multiple samples with common fields and unique per-sample data.

**Request Schema**: `BulkSampleAccessioningRequest`
```python
{
    # Common fields (applied to all samples)
    "due_date": datetime,           # Required
    "received_date": datetime,      # Required
    "sample_type": UUID,            # Required
    "matrix": UUID,                 # Required
    "project_id": UUID,             # Required
    "client_project_id": Optional[UUID],
    "container_type_id": UUID,      # Required
    "qc_type": Optional[UUID],
    "battery_id": Optional[UUID],
    "assigned_tests": Optional[List[UUID]],
    
    # Auto-naming (if sample names not provided)
    "auto_name_prefix": Optional[str],
    "auto_name_start": Optional[int],  # Default: 1
    
    # Unique fields per sample
    "uniques": List[{
        "name": Optional[str],           # Required if auto_name_prefix not provided
        "client_sample_id": Optional[str],
        "container_name": str,           # Required, unique
        "temperature": Optional[float],
        "description": Optional[str],
        "anomalies": Optional[str]
    }]
}
```

**Response**: `List[SampleResponse]`

**Implementation**: `backend/app/routers/samples.py::bulk_accession_samples()`

**Processing Steps**:
1. **Access Control**
   - Verifies user has `sample:create` permission
   - Checks project access

2. **Validation**
   - Validates container type exists
   - Validates client project (if provided)
   - Validates unique names, container names, and client_sample_ids (no duplicates)
   - Generates sample names if `auto_name_prefix` provided

3. **Atomic Creation** (single transaction)
   - For each unique entry:
     - Creates sample with common + unique fields
     - Creates container instance
     - Links sample to container via `Contents` junction
     - Creates tests (battery and/or individual analyses)
   - Links project to client project (if provided, once)

4. **Transaction Commit**
   - Commits all samples, containers, contents, and tests atomically
   - Rolls back on any error

**Error Handling**:
- 400: Duplicate names/containers, invalid container type, missing required fields
- 403: Insufficient project permissions
- 500: Database errors (transaction rolled back)

---

### Container Management

#### POST `/containers`
**Purpose**: Create container instance dynamically during accessioning.

**Request Schema**: `ContainerCreate`
```python
{
    "name": str,                    # Required, unique
    "type_id": UUID,                # Required, FK to container_types
    "row": int,                     # Default: 1
    "column": int,                  # Default: 1
    "concentration": Optional[float],
    "concentration_units": Optional[UUID],  # FK to units
    "amount": Optional[float],
    "amount_units": Optional[UUID],  # FK to units
    "parent_container_id": Optional[UUID]
}
```

**Response**: `ContainerResponse`

**Implementation**: `backend/app/routers/containers.py::create_container()`

**Processing Steps**:
1. Verify container type exists and is active
2. Validate unique container name
3. Create container record
4. Return container with type details

---

#### POST `/contents`
**Purpose**: Link sample to container with concentration/amount.

**Request Schema**: `ContentCreate`
```python
{
    "container_id": UUID,           # Required
    "sample_id": UUID,              # Required
    "concentration": Optional[float],
    "concentration_units": Optional[UUID],
    "amount": Optional[float],
    "amount_units": Optional[UUID]
}
```

**Response**: `ContentResponse`

**Implementation**: `backend/app/routers/containers.py::create_content()`

**Processing Steps**:
1. Verify container and sample exist
2. Check for existing content (unique constraint)
3. Create content junction record
4. Return content record

---

### Test Assignment

#### POST `/tests/assign`
**Purpose**: Assign individual test to sample after accessioning.

**Request Schema**: `TestAssignmentRequest`
```python
{
    "sample_id": UUID,              # Required
    "analysis_id": UUID,            # Required
    "test_date": Optional[datetime],
    "technician_id": Optional[UUID]
}
```

**Response**: `TestResponse`

**Implementation**: `backend/app/routers/tests.py::assign_test_to_sample()`

**Processing Steps**:
1. Verify sample exists and user has access
2. Verify analysis exists and is active
3. Get "In Process" status from `list_entries`
4. Create test record with status "In Process"
5. Return test record

---

### Batch Management

#### POST `/batches`
**Purpose**: Create new batch with cross-project support and QC sample generation.

**Request Schema**: `BatchCreate`
```python
{
    "name": str,                    # Required
    "description": Optional[str],
    "type": Optional[UUID],        # FK to list_entries
    "status": UUID,                 # Required, FK to list_entries
    "start_date": Optional[datetime],
    "end_date": Optional[datetime],
    "container_ids": Optional[List[UUID]],  # Containers to add to batch
    "cross_project": Optional[bool],  # Auto-detected if container_ids from multiple projects
    "divergent_analyses": Optional[List[UUID]],  # Future: analyses requiring sub-batches
    "qc_additions": Optional[List[{  # US-27: QC samples to auto-generate
        "qc_type": UUID,            # Required, FK to list_entries
        "notes": Optional[str]
    }]]
}
```

**Response**: `BatchResponse` with containers

**Implementation**: `backend/app/routers/batches.py::create_batch()`

**Processing Steps**:
1. **Cross-Project Detection** (if `container_ids` provided)
   - Auto-detects if containers are from multiple projects
   - Validates all containers exist and are active

2. **RLS Access Check** (US-26)
   - Gets all projects for samples in containers
   - Uses `has_project_access()` SQL function to check access for all projects
   - Returns 403 if user lacks access to any project

3. **Compatibility Validation** (US-26)
   - Gets all tests for samples in containers
   - Groups tests by sample to find common analyses
   - Validates samples share at least one common analysis
   - Returns 400 with details if incompatible (projects, analyses, suggestion)

4. **QC Requirement Check** (US-27)
   - Checks if batch type requires QC (via `REQUIRE_QC_FOR_BATCH_TYPES` env var)
   - Validates QC additions provided if required

5. **Batch Creation**
   - Creates batch record
   - Uses `db.flush()` to get batch ID

6. **Container Addition**
   - Adds containers to batch via `BatchContainer` junction

7. **QC Sample Generation** (US-27, if `qc_additions` provided)
   - Gets first sample from first container for property inheritance
   - For each QC addition:
     - Validates QC type exists and is active
     - Creates QC sample inheriting: project_id, sample_type, matrix, temperature, due_date
     - Sets `qc_type` field on sample
     - Creates container for QC sample (uses first container's type or default)
     - Links QC sample to container via `Contents` junction
     - Links QC container to batch via `BatchContainer` junction
   - All QC creation happens atomically within batch transaction

8. **Transaction Commit**
   - Commits batch, containers, QC samples, contents, and batch_containers
   - Rolls back on any error

**Error Handling**:
- 400: Invalid data, incompatible samples (no shared analyses), QC required but not provided, QC type invalid
- 403: Insufficient project permissions (cross-project access denied)
- 500: Database errors (transaction rolled back)

---

#### POST `/batches/validate-compatibility`
**Purpose**: Validate container compatibility for cross-project batching without creating batch.

**Request Schema**: `dict`
```python
{
    "container_ids": List[UUID]    # Required, at least 2 containers
}
```

**Response**: `dict`
```python
{
    "compatible": bool,
    "error": Optional[str],
    "details": Optional[{
        "projects": List[str],
        "common_analyses": List[str]  # If compatible
        # OR
        "analyses": List[str],        # If incompatible
        "suggestion": str
    }]
}
```

**Implementation**: `backend/app/routers/batches.py::validate_batch_compatibility()`

**Processing Steps**:
1. Validates at least 2 containers provided
2. Verifies all containers exist
3. Gets all samples from containers
4. Checks RLS access for all projects
5. Validates compatibility (shared analyses)
6. Returns compatibility status with details

---

#### POST `/batches/with-containers`
**Purpose**: Create batch with containers in single request (legacy endpoint).

**Request Schema**: `BatchCreateWithContainersRequest`
```python
{
    "name": str,
    "description": Optional[str],
    "type": Optional[UUID],
    "status": UUID,
    "start_date": Optional[datetime],
    "end_date": Optional[datetime],
    "containers": List[{
        "container_id": UUID,
        "position": Optional[str],
        "notes": Optional[str]
    }]
}
```

**Response**: `BatchResponse`

**Implementation**: `backend/app/routers/batches.py::create_batch_with_containers()`

**Processing Steps**:
1. Create batch record
2. Use `db.flush()` to get batch ID
3. For each container:
   - Verify container exists
   - Create `BatchContainer` junction record
4. Commit transaction
5. Return batch with containers

---

#### POST `/batches/{batch_id}/containers`
**Purpose**: Add container to existing batch.

**Request Schema**: `BatchContainerRequest`
```python
{
    "container_id": UUID,           # Required
    "position": Optional[str],
    "notes": Optional[str]
}
```

**Response**: `BatchContainerResponse`

**Implementation**: `backend/app/routers/batches.py::add_container_to_batch()`

---

### Results Entry

#### POST `/results/batch` (US-28: Batch Results Entry)
**Purpose**: Enter results for multiple tests/samples in a batch atomically.

**Request Schema**: `BatchResultsEntryRequestUS28`
```python
{
    "batch_id": UUID,               # Required
    "results": List[{
        "test_id": UUID,            # Required
        "analyte_results": List[{
            "analyte_id": UUID,      # Required
            "raw_result": Optional[str],
            "reported_result": Optional[str],
            "qualifiers": Optional[UUID],  # FK to list_entries
            "notes": Optional[str]
        }]
    }]
}
```

**Response**: `BatchResponse` with updated batch status

**Implementation**: `backend/app/routers/results.py::enter_batch_results_us28()`

**Processing Steps**:
1. **Access Control**
   - Verifies user has `result:enter` permission
   - Verifies user has `batch:read` permission
   - Fetches batch and validates it exists

2. **Batch Validation**
   - Gets all containers in batch via `BatchContainer` junction
   - Gets all samples from containers via `Contents` junction
   - Gets all tests for samples in batch
   - Validates all `test_id`s in request exist in batch

3. **Result Validation** (per test/analyte)
   - For each test result entry:
     - Gets `analysis_analytes` configuration for test's analysis
     - For each analyte result:
       - Validates required analytes have values
       - Validates data type (numeric vs text)
       - Validates range (low_value, high_value) for numeric analytes
       - Collects validation errors per test/analyte
   - If validation errors exist, rolls back and returns detailed errors

4. **Result Creation/Update**
   - For each validated result:
     - Checks if result already exists (update) or creates new
     - Sets `entry_date` to current timestamp
     - Sets `entered_by` to current user
     - Sets audit fields

5. **Test Status Update**
   - For each test, checks if all analytes have results
   - Updates test status to "Complete" when all analytes entered
   - Updates test `modified_by` and `modified_at`

6. **QC Validation**
   - Identifies QC samples in batch (samples with `qc_type` set)
   - Checks QC tests for failures:
     - Missing results for QC tests
     - Results outside expected ranges (future: configurable QC acceptance criteria)
   - If `FAIL_QC_BLOCKS_BATCH` env var is `true`, blocks submission on QC failures
   - If `false`, allows submission but includes QC failures in response

7. **Batch Status Update**
   - Checks if all tests in batch are complete
   - If all tests complete, updates batch status to "Completed"
   - Sets batch `end_date` to current timestamp

8. **Transaction Commit**
   - Commits all results, test statuses, and batch status in single transaction
   - Returns updated batch with containers

**Error Handling**:
- 400: Validation errors (detailed per test/analyte), batch has no containers/samples, tests not found in batch, QC failures (if blocking enabled)
- 403: Insufficient permissions
- 404: Batch not found
- 500: Database errors (transaction rolled back)

---

#### POST `/results/validate`
**Purpose**: Validate a result before entry.

**Request Schema**: `ResultValidationRequest`
```python
{
    "test_id": UUID,                # Required
    "analyte_id": UUID,             # Required
    "raw_result": Optional[str],
    "reported_result": str          # Required
}
```

**Response**: `ResultValidationResponse`
```python
{
    "is_valid": bool,
    "errors": List[str],
    "warnings": List[str],
    "significant_figures": Optional[int],
    "data_type": str,
    "high_value": Optional[float],
    "low_value": Optional[float]
}
```

**Implementation**: `backend/app/routers/results.py::validate_result()`

**Validation Logic**:
1. Get `analysis_analytes` record for test's analysis and analyte
2. **Data Type Validation**:
   - If `data_type == "numeric"`:
     - Verify `raw_result` is numeric (if provided)
     - Verify `reported_result` is numeric
3. **Range Validation**:
   - If `low_value` or `high_value` defined:
     - Check `raw_result` is within range
     - Add error if out of range
4. **Significant Figures**:
   - If `significant_figures` defined:
     - Check reported result doesn't exceed significant figures
     - Add warning (not error) if exceeded
5. **Required Field**:
   - If `is_required == True`:
     - Verify `reported_result` is not empty

---

### Results Review

#### PATCH `/tests/{test_id}/review`
**Purpose**: Review and approve test results.

**Request Schema**: `TestReviewRequest`
```python
{
    "review_date": datetime          # Required
}
```

**Response**: `TestResponse`

**Implementation**: `backend/app/routers/tests.py::review_test()`

**Processing Steps**:
1. **Access Control**
   - Verify test exists
   - Check user has `result:review` permission
   - Verify project access

2. **Status Update**
   - Get "Complete" status from `list_entries`
   - Update test status to "Complete"
   - Set `review_date` from request
   - Update audit fields

3. **Sample Status Check**
   - Get "Reviewed" status from `list_entries`
   - Query all tests for sample
   - Count incomplete tests
   - If all tests complete:
     - Update sample status to "Reviewed"
     - Update sample audit fields

4. **Commit**
   - Commit test and sample updates
   - Return updated test

**Error Handling**:
- 400: Status not found, test not ready
- 403: Insufficient permissions
- 404: Test not found

---

### Status Management

#### PATCH `/samples/{sample_id}/status`
**Purpose**: Update sample status (e.g., to "Reported").

**Request**: Query parameter `status_id: UUID`

**Response**: `SampleResponse`

**Implementation**: `backend/app/routers/samples.py::update_sample_status()`

**Processing Steps**:
1. Verify sample exists
2. Verify status exists in `list_entries`
3. Update sample status
4. Update audit fields
5. Return updated sample

---

#### PATCH `/tests/{test_id}/status`
**Purpose**: Update test status.

**Request Schema**: `TestStatusUpdateRequest`
```python
{
    "status": UUID,                 # Required
    "review_date": Optional[datetime],
    "test_date": Optional[datetime],
    "technician_id": Optional[UUID]
}
```

**Response**: `TestResponse`

**Implementation**: `backend/app/routers/tests.py::update_test_status()`

---

## Data Models

### Sample
```python
class Sample(BaseModel):
    id: UUID
    name: str  # Unique
    description: Optional[str]
    due_date: datetime
    received_date: datetime
    report_date: Optional[datetime]
    sample_type: UUID  # FK to list_entries
    status: UUID  # FK to list_entries
    matrix: UUID  # FK to list_entries
    temperature: Optional[float]
    parent_sample_id: Optional[UUID]  # FK to samples
    project_id: UUID  # FK to projects
    qc_type: Optional[UUID]  # FK to list_entries
    # Standard fields: active, created_at, created_by, modified_at, modified_by
```

### Container
```python
class Container(BaseModel):
    id: UUID
    name: str  # Unique
    row: int  # Default: 1
    column: int  # Default: 1
    concentration: Optional[float]
    concentration_units: Optional[UUID]  # FK to units
    amount: Optional[float]
    amount_units: Optional[UUID]  # FK to units
    type_id: UUID  # FK to container_types (required)
    parent_container_id: Optional[UUID]  # FK to containers
    # Standard fields
```

### Content (Junction)
```python
class Content(Base):
    container_id: UUID  # FK to containers
    sample_id: UUID  # FK to samples
    concentration: Optional[float]
    concentration_units: Optional[UUID]  # FK to units
    amount: Optional[float]
    amount_units: Optional[UUID]  # FK to units
    # Unique constraint: (container_id, sample_id)
```

### Test
```python
class Test(BaseModel):
    id: UUID
    name: str
    sample_id: UUID  # FK to samples
    analysis_id: UUID  # FK to analyses
    battery_id: Optional[UUID]  # FK to test_batteries
    status: UUID  # FK to list_entries
    review_date: Optional[datetime]
    test_date: Optional[datetime]
    technician_id: UUID  # FK to users
    # Standard fields
```

### Result
```python
class Result(BaseModel):
    id: UUID
    test_id: UUID  # FK to tests
    analyte_id: UUID  # FK to analytes
    raw_result: Optional[str]
    reported_result: str
    qualifiers: Optional[UUID]  # FK to list_entries
    calculated_result: Optional[str]
    entry_date: datetime
    entered_by: UUID  # FK to users
    # Standard fields
```

### Batch
```python
class Batch(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: Optional[UUID]  # FK to list_entries
    status: UUID  # FK to list_entries
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    # Standard fields
```

### BatchContainer (Junction)
```python
class BatchContainer(Base):
    batch_id: UUID  # FK to batches
    container_id: UUID  # FK to containers
    position: Optional[str]
    notes: Optional[str]
    # Composite primary key: (batch_id, container_id)
```

### AnalysisAnalyte (Junction)
```python
class AnalysisAnalyte(Base):
    analysis_id: UUID  # FK to analyses
    analyte_id: UUID  # FK to analytes
    data_type: str  # e.g., "numeric", "text", "list"
    list_id: Optional[UUID]  # FK to lists (for list-based analytes)
    high_value: Optional[float]
    low_value: Optional[float]
    significant_figures: Optional[int]
    calculation: Optional[str]
    reported_name: str
    display_order: int
    is_required: bool
    default_value: Optional[str]
    # Composite primary key: (analysis_id, analyte_id)
```

---

## Validation Logic

### Sample Accessioning Validation
- **Name**: Required, 1-255 chars, unique
- **Due Date**: Required, valid datetime
- **Received Date**: Required, valid datetime
- **Sample Type**: Required, must exist in `list_entries` with `list_id == "sample_types"`
- **Matrix**: Required, must exist in `list_entries` with `list_id == "matrix_types"`
- **Temperature**: Optional, if provided: -273.15 to 1000
- **Project ID**: Required, user must have access
- **Container Type**: Required, must exist and be active
- **Container Name**: Required, unique

### Results Validation
- **Required Analytes**: Must have value if `is_required == True`
- **Data Type**: Numeric analytes must be valid numbers
- **Range**: Values must be within `low_value` and `high_value` (if defined)
- **Significant Figures**: Warning if exceeded (not blocking)

### Status Validation
- Status must exist in `list_entries` with appropriate `list_id`
- Status must be active
- Status transitions validated by business logic

---

## Database Transactions

### Accessioning Transaction
```python
# Single transaction for:
1. Create sample
2. Create container
3. Create content
4. Create tests (multiple)
# All or nothing
```

### Results Entry Transaction
```python
# Single transaction for:
1. Create results (multiple)
2. Update test status
# All or nothing
```

### Review Transaction
```python
# Single transaction for:
1. Update test status
2. Update sample status (if all tests complete)
# All or nothing
```

---

## Security

### Permission Checks
- `sample:create`: Required for accessioning
- `test:assign`: Required for test assignment
- `result:enter`: Required for results entry
- `result:review`: Required for review
- `batch:manage`: Required for batch operations
- `batch:read`: Required for viewing batches

### Project Access Control
- Non-administrators: Must have access via `project_users` table
- Client users: Can only access their own client's projects
- Lab users: Can access projects they're assigned to

### Row-Level Security
- PostgreSQL RLS policies enforce data isolation
- Client users see only their own data
- Lab users see data for accessible projects

---

## Error Codes

### 400 Bad Request
- Invalid request data
- Missing required fields
- Validation failures
- Status not found
- Duplicate entries

### 403 Forbidden
- Insufficient permissions
- Project access denied
- Client data isolation violation

### 404 Not Found
- Sample not found
- Test not found
- Container not found
- Batch not found

### 500 Internal Server Error
- Database errors
- Unexpected exceptions

---

## Performance Considerations

### Indexes
- Foreign keys indexed for join performance
- Unique constraints on names/usernames
- Composite indexes on junction tables

### Query Optimization
- Eager loading for relationships (where needed)
- Pagination for list endpoints
- Batch operations for bulk updates

### Caching
- List entries cached (future enhancement)
- Analysis-analyte rules cached (future enhancement)

---

## Testing

### Unit Tests
- Test validation logic
- Test status transitions
- Test permission checks

### Integration Tests
- Test complete workflow end-to-end
- Test transaction rollback on errors
- Test access control enforcement

### Test Files
- `backend/tests/test_samples.py`: Sample accessioning tests
- `backend/tests/test_tests.py`: Test assignment tests
- `backend/tests/test_results.py`: Results entry tests
- `backend/tests/test_batches.py`: Batch management tests

