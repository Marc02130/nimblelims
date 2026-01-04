# UAT Scripts: Single Sample Accessioning

## Overview

This document contains User Acceptance Testing (UAT) scripts for single sample accessioning in NimbleLIMS. These scripts validate the core accessioning workflow as defined in:

- **User Stories**: US-1 (Sample Accessioning), US-5 (Container Management), US-7 (Assign Tests to Samples)
- **PRD**: Section 3.1 (Sample Tracking)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stage 1: Sample Accessioning)
- **UI Document**: `ui-accessioning-to-reporting.md` (AccessioningForm.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (POST /samples/accession)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Sample types list entries
  - Sample status list entries (including "Received")
  - Matrix types list entries
  - Container types (at least one pre-configured)
  - Units for concentration/amount
  - At least one project
  - At least one analysis for test assignment
- Test user accounts:
  - Lab Technician with `sample:create` permission
  - Lab Technician without project access (for RLS test)

---

## Test Case 1: Happy Path - Full Accessioning with Container and Test Assignment

### Test Case ID
TC-ACC-001

### Description
Complete single sample accessioning workflow with all required fields, container assignment, and test assignment.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to at least one project |
| **Container Types** | At least one container type configured in system |
| **Analyses** | At least one analysis available for assignment |
| **Sample Status** | "Received" status exists in `sample_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads with 3-step wizard (Sample Details, Test Assignment, Review & Submit) |
| 2 | Verify user is logged in as Lab Technician | User context shows Lab Technician role with `sample:create` permission |
| 3 | **Step 1: Sample Details** | |
| 3.1 | Enter Sample Name: `SAMPLE-TC-001-2025` | Field accepts input, no validation errors |
| 3.2 | Enter Description: `Test sample for UAT TC-ACC-001` | Field accepts input |
| 3.3 | Select Due Date: `2025-02-15` (using DatePicker) | Date selected, displayed correctly |
| 3.4 | Select Received Date: `2025-01-15` (defaults to today) | Date selected, displayed correctly |
| 3.5 | Select Sample Type: `Blood` (from dropdown) | Option selected from `sample_types` list |
| 3.6 | Verify Status: `Received` (pre-selected or selectable) | Status available from `sample_status` list |
| 3.7 | Select Matrix: `Serum` (from dropdown) | Option selected from `matrix_types` list |
| 3.8 | Enter Temperature: `4.0` | Field accepts numeric input, validated range (-273.15 to 1000) |
| 3.9 | Select Project: `Project Alpha` (from filtered dropdown) | Only projects user has access to are shown |
| 3.10 | Select QC Type: `Sample` (optional, from dropdown) | Option selected from `qc_types` list |
| 3.11 | Enter Anomalies/Notes: `No anomalies observed` | Field accepts multiline text |
| 3.12 | **Container Information Section** | |
| 3.13 | Select Container Type: `Tube (1x1)` (from admin-configured types) | Container type dropdown shows pre-configured types |
| 3.14 | Enter Container Name/Barcode: `CONTAINER-TC-001` | Field accepts input, unique identifier |
| 3.15 | Verify Row: `1` (default) | Default value set |
| 3.16 | Verify Column: `1` (default) | Default value set |
| 3.17 | Enter Concentration: `10.5` | Field accepts numeric input |
| 3.18 | Select Concentration Units: `mg/L` (from units filtered by type: "concentration") | Units dropdown filtered by type |
| 3.19 | Enter Amount: `5.0` | Field accepts numeric input |
| 3.20 | Select Amount Units: `mL` (from units filtered by type: "volume") | Units dropdown filtered by type |
| 3.21 | Click "Next" button | Form validates, advances to Step 2 (Test Assignment) if valid |
| 4 | **Step 2: Test Assignment** | |
| 4.1 | Verify analysis cards are displayed | Grid of analysis cards shows available analyses |
| 4.2 | Select Analysis: `EPA Method 8080` (click card or checkbox) | Card selected, shows blue border (2px), added to selected list |
| 4.3 | Verify Selected Analyses Summary | Summary shows count: "1 analysis selected", chip displays selected analysis name |
| 4.4 | Click "Next" button | Advances to Step 3 (Review & Submit) |
| 5 | **Step 3: Review & Submit** | |
| 5.1 | Review Sample Information section | All entered sample details displayed correctly |
| 5.2 | Review Container Information section | All container details displayed correctly |
| 5.3 | Review Test Assignment section | Selected analysis displayed: "EPA Method 8080" |
| 5.4 | Click "Submit" button | Form submits, loading spinner shown in button |
| 5.5 | Wait for API response | Success message displayed: "Sample accessioned successfully" |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Calls** | 1. POST `/containers` creates container instance<br>2. POST `/samples/accession` creates sample with test assignment<br>3. POST `/contents` links sample to container |
| **Sample Record** | - Sample created with status: `"Received"`<br>- All fields saved correctly (name, description, dates, type, matrix, temperature, project_id)<br>- Audit fields set: `created_by` = current user ID, `created_at` = current timestamp |
| **Container Record** | - Container created with type, name, position (row=1, column=1)<br>- Concentration and amount with units saved<br>- Audit fields set |
| **Content Junction** | - Sample linked to container via `contents` table<br>- Concentration and amount preserved |
| **Test Records** | - Test created for "EPA Method 8080" analysis<br>- Test status: `"In Process"`<br>- Test linked to sample via `sample_id`<br>- Audit fields set |
| **UI Feedback** | - Success alert displayed<br>- Form resets to initial state<br>- Optional: Aliquot/Derivative dialog opens |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Sample created with correct data | ✓ | ✗ |
| Sample status = "Received" | ✓ | ✗ |
| Container created and linked | ✓ | ✗ |
| Test created with status "In Process" | ✓ | ✗ |
| Audit fields (`created_by`, `created_at`) set | ✓ | ✗ |
| No validation errors | ✓ | ✗ |
| Success message displayed | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Double-Entry Validation

### Test Case ID
TC-ACC-002

### Description
Validate double-entry verification feature for sample name and sample type during accessioning.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to at least one project |
| **Container Types** | At least one container type configured |
| **Analyses** | At least one analysis available |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/accessioning` route | Accessioning form loads |
| 2 | **Step 1: Sample Details** | |
| 2.1 | Enter Sample Name: `SAMPLE-DE-001` | Field accepts input |
| 2.2 | Select Sample Type: `Blood` | Option selected |
| 2.3 | Fill all other required fields (due_date, received_date, matrix, temperature, project, container type, container name) | All fields filled |
| 2.4 | **Enable Double Entry Validation** | |
| 2.5 | Toggle "Enable Double Entry Validation" switch to ON | Verification fields appear: "Verify Sample Name" and "Verify Sample Type" |
| 2.6 | Enter Verify Sample Name: `SAMPLE-DE-001` (matches original) | Field accepts input, no error |
| 2.7 | Select Verify Sample Type: `Blood` (matches original) | Option selected, no error |
| 2.8 | Click "Next" button | Advances to Step 2 |
| 3 | **Step 2: Test Assignment** | |
| 3.1 | Select at least one analysis | Analysis selected |
| 3.2 | Click "Next" button | Advances to Step 3 |
| 4 | **Step 3: Review & Submit** | |
| 4.1 | Review Double Entry Verification section | Verification fields displayed with entered values |
| 4.2 | Verify validation logic | System compares `name_verification` with `name`, `sample_type_verification` with `sample_type` |
| 4.3 | Click "Submit" button | Form validates double-entry fields |
| 4.4 | Wait for API response | Success message displayed (if validation passes) |

### Expected Results - Matching Values

| Category | Expected Outcome |
|----------|------------------|
| **Validation** | - Double-entry fields match original values<br>- No validation errors displayed<br>- Submit button enabled |
| **API Call** | POST `/samples/accession` includes `double_entry_required: true` |
| **Sample Creation** | Sample created successfully with all data |

### Test Steps - Mismatched Values (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5 | Return to Step 1 (or start new form) | Form loads |
| 5.1 | Enter Sample Name: `SAMPLE-DE-002` | Field accepts input |
| 5.2 | Select Sample Type: `Urine` | Option selected |
| 5.3 | Fill all other required fields | All fields filled |
| 5.4 | Enable Double Entry Validation | Toggle ON |
| 5.5 | Enter Verify Sample Name: `SAMPLE-DE-003` (mismatch) | Field accepts input |
| 5.6 | Select Verify Sample Type: `Blood` (mismatch) | Option selected |
| 5.7 | Complete Steps 2 and 3 | Navigate to Review step |
| 5.8 | Click "Submit" button | Validation error displayed: "Sample name verification does not match" and/or "Sample type verification does not match" |
| 5.9 | Verify Submit button disabled | Button remains disabled until errors resolved |

### Expected Results - Mismatched Values

| Category | Expected Outcome |
|----------|------------------|
| **Validation Errors** | - Error messages displayed for mismatched fields<br>- Submit button disabled<br>- Errors shown in red below fields or in summary |
| **API Call** | POST `/samples/accession` NOT called (validation prevents submission) |
| **Sample Creation** | No sample created |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Double-entry fields appear when toggle enabled | ✓ | ✗ |
| Matching values allow submission | ✓ | ✗ |
| Mismatched values prevent submission | ✓ | ✗ |
| Clear error messages for mismatches | ✓ | ✗ |
| Submit button disabled on validation errors | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Error Case - Invalid Project Access via RLS

### Test Case ID
TC-ACC-003

### Description
Verify Row-Level Security (RLS) prevents sample accessioning when user lacks project access.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User does NOT have access to "Project Beta" (not in `project_users` junction) |
| **Container Types** | At least one container type configured |
| **Analyses** | At least one analysis available |
| **Test Project** | "Project Beta" exists but user has no access |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician without access to "Project Beta" | User authenticated, role verified |
| 2 | Navigate to `/accessioning` route | Accessioning form loads |
| 3 | **Step 1: Sample Details** | |
| 3.1 | Enter Sample Name: `SAMPLE-RLS-001` | Field accepts input |
| 3.2 | Fill all required fields (due_date, received_date, sample_type, status, matrix, temperature) | All fields filled |
| 3.3 | **Attempt to select project** | |
| 3.4 | Open Project dropdown | Dropdown shows only projects user has access to |
| 3.5 | Verify "Project Beta" is NOT in dropdown | "Project Beta" not listed (RLS filtering) |
| 3.6 | Select an accessible project: `Project Alpha` | Project selected |
| 3.7 | Fill container information (type, name) | Container details entered |
| 3.8 | Complete Steps 2 and 3 | Navigate through test assignment and review |
| 3.9 | Click "Submit" button | Form submits with accessible project |
| 4 | **Direct API Test (Bypass UI)** | |
| 4.1 | Use API client (e.g., Postman, curl) to send POST `/samples/accession` | API request prepared |
| 4.2 | Set `project_id` to UUID of "Project Beta" (user has no access) | Request body includes inaccessible project |
| 4.3 | Include valid JWT token for Lab Technician | Authorization header set |
| 4.4 | Send request | API processes request |
| 4.5 | Verify response | HTTP 403 Forbidden returned |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **UI Filtering** | Project dropdown only shows projects from `project_users` where `user_id` = current user |
| **API Response** | HTTP 403 Forbidden with message: `"Access denied: insufficient project permissions"` |
| **Backend Check** | `accession_sample()` function checks `project_users` junction:<br>- If user is not Administrator<br>- Query `ProjectUser` for `project_id` and `user_id`<br>- Raise 403 if no access found |
| **Sample Creation** | No sample created (transaction rolled back) |
| **Error Handling** | Error message displayed in UI (if attempted via UI manipulation) |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Project dropdown filtered by RLS | ✓ | ✗ |
| API returns 403 for inaccessible project | ✓ | ✗ |
| Error message is clear and informative | ✓ | ✗ |
| No sample created for inaccessible project | ✓ | ✗ |
| Accessible project allows creation | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Stories
- **US-1**: Sample Accessioning - Form fields, test assignment, double-entry option, review step
- **US-5**: Container Management - Container types, instances, hierarchical relationships
- **US-7**: Assign Tests to Samples - Individual analyses or test batteries

### PRD Section 3.1 (Sample Tracking)
- Accessioning: Receive, inspect, note anomalies, double-entry option, assign tests, review/release
- Status management: Received, Available for Testing, Testing Complete, Reviewed, Reported
- Containers: Hierarchical types, contents linking samples with concentration/amount

### Workflow Document (Stage 1)
- **Variation A: Single Sample Accessioning**
  - Sample Details Entry (name, dates, type, matrix, temperature, project, QC type, anomalies, custom fields)
  - Container Assignment (type, name/barcode, position, concentration/amount with units)
  - Test Assignment (individual analyses or test battery)
  - Double Entry Validation (optional toggle)
  - Review and Submit (creates container, sample, content junction, tests)

### UI Document (AccessioningForm.tsx)
- Multi-step wizard: Sample Details → Test Assignment → Review & Submit
- Step 1: Sample Information and Container Information sections
- Double-entry toggle with verification fields
- Step 2: Analysis card selection
- Step 3: Review with double-entry validation

### Technical Document (POST /samples/accession)
- **Request Schema**: `SampleAccessioningRequest` with required/optional fields
- **Processing Steps**:
  1. Access control check (`sample:create` permission, project access via `project_users`)
  2. Custom attributes validation (if provided)
  3. Client project validation (if provided)
  4. Status assignment ("Received")
  5. Sample creation with audit fields
  6. Test assignment (battery or individual analyses)
  7. Transaction commit
- **Error Handling**: 400 (invalid data), 403 (insufficient permissions), 500 (database errors)

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-ACC-001 | | | | |
| TC-ACC-002 | | | | |
| TC-ACC-003 | | | | |

---

## Appendix: Sample Test Data

### Sample Names
- `SAMPLE-TC-001-2025` (Happy path)
- `SAMPLE-DE-001` (Double-entry matching)
- `SAMPLE-DE-002` (Double-entry mismatch)
- `SAMPLE-RLS-001` (RLS test)

### Container Names
- `CONTAINER-TC-001` (Happy path)

### Projects
- `Project Alpha` (accessible)
- `Project Beta` (inaccessible for RLS test)

### Sample Types
- `Blood`
- `Urine`

### Matrix Types
- `Serum`
- `Plasma`

### Analyses
- `EPA Method 8080`

### Container Types
- `Tube (1x1)`

### Units
- Concentration: `mg/L`
- Amount: `mL`

