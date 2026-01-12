# Accessioning Form Submit Flow Analysis

## Problem Statement
- **No sample is created** when form is submitted
- **Containers are created** but have **no contents** (sample-container link is missing)
- **Tests are not associated** with samples that are accessioned

## Summary of Root Causes

### 1. Sample Not Created
- **Cause**: Likely failure in Step 2 (`POST /api/samples/accession`) - error may be caught but not properly displayed
- **Location**: `AccessioningForm.tsx:579` - `apiService.accessionSample(sampleData)`
- **Fix Needed**: Better error logging and validation to identify where the flow breaks

### 2. Containers Created with No Contents
- **Cause**: No rollback mechanism - if Step 2 (sample creation) or Step 3 (content linking) fails, the container from Step 1 remains orphaned
- **Location**: `AccessioningForm.tsx:555, 579, 587` - Three-step process with no cleanup on failure
- **Fix Needed**: 
  - Add container deletion/rollback if sample creation fails
  - OR: Create container and sample in a single transaction (use bulk accession endpoint)
  - OR: Validate all steps before committing any changes

## How Containers Are Associated with Samples

### Database Schema

The association between containers and samples is implemented using a **junction table** called `contents`:

```sql
CREATE TABLE contents (
    container_id UUID NOT NULL REFERENCES containers(id),
    sample_id UUID NOT NULL REFERENCES samples(id),
    concentration NUMERIC(15,6),
    concentration_units UUID REFERENCES units(id),
    amount NUMERIC(15,6),
    amount_units UUID REFERENCES units(id),
    PRIMARY KEY (container_id, sample_id)
);
```

**Key Points:**
- The `contents` table is a **many-to-many junction table** that links containers to samples
- **Composite Primary Key**: `(container_id, sample_id)` ensures a sample can only appear once per container
- **Multiple samples per container**: A container can contain multiple samples (pooled samples)
- **Sample-specific measurements**: Each contents record can store concentration and amount specific to that sample-container pair
- **No RLS on contents**: The `contents` table does NOT have Row-Level Security enabled, so all contents are visible to all users

### Data Model Relationships

**Container Model** (`backend/models/container.py`):
```python
class Container(BaseModel):
    # ... container fields ...
    contents = relationship("Contents", back_populates="container")
```

**Contents Model** (`backend/models/container.py`):
```python
class Contents(Base):
    __tablename__ = 'contents'
    container_id = Column(PostgresUUID(as_uuid=True), ForeignKey('containers.id'), primary_key=True)
    sample_id = Column(PostgresUUID(as_uuid=True), ForeignKey('samples.id'), primary_key=True)
    # ... other fields ...
    container = relationship("Container", back_populates="contents")
    sample = relationship("Sample", back_populates="contents")
```

**Sample Model** (`backend/models/sample.py`):
```python
class Sample(BaseModel):
    # ... sample fields ...
    contents = relationship("Contents", back_populates="sample")
```

### Association Process During Accessioning

The association happens in **three sequential API calls**:

#### Step 1: Create Container
- **Endpoint**: `POST /api/containers`
- **Location**: `frontend/src/pages/AccessioningForm.tsx:555-558`
- **Backend**: `backend/app/routers/containers.py:156` - `create_container()`
- **What it does**: Creates a container record with name, type, row, column
- **Returns**: `ContainerResponse` with container `id`

#### Step 2: Accession Sample
- **Endpoint**: `POST /api/samples/accession`
- **Location**: `frontend/src/pages/AccessioningForm.tsx:626`
- **Backend**: `backend/app/routers/samples.py:351` - `accession_sample()`
- **What it does**: 
  - Creates sample record
  - Auto-creates project if needed
  - Creates tests for the sample
  - Commits transaction
- **Returns**: `SampleResponse` with sample `id`

#### Step 3: Link Sample to Container (Create Contents)
- **Endpoint**: `POST /api/containers/{container_id}/contents`
- **Location**: `frontend/src/pages/AccessioningForm.tsx:642`
- **Backend**: `backend/app/routers/containers.py:433` - `add_sample_to_container()`
- **What it does**:
  1. Verifies container exists and is active
  2. Verifies sample exists and is active
  3. Checks if contents already exists (prevents duplicates)
  4. Creates `Contents` record with `container_id` and `sample_id`
  5. Commits to database
  6. Eagerly loads sample relationship
  7. Returns `ContentsResponse` with sample data included
- **Request Body**:
  ```json
  {
    "container_id": "uuid",
    "sample_id": "uuid"
  }
  ```
- **Returns**: `ContentsResponse` with sample relationship included

### Current Implementation Status

**✅ What Works:**
1. **Contents are being created**: Backend logs show successful creation (lines 432-433 in backend.logs)
2. **Database records exist**: `schema_data.sql` shows contents records (lines 271-274)
3. **API returns 200 OK**: Both frontend and backend logs confirm successful API calls

**❌ What Doesn't Work:**
1. **List endpoint doesn't include contents**: `GET /containers` returns `List[ContainerResponse]` which does NOT include contents
2. **Frontend expects contents in list**: `ContainerManagement.tsx:147` tries to access `row.contents?.length` but contents aren't in the response
3. **Contents only available in detail view**: `GET /containers/{container_id}` returns `ContainerWithContentsResponse` with contents, but this is only called when viewing a single container

### The Problem

**Root Cause**: The `GET /containers` list endpoint does not include contents in the response, so the UI cannot display which samples are in each container.

**Evidence**:
- `backend/app/routers/containers.py:114-153`: `get_containers()` returns `List[ContainerResponse]`
- `ContainerResponse` schema does NOT include contents field
- `ContainerWithContentsResponse` (which includes contents) is only used in `get_container()` single-item endpoint
- Frontend `ContainerManagement.tsx:147` expects `row.contents?.length` but gets `undefined`

**Impact**:
- Container list shows "0 Samples" for all containers even when they have contents
- Users cannot see which samples are in containers without clicking into each container
- The association exists in the database but is not visible in the UI

## Form Submit Flow (Single Sample Mode)

### Expected Flow:
1. User fills out form (Sample Details → Test Assignment → Review & Submit)
2. User clicks "Submit" button on Review step
3. `handleSubmit` function executes (line 486 in AccessioningForm.tsx)
4. **Step 1**: Create container via `POST /api/containers`
5. **Step 2**: Accession sample via `POST /api/samples/accession`
6. **Step 3**: Link sample to container via `POST /api/containers/{container_id}/contents`

### Actual Code Flow (lines 555-650):

```typescript
// Step 1: Create container
const containerData = {
  name: `${values.container_name}-${timestamp}`,  // Timestamp appended for uniqueness
  type_id: values.container_type_id,
  row: values.container_row || 1,
  column: values.container_column || 1,
};
const container = await apiService.createContainer(containerData);
// ENDPOINT: POST /api/containers
// Returns: ContainerResponse with container.id

// Step 2: Accession sample
const sampleData = {
  name: values.auto_generate_name ? undefined : values.name,
  description: values.description,
  due_date: values.due_date,
  received_date: values.received_date,
  sample_type: values.sample_type,
  matrix: values.matrix,
  temperature: values.temperature,
  anomalies: values.anomalies,
  client_id: values.client_id,
  client_project_id: values.client_project_id || undefined,
  qc_type: values.qc_type || undefined,
  assigned_tests: values.selected_analyses,
  battery_id: values.battery_id || undefined,
  custom_attributes: values.custom_attributes || {},
};
const sample = await apiService.accessionSample(sampleData);
// ENDPOINT: POST /api/samples/accession
// Returns: SampleResponse with sample.id

// Step 3: Link sample to container
const contentData = {
  container_id: container.id,
  sample_id: sample.id,
};
const contentResult = await apiService.createContent(container.id, contentData);
// ENDPOINT: POST /api/containers/{container_id}/contents
// Returns: ContentsResponse with sample relationship included

// Success handling
setSuccess('Sample accessioned successfully!');
setActiveStep(0);
```

## API Endpoints Used

### 1. Create Container
- **Endpoint**: `POST /api/containers`
- **Service Method**: `apiService.createContainer(containerData)`
- **Request Body**:
  ```json
  {
    "name": "container-name-timestamp",
    "type_id": "uuid",
    "row": 1,
    "column": 1
  }
  ```
- **Backend Route**: `backend/app/routers/containers.py:156` - `create_container()`
- **Expected Response**: `ContainerResponse` with container ID
- **Transaction**: Commits immediately, container exists even if later steps fail

### 2. Accession Sample
- **Endpoint**: `POST /api/samples/accession`
- **Service Method**: `apiService.accessionSample(sampleData)`
- **Request Body**:
  ```json
  {
    "name": "optional",
    "description": "string",
    "due_date": "YYYY-MM-DD",
    "received_date": "YYYY-MM-DD",
    "sample_type": "uuid",
    "matrix": "uuid",
    "temperature": 0,
    "anomalies": "string",
    "client_id": "uuid",
    "client_project_id": "uuid (optional)",
    "qc_type": "uuid (optional)",
    "assigned_tests": ["uuid"],
    "battery_id": "uuid (optional)",
    "custom_attributes": {}
  }
  ```
- **Backend Route**: `backend/app/routers/samples.py:351` - `accession_sample()`
- **Expected Response**: `SampleResponse` with sample ID
- **What it does**:
  - Validates client and project access
  - Auto-creates project if `project_id` not provided (fixes "local variable 'project' referenced before assignment" error)
  - Creates sample record
  - Creates tests based on `assigned_tests` or `battery_id`
  - Commits transaction
  - Returns sample with ID
- **Transaction**: Commits immediately, sample exists even if Step 3 fails

### 3. Create Contents (Link Sample to Container)
- **Endpoint**: `POST /api/containers/{container_id}/contents`
- **Service Method**: `apiService.createContent(containerId, contentData)`
- **Path Parameter**: `container_id` (UUID)
- **Request Body**:
  ```json
  {
    "container_id": "uuid",
    "sample_id": "uuid"
  }
  ```
- **Backend Route**: `backend/app/routers/containers.py:433` - `add_sample_to_container()`
- **What it does**:
  1. Verifies container exists and is active (404 if not found)
  2. Verifies sample exists and is active (404 if not found)
  3. Checks if contents already exists (400 if duplicate)
  4. Creates `Contents` record:
     ```python
     contents = Contents(
         container_id=container_id,
         sample_id=contents_data.sample_id,
         concentration=contents_data.concentration,  # Optional
         concentration_units=contents_data.concentration_units,  # Optional
         amount=contents_data.amount,  # Optional
         amount_units=contents_data.amount_units  # Optional
     )
     ```
  5. Commits to database
  6. Eagerly loads sample relationship using `joinedload(Contents.sample)`
  7. Builds response with sample data included
  8. Returns `ContentsResponse` with sample relationship
- **Expected Response**: `ContentsResponse` with sample data:
  ```json
  {
    "container_id": "uuid",
    "sample_id": "uuid",
    "concentration": null,
    "concentration_units": null,
    "amount": null,
    "amount_units": null,
    "sample": {
      "id": "uuid",
      "name": "SAMPLE-2026-004",
      "description": "...",
      // ... full sample data
    }
  }
  ```
- **Transaction**: Commits immediately, contents record exists in database

## Retrieving Container-Sample Associations

### Single Container (With Contents)
- **Endpoint**: `GET /api/containers/{container_id}`
- **Backend**: `backend/app/routers/containers.py:236` - `get_container()`
- **Response Model**: `ContainerWithContentsResponse`
- **What it does**:
  1. Queries container by ID
  2. Queries all contents for that container with sample relationship eagerly loaded:
     ```python
     contents = db.query(Contents).options(
         joinedload(Contents.sample)
     ).filter(Contents.container_id == container_id).all()
     ```
  3. Builds response with sample data for each content
  4. Returns container with contents array
- **Response Structure**:
  ```json
  {
    "id": "uuid",
    "name": "container-name",
    // ... container fields ...
    "contents": [
      {
        "container_id": "uuid",
        "sample_id": "uuid",
        "sample": {
          "id": "uuid",
          "name": "SAMPLE-2026-004",
          // ... full sample data
        }
      }
    ]
  }
  ```

### Container List (Without Contents) ⚠️ **PROBLEM**
- **Endpoint**: `GET /api/containers`
- **Backend**: `backend/app/routers/containers.py:114` - `get_containers()`
- **Response Model**: `List[ContainerResponse]` (does NOT include contents)
- **What it does**:
  1. Queries all active containers
  2. Applies filters (type_id, parent_id, project_ids)
  3. Returns list of containers WITHOUT contents
- **Response Structure**:
  ```json
  [
    {
      "id": "uuid",
      "name": "container-name",
      // ... container fields ...
      // NO "contents" field!
    }
  ]
  ```
- **Problem**: Frontend expects `contents` array but it's not in the response

### Container Contents (Pagination)
- **Endpoint**: `GET /api/containers/{container_id}/contents?page=1&size=10`
- **Backend**: `backend/app/routers/containers.py:352` - `get_container_contents()`
- **Response Model**: `ContentsListResponse`
- **What it does**:
  1. Verifies container exists
  2. Queries contents with pagination and sample relationship eagerly loaded
  3. Returns paginated list of contents with sample data
- **Use Case**: For containers with many samples, get contents in pages

## Identified Problems

### Problem 1: Sample Not Created
**Possible Causes**:
1. **Error in Step 2** (`accessionSample`): The `POST /api/samples/accession` call fails silently or throws an error that's caught but not properly handled
2. **Error in Step 1** (`createContainer`): If container creation fails, the flow stops, but error might not be visible
3. **Transaction rollback**: If any step fails, previous steps might be rolled back (but containers are created in separate transaction)

**Check**: Look at browser console for errors during submission. Check backend logs for failed requests.

### Problem 2: Containers Created with No Contents
**Possible Causes**:
1. **Step 2 fails** (sample accession fails): Container is created, but sample is not, so Step 3 (createContent) never executes
2. **Step 3 fails** (createContent fails): Sample is created, container is created, but linking fails silently
3. **Error handling**: If Step 2 or Step 3 throws an error, the catch block (line 598) executes, but container already exists

**Root Cause**: **No rollback mechanism for containers**. If sample accession fails after container creation, the container remains orphaned.

### Problem 3: Contents Not Visible in Container List ⚠️ **CURRENT ISSUE**
**Root Cause**: The `GET /containers` endpoint returns `List[ContainerResponse]` which does NOT include the `contents` field.

**Evidence**:
- `backend/app/routers/containers.py:152`: Returns `[ContainerResponse.model_validate(container) for container in containers]`
- `ContainerResponse` schema (`backend/app/schemas/container.py:93`) does NOT have a `contents` field
- Only `ContainerWithContentsResponse` (used in `get_container()`) includes contents
- Frontend `ContainerManagement.tsx:147` tries to access `row.contents?.length` but gets `undefined`

**Impact**:
- Container list always shows "0 Samples" even when containers have contents
- Users cannot see which samples are in containers without clicking into each container
- The association exists in the database (verified in `schema_data.sql`) but is not visible in the UI

**Solution Options**:
1. **Option A**: Modify `GET /containers` to return `List[ContainerWithContentsResponse]` (include contents in list)
   - Pros: Frontend gets all data in one call
   - Cons: May be slow for containers with many samples, increases response size
2. **Option B**: Add a separate endpoint to get contents counts: `GET /containers?include_counts=true`
   - Pros: Lightweight, only returns counts not full sample data
   - Cons: Requires additional API call or query parameter
3. **Option C**: Frontend fetches contents separately for each container
   - Pros: No backend changes needed
   - Cons: N+1 query problem, many API calls
4. **Option D**: Add `contents_count` field to `ContainerResponse` (computed field, not relationship)
   - Pros: Lightweight, shows count without full contents
   - Cons: Still doesn't show which samples are in container

**Recommended Solution**: **Option A** - Include contents in list response, but limit to essential fields to keep response size manageable.

## Error Handling Flow

```typescript
try {
  // Step 1: Create container
  const container = await apiService.createContainer(containerData);
  
  // Step 2: Accession sample
  const sample = await apiService.accessionSample(sampleData);
  
  // Step 3: Link sample to container
  await apiService.createContent(container.id, contentData);
  
  // Success
  setSuccess('Sample accessioned successfully!');
  setActiveStep(0);
} catch (err) {
  // Error handling
  setError(errorMessage);
  // PROBLEM: Container already created, but no cleanup!
}
```

## Why Tests Are Not Associated with Samples

### Expected Behavior
When a sample is accessioned via `POST /api/samples/accession`, the backend should:
1. Create the sample (line 491-505 in `samples.py`)
2. Call `_create_tests_for_sample()` helper function (line 532-539)
3. This function creates Test records linked to the sample via `sample_id`

### How Tests Are Created
The `_create_tests_for_sample()` function (lines 29-103 in `samples.py`) creates tests in two ways:

1. **If `battery_id` is provided**:
   - Queries the TestBattery to get all analyses in the battery
   - Creates a Test record for each analysis in the battery
   - Each test has `sample_id` set to the sample's ID

2. **If `assigned_tests` array is provided**:
   - Creates a Test record for each analysis ID in the array
   - Checks if test already exists (from battery) to avoid duplicates
   - Each test has `sample_id` set to the sample's ID

### Why Tests Might Not Be Created

**Problem 1: Empty `assigned_tests` Array**
- **Location**: Frontend sends `assigned_tests: values.selected_analyses` (line 570 in AccessioningForm.tsx)
- **Issue**: If `values.selected_analyses` is an empty array `[]`, the condition `if assigned_tests:` (line 83) evaluates to `False` (empty array is falsy in Python)
- **Result**: No tests are created if user doesn't select any analyses AND doesn't select a battery

**Problem 2: No Battery Selected**
- **Location**: Frontend sends `battery_id: values.battery_id || undefined` (line 571)
- **Issue**: If `values.battery_id` is empty string `""`, it becomes `undefined`
- **Result**: Battery path is skipped, relies on `assigned_tests` array

**Problem 3: Transaction Rollback**
- **Location**: If any error occurs after `_create_tests_for_sample()` is called but before `db.commit()` (line 541)
- **Issue**: The entire transaction is rolled back, including tests that were created
- **Result**: Sample creation fails, tests are never committed

**Problem 4: Silent Failure in Test Creation**
- **Location**: `_create_tests_for_sample()` doesn't return anything, just calls `db.add(test)`
- **Issue**: If test creation fails (e.g., invalid `analysis_id`), the error might not be caught until commit
- **Result**: Tests fail to create but error might be generic "Internal server error"

**Problem 5: Missing Required Data**
- **Location**: Test creation requires `in_process_status_id` (line 537)
- **Issue**: If "In Process" status doesn't exist in the database, test creation fails
- **Result**: Tests are not created, but sample might still be created (depending on when error occurs)

## Why Samples Are Not Created

### Expected Behavior
Frontend calls `POST /api/samples/accession` which should:
1. Validate client and project
2. Create sample record
3. Create tests
4. Commit transaction
5. Return sample with ID

### Why Samples Might Not Be Created

**Problem 1: Validation Failures Before Sample Creation**
- **Location**: Multiple validation steps before sample creation (lines 339-457)
- **Possible Failures**:
  - Client not found or inaccessible (line 340-345)
  - Client project validation fails (line 348-367)
  - Project status list not found (line 376-382)
  - Project status "Active" not found (line 384-394)
  - Sample status list not found (line 460-466)
  - Sample status "Received" not found (line 468-478)
  - Test status list not found (line 511-517)
  - Test status "In Process" not found (line 519-529)
- **Result**: HTTP 400/403 error returned, sample never created

**Problem 2: Transaction Rollback on Error**
- **Location**: Exception handler (lines 551-560)
- **Issue**: If ANY error occurs during the process, `db.rollback()` is called
- **Result**: Sample is rolled back, not committed to database

**Problem 3: Name Generation Failure**
- **Location**: `generate_name_for_sample()` call (line 483-488)
- **Issue**: If name generation fails and no fallback, sample creation might fail
- **Result**: Sample not created, error might be unclear

**Problem 4: Frontend Error Handling**
- **Location**: Frontend catch block (line 598 in AccessioningForm.tsx)
- **Issue**: If backend returns error, frontend catches it but might not display clearly
- **Result**: User sees generic error, doesn't know sample wasn't created

**Problem 5: Database Constraint Violations**
- **Location**: Sample creation (line 507 `db.add(sample)`)
- **Issue**: If sample name already exists (unique constraint) or foreign key invalid
- **Result**: Database error, transaction rolled back, sample not created

## Why Samples Are Not Put in Containers

### Expected Behavior
After sample is created, frontend should:
1. Call `POST /api/containers/{container_id}/contents` with `container_id` and `sample_id`
2. Backend creates Contents record linking sample to container

### Why Samples Might Not Be Put in Containers

**Problem 1: Sample Creation Fails**
- **Location**: Step 2 fails (line 579 in AccessioningForm.tsx)
- **Issue**: If `apiService.accessionSample()` throws error, Step 3 never executes
- **Result**: Container exists, but no sample to link, so Step 3 is skipped

**Problem 2: Content Creation Fails**
- **Location**: Step 3 (line 587 in AccessioningForm.tsx)
- **Possible Failures**:
  - Container not found (line 405-414 in containers.py)
  - Sample not found (line 418-427 in containers.py)
  - Contents already exists (line 430-439 in containers.py)
  - Database error during commit (line 452)
- **Result**: Sample exists, container exists, but no link between them

**Problem 3: Error Handling Doesn't Clean Up**
- **Location**: Frontend catch block (line 598)
- **Issue**: If Step 3 fails, error is caught but container and sample already exist
- **Result**: Orphaned container and sample with no link

**Problem 4: Wrong Container ID**
- **Location**: Frontend passes `container.id` to `createContent()` (line 587)
- **Issue**: If container creation succeeded but returned wrong ID, or ID is undefined
- **Result**: Content creation fails with 404 "Container not found"

**Problem 5: Sample ID Not Available**
- **Location**: Frontend uses `sample.id` from accession response (line 584)
- **Issue**: If sample creation succeeded but response doesn't include ID, or ID is undefined
- **Result**: Content creation fails with 404 "Sample not found"

**Problem 6: Race Condition**
- **Location**: Three separate API calls (container → sample → content)
- **Issue**: If sample is created but not yet visible in database (transaction not committed), content creation might fail
- **Result**: Sample exists but content creation fails

**Problem 7: Contents Not Included in List Response** ⚠️ **CURRENT ISSUE**
- **Location**: `GET /containers` endpoint returns containers without contents
- **Issue**: Frontend expects `contents` array but `ContainerResponse` doesn't include it
- **Result**: UI shows "0 Samples" even when containers have contents
- **Fix**: Modify `GET /containers` to include contents or add `contents_count` field

## Root Cause Summary

### Tests Not Created
1. **Empty `assigned_tests` array** - User didn't select analyses, no battery selected
2. **Test status missing** - "In Process" status doesn't exist in database
3. **Transaction rollback** - Error occurs after test creation but before commit
4. **Invalid analysis IDs** - Analysis IDs in `assigned_tests` don't exist

### Samples Not Created
1. **Validation failures** - Missing configuration data (status lists, status entries)
2. **Transaction rollback** - Any error causes rollback, sample not committed
3. **Name generation failure** - Can't generate unique sample name
4. **Database constraints** - Duplicate name or invalid foreign keys
5. **Frontend error handling** - Errors not properly displayed to user

### Samples Not in Containers
1. **Sample creation fails** - Step 2 fails, Step 3 never executes
2. **Content creation fails** - Container or sample not found, or already linked
3. **Wrong IDs** - Container ID or sample ID is wrong/undefined
4. **No rollback** - If content creation fails, container and sample remain orphaned
5. **Race condition** - Sample not yet committed when content creation is attempted
6. **Contents not in list response** - `GET /containers` doesn't include contents, so UI can't display them ⚠️ **CURRENT ISSUE**

## Current Status (Based on Logs)

### What's Working ✅
1. **Container creation**: `POST /containers` returns 200 OK (line 412 in backend.logs)
2. **Sample accession**: `POST /samples/accession` returns 200 OK (line 426 in backend.logs)
3. **Contents creation**: `POST /containers/{id}/contents` returns 200 OK (line 436 in backend.logs)
4. **Backend logging**: Shows "Creating contents" and "Successfully created contents" (lines 432-433)
5. **Database records**: `schema_data.sql` shows contents records exist (lines 271-274)

### What's Not Working ❌
1. **Container list doesn't show contents**: `GET /containers` returns containers without contents array
2. **UI shows "0 Samples"**: Frontend tries to access `row.contents?.length` but gets `undefined`
3. **Contents only visible in detail view**: Must click into container to see contents

## Recommendations

1. **Fix container list endpoint**: Modify `GET /containers` to include contents (or at least contents_count)
   - **Option A**: Return `List[ContainerWithContentsResponse]` with full contents
   - **Option B**: Add `contents_count` computed field to `ContainerResponse`
   - **Option C**: Add query parameter `?include_contents=true` to optionally include contents
2. **Validate test assignment before submission**: Ensure at least one analysis or battery is selected
3. **Better error messages**: Display specific validation errors from backend
4. **Add rollback for containers**: If sample creation fails, delete the container that was created
5. **Use single transaction**: Consider using bulk accession endpoint which creates container, sample, and content in one transaction
6. **Validate all steps before committing**: Check that container, sample, and content can all be created before starting
7. **Better logging**: Log each step's success/failure to identify where the flow breaks
8. **Check database state**: Verify that required configuration data (status lists, status entries) exists
9. **Handle empty arrays properly**: Check if `assigned_tests` is empty and `battery_id` is missing, show error to user

## Database Verification

To verify contents are being created, query the database:

```sql
-- Check all contents records
SELECT c.container_id, c.sample_id, s.name as sample_name, cont.name as container_name
FROM contents c
JOIN samples s ON c.sample_id = s.id
JOIN containers cont ON c.container_id = cont.id
WHERE s.active = true AND cont.active = true;

-- Check contents for a specific container
SELECT c.*, s.name as sample_name
FROM contents c
JOIN samples s ON c.sample_id = s.id
WHERE c.container_id = 'bc3fdae6-f2c4-40f0-ace9-6ff82ab975d0';

-- Count samples per container
SELECT cont.id, cont.name, COUNT(c.sample_id) as sample_count
FROM containers cont
LEFT JOIN contents c ON cont.id = c.container_id
WHERE cont.active = true
GROUP BY cont.id, cont.name;
```

Based on `schema_data.sql`, the following contents records exist:
- Container `1477fa9b-d946-4ffc-a084-d9728774def9` → Sample `913ec796-f56c-44da-9b81-c6bee5275cc3`
- Container `b5479921-83af-49e4-9ca4-efea13d85a27` → Sample `5d38f989-a658-4ece-956b-43b089e3adff`
- Container `5461535c-b6c5-4810-b8c5-c524f7dccffe` → Sample `e003579c-0126-4dda-b0ad-325447f5e782`
- Container `bc3fdae6-f2c4-40f0-ace9-6ff82ab975d0` → Sample `cd9fa678-53ce-4311-a327-b7d5835270f3`

**Conclusion**: The contents records ARE being created successfully. The issue is that the `GET /containers` list endpoint doesn't return them, so the UI cannot display the associations.
