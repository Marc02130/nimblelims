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

## Form Submit Flow (Single Sample Mode)

### Expected Flow:
1. User fills out form (Sample Details → Test Assignment → Review & Submit)
2. User clicks "Submit" button on Review step
3. `handleSubmit` function executes (line 486 in AccessioningForm.tsx)
4. **Step 1**: Create container via `POST /api/containers`
5. **Step 2**: Accession sample via `POST /api/samples/accession`
6. **Step 3**: Link sample to container via `POST /api/containers/{container_id}/contents`

### Actual Code Flow (lines 537-597):

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

// Step 3: Link sample to container
const contentData = {
  container_id: container.id,
  sample_id: sample.id,
};
await apiService.createContent(container.id, contentData);
// ENDPOINT: POST /api/containers/{container_id}/contents

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
- **Backend Route**: `backend/app/routers/samples.py:317` - `accession_sample()`
- **Expected Response**: `SampleResponse` with sample ID
- **What it does**:
  - Creates sample
  - Auto-creates project if `project_id` not provided
  - Creates tests based on `assigned_tests` or `battery_id`
  - Returns sample with ID

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
- **Backend Route**: `backend/app/routers/containers.py:393` - `add_sample_to_container()`
- **Expected Response**: `ContentsResponse`

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

## Recommendations

1. **Validate test assignment before submission**: Ensure at least one analysis or battery is selected
2. **Better error messages**: Display specific validation errors from backend
3. **Add rollback for containers**: If sample creation fails, delete the container that was created
4. **Use single transaction**: Consider using bulk accession endpoint which creates container, sample, and content in one transaction
5. **Validate all steps before committing**: Check that container, sample, and content can all be created before starting
6. **Better logging**: Log each step's success/failure to identify where the flow breaks
7. **Check database state**: Verify that required configuration data (status lists, status entries) exists
8. **Handle empty arrays properly**: Check if `assigned_tests` is empty and `battery_id` is missing, show error to user
