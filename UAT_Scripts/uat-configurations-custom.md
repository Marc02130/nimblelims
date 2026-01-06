# UAT Scripts: Configurations and Custom Fields

## Overview

This document contains User Acceptance Testing (UAT) scripts for configurations and custom fields in NimbleLIMS. These scripts validate list management, custom field creation, and dynamic form rendering as defined in:

- **User Stories**: US-15 (Configurable Lists), US-16 to US-23 (Configurations), Post-MVP Custom Fields
- **PRD**: Section 4.5 (Custom Fields)
- **UI Document**: `ui-accessioning-to-reporting.md` (CustomFieldsManagement.tsx, ListsManagement.tsx)
- **Technical Document**: `technical-accessioning-to-reporting.md` (custom_attributes_config table)
- **API Document**: `api_endpoints.md` (CRUD `/admin/custom-attributes`, `/lists`)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Roles: Administrator with `config:edit` permission
  - Lists: At least one list exists (e.g., `sample_status` with entries)
  - No custom attribute configurations exist initially (for creation test)
- Test user accounts:
  - Administrator with `config:edit` permission
  - Lab Technician without `config:edit` permission (for permission denial test)

---

## Test Case 1: List Editing - Add Status Entry

### Test Case ID
TC-LIST-EDIT-001

### Description
Add a new entry to an existing list (e.g., sample status) via the admin interface.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Administrator |
| **Required Permission** | `config:edit` |
| **List Exists** | At least one list exists (e.g., `sample_status` list) |
| **List Management UI** | Lists Management page accessible at `/admin/lists` |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Administrator | User authenticated with `config:edit` permission |
| 2 | Navigate to Lists Management page (e.g., `/admin/lists`) | Lists Management page loads |
| 3 | **Locate List** | |
| 3.1 | Locate list: `sample_status` | List visible in list table or expandable view |
| 3.2 | Click on list or "View Entries" button | List entries view opens |
| 3.3 | Verify existing entries displayed | Current entries visible (e.g., "Received", "Available for Testing", "Reviewed") |
| 4 | **Add New Entry** | |
| 4.1 | Click "Add Entry" or "Create Entry" button | Entry creation dialog/form opens |
| 4.2 | Enter entry name: `On Hold` | Field accepts input |
| 4.3 | Enter description (optional): `Sample is on hold pending additional information` | Field accepts input |
| 4.4 | Verify active checkbox: `true` (checked) | Checkbox checked by default |
| 4.5 | Click "Save" or "Create" button | Form submits, loading spinner shown |
| 5 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/lists/{list_name}/entries` called with:<br>```json
{
  "name": "On Hold",
  "description": "Sample is on hold pending additional information",
  "active": true
}
```<br>Where `list_name` = "sample_status" (normalized) |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify user has `config:edit` permission<br>2. **List Validation**:<br>   - Get list by normalized name (e.g., "sample_status")<br>   - Verify list exists and is active<br>3. **Entry Validation**:<br>   - Check unique constraint: (list_id, name) must be unique<br>   - Return 400 if entry name already exists in list<br>4. **Entry Creation**:<br>   - Create `ListEntry` record:<br>     - `list_id` = list UUID<br>     - `name` = "On Hold"<br>     - `description` = "Sample is on hold pending additional information"<br>     - `active` = true<br>     - `created_by` = current user UUID<br>     - `modified_by` = current user UUID<br>5. **Commit**:<br>   - Commit to database<br>   - Return created entry |
| **List Entry Record** | - Entry created in `list_entries` table:<br>  - `list_id` = sample_status list UUID<br>  - `name` = "On Hold"<br>  - `description` = "Sample is on hold pending additional information"<br>  - `active` = true<br>  - Audit fields set |
| **UI Feedback** | - Success message: "Entry created successfully"<br>- Entry appears in list entries view<br>- Entry available in dropdowns (e.g., sample status dropdown) |
| **List Query** | - GET `/lists/sample_status/entries` returns new entry in response<br>- Entry visible in all list queries |

### Test Steps - Edit Entry (Optional)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Edit Existing Entry** | |
| 6.1 | Click "Edit" button on entry | Edit dialog opens with pre-filled data |
| 6.2 | Update description: `Sample is on hold pending additional information or approval` | Field accepts input |
| 6.3 | Click "Save" | Form submits |
| 6.4 | Verify entry updated | Entry description updated in list view |

### Expected Results - Edit Entry

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/lists/{list_name}/entries/{entry_id}` called with:<br>```json
{
  "description": "Sample is on hold pending additional information or approval"
}
``` |
| **Entry Update** | - Entry `description` updated<br>- `modified_by` and `modified_at` updated |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| List entry created successfully | ✓ | ✗ |
| Entry name unique within list | ✓ | ✗ |
| Entry visible in list entries view | ✓ | ✗ |
| Entry available in dropdowns | ✓ | ✗ |
| Audit fields set correctly | ✓ | ✗ |
| Entry can be edited | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Custom Field Creation - For Samples Entity

### Test Case ID
TC-CUSTOM-FIELD-CREATE-002

### Description
Create a new custom attribute configuration for the 'samples' entity type via the admin interface.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Administrator |
| **Required Permission** | `config:edit` |
| **Custom Fields UI** | Custom Fields Management page accessible at `/admin/custom-fields` |
| **No Existing Config** | No custom attribute configuration exists for `entity_type='samples'` and `attr_name='ph_level'` |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Administrator | User authenticated with `config:edit` permission |
| 2 | Navigate to Custom Fields Management page (e.g., `/admin/custom-fields`) | Custom Fields Management page loads |
| 3 | **Verify Page Loads** | |
| 3.1 | Verify DataGrid displays | DataGrid shows existing custom attribute configurations (if any) |
| 3.2 | Verify filter controls | Filter by entity type dropdown visible |
| 3.3 | Verify "Add Custom Field" button | Button visible and enabled |
| 4 | **Create Custom Field** | |
| 4.1 | Click "Add Custom Field" button | Custom field creation dialog opens |
| 4.2 | **Enter Field Information** | |
| 4.2.1 | Select Entity Type: `samples` from dropdown | Entity type selected |
| 4.2.2 | Enter Attribute Name: `ph_level` | Field accepts input (alphanumeric, underscores, hyphens) |
| 4.2.3 | Select Data Type: `number` from dropdown | Data type selected (options: text, number, date, boolean, select) |
| 4.2.4 | **Enter Validation Rules** | |
| 4.2.4.1 | Enter Min Value: `0` | Field accepts numeric input |
| 4.2.4.2 | Enter Max Value: `14` | Field accepts numeric input |
| 4.2.5 | Enter Description: `pH level of the sample (0-14 scale)` | Field accepts input |
| 4.2.6 | Verify Active checkbox: `true` (checked) | Checkbox checked by default |
| 4.3 | Click "Create" or "Save" button | Form submits, loading spinner shown |
| 5 | Wait for API response | Success message displayed |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | POST `/admin/custom-attributes` called with:<br>```json
{
  "entity_type": "samples",
  "attr_name": "ph_level",
  "data_type": "number",
  "validation_rules": {
    "min": 0,
    "max": 14
  },
  "description": "pH level of the sample (0-14 scale)",
  "active": true
}
``` |
| **Backend Processing** | 1. **Access Control**:<br>   - Verify user has `config:edit` permission<br>2. **Validation**:<br>   - Validate `entity_type` is one of: samples, tests, results, projects, client_projects, batches<br>   - Validate `attr_name` format (alphanumeric, underscores, hyphens)<br>   - Validate `data_type` is one of: text, number, date, boolean, select<br>   - Validate `validation_rules` match data_type:<br>     - Number: `min`, `max` (numbers, min must be <= max)<br>     - Text: `max_length`, `min_length` (integers)<br>     - Date: `min_date`, `max_date` (ISO date strings YYYY-MM-DD, min_date must be <= max_date)<br>     - Select: `options` (array of strings, non-empty)<br>3. **Uniqueness Check**:<br>   - Check unique constraint: (entity_type, attr_name) must be unique<br>   - Query: `SELECT * FROM custom_attributes_config WHERE entity_type = 'samples' AND attr_name = 'ph_level'`<br>   - Return 400 if configuration already exists<br>4. **Configuration Creation**:<br>   - Create `CustomAttributeConfig` record:<br>     - `entity_type` = "samples"<br>     - `attr_name` = "ph_level"<br>     - `data_type` = "number"<br>     - `validation_rules` = {"min": 0, "max": 14}<br>     - `description` = "pH level of the sample (0-14 scale)"<br>     - `active` = true<br>     - `created_by` = current user UUID<br>     - `modified_by` = current user UUID<br>5. **Commit**:<br>   - Commit to database<br>   - Return created configuration |
| **Configuration Record** | - Configuration created in `custom_attributes_config` table:<br>  - `entity_type` = "samples"<br>  - `attr_name` = "ph_level"<br>  - `data_type` = "number"<br>  - `validation_rules` = {"min": 0, "max": 14} (JSONB)<br>  - `description` = "pH level of the sample (0-14 scale)"<br>  - `active` = true<br>  - Audit fields set |
| **UI Feedback** | - Success message: "Custom field created successfully"<br>- Configuration appears in DataGrid<br>- Configuration visible when filtering by entity_type='samples' |

### Test Steps - Validation Errors (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Test Validation Errors** | |
| 6.1 | Attempt to create duplicate: same entity_type and attr_name | Form submits |
| 6.2 | Verify error response | HTTP 400 Bad Request:<br>- Error message: "Custom attribute 'ph_level' already exists for entity type 'samples'" |
| 6.3 | Attempt invalid data_type: `invalid_type` | Form validation prevents submission or returns error |
| 6.4 | Attempt invalid attr_name: `ph level` (with space) | Form validation prevents submission or returns error: "attr_name must contain only alphanumeric characters, underscores, and hyphens" |

### Expected Results - Validation Errors

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 400 Bad Request<br>- Clear error message indicating validation failure<br>- No configuration created |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Custom field configuration created successfully | ✓ | ✗ |
| Unique constraint enforced (entity_type, attr_name) | ✓ | ✗ |
| Validation rules stored correctly | ✓ | ✗ |
| Configuration visible in DataGrid | ✓ | ✗ |
| Audit fields set correctly | ✓ | ✗ |
| Validation errors prevent duplicate creation | ✓ | ✗ |
| Invalid data rejected with clear errors | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Custom Field Usage and Validation in Form

### Test Case ID
TC-CUSTOM-FIELD-USAGE-003

### Description
Verify that custom fields are dynamically rendered in forms and validated against configurations during sample creation/editing.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician |
| **Required Permission** | `sample:create` or `sample:update` |
| **Custom Field Configured** | At least one active custom attribute configuration exists for `entity_type='samples'`:<br>- `attr_name` = "ph_level"<br>- `data_type` = "number"<br>- `validation_rules` = {"min": 0, "max": 14} |
| **Sample Form** | Sample creation or editing form accessible (e.g., `/accessioning` or `/samples/{id}/edit`) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician | User authenticated |
| 2 | Navigate to sample creation page (e.g., `/accessioning`) | Sample creation form loads |
| 3 | **Verify Custom Fields Section** | |
| 3.1 | Locate "Custom Fields" section in form | Section visible below standard fields |
| 3.2 | Verify custom field rendered | Field for "ph_level" visible:<br>- Label: "pH level" or "ph_level"<br>- Input type: Number input (for number data type) |
| 3.3 | Verify description displayed | Description tooltip or helper text: "pH level of the sample (0-14 scale)" |
| 4 | **Enter Valid Value** | |
| 4.1 | Enter ph_level: `7.5` | Field accepts input |
| 4.2 | Verify no validation error | No error message displayed |
| 4.3 | Fill in other required fields | Standard fields completed |
| 4.4 | Click "Submit" or "Create" button | Form submits |
| 4.5 | Wait for API response | Success message displayed |
| 5 | **Test Validation Errors** | |
| 5.1 | Start new sample creation | Form loads |
| 5.2 | Enter ph_level: `15.0` (exceeds max of 14) | Field accepts input |
| 5.3 | Verify validation error | Real-time validation error displayed:<br>- Error message: "Value must be at most 14"<br>- Field highlighted in red<br>- Error appears on blur (when field loses focus) and on change |
| 5.4 | Enter ph_level: `-1.0` (below min of 0) | Field accepts input |
| 5.5 | Verify validation error | Real-time validation error displayed:<br>- Error message: "Value must be at least 0"<br>- Error appears on blur and on change |
| 5.6 | Fix value to `7.5` | Error message disappears |
| 5.7 | Submit form | Form submits successfully |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Custom Fields Loading** | - Frontend fetches active custom attribute configurations:<br>  - API call: GET `/admin/custom-attributes?entity_type=samples&active=true`<br>  - Returns configurations for 'samples' entity type<br>- Dynamic rendering based on `data_type`:<br>  - `text` → TextField<br>  - `number` → NumberField<br>  - `date` → DatePicker<br>  - `boolean` → Checkbox<br>  - `select` → Select dropdown with options from `validation_rules.options` |
| **Form Integration** | - Custom fields included in Formik form values<br>- Custom fields included in form submission<br>- Yup validation schema generated from `validation_rules` |
| **Client-Side Validation** | - Real-time validation using Yup:<br>  - Number: `min()`, `max()` validators with transforms to handle NaN and empty strings<br>  - Text: `maxLength()`, `minLength()` validators<br>  - Date: `min_date`, `max_date` validators with string-to-Date transforms<br>  - Select: `oneOf()` validator<br>- Validation triggers: `validateOnChange` and `validateOnBlur` enabled<br>- Error messages displayed inline with specific messages:<br>  - Number: "Value must be at least {min}" or "Value must be at most {max}"<br>  - Date: "Date must be on or after {min_date}" or "Date must be on or before {max_date}"<br>  - Text: "Minimum length is {min_length}" or "Maximum length is {max_length}" |
| **API Call** | POST `/samples` or PATCH `/samples/{id}` called with:<br>```json
{
  "name": "SAMPLE-001",
  "sample_type": "uuid",
  "status": "uuid",
  "matrix": "uuid",
  "project_id": "uuid",
  "custom_attributes": {
    "ph_level": 7.5
  }
}
``` |
| **Backend Validation** | 1. **Custom Attributes Validation**:<br>   - Call `validate_custom_attributes(db, 'samples', custom_attributes)`<br>   - Fetch active configs for 'samples' entity type<br>   - For each attribute in `custom_attributes`:<br>     - Verify `attr_name` exists in active configs<br>     - Verify `data_type` matches config<br>     - Verify value matches `validation_rules`:<br>       - Number: Check min/max<br>       - Text: Check length<br>       - Select: Check options<br>   - Return 400 with detailed errors if validation fails<br>2. **Sample Creation/Update**:<br>   - Create/update sample with `custom_attributes` JSONB field<br>   - Store as: `{"ph_level": 7.5}` |
| **Database Storage** | - Sample record created/updated with:<br>  - `custom_attributes` = `{"ph_level": 7.5}` (JSONB)<br>  - GIN index on `custom_attributes` enables efficient querying |
| **UI Feedback** | - Success message displayed<br> - Sample created/updated with custom attributes<br> - Custom attributes visible in sample details view |

### Test Steps - Querying Custom Attributes

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Test Custom Attribute Querying** | |
| 6.1 | Navigate to samples list page | Samples list loads |
| 6.2 | Filter by custom attribute: `?custom.ph_level=7.5` | Filter applied |
| 6.3 | Verify filtered results | Only samples with `custom_attributes.ph_level = 7.5` displayed |
| 6.4 | Verify query uses JSONB operator | Backend query uses: `custom_attributes @> '{"ph_level": 7.5}'::jsonb` |

### Expected Results - Querying

| Category | Expected Outcome |
|----------|------------------|
| **Query Parameter** | - GET `/samples?custom.ph_level=7.5`<br>- Backend parses `custom.*` query parameters<br>- Converts to JSONB query: `custom_attributes @> '{"ph_level": 7.5}'::jsonb` |
| **Database Query** | - Uses GIN index on `custom_attributes` column<br> - Efficient querying of JSONB data |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Custom fields dynamically rendered in form | ✓ | ✗ |
| Field type matches data_type configuration | ✓ | ✗ |
| Client-side validation works (min/max) | ✓ | ✗ |
| Server-side validation works | ✓ | ✗ |
| Custom attributes saved in JSONB column | ✓ | ✗ |
| Custom attributes queryable via ?custom.attr_name=value | ✓ | ✗ |
| Validation errors prevent invalid submission | ✓ | ✗ |
| Valid values accepted and saved | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-15 (Configurable Lists)
- **As an** Administrator
- **I want** to manage lists for statuses, types, etc.
- **So that** the system is flexible
- **Acceptance Criteria**:
  - Lists/list_entries tables; modifiable via UI/API
  - Used for sample_type, status, qc_type, units type (concentration, mass, volume, molar)
  - API: CRUD `/lists`; RBAC: `config:edit`

### User Stories US-16 to US-23 (Configurations)
- **US-16**: Units Management (CRUD /units)
- **US-17**: Analyses Management (CRUD /analyses)
- **US-18**: Analytes Management (CRUD /analytes)
- **US-19**: Analysis-Analyte Configuration (CRUD /analyses/{id}/analyte-rules)
- **US-20**: Users Management (CRUD /users)
- **US-21**: Container Types Management (CRUD /containers/types)
- **US-22**: Test Batteries Management (CRUD /test-batteries)
- **US-23**: Test Battery Assignment in Accessioning

### Post-MVP Custom Fields
- **As an** Administrator
- **I want** to define custom attributes for samples, tests, results, projects, client_projects, and batches without schema changes
- **So that** the system can be customized for laboratory-specific requirements
- **Acceptance Criteria**:
  - Admin interface for creating custom attribute configurations (entity_type, attr_name, data_type, validation_rules)
  - Support for data types: text, number, date, boolean, select
  - Validation rules: min/max for numbers, length for text, options for select
  - Dynamic field rendering in forms based on configurations
  - Server-side validation against active configurations
  - Custom attributes stored in JSONB columns with GIN indexes for querying
  - List endpoints support filtering via `?custom.attr_name=value`
  - API: CRUD `/admin/custom-attributes`; RBAC: `config:edit`

### PRD Section 4.5 (Custom Fields)
- **Purpose**: Enable administrators to define custom attributes for various entity types without schema changes
- **Functional Requirements**:
  1. Custom Field Definition: Administrators can create custom attribute configurations via admin interface
  2. Custom Field Usage: Custom fields appear in relevant forms/views based on entity type, with dynamic rendering and real-time validation
  3. Entity Support: Samples, Tests, Results, Projects, Client Projects, Batches
  4. Querying: List endpoints support filtering by custom attributes: `?custom.attr_name=value`
  5. Bulk Mode: Custom fields can be included in bulk unique fields table

### UI Document (CustomFieldsManagement.tsx)
- **Component**: `CustomFieldsManagement.tsx`
- **Location**: `/admin/custom-fields`
- **Features**:
  - DataGrid displaying custom attribute configurations
  - Filter by entity type
  - Search functionality
  - CRUD dialogs for creating/editing custom fields
  - Delete confirmation dialog
- **CustomFieldDialog.tsx**: Dialog for creating/editing custom attribute configurations
  - Entity type dropdown
  - Attribute name input
  - Data type dropdown
  - Validation rules inputs (dynamic based on data type)
  - Description input
  - Active checkbox

### Technical Document (custom_attributes_config table)
- **Table**: `custom_attributes_config`
- **Fields**:
  - `id`: UUID PK
  - `entity_type`: String (samples, tests, results, projects, client_projects, batches)
  - `attr_name`: String (unique within entity_type)
  - `data_type`: String (text, number, date, boolean, select)
  - `validation_rules`: JSONB (min/max for numbers, length for text, options for select)
  - `description`: Text (nullable)
  - `active`: Boolean (default true)
  - Audit fields: `created_at`, `created_by`, `modified_at`, `modified_by`
- **Unique Constraint**: (`entity_type`, `attr_name`)
- **Indexes**: `idx_custom_attributes_config_entity_type`, `idx_custom_attributes_config_active`

### API Endpoints
- **GET `/admin/custom-attributes`**: List custom attribute configurations with filtering (entity_type, active, pagination)
  - Requires: `config:edit` permission
- **POST `/admin/custom-attributes`**: Create new custom attribute configuration
  - Requires: `config:edit` permission
  - Request: `{entity_type, attr_name, data_type, validation_rules, description, active}`
- **GET `/admin/custom-attributes/{id}`**: Get specific configuration
  - Requires: `config:edit` permission
- **PATCH `/admin/custom-attributes/{id}`**: Update configuration
  - Requires: `config:edit` permission
- **DELETE `/admin/custom-attributes/{id}`**: Soft-delete configuration (sets active=false)
  - Requires: `config:edit` permission
- **GET `/lists/{list_name}/entries`**: Get entries for a list
- **POST `/lists/{list_name}/entries`**: Add entry to list (requires `config:edit`)
- **PATCH `/lists/{list_name}/entries/{entry_id}`**: Update entry (requires `config:edit`)
- **DELETE `/lists/{list_name}/entries/{entry_id}`**: Soft-delete entry (requires `config:edit`)

### Validation
- **Server-Side**: `app.core.custom_attributes.validate_custom_attributes()`
  - Validates against active `custom_attributes_config` for entity type
  - Checks data type, validation rules (min/max for numbers, min_length/max_length for text, min_date/max_date for dates, options for select)
  - Returns validated dict or raises HTTPException with detailed errors
- **Client-Side**: Yup validation schema generated from `validation_rules`
  - Schema structure: `{ custom_attributes: Yup.object().shape({ attr_name: fieldSchema }).noUnknown(true).nullable() }`
  - Uses `useMemo` to ensure schema updates when configs change
  - Real-time validation in forms with `validateOnChange` and `validateOnBlur` enabled
  - Transforms for number fields (handle NaN, empty strings) and date fields (string-to-Date conversion)
  - Error messages displayed inline with specific messages for each validation rule

### Schema
- **`custom_attributes_config` table**:
  - `entity_type`: String (indexed)
  - `attr_name`: String
  - `data_type`: String
  - `validation_rules`: JSONB
  - `description`: Text (nullable)
  - `active`: Boolean (indexed)
  - Unique constraint: (`entity_type`, `attr_name`)
- **Entity tables with `custom_attributes` JSONB column**:
  - `samples`, `tests`, `results`, `projects`, `client_projects`, `batches`
  - GIN indexes on all `custom_attributes` columns for efficient querying

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-LIST-EDIT-001 | | | | |
| TC-CUSTOM-FIELD-CREATE-002 | | | | |
| TC-CUSTOM-FIELD-USAGE-003 | | | | |

---

## Appendix: Sample Test Data

### Lists
- `sample_status` (list for sample statuses)
  - Entries: "Received", "Available for Testing", "Testing Complete", "Reviewed", "Reported"

### Custom Attribute Configurations
- Entity Type: `samples`
  - `attr_name`: "ph_level"
  - `data_type`: "number"
  - `validation_rules`: {"min": 0, "max": 14}
  - `description`: "pH level of the sample (0-14 scale)"

### Entity Types
- `samples` (for sample custom attributes)
- `tests` (for test custom attributes)
- `results` (for result custom attributes)
- `projects` (for project custom attributes)
- `client_projects` (for client project custom attributes)
- `batches` (for batch custom attributes)

### Data Types
- `text` (TextField)
- `number` (NumberField)
- `date` (DatePicker)
- `boolean` (Checkbox)
- `select` (Select dropdown)

### Validation Rules Examples
- **Number**: `{"min": 0, "max": 14}` (min must be <= max)
- **Text**: `{"min_length": 1, "max_length": 255}`
- **Date**: `{"min_date": "2023-01-01", "max_date": "2023-12-31"}` (ISO format YYYY-MM-DD, min_date must be <= max_date)
- **Select**: `{"options": ["Option 1", "Option 2", "Option 3"]}` (non-empty array)

