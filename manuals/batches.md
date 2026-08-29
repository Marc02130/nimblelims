# Batches Documentation

## Overview

Batches in the LIMS system provide a way to group containers (and their samples) for processing, testing, and workflow management. Batches support cross-project grouping, automatic QC sample generation, container position tracking, and sample prioritization based on expiration and due dates.

Key features:
- **Cross-Project Batching**: Combine containers from different projects into a single batch
- **QC Sample Generation**: Automatically create QC samples (blanks, spikes, duplicates) during batch creation
- **Container Position Tracking**: Track container positions within batches (e.g., A1, B2)
- **Atomic Transactions**: All batch creation operations (containers, QC samples) occur atomically
- **Batch Type Configuration**: Require QC samples for specific batch types
- **Sample Prioritization**: Sort and flag samples by expiration and due date priority

## Data Model

### Batch Model

**Table**: `batches`

**Standard Fields** (inherited from BaseModel):
- **id**: UUID primary key
- **name**: Batch name (auto-generated if not provided)
- **description**: Optional description
- **active**: Boolean flag for soft deletion
- **created_at**, **created_by**: Audit timestamp and user
- **modified_at**, **modified_by**: Audit timestamp and user

**Batch-Specific Fields**:
- **type**: FK to list_entries.id (batch type, optional)
- **status**: FK to list_entries.id (batch status, required)
- **start_date**: DateTime (optional)
- **end_date**: DateTime (optional)
- **custom_attributes**: JSONB for custom fields

**Relationships**:
- **containers**: Many-to-many with Container via batch_containers
- **batch_containers**: One-to-many with BatchContainer (junction table)
- **creator**: Many-to-one with User (created_by)
- **modifier**: Many-to-one with User (modified_by)

**Implementation**: `backend/models/batch.py::Batch`

### BatchContainer Model (Junction Table)

**Table**: `batch_containers`

**Fields**:
- **batch_id**: FK to batches.id (primary key, part of composite)
- **container_id**: FK to containers.id (primary key, part of composite)
- **position**: String (optional, e.g., "A1", "B2")
- **notes**: String (optional)

**Relationships**:
- **batch**: Many-to-one with Batch
- **container**: Many-to-one with Container

**Note**: This is a simple junction table without audit fields (created_by, modified_by).

**Implementation**: `backend/models/batch.py::BatchContainer`

### Prioritization Fields

**Table**: `samples` (additional fields for prioritization)
- **date_sampled**: DateTime (optional) - When sample was collected, used for expiration calculation

**Table**: `analyses` (additional fields for prioritization)
- **shelf_life**: Integer (optional) - Days until expiration; expiration = date_sampled + shelf_life

**Table**: `projects` (additional fields for prioritization)
- **due_date**: DateTime (optional) - Project-level turnaround; samples inherit if sample.due_date is null

**Indexes**:
- `idx_samples_date_sampled`: On samples.date_sampled (WHERE date_sampled IS NOT NULL)
- `idx_samples_prioritization`: Composite on (project_id, due_date, date_sampled) WHERE active=true
- `idx_analyses_shelf_life`: On analyses.shelf_life (WHERE shelf_life IS NOT NULL)
- `idx_projects_due_date`: On projects.due_date (WHERE due_date IS NOT NULL)

## Sample Prioritization

Sample prioritization helps laboratory personnel focus on the most urgent samples during batch creation. Samples are prioritized based on two key metrics:

### Priority Calculations

1. **Days Until Expiration**
   ```
   expiration_date = sample.date_sampled + analysis.shelf_life (in days)
   days_until_expiration = (expiration_date - now()).days
   ```
   - Negative values indicate expired samples
   - If `date_sampled` or `shelf_life` is null, expiration is not calculated (null)

2. **Days Until Due**
   ```
   effective_due_date = COALESCE(sample.due_date, project.due_date)
   days_until_due = (effective_due_date - now()).days
   ```
   - Sample's due_date takes precedence over project's due_date
   - Negative values indicate overdue samples
   - If both are null, due date is not calculated (null)

### Sorting Logic

Samples are sorted by priority using:
1. **Primary**: `days_until_expiration ASC NULLS LAST` (most urgent expiration first)
2. **Secondary**: `days_until_due ASC NULLS LAST` (earliest due date first)

This ensures:
- Expired samples appear first (negative days)
- Expiring soon samples appear next
- Samples without expiration data appear last
- Within same expiration tier, earliest due samples are prioritized

### Expiration Flags

Each eligible sample includes boolean flags:
- **is_expired**: `true` if `days_until_expiration < 0`
- **is_overdue**: `true` if `days_until_due < 0`

### Warning Messages

The system generates warnings for:
- **Expired Samples**: "Expired: Testing invalid" - Results from expired samples may not be valid
- **Expiring Soon** (≤3 days): "Expiring soon" - Sample should be tested immediately
- **Overdue Samples**: "Overdue" - Sample has passed its due date

### Frontend Display

The BatchFormEnhanced component displays prioritization in a DataGrid:
- **Columns**: Sample Name, Project, Days to Expiration, Days to Due, Analysis, Shelf Life, Warning
- **Visual Indicators**:
  - Expired rows: Red background with error icon
  - Urgent rows (≤3 days): Orange background with warning icon
  - Tooltips on priority cells with detailed status
- **Accessibility**: ARIA labels on sorted columns (e.g., "Sorted by expiration priority")

## Batch Status Lifecycle

Batches follow a status-based lifecycle using the `batch_status` list:

| Status | Description |
|--------|-------------|
| **Created** | Batch has been created, containers assigned |
| **In Process** | Batch is actively being processed/tested |
| **Completed** | All processing complete |

**Status Transitions**:
```
Created → In Process → Completed
```

**Note**: Status transitions are not enforced by the system; any status can be set at any time.

## Batch Types

Batch types are configured via the `batch_types` list. Common types include:

| Type | Description | QC Required |
|------|-------------|-------------|
| **Standard** | Regular batch processing | Optional |
| **QC Batch** | Quality control batch | Yes |
| **Rush** | Priority processing | Optional |

## API Endpoints

### GET /samples/eligible

Get eligible samples with prioritization for batch creation.

**Authentication**: Required (JWT token)

**Requires**: `sample:read` permission

**Query Parameters**:
- `test_ids` (optional, string): Comma-separated analysis UUIDs to filter by
- `project_id` (optional, UUID): Filter by specific project
- `include_expired` (optional, boolean, default=false): Include expired samples
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10, max=100): Page size

**Response**:
```json
{
  "samples": [
    {
      "id": "uuid",
      "name": "SAMPLE-001",
      "description": "Sample description",
      "due_date": "2026-01-25T00:00:00",
      "received_date": "2026-01-19T00:00:00",
      "date_sampled": "2026-01-15T00:00:00",
      "sample_type": "uuid",
      "status": "uuid",
      "matrix": "uuid",
      "project_id": "uuid",
      "days_until_expiration": 5,
      "days_until_due": 6,
      "is_expired": false,
      "is_overdue": false,
      "expiration_warning": null,
      "analysis_id": "uuid",
      "analysis_name": "EPA Method 8080",
      "shelf_life": 14,
      "project_name": "Project Alpha",
      "project_due_date": "2026-01-25T00:00:00",
      "effective_due_date": "2026-01-25T00:00:00"
    },
    {
      "id": "uuid",
      "name": "SAMPLE-002",
      "days_until_expiration": -2,
      "is_expired": true,
      "expiration_warning": "Expired: Testing may be invalid"
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5,
  "warnings": [
    "2 samples are expired and may produce invalid results",
    "3 samples are expiring within 3 days"
  ]
}
```

**Implementation**: `backend/app/routers/samples.py::get_eligible_samples()`

### GET /batches

List batches with filtering and pagination.

**Authentication**: Required (JWT token)

**Requires**: `batch:read` permission

**Query Parameters**:
- `type` (optional, UUID): Filter by batch type ID
- `status` (optional, UUID): Filter by status ID
- `page` (optional, int, default=1): Page number
- `size` (optional, int, default=10, max=100): Page size

**Response**:
```json
{
  "batches": [
    {
      "id": "uuid",
      "name": "BATCH-2026-001",
      "description": "January batch",
      "type": "uuid",
      "status": "uuid",
      "start_date": "2026-01-19T00:00:00",
      "end_date": null,
      "custom_attributes": {},
      "active": true,
      "created_at": "2026-01-19T10:00:00",
      "created_by": "uuid",
      "modified_at": "2026-01-19T10:00:00",
      "modified_by": "uuid",
      "containers": [
        {
          "batch_id": "uuid",
          "container_id": "uuid",
          "position": "A1",
          "notes": null
        }
      ]
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

**Implementation**: `backend/app/routers/batches.py::get_batches()`

### POST /batches

Create a new batch with cross-project support and QC sample generation.

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Request Body**:
```json
{
  "name": "BATCH-2026-001",
  "description": "January batch",
  "type": "uuid",
  "status": "uuid",
  "start_date": "2026-01-19T00:00:00",
  "end_date": null,
  "container_ids": ["uuid1", "uuid2", "uuid3"],
  "cross_project": true,
  "qc_additions": [
    {
      "qc_type": "uuid",
      "notes": "Method blank"
    },
    {
      "qc_type": "uuid",
      "notes": "Matrix spike"
    }
  ]
}
```

**Request Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Batch name (auto-generated if not provided) |
| `description` | string | No | Batch description |
| `type` | UUID | No | Batch type from list_entries |
| `status` | UUID | **Yes** | Batch status from list_entries |
| `start_date` | datetime | No | Batch start date |
| `end_date` | datetime | No | Batch end date |
| `container_ids` | UUID[] | No | Container IDs to add to batch |
| `cross_project` | boolean | No | Flag for cross-project batching (auto-detected) |
| `qc_additions` | QCAddition[] | No | QC samples to auto-create |

**QCAddition Schema**:
```json
{
  "qc_type": "uuid",
  "notes": "optional notes"
}
```

**Response**: BatchResponse (HTTP 201 Created)

**Error Responses**:
- **400 Bad Request**: 
  - Invalid status or type ID
  - QC required but not provided (for certain batch types)
  - No samples found in containers for QC inheritance
  - First sample missing required fields (sample_type, matrix, project_id)
- **403 Forbidden**: Insufficient permissions or cross-project access denied
- **500 Internal Server Error**: Database transaction failed

**Implementation**: `backend/app/routers/batches.py::create_batch()`

### POST /batches/with-containers

Alternative endpoint to create batch with container details (position, notes).

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Request Body**:
```json
{
  "name": "BATCH-2026-001",
  "description": "January batch",
  "type": "uuid",
  "status": "uuid",
  "start_date": "2026-01-19T00:00:00",
  "containers": [
    {
      "container_id": "uuid",
      "position": "A1",
      "notes": "First container"
    },
    {
      "container_id": "uuid",
      "position": "A2",
      "notes": null
    }
  ]
}
```

**Implementation**: `backend/app/routers/batches.py::create_batch_with_containers()`

### POST /batches/validate-compatibility

Validate container compatibility for cross-project batching without creating a batch. Also checks for expired samples.

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Request Body**:
```json
{
  "container_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response**:
```json
{
  "compatible": true,
  "projects": ["uuid1", "uuid2"],
  "shared_analyses": ["uuid1", "uuid2"],
  "incompatible_containers": [],
  "message": "Containers are compatible for cross-project batching",
  "warnings": [
    {
      "type": "expired_samples",
      "message": "Expired samples cannot be tested validly",
      "samples": [
        {
          "sample_id": "uuid",
          "sample_name": "SAMPLE-001",
          "days_expired": 5,
          "expiration_date": "2026-01-14T00:00:00"
        }
      ]
    },
    {
      "type": "expiring_soon",
      "message": "Some samples are expiring soon",
      "samples": [
        {
          "sample_id": "uuid",
          "sample_name": "SAMPLE-002",
          "days_until_expiration": 2,
          "expiration_date": "2026-01-21T00:00:00"
        }
      ]
    }
  ]
}
```

**Use Case**: Check if containers from different projects can be batched together before creating the batch. Also warns about expired or soon-to-expire samples.

**Implementation**: `backend/app/routers/batches.py::validate_compatibility()`

### GET /batches/{id}

Get batch details with containers.

**Authentication**: Required (JWT token)

**Requires**: `batch:read` permission

**Path Parameters**:
- `id` (UUID): Batch ID

**Response**: BatchResponse

**Error Responses**:
- **404 Not Found**: Batch not found

**Implementation**: `backend/app/routers/batches.py::get_batch()`

### PATCH /batches/{id}

Update batch details.

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Path Parameters**:
- `id` (UUID): Batch ID

**Request Body** (all fields optional):
```json
{
  "name": "Updated batch name",
  "description": "Updated description",
  "type": "uuid",
  "status": "uuid",
  "start_date": "2026-01-20T00:00:00",
  "end_date": "2026-01-25T00:00:00",
  "custom_attributes": {
    "priority": "high"
  }
}
```

**Response**: BatchResponse

**Error Responses**:
- **404 Not Found**: Batch not found
- **400 Bad Request**: Invalid status or type ID

**Implementation**: `backend/app/routers/batches.py::update_batch()`

### DELETE /batches/{id}

Soft-delete a batch (sets active=false).

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Path Parameters**:
- `id` (UUID): Batch ID

**Response**: HTTP 204 No Content

**Error Responses**:
- **404 Not Found**: Batch not found

**Implementation**: `backend/app/routers/batches.py::delete_batch()`

### POST /batches/{id}/containers

Add container to existing batch.

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Path Parameters**:
- `id` (UUID): Batch ID

**Request Body**:
```json
{
  "container_id": "uuid",
  "position": "B1",
  "notes": "Added later"
}
```

**Response**: BatchContainerResponse (HTTP 201 Created)

**Error Responses**:
- **404 Not Found**: Batch or container not found
- **400 Bad Request**: Container already in batch

**Implementation**: `backend/app/routers/batches.py::add_container_to_batch()`

### DELETE /batches/{batch_id}/containers/{container_id}

Remove container from batch.

**Authentication**: Required (JWT token)

**Requires**: `batch:manage` permission

**Path Parameters**:
- `batch_id` (UUID): Batch ID
- `container_id` (UUID): Container ID

**Response**: HTTP 204 No Content

**Error Responses**:
- **404 Not Found**: Batch-container relationship not found

**Implementation**: `backend/app/routers/batches.py::remove_container_from_batch()`

## QC Sample Generation (US-27)

When creating a batch, you can automatically generate QC samples. This feature:

1. **Inherits Properties**: QC samples inherit from the first sample in the batch:
   - `project_id`
   - `sample_type`
   - `matrix`
   - `temperature`
   - `due_date`

2. **Creates Container**: Each QC sample gets its own container

3. **Links to Batch**: QC containers are automatically added to the batch

4. **Sets Status**: QC samples are created with "Received" status

### QC Types

QC types are configured via the `qc_types` list:

| QC Type | Description |
|---------|-------------|
| **Blank** | Method blank (no analyte) |
| **Blank Spike** | Blank spiked with known concentration |
| **Duplicate** | Duplicate of sample for precision |
| **Matrix Spike** | Sample spiked with known concentration |
| **Sample** | Regular sample (default) |

### QC Creation Workflow

```
1. User creates batch with qc_additions
2. System validates QC types exist
3. System finds first sample in containers (for property inheritance)
4. For each QC addition:
   a. Create QC Sample (inherit properties, set qc_type)
   b. Create Container for QC sample
   c. Create Contents record (link sample to container)
   d. Create BatchContainer record (link container to batch)
5. Commit all changes atomically
```

### Example QC Request

```json
{
  "status": "uuid-of-created-status",
  "container_ids": ["uuid-of-container-with-samples"],
  "qc_additions": [
    {
      "qc_type": "uuid-of-blank",
      "notes": "Method blank"
    },
    {
      "qc_type": "uuid-of-matrix-spike",
      "notes": "Matrix spike at 100ppb"
    },
    {
      "qc_type": "uuid-of-duplicate",
      "notes": "Duplicate of sample 1"
    }
  ]
}
```

## Batch Name Auto-Generation

If no batch name is provided, the system generates one:

```
Format: BATCH-{YEAR}-{SEQUENCE}
Example: BATCH-2026-001
```

## Cross-Project Batching

Batches can contain containers from multiple projects. The system validates:

1. **Project Access**: User must have access to all projects
2. **Analysis Compatibility**: Containers should share common analyses
3. **QC Inheritance**: QC samples inherit from the first sample's project

### Compatibility Validation

Use `POST /batches/validate-compatibility` before creating cross-project batches:

```json
// Request
{
  "container_ids": ["container-from-project-a", "container-from-project-b"]
}

// Response
{
  "compatible": true,
  "projects": ["project-a-id", "project-b-id"],
  "shared_analyses": ["analysis-1", "analysis-2"],
  "incompatible_containers": [],
  "message": "Containers are compatible",
  "warnings": []
}
```

## Permissions

| Permission | Description | Roles |
|------------|-------------|-------|
| `batch:read` | View batches | All lab roles |
| `batch:manage` | Create, update, delete batches | Lab Technician, Lab Manager, Admin |

**Note**: `batch:manage` includes read access.

## Frontend Usage

### Batch Management Page

The Batches page (`/batches`) provides:

- **Batch List View**: All batches with filtering by status and type
- **Container Count**: Displays number of containers in each batch
- **Create Batch**: Multi-step form with sample prioritization, QC configuration
- **Edit Batch**: Update batch metadata and manage containers
- **View Batch Details**: Tabs for Containers, Results, and Details

### Batch Creation Steps (BatchFormEnhanced)

1. **Batch Details**: Name, description, type, status, start date
2. **Select Eligible Samples**: 
   - DataGrid with prioritization columns (days to expiration, days to due)
   - Default sort by expiration priority
   - Visual highlighting for expired/urgent samples
   - Container selection for cross-project batching
3. **QC Samples**: Add/configure QC samples with type selection
4. **Review & Create**: Summary of batch configuration before submission

### Prioritization Display Features

- **Red highlighting** for expired samples (`days_until_expiration < 0`)
- **Orange highlighting** for urgent samples (`days_until_expiration <= 3`)
- **Tooltips** with detailed expiration status
- **Warning alerts** for expired/expiring samples on validation
- **ARIA labels** for accessibility (e.g., "Sorted by expiration priority")

### Creating a Batch (Frontend Flow)

```typescript
// 1. Load lookup data
const [batchStatuses, setBatchStatuses] = useState([]);
const [batchTypes, setBatchTypes] = useState([]);

useEffect(() => {
  Promise.all([
    apiService.getListEntries('batch_status'),
    apiService.getListEntries('batch_types'),
  ]).then(([statuses, types]) => {
    setBatchStatuses(statuses);
    setBatchTypes(types);
  });
}, []);

// 2. Load eligible samples with prioritization
const loadEligibleSamples = async () => {
  const response = await apiService.getEligibleSamples({
    include_expired: false,
    size: 100,
  });
  setEligibleSamples(response.samples);
  setWarnings(response.warnings);
};

// 3. Validate compatibility (includes expiration checks)
const validateBatch = async () => {
  const result = await apiService.validateBatchCompatibility({
    container_ids: selectedContainers.map(c => c.id),
  });
  if (result.warnings) {
    // Display expiration warnings
    setCompatibilityWarnings(result.warnings);
  }
};

// 4. Create batch
const handleCreateBatch = async (formData) => {
  const batchData = {
    status: formData.status,
    type: formData.type,
    container_ids: formData.selectedContainers,
    qc_additions: formData.qcSamples,
  };
  
  const batch = await apiService.createBatch(batchData);
};
```

## Request/Response Schemas

### BatchCreate

```python
class BatchCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: UUID  # Required
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_attributes: Dict[str, Any] = {}
    container_ids: Optional[List[UUID]] = None
    cross_project: Optional[bool] = None
    qc_additions: Optional[List[QCAddition]] = None
```

### BatchUpdate

```python
class BatchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[UUID] = None
    status: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_attributes: Optional[Dict[str, Any]] = None
```

### BatchResponse

```python
class BatchResponse(BaseModel):
    id: UUID
    name: Optional[str]
    description: Optional[str]
    type: Optional[UUID]
    status: UUID
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    custom_attributes: Dict[str, Any]
    active: bool
    created_at: datetime
    created_by: UUID
    modified_at: datetime
    modified_by: UUID
    containers: Optional[List[BatchContainerResponse]]
```

### BatchContainerResponse

```python
class BatchContainerResponse(BaseModel):
    batch_id: UUID
    container_id: UUID
    position: Optional[str]
    notes: Optional[str]
```

### QCAddition

```python
class QCAddition(BaseModel):
    qc_type: UUID  # Required - ID from qc_types list
    notes: Optional[str] = None
```

### EligibleSampleResponse

```python
class EligibleSampleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    date_sampled: Optional[datetime] = None
    sample_type: UUID
    status: UUID
    matrix: UUID
    project_id: UUID
    qc_type: Optional[UUID] = None
    # Prioritization fields
    days_until_expiration: Optional[int] = None
    days_until_due: Optional[int] = None
    is_expired: bool = False
    is_overdue: bool = False
    expiration_warning: Optional[str] = None
    # Analysis context
    analysis_id: Optional[UUID] = None
    analysis_name: Optional[str] = None
    shelf_life: Optional[int] = None
    # Project context
    project_name: Optional[str] = None
    project_due_date: Optional[datetime] = None
    effective_due_date: Optional[datetime] = None
```

### EligibleSamplesResponse

```python
class EligibleSamplesResponse(BaseModel):
    samples: List[EligibleSampleResponse]
    total: int
    page: int
    size: int
    pages: int
    warnings: List[str] = []
```

**Implementation**: `backend/app/schemas/batch.py`, `backend/app/schemas/sample.py`

## Error Handling

### Common Errors

| Error | Status | Cause |
|-------|--------|-------|
| Invalid batch status ID | 400 | Status UUID doesn't exist or is inactive |
| Invalid batch type ID | 400 | Type UUID doesn't exist or is inactive |
| QC required but not provided | 400 | Batch type requires QC samples |
| No samples found for QC | 400 | Containers have no samples to inherit from |
| Container already in batch | 400 | Attempting to add duplicate container |
| Batch not found | 404 | Batch ID doesn't exist or is inactive |
| Permission denied | 403 | User lacks required permission |

## Transaction Atomicity

Batch creation is atomic - if any step fails, the entire operation is rolled back:

```python
try:
    db.add(batch)
    db.flush()
    
    # Add containers
    for container_id in container_ids:
        db.add(BatchContainer(...))
    
    # Create QC samples
    for qc in qc_additions:
        db.add(Sample(...))
        db.add(Container(...))
        db.add(Contents(...))
        db.add(BatchContainer(...))
    
    db.commit()
except Exception as e:
    db.rollback()
    raise HTTPException(500, f"Failed to create batch: {str(e)}")
```

This ensures:
- No orphaned records
- Consistent state
- Easy error recovery

## Related User Stories

- **US-11**: Create and Manage Batches (with prioritization)
- **US-26**: Cross-Project Batching
- **US-27**: QC Sample Auto-Creation

## Implementation Files

### Backend
- `backend/models/batch.py`: Batch and BatchContainer models
- `backend/models/sample.py`: Sample model with date_sampled field
- `backend/models/analysis.py`: Analysis model with shelf_life field
- `backend/models/project.py`: Project model with due_date field
- `backend/app/routers/batches.py`: Batch API endpoints (including validate-compatibility with expiration checks)
- `backend/app/routers/samples.py`: Samples API endpoints (including eligible endpoint)
- `backend/app/schemas/batch.py`: Batch request/response schemas
- `backend/app/schemas/sample.py`: Sample schemas including EligibleSampleResponse
- `backend/app/core/rbac.py`: Permission dependencies
- `backend/db/migrations/versions/0026_add_prioritization_fields.py`: Migration for prioritization columns

### Frontend
- `frontend/src/pages/BatchManagement.tsx`: Batch management page
- `frontend/src/components/batches/BatchManagement.tsx`: Batch management component
- `frontend/src/components/batches/BatchList.tsx`: Batch list view
- `frontend/src/components/batches/BatchForm.tsx`: Basic batch create/edit form
- `frontend/src/components/batches/BatchFormEnhanced.tsx`: Enhanced batch creation with prioritization and QC
- `frontend/src/components/batches/ContainerGrid.tsx`: Container management within batch
- `frontend/src/services/apiService.ts`: API service methods (getEligibleSamples, validateBatchCompatibility)
