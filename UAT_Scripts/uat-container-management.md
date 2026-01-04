# UAT Scripts: Container Management and Editing

## Overview

This document contains User Acceptance Testing (UAT) scripts for container management and editing in NimbleLIMS. These scripts validate the container workflows as defined in:

- **User Stories**: US-5 (Container Management)
- **PRD**: Section 3.1 (Containers)
- **UI Document**: `ui-accessioning-to-reporting.md` (ContainerManagement.tsx, ContainerForm.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (PATCH /containers/{id})
- **Schema**: `containers` table with `type_id` FK, `parent_container_id` FK, `contents` junction table

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Container types: "96-well plate", "well", "tube" (at least)
  - Units for concentration and amount (with multipliers)
  - At least two samples (for pooling test)
- Test user accounts:
  - Lab Technician with `sample:create` and `sample:update` permissions

---

## Test Case 1: Hierarchical Creation - Plate with Wells

### Test Case ID
TC-CONTAINER-HIERARCHY-001

### Description
Create a hierarchical container structure: parent plate container with child well containers.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` |
| **Container Types** | "96-well plate" and "well" container types exist |
| **Units** | Concentration and amount units available |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/containers` route | Container Management page loads with DataGrid |
| 2 | Click "Create Container" button | ContainerForm dialog opens |
| 3 | **Create Parent Container (Plate)** | |
| 3.1 | Enter Container Name: `PLATE-001` | Field accepts input |
| 3.2 | Select Container Type: `96-well plate` | Type selected from dropdown (shows name, material, dimensions) |
| 3.3 | Leave Parent Container empty (no parent) | Field remains empty |
| 3.4 | Leave Row/Column as defaults (1, 1) | Default values set |
| 3.5 | Click "Save" or "Create" button | Container created, dialog closes or refreshes |
| 4 | **Verify Parent Container Created** | |
| 4.1 | Locate "PLATE-001" in DataGrid | Container visible in list |
| 4.2 | Verify container type shows "96-well plate" | Type displayed correctly |
| 5 | **Create Child Container (Well A1)** | |
| 5.1 | Click "Create Container" button again | ContainerForm dialog opens |
| 5.2 | Enter Container Name: `PLATE-001-A1` | Field accepts input |
| 5.3 | Select Container Type: `well` | Type selected |
| 5.4 | **Select Parent Container** | |
| 5.5 | Open Parent Container dropdown | Dropdown shows available containers |
| 5.6 | Select Parent Container: `PLATE-001` | Parent selected |
| 5.7 | Enter Row: `1` (for well A1) | Field accepts integer >= 1 |
| 5.8 | Enter Column: `1` (for well A1) | Field accepts integer >= 1 |
| 5.9 | Click "Save" button | Child container created |
| 6 | **Create Additional Wells (Optional)** | |
| 6.1 | Repeat steps 5.1-5.9 for well A2 | Well A2 created (row=1, column=2) |
| 6.2 | Repeat for well B1 | Well B1 created (row=2, column=1) |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Calls** | 1. POST `/containers` for parent plate<br>2. POST `/containers` for each well with `parent_container_id` set |
| **Parent Container Record** | - Container created with:<br>  - `name`: "PLATE-001"<br>  - `type_id`: UUID of "96-well plate"<br>  - `parent_container_id`: NULL<br>  - `row`: 1, `column`: 1 (defaults)<br>- Audit fields set: `created_by`, `created_at` |
| **Child Container Records** | - Each well container created with:<br>  - `name`: "PLATE-001-A1", etc.<br>  - `type_id`: UUID of "well"<br>  - `parent_container_id`: UUID of PLATE-001<br>  - `row`: 1-8 (A-H), `column`: 1-12<br>- Audit fields set |
| **Hierarchical Relationship** | - `parent_container` relationship established<br>- `child_containers` relationship accessible<br>- Parent container can query child containers |
| **UI Feedback** | - Success message or dialog closes<br>- DataGrid refreshes showing new containers<br>- Parent-child relationship visible in container details |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Parent container created successfully | ✓ | ✗ |
| Child containers created with `parent_container_id` set | ✓ | ✗ |
| Row/column positions set correctly | ✓ | ✗ |
| Hierarchical relationship established | ✓ | ✗ |
| Audit fields set on all containers | ✓ | ✗ |
| UI reflects parent-child structure | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Edit Container - Update Concentration

### Test Case ID
TC-CONTAINER-EDIT-002

### Description
Edit an existing container to update concentration and amount values.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:update` |
| **Container Exists** | At least one container exists (e.g., "CONTAINER-001") |
| **Units** | Concentration and amount units available |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/containers` route | Container Management page loads |
| 2 | Locate existing container in DataGrid | Container visible in list |
| 3 | Click "Edit" button on container row | Edit dialog opens (ContainerForm) with pre-filled data |
| 4 | **Verify Pre-filled Data** | |
| 4.1 | Verify container name is displayed | Name field shows current value |
| 4.2 | Verify container type is selected | Type dropdown shows current type |
| 4.3 | Verify current concentration (if set) | Concentration field shows current value |
| 5 | **Update Concentration** | |
| 5.1 | Clear or modify Concentration field | Field accepts input |
| 5.2 | Enter new Concentration: `15.5` | Field accepts numeric input |
| 5.3 | Select Concentration Units: `mg/L` | Units dropdown filtered by type: "concentration" |
| 5.4 | Enter Amount: `10.0` | Field accepts numeric input |
| 5.5 | Select Amount Units: `mL` | Units dropdown filtered by type: "volume" |
| 6 | Click "Save" button | Form submits, loading spinner shown |
| 7 | Wait for API response | Success message displayed or dialog closes |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/containers/{container_id}` called with:<br>- `concentration`: 15.5<br>- `concentration_units`: UUID of "mg/L"<br>- `amount`: 10.0<br>- `amount_units`: UUID of "mL" |
| **Backend Processing** | 1. Verify container exists<br>2. Check `sample:update` permission<br>3. Validate container type (if updated)<br>4. Validate parent container (if updated)<br>5. Update fields (partial update, only provided fields)<br>6. Update audit fields: `modified_by` = current user, `modified_at` = current timestamp<br>7. Commit transaction |
| **Container Record** | - `concentration` updated to 15.5<br>- `concentration_units` updated to selected unit UUID<br>- `amount` updated to 10.0<br>- `amount_units` updated to selected unit UUID<br>- `modified_by` = current user ID<br>- `modified_at` = current timestamp (updated)<br>- Other fields unchanged |
| **UI Feedback** | - Success message or dialog closes<br>- DataGrid refreshes showing updated values<br>- Updated concentration/amount visible in container details |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Container updated successfully | ✓ | ✗ |
| Concentration updated correctly | ✓ | ✗ |
| Concentration units updated | ✓ | ✗ |
| Amount updated correctly | ✓ | ✗ |
| Amount units updated | ✓ | ✗ |
| Audit fields (`modified_by`, `modified_at`) updated | ✓ | ✗ |
| Other fields unchanged | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Pooling via Contents - Multiple Samples in Container

### Test Case ID
TC-CONTAINER-POOLING-003

### Description
Add multiple samples to a single container via contents junction (pooling).

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` (for adding contents) |
| **Container Exists** | At least one container exists (e.g., "POOL-CONTAINER-001") |
| **Samples Exist** | At least two samples exist (e.g., "SAMPLE-001", "SAMPLE-002") |
| **Units** | Concentration and amount units available with multipliers |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/containers` route | Container Management page loads |
| 2 | Locate container in DataGrid | Container visible in list |
| 3 | Click on container row | ContainerDetails dialog opens |
| 4 | **Verify Contents Section** | |
| 4.1 | Locate "Contents" section in dialog | Section visible showing current contents (if any) |
| 4.2 | Verify "Add Sample" button visible | Button available in Contents section |
| 5 | **Add First Sample** | |
| 5.1 | Click "Add Sample" button | Add Sample dialog opens |
| 5.2 | Select Sample: `SAMPLE-001` | Sample selected from dropdown (all accessible samples shown) |
| 5.3 | Enter Concentration: `10.0` | Field accepts numeric input |
| 5.4 | Select Concentration Units: `mg/L` | Units selected |
| 5.5 | Enter Amount: `5.0` | Field accepts numeric input |
| 5.6 | Select Amount Units: `mL` | Units selected |
| 5.7 | Click "Add" or "Save" button | Contents entry created, dialog closes |
| 5.8 | Verify sample appears in Contents list | Sample "SAMPLE-001" listed with concentration/amount |
| 6 | **Add Second Sample (Pooling)** | |
| 6.1 | Click "Add Sample" button again | Add Sample dialog opens |
| 6.2 | Select Sample: `SAMPLE-002` | Sample selected (different from first) |
| 6.3 | Enter Concentration: `20.0` | Field accepts input |
| 6.4 | Select Concentration Units: `mg/L` | Units selected |
| 6.5 | Enter Amount: `3.0` | Field accepts input |
| 6.6 | Select Amount Units: `mL` | Units selected |
| 6.7 | Click "Add" button | Contents entry created |
| 6.8 | Verify both samples in Contents list | Both "SAMPLE-001" and "SAMPLE-002" listed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Calls** | POST `/containers/{container_id}/contents` called for each sample with:<br>- `container_id`: UUID of container<br>- `sample_id`: UUID of sample<br>- `concentration`: value<br>- `concentration_units`: unit UUID<br>- `amount`: value<br>- `amount_units`: unit UUID |
| **Backend Processing** | 1. Verify container exists<br>2. Verify sample exists and user has access (RLS)<br>3. Check unique constraint (same sample cannot be in same container twice)<br>4. Validate units (concentration units for concentration, mass/volume for amount)<br>5. Create `Contents` record<br>6. Commit transaction |
| **Contents Records** | - First contents entry:<br>  - `container_id`: UUID of container<br>  - `sample_id`: UUID of SAMPLE-001<br>  - `concentration`: 10.0, `concentration_units`: UUID<br>  - `amount`: 5.0, `amount_units`: UUID<br>- Second contents entry:<br>  - `container_id`: UUID of container (same)<br>  - `sample_id`: UUID of SAMPLE-002 (different)<br>  - `concentration`: 20.0, `concentration_units`: UUID<br>  - `amount`: 3.0, `amount_units`: UUID<br>- Audit fields set on both |
| **Pooling Validation** | - Multiple samples can exist in same container<br> - Unique constraint prevents duplicate sample-container pairs<br> - Volume calculations can be performed (if implemented) using multipliers |
| **UI Feedback** | - Contents list shows both samples<br>- Each entry displays sample name, concentration, amount with units<br>- Remove button available for each entry |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| First sample added successfully | ✓ | ✗ |
| Second sample added successfully (pooling) | ✓ | ✗ |
| Both samples visible in Contents list | ✓ | ✗ |
| Unique constraint prevents duplicate sample-container pairs | ✓ | ✗ |
| Concentration and amount saved correctly | ✓ | ✗ |
| Units validated correctly | ✓ | ✗ |
| RLS enforced (only accessible samples shown) | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-5 (Container Management)
- **As a** Lab Technician
- **I want** to assign and manage hierarchical containers for samples
- **So that** physical storage is tracked
- **Acceptance Criteria**:
  - Types: tube, plate, well, rack (from container_types table with capacity, material, dimensions, preservative)
  - Self-referential (parent_container_id for plates/wells)
  - Contents link: Multiple samples per container (pooling) with concentration/amount/units
  - Units table: id, name, description, active, audit fields, multiplier, type (list: concentration, mass, volume, molar)
  - API: POST `/containers`; link via `/contents`; RBAC: `sample:update`

### PRD Section 3.1 (Containers)
- **Containers**: Hierarchical (self-referential; types like tube, plate, well); contents linking samples with concentration/amount (volume calculated)

### UI Document (ContainerManagement.tsx, ContainerForm.tsx)
- **ContainerManagement.tsx**: DataGrid listing containers, Create/Edit buttons, ContainerDetails dialog
- **ContainerForm.tsx**: Reusable form for creating/editing containers
  - Fields: name, type_id, parent_container_id, row, column, concentration, concentration_units, amount, amount_units
  - Handles both create and edit modes
  - Formik/Yup validation
  - Permission-gated for `sample:create`/`sample:update`
- **ContainerDetails.tsx**: Dialog showing container details and contents management (Add Sample functionality)

### Technical Document (PATCH /containers/{id})
- **Request Schema**: `ContainerUpdate` (partial, optional fields)
  ```json
  {
    "name": "CONTAINER-001-UPDATED",
    "concentration": 15.5,
    "concentration_units": "uuid",
    "amount": 10.0,
    "amount_units": "uuid",
    "type_id": "uuid",
    "parent_container_id": "uuid"
  }
  ```
- **Processing Steps**:
  1. Verify container exists
  2. Check `sample:update` permission
  3. Validate container type (if updated)
  4. Validate parent container (if updated)
  5. Update fields (partial update)
  6. Update audit fields: `modified_by`, `modified_at`
  7. Commit transaction
- **Error Handling**: 404 (container not found), 403 (permission denied), 400 (invalid type/parent)

### Schema
- **`containers` table**:
  - `type_id`: UUID FK to `container_types.id` (required)
  - `parent_container_id`: UUID FK to `containers.id` (nullable, self-referential)
  - `row`: Integer (default: 1)
  - `column`: Integer (default: 1)
  - `concentration`: Numeric(15,6)
  - `concentration_units`: UUID FK to `units.id`
  - `amount`: Numeric(15,6)
  - `amount_units`: UUID FK to `units.id`
- **`contents` junction table**:
  - `container_id`: UUID FK to `containers.id` (primary key)
  - `sample_id`: UUID FK to `samples.id` (primary key)
  - `concentration`: Numeric(15,6)
  - `concentration_units`: UUID FK to `units.id`
  - `amount`: Numeric(15,6)
  - `amount_units`: UUID FK to `units.id`
  - Unique constraint: (container_id, sample_id)

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-CONTAINER-HIERARCHY-001 | | | | |
| TC-CONTAINER-EDIT-002 | | | | |
| TC-CONTAINER-POOLING-003 | | | | |

---

## Appendix: Sample Test Data

### Container Names
- `PLATE-001` (parent plate)
- `PLATE-001-A1` (well A1, row=1, column=1)
- `PLATE-001-A2` (well A2, row=1, column=2)
- `PLATE-001-B1` (well B1, row=2, column=1)
- `CONTAINER-001` (for edit test)
- `POOL-CONTAINER-001` (for pooling test)

### Container Types
- `96-well plate` (parent type)
- `well` (child type)
- `tube` (alternative type)

### Samples
- `SAMPLE-001` (for pooling)
- `SAMPLE-002` (for pooling)

### Units
- Concentration: `mg/L`, `ng/µL`
- Amount: `mL`, `µL`

### Hierarchical Structure Example
```
PLATE-001 (96-well plate)
├── PLATE-001-A1 (well, row=1, column=1)
├── PLATE-001-A2 (well, row=1, column=2)
├── PLATE-001-B1 (well, row=2, column=1)
└── ... (additional wells)
```

