# Workflow: Accessioning Through Reporting

## Overview

This document describes the complete workflow from sample accessioning through results reporting in the LIMS MVP. The workflow covers the lifecycle of a sample from initial receipt to final reporting, including test assignment, results entry, review, and status management.

## Workflow Stages

### Stage 1: Sample Accessioning

**Purpose**: Receive and register new samples into the system with all required metadata and test assignments.

**Actors**: Lab Technician

**Variation A: Single Sample Accessioning**

**Steps**:

1. **Sample Details Entry**
   - Enter sample identification: name (unique), description
   - Set dates: due_date (when results are due), received_date (when sample was received)
   - Select sample type from configured list (e.g., Blood, Urine, Tissue)
   - Select matrix from configured list (e.g., Serum, Plasma, Whole Blood)
   - Enter storage temperature (validated: -273.15 to 1000°C)
   - Select project (must have project access)
   - Optionally select client project (for grouping multiple projects)
   - Optionally select QC type (Sample, Positive Control, Negative Control, Matrix Spike, Duplicate, Blank)
   - Document any anomalies observed during inspection

2. **Container Assignment**
   - Select container type from admin-preconfigured types (e.g., tube, plate, well)
   - Enter container name/barcode (unique identifier)
   - Set position (row, column) for plate-based containers
   - Optionally enter concentration and amount with units
   - Container instance is created dynamically during accessioning

3. **Test Assignment**
   - Option 1: Assign individual analyses
     - Select one or more analyses from available list
     - Each analysis creates a separate test instance
   - Option 2: Assign test battery
     - Select a pre-configured test battery
     - System automatically creates tests for all analyses in battery (ordered by sequence)
     - Optional analyses in battery can be skipped (future enhancement)
   - Option 3: Combine both (battery + individual analyses)
     - System prevents duplicate test creation if analysis already exists from battery

4. **Double Entry Validation** (Optional)
   - Enable double-entry toggle
   - Re-enter sample name and sample type for verification
   - Validation occurs in review step before submission

5. **Review and Submit**
   - Review all entered information
   - Validate double-entry fields if enabled
   - Submit creates (via separate API calls):
     - Container instance (POST `/containers`)
     - Sample record (POST `/samples` or POST `/samples/accession`, status: "Received")
     - Content junction (POST `/contents`, links sample to container)
     - Test instances (via `/samples/accession` with battery_id/assigned_tests, status: "In Process")
   - **Note**: Frontend uses separate API calls for granular error handling. The `/samples/accession` endpoint can also create tests, but containers are created separately.

**Status Transitions**:
- Sample: Created with status "Received"
- Tests: Created with status "In Process"

**Post-Accessioning**:
- Optional: Create aliquots/derivatives from parent sample
- Sample becomes available for testing workflow

**Variation B: Bulk Sample Accessioning** (US-24)

**Steps**:

1. **Enable Bulk Mode**
   - Toggle "Bulk Accessioning Mode" switch in UI
   - Form switches to bulk mode layout

2. **Common Fields Entry**
   - Enter fields that apply to all samples:
     - Due date, received date
     - Sample type, matrix
     - Project, client project (optional)
     - Container type
     - QC type (optional)
     - Test battery and/or individual analyses
   - Configure auto-naming (optional):
     - Prefix (e.g., "SAMPLE-")
     - Start number (default: 1)

3. **Unique Fields Entry**
   - For each sample, enter unique data in table:
     - Sample name (optional if auto-naming enabled)
     - Client sample ID (optional)
     - Container name (required, unique)
     - Temperature (optional, overrides common)
     - Description (optional)
     - Anomalies (optional)
   - Add/remove rows as needed

4. **Test Assignment**
   - Assign test battery and/or individual analyses (applies to all samples)
   - System creates tests for all samples in bulk

5. **Review and Submit**
   - Review all samples in bulk view
   - Submit via POST `/samples/bulk-accession` to create all samples, containers, contents, and tests atomically
   - System validates:
     - No duplicate sample names
     - No duplicate container names
     - No duplicate client_sample_ids
   - All-or-nothing transaction (rolls back on any error)
   - **Note**: Bulk accessioning uses a single endpoint that creates everything in one transaction, unlike single sample accessioning which uses separate calls.

**Status Transitions**:
- All samples: Created with status "Received"
- All tests: Created with status "In Process"

**Use Cases**:
- Batch submissions from same client/project
- Multiple samples with shared metadata
- Efficient data entry for high-volume workflows

---

### Stage 2: Batch Creation and Organization

**Purpose**: Group containers/samples together for batch processing and results entry. Supports cross-project batching and automatic QC sample generation.

**Actors**: Lab Technician, Lab Manager

**Steps**:

1. **Create Batch**
   - Enter batch name and description
   - Select batch type from configured list (optional)
   - Set initial status: "Created"
   - Optionally set start_date and end_date

2. **Add Containers to Batch (Cross-Project Support)**
   - **Single-Project Batching**: Select containers from one project
   - **Cross-Project Batching** (US-26):
     - Select containers from multiple accessible projects
     - System auto-detects cross-project when containers from multiple projects are selected
     - **Compatibility Validation**: System validates that all samples share at least one common analysis (e.g., shared prep method like "EPA Method 8080 Prep")
     - If incompatible, system provides error with details:
       - List of projects involved
       - List of analyses found
       - Suggestion to use shared prep method
     - **RLS Access Check**: System verifies user has access to all projects via `has_project_access` SQL function
     - **Sub-Batch Support**: Option to specify divergent analyses that require separate sub-batches (future: child_batch_id FK)
   - For each container, optionally specify:
     - Position within batch
     - Notes
   - Containers can be added individually or in bulk via search/autocomplete

3. **Add QC Samples** (US-27)
   - **QC Addition**: Add one or more QC samples to be auto-generated with the batch
   - For each QC addition:
     - Select QC type from configured list (e.g., Blank, Blank Spike, Matrix Spike, Duplicate, Positive Control, Negative Control)
     - Optionally add notes
   - **Auto-Suggestions**: System suggests QC samples based on:
     - Batch size: Large batches (≥10 containers) suggest Blank, Blank Spike, Matrix Spike
     - Batch size: Medium batches (5-9 containers) suggest Blank, Matrix Spike
     - Batch size: Small batches (2-4 containers) suggest Blank
   - **QC Requirement**: Some batch types may require QC samples (configurable via `REQUIRE_QC_FOR_BATCH_TYPES` environment variable)
   - **Auto-Generation**: On batch creation, system automatically:
     - Creates QC sample records inheriting properties from first sample in batch:
       - project_id
       - sample_type
       - matrix
       - temperature
       - due_date
     - Sets qc_type field on sample
     - Creates container for QC sample (uses first container's type or default)
     - Links QC sample to container via Contents junction
     - Links QC container to batch via BatchContainer junction
   - All QC creation happens atomically within the batch creation transaction

4. **Batch Status Management**
   - **Created**: Initial state, containers and QC samples added
   - **In Process**: Batch is actively being processed
   - **Completed**: All results entered and ready for review

**Status Flow**:
```
Created → In Process → Completed
```

**Use Cases**:
- Group samples for plate-based analysis
- Organize samples by analysis run
- Track batch-level progress
- Cross-project batching for shared prep steps
- Automatic QC integration for quality assurance

**Technical Notes**:
- Cross-project compatibility validation checks for shared analyses across all samples
- QC samples are created in the same transaction as the batch (atomic operation)
- QC requirement enforcement is configurable per batch type via `REQUIRE_QC_FOR_BATCH_TYPES` env var
- All operations respect RLS (Row-Level Security) for project access
- Compatibility can be pre-validated via POST `/batches/validate-compatibility` endpoint

---

### Stage 3: Results Entry

**Purpose**: Enter test results for samples in a batch. Supports both single-test and bulk entry modes.

**Actors**: Lab Technician

**Variation A: Single-Test Entry (Traditional)**

**Steps**:

1. **Select Batch and Test**
   - Navigate to Results Management
   - Select a batch from list (filtered by status if needed)
   - View batch details: containers, samples, associated tests
   - QC samples are highlighted with warning indicators (from Sprint 6)
   - Select test (analysis) to enter results for

2. **Load Analytes**
   - System loads all analytes configured for the selected test's analysis
   - Analytes displayed in order specified by `display_order`
   - Each analyte shows:
     - Reported name
     - Data type (numeric, text, list)
     - Required flag
     - Validation rules (min/max values, significant figures)

3. **Enter Results**
   - For each sample in batch:
     - Enter raw_result (instrument reading or initial value)
     - Enter reported_result (final value to report)
     - Select qualifiers (if applicable, from configured list)
     - System validates:
       - Required fields are populated
       - Numeric values are valid numbers
       - Values are within configured ranges
       - Significant figures are respected (warning if exceeded)

4. **Save Results**
   - System validates all results before saving
   - Creates result records for each sample-analyte combination
   - Updates test status to "In Analysis" (if not already)
   - Records entry_date and entered_by (current user)

**Variation B: Batch Results Entry (US-28: Batch Results Entry)**

**Steps**:

1. **Select Batch**
   - Navigate to Results Management
   - Select a batch from list
   - View batch details with QC indicators (warning icons for QC samples)
   - Batch results entry is the default mode (no toggle needed)

2. **Batch Entry Interface**
   - System displays tabular interface:
     - **Rows**: All tests in the batch (one row per test, which is one per sample-analysis combination)
     - **Columns**: Sample name, Test name, Position, and all analytes (one column per analyte)
   - QC sample rows are highlighted with warning background color
   - Each analyte column header shows:
     - Reported name
     - Required indicator (if applicable)
     - Min/max values (for numeric analytes)
     - Data type (numeric/text/list)

3. **Enter Results for Batch**
   - Edit cells directly in the table:
     - Raw result field (validated in real-time)
     - Reported result field
     - Qualifiers dropdown (if applicable)
     - Notes field (optional)
   - **Real-time Validation**:
     - Inline error messages for invalid values
     - Range validation (min/max)
     - Data type validation (numeric vs text)
     - Required field validation
   - Validation errors displayed at top of table with row details
   - Can enter results for multiple tests/analytes in single submission

4. **QC Validation**
   - System checks QC samples for failures:
     - Missing results for QC tests
     - Results outside expected ranges (future: configurable QC acceptance criteria)
   - **Configurable QC Handling**:
     - If `FAIL_QC_BLOCKS_BATCH=true`: Submission blocked on QC failures
     - If `FAIL_QC_BLOCKS_BATCH=false`: Warning shown but submission allowed
   - QC failures displayed in error alert with details

5. **Submit Results**
   - Click "Submit Results" button
   - System validates all results before submission:
     - Required analytes have values
     - Numeric values are valid numbers
     - Values are within configured ranges
     - All test_ids exist in batch
   - If validation passes:
     - Creates/updates result records atomically in transaction
     - Updates test statuses to "Complete" when all analytes entered for that test
     - Checks if all tests in batch are complete
     - **Auto-updates batch status to "Completed"** if all tests complete
     - Sets batch end_date to current timestamp
   - If validation fails:
     - Transaction rolled back
     - Detailed error messages per test/analyte returned
     - User can fix errors and resubmit
   - If QC failures detected:
     - If `FAIL_QC_BLOCKS_BATCH=true`: Submission blocked, error shown
     - If `FAIL_QC_BLOCKS_BATCH=false`: Warning shown, submission allowed

**Validation Rules**:
- Required analytes must have values
- Numeric analytes must be valid numbers
- Values must be within configured min/max ranges
- Significant figures warnings (not blocking)
- QC validation (configurable blocking)

**Status Transitions**:
- Test: "In Process" → "Complete" (when all analytes have results)
- Batch: "Created" or "In Process" → "Completed" (when all tests in batch are complete)
- Batch end_date set automatically when batch status changes to "Completed"

**Technical Notes**:
- Batch results entry uses POST `/results/batch` endpoint (US-28)
- All results created/updated in single transaction
- Test statuses updated to "Complete" when all analytes entered
- Batch status update occurs automatically after successful submission (when all tests complete)
- QC validation checks for missing results and out-of-range values
- QC blocking configurable via `FAIL_QC_BLOCKS_BATCH` env var
- Real-time validation provides immediate feedback
- Validation errors returned with per-test/analyte details

---

### Stage 4: Results Review

**Purpose**: Review and approve test results before reporting.

**Actors**: Lab Manager

**Steps**:

1. **Access Test for Review**
   - Navigate to test details or batch view
   - View all results for the test
   - Review sample information and test metadata

2. **Review Results**
   - Verify all required analytes have results
   - Check result values against expected ranges
   - Review qualifiers and notes
   - Verify calculations (if applicable, post-MVP)

3. **Approve Test**
   - Set review_date (current timestamp)
   - Update test status to "Complete"
   - System checks if all tests for sample are complete
   - If all tests complete, updates sample status to "Reviewed"

**Status Transitions**:
- Test: "In Analysis" → "Complete"
- Sample: "Testing Complete" → "Reviewed" (when all tests complete)

**Business Rules**:
- Only Lab Managers (with `result:review` permission) can review
- Test must have all required results entered before review
- Sample status updates automatically when all tests are reviewed

---

### Stage 5: Reporting

**Purpose**: Mark sample as reported to client.

**Actors**: Lab Manager, Administrator

**Steps**:

1. **Verify Sample Readiness**
   - Verify sample status is "Reviewed"
   - Confirm all tests are "Complete"
   - Verify all required results are present

2. **Mark as Reported**
   - Update sample status to "Reported"
   - Set report_date (current timestamp)
   - Optionally generate report (post-MVP feature)

**Status Transitions**:
- Sample: "Reviewed" → "Reported"

**Final State**:
- Sample lifecycle complete
- All tests complete and reviewed
- Results available for client viewing (if client user)

---

## Complete Status Flow

### Sample Status Flow
```
Received → Available for Testing → Testing Complete → Reviewed → Reported
```

**Status Definitions**:
- **Received**: Sample accessioned, entered into system
- **Available for Testing**: Sample ready for analysis (set during review/release)
- **Testing Complete**: All tests finished
- **Reviewed**: Results reviewed by Lab Manager
- **Reported**: Results reported to client

### Test Status Flow
```
In Process → In Analysis → Complete
```

**Status Definitions**:
- **In Process**: Test assigned, ready for analysis
- **In Analysis**: Results being entered
- **Complete**: Results reviewed and approved

### Batch Status Flow
```
Created → In Process → Completed
```

**Status Definitions**:
- **Created**: Batch created, containers added
- **In Process**: Batch actively being processed
- **Completed**: All results entered and ready for review

---

## Workflow Variations

### Variation 1: Aliquot/Derivative Creation
- After accessioning, create aliquots or derivatives
- Aliquot: Same sample, new container
- Derivative: New sample, new container, inherits project/client
- Both inherit from parent sample

### Variation 2: Test Battery Assignment
- Assign test battery during accessioning
- System creates all tests automatically in sequence order
- Optional analyses can be skipped (future enhancement)

### Variation 3: Individual Test Assignment
- Assign tests individually after accessioning
- Use `/tests/assign` endpoint
- Tests created with "In Process" status

### Variation 4: Pooled Samples
- Multiple samples in single container
- Concentration/amount calculations using units multipliers
- Volume calculated from concentration and amount

---

## Permissions Required

### Sample Accessioning
- `sample:create`: Create samples
- `test:assign`: Assign tests (implicit in accessioning)
- Project access: User must have access to selected project

### Results Entry
- `result:enter`: Enter results
- `batch:read`: View batches

### Results Review
- `result:review`: Review and approve results
- `test:update`: Update test status

### Reporting
- `sample:update`: Update sample status
- Typically restricted to Lab Manager or Administrator

---

## Data Relationships

```
Sample
  ├─ Container (via Contents junction)
  ├─ Project
  ├─ Tests
  │   ├─ Analysis
  │   ├─ Results
  │   │   └─ Analyte
  │   └─ Test Battery (optional)
  └─ Status (from lists)
```

**Key Relationships**:
- Sample → Container: Many-to-many via Contents
- Sample → Tests: One-to-many
- Test → Results: One-to-many
- Test → Analysis: Many-to-one
- Result → Analyte: Many-to-one
- Batch → Containers: Many-to-many via BatchContainers

---

## Error Handling

### Accessioning Errors
- Duplicate sample name: 400 Bad Request
- Invalid project access: 403 Forbidden
- Missing required status: 400 Bad Request
- Invalid container type: 400 Bad Request

### Results Entry Errors
- Validation failures: 400 Bad Request with error details
- Missing required analytes: Validation error
- Out of range values: Validation error
- Invalid test access: 403 Forbidden

### Review Errors
- Test not ready: 400 Bad Request
- Insufficient permissions: 403 Forbidden
- Missing results: Validation error

---

## Audit Trail

All workflow steps maintain audit information:
- `created_at`: Timestamp of creation
- `created_by`: User who created
- `modified_at`: Timestamp of last modification
- `modified_by`: User who last modified

**Audited Actions**:
- Sample creation and updates
- Test creation and status changes
- Result entry and updates
- Review actions
- Status transitions

---

## Notes

- All status values come from configurable lists (admin-managed)
- Container types must be pre-configured by administrators
- Test batteries must be configured before use
- Analysis-analyte rules must be configured for validation
- Units must be configured for concentration/amount conversions
- Project access is enforced at all workflow stages

