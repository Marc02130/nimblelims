# UAT Scripts: Sample Status Management and Editing

## Overview

This document contains User Acceptance Testing (UAT) scripts for sample status management and editing in NimbleLIMS. These scripts validate the editing workflow as defined in:

- **User Stories**: US-2 (Sample Status Management)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stage 1.5: Sample/Test/Container Editing)
- **UI Document**: `ui-accessioning-to-reporting.md` (SamplesManagement.tsx, SampleForm.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (PATCH /samples/{id})
- **Schema**: `samples` table with `status` FK to `list_entries`, `custom_attributes` JSONB column

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Sample status list entries: "Received", "Available for Testing", "Testing Complete", "Reviewed", "Reported"
  - At least one existing sample with status "Received"
  - Custom attribute configurations for 'samples' entity type (at least one active config)
- Test user accounts:
  - Lab Technician with `sample:update` permission and project access
  - Lab Technician without project access (for RLS test)

---

## Test Case 1: Status Update - Change Sample Status to 'Available for Testing'

### Test Case ID
TC-SAMPLE-STATUS-001

### Description
Update sample status from "Received" to "Available for Testing" using the status update functionality.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `sample:update` |
| **Project Access** | User has access to sample's project |
| **Sample Exists** | At least one sample with status "Received" exists |
| **Status Available** | "Available for Testing" status exists in `sample_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/samples` route | Samples Management page loads with DataGrid showing accessible samples |
| 2 | Verify user is logged in with `sample:update` permission | User context shows appropriate role and permission |
| 3 | Locate sample with status "Received" | Sample row visible in DataGrid with status column showing "Received" |
| 4 | Click "Edit" button on sample row | Edit dialog opens (SampleForm component) |
| 5 | Verify sample details are pre-filled | Form shows current sample data: name, description, status, etc. |
| 6 | **Update Status** | |
| 6.1 | Open Status dropdown | Dropdown shows available statuses from `sample_status` list |
| 6.2 | Select "Available for Testing" | Status selected, displayed in dropdown |
| 6.3 | Click "Save" button | Form submits, loading spinner shown |
| 6.4 | Wait for API response | Success message displayed or dialog closes |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/samples/{sample_id}` called with `{"status": "uuid-of-available-for-testing-status"}` |
| **Backend Processing** | 1. Verify sample exists<br>2. Check `sample:update` permission<br>3. Verify project access (RLS)<br>4. Validate status exists in `list_entries`<br>5. Update `sample.status` field<br>6. Update audit fields: `modified_by` = current user ID, `modified_at` = current timestamp<br>7. Commit transaction |
| **Sample Record** | - Status field updated to "Available for Testing" status UUID<br>- `modified_by` = current user ID<br>- `modified_at` = current timestamp (updated)<br>- All other fields unchanged |
| **UI Feedback** | - Success message displayed (if implemented)<br>- DataGrid refreshes showing updated status<br>- Edit dialog closes<br>- Status column shows "Available for Testing" |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Status updated successfully | ✓ | ✗ |
| Status value = "Available for Testing" UUID | ✓ | ✗ |
| Audit fields (`modified_by`, `modified_at`) updated | ✓ | ✗ |
| No validation errors | ✓ | ✗ |
| UI reflects updated status | ✓ | ✗ |
| Other sample fields unchanged | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Edit with Custom Attributes - Validation Success and Failure

### Test Case ID
TC-SAMPLE-EDIT-002

### Description
Edit sample with custom attributes, testing both successful validation and validation failure scenarios.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `sample:update` |
| **Project Access** | User has access to sample's project |
| **Sample Exists** | At least one sample exists |
| **Custom Attribute Configs** | At least one active custom attribute configuration for 'samples' entity type exists (e.g., `ph_level` as number type with min=0, max=14) |

### Test Steps - Validation Success

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/samples` route | Samples Management page loads |
| 2 | Click "Edit" button on any sample row | Edit dialog opens with SampleForm |
| 3 | **Verify Custom Attributes Section** | |
| 3.1 | Scroll to "Custom Fields" section | Section visible with dynamically rendered fields |
| 3.2 | Verify custom attribute fields are displayed | Fields rendered based on active configs (e.g., `ph_level` as NumberField) |
| 3.3 | Verify field labels and types match configs | Text fields for text type, number fields for number type, etc. |
| 4 | **Enter Valid Custom Attribute Values** | |
| 4.1 | Enter `ph_level`: `7.2` (within range 0-14) | Field accepts input, no validation error |
| 4.2 | If text field exists, enter valid text | Field accepts input |
| 4.3 | Verify real-time validation | No red borders or error messages |
| 5 | Click "Save" button | Form submits successfully |

### Expected Results - Validation Success

| Category | Expected Outcome |
|----------|------------------|
| **Client-Side Validation** | - Real-time validation passes<br>- No error messages displayed<br>- Form allows submission |
| **API Call** | PATCH `/samples/{sample_id}` called with `{"custom_attributes": {"ph_level": 7.2}}` |
| **Backend Validation** | 1. `validate_custom_attributes()` function called<br>2. Validates against active configs for 'samples'<br>3. Checks data types (number for `ph_level`)<br>4. Validates ranges (0-14 for `ph_level`)<br>5. Validation passes |
| **Sample Record** | - `custom_attributes` JSONB updated: `{"ph_level": 7.2}`<br>- Audit fields updated |
| **UI Feedback** | - Success message or dialog closes<br> - DataGrid refreshes |

### Test Steps - Validation Failure

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | Return to edit dialog (or start new edit) | Edit dialog opens |
| 7 | **Enter Invalid Custom Attribute Values** | |
| 7.1 | Enter `ph_level`: `15.5` (outside range 0-14) | Field shows validation error: "Value must be between 0 and 14" (or similar) |
| 7.2 | Verify error display | Red border on field, error text below field |
| 7.3 | Attempt to click "Save" | Save button disabled or form prevents submission |
| 8 | **Test Unknown Attribute** | |
| 8.1 | Use browser dev tools to inject invalid attribute | (Alternative: Test via direct API call) |
| 8.2 | Send PATCH request with unknown attribute | API returns 400 error: "unknown custom attribute" |

### Expected Results - Validation Failure

| Category | Expected Outcome |
|----------|------------------|
| **Client-Side Validation** | - Error message displayed for out-of-range value<br>- Save button disabled or submission blocked<br>- Error shown in red with clear message |
| **Server-Side Validation** | - API returns 400 Bad Request<br> - Error message: "Validation error" with details about invalid custom attribute<br>- Sample not updated |
| **Sample Record** | - `custom_attributes` unchanged (no update performed) |
| **UI Feedback** | - Error alert displayed with validation details |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Custom attribute fields dynamically rendered | ✓ | ✗ |
| Valid values accepted and saved | ✓ | ✗ |
| Invalid values rejected with clear errors | ✓ | ✗ |
| Client-side validation works | ✓ | ✗ |
| Server-side validation works | ✓ | ✗ |
| Unknown attributes rejected | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: RLS Denial - Non-Project User Attempts Edit

### Test Case ID
TC-SAMPLE-RLS-003

### Description
Verify Row-Level Security (RLS) prevents sample editing when user lacks project access.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:update` |
| **Project Access** | User does NOT have access to sample's project (not in `project_users` junction) |
| **Sample Exists** | Sample exists in project user has no access to |
| **Alternative User** | User with access to different project (for comparison) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician without access to sample's project | User authenticated, has `sample:update` permission |
| 2 | Navigate to `/samples` route | Samples Management page loads |
| 3 | **Verify RLS Filtering in DataGrid** | |
| 3.1 | Check samples displayed in DataGrid | Only samples from projects user has access to are shown |
| 3.2 | Verify inaccessible sample is NOT visible | Sample from inaccessible project not in list |
| 4 | **Direct API Test (Bypass UI)** | |
| 4.1 | Use API client (e.g., Postman, curl) to send GET `/samples/{id}` | Request prepared with valid JWT token |
| 4.2 | Set `{id}` to UUID of sample from inaccessible project | Request targets inaccessible sample |
| 4.3 | Send request | API processes request |
| 4.4 | Verify response | HTTP 404 Not Found (RLS hides sample) OR 403 Forbidden |
| 5 | **Attempt Update via API** | |
| 5.1 | Send PATCH `/samples/{inaccessible_sample_id}` | Request prepared with update data |
| 5.2 | Include valid JWT token | Authorization header set |
| 5.3 | Include update payload: `{"status": "uuid-of-status"}` | Request body includes status update |
| 5.4 | Send request | API processes request |
| 5.5 | Verify response | HTTP 403 Forbidden with message: "Access denied: insufficient project permissions" |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **UI Filtering** | DataGrid only shows samples from `project_users` where `user_id` = current user |
| **GET Request** | GET `/samples/{id}` returns 404 (sample not found due to RLS) OR 403 (access denied) |
| **PATCH Request** | PATCH `/samples/{id}` returns 403 Forbidden |
| **Backend Check** | `update_sample()` function checks:<br>- If user is not Administrator<br>- If `current_user.client_id` and `sample.project.client_id` don't match<br>- Raises 403 if access denied |
| **Sample Record** | No sample updated (transaction not committed) |
| **Error Handling** | Clear error message: "Access denied: insufficient project permissions" |

### Test Steps - Comparison: Accessible Sample

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Test with Accessible Sample** | |
| 6.1 | Locate sample from accessible project | Sample visible in DataGrid |
| 6.2 | Click "Edit" button | Edit dialog opens successfully |
| 6.3 | Make a change (e.g., update description) | Form accepts changes |
| 6.4 | Click "Save" | Update succeeds (HTTP 200) |
| 6.5 | Verify sample updated | DataGrid shows updated data |

### Expected Results - Accessible Sample

| Category | Expected Outcome |
|----------|------------------|
| **UI Access** | Sample visible and editable in UI |
| **API Access** | GET and PATCH requests succeed (200 OK) |
| **Update Success** | Sample updated with audit fields set |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Inaccessible sample not visible in UI | ✓ | ✗ |
| GET request returns 404 or 403 for inaccessible sample | ✓ | ✗ |
| PATCH request returns 403 for inaccessible sample | ✓ | ✗ |
| Error message is clear and informative | ✓ | ✗ |
| No sample updated for inaccessible project | ✓ | ✗ |
| Accessible sample can be edited successfully | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-2 (Sample Status Management)
- **As a** Lab Technician or Lab Manager
- **I want** to update sample statuses throughout the lifecycle
- **So that** progress is tracked accurately
- **Acceptance Criteria**:
  - Statuses: Received, Available for Testing, Testing Complete, Reviewed, Reported (from lists)
  - Updates trigger audit logs
  - Filtered views by status/project
  - API: PATCH `/samples/{id}/status`; RBAC: `sample:update`

### Workflow Document (Stage 1.5: Sample Editing)
- **Navigate to Samples Management**: User navigates to `/samples` route, DataGrid shows accessible samples (RLS filtered)
- **Open Edit Dialog**: Click "Edit" button, GET `/samples/{id}` fetches details, SampleForm dialog opens
- **Edit Sample Details**: Modify name, description, status, custom attributes (validated against active configs)
- **Submit Changes**: PATCH `/samples/{id}` with partial update, backend validates permission and RLS, updates audit fields

### UI Document (SamplesManagement.tsx, SampleForm.tsx)
- **SamplesManagement.tsx**: DataGrid listing with columns (name, status, sample_type, matrix, project, due_date, modified_at), Edit button per row, Edit dialog with SampleForm
- **SampleForm.tsx**: Reusable form component for editing sample details
  - Handles edit mode: fetches existing sample via GET `/samples/{id}`, pre-fills form, uses PATCH for updates
  - Formik/Yup validation with custom attribute validation
  - Permission-gated for `sample:update`
  - Dynamically renders custom attribute fields using `CustomAttributeField` component
  - Tooltips for user guidance

### Technical Document (PATCH /samples/{id})
- **Request Schema**: `SampleUpdate` (partial, optional fields)
  ```json
  {
    "name": "SAMPLE-001-UPDATED",
    "description": "Updated description",
    "status": "uuid",
    "custom_attributes": {
      "ph_level": 7.2,
      "notes": "Sample appears normal"
    }
  }
  ```
- **Processing Steps**:
  1. Verify sample exists
  2. Check `sample:update` permission
  3. Check project access (RLS): If user is not Administrator, verify `current_user.client_id` matches `sample.project.client_id`
  4. Validate custom attributes (if provided): `validate_custom_attributes()` checks against active configs for 'samples'
  5. Update fields (partial update)
  6. Update audit fields: `modified_by` = current user, `modified_at` = current timestamp
  7. Commit transaction
- **Error Handling**: 404 (sample not found), 403 (permission denied or RLS denies access), 400 (validation error)

### Schema (samples table)
- **status**: UUID FK to `list_entries.id` (list_id: "sample_status")
- **custom_attributes**: JSONB column (default '{}'), with GIN index for querying
- **Audit fields**: `modified_by` (UUID FK to users.id), `modified_at` (timestamp)
- **RLS**: Row-level security policies enforce project access via `project_users` junction table

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-SAMPLE-STATUS-001 | | | | |
| TC-SAMPLE-EDIT-002 | | | | |
| TC-SAMPLE-RLS-003 | | | | |

---

## Appendix: Sample Test Data

### Sample Names
- `SAMPLE-STATUS-001` (Status update test)
- `SAMPLE-EDIT-002` (Custom attributes test)
- `SAMPLE-RLS-003` (RLS test - inaccessible)

### Status Values
- `Received` (initial status)
- `Available for Testing` (target status for TC-001)
- `Testing Complete`
- `Reviewed`
- `Reported`

### Custom Attributes
- **ph_level**: Number type, min: 0, max: 14
  - Valid: `7.2`
  - Invalid: `15.5` (out of range)
- **notes**: Text type (if configured)

### Projects
- `Project Alpha` (accessible)
- `Project Beta` (inaccessible for RLS test)

