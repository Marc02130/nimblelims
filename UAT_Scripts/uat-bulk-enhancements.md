# UAT Scripts: Bulk Accessioning and Enhancements

## Overview

This document contains User Acceptance Testing (UAT) scripts for bulk accessioning and batch results entry enhancements in NimbleLIMS. These scripts validate bulk workflows as defined in:

- **User Stories**: US-24 (Bulk Sample Accessioning), US-28 (Batch Results Entry)
- **Post-MVP PRD**: Section 4.1 (Bulk Accessioning), Section 4.4 (Batch Results)
- **API Document**: `api_endpoints.md` (POST `/samples/bulk-accession`, POST `/results/batch`)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Variation B: Bulk Sample Accessioning, Variation B: Batch Results Entry)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Sample status list entries: "Received"
  - Test status list entries: "In Process"
  - At least one sample type, matrix, project, container type
  - At least one test battery (for test assignment)
  - At least one analysis (for test assignment)
  - At least one batch with samples and tests (for batch results entry)
- Test user accounts:
  - Lab Technician with `sample:create` and `result:enter` permissions

---

## Test Case 1: Bulk Accessioning - 5 Samples with Unique Fields

### Test Case ID
TC-BULK-UNIQUES-001

### Description
Accession 5 samples in bulk mode with common fields shared and unique fields per sample, verifying atomic creation and validation.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to at least one project |
| **Common Fields Valid** | Sample type, matrix, project, container type exist and are accessible |
| **No Duplicates** | Sample names and container names to be used do not exist in database |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads |
| 2 | **Enable Bulk Mode** | |
| 2.1 | Locate "Bulk Accessioning Mode" toggle switch | Switch visible at top of form |
| 2.2 | Toggle switch to ON | Form switches to bulk mode layout:<br>- Common fields section appears<br>- Unique fields table appears<br>- Auto-naming section appears |
| 3 | **Enter Common Fields** | |
| 3.1 | Enter Due Date: `2025-02-15` | Field accepts input |
| 3.2 | Enter Received Date: `2025-01-20` | Field accepts input |
| 3.3 | Select Sample Type: `Blood` | Type selected from dropdown |
| 3.4 | Select Matrix: `Whole Blood` | Matrix selected from dropdown |
| 3.5 | Select Project: `Project Alpha` | Project selected from dropdown |
| 3.6 | Select Container Type: `15mL Tube` | Container type selected from dropdown |
| 3.7 | Select Test Battery: `Standard Blood Panel` (optional) | Battery selected from dropdown |
| 4 | **Enter Unique Fields for 5 Samples** | |
| 4.1 | Verify unique fields table displays | Table shows columns: Name, Client Sample ID, Container Name, Temperature, Description, Anomalies |
| 4.2 | **Sample 1**: Enter Name: `BULK-001`, Container: `CONTAINER-BULK-001` | Fields accept input |
| 4.3 | **Sample 2**: Enter Name: `BULK-002`, Container: `CONTAINER-BULK-002` | Fields accept input |
| 4.4 | **Sample 3**: Enter Name: `BULK-003`, Container: `CONTAINER-BULK-003`, Temperature: `-20` | Fields accept input |
| 4.5 | **Sample 4**: Enter Name: `BULK-004`, Container: `CONTAINER-BULK-004`, Client Sample ID: `CLIENT-001` | Fields accept input |
| 4.6 | **Sample 5**: Enter Name: `BULK-005`, Container: `CONTAINER-BULK-005`, Description: `Priority sample` | Fields accept input |
| 4.7 | Click "Add Row" button (if needed) | Additional row added to table |
| 5 | **Review and Submit** | |
| 5.1 | Navigate to Review step (if stepper used) | Review step shows summary of all 5 samples |
| 5.2 | Verify all samples listed | All 5 samples visible with common and unique fields |
| 5.3 | Click "Submit" or "Accession Samples" button | Form submits, loading spinner shown |
| 6 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/samples/bulk-accession` called with:<br>```json
{
  "due_date": "2025-02-15T00:00:00Z",
  "received_date": "2025-01-20T00:00:00Z",
  "sample_type": "uuid-of-blood",
  "matrix": "uuid-of-whole-blood",
  "project_id": "uuid-of-project-alpha",
  "container_type_id": "uuid-of-15ml-tube",
  "battery_id": "uuid-of-standard-blood-panel",
  "assigned_tests": [],
  "uniques": [
    {
      "name": "BULK-001",
      "container_name": "CONTAINER-BULK-001"
    },
    {
      "name": "BULK-002",
      "container_name": "CONTAINER-BULK-002"
    },
    {
      "name": "BULK-003",
      "container_name": "CONTAINER-BULK-003",
      "temperature": -20
    },
    {
      "name": "BULK-004",
      "container_name": "CONTAINER-BULK-004",
      "client_sample_id": "CLIENT-001"
    },
    {
      "name": "BULK-005",
      "container_name": "CONTAINER-BULK-005",
      "description": "Priority sample"
    }
  ]
}
``` |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify user has `sample:create` permission<br>   - Check project access via `project_users` or RLS<br>2. **Validation**:<br>   - Validate container type exists and is active<br>   - Validate client project (if provided)<br>   - Validate unique names:<br>     - Check for duplicate sample names in database<br>     - Return 400 if duplicates found<br>   - Validate container names:<br>     - Check for duplicate container names in database<br>     - Return 400 if duplicates found<br>   - Validate client_sample_ids:<br>     - Check for duplicate client_sample_ids in database<br>     - Return 400 if duplicates found<br>3. **Atomic Creation** (single transaction):<br>   - For each unique entry (5 samples):<br>     - Create sample with common + unique fields<br>     - Set status = "Received"<br>     - Create container instance<br>     - Link sample to container via `Contents` junction<br>     - Create tests (from battery and/or assigned_tests)<br>     - Set test status = "In Process"<br>   - Link project to client project (if provided, once)<br>4. **Transaction Commit**:<br>   - Commit all samples, containers, contents, and tests atomically<br>   - Rollback on any error (all-or-nothing) |
| **Sample Records** | - 5 sample records created:<br>  - BULK-001: Common fields + unique fields<br>  - BULK-002: Common fields + unique fields<br>  - BULK-003: Common fields + temperature override (-20)<br>  - BULK-004: Common fields + client_sample_id<br>  - BULK-005: Common fields + description<br>- All samples have:<br>  - `status` = "Received" status UUID<br>  - `project_id` = Project Alpha UUID<br>  - `sample_type`, `matrix` from common fields<br>  - `due_date`, `received_date` from common fields<br>  - Audit fields set |
| **Container Records** | - 5 container records created:<br>  - CONTAINER-BULK-001, CONTAINER-BULK-002, etc.<br>- All containers have:<br>  - `type_id` = 15mL Tube UUID<br>  - `row` = 1, `column` = 1 (defaults)<br>  - Audit fields set |
| **Contents Records** | - 5 `Contents` junction records created:<br>  - Each linking sample to container |
| **Test Records** | - Tests created for all samples:<br>  - From test battery: All analyses in battery<br>  - From assigned_tests: Individual analyses<br>  - All tests have status "In Process" |
| **UI Feedback** | - Success message: "Successfully accessioned 5 sample(s)!"<br>- All 5 samples visible in samples list<br>- All containers visible in containers list<br>- All tests visible in tests list |

### Test Steps - Duplicate Validation (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Duplicate Validation** | |
| 7.1 | Start new bulk accessioning | Form loads |
| 7.2 | Enter common fields | Common fields entered |
| 7.3 | Enter unique fields with duplicate sample name: `BULK-001` (already exists) | Name entered |
| 7.4 | Enter container name: `CONTAINER-NEW-001` | Container name entered |
| 7.5 | Click "Submit" | Form submits |
| 7.6 | Verify error response | HTTP 400 Bad Request:<br>- Error message: "Duplicate sample names found: BULK-001"<br>- No samples created |

### Expected Results - Duplicate Validation

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 400 Bad Request<br>- Error message: "Duplicate sample names found: {name}" or "Duplicate container names found: {name}"<br>- No samples created (transaction rolled back) |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Bulk mode toggle works | ✓ | ✗ |
| Common fields shared across all samples | ✓ | ✗ |
| Unique fields table accepts input | ✓ | ✗ |
| All 5 samples created successfully | ✓ | ✗ |
| All containers created and linked | ✓ | ✗ |
| All tests created for all samples | ✓ | ✗ |
| Atomic transaction (all-or-nothing) | ✓ | ✗ |
| Duplicate validation prevents creation | ✓ | ✗ |
| Temperature override works | ✓ | ✗ |
| Client sample ID stored correctly | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Bulk Accessioning - Auto-Naming

### Test Case ID
TC-BULK-AUTO-NAME-002

### Description
Accession multiple samples in bulk mode using auto-generated sequential names with prefix and start number.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to at least one project |
| **Common Fields Valid** | Sample type, matrix, project, container type exist |
| **No Duplicates** | Auto-generated names (e.g., "BATCH-001", "BATCH-002") do not exist |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads |
| 2 | **Enable Bulk Mode** | |
| 2.1 | Toggle "Bulk Accessioning Mode" switch to ON | Form switches to bulk mode |
| 3 | **Enter Common Fields** | |
| 3.1 | Enter Due Date: `2025-02-15` | Field accepts input |
| 3.2 | Enter Received Date: `2025-01-20` | Field accepts input |
| 3.3 | Select Sample Type: `Blood` | Type selected |
| 3.4 | Select Matrix: `Whole Blood` | Matrix selected |
| 3.5 | Select Project: `Project Alpha` | Project selected |
| 3.6 | Select Container Type: `15mL Tube` | Container type selected |
| 4 | **Configure Auto-Naming** | |
| 4.1 | Locate "Auto-Naming" section | Section visible in form |
| 4.2 | Enter Prefix: `BATCH-` | Field accepts input |
| 4.3 | Enter Start Number: `1` | Field accepts input (default: 1) |
| 5 | **Enter Unique Fields (No Names)** | |
| 5.1 | Verify unique fields table | Table displays with Name column |
| 5.2 | **Sample 1**: Leave Name empty, Enter Container: `CONTAINER-AUTO-001` | Name field empty (will be auto-generated) |
| 5.3 | **Sample 2**: Leave Name empty, Enter Container: `CONTAINER-AUTO-002` | Name field empty |
| 5.4 | **Sample 3**: Leave Name empty, Enter Container: `CONTAINER-AUTO-003` | Name field empty |
| 5.5 | Verify auto-naming preview (if available) | Preview shows: "BATCH-001", "BATCH-002", "BATCH-003" |
| 6 | **Submit** | |
| 6.1 | Click "Submit" or "Accession Samples" button | Form submits |
| 6.2 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/samples/bulk-accession` called with:<br>```json
{
  "due_date": "2025-02-15T00:00:00Z",
  "received_date": "2025-01-20T00:00:00Z",
  "sample_type": "uuid-of-blood",
  "matrix": "uuid-of-whole-blood",
  "project_id": "uuid-of-project-alpha",
  "container_type_id": "uuid-of-15ml-tube",
  "auto_name_prefix": "BATCH-",
  "auto_name_start": 1,
  "uniques": [
    {
      "container_name": "CONTAINER-AUTO-001"
    },
    {
      "container_name": "CONTAINER-AUTO-002"
    },
    {
      "container_name": "CONTAINER-AUTO-003"
    }
  ]
}
``` |
| **Backend Processing** | 1. **Name Generation**:<br>   - Initialize counter: `auto_name_counter = auto_name_start or 1`<br>   - For each unique entry:<br>     - If `unique.name` provided, use it<br>     - Else if `auto_name_prefix` provided:<br>       - Generate: `sample_name = f"{auto_name_prefix}{auto_name_counter}"`<br>       - Increment counter<br>     - Else: Return 400 error<br>2. **Validation**:<br>   - Validate generated names are unique<br>   - Check for duplicates in database<br>3. **Creation**:<br>   - Create samples with generated names:<br>     - BATCH-001, BATCH-002, BATCH-003<br>   - Create containers and tests as in TC-BULK-UNIQUES-001 |
| **Sample Records** | - 3 sample records created:<br>  - `name` = "BATCH-001"<br>  - `name` = "BATCH-002"<br>  - `name` = "BATCH-003"<br>- All samples have common fields applied |
| **UI Feedback** | - Success message: "Successfully accessioned 3 sample(s)!"<br>- Samples visible with auto-generated names |

### Test Steps - Custom Start Number

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Custom Start Number** | |
| 7.1 | Start new bulk accessioning | Form loads |
| 7.2 | Enter common fields | Common fields entered |
| 7.3 | Enter Prefix: `SAMPLE-` | Prefix entered |
| 7.4 | Enter Start Number: `100` | Start number entered |
| 7.5 | Enter 2 unique entries (containers only) | 2 rows added |
| 7.6 | Submit | Form submits |
| 7.7 | Verify generated names | Samples created with names: "SAMPLE-100", "SAMPLE-101" |

### Expected Results - Custom Start Number

| Category | Expected Outcome |
|----------|------------------|
| **Name Generation** | - Names generated: "SAMPLE-100", "SAMPLE-101"<br>- Counter starts at 100 and increments |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Auto-naming section visible | ✓ | ✗ |
| Prefix and start number fields accept input | ✓ | ✗ |
| Names auto-generated when not provided | ✓ | ✗ |
| Sequential numbering works correctly | ✓ | ✗ |
| Custom start number works | ✓ | ✗ |
| All samples created with generated names | ✓ | ✗ |
| Validation ensures generated names are unique | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Batch Results Entry - Tabular Interface

### Test Case ID
TC-BATCH-RESULTS-003

### Description
Enter results for multiple tests/samples in a batch using the tabular interface with real-time validation and QC checks.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `result:enter`, `batch:read` |
| **Batch Exists** | At least one batch with status "In Process" exists |
| **Tests in Batch** | Batch contains at least 3 tests with status "In Analysis" |
| **Analyses Configured** | Tests have analyses with configured analytes:<br>- At least one numeric analyte with range (low_value, high_value)<br>- At least one required analyte |
| **QC Samples** | At least one QC sample in batch (for QC validation test) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/results` or Results Management page | Results Management page loads |
| 2 | **Select Batch** | |
| 2.1 | Locate batch: `BATCH-RESULTS-001` | Batch row visible in table |
| 2.2 | Click "Enter Results" button | Batch results entry view opens |
| 2.3 | Verify batch information card | Card displays: batch name, status, sample count, test count |
| 3 | **Load Tabular Interface** | |
| 3.1 | Verify tabular interface loads | Table displays with:<br>- Rows: Tests/samples in batch<br>- Columns: Sample name, Position, custom attributes (if configured), analyte columns |
| 3.2 | Verify QC sample highlighting | QC sample rows highlighted with warning background color |
| 3.3 | Verify analyte columns | Each analyte column header shows:<br>- Reported name<br>- Required indicator (*) if applicable<br>- Min/max values (for numeric analytes) |
| 4 | **Enter Results for Multiple Tests** | |
| 4.1 | Enter raw_result for Test 1, Analyte 1: `10.5` (numeric, within range) | Cell accepts input, no validation error |
| 4.2 | Enter reported_result: `10.5` | Cell accepts input |
| 4.3 | Enter raw_result for Test 2, same analyte: `12.3` | Cell accepts input |
| 4.4 | Enter raw_result for Test 3, same analyte: `8.7` | Cell accepts input |
| 4.5 | Enter raw_result for Test 1, Analyte 2 (text): `Pass` | Cell accepts input |
| 5 | **Test Validation** | |
| 5.1 | Enter invalid value: raw_result = `25.0` (exceeds high_value of 20.0) | Real-time validation error displayed:<br>- Inline error message: "Value exceeds maximum of 20.0"<br>- Cell highlighted in red |
| 5.2 | Clear invalid value | Error message disappears |
| 5.3 | Leave required analyte empty | Validation error displayed:<br>- "Required field" message |
| 6 | **Submit Results** | |
| 6.1 | Fix all validation errors | All cells have valid values |
| 6.2 | Click "Submit Results" button | Form submits, loading spinner shown |
| 6.3 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/results/batch` called with:<br>```json
{
  "batch_id": "uuid-of-batch",
  "results": [
    {
      "test_id": "uuid-of-test-1",
      "analyte_results": [
        {
          "analyte_id": "uuid-of-analyte-1",
          "raw_result": "10.5",
          "reported_result": "10.5",
          "qualifiers": null,
          "notes": null
        },
        {
          "analyte_id": "uuid-of-analyte-2",
          "raw_result": "Pass",
          "reported_result": "Pass",
          "qualifiers": null,
          "notes": null
        }
      ]
    },
    {
      "test_id": "uuid-of-test-2",
      "analyte_results": [
        {
          "analyte_id": "uuid-of-analyte-1",
          "raw_result": "12.3",
          "reported_result": "12.3",
          "qualifiers": null,
          "notes": null
        }
      ]
    },
    {
      "test_id": "uuid-of-test-3",
      "analyte_results": [
        {
          "analyte_id": "uuid-of-analyte-1",
          "raw_result": "8.7",
          "reported_result": "8.7",
          "qualifiers": null,
          "notes": null
        }
      ]
    }
  ]
}
``` |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify user has `result:enter` permission<br>   - Verify user has `batch:read` permission<br>   - Fetch batch and validate it exists<br>2. **Batch Validation**:<br>   - Get all containers in batch via `BatchContainer` junction<br>   - Get all samples from containers via `Contents` junction<br>   - Get all tests for samples in batch<br>   - Validate all `test_id`s in request exist in batch<br>3. **Result Validation** (per test/analyte):<br>   - For each test result entry:<br>     - Get `analysis_analytes` configuration for test's analysis<br>     - For each analyte result:<br>       - Validate required analytes have values<br>       - Validate data type (numeric vs text)<br>       - Validate range (low_value, high_value) for numeric analytes<br>       - Collect validation errors per test/analyte<br>   - If validation errors exist, rollback and return detailed errors<br>4. **Result Creation/Update**:<br>   - For each validated result:<br>     - Check if result already exists (update) or creates new<br>     - Set `entry_date` to current timestamp<br>     - Set `entered_by` to current user<br>     - Set audit fields<br>5. **Test Status Update**:<br>   - For each test, check if all analytes have results<br>   - Update test status to "Complete" when all analytes entered<br>   - Update test `modified_by` and `modified_at`<br>6. **QC Validation**:<br>   - Identifies QC samples in batch (samples with `qc_type` set)<br>   - Checks QC tests for failures:<br>     - Missing results for QC tests<br>     - Results outside expected ranges<br>   - If `FAIL_QC_BLOCKS_BATCH=true`, blocks submission on QC failures<br>   - If `false`, allows submission but includes QC failures in response<br>7. **Batch Status Update**:<br>   - Checks if all tests in batch are complete<br>   - Updates batch status to "Completed" if all tests complete<br>8. **Commit Transaction**:<br>   - All operations atomic (all or nothing) |
| **Result Records** | - Result records created/updated for each test-analyte combination:<br>  - `test_id` = test UUID<br>  - `analyte_id` = analyte UUID<br>  - `raw_result` = entered value<br>  - `reported_result` = entered value<br>  - `entry_date` = current timestamp<br>  - `entered_by` = current user UUID<br>  - Audit fields set |
| **Test Status Updates** | - Tests updated with status "Complete" when all analytes have results<br>- Test `modified_by` and `modified_at` updated |
| **Batch Status Update** | - Batch status updated to "Completed" if all tests are complete |
| **UI Feedback** | - Success message: "Results saved successfully"<br>- Table refreshes with saved results<br>- Test status indicators update to "Complete"<br>- Batch status indicator updates if all tests complete |

### Test Steps - QC Validation (Optional)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test QC Validation** | |
| 7.1 | Enter results for regular samples | Results entered successfully |
| 7.2 | Leave QC test results empty | QC test row visible but no results entered |
| 7.3 | Click "Submit Results" | Form submits |
| 7.4 | Verify QC failure detected | QC failure detected and reported:<br>- If `FAIL_QC_BLOCKS_BATCH=true`: Submission blocked<br>- If `false`: Warning shown, submission allowed |

### Expected Results - QC Validation

| Category | Expected Outcome |
|----------|------------------|
| **QC Failure Detection** | - QC failures identified:<br>  - Missing results for QC tests<br>  - Results outside expected ranges<br>- Response includes `qc_failures` array with details |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Tabular interface loads correctly | ✓ | ✗ |
| QC samples highlighted | ✓ | ✗ |
| Real-time validation works | ✓ | ✗ |
| Results saved for multiple tests | ✓ | ✗ |
| Test status updated to "Complete" when all analytes entered | ✓ | ✗ |
| Batch status updated when all tests complete | ✓ | ✗ |
| QC validation works | ✓ | ✗ |
| Transaction atomicity (all or nothing) | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-24 (Bulk Sample Accessioning)
- **As a** Lab Technician
- **I want** to accession multiple samples at once with shared common fields
- **So that** repetitive data entry is minimized for batch submissions
- **Acceptance Criteria**:
  - Toggle for bulk mode in accessioning UI
  - Common fields: sample_type, matrix, due_date, received_date, project_id, client_project_id, container_type, test battery/analyses
  - Unique fields per sample: name, client_sample_id, container_name/barcode, overrides (e.g., temperature)
  - Auto-generation option for sequential names (e.g., prefix + number)
  - Single transaction creates all samples/containers/tests; validation for uniques across set
  - API: POST `/samples/bulk-accession`; RBAC: `sample:create`

### User Story US-28 (Batch Results Entry)
- **As a** Lab Technician
- **I want** to enter results for multiple tests/samples in a batch at once
- **So that** data entry is efficient for grouped processing
- **Acceptance Criteria**:
  - Tabular UI for batch with rows for tests/samples and columns for analytes
  - Auto-fill common fields; real-time validation including QC checks
  - Atomic submit updates all results and statuses
  - Failing QC flags or blocks batch approval (configurable)
  - API: POST `/results/batch`; RBAC: `result:enter`

### Post-MVP PRD Section 4.1 (Bulk Accessioning)
- **UI**: Toggle, common fields, unique table
- **Backend**: Atomic multi-create
- **Features**:
  - Common fields shared across all samples
  - Unique fields per sample in table format
  - Auto-naming with prefix and start number
  - Single transaction for all samples, containers, contents, and tests

### Post-MVP PRD Section 4.4 (Batch Results)
- **Tabular entry**: Rows = tests/samples, Columns = analytes
- **QC flags/blocks**: Configurable QC validation
- **Features**:
  - Real-time validation
  - Atomic submission
  - Test status updates
  - Batch status updates

### Workflow Document (Variation B: Bulk Sample Accessioning)
- **Steps**:
  1. Enable Bulk Mode (toggle switch)
  2. Common Fields Entry (due_date, received_date, sample_type, matrix, project, container_type, QC type, test battery/analyses)
  3. Unique Fields Entry (table with name, client_sample_id, container_name, temperature, description, anomalies)
  4. Test Assignment (applies to all samples)
  5. Review and Submit (atomic transaction)
- **Validation**: No duplicate sample names, container names, or client_sample_ids
- **Status Transitions**: All samples "Received", all tests "In Process"

### Workflow Document (Variation B: Batch Results Entry)
- **Steps**:
  1. Select Batch
  2. Batch Entry Interface (tabular: rows = samples, columns = analytes)
  3. Enter Results for Batch (real-time validation)
  4. QC Validation (checks for failures)
  5. Submit Results (atomic operation)
- **Features**: Real-time validation, QC checks, atomic submission

### API Endpoints
- **POST `/samples/bulk-accession`**: Bulk accession multiple samples
  - Request: `BulkSampleAccessioningRequest` with common fields, uniques array, auto-naming options
  - Response: `List[SampleResponse]`
  - Processing: Atomic transaction, duplicate validation, auto-naming
- **POST `/results/batch`**: Enter results for batch
  - Request: `BatchResultsEntryRequestUS28` with batch_id and results array
  - Response: `BatchResponse` with updated batch status
  - Processing: Validation, QC checks, test status updates, batch status updates

### Schema
- **`BulkSampleAccessioningRequest`**:
  - Common fields: `due_date`, `received_date`, `sample_type`, `matrix`, `project_id`, `container_type_id`, `battery_id`, `assigned_tests`
  - Auto-naming: `auto_name_prefix`, `auto_name_start`
  - Uniques: `List[BulkSampleUnique]` with `name`, `client_sample_id`, `container_name`, `temperature`, `description`, `anomalies`, `custom_attributes`
- **`BulkSampleUnique`**:
  - `name`: Optional (required if no auto_name_prefix)
  - `client_sample_id`: Optional
  - `container_name`: Required, unique
  - `temperature`: Optional (overrides common)
  - `description`: Optional
  - `anomalies`: Optional
  - `custom_attributes`: Optional (validated against active configs)

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-BULK-UNIQUES-001 | | | | |
| TC-BULK-AUTO-NAME-002 | | | | |
| TC-BATCH-RESULTS-003 | | | | |

---

## Appendix: Sample Test Data

### Sample Names
- `BULK-001` through `BULK-005` (for bulk accessioning with unique fields)
- `BATCH-001` through `BATCH-003` (for auto-naming)
- `SAMPLE-100`, `SAMPLE-101` (for custom start number)

### Container Names
- `CONTAINER-BULK-001` through `CONTAINER-BULK-005`
- `CONTAINER-AUTO-001` through `CONTAINER-AUTO-003`

### Auto-Naming
- Prefix: `BATCH-`, `SAMPLE-`
- Start numbers: `1` (default), `100` (custom)

### Batches
- `BATCH-RESULTS-001` (batch for results entry)

### Test Statuses
- `In Process` (initial status)
- `In Analysis` (results being entered)
- `Complete` (all analytes entered)

### Batch Statuses
- `Created` (initial status)
- `In Process` (analysis in progress)
- `Completed` (all tests complete)

