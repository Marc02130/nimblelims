# UAT Scripts: Batch Creation and Management

## Overview

This document contains User Acceptance Testing (UAT) scripts for batch creation and management in NimbleLIMS. These scripts validate the batch workflows as defined in:

- **User Stories**: US-9 (Batch-Based Results Entry), US-10 (Results Review), US-26 (Cross-Project Batching), US-27 (Add QC Samples at Batch Creation)
- **PRD**: Section 3.1 (Batches/Plates)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stage 2: Batch Creation and Organization)
- **UI Document**: `ui-accessioning-to-reporting.md` (ResultsManagement.tsx, BatchFormEnhanced.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (POST /batches)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Batch status list entries: "Created", "In Process", "Completed"
  - Batch types (optional)
  - QC types: Blank, Positive Control, Negative Control, Matrix Spike, Duplicate
  - At least two containers with samples (for basic batch)
  - Containers from multiple projects (for cross-project test)
  - At least one analysis (for compatibility validation)
- Test user accounts:
  - Lab Technician with `batch:manage` permission and access to multiple projects

---

## Test Case 1: Basic Batch Creation - Add Containers

### Test Case ID
TC-BATCH-BASIC-001

### Description
Create a basic batch by adding containers from a single project.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `batch:manage` |
| **Project Access** | User has access to at least one project |
| **Containers Available** | At least two containers with samples exist in accessible project |
| **Status Available** | "Created" status exists in `batch_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to batch creation page (e.g., `/batches` or via Results Management) | Batch creation form loads |
| 2 | **Enter Batch Information** | |
| 2.1 | Enter Batch Name: `BATCH-001` | Field accepts input |
| 2.2 | Enter Description: `Basic batch for UAT testing` | Field accepts input |
| 2.3 | Select Batch Type: `Standard Batch` (optional, from dropdown) | Type selected if available |
| 2.4 | Verify Status: `Created` (pre-selected or selectable) | Status available from `batch_status` list |
| 2.5 | Optionally set Start Date: `2025-01-20` | Date selected using DatePicker |
| 3 | **Add Containers to Batch** | |
| 3.1 | Locate "Containers" section | Section visible with container selection interface |
| 3.2 | Click "Add Container" or search for containers | Container selection dialog or autocomplete opens |
| 3.3 | Search/Select Container: `CONTAINER-001` | Container selected, added to selected containers list |
| 3.4 | Search/Select Container: `CONTAINER-002` | Second container selected, added to list |
| 3.5 | Verify selected containers displayed | Both containers shown in selected containers list with details (name, project, sample count) |
| 4 | Click "Create Batch" or "Submit" button | Form submits, loading spinner shown |
| 5 | Wait for API response | Success message displayed or batch details view opens |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/batches` called with:<br>- `name`: "BATCH-001"<br>- `description`: "Basic batch for UAT testing"<br>- `status`: UUID of "Created" status<br>- `container_ids`: [UUID of CONTAINER-001, UUID of CONTAINER-002] |
| **Backend Processing** | 1. Verify containers exist and are active<br>2. Get all samples in containers via `Contents` junction<br>3. Get all projects for samples<br>4. Check RLS access (single project in this case)<br>5. Validate compatibility (samples share common analysis)<br>6. Create batch record<br>7. Add containers to batch via `BatchContainer` junction<br>8. Commit transaction |
| **Batch Record** | - Batch created with:<br>  - `name`: "BATCH-001"<br>  - `description`: "Basic batch for UAT testing"<br>  - `status` = "Created" status UUID<br>  - `type` = batch type UUID (if provided)<br>  - `start_date` = selected date (if provided)<br>- Audit fields set: `created_by`, `created_at` |
| **BatchContainer Records** | - Two `BatchContainer` junction records created:<br>  - `batch_id` = batch UUID<br>  - `container_id` = CONTAINER-001 UUID<br>  - `container_id` = CONTAINER-002 UUID<br>- Audit fields set |
| **UI Feedback** | - Success message or batch details view opens<br>- Batch visible in batch list<br>- Containers visible in batch details view |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Batch created successfully | ✓ | ✗ |
| Batch status = "Created" | ✓ | ✗ |
| Containers added to batch | ✓ | ✗ |
| BatchContainer junction records created | ✓ | ✗ |
| Audit fields set | ✓ | ✗ |
| Batch visible in list view | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Cross-Project Batching - Compatibility Check

### Test Case ID
TC-BATCH-CROSS-PROJECT-002

### Description
Create a batch with containers from multiple projects, verifying compatibility validation and RLS access.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `batch:manage` |
| **Project Access** | User has access to at least two projects (e.g., "Project Alpha", "Project Beta") |
| **Containers Available** | At least one container with sample in "Project Alpha"<br>At least one container with sample in "Project Beta" |
| **Compatible Analyses** | Samples in both projects share at least one common analysis (e.g., "EPA Method 8080 Prep") |
| **Tests Assigned** | Samples have tests assigned with shared analysis |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to batch creation page | Batch creation form loads |
| 2 | **Enter Batch Information** | |
| 2.1 | Enter Batch Name: `BATCH-CROSS-001` | Field accepts input |
| 2.2 | Enter Description: `Cross-project batch for shared prep` | Field accepts input |
| 2.3 | Select Status: `Created` | Status selected |
| 3 | **Add Containers from Multiple Projects** | |
| 3.1 | Locate "Containers" section | Section visible |
| 3.2 | Search/Select Container from "Project Alpha": `CONTAINER-ALPHA-001` | Container selected, project name visible |
| 3.3 | Search/Select Container from "Project Beta": `CONTAINER-BETA-001` | Container selected, project name visible |
| 3.4 | Verify both containers in selected list | Both containers shown with their respective project names |
| 3.5 | **Verify Cross-Project Detection** | System auto-detects cross-project (multiple projects in selected containers) |
| 4 | **Validate Compatibility** (Optional UI feature) | |
| 4.1 | Click "Validate Compatibility" button (if available) | Compatibility validation runs |
| 4.2 | Verify compatibility result | Result shows: "Compatible" with common analyses listed (e.g., "EPA Method 8080 Prep") |
| 5 | Click "Create Batch" button | Form submits |
| 6 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/batches` called with:<br>- `name`: "BATCH-CROSS-001"<br>- `container_ids`: [UUID of CONTAINER-ALPHA-001, UUID of CONTAINER-BETA-001]<br>- `cross_project`: true (auto-detected) |
| **Backend Processing** | 1. Verify all containers exist<br>2. Get all samples from containers<br>3. Get all projects for samples (Project Alpha, Project Beta)<br>4. **RLS Access Check**:<br>   - Use `has_project_access()` SQL function for each project<br>   - Verify user has access to all projects<br>   - Return 403 if any project inaccessible<br>5. **Compatibility Validation**:<br>   - Get all tests for samples<br>   - Group tests by sample to find common analyses<br>   - Verify samples share at least one common analysis<br>   - Return 400 with details if incompatible<br>6. Create batch record<br>7. Add containers to batch<br>8. Commit transaction |
| **Batch Record** | - Batch created with cross-project flag (if stored)<br>- Status = "Created"<br>- Audit fields set |
| **BatchContainer Records** | - Junction records created for both containers<br>- Containers from different projects linked to same batch |
| **Compatibility Validation** | - Validation passes (samples share common analysis)<br>- Common analyses identified (e.g., "EPA Method 8080 Prep")<br>- No error returned |

### Test Steps - Incompatible Samples (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Incompatible Samples** | |
| 7.1 | Start new batch creation | Form loads |
| 7.2 | Select containers with samples that have NO shared analyses | Containers selected |
| 7.3 | Click "Create Batch" | Form submits |
| 7.4 | Verify error response | HTTP 400 Bad Request returned with error:<br>- "Incompatible samples: no shared analyses found"<br>- Details include: projects list, analyses list, suggestion message |

### Expected Results - Incompatible Samples

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 400 Bad Request<br>- Error message: "Incompatible samples: no shared analyses found"<br>- Details object includes:<br>  - `projects`: List of project IDs<br>  - `analyses`: List of analysis names found<br>  - `suggestion`: "Samples must share at least one common analysis (e.g., prep method) for cross-project batching" |
| **Batch Creation** | No batch created (validation prevents creation) |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Cross-project auto-detected | ✓ | ✗ |
| RLS access checked for all projects | ✓ | ✗ |
| Compatibility validation passes for compatible samples | ✓ | ✗ |
| Error returned for incompatible samples | ✓ | ✗ |
| Batch created successfully (compatible case) | ✓ | ✗ |
| Containers from multiple projects linked | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Batch Creation with QC Addition

### Test Case ID
TC-BATCH-QC-003

### Description
Create a batch with QC samples auto-generated during batch creation.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `batch:manage` |
| **Project Access** | User has access to at least one project |
| **Containers Available** | At least one container with sample exists |
| **QC Types Available** | QC types exist: Blank, Positive Control, Negative Control, Matrix Spike |
| **Container Types** | At least one container type configured (for QC container creation) |
| **Status Available** | "Received" status exists in `sample_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to batch creation page | Batch creation form loads |
| 2 | **Enter Batch Information** | |
| 2.1 | Enter Batch Name: `BATCH-QC-001` | Field accepts input |
| 2.2 | Enter Description: `Batch with QC samples` | Field accepts input |
| 2.3 | Select Status: `Created` | Status selected |
| 3 | **Add Containers** | |
| 3.1 | Select Container: `CONTAINER-001` | Container selected |
| 4 | **Add QC Samples** | |
| 4.1 | Locate "QC Samples" section | Section visible with "Add QC" button |
| 4.2 | Click "Add QC" button | QC addition form/dialog opens |
| 4.3 | Select QC Type: `Blank` | QC type selected from dropdown |
| 4.4 | Enter Notes (optional): `Blank control for batch` | Field accepts input |
| 4.5 | Click "Add" or "Save" | QC addition added to list |
| 4.6 | Click "Add QC" button again | Second QC addition form opens |
| 4.7 | Select QC Type: `Matrix Spike` | QC type selected |
| 4.8 | Click "Add" | Second QC addition added |
| 4.9 | Verify QC additions in list | Both QC additions displayed (Blank, Matrix Spike) |
| 5 | Click "Create Batch" button | Form submits, loading spinner shown |
| 6 | Wait for API response | Success message displayed |
| 7 | **Verify QC Samples Created** | |
| 7.1 | Navigate to batch details view | Batch details displayed |
| 7.2 | View containers in batch | QC containers visible in batch |
| 7.3 | Verify QC samples | QC samples visible with QC type indicators |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/batches` called with:<br>- `name`: "BATCH-QC-001"<br>- `container_ids`: [UUID of CONTAINER-001]<br>- `qc_additions`: [<br>  {`qc_type`: UUID of "Blank", `notes`: "Blank control for batch"},<br>  {`qc_type`: UUID of "Matrix Spike", `notes`: null}<br>] |
| **Backend Processing** | 1. Create batch record<br>2. Add containers to batch<br>3. **QC Sample Generation** (for each QC addition):<br>   - Get first sample from first container for property inheritance<br>   - Validate QC type exists<br>   - Create QC sample:<br>     - `name`: "QC-BATCH-QC-001-1", "QC-BATCH-QC-001-2"<br>     - `description`: "QC sample (Blank): Blank control for batch", etc.<br>     - Inherit: `project_id`, `sample_type`, `matrix`, `temperature`, `due_date` from first sample<br>     - Set `qc_type` = QC type UUID<br>     - Set `status` = "Received"<br>   - Create container for QC sample (uses first container's type or default)<br>   - Link QC sample to container via `Contents` junction<br>   - Link QC container to batch via `BatchContainer` junction<br>4. Commit transaction atomically |
| **Batch Record** | - Batch created with status "Created"<br>- Audit fields set |
| **QC Sample Records** | - Two QC samples created:<br>  - "QC-BATCH-QC-001-1" (Blank)<br>  - "QC-BATCH-QC-001-2" (Matrix Spike)<br>- Each inherits properties from first sample<br>- Each has `qc_type` set correctly<br>- Each has status "Received" |
| **QC Container Records** | - Two containers created for QC samples<br>  - "QC-BATCH-QC-001-1-Container"<br>  - "QC-BATCH-QC-001-2-Container"<br>- Each linked to QC sample via `Contents`<br>- Each linked to batch via `BatchContainer` |
| **UI Feedback** | - Success message displayed<br>- Batch visible in list<br>- QC samples visible in batch with QC indicators<br>- QC containers visible in batch details |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Batch created successfully | ✓ | ✗ |
| QC samples auto-generated | ✓ | ✗ |
| QC samples inherit properties from first sample | ✓ | ✗ |
| QC type set correctly on samples | ✓ | ✗ |
| QC containers created and linked | ✓ | ✗ |
| QC containers added to batch | ✓ | ✗ |
| All operations atomic (transaction) | ✓ | ✗ |
| QC samples visible in batch view | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-9 (Batch-Based Results Entry)
- **As a** Lab Technician
- **I want** to enter results for a batch of containers
- **So that** analytes are populated efficiently
- **Acceptance Criteria**:
  - Select batch/test → Display analytes per sample
  - Fields: raw_result, reported_result, qualifiers, calculated_result (stub)
  - Validation: Based on analysis_analytes (data_type, ranges, sig figs)
  - Update statuses on entry/completion
  - API: POST `/results`; RBAC: `result:enter`

### User Story US-10 (Results Review)
- **As a** Lab Manager
- **I want** to review and approve results at the test level
- **So that** quality is ensured
- **Acceptance Criteria**:
  - Batch view for review; update test status to Complete
  - Record review_date
  - API: PATCH `/tests/{id}/review`; RBAC: `result:review`

### User Story US-26 (Cross-Project Batching)
- **As a** Lab Technician
- **I want** to batch samples from multiple NimbleLIMS projects together if they have compatible test types
- **So that** shared processing steps like prep can be efficient
- **Acceptance Criteria**:
  - Batch creation allows selection across accessible projects
  - Validation for compatibility (e.g., shared prep analysis like "EPA Method 8080 Prep")
  - Option to split into sub-batches for divergent steps
  - RLS enforces access to all included samples
  - API: POST `/batches` with cross-project container_ids; RBAC: `batch:manage`

### User Story US-27 (Add QC Samples at Batch Creation)
- **As a** Lab Technician
- **I want** to add QC samples directly during batch creation
- **So that** controls are integrated contextually
- **Acceptance Criteria**:
  - Select qc_type (e.g., Blank, Blank Spike, Duplicate, Matrix Spike) and auto-generate QC sample/container
  - Link to batch with inherited project_id
  - Required for certain batch types (configurable)
  - API: POST `/batches` with `qc_additions` list; RBAC: `batch:manage`

### PRD Section 3.1 (Batches/Plates)
- **Batches/Plates**: Batches as container groups; statuses: Created, In Process, Completed
- **Plates**: As containers with wells; support pooling via contents

### Workflow Document (Stage 2: Batch Creation)
- **Create Batch**: Enter name, description, type, status "Created"
- **Add Containers**: Single-project or cross-project (with compatibility validation)
- **Add QC Samples**: Auto-generate QC samples/containers with property inheritance
- **Status Flow**: Created → In Process → Completed

### UI Document (ResultsManagement.tsx, BatchFormEnhanced.tsx)
- **ResultsManagement.tsx**: Batch list view with filter, batch table, "Enter Results" button
- **BatchFormEnhanced.tsx**: Batch creation form with:
  - Container selection (search/autocomplete, cross-project support)
  - Compatibility validation button
  - QC additions section with "Add QC" button
  - QC type dropdown, notes field
  - Auto-suggestions based on batch size

### Technical Document (POST /batches)
- **Request Schema**: `BatchCreate`
  ```json
  {
    "name": "BATCH-001",
    "description": "Batch description",
    "status": "uuid-of-created-status",
    "container_ids": ["uuid1", "uuid2"],
    "cross_project": true,
    "qc_additions": [
      {"qc_type": "uuid-of-blank", "notes": "Optional notes"}
    ]
  }
  ```
- **Processing Steps**:
  1. Cross-project detection (auto-detect if multiple projects)
  2. RLS access check (verify access to all projects)
  3. Compatibility validation (samples share common analysis)
  4. QC requirement check (if batch type requires QC)
  5. Batch creation
  6. Container addition
  7. QC sample generation (inherit from first sample, create container, link to batch)
  8. Transaction commit (atomic)

### Schema
- **`batches` table**:
  - `type`: UUID FK to `list_entries.id` (nullable)
  - `status`: UUID FK to `list_entries.id` (required, list_id: "batch_status")
- **`batch_containers` junction table**:
  - `batch_id`: UUID FK to `batches.id`
  - `container_id`: UUID FK to `containers.id`
  - `position`: String (nullable)
  - `notes`: String (nullable)
  - Composite primary key: (batch_id, container_id)

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-BATCH-BASIC-001 | | | | |
| TC-BATCH-CROSS-PROJECT-002 | | | | |
| TC-BATCH-QC-003 | | | | |

---

## Appendix: Sample Test Data

### Batch Names
- `BATCH-001` (basic batch)
- `BATCH-CROSS-001` (cross-project batch)
- `BATCH-QC-001` (batch with QC)

### Containers
- `CONTAINER-001` (Project Alpha)
- `CONTAINER-002` (Project Alpha)
- `CONTAINER-ALPHA-001` (Project Alpha, for cross-project)
- `CONTAINER-BETA-001` (Project Beta, for cross-project)

### Projects
- `Project Alpha` (accessible)
- `Project Beta` (accessible, for cross-project)

### QC Types
- `Blank` (QC type)
- `Matrix Spike` (QC type)
- `Positive Control` (QC type)
- `Negative Control` (QC type)

### Batch Statuses
- `Created` (initial status)
- `In Process` (active processing)
- `Completed` (finished)

### Analyses
- `EPA Method 8080 Prep` (shared prep method for compatibility)
- `EPA Method 8080 Analytical` (analytical method)

