# UAT Scripts: Test Ordering and Status Management

## Overview

This document contains User Acceptance Testing (UAT) scripts for test ordering and status management in NimbleLIMS. These scripts validate the test assignment and status workflows as defined in:

- **User Stories**: US-7 (Assign Tests to Samples), US-8 (Test Status Management), US-23 (Test Battery Assignment)
- **PRD**: Section 3.1 (Test Ordering)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stage 1: Test Assignment)
- **UI Document**: `ui-accessioning-to-reporting.md` (TestAssignmentStep.tsx, TestsManagement.tsx, TestForm.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (POST /tests, POST /samples/accession)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Test status list entries: "In Process", "In Analysis", "Complete"
  - At least one analysis (e.g., "EPA Method 8080")
  - At least one test battery with multiple analyses (for battery test)
  - At least one sample (for status update test)
- Test user accounts:
  - Lab Technician with `test:assign` and `test:update` permissions
  - Lab Manager with `test:update` permission

---

## Test Case 1: Test Assignment During Accessioning

### Test Case ID
TC-TEST-ASSIGN-001

### Description
Assign individual analyses to a sample during the accessioning workflow.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `test:assign` (implicit in `sample:create`) |
| **Project Access** | User has access to at least one project |
| **Analyses Available** | At least one analysis exists (e.g., "EPA Method 8080") |
| **Container Types** | At least one container type configured |
| **Status Available** | "In Process" status exists in `test_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads with 3-step wizard |
| 2 | Complete Step 1: Sample Details | Sample information entered (name, dates, type, matrix, temperature, project, container) |
| 3 | Click "Next" to advance to Step 2 | Test Assignment step displayed |
| 4 | **Step 2: Test Assignment** | |
| 4.1 | Verify analysis cards are displayed | Grid of analysis cards shows available analyses with details (name, method, turnaround time, cost) |
| 4.2 | **Select Individual Analysis** | |
| 4.3 | Click analysis card: `EPA Method 8080` | Card selected, shows blue border (2px), added to selected list |
| 4.4 | Verify Selected Analyses Summary | Summary shows count: "1 analysis selected", chip displays selected analysis name |
| 4.5 | Verify analysis details in summary | Summary card shows: "EPA Method 8080 • Method: EPA 8080 • 5 days • $150" |
| 4.6 | Click "Next" to advance to Step 3 | Review step displayed |
| 5 | **Step 3: Review & Submit** | |
| 5.1 | Review Test Assignment section | Selected analysis "EPA Method 8080" displayed |
| 5.2 | Click "Submit" button | Form submits, loading spinner shown |
| 5.3 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Calls** | 1. POST `/containers` creates container<br>2. POST `/samples/accession` creates sample with `assigned_tests: [analysis_id]`<br>3. POST `/contents` links sample to container<br>4. Tests created via `/samples/accession` endpoint |
| **Backend Processing** | 1. Sample created with status "Received"<br>2. `_create_tests_for_sample()` function called<br>3. For each analysis in `assigned_tests`:<br>   - Verify analysis exists and is active<br>   - Check if test already exists (prevent duplicates)<br>   - Create `Test` record with:<br>     - `sample_id` = sample ID<br>     - `analysis_id` = analysis ID<br>     - `battery_id` = NULL (individual assignment)<br>     - `status` = "In Process"<br>     - `technician_id` = current user ID<br>4. Commit transaction |
| **Test Records** | - Test created for "EPA Method 8080" analysis<br>- Test `name`: `{sample_name}_test_{analysis_id}`<br>- Test `status` = "In Process" status UUID<br>- Test `sample_id` = sample ID<br>- Test `analysis_id` = analysis ID<br>- Test `battery_id` = NULL<br>- Test `technician_id` = current user ID<br>- Audit fields set: `created_by`, `modified_by` = current user |
| **UI Feedback** | - Success message: "Sample accessioned successfully"<br>- Optional: Aliquot/Derivative dialog opens<br>- Form resets |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Test created successfully | ✓ | ✗ |
| Test status = "In Process" | ✓ | ✗ |
| Test linked to correct sample and analysis | ✓ | ✗ |
| `battery_id` = NULL (individual assignment) | ✓ | ✗ |
| `technician_id` set to current user | ✓ | ✗ |
| Audit fields set | ✓ | ✗ |
| No duplicate tests created | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Test Status Update - Change to 'In Analysis'

### Test Case ID
TC-TEST-STATUS-002

### Description
Update test status from "In Process" to "In Analysis" and assign technician.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `test:update` |
| **Test Exists** | At least one test with status "In Process" exists |
| **Status Available** | "In Analysis" status exists in `test_status` list |
| **Technicians** | At least one user exists (for technician assignment) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/tests` route | Tests Management page loads with DataGrid showing accessible tests |
| 2 | Verify user is logged in with `test:update` permission | User context shows appropriate role and permission |
| 3 | Locate test with status "In Process" | Test row visible in DataGrid with status column showing "In Process" |
| 4 | Click "Edit" button on test row | Edit dialog opens (TestForm component) |
| 5 | **Verify Pre-filled Data** | |
| 5.1 | Verify test details are displayed | Form shows current test data: name, status, sample, analysis, technician |
| 5.2 | Verify status dropdown shows "In Process" | Current status selected |
| 6 | **Update Status and Technician** | |
| 6.1 | Open Status dropdown | Dropdown shows available statuses from `test_status` list |
| 6.2 | Select "In Analysis" | Status selected, displayed in dropdown |
| 6.3 | **Assign Technician** (optional) | |
| 6.4 | Open Technician dropdown | Dropdown shows available users |
| 6.5 | Select Technician: `Lab Tech User` | Technician selected |
| 6.6 | **Set Test Date** (optional) | |
| 6.7 | Enter Test Date: `2025-01-20` (using DatePicker) | Date selected |
| 6.8 | Click "Save" button | Form submits, loading spinner shown |
| 6.9 | Wait for API response | Success message displayed or dialog closes |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/tests/{test_id}` called with:<br>- `status`: UUID of "In Analysis" status<br>- `technician_id`: UUID of selected technician (optional)<br>- `test_date`: "2025-01-20" (optional) |
| **Backend Processing** | 1. Verify test exists<br>2. Check `test:update` permission<br>3. Verify project access (RLS)<br>4. Validate status exists in `list_entries`<br>5. Update test fields (partial update)<br>6. Update audit fields: `modified_by` = current user ID, `modified_at` = current timestamp<br>7. Commit transaction |
| **Test Record** | - `status` field updated to "In Analysis" status UUID<br>- `technician_id` updated to selected technician UUID (if provided)<br>- `test_date` updated to selected date (if provided)<br>- `modified_by` = current user ID<br>- `modified_at` = current timestamp (updated)<br>- All other fields unchanged |
| **UI Feedback** | - Success message or dialog closes<br>- DataGrid refreshes showing updated status<br>- Status column shows "In Analysis" |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Status updated successfully | ✓ | ✗ |
| Status value = "In Analysis" UUID | ✓ | ✗ |
| Technician assigned (if provided) | ✓ | ✗ |
| Test date set (if provided) | ✓ | ✗ |
| Audit fields (`modified_by`, `modified_at`) updated | ✓ | ✗ |
| No validation errors | ✓ | ✗ |
| UI reflects updated status | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Test Battery Assignment - Sequence Order

### Test Case ID
TC-TEST-BATTERY-003

### Description
Assign a test battery to a sample during accessioning, verifying tests are created in sequence order.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `test:assign` (implicit in `sample:create`) |
| **Project Access** | User has access to at least one project |
| **Test Battery Exists** | At least one test battery exists with multiple analyses (e.g., "EPA 8080 Full" with 3+ analyses) |
| **Battery Analyses** | Battery has analyses with sequence ordering (sequence: 1, 2, 3, etc.) |
| **Container Types** | At least one container type configured |
| **Status Available** | "In Process" status exists in `test_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads |
| 2 | Complete Step 1: Sample Details | Sample information entered |
| 3 | Click "Next" to advance to Step 2 | Test Assignment step displayed |
| 4 | **Step 2: Test Assignment** | |
| 4.1 | **Select Test Battery** | |
| 4.2 | Locate "Test Battery" dropdown | Dropdown visible above analysis cards |
| 4.3 | Open Test Battery dropdown | Dropdown shows available test batteries |
| 4.4 | Select Battery: `EPA 8080 Full` | Battery selected, displayed in dropdown |
| 4.5 | Verify helper text displayed | Text shows: "Selecting a test battery will automatically create tests for all analyses in the battery." |
| 4.6 | **Verify Battery Analyses Display** (if implemented) | Battery analyses shown with sequence order |
| 4.7 | **Optionally Select Individual Analysis** | |
| 4.8 | Select additional analysis: `pH Analysis` (not in battery) | Analysis selected, added to selected list |
| 4.9 | Verify both battery and individual analysis selected | Summary shows battery name and individual analysis |
| 4.10 | Click "Next" to advance to Step 3 | Review step displayed |
| 5 | **Step 3: Review & Submit** | |
| 5.1 | Review Test Assignment section | Battery name and individual analysis displayed |
| 5.2 | Click "Submit" button | Form submits |
| 5.3 | Wait for API response | Success message displayed |
| 6 | **Verify Tests Created** | |
| 6.1 | Navigate to `/tests` route | Tests Management page loads |
| 6.2 | Filter by sample name | Tests for accessioned sample displayed |
| 6.3 | Verify tests created for battery analyses | Tests exist for each analysis in battery |
| 6.4 | Verify test sequence order | Tests ordered by battery sequence (if displayed) |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/samples/accession` called with:<br>- `battery_id`: UUID of selected battery<br>- `assigned_tests`: [UUID of individual analysis] (if provided) |
| **Backend Processing** | 1. Sample created with status "Received"<br>2. `_create_tests_for_sample()` function called<br>3. **Battery Processing**:<br>   - Verify battery exists and is active<br>   - Query `battery_analyses` ordered by `sequence`<br>   - For each analysis in battery (in sequence order):<br>     - Create `Test` record with:<br>       - `sample_id` = sample ID<br>       - `analysis_id` = battery analysis ID<br>       - `battery_id` = battery ID<br>       - `status` = "In Process"<br>       - `technician_id` = current user ID<br>4. **Individual Analysis Processing**:<br>   - Check if test already exists (from battery)<br>   - Create test only if not duplicate<br>   - Set `battery_id` = NULL for individual assignments<br>5. Commit transaction |
| **Test Records** | - Tests created for all analyses in battery (ordered by sequence)<br>- Each test has:<br>  - `battery_id` = battery UUID<br>  - `status` = "In Process"<br>  - `sample_id` = sample ID<br>  - `analysis_id` = analysis ID from battery<br>- Test for individual analysis (if provided) has:<br>  - `battery_id` = NULL<br>  - `status` = "In Process"<br>- All tests have audit fields set |
| **Sequence Order** | - Tests created in sequence order (1, 2, 3, etc.)<br> - Battery analyses queried with `.order_by(BatteryAnalysis.sequence)`<br> - Tests maintain sequence relationship via `battery_id` |
| **UI Feedback** | - Success message displayed<br>- Tests visible in Tests Management page<br>- Battery relationship visible (if displayed) |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Battery selected successfully | ✓ | ✗ |
| Tests created for all battery analyses | ✓ | ✗ |
| Tests created in sequence order | ✓ | ✗ |
| All tests have `battery_id` set | ✓ | ✗ |
| All tests have status "In Process" | ✓ | ✗ |
| Individual analysis test created (if provided) | ✓ | ✗ |
| No duplicate tests created | ✓ | ✗ |
| Audit fields set on all tests | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-7 (Assign Tests to Samples)
- **As a** Lab Technician
- **I want** to order tests during accessioning
- **So that** analyses are linked to samples
- **Acceptance Criteria**:
  - Select analysis_id → Create test instance with status 'In Process'
  - Analyses fields: method, turnaround_time, cost
  - API: POST `/tests`; RBAC: `test:assign`

### User Story US-8 (Test Status Management)
- **As a** Lab Technician or Lab Manager
- **I want** to update test statuses
- **So that** analysis progress is visible
- **Acceptance Criteria**:
  - Statuses: In Process, In Analysis, Complete (from lists)
  - Fields: review_date, test_date, technician_id
  - API: PATCH `/tests/{id}`; RBAC: `test:update`

### User Story US-23 (Test Battery Assignment)
- **As a** Lab Technician
- **I want** to assign a test battery to a sample during accessioning
- **So that** all analyses in the battery are automatically created as sequenced tests
- **Acceptance Criteria**:
  - Select test battery during accessioning workflow
  - System creates tests for all analyses in battery (ordered by sequence)
  - Optional analyses can be skipped (future enhancement)
  - Battery assignment can be combined with individual analysis assignments
  - API: POST `/samples/accession` with `battery_id`; auto-creates tests

### PRD Section 3.1 (Test Ordering)
- **Test Ordering**: Assign individual analyses or test batteries to samples at accessioning
- **Test Batteries**: Automatically create sequenced tests for all analyses in the battery
- **Test Instances**: Status: In Process, In Analysis, Complete

### Workflow Document (Stage 1: Test Assignment)
- **Option 1**: Assign individual analyses (select from cards, creates separate test instances)
- **Option 2**: Assign test battery (select battery, system creates tests for all analyses ordered by sequence)
- **Option 3**: Combine both (battery + individual analyses, prevents duplicates)
- **Status**: Tests created with "In Process" status

### UI Document (TestAssignmentStep.tsx, TestsManagement.tsx, TestForm.tsx)
- **TestAssignmentStep.tsx**: Step 2 of accessioning wizard
  - Analysis cards grid (name, method, turnaround time, cost)
  - Test battery dropdown (optional)
  - Selected analyses summary with chips
  - Card selection with blue border highlight
- **TestsManagement.tsx**: DataGrid listing tests with Edit button
- **TestForm.tsx**: Reusable form for editing test details
  - Fields: status, technician_id, test_date, review_date, custom_attributes
  - Handles edit mode, Formik/Yup validation
  - Permission-gated for `test:update`

### Technical Document (POST /tests, POST /samples/accession)
- **POST `/tests/assign`**: Assign individual test to sample
  - Request: `TestAssignmentRequest` (sample_id, analysis_id, test_date, technician_id)
  - Creates test with "In Process" status
- **POST `/samples/accession`**: Accession sample with test assignment
  - Request: `SampleAccessioningRequest` with `battery_id` and/or `assigned_tests`
  - `_create_tests_for_sample()` helper function:
    - Handles battery assignment (queries `battery_analyses` ordered by `sequence`)
    - Creates tests for each analysis in battery
    - Handles individual assignments (prevents duplicates)
    - All tests created with "In Process" status
- **PATCH `/tests/{id}`**: Update test (status, technician_id, test_date, review_date)
  - Requires `test:update` permission
  - Validates status exists
  - Updates audit fields

### Schema
- **`tests` table**:
  - `sample_id`: UUID FK to `samples.id`
  - `analysis_id`: UUID FK to `analyses.id`
  - `battery_id`: UUID FK to `test_batteries.id` (nullable)
  - `status`: UUID FK to `list_entries.id` (list_id: "test_status")
  - `technician_id`: UUID FK to `users.id` (nullable)
  - `test_date`: timestamp (nullable)
  - `review_date`: timestamp (nullable)
- **`battery_analyses` junction table**:
  - `battery_id`: UUID FK to `test_batteries.id`
  - `analysis_id`: UUID FK to `analyses.id`
  - `sequence`: Integer (>= 1) - Ordering within battery
  - `is_optional`: Boolean (default: False)

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-TEST-ASSIGN-001 | | | | |
| TC-TEST-STATUS-002 | | | | |
| TC-TEST-BATTERY-003 | | | | |

---

## Appendix: Sample Test Data

### Sample Names
- `SAMPLE-TEST-001` (for test assignment)
- `SAMPLE-BATTERY-001` (for battery assignment)

### Analyses
- `EPA Method 8080` (individual assignment)
- `pH Analysis` (individual assignment)

### Test Batteries
- `EPA 8080 Full` (battery with multiple analyses, e.g., Prep Analysis, Analytical Analysis, with sequence: 1, 2)

### Test Statuses
- `In Process` (initial status)
- `In Analysis` (target status for TC-002)
- `Complete` (final status)

### Technicians
- `Lab Tech User` (for technician assignment)

