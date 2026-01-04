# UI Documentation: Accessioning Through Reporting

## Overview

This document describes the user interface components and interactions for the accessioning through reporting workflow in NimbleLIMS. The UI is built with React and Material-UI (MUI), using Formik for form management and Yup for validation.

## Technology Stack

- **Framework**: React 18+ with TypeScript
- **UI Library**: Material-UI (MUI) v5+
- **Form Management**: Formik with Yup validation
- **Date Pickers**: MUI X Date Pickers
- **State Management**: React Context API (UserContext)
- **API Communication**: Axios via `apiService`

---

## Component Architecture

### Page Components
- `AccessioningForm.tsx`: Main accessioning page with multi-step wizard
- `ResultsManagement.tsx`: Results management page with batch selection
- `SamplesManagement.tsx`: Sample management page with DataGrid listing and edit functionality
- `TestsManagement.tsx`: Test management page with DataGrid listing and edit functionality
- `ContainerManagement.tsx`: Container management page with DataGrid listing, create, and edit functionality

### Step Components (Accessioning)
- `SampleDetailsStep.tsx`: Sample and container information entry
- `TestAssignmentStep.tsx`: Test/analysis selection
- `ReviewStep.tsx`: Review and submit step

### Results Components
- `ResultsManagement.tsx`: Batch list and filtering
- `BatchResultsView.tsx`: Batch details and test selection
- `ResultsEntryTable.tsx`: Results entry table for batch

### Supporting Components
- `AliquotDerivativeDialog.tsx`: Dialog for creating aliquots/derivatives
- `CustomAttributeField.tsx`: Reusable component for rendering custom attribute fields dynamically based on data type (text, number, date, boolean, select)
- `SampleForm.tsx`: Reusable form component for editing sample details (name, description, status, custom_attributes)
  - Handles edit mode: fetches existing sample via GET /samples/{id}, pre-fills form, uses PATCH for updates
  - Simplified wizard for edits (skips creation-only steps like initial test assignment)
  - Formik/Yup validation with custom attribute validation
  - Permission-gated for sample:update
  - Tooltips for user guidance (e.g., "Edit status: Requires sample:update permission")
- `TestForm.tsx`: Reusable form component for test details (status, technician_id, custom_attributes)
  - Handles both create and edit modes based on `test` prop
  - Fetches lookup data (analyses, statuses, users) for dropdowns
  - Dynamically renders custom attribute fields using `CustomAttributeField`
  - Permission-gated for test:update
  - Tooltips for user guidance
- `ContainerForm.tsx`: Reusable form component for container details (name, type_id, concentration, custom_attributes)
  - Handles both create and edit modes based on `container` prop
  - Fetches lookup data (container types, units) for dropdowns
  - Dynamically renders custom attribute fields
  - Permission-gated for sample:update (since containers link to samples)
  - Tooltips for user guidance

### Help Components
- `ClientHelpSection.tsx`: Role-filtered help content component for Client users
  - Displays help entries in accordion format (Material-UI Accordion)
  - Fetches help entries via GET /help?role=Client API endpoint
  - Shows loading state while fetching
  - Handles errors gracefully with user-friendly messages
  - Displays empty state when no help content available
  - Used in `HelpPage.tsx` with conditional rendering based on user role
  - Plain language content focused on 3-5 key topics for Client users
- `LabTechHelpSection.tsx`: Role-filtered help content component for Lab Technician users
  - Displays help entries in accordion format (Material-UI Accordion)
  - Fetches help entries via GET /help?role=lab-technician API endpoint
  - Shows loading state while fetching with ARIA labels (aria-live="polite", aria-label="Loading help content")
  - Handles errors gracefully with user-friendly messages (role="alert", aria-live="assertive")
  - Displays empty state when no help content available (role="status", aria-live="polite")
  - Used in `HelpPage.tsx` with conditional rendering based on user role (user?.role === 'lab-technician')
  - Comprehensive workflow content covering accessioning, batch creation, results entry, container management, and test assignment
  - ARIA accessibility: Navigation role, labeled headings (id="lab-tech-help-heading"), accordion controls with aria-controls, aria-expanded, and aria-label attributes
- `LabManagerHelpSection.tsx`: Role-filtered help content component for Lab Manager users
  - Displays help entries in accordion format (Material-UI Accordion)
  - Fetches help entries via GET /help API endpoint (backend automatically filters by current user's role)
  - Shows loading state while fetching with ARIA labels (aria-live="polite", aria-label="Loading help content")
  - Handles errors gracefully with user-friendly messages (role="alert", aria-live="assertive")
  - Displays empty state when no help content available (role="status", aria-live="polite")
  - Used in `HelpPage.tsx` with conditional rendering based on user role (user?.role === 'Lab Manager' || user?.role === 'lab-manager')
  - Comprehensive management content covering results review, batch management, project management, quality control, and test assignment oversight
  - ARIA accessibility: Navigation role, labeled headings (id="lab-manager-help-heading"), accordion controls with aria-controls, aria-expanded, and aria-label attributes
  - Tips include: "Batch Management: Cross-project (US-25)", "Review Workflow: Approvals (US-11)"
- `AdminHelpSection.tsx`: Role-filtered help content component for Administrator users
  - Displays help entries in accordion format (Material-UI Accordion)
  - Fetches help entries via GET /help?role=administrator API endpoint
  - Shows loading state while fetching with ARIA labels (aria-live="polite", aria-label="Loading help content")
  - Handles errors gracefully with user-friendly messages (role="alert", aria-live="assertive")
  - Displays empty state when no help content available (role="status", aria-live="polite")
  - Used in `HelpPage.tsx` with conditional rendering based on user role (user?.role === 'Administrator')
  - Comprehensive administration content covering user management, EAV configuration, RLS, system configuration, data management, and getting started
  - ARIA accessibility: Navigation role, labeled headings (id="admin-help-heading"), accordion controls with aria-controls, aria-expanded, and aria-label attributes
  - Tips include: "Custom Attributes: Edit configs (post-MVP EAV)" in EAV Configuration section

### Client Management Components
- `ClientsManagement.tsx`: Client (organization) management page with DataGrid
  - Lists clients with columns: name, description, active, created_at
  - Filtering, sorting, and pagination support
  - CRUD operations (create, update, soft-delete via active=false)
  - Requires `project:manage` permission
  - Accessible via `/clients` route
  - Responsive design with mobile adaptations
- `ClientDialog.tsx`: Dialog component for creating/editing clients
  - Formik/Yup validation
  - Fields: name (required, unique), description (optional), active (toggle)
  - Client-side uniqueness validation
  - Used by ClientsManagement page

### Admin Components
- `CustomFieldsManagement.tsx`: Admin page for managing custom attribute configurations
  - Lists custom fields by entity type with filtering
  - CRUD operations for custom attribute configs
  - Requires `config:edit` permission
  - Tooltip: "Edit help: Use config:edit permission to manage help entries in Help Management"
- `CustomFieldDialog.tsx`: Dialog for creating/editing custom attribute configurations
  - Formik/Yup validation
  - Entity type selection
  - Data type selection with validation rules editor
  - Attribute name uniqueness checking
- `HelpManagement.tsx`: Admin page for managing help entries (CRUD)
  - Lists help entries in DataGrid with search and role filtering
  - Create/Edit/Delete operations for help entries
  - Requires `config:edit` permission
  - Role filter dropdown to filter by role (All Roles, Administrator, Lab Manager, Lab Technician, Client, Public)
  - Search functionality for section and content
  - Pagination support
  - Responsive design for mobile devices
  - Used in admin section sidebar navigation
- `HelpEntryDialog.tsx`: Dialog for creating/editing help entries
  - Formik/Yup validation
  - Fields: section (required), content (required, multiline), role_filter (dropdown with validation), active (switch for edits)
  - Role filter validation against existing roles
  - Used by HelpManagement page

---

## Help Management UI (Admin)

### Page: Help Management

**Location**: `frontend/src/pages/admin/HelpManagement.tsx`

**Access**: Requires `config:edit` permission. Accessible via `/admin/help` route and "Help Management" link in admin sidebar.

**Layout**:
- Material-UI DataGrid for displaying help entries
- Search bar for filtering by section or content
- Role filter dropdown (All Roles, Administrator, Lab Manager, Lab Technician, Client, Public)
- Create Help Entry button (top right)
- Edit/Delete actions in DataGrid rows
- Responsive design for mobile devices

**Features**:
- **CRUD Operations**:
  - Create: Click "Create Help Entry" → Opens HelpEntryDialog → Fill form → Submit
  - Read: View all help entries in DataGrid with pagination (users with config:edit see ALL entries by default, regardless of role_filter)
  - Update: Click Edit icon → Opens HelpEntryDialog with pre-filled data → Modify → Submit
  - Delete: Click Delete icon → Confirmation dialog → Confirm → Soft delete (sets active=false)

- **Search & Filter**:
  - Search by section name or content text
  - Filter by role (dropdown with all available roles) - when "All Roles" is selected, shows all entries; when a specific role is selected, filters by that role
  - Real-time filtering as user types

- **DataGrid Columns**:
  - Section: Help entry section name
  - Content Preview: Truncated content (first 100 characters)
  - Role: Role filter chip (colored for role-specific, outlined for public)
  - Status: Active/Inactive chip
  - Actions: Edit and Delete buttons (only visible with config:edit permission)

- **Form Dialog (HelpEntryDialog)**:
  - Section field (required, text input)
  - Content field (required, multiline textarea, 8 rows)
  - Role Filter dropdown (optional, includes "Public (No Role)" option)
  - Active switch (only shown for edit mode)
  - Formik/Yup validation
  - Role filter validation against existing roles
  - Error handling with user-friendly messages

**RBAC**:
- All CRUD operations require `config:edit` permission
- Users without permission see warning message
- Backend validates permission on all endpoints

**Integration**:
- Uses `apiService.getHelp()` with role filter for loading entries
- Uses `apiService.createHelpEntry()` for creating entries
- Uses `apiService.updateHelpEntry()` for updating entries
- Uses `apiService.deleteHelpEntry()` for soft deleting entries
- Uses `apiService.getRoles()` for role filter dropdown

**Accessibility**:
- ARIA labels on all interactive elements
- Keyboard navigation support
- Screen reader friendly DataGrid
- Form validation with accessible error messages

---

## Accessioning Workflow UI

### Page: Accessioning Form

**Location**: `frontend/src/pages/AccessioningForm.tsx`

**Layout**:
- Material-UI Stepper component showing 3 steps
- Formik form wrapper with Yup validation
- Error/success alerts at top
- Navigation buttons (Back/Next/Submit)
- **Bulk Mode Toggle**: Switch at top to enable bulk accessioning mode

**Steps**:
1. Sample Details
2. Test Assignment
3. Review & Submit

**Bulk Mode**:
- Toggle switch at top of form
- When enabled:
  - Common fields apply to all samples
  - Unique fields table for per-sample data
  - Auto-naming option (prefix + sequential number)
  - Submit button shows count: "Submit N Sample(s)"

---

### Step 1: Sample Details

**Component**: `SampleDetailsStep.tsx`

**Sections**:

#### Sample Information
- **Sample Name**: TextField (required, unique)
- **Description**: TextField (optional, multiline)
- **Due Date**: DatePicker (required)
- **Received Date**: DatePicker (required, defaults to today)
- **Sample Type**: Select dropdown (required, from `sample_types` list)
- **Status**: Select dropdown (required, from `sample_status` list)
- **Matrix**: Select dropdown (required, from `matrix_types` list)
- **Temperature**: Number input (required, validated: -273.15 to 1000°C)
- **QC Type**: Select dropdown (optional, from `qc_types` list)
- **Project**: Select dropdown (required, filtered by user access)
- **Client Project**: Select dropdown (optional, for grouping multiple projects)
- **Anomalies/Notes**: Multiline TextField (optional)

**Bulk Mode Specific** (when bulk mode enabled):
- **Auto-Name Prefix**: TextField (optional, e.g., "SAMPLE-")
- **Auto-Name Start**: Number input (default: 1)
- **Unique Fields Table**: Editable table with columns:
  - Sample Name (optional if auto-naming enabled)
  - Client Sample ID (optional)
  - Container Name (required, unique)
  - Temperature (optional, overrides common)
  - Description (optional)
  - Anomalies (optional)
  - Custom Attributes (dynamic columns based on active configs for 'samples')
- Add/Remove rows buttons
- Validation: Either names provided OR auto-name prefix configured
- Custom attributes validated per row with inline error display

**UI Features**:
- Grid layout (responsive: 2 columns on desktop, 1 on mobile)
- Required fields marked with asterisk
- Real-time validation with error messages
- Date pickers with calendar interface

#### Container Information
- **Container Type**: Select dropdown (required, from admin-configured types)
  - Shows type name and dimensions (e.g., "Tube (1x1)")
- **Container Name/Barcode**: TextField (required, unique)
  - Helper text: "Unique identifier for this container instance"
- **Row**: Number input (default: 1, min: 1)
  - Helper text: "Row position for plate-based containers"
- **Column**: Number input (default: 1, min: 1)
  - Helper text: "Column position for plate-based containers"
- **Concentration**: Number input (optional, min: 0, step: 0.01)
- **Concentration Units**: Select dropdown (optional, filtered by type: "concentration")
- **Amount**: Number input (optional, min: 0, step: 0.01)
- **Amount Units**: Select dropdown (optional, filtered by type: "mass" or "volume")

**UI Features**:
- Conditional unit dropdowns (only show relevant units)
- Helper text for optional fields
- Visual separator (Divider) between sections

#### Double Entry Validation
- **Toggle Switch**: "Enable Double Entry Validation"
- When enabled, shows:
  - **Verify Sample Name**: TextField (required)
  - **Verify Sample Type**: Select dropdown (required)
- Validation occurs in Review step

**UI Features**:
- Toggle to show/hide verification fields
- Fields cleared when toggle disabled

---

### Step 2: Test Assignment

**Component**: `TestAssignmentStep.tsx`

**Layout**:
- Grid of analysis cards (responsive: 3 columns desktop, 2 tablet, 1 mobile)
- Each card shows:
  - Checkbox for selection
  - Analysis name (bold)
  - Method name
  - Turnaround time (days)
  - Cost ($)

**UI Features**:
- **Card Selection**:
  - Click card or checkbox to toggle
  - Selected cards have blue border (2px)
  - Hover effect: border color changes
- **Selected Analyses Summary**:
  - Shows count of selected analyses
  - Chips for each selected analysis (with delete button)
  - Summary card with list of selected analyses
- **Empty State**: Message if no analyses available

**Test Battery Selection**:
- Dropdown to select test battery (optional)
- When selected, displays analyses in battery with sequence order
- Can combine battery with individual analysis selection
- System prevents duplicate test creation

---

### Step 3: Review & Submit

**Component**: `ReviewStep.tsx`

**Layout**:
- Read-only display of all entered information
- Organized by sections:
  - Sample Information
  - Container Information
  - Test Assignment
  - Double Entry Verification (if enabled)

**UI Features**:
- **Double Entry Validation**:
  - Compares name_verification with name
  - Compares sample_type_verification with sample_type
  - Shows error if mismatch
- **Submit Button**:
  - Disabled if validation fails
  - Shows loading spinner during submission
  - Text changes to "Submitting..." during submission

**Post-Submit**:
- Success message displayed
- Aliquot/Derivative dialog opens (optional)
- Form resets to initial state

---

### Aliquot/Derivative Dialog

**Component**: `AliquotDerivativeDialog.tsx`

**Purpose**: Create aliquots or derivatives from accessioned sample

**UI Features**:
- Modal dialog
- Form for creating child sample
- Inherits project/client from parent
- Option to create new container

---

## Results Entry Workflow UI

### Page: Results Management

**Location**: `frontend/src/pages/ResultsManagement.tsx`

**Layout**:
- Two views: List view and Entry view
- Filter controls at top
- Batch table with actions

#### List View

**Components**:
- **Filter Section**:
  - Status dropdown (filter by batch status)
  - "All Statuses" option
- **Batch Table**:
  - Columns: Batch Name, Description, Status, Containers, Created, Actions
  - Status shown as colored Chip:
    - Created: default (gray)
    - In Process: primary (blue)
    - Completed: success (green)
  - Actions column: "Enter Results" button

**UI Features**:
- Pagination (if implemented)
- Empty state message if no batches
- Loading spinner during data fetch
- Error alert if fetch fails

#### Entry View

**Component**: `BatchResultsView.tsx`

**Layout**:
- Batch information card at top
- Test selection dropdown
- Results entry table below

**Batch Information Card**:
- Batch name (large heading)
- Status chip (colored)
- Description
- Sample count
- Test count

**Test Selection**:
- Dropdown showing all tests in batch
- Each option shows:
  - Test name
  - Status chip (colored):
    - In Process: primary (blue)
    - In Analysis: warning (orange)
    - Complete: success (green)
- "Start Analysis" button (future functionality)

**UI Features**:
- Results saved indicator (green chip with checkmark)
- Empty states:
  - "No samples found in this batch"
  - "Select a test to enter results"

---

### Results Entry Table

**Component**: `ResultsEntryTable.tsx` (US-28: Batch Results Entry)

**Layout**:
- Table with samples as rows, custom attributes and analytes as columns
- **Custom Attribute Columns**: Dynamically rendered based on active configs for 'tests' entity type
  - Displayed before analyte columns
  - Shows test custom_attributes values (formatted by data type)
  - Read-only display (values set during test creation/update)
- Header row shows custom attribute names, then analyte names with metadata
- Each cell contains input fields for that sample-analyte combination
- **QC Sample Indicators**: QC samples highlighted with warning background color

**Table Structure**:
```
| Sample | Test | Position | Analyte 1 | Analyte 2 | ... |
|--------|------|----------|-----------|-----------|-----|
| S001   | T1   | 1,1      | [inputs]  | [inputs]  | ... |
| S002   | T1   | 1,2      | [inputs]  | [inputs]  | ... |
| QC-1   | T1   | 1,3      | [inputs]  | [inputs]  | ... (QC warning)
```

**Rows**: Each row represents a test (one test per sample-analysis combination)
**QC Indicators**: QC sample rows have warning background color and icon

**Analyte Column Header**:
- Analyte reported name (bold)
- Required chip (red, if required)
- Min/Max values (if numeric, as caption text)

**Input Fields per Cell**:
- **Raw Result**: TextField or Number input (based on data type)
  - Shows validation errors (red border, error text)
- **Reported Result**: TextField or Number input
- **Qualifiers**: Select dropdown (from `qualifiers` list)
  - "None" option available

**UI Features**:
- **Real-time Validation**:
  - Required field check
  - Numeric validation
  - Range validation (min/max)
  - Error messages shown below field
  - Validation errors displayed at top with row details
- **Auto-fill Feature** (future enhancement):
  - Button in column header to fill all rows for that analyte
- **Save Button**:
  - Top-right of table
  - Shows loading spinner during save
  - Disabled during save
  - Text: "Submit Results"
- **Success/Error Alerts**:
  - Success: "Results saved successfully"
  - Error: Shows validation errors or API error with per-row details
  - QC Warning: Shows QC failures if `FAIL_QC_BLOCKS_BATCH=false`
  - QC Error: Blocks submission if `FAIL_QC_BLOCKS_BATCH=true` and QC failures detected

**Validation Display**:
- Red border on invalid fields
- Error text below field
- Helper text for guidance
- Summary of validation errors at top of table
- QC failure indicators on QC sample rows

---

## Form Validation

### Accessioning Form Validation

**Schema**: Yup validation schema in `AccessioningForm.tsx`

**Rules**:
- **Name**: Required, string, 1-255 chars
- **Due Date**: Required, valid date
- **Received Date**: Required, valid date
- **Sample Type**: Required
- **Status**: Required
- **Matrix**: Required
- **Temperature**: Required, number, -273.15 to 1000
- **Project**: Required
- **Container Type**: Required
- **Container Name**: Required
- **Container Row/Column**: Required, integer, min: 1
- **Concentration Units**: Required if concentration provided
- **Amount Units**: Required if amount provided
- **Double Entry**:
  - Name verification: Required if double entry enabled
  - Sample type verification: Required if double entry enabled

**Validation Timing**:
- On blur (field loses focus)
- On submit
- Real-time for some fields (e.g., numeric inputs)

---

### Results Entry Validation

**Client-side Validation**:
- Required analytes must have values
- Numeric analytes must be valid numbers
- Values must be within min/max ranges (if defined)

**Server-side Validation**:
- Additional validation via `/results/validate` endpoint
- Checks against `analysis_analytes` configuration
- Significant figures warnings

**Validation Display**:
- Errors shown in red below field
- Warnings shown in orange (future enhancement)
- Save button disabled if validation errors

---

## Dynamic Field Rendering

### CustomAttributeField Component

**Location**: `frontend/src/components/common/CustomAttributeField.tsx`

**Purpose**: Reusable component for rendering custom attribute fields dynamically based on configuration.

**Props**:
- `config`: CustomAttributeConfig object with data_type and validation_rules
- `value`: Current field value
- `onChange`: Callback function for value changes
- `error`: Boolean indicating validation error
- `helperText`: Error message or description
- `fullWidth`: Boolean for full-width layout
- `size`: 'small' | 'medium'

**Rendering Logic**:
- **Text**: Renders TextField with max_length/min_length validation
- **Number**: Renders NumberField with min/max validation
- **Date**: Renders DatePicker (MUI X)
- **Boolean**: Renders Checkbox with FormControlLabel
- **Select**: Renders Select dropdown with options from validation_rules

**Integration**:
- Used in `SampleDetailsStep.tsx` for sample custom fields
- Can be extended to other forms (client projects, batches, etc.)
- Integrated with Formik for form state management
- Real-time validation using Yup schema generated from validation_rules

## User Interactions

### Accessioning Workflow

1. **Navigate to Accessioning**:
   - Click "Accessioning" in navigation menu
   - Form loads with empty state

2. **Step 1: Enter Sample Details**:
   - Fill required fields
   - Select container type and enter container name
   - Optionally enable double entry
   - Click "Next" (disabled until valid)

3. **Step 2: Assign Tests**:
   - Select analyses by clicking cards or checkboxes
   - Review selected analyses in summary
   - Click "Next"

4. **Step 3: Review**:
   - Review all information
   - Verify double entry fields (if enabled)
   - Click "Submit"
   - Wait for success message
   - Optionally create aliquot/derivative

### Results Entry Workflow

1. **Navigate to Results Management**:
   - Click "Results" in navigation menu
   - View batch list

2. **Select Batch**:
   - Optionally filter by status
   - Click "Enter Results" button on batch row
   - View batch details

3. **Select Test**:
   - Choose test from dropdown
   - View samples in batch

4. **Enter Results**:
   - Fill in result fields for each sample-analyte combination
   - See validation errors in real-time
   - Click "Save Results"
   - Wait for success confirmation

5. **Review Results** (Lab Manager):
   - Navigate to test details
   - Review all results
   - Approve test (sets status to "Complete")

### Help Access Workflow

**For Administrators**:
1. Navigate to Help page (`/help`)
2. View AdminHelpSection with administrator-specific help content
3. Click "Manage Help" button (if user has config:edit permission)
4. Redirected to Help Management page (`/admin/help`)
5. View all help entries in DataGrid (users with config:edit permission see ALL entries by default, regardless of role_filter)
6. Filter by role (select "All Roles" to see all, or select specific role to filter) or search by section/content
7. Create new help entry: Click "Create Help Entry" → Fill form → Submit
8. Edit existing entry: Click Edit icon → Modify form → Submit
9. Delete entry: Click Delete icon → Confirm → Entry soft-deleted (active=false)

**Help Management CRUD Workflow**:
1. **Create**: Click "Create Help Entry" → Dialog opens → Enter section, content, select role_filter (optional) → Submit → Entry created → Dialog closes → DataGrid refreshes
2. **Read**: View entries in DataGrid → Use search/filter to find specific entries → Click on row to view full content in tooltip
3. **Update**: Click Edit icon on row → Dialog opens with pre-filled data → Modify fields → Submit → Entry updated → Dialog closes → DataGrid refreshes
4. **Delete**: Click Delete icon on row → Confirmation dialog → Confirm → Entry soft-deleted → DataGrid refreshes → Entry no longer visible (active=false)

**Role Filter Validation**:
- When creating/editing, role_filter is validated against existing roles
- Invalid role_filter returns 400 error with list of available roles
- Role names are normalized to slug format (e.g., "Lab Technician" → "lab-technician")
- Public entries use role_filter=null

1. **Navigate to Help**:
   - Click "Help" in navigation menu (visible to all users)
   - Help page loads based on user role

2. **Client Users**:
   - See `ClientHelpSection` component with accordion-style FAQ
   - Help entries filtered by role (Client-specific and public entries)
   - Sections include: "Viewing Projects", "Viewing Samples", "Viewing Results"
   - Plain language, no technical jargon
   - Tooltips available in components like ResultsManagement

3. **Lab Technician Users**:
   - See `LabTechHelpSection` component with accordion-style help
   - Help entries filtered by role (lab-technician-specific and public entries)
   - Sections include: "Accessioning Workflow", "Batch Creation", "Results Entry", "Container Management", "Test Assignment", "Getting Started"
   - Workflow-focused content with step-by-step guidance
   - Tooltips available in accessioning and results entry components

4. **Lab Manager Users**:
   - See `LabManagerHelpSection` component with accordion-style help
   - Help entries filtered by role (lab-manager-specific and public entries)
   - Sections include: "Results Review", "Batch Management", "Project Management", "Quality Control", "Test Assignment Oversight", "Getting Started"
   - Management-focused content covering oversight and review workflows
   - Tooltips available in Results Management ("Review results: Use result:review permission") and Batch Results View ("QC at batch: US-27")

5. **Other Users**:
   - See generic help message
   - No API call made (no role-specific help content)

---

## Error Handling

### Form Errors

**Display**:
- Error messages below invalid fields
- Red border on invalid fields
- Submit button disabled if errors present

**Common Errors**:
- "Field is required"
- "Invalid format"
- "Value out of range"
- "Duplicate entry" (for unique fields)

### API Errors

**Display**:
- Alert component at top of page
- Severity: "error" (red) or "success" (green)
- Message from API response or generic message

**Error Messages**:
- 400: "Validation errors: [details]"
- 403: "Access denied: insufficient permissions"
- 404: "[Resource] not found"
- 500: "Failed to [action]. Please try again."

---

## Loading States

### Data Loading

**Indicators**:
- CircularProgress spinner
- Centered in container
- Full page overlay for initial loads

**Locations**:
- Accessioning form: During lookup data load
- Results management: During batch list load
- Results entry: During analytes load

### Form Submission

**Indicators**:
- Loading spinner in submit button
- Button text changes to "Submitting..."
- Button disabled during submission

**Locations**:
- Accessioning form submit
- Results entry save

---

## Responsive Design

### Breakpoints

**Material-UI Grid System**:
- xs: < 600px (mobile)
- sm: 600-960px (tablet)
- md: 960-1280px (desktop)
- lg: > 1280px (large desktop)

### Layout Adaptations

**Accessioning Form**:
- Desktop: 2-column grid for form fields
- Tablet: 2-column grid
- Mobile: 1-column stack

**Test Assignment**:
- Desktop: 3-column grid
- Tablet: 2-column grid
- Mobile: 1-column stack

**Results Table**:
- Horizontal scroll on mobile
- Sticky header (if implemented)
- Responsive column widths

---

## Accessibility

### ARIA Labels

- Form fields have associated labels
- Error messages linked to fields
- Button labels descriptive
- Status chips have aria-labels

### Keyboard Navigation

- Tab order follows visual flow
- Enter key submits forms
- Escape key closes dialogs
- Arrow keys navigate dropdowns

### Screen Reader Support

- All interactive elements have labels
- Status changes announced
- Error messages announced
- Loading states announced

---

## State Management

### Form State

**Formik State**:
- Form values
- Validation errors
- Touched fields
- Submission state

**Component State**:
- Active step (accessioning)
- Selected test (results)
- Loading states
- Error/success messages

### Context

**UserContext**:
- Current user information
- Authentication state
- Permissions

---

## API Integration

### Service Layer

**Component**: `apiService.ts`

**Methods Used**:
- `getListEntries(listName)`: Load dropdown options
- `getProjects()`: Load projects
- `getAnalyses()`: Load analyses
- `getContainerTypes()`: Load container types
- `getUnits()`: Load units
- `createContainer(data)`: Create container
- `createSample(data)`: Create sample
- `createContent(data)`: Link sample to container
- `createTest(data)`: Create test
- `getBatches(filters)`: Load batches
- `getBatch(batchId)`: Load batch details
- `getBatchContainers(batchId)`: Load batch containers
- `getTestsByBatch(batchId)`: Load tests for batch
- `getAnalysisAnalytes(testId)`: Load analytes for test
- `enterBatchResults(batchId, data)`: Save results
- `getHelp(filters)`: Load help entries filtered by role (e.g., `{role: 'Client'}`, `{role: 'administrator'}`)
- `getContextualHelp(section)`: Load contextual help for a specific section
- `createHelpEntry(data)`: Create new help entry (requires config:edit permission)
- `updateHelpEntry(id, data)`: Update existing help entry (requires config:edit permission)
- `deleteHelpEntry(id)`: Soft delete help entry (requires config:edit permission)

**Error Handling**:
- Try/catch blocks in components
- Error messages from API response
- Generic fallback messages

---

## Future Enhancements

### Planned UI Improvements

1. **Test Battery Selection**:
   - UI for selecting test batteries during accessioning
   - Display battery analyses with sequence
   - Option to skip optional analyses

2. **Batch Status Management**:
   - UI for updating batch status
   - Status transition buttons
   - Confirmation dialogs

3. **Results Review UI**:
   - Dedicated review page
   - Side-by-side comparison view
   - Review history

4. **Reporting UI**:
   - Mark sample as reported
   - Report generation (post-MVP)
   - Report preview

5. **Enhanced Validation**:
   - Real-time server validation
   - Significant figures warnings
   - Range violation highlights

6. **Bulk Operations**:
   - Bulk result entry
   - Bulk status updates
   - Batch operations

---

## Component File Structure

```
frontend/src/
├── pages/
│   ├── AccessioningForm.tsx
│   ├── ResultsManagement.tsx
│   ├── HelpPage.tsx
│   └── admin/
│       └── CustomFieldsManagement.tsx
├── components/
│   ├── accessioning/
│   │   ├── SampleDetailsStep.tsx
│   │   ├── TestAssignmentStep.tsx
│   │   ├── ReviewStep.tsx
│   │   └── BulkUniquesTable.tsx
│   ├── results/
│   │   ├── ResultsManagement.tsx
│   │   ├── BatchResultsView.tsx
│   │   └── ResultsEntryTable.tsx
│   ├── aliquots/
│   │   └── AliquotDerivativeDialog.tsx
│   ├── help/
│   │   └── ClientHelpSection.tsx
│   ├── admin/
│   │   └── CustomFieldDialog.tsx
│   └── common/
│       └── CustomAttributeField.tsx
├── services/
│   └── apiService.ts
└── contexts/
    └── UserContext.tsx
```

---

## Testing

### Component Tests

**Test Files**:
- `AccessioningForm.test.tsx`
- `ResultsEntryTable.test.tsx`
- `HelpPage.test.tsx`
- `HelpManagement.test.tsx`
- Component-specific test files

**Test Coverage**:
- Form validation
- User interactions
- API integration
- Error handling
- Role-based rendering (e.g., Client help vs. general help)

### UI Testing

**Manual Testing Checklist**:
- [ ] Accessioning form validation
- [ ] Multi-step navigation
- [ ] Results entry validation
- [ ] Error message display
- [ ] Loading states
- [ ] Responsive layout
- [ ] Keyboard navigation
- [ ] Screen reader compatibility

