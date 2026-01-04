# UAT Scripts: Aliquots/Derivatives Creation and QC Handling

## Overview

This document contains User Acceptance Testing (UAT) scripts for aliquots/derivatives creation and QC handling in NimbleLIMS. These scripts validate the workflows as defined in:

- **User Stories**: US-3 (Create Aliquots/Derivatives), US-4 (QC Sample Handling)
- **PRD**: Section 3.1 (QC Integration)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Variation 1: Aliquots/Derivatives)
- **UI Document**: `ui-accessioning-to-reporting.md` (AliquotDerivativeDialog.tsx)
- **Schema**: `samples` table with `parent_sample_id` FK, `qc_type` FK to `list_entries`

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Sample status list entries (including "Available for Testing")
  - Sample types list entries (e.g., Blood, DNA Extract)
  - QC types list entries: Sample, Positive Control, Negative Control, Matrix Spike, Duplicate, Blank
  - Container types (at least one pre-configured)
  - Units for concentration/amount
- Test data:
  - At least one parent sample exists (status: "Received" or "Available for Testing")
  - At least one batch with samples (for QC flag test)
- Test user accounts:
  - Lab Technician with `sample:create` permission and project access

---

## Test Case 1: Aliquot Creation - Inherit Project from Parent

### Test Case ID
TC-ALIQUOT-001

### Description
Create an aliquot from a parent sample, verifying that project and other properties are inherited correctly.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to parent sample's project |
| **Parent Sample Exists** | At least one sample exists with status "Received" or "Available for Testing" |
| **Container Type** | At least one container type configured |
| **Status Available** | "Available for Testing" status exists in `sample_status` list |
| **Units Available** | Concentration and amount units available |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Complete sample accessioning workflow | Parent sample created (e.g., "SAMPLE-PARENT-001") |
| 2 | After successful accessioning, verify Aliquot/Derivative dialog opens | Dialog appears with tabs: "Create Aliquot" and "Create Derivative" |
| 3 | **Aliquot Tab Selected** | |
| 3.1 | Verify "Create Aliquot" tab is active | Tab highlighted, aliquot form displayed |
| 3.2 | Verify parent sample name displayed in dialog title | Title shows: "Create Aliquot or Derivative from {parentSampleName}" |
| 4 | **Fill Aliquot Form** | |
| 4.1 | Enter Aliquot Name: `ALIQUOT-001` | Field accepts input |
| 4.2 | Enter Description: `Aliquot from parent sample` | Field accepts input |
| 4.3 | Verify Sample Type is pre-filled (same as parent) | Sample type dropdown shows parent's sample type (e.g., "Blood") |
| 4.4 | Verify Matrix is pre-filled (same as parent) | Matrix dropdown shows parent's matrix |
| 4.5 | Enter Temperature: `4.0` (or leave blank to inherit) | Field accepts input or inherits from parent |
| 4.6 | **Container Information** | |
| 4.7 | Select Container Type: `Tube (1x1)` | Container type selected from dropdown |
| 4.8 | Enter Container Name: `CONTAINER-ALIQUOT-001` | Field accepts input |
| 4.9 | Enter Concentration: `10.5` | Field accepts numeric input |
| 4.10 | Select Concentration Units: `mg/L` | Units dropdown filtered by type: "concentration" |
| 4.11 | Enter Amount: `2.0` | Field accepts numeric input |
| 4.12 | Select Amount Units: `mL` | Units dropdown filtered by type: "volume" |
| 5 | Click "Create Aliquot" or "Submit" button | Form submits, loading spinner shown |
| 6 | Wait for API response | Success message displayed or dialog closes |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/aliquots/aliquot` called with:<br>- `parent_sample_id`: UUID of parent sample<br>- `name`: "ALIQUOT-001"<br>- `container_id`: UUID of created container<br>- `concentration`, `amount`, units |
| **Backend Processing** | 1. Verify parent sample exists and user has access<br>2. Check project access (RLS)<br>3. Create container instance (if not pre-created)<br>4. Get "Available for Testing" status<br>5. Create aliquot sample with:<br>   - `parent_sample_id` = parent sample ID<br>   - `sample_type` = parent's sample_type (same)<br>   - `matrix` = parent's matrix (same)<br>   - `project_id` = parent's project_id (inherited)<br>   - `due_date` = parent's due_date (inherited)<br>   - `received_date` = parent's received_date (inherited)<br>   - `status` = "Available for Testing"<br>6. Create `Contents` junction linking aliquot to container<br>7. Commit transaction |
| **Aliquot Record** | - New sample created with `parent_sample_id` FK set<br>- `sample_type` = parent's sample_type (same type)<br>- `project_id` = parent's project_id (inherited)<br>- `status` = "Available for Testing"<br>- `matrix` = parent's matrix (inherited)<br>- Audit fields set: `created_by`, `modified_by` = current user |
| **Container Record** | - Container created (if not pre-created)<br>- Container linked to aliquot via `Contents` junction<br>- Concentration and amount with units saved |
| **UI Feedback** | - Success message: "Aliquot/Derivative created successfully: ALIQUOT-001"<br>- Dialog closes<br>- Optional: Navigate to aliquot in samples list |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Aliquot created successfully | ✓ | ✗ |
| `parent_sample_id` FK set correctly | ✓ | ✗ |
| `project_id` inherited from parent | ✓ | ✗ |
| `sample_type` same as parent | ✓ | ✗ |
| `matrix` inherited from parent | ✓ | ✗ |
| Container created and linked | ✓ | ✗ |
| Status = "Available for Testing" | ✓ | ✗ |
| Audit fields set | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Derivative Creation - New Sample Type

### Test Case ID
TC-DERIVATIVE-002

### Description
Create a derivative from a parent sample with a different sample type (e.g., DNA Extract from Blood).

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Project Access** | User has access to parent sample's project |
| **Parent Sample Exists** | At least one sample exists (e.g., Blood sample) |
| **Sample Types** | At least two sample types exist (e.g., "Blood", "DNA Extract") |
| **Container Type** | At least one container type configured |
| **Status Available** | "Available for Testing" status exists |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Complete sample accessioning workflow | Parent sample created (e.g., "SAMPLE-BLOOD-001", type: "Blood") |
| 2 | After successful accessioning, Aliquot/Derivative dialog opens | Dialog appears |
| 3 | **Select Derivative Tab** | |
| 3.1 | Click "Create Derivative" tab | Tab switches, derivative form displayed |
| 3.2 | Verify parent sample name displayed | Title shows parent sample name |
| 4 | **Fill Derivative Form** | |
| 4.1 | Enter Derivative Name: `DNA-EXTRACT-001` | Field accepts input |
| 4.2 | Enter Description: `DNA extract from blood sample` | Field accepts input |
| 4.3 | **Select Different Sample Type** | |
| 4.4 | Open Sample Type dropdown | Dropdown shows all available sample types |
| 4.5 | Select Sample Type: `DNA Extract` (different from parent's "Blood") | Sample type selected, different from parent |
| 4.6 | Verify Matrix is pre-filled (same as parent) | Matrix shows parent's matrix (inherited) |
| 4.7 | Enter Temperature: `-20.0` (different from parent) | Field accepts input |
| 4.8 | **Container Information** | |
| 4.9 | Select Container Type: `DNA Tube` | Container type selected |
| 4.10 | Enter Container Name: `CONTAINER-DERIVATIVE-001` | Field accepts input |
| 4.11 | Enter Concentration: `50.0` | Field accepts numeric input |
| 4.12 | Select Concentration Units: `ng/µL` | Units selected |
| 4.13 | Enter Amount: `100.0` | Field accepts numeric input |
| 4.14 | Select Amount Units: `µL` | Units selected |
| 5 | Click "Create Derivative" or "Submit" button | Form submits |
| 6 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/aliquots/derivative` called with:<br>- `parent_sample_id`: UUID of parent sample<br>- `name`: "DNA-EXTRACT-001"<br>- `sample_type`: UUID of "DNA Extract" (different from parent)<br>- `container_id`: UUID of created container |
| **Backend Processing** | 1. Verify parent sample exists and user has access<br>2. Check project access (RLS)<br>3. Create container instance<br>4. Get "Available for Testing" status<br>5. Create derivative sample with:<br>   - `parent_sample_id` = parent sample ID<br>   - `sample_type` = "DNA Extract" (different from parent's "Blood")<br>   - `matrix` = parent's matrix (inherited, same)<br>   - `project_id` = parent's project_id (inherited)<br>   - `due_date` = parent's due_date (inherited)<br>   - `received_date` = parent's received_date (inherited)<br>   - `status` = "Available for Testing"<br>6. Create `Contents` junction linking derivative to container<br>7. Commit transaction |
| **Derivative Record** | - New sample created with `parent_sample_id` FK set<br>- `sample_type` = "DNA Extract" (different from parent's "Blood")<br>- `project_id` = parent's project_id (inherited)<br>- `matrix` = parent's matrix (inherited)<br>- `status` = "Available for Testing"<br>- Audit fields set |
| **Container Record** | - Container created and linked via `Contents` junction |
| **UI Feedback** | - Success message: "Aliquot/Derivative created successfully: DNA-EXTRACT-001"<br>- Dialog closes |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Derivative created successfully | ✓ | ✗ |
| `parent_sample_id` FK set correctly | ✓ | ✗ |
| `sample_type` different from parent | ✓ | ✗ |
| `project_id` inherited from parent | ✓ | ✗ |
| `matrix` inherited from parent | ✓ | ✗ |
| Container created and linked | ✓ | ✗ |
| Status = "Available for Testing" | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: QC Flag Display in Batch View

### Test Case ID
TC-QC-FLAG-003

### Description
Verify QC samples are properly flagged and highlighted in batch views and results entry tables.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `batch:read` or `result:read` |
| **Batch Exists** | At least one batch exists with samples |
| **QC Samples** | At least one sample in batch has `qc_type` set (e.g., "Blank", "Positive Control") |
| **Regular Samples** | At least one sample in batch has `qc_type` = NULL or "Sample" |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/results` or Results Management page | Results Management page loads |
| 2 | **Verify Batch List View** | |
| 2.1 | Locate batch with QC samples | Batch row visible in table |
| 2.2 | Check "QC" column in batch table | Column shows QC indicators |
| 2.3 | Verify QC indicator displayed | Warning icon (⚠️) and chip showing QC type(s) (e.g., "Blank", "Positive Control") |
| 2.4 | Verify non-QC batches show "None" | Batches without QC samples show "None" in QC column |
| 3 | **Open Batch Results View** | |
| 3.1 | Click "Enter Results" button on batch row | Batch results view opens |
| 3.2 | Verify batch details displayed | Batch information card shows batch name, status, sample count |
| 4 | **Verify Results Entry Table** | |
| 4.1 | Select a test from dropdown | Test selected, results entry table displayed |
| 4.2 | Locate QC sample row in table | QC sample row visible in DataGrid |
| 4.3 | **Verify QC Row Highlighting** | |
| 4.4 | Check row background color | QC sample row has warning background color (warning.light) |
| 4.5 | Check sample name cell | Sample name displayed with warning color (warning.main) and bold font |
| 4.6 | Verify QC chip displayed | "QC" chip shown next to sample name (warning color, small size) |
| 4.7 | Verify regular sample rows | Non-QC sample rows have normal background color |
| 5 | **Verify QC Types Display** | |
| 5.1 | Check if multiple QC types in batch | If batch has multiple QC types, all types shown in batch list view |
| 5.2 | Verify QC type names | QC type names match list entries (e.g., "Blank", "Positive Control") |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Batch List View** | - QC column shows warning icon and chip with QC type names<br>- Batches without QC show "None"<br>- Function `hasQCSamples()` returns true for batches with QC |
| **Results Entry Table** | - QC sample rows have CSS class `qc-row`<br>- Row background: `warning.light` (default), `warning.main` (hover)<br>- Sample name cell: Warning color, bold font, "QC" chip displayed<br>- Regular sample rows: Normal styling |
| **QC Detection Logic** | - Function `isQCSample(sample)` checks if `sample.qc_type` is not NULL and not "Sample"<br>- QC types: Blank, Positive Control, Negative Control, Matrix Spike, Duplicate |
| **Data Source** | - QC information comes from `samples.qc_type` FK to `list_entries`<br>- Batch samples loaded with QC type information |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| QC samples identified correctly | ✓ | ✗ |
| QC indicator shown in batch list | ✓ | ✗ |
| QC rows highlighted in results table | ✓ | ✗ |
| QC chip displayed next to sample name | ✓ | ✗ |
| Regular samples not highlighted | ✓ | ✗ |
| Multiple QC types displayed correctly | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-3 (Create Aliquots/Derivatives)
- **As a** Lab Technician
- **I want** to create aliquots or derivatives from parent samples during workflows
- **So that** sub-samples are linked and inherit properties
- **Acceptance Criteria**:
  - Aliquot: Same sample_id, new container_id
  - Derivative: New sample_id/type, new container_id
  - Inherit project_id, client_id; configurable workflow steps
  - Example: DNA extraction from blood
  - API: POST `/samples/aliquot` or `/derivative` with parent_id; RBAC: `sample:create`

### User Story US-4 (QC Sample Handling)
- **As a** Lab Technician
- **I want** to flag samples as QC types
- **So that** controls/blanks are integrated into batches
- **Acceptance Criteria**:
  - qc_type from lists: Sample, Positive Control, Negative Control, Matrix Spike, Duplicate, Blank
  - Display in batch views for validation
  - API: Included in sample creation/update; no separate permission

### PRD Section 3.1 (QC Integration)
- **QC Integration**: `qc_type` field (e.g., Sample, Positive Control, Blank) from lists
- **Aliquots/Derivatives**: Linked via `parent_sample_id`; inheritance of project/client; created in workflows (e.g., DNA extraction)

### Workflow Document (Variation 1: Aliquots/Derivatives)
- **Post-Accessioning**: Optional: Create aliquots/derivatives from parent sample
- **Aliquot**: Same sample type as parent, new container, inherits project
- **Derivative**: Different sample type, new container, inherits project
- **Status**: Created with "Available for Testing" status

### UI Document (AliquotDerivativeDialog.tsx)
- **Dialog Component**: Modal dialog with tabs for "Create Aliquot" and "Create Derivative"
- **AliquotForm**: Form for creating aliquots (pre-fills sample_type from parent)
- **DerivativeForm**: Form for creating derivatives (allows selecting different sample_type)
- **Integration**: Opens after successful sample accessioning, shows parent sample name in title

### Technical Implementation
- **POST `/aliquots/aliquot`**: Creates aliquot with same `sample_type` as parent, inherits `project_id`, `matrix`, `due_date`, `received_date`
- **POST `/aliquots/derivative`**: Creates derivative with different `sample_type`, inherits `project_id`, `matrix`, dates
- **Both**: Set `parent_sample_id` FK, create container, link via `Contents` junction, set status to "Available for Testing"
- **QC Flagging**: `samples.qc_type` FK to `list_entries`, displayed in batch views with warning indicators

### Schema
- **`samples.parent_sample_id`**: UUID FK to `samples.id` (nullable, self-referential)
- **`samples.qc_type`**: UUID FK to `list_entries.id` (nullable, list_id: "qc_types")
- **`contents`**: Junction table linking samples to containers with concentration/amount/units

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-ALIQUOT-001 | | | | |
| TC-DERIVATIVE-002 | | | | |
| TC-QC-FLAG-003 | | | | |

---

## Appendix: Sample Test Data

### Parent Samples
- `SAMPLE-PARENT-001` (type: "Blood", for aliquot test)
- `SAMPLE-BLOOD-001` (type: "Blood", for derivative test)

### Aliquots/Derivatives
- `ALIQUOT-001` (aliquot from parent, same type)
- `DNA-EXTRACT-001` (derivative, type: "DNA Extract" from "Blood")

### Containers
- `CONTAINER-ALIQUOT-001` (for aliquot)
- `CONTAINER-DERIVATIVE-001` (for derivative)

### QC Types
- `Blank` (QC type)
- `Positive Control` (QC type)
- `Negative Control` (QC type)
- `Matrix Spike` (QC type)
- `Duplicate` (QC type)
- `Sample` (regular sample, qc_type = NULL or "Sample")

### Sample Types
- `Blood` (parent sample type)
- `DNA Extract` (derivative sample type)

