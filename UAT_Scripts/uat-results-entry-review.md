# UAT Scripts: Results Entry and Review

## Overview

This document contains User Acceptance Testing (UAT) scripts for results entry and review in NimbleLIMS. These scripts validate the results entry workflow and review process as defined in:

- **User Stories**: US-11 (Create and Manage Batches), US-28 (Batch Results Entry)
- **PRD**: Section 3.1 (Results Entry)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stages 3-4: Results Entry and Review)
- **UI Document**: `ui-accessioning-to-reporting.md` (ResultsEntryTable.tsx, BatchResultsEntryTable.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (POST /results/batch)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Test status list entries: "In Process", "In Analysis", "Complete"
  - Sample status list entries: "Available for Testing", "Testing Complete", "Reviewed"
  - Batch status list entries: "Created", "In Process", "Completed"
  - At least one batch with status "In Process"
  - At least one test with status "In Analysis" in the batch
  - At least one analysis with configured analytes (with validation rules: data type, ranges, required flags)
  - At least one QC sample in batch (for QC failure test)
- Test user accounts:
  - Lab Technician with `result:enter` and `batch:read` permissions
  - Lab Manager with `result:review` permission

---

## Test Case 1: Batch Results Entry - Analyte Validation

### Test Case ID
TC-RESULTS-ENTRY-001

### Description
Enter results for multiple tests/samples in a batch using the tabular interface, with real-time validation of analyte values.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `result:enter`, `batch:read` |
| **Batch Exists** | At least one batch with status "In Process" exists |
| **Tests in Batch** | At least two tests with status "In Analysis" exist in batch |
| **Analysis Configured** | Tests have analyses with configured analytes:<br>- At least one required analyte<br>- At least one numeric analyte with range (low_value, high_value)<br>- At least one text analyte |
| **Samples in Batch** | Batch contains at least two samples (from containers) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/results` or Results Management page | Results Management page loads with batch list |
| 2 | **Select Batch** | |
| 2.1 | Locate batch: `BATCH-RESULTS-001` | Batch row visible in table with status "In Process" |
| 2.2 | Click "Enter Results" button | Batch results entry view opens |
| 2.3 | Verify batch information card | Card displays: batch name, status, description, sample count, test count |
| 3 | **Load Tabular Interface** | |
| 3.1 | Verify tabular interface loads | Table displays with:<br>- Rows: Tests/samples in batch<br>- Columns: Sample name, Position, custom attributes (if configured), analyte columns |
| 3.2 | Verify analyte columns | Each analyte column header shows:<br>- Reported name<br>- Required indicator (*) if applicable<br>- Min/max values (for numeric analytes)<br>- Data type indicator |
| 4 | **Enter Valid Results** | |
| 4.1 | Enter raw_result for first test, first analyte: `10.5` (numeric, within range) | Cell accepts input, no validation error |
| 4.2 | Enter reported_result: `10.5` | Cell accepts input |
| 4.3 | Enter raw_result for second test, same analyte: `12.3` | Cell accepts input, no validation error |
| 4.4 | Enter raw_result for first test, second analyte (text): `Pass` | Cell accepts input, no validation error |
| 5 | **Test Validation Errors** | |
| 5.1 | Enter invalid value: raw_result = `25.0` (numeric analyte, exceeds high_value of 20.0) | Real-time validation error displayed:<br>- Inline error message: "Value exceeds maximum of 20.0"<br>- Cell highlighted in red |
| 5.2 | Clear invalid value | Error message disappears |
| 5.3 | Enter value below range: raw_result = `-5.0` (numeric analyte, low_value = 0.0) | Real-time validation error displayed:<br>- Inline error message: "Value below minimum of 0.0" |
| 5.4 | Leave required analyte empty | Validation error displayed:<br>- "Required field" message |
| 5.5 | Enter non-numeric value in numeric field: `abc` | Validation error displayed:<br>- "Invalid data type: expected numeric" |
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
    }
  ]
}
``` |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify user has `result:enter` permission<br>   - Verify user has `batch:read` permission<br>   - Fetch batch and validate it exists<br>2. **Batch Validation**:<br>   - Get all containers in batch via `BatchContainer` junction<br>   - Get all samples from containers via `Contents` junction<br>   - Get all tests for samples in batch<br>   - Validate all `test_id`s in request exist in batch<br>3. **Result Validation** (per test/analyte):<br>   - For each test result entry:<br>     - Get `analysis_analytes` configuration for test's analysis<br>     - For each analyte result:<br>       - Validate required analytes have values<br>       - Validate data type (numeric vs text)<br>       - Validate range (low_value, high_value) for numeric analytes<br>       - Validate significant figures (warning if exceeded)<br>       - Collect validation errors per test/analyte<br>   - If validation errors exist, rollback and return detailed errors<br>4. **Result Creation/Update**:<br>   - For each validated result:<br>     - Check if result already exists (update) or creates new<br>     - Set `entry_date` to current timestamp<br>     - Set `entered_by` to current user<br>     - Set audit fields<br>5. **Test Status Update**:<br>   - For each test, check if all analytes have results<br>   - Update test status to "Complete" when all analytes entered<br>   - Update test `modified_by` and `modified_at`<br>6. **Batch Status Update**:<br>   - Check if all tests in batch are complete<br>   - Update batch status to "Completed" if all tests complete<br>7. **Commit Transaction**:<br>   - All operations atomic (all or nothing) |
| **Result Records** | - Result records created/updated for each test-analyte combination:<br>  - `test_id` = test UUID<br>  - `analyte_id` = analyte UUID<br>  - `raw_result` = entered value<br>  - `reported_result` = entered value<br>  - `entry_date` = current timestamp<br>  - `entered_by` = current user UUID<br>  - Audit fields set |
| **Test Status Updates** | - Tests updated with status "Complete" when all analytes have results<br>- Test `modified_by` and `modified_at` updated |
| **Batch Status Update** | - Batch status updated to "Completed" if all tests are complete |
| **UI Feedback** | - Success message: "Results saved successfully"<br>- Table refreshes with saved results<br>- Test status indicators update to "Complete"<br>- Batch status indicator updates if all tests complete |

### Test Steps - Validation Error Response (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Validation Error Response** | |
| 7.1 | Enter invalid results (e.g., out of range, missing required) | Invalid values entered |
| 7.2 | Click "Submit Results" | Form submits |
| 7.3 | Verify error response | HTTP 400 Bad Request returned with detailed errors:<br>```json
{
  "detail": "Validation errors found",
  "validation_errors": [
    {
      "test_id": "uuid",
      "analyte_id": "uuid",
      "error": "Value exceeds maximum of 20.0"
    },
    {
      "test_id": "uuid",
      "analyte_id": "uuid",
      "error": "Required field missing"
    }
  ]
}
```<br>- Validation errors displayed at top of table<br>- Individual cells highlighted with errors |

### Expected Results - Validation Errors

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 400 Bad Request<br>- Detailed validation errors per test/analyte<br>- No results created (transaction rolled back) |
| **UI Display** | - Error alert at top of table<br>- Individual cells highlighted with inline error messages<br>- Table remains editable |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Tabular interface loads correctly | ✓ | ✗ |
| Real-time validation works for numeric ranges | ✓ | ✗ |
| Real-time validation works for data types | ✓ | ✗ |
| Required field validation works | ✓ | ✗ |
| Validation errors displayed inline | ✓ | ✗ |
| Results saved successfully (valid data) | ✓ | ✗ |
| Test status updated to "Complete" when all analytes entered | ✓ | ✗ |
| Batch status updated when all tests complete | ✓ | ✗ |
| Validation errors prevent submission | ✓ | ✗ |
| Transaction atomicity (all or nothing) | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Results Review - Status Update to 'Complete'

### Test Case ID
TC-RESULTS-REVIEW-002

### Description
Review and approve test results, updating test status to "Complete" and sample status to "Reviewed" when all tests are complete.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Manager |
| **Required Permission** | `result:review` |
| **Test Exists** | At least one test with status "In Analysis" exists |
| **Results Entered** | All required analytes have results entered for the test |
| **Sample Has Multiple Tests** | Sample has at least two tests (one ready for review, one incomplete) |
| **Status Available** | "Complete" status exists in `test_status` list<br>"Reviewed" status exists in `sample_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to test details or batch view | Test details view loads |
| 2 | **Access Test for Review** | |
| 2.1 | Locate test: `TEST-REVIEW-001` with status "In Analysis" | Test visible in list or details view |
| 2.2 | Click on test or "Review" button | Test review view opens |
| 2.3 | Verify test information displayed | Test details show:<br>- Test name, analysis, status<br>- Sample information<br>- All results for the test |
| 3 | **Review Results** | |
| 3.1 | Verify all required analytes have results | Results displayed for all required analytes |
| 3.2 | Check result values against expected ranges | Values within configured ranges |
| 3.3 | Review qualifiers and notes | Qualifiers and notes visible (if applicable) |
| 3.4 | Verify calculations (if applicable) | Calculated results displayed (post-MVP) |
| 4 | **Approve Test** | |
| 4.1 | Click "Approve" or "Mark Complete" button | Review dialog or confirmation appears |
| 4.2 | Confirm review date: `2025-01-20 14:30:00` | Review date set (or auto-set to current timestamp) |
| 4.3 | Click "Confirm" or "Approve" | Form submits, loading spinner shown |
| 4.4 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/tests/{test_id}/review` called with:<br>```json
{
  "review_date": "2025-01-20T14:30:00Z"
}
``` |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify test exists<br>   - Check user has `result:review` permission<br>   - Verify project access (RLS)<br>2. **Status Update**:<br>   - Get "Complete" status from `list_entries`<br>   - Update test status to "Complete"<br>   - Set `review_date` from request (or current timestamp)<br>   - Update audit fields: `modified_by`, `modified_at`<br>3. **Sample Status Check**:<br>   - Get "Reviewed" status from `list_entries`<br>   - Query all tests for sample<br>   - Count incomplete tests<br>   - If all tests complete:<br>     - Update sample status to "Reviewed"<br>     - Update sample audit fields<br>4. **Commit**:<br>   - Commit test and sample updates<br>   - Return updated test |
| **Test Record** | - Test updated with:<br>  - `status` = UUID of "Complete" status<br>  - `review_date` = review date timestamp<br>  - `modified_by` = current user UUID<br>  - `modified_at` = current timestamp |
| **Sample Status Update** | - If all tests for sample are complete:<br>  - Sample `status` = UUID of "Reviewed" status<br>  - Sample `modified_by` and `modified_at` updated |
| **UI Feedback** | - Success message: "Test reviewed and approved"<br>- Test status indicator updates to "Complete" (green chip)<br>- Sample status updates to "Reviewed" if all tests complete<br>- Test no longer appears in "In Analysis" filter |

### Test Steps - Partial Completion (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5 | **Test Partial Completion** | |
| 5.1 | Locate sample with multiple tests | Sample visible |
| 5.2 | Review first test (all results entered) | First test status = "Complete" |
| 5.3 | Verify sample status | Sample status remains "Testing Complete" (not "Reviewed") |
| 5.4 | Review second test (all results entered) | Second test status = "Complete" |
| 5.5 | Verify sample status | Sample status updates to "Reviewed" (all tests complete) |

### Expected Results - Partial Completion

| Category | Expected Outcome |
|----------|------------------|
| **Sample Status Logic** | - Sample status remains "Testing Complete" until all tests are complete<br>- Sample status updates to "Reviewed" only when all tests have status "Complete" |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Test status updated to "Complete" | ✓ | ✗ |
| review_date set correctly | ✓ | ✗ |
| Audit fields updated | ✓ | ✗ |
| Sample status updates to "Reviewed" when all tests complete | ✓ | ✗ |
| Sample status remains "Testing Complete" if tests incomplete | ✓ | ✗ |
| Test visible in "Complete" filter | ✓ | ✗ |
| Test no longer visible in "In Analysis" filter | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: QC Failure Flag - Blocking and Warning

### Test Case ID
TC-QC-FAILURE-003

### Description
Verify QC failure detection and handling during batch results entry, with configurable blocking behavior.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `result:enter`, `batch:read` |
| **Batch Exists** | At least one batch with status "In Process" exists |
| **QC Sample in Batch** | At least one sample in batch has `qc_type` set (e.g., "Blank", "Positive Control") |
| **QC Test** | QC sample has at least one test assigned |
| **QC Failure Scenario** | One of the following:<br>- QC test has no results entered<br>- QC test has results outside expected range |
| **Configuration** | `FAIL_QC_BLOCKS_BATCH` environment variable set (test both `true` and `false`) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/results` or Results Management page | Results Management page loads |
| 2 | **Select Batch with QC Sample** | |
| 2.1 | Locate batch: `BATCH-QC-001` | Batch row visible |
| 2.2 | Verify QC indicator | Batch row shows QC warning icon (⚠️) or chip |
| 2.3 | Click "Enter Results" button | Batch results entry view opens |
| 3 | **Verify QC Sample Highlighting** | |
| 3.1 | Locate QC sample row in table | QC sample row highlighted with warning background color |
| 3.2 | Verify QC type indicator | QC type displayed (e.g., "Blank", "Positive Control") |
| 4 | **Enter Results with QC Failure** | |
| 4.1 | Enter results for regular samples | Results entered successfully |
| 4.2 | **Scenario A: Missing QC Results** | |
| 4.2.1 | Leave QC test results empty | QC test row visible but no results entered |
| 4.2.2 | Click "Submit Results" | Form submits |
| 4.2.3 | Verify QC failure detected | QC failure detected and reported |
| 4.3 | **Scenario B: Out-of-Range QC Results** | |
| 4.3.1 | Enter QC test result: `25.0` (exceeds expected range of 0.0-20.0) | Result entered |
| 4.3.2 | Click "Submit Results" | Form submits |
| 4.3.3 | Verify QC failure detected | QC failure detected and reported |
| 5 | **Test Blocking Behavior (FAIL_QC_BLOCKS_BATCH=true)** | |
| 5.1 | Set environment variable: `FAIL_QC_BLOCKS_BATCH=true` | Configuration set |
| 5.2 | Enter results with QC failure | QC failure scenario created |
| 5.3 | Click "Submit Results" | Form submits |
| 5.4 | Verify submission blocked | HTTP 400 Bad Request returned:<br>- Error message: "QC failures detected and blocking is enabled. Batch submission blocked."<br>- QC failures detailed in response<br>- No results saved |
| 6 | **Test Warning Behavior (FAIL_QC_BLOCKS_BATCH=false)** | |
| 6.1 | Set environment variable: `FAIL_QC_BLOCKS_BATCH=false` | Configuration set |
| 6.2 | Enter results with QC failure | QC failure scenario created |
| 6.3 | Click "Submit Results" | Form submits |
| 6.4 | Verify submission allowed with warning | HTTP 200 OK returned:<br>- Warning message: "Warning: X QC failure(s) detected."<br>- QC failures included in response<br>- Results saved successfully |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **QC Sample Detection** | - QC samples identified by `qc_type` field (not null)<br>- QC samples highlighted in UI with warning background color<br>- QC type displayed in sample row |
| **QC Failure Detection** | Backend checks QC samples for failures:<br>1. **Missing Results**:<br>   - Query QC tests in batch<br>   - Check if QC test has no results entered<br>   - Flag as failure: "No results entered for QC sample"<br>2. **Out-of-Range Results** (simplified check):<br>   - Check if QC results are within expected ranges<br>   - Flag as failure if outside range (future: configurable QC acceptance criteria) |
| **API Response - Blocking Enabled** | ```json
{
  "detail": "QC failures detected and blocking is enabled. Batch submission blocked.",
  "qc_failures": [
    {
      "test_id": "uuid",
      "sample_id": "uuid",
      "reason": "No results entered for QC sample"
    }
  ]
}
```<br>- HTTP 400 Bad Request<br>- No results saved (transaction rolled back) |
| **API Response - Warning Only** | ```json
{
  "id": "batch-uuid",
  "name": "BATCH-QC-001",
  "status": "In Process",
  "qc_failures": [
    {
      "test_id": "uuid",
      "sample_id": "uuid",
      "reason": "No results entered for QC sample"
    }
  ]
}
```<br>- HTTP 200 OK<br>- Results saved successfully<br>- QC failures included in response |
| **UI Feedback - Blocking** | - Error alert: "QC failures detected and blocking is enabled. Batch submission blocked."<br>- QC failures listed with details<br>- Table remains editable<br>- No results saved |
| **UI Feedback - Warning** | - Warning alert: "Warning: X QC failure(s) detected."<br>- QC failures listed with details<br>- Results saved successfully<br>- Success message displayed |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| QC samples highlighted in UI | ✓ | ✗ |
| QC failure detected for missing results | ✓ | ✗ |
| QC failure detected for out-of-range results | ✓ | ✗ |
| Submission blocked when FAIL_QC_BLOCKS_BATCH=true | ✓ | ✗ |
| Submission allowed with warning when FAIL_QC_BLOCKS_BATCH=false | ✓ | ✗ |
| QC failures detailed in response | ✓ | ✗ |
| Transaction atomicity maintained (blocking case) | ✓ | ✗ |
| Results saved when warning only | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-11 (Create and Manage Batches)
- **As a** Lab Technician
- **I want** to create batches of containers
- **So that** group processing is supported
- **Acceptance Criteria**:
  - Add containers; statuses: Created, In Process, Completed
  - Workflow: Created → In Process (analysis) → Completed (review)
  - Plates: As containers with wells (row/column)
  - API: POST `/batches`; add via `/batch-containers`; RBAC: `batch:manage`

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

### PRD Section 3.1 (Results Entry)
- **Results Entry**:
  - Batch/plate-based: Select batch (container collection), test; display analytes for entry
  - Fields: raw_result, reported_result, qualifiers, calculated_result (post-MVP calculations)
  - Validation: Per analyte (data type, ranges, sig figs)
  - Review: Lab manager at test level; updates statuses

### Workflow Document (Stage 3: Results Entry)
- **Purpose**: Enter test results for samples in a batch
- **Actors**: Lab Technician
- **Variation B: Batch Results Entry (US-28)**:
  - Select batch from Results Management
  - System displays tabular interface (rows: samples, columns: analytes)
  - QC sample rows highlighted with warning background color
  - Enter results directly in table cells with real-time validation
  - Real-time validation: inline error messages, range validation, data type validation, required field validation
  - QC validation checks QC samples for failures
  - Submit results: atomic operation, updates test statuses, updates batch status

### Workflow Document (Stage 4: Results Review)
- **Purpose**: Review and approve test results before reporting
- **Actors**: Lab Manager
- **Steps**:
  1. Access test for review
  2. Review results (verify required analytes, check values, review qualifiers)
  3. Approve test: Set review_date, update test status to "Complete"
  4. System checks if all tests for sample are complete
  5. If all tests complete, updates sample status to "Reviewed"
- **Status Transitions**:
  - Test: "In Analysis" → "Complete"
  - Sample: "Testing Complete" → "Reviewed" (when all tests complete)
- **Business Rules**:
  - Only Lab Managers (with `result:review` permission) can review
  - Test must have all required results entered before review
  - Sample status updates automatically when all tests are reviewed

### UI Document (ResultsEntryTable.tsx, BatchResultsEntryTable.tsx)
- **BatchResultsEntryTable.tsx**: Tabular interface for batch results entry
  - Rows: Tests/samples in batch
  - Columns: Sample name, Position, custom attributes (if configured), analyte columns
  - QC sample rows highlighted with warning background color
  - Real-time validation with inline error messages
  - Validation errors displayed at top of table
  - Submit button for atomic submission
- **ResultsEntryTable.tsx**: Single-test results entry interface
  - Form-based entry for one test at a time
  - Validation before save

### Technical Document (POST /results/batch)
- **Purpose**: Enter results for multiple tests/samples in a batch atomically
- **Request Schema**: `BatchResultsEntryRequestUS28`
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
- **Processing Steps**:
  1. Access control (verify permissions, fetch batch)
  2. Batch validation (validate test_ids exist in batch)
  3. Result validation (per test/analyte: required, data type, range, sig figs)
  4. Result creation/update (atomic transaction)
  5. Test status update (to "Complete" when all analytes entered)
  6. QC validation (check QC samples for failures)
  7. Batch status update (to "Completed" when all tests complete)
  8. Commit transaction
- **QC Validation**:
  - Identifies QC samples (samples with `qc_type` set)
  - Checks QC tests for failures (missing results, out-of-range results)
  - Configurable blocking via `FAIL_QC_BLOCKS_BATCH` env var
  - If `true`: blocks submission on QC failures
  - If `false`: allows submission but includes QC failures in response

### Technical Document (PATCH /tests/{id}/review)
- **Purpose**: Review and approve test results
- **Request Schema**: `TestReviewRequest`
  ```json
  {
    "review_date": "2025-01-20T14:30:00Z"
  }
  ```
- **Processing Steps**:
  1. Access control (verify test exists, check `result:review` permission, verify project access)
  2. Status update (get "Complete" status, update test status, set review_date, update audit fields)
  3. Sample status check (get "Reviewed" status, query all tests for sample, if all tests complete, update sample status to "Reviewed")
  4. Commit (commit test and sample updates, return updated test)

### Schema
- **`results` table**:
  - `test_id`: UUID FK to `tests.id`
  - `analyte_id`: UUID FK to `analytes.id`
  - `raw_result`: String (nullable)
  - `reported_result`: String (nullable)
  - `qualifiers`: UUID FK to `list_entries.id` (nullable)
  - `calculated_result`: String (nullable)
  - `entry_date`: DateTime
  - `entered_by`: UUID FK to `users.id`
  - Audit fields: `created_at`, `created_by`, `modified_at`, `modified_by`
- **`tests` table**:
  - `status`: UUID FK to `list_entries.id`
  - `review_date`: DateTime (nullable)
  - `test_date`: DateTime (nullable)
  - `technician_id`: UUID FK to `users.id` (nullable)
- **`samples` table**:
  - `status`: UUID FK to `list_entries.id`
  - `qc_type`: UUID FK to `list_entries.id` (nullable)
- **`analysis_analytes` junction table**:
  - `analysis_id`: UUID FK to `analyses.id`
  - `analyte_id`: UUID FK to `analytes.id`
  - `data_type`: UUID FK to `list_entries.id`
  - `low_value`: Numeric (nullable)
  - `high_value`: Numeric (nullable)
  - `significant_figures`: Integer (nullable)
  - `is_required`: Boolean
  - `reported_name`: String

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-RESULTS-ENTRY-001 | | | | |
| TC-RESULTS-REVIEW-002 | | | | |
| TC-QC-FAILURE-003 | | | | |

---

## Appendix: Sample Test Data

### Batch Names
- `BATCH-RESULTS-001` (batch for results entry)
- `BATCH-QC-001` (batch with QC samples)

### Tests
- `TEST-REVIEW-001` (test ready for review)

### Samples
- Regular samples (no QC type)
- QC samples (with `qc_type` set: "Blank", "Positive Control", etc.)

### Analytes
- Numeric analyte with range (e.g., low_value = 0.0, high_value = 20.0)
- Text analyte
- Required analyte (is_required = true)
- Optional analyte (is_required = false)

### Test Statuses
- `In Process` (initial status)
- `In Analysis` (results being entered)
- `Complete` (reviewed and approved)

### Sample Statuses
- `Available for Testing` (ready for analysis)
- `Testing Complete` (all tests finished)
- `Reviewed` (all tests reviewed)

### Batch Statuses
- `Created` (initial status)
- `In Process` (analysis in progress)
- `Completed` (all tests complete)

### Configuration
- `FAIL_QC_BLOCKS_BATCH`: Environment variable
  - `true`: Blocks submission on QC failures
  - `false`: Allows submission with warning

