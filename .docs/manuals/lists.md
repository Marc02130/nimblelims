# Lists Documentation

## Overview

Lists in the LIMS system provide a configurable way to manage dropdown options, status values, and categorical data throughout the application. They enable administrators to customize the system without code changes, making the LIMS flexible for different laboratory workflows and requirements.

Lists consist of two components:
- **Lists**: Container definitions (e.g., "Sample Status", "Sample Types")
- **List Entries**: Individual options within a list (e.g., "Received", "Available for Testing")

This documentation covers list structure, standard lists, API usage, and integration throughout the system.

## Data Model

### List Model

**Table**: `lists`

**Standard Fields** (inherited from BaseModel):
- **id**: UUID primary key
- **name**: Unique list name (normalized to lowercase slug format)
- **description**: Optional description
- **active**: Boolean flag for soft deletion
- **created_at**, **created_by**: Audit timestamp and user
- **modified_at**, **modified_by**: Audit timestamp and user

**Relationships**:
- **entries**: One-to-many relationship with ListEntry

**Implementation**: `backend/models/list.py::List`

### List Entry Model

**Table**: `list_entries`

**Standard Fields** (inherited from BaseModel):
- **id**: UUID primary key
- **name**: Entry name (unique within list)
- **description**: Optional description
- **active**: Boolean flag for soft deletion
- **created_at**, **created_by**: Audit timestamp and user
- **modified_at**, **modified_by**: Audit timestamp and user

**List-Specific Fields**:
- **list_id**: FK to lists.id (required)

**Constraints**:
- Unique constraint on (list_id, name) - entries must have unique names within a list

**Relationships**:
- **list**: Many-to-one relationship with List

**Implementation**: `backend/models/list.py::ListEntry`

## List Name Normalization

List names are normalized to lowercase slug format for API access:

- **Display Name** → **API Name**
- "Sample Status" → `sample_status`
- "Test Status" → `test_status`
- "Sample Types" → `sample_types`
- "Matrix Types" → `matrix_types`
- "QC Types" → `qc_types`
- "Unit Types" → `unit_types`
- "Contact Types" → `contact_types`
- "Project Status" → `project_status`
- "Batch Status" → `batch_status`

**Migration**: `backend/db/migrations/versions/0007_normalize_list_names.py`

**Note**: When accessing lists via API, use the normalized slug format (e.g., `/lists/sample_status/entries`).

## Standard Lists

The system includes the following standard lists, populated during initial migration:

### 1. Sample Status (`sample_status`)

Tracks sample lifecycle status:

- **Received**: Sample received and accessioned
- **Available for Testing**: Sample ready for analysis
- **Testing Complete**: All tests completed
- **Reviewed**: Results reviewed by Lab Manager
- **Reported**: Results reported to client

**Usage**: 
- `samples.status` FK to list_entries.id
- Used in sample filtering and status updates

### 2. Test Status (`test_status`)

Tracks test/analysis progress:

- **In Process**: Test assigned and in progress
- **In Analysis**: Test currently being analyzed
- **Complete**: Test completed with results

**Usage**:
- `tests.status` FK to list_entries.id
- Used in test workflow management

### 3. Batch Status (`batch_status`)

Tracks batch processing status:

- **Created**: Batch created
- **In Process**: Batch being processed
- **Completed**: Batch completed

**Usage**:
- `batches.status` FK to list_entries.id
- Used in batch workflow management

### 4. Project Status (`project_status`)

Tracks project lifecycle:

- **Active**: Project is active
- **Completed**: Project completed
- **On Hold**: Project temporarily on hold

**Usage**:
- `projects.status` FK to list_entries.id
- Used in project management

### 5. Sample Types (`sample_types`)

Defines types of samples:

- **Blood**: Blood sample
- **Urine**: Urine sample
- **Tissue**: Tissue sample
- **Water**: Water sample

**Usage**:
- `samples.sample_type` FK to list_entries.id
- Used in sample accessioning and filtering

**Note**: Additional sample types can be added as needed.

### 6. Matrix Types (`matrix_types`)

Defines sample matrix categories:

- **Sludge**: Sludge matrix
- **Ground Water**: Ground Water matrix
- **Soil**: Soil matrix
- **Air**: Air matrix
- **Drinking Water**: Drinking Water matrix

**Usage**:
- `samples.matrix` FK to list_entries.id
- Used in sample classification

### 7. QC Types (`qc_types`)

Quality control sample classifications:

- **Sample**: Regular sample
- **Positive Control**: Positive control sample
- **Negative Control**: Negative control sample
- **Matrix Spike**: Matrix spike sample
- **Duplicate**: Duplicate sample
- **Blank**: Blank sample

**Usage**:
- `samples.qc_type` FK to list_entries.id (nullable)
- Used in QC workflow and batch validation

### 8. Unit Types (`unit_types`)

Defines unit categories for the units system:

- **concentration**: Concentration units (e.g., g/L, mg/L)
- **mass**: Mass units (e.g., g, mg, µg)
- **volume**: Volume units (e.g., L, mL, µL)
- **molar**: Molar units (e.g., mol/L, mmol/L)

**Usage**:
- `units.type` FK to list_entries.id
- Used to categorize units for filtering and validation

### 9. Contact Types (`contact_types`)

Contact method types:

- **Email**: Email address
- **Phone**: Phone number
- **Mobile**: Mobile phone number

**Usage**:
- `contact_methods.type` FK to list_entries.id
- Used in client contact management

**Initial Data**: `backend/db/migrations/versions/0004_initial_data.py`

## API Endpoints

### GET /lists

Get all active lists with their entries.

**Authentication**: Required (JWT token)

**Response**: Array of ListResponse
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

**Implementation**: `backend/app/routers/lists.py::get_lists()`

### POST /lists

Create a new list.

**Authentication**: Required (JWT token)

**Requires**: `config:edit` permission

**Request Body**:
```json
{
  "name": "custom_list",
  "description": "A custom list for specific workflow"
}
```

**Response**: ListResponse (HTTP 201 Created)
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

**Error Responses**:
- **400 Bad Request**: List with same name already exists
- **403 Forbidden**: User lacks `config:edit` permission

**Implementation**: `backend/app/routers/lists.py::create_list()`

### PATCH /lists/{list_id}

Update an existing list.

**Path Parameters**:
- `list_id` (UUID): The list ID

**Authentication**: Required (JWT token)

**Requires**: `config:edit` permission

**Request Body** (all fields optional):
```json
{
  "name": "updated_list_name",
  "description": "Updated description",
  "active": false
}
```

**Response**: ListResponse

**Error Responses**:
- **404 Not Found**: List not found
- **400 Bad Request**: List with new name already exists
- **403 Forbidden**: User lacks `config:edit` permission

**Implementation**: `backend/app/routers/lists.py::update_list()`

### DELETE /lists/{list_id}

Soft-delete a list (sets active=false).

**Path Parameters**:
- `list_id` (UUID): The list ID

**Authentication**: Required (JWT token)

**Requires**: `config:edit` permission

**Response**: HTTP 204 No Content

**Error Responses**:
- **404 Not Found**: List not found
- **403 Forbidden**: User lacks `config:edit` permission

**Note**: This is a soft delete. The list is marked as inactive but not removed from the database. Inactive lists are not returned by GET /lists.

**Implementation**: `backend/app/routers/lists.py::delete_list()`

### GET /lists/{list_name}/entries

Get all active entries for a specific list.

**Path Parameters**:
- `list_name` (string): Normalized list name (e.g., `sample_status`, `sample_types`)

**Authentication**: Required (JWT token)

**Response**: Array of ListEntryResponse
```json
[
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
```

**Error Responses**:
- **404 Not Found**: List name not found

**Implementation**: `backend/app/routers/lists.py::get_list_entries()`

## Request/Response Schemas

### ListEntryResponse

```python
{
    "id": UUID,
    "name": str,
    "description": Optional[str],
    "active": bool,
    "created_at": datetime,
    "modified_at": datetime,
    "list_id": UUID
}
```

### ListResponse

```python
{
    "id": UUID,
    "name": str,
    "description": Optional[str],
    "active": bool,
    "created_at": datetime,
    "modified_at": datetime,
    "entries": List[ListEntryResponse]
}
```

**Implementation**: `backend/app/schemas/list.py`

## Frontend Usage

### API Service

The frontend uses the `apiService` to fetch list entries:

```typescript
// Get entries for a specific list
const statuses = await apiService.getListEntries('sample_status');
const sampleTypes = await apiService.getListEntries('sample_types');
const matrices = await apiService.getListEntries('matrix_types');
const qcTypes = await apiService.getListEntries('qc_types');
```

**Implementation**: `frontend/src/services/apiService.ts::getListEntries()`

### Common Usage Patterns

#### Dropdown Population

Lists are commonly used to populate dropdown selects in forms:

```typescript
// In AccessioningForm
const [lookupData, setLookupData] = useState({
  sampleTypes: [],
  statuses: [],
  matrices: [],
  qcTypes: [],
  // ...
});

useEffect(() => {
  const loadLookupData = async () => {
    const [
      sampleTypes,
      statuses,
      matrices,
      qcTypes,
    ] = await Promise.all([
      apiService.getListEntries('sample_types'),
      apiService.getListEntries('sample_status'),
      apiService.getListEntries('matrix_types'),
      apiService.getListEntries('qc_types'),
    ]);
    
    setLookupData({
      sampleTypes,
      statuses,
      matrices,
      qcTypes,
    });
  };
  
  loadLookupData();
}, []);
```

#### Form Field Rendering

```typescript
<FormControl fullWidth required>
  <InputLabel>Sample Type</InputLabel>
  <Select
    value={values.sample_type}
    onChange={(e) => setFieldValue('sample_type', e.target.value)}
  >
    {lookupData.sampleTypes.map((type) => (
      <MenuItem key={type.id} value={type.id}>
        {type.name}
      </MenuItem>
    ))}
  </Select>
</FormControl>
```

**Example Components**:
- `frontend/src/pages/AccessioningForm.tsx`
- `frontend/src/components/accessioning/SampleDetailsStep.tsx`
- `frontend/src/components/batches/BatchForm.tsx`

## Usage Throughout System

### Samples

Lists are used extensively in sample management:

- **sample_type**: From `sample_types` list
- **status**: From `sample_status` list
- **matrix**: From `matrix_types` list
- **qc_type**: From `qc_types` list (optional)

**Example**: Sample accessioning requires selecting from these lists.

### Tests

- **status**: From `test_status` list

**Example**: Test status transitions (In Process → In Analysis → Complete).

### Batches

- **status**: From `batch_status` list
- **type**: From list (optional, configurable)

**Example**: Batch workflow (Created → In Process → Completed).

### Projects

- **status**: From `project_status` list

**Example**: Project lifecycle management.

### Units

- **type**: From `unit_types` list

**Example**: Categorizing units for filtering (concentration, mass, volume, molar).

### Analysis Analytes

- **list_id**: Optional FK to lists.id for categorical analytes

**Example**: Analytes with predefined value lists (e.g., "Positive/Negative", "Pass/Fail").

## Validation and Constraints

### List Constraints

- **Name**: Must be unique across all lists
- **Active**: Only active lists are returned by API

### List Entry Constraints

- **Name**: Must be unique within a list (list_id, name unique constraint)
- **List ID**: Must reference existing active list
- **Active**: Only active entries are returned by API

### Referential Integrity

- Foreign keys to list_entries.id are validated
- Soft deletion (active=false) prevents breaking references
- Inactive entries are filtered out in queries

## Permissions

### Read Access

- **No special permission required**: Lists are public lookup data
- All authenticated users can read lists and entries
- Used for dropdown population in forms

### Write Access

- **config:edit permission**: Required to create/update/delete lists and entries
- Typically restricted to Administrators
- Allows system customization without code changes

**Available Operations**:
- **Create List**: POST `/lists` - Create new lists
- **Update List**: PATCH `/lists/{list_id}` - Update list name, description, or active status
- **Delete List**: DELETE `/lists/{list_id}` - Soft-delete a list
- **Create Entry**: POST `/lists/{list_name}/entries` - Add entries to a list
- **Update Entry**: PATCH `/lists/{list_name}/entries/{entry_id}` - Update an entry
- **Delete Entry**: DELETE `/lists/{list_name}/entries/{entry_id}` - Soft-delete an entry

## Best Practices

### 1. Use Normalized Names

Always use normalized slug format when accessing lists via API:
```typescript
// ✅ Correct
apiService.getListEntries('sample_status');

// ❌ Incorrect
apiService.getListEntries('Sample Status');
```

### 2. Cache List Data

Cache list entries in component state or context to avoid repeated API calls:
```typescript
// Load once, reuse throughout component
const [statuses, setStatuses] = useState([]);

useEffect(() => {
  apiService.getListEntries('sample_status').then(setStatuses);
}, []);
```

### 3. Handle Loading States

Show loading indicators while fetching list data:
```typescript
const [loading, setLoading] = useState(true);

useEffect(() => {
  Promise.all([
    apiService.getListEntries('sample_types'),
    apiService.getListEntries('sample_status'),
  ]).then(([types, statuses]) => {
    setLookupData({ types, statuses });
    setLoading(false);
  });
}, []);
```

### 4. Validate List Existence

Handle cases where lists may not exist:
```typescript
try {
  const entries = await apiService.getListEntries('custom_list');
} catch (error) {
  if (error.response?.status === 404) {
    // List doesn't exist, handle gracefully
  }
}
```

## Data Relationships

Lists are referenced throughout the system via foreign keys:

```
List (1) ──< (many) ListEntry
ListEntry (1) ──< (many) Sample (sample_type, status, matrix, qc_type)
ListEntry (1) ──< (many) Test (status)
ListEntry (1) ──< (many) Batch (status, type)
ListEntry (1) ──< (many) Project (status)
ListEntry (1) ──< (many) Unit (type)
ListEntry (1) ──< (many) Analysis_Analyte (list_id, optional)
ListEntry (1) ──< (many) Contact_Method (type)
```

## Error Handling

### Common Errors

1. **404 Not Found**: 
   - List name doesn't exist
   - List name not normalized correctly
   - List is inactive

2. **400 Bad Request**:
   - Invalid list entry ID in foreign key
   - List entry doesn't exist
   - List entry is inactive

### Frontend Error Handling

```typescript
try {
  const entries = await apiService.getListEntries('sample_status');
} catch (error) {
  if (error.response?.status === 404) {
    console.error('List not found:', error.response.data.detail);
    // Show user-friendly message or use default values
  } else {
    console.error('Failed to load list entries:', error);
  }
}
```

## Related User Stories

- **US-15**: Configurable Lists
- **US-1**: Sample Accessioning (uses sample_types, sample_status, matrix_types, qc_types)
- **US-2**: Sample Status Management (uses sample_status)
- **US-7**: Assign Tests to Samples (uses test_status)
- **US-11**: Create and Manage Batches (uses batch_status)

## Implementation Files

### Backend
- `backend/models/list.py`: List and ListEntry models
- `backend/app/routers/lists.py`: List API endpoints
- `backend/app/schemas/list.py`: Request/response schemas
- `backend/db/migrations/versions/0004_initial_data.py`: Initial list data
- `backend/db/migrations/versions/0007_normalize_list_names.py`: List name normalization

### Frontend
- `frontend/src/services/apiService.ts`: API service for list endpoints
- `frontend/src/pages/AccessioningForm.tsx`: Example usage in forms
- `frontend/src/components/accessioning/SampleDetailsStep.tsx`: Dropdown population

## Frontend Lists Management

The Lists Management page (`/admin/lists`) provides a full administrative interface for managing lists and their entries.

### Features

- **DataGrid View**: All lists displayed in a searchable, sortable grid
- **Expandable Rows**: Click the expand arrow to view and manage entries for any list (works for both empty and populated lists)
- **Search**: Filter lists and entries by name or description
- **Create List**: Add new lists with name and description
- **Edit List**: Update list name, description, or active status
- **Delete List**: Soft-delete lists (with confirmation dialog)
- **Add Entries**: Expand any list and click "Add Entry" to add new entries
- **Edit Entries**: Update entry name, description, or active status
- **Delete Entries**: Soft-delete entries (with confirmation dialog)

### Access Control

- **View**: All authenticated users can view the Lists Management page
- **Edit**: Only users with `config:edit` permission can create, update, or delete lists and entries

**Implementation**: `frontend/src/pages/admin/ListsAdmin.tsx`

## Future Enhancements

Potential improvements:

1. **List Entry Ordering**: Display order for entries
2. **List Entry Hierarchies**: Nested/categorized entries
3. **List Validation Rules**: Custom validation for list entries
4. **List Dependencies**: Relationships between lists
5. **List Versioning**: Track changes to lists over time
6. **List Import/Export**: Bulk import/export of lists
7. **List Templates**: Pre-configured list sets for different lab types
8. **List Permissions**: Restrict list access by role
9. **List Caching**: Client-side caching for improved performance

