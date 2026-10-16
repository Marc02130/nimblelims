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
| 4.1 | Read the note that an aliquot is the same sample in another container | Copy says no new sample is created |
| 4.2 | Select Destination container: a vessel that does not already hold this sample | Container selected |
| 4.3 | Leave Source container as "Only vessel" when the sample is in one vessel | Optional source stays empty |
| 4.4 | Enter Amount less than or equal to the source vessel amount (e.g. `2.0` from `10`) | Field accepts numeric input |
| 4.5 | Select Amount Units that match the source vessel, if the source has units | Units dropdown filtered by type |
| 4.6 | Optionally enter concentration | Field accepts numeric input |
| 5 | Click "Create Aliquot" or "Submit" button | Form submits, loading spinner shown |
| 6 | Wait for API response | Success message displayed or dialog closes |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/aliquots` (alias POST `/aliquots/aliquot`) with:<br>- `parent_sample_id`: UUID of the sample<br>- `container_id`: destination container<br>- `amount`: positive number not greater than the source vessel |
| **Backend Processing** | 1. Verify the sample exists and the user has access<br>2. Refuse a different `sample_type` (**400** `aliquot_type_change_not_allowed`)<br>3. Debit the source `contents.amount` in one UPDATE<br>4. Insert a `contents` row for the same sample in the destination container<br>5. Do not insert a Sample row<br>6. Commit |
| **Aliquot Record** | - Response `id` is the parent sample id<br>- Sample row count is unchanged<br>- Source vessel amount decreased by `amount`<br>- Destination vessel holds that amount of the same sample<br>- A full draw leaves the source row with amount 0 (the row is not deleted) |
| **Over-draw** | Amount greater than the source vessel → **400** `insufficient_amount`. Source amount unchanged. No destination contents row. |
| **UI Feedback** | - Dialog closes on success<br>- The sample id in the result is the parent sample |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Aliquot places the same sample in the destination container | ✓ | ✗ |
| No new Sample row | ✓ | ✗ |
| Source amount decreased by the transferred amount | ✓ | ✗ |
| Over-draw refused with **400** `insufficient_amount` | ✓ | ✗ |
| Source row remains when the remainder is 0 | ✓ | ✗ |
| Sample type unchanged | ✓ | ✗ |

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
| **API Call** | POST `/aliquots/derivative` with:<br>- `parent_sample_id`: UUID of parent sample<br>- `sample_type`: a different type that has an active `derivative` transition<br>- `container_id`: destination container<br>- `amount`: positive and not greater than the source vessel |
| **Backend Processing** | 1. Verify parent sample exists and user has access<br>2. Refuse the same type (**400** `derivative_same_type`) and a type with no active derivative transition (**400** `dest_sample_type_not_allowed`)<br>3. Debit the source vessel<br>4. Insert a child sample named `{parent}-DER-{token}` with `parent_sample_id` set<br>5. Link that child to the destination container<br>6. Commit. The parent row stays |
| **Derivative Record** | - New sample whose name contains `-DER-` and not `-ALQ-`<br>- `sample_type` differs from the parent<br>- `parent_sample_id` points at the parent<br>- Source vessel amount decreased by `amount`<br>- Over-draw is **400** `insufficient_amount` and creates no child<br>- Temperature `0` is stored as 0 °C. A blank temperature copies the parent, including when the parent is 0 °C |
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

## Test Case 2b: Pool debit is all-or-nothing

### Test Case ID
TC-POOL-002B

### Description
Pool two samples into one container. Each source vessel is debited. If the second source cannot cover its amount, the first source is unchanged and the destination stays empty.

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Place sample A in a vessel with amount 10 and sample B in a vessel with amount 3 | Two contents rows |
| 2 | POST `/aliquots/pool` drawing 6 from each into an empty destination, with positive concentrations | **400** `insufficient_amount` |
| 3 | Re-read both source vessels and the destination | A is still 10, B is still 3, destination has no contents |
| 4 | POST the same pool drawing 2 from each | **200**. A is 8, B is 1. Both samples are in the destination. Source rows remain |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Failed pool debits nothing | ✓ | ✗ |
| Successful pool conserves amount | ✓ | ✗ |
| Source contents rows are not deleted | ✓ | ✗ |

---

## Test Case 2c: Pool on seed concentration units

### Test Case ID
TC-POOL-002C

### Description
Seed concentration units include several multiplier-1 units (`g/L`, `ng/µL`, `µg/mL`, `EU/mL`, `copies/µL`). They are not one scale. A pool of sources that share `ng/µL` succeeds in that unit. Mixing `ng/µL` with `EU/mL` debits nothing.

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Two vessels, amounts 50, concentration unit `ng/µL` on the contents. The concentration type also has `µg/mL`, `EU/mL`, `copies/µL`, and `g/L` at multiplier 1 | Rows exist |
| 2 | POST `/aliquots/pool` with one line `ng/µL` and the other `EU/mL` | **400** `incompatible_units`. Both amounts still 50. Destination empty |
| 3 | POST the same pool with both lines `ng/µL`, amounts 5 and 10 | **200**. Response `concentration_units` is `ng/µL`. Amounts are 45 and 40 |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Shared seed unit does not require a single base unit | ✓ | ✗ |
| Mixed seed units debit nothing | ✓ | ✗ |

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
  - API: POST `/aliquots` (same sample, new container) or POST `/aliquots/derivative` (child named `{parent}-DER-{token}`); RBAC: `sample:create`

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
- **AliquotForm**: Places the same sample in a destination container and sends `amount`. It does not collect a new sample type.
- **DerivativeForm**: Collects a different sample type and a destination container. The server names the child `{parent}-DER-{token}`.
- **Integration**: Opens after successful sample accessioning, shows parent sample name in title

### Technical Implementation
- **POST `/aliquots` and POST `/aliquots/aliquot`**: Same sample, new contents row, source vessel debited. No new Sample row.
- **POST `/aliquots/derivative`**: New child sample named `{parent}-DER-{token}`, different `sample_type`, source vessel debited. Parent row stays.
- **Both**: Refuse an over-draw (**400** `insufficient_amount`). A vessel drawn to zero keeps its contents row with amount 0. Nothing is deleted.
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

