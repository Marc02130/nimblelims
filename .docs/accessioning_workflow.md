# Sample Accessioning Workflow Documentation

## Overview

The sample accessioning workflow enables Lab Technicians to receive, inspect, and enter new samples into the LIMS system. This workflow implements **US-1: Sample Accessioning** from the user stories and covers the complete process from sample receipt to test assignment and release.

## Workflow Steps

### 1. Sample Details Entry

**Purpose**: Capture all required sample information during receipt.

**Required Fields**:
- **Sample Name**: Unique identifier for the sample (required)
- **Description**: Optional notes about the sample
- **Due Date**: When results are due (required)
- **Received Date**: When the sample was received (required, defaults to today)
- **Sample Type**: Type of sample from configured list (required)
- **Status**: Initial status from sample_status list (required)
- **Matrix**: Sample matrix type from configured list (required)
- **Temperature**: Storage temperature in °C (required, validated: -273.15 to 1000°C)
- **Project**: Project the sample belongs to (required)
- **QC Type**: Optional QC classification (Sample, Positive Control, Negative Control, etc.)

**Optional Fields**:
- **Anomalies/Notes**: Text field for documenting any issues found during inspection

**Double Entry Validation** (Optional):
- Toggle to enable double-entry verification
- When enabled, requires re-entry of:
  - Sample Name (must match original)
  - Sample Type (must match original)
- Validation occurs in the Review step before submission

**Component**: `frontend/src/components/accessioning/SampleDetailsStep.tsx`

### 2. Test Assignment

**Purpose**: Assign analyses/tests to be performed on the sample.

**Process**:
- Display all available analyses with details:
  - Analysis name
  - Method
  - Turnaround time (days)
  - Cost
- User selects analyses via checkboxes or card selection
- Selected analyses are displayed in a summary view
- At least one analysis can be selected (validation allows zero for flexibility)

**Component**: `frontend/src/components/accessioning/TestAssignmentStep.tsx`

### 3. Review & Submit

**Purpose**: Review all entered information before final submission.

**Review Sections**:
1. **Sample Details**: All sample information entered in Step 1
2. **Container Details**: Container information (name, type, concentration, amount, units)
3. **Test Assignment**: Summary of selected analyses
4. **Double Entry Validation**: If enabled, shows comparison of original vs. verified fields

**Validation**:
- All required fields must be completed
- Double-entry fields must match if validation is enabled
- Form validation prevents submission if errors exist

**Component**: `frontend/src/components/accessioning/ReviewStep.tsx`

## Backend Processing

### API Endpoint

**POST** `/samples/accession`

**Request Schema**: `SampleAccessioningRequest`
```python
{
    "name": str,                    # Required, 1-255 chars
    "description": Optional[str],
    "due_date": datetime,           # Required
    "received_date": datetime,       # Required
    "sample_type": UUID,            # Required, FK to list_entries
    "matrix": UUID,                 # Required, FK to list_entries
    "temperature": Optional[float], # Validated: -273.15 to 1000
    "project_id": UUID,             # Required
    "qc_type": Optional[UUID],      # FK to list_entries
    "anomalies": Optional[str],
    "double_entry_required": bool,   # Default: False
    "assigned_tests": List[UUID]    # List of analysis IDs
}
```

**Response**: `SampleResponse` with created sample data

**Implementation**: `backend/app/routers/samples.py::accession_sample()`

### Processing Steps

1. **Access Control Check**:
   - Verifies user has `sample:create` permission
   - Checks project access via `project_users` junction table
   - Administrators bypass project checks

2. **Status Assignment**:
   - Automatically sets sample status to "Received" (from `sample_status` list)
   - Validates that "Received" status exists in configuration

3. **Sample Creation**:
   - Creates sample record with all provided data
   - Sets audit fields (`created_by`, `modified_by` to current user)
   - Uses `db.flush()` to get sample ID before committing

4. **Test Assignment**:
   - For each analysis ID in `assigned_tests`:
     - Creates a `Test` record linked to the sample
     - Sets test status to "In Process" (from `test_status` list)
     - Assigns `technician_id` to current user
     - Sets audit fields

5. **Transaction Commit**:
   - Commits all changes in a single transaction
   - Returns created sample with all relationships

### Frontend Submission Flow

The frontend performs additional operations beyond the `/accession` endpoint:

1. **Create Sample**: `POST /samples` with sample data
2. **Create Container**: `POST /containers` with container details
3. **Link Sample to Container**: `POST /contents` to create the relationship
4. **Create Tests**: `POST /tests` for each selected analysis

**Note**: The frontend uses separate API calls rather than the dedicated `/accession` endpoint. This allows for more granular error handling and step-by-step progress.

**Implementation**: `frontend/src/pages/AccessioningForm.tsx::handleSubmit()`

## Data Flow Diagram

```
User Input
    ↓
[Step 1: Sample Details]
    ↓ (validation)
[Step 2: Test Assignment]
    ↓ (validation)
[Step 3: Review & Submit]
    ↓
Frontend API Calls:
    ├─ POST /samples → Create sample
    ├─ POST /containers → Create container
    ├─ POST /contents → Link sample to container
    └─ POST /tests (for each analysis) → Create tests
    ↓
Backend Processing:
    ├─ Validate permissions (sample:create)
    ├─ Check project access
    ├─ Create sample record
    ├─ Create container record
    ├─ Create content junction
    └─ Create test records
    ↓
Success Response
    ↓
[Optional: Aliquot/Derivative Dialog]
```

## Status Transitions

### Sample Status Flow

1. **Received** (Initial): Sample is accessioned and entered into system
2. **Available for Testing**: Sample is ready for analysis (set during review/release)
3. **Testing Complete**: All tests are finished
4. **Reviewed**: Results have been reviewed by Lab Manager
5. **Reported**: Results have been reported to client

### Test Status Flow

1. **In Process** (Initial): Test is assigned and ready for analysis
2. **In Analysis**: Test is currently being performed
3. **Complete**: Test is finished and results are entered

## Permissions Required

- **sample:create**: Required to create samples
- **test:assign**: Required to assign tests (implicit in sample creation)
- **Project Access**: User must have access to the selected project via `project_users` table

## Validation Rules

### Frontend Validation (Yup Schema)

- Sample name: Required, non-empty
- Due date: Required, valid date
- Received date: Required, valid date
- Sample type: Required
- Status: Required
- Matrix: Required
- Temperature: Required, number
- Project: Required
- Container type: Required
- Container name: Required
- Concentration/Amount: Must be positive numbers
- Units: Required for concentration and amount
- Double-entry fields: Required if double-entry is enabled

### Backend Validation

- Date validation: Dates cannot be in the future
- Temperature validation: -273.15°C to 1000°C
- Project access: User must have access to project
- Status existence: "Received" status must exist in configuration
- Test status existence: "In Process" status must exist for tests

## Error Handling

### Common Errors

1. **403 Forbidden**: User lacks `sample:create` permission or project access
2. **400 Bad Request**: 
   - Invalid date (future date)
   - Invalid temperature range
   - Missing required status in configuration
   - Validation errors in request data
3. **404 Not Found**: Project, sample type, or other referenced entities not found

### Frontend Error Display

- Errors are displayed in an Alert component at the top of the form
- Validation errors appear inline on form fields
- Submission errors show detailed messages from API response

## Post-Accessioning Actions

After successful accessioning:

1. **Aliquot/Derivative Creation**: 
   - Dialog opens automatically to allow creating aliquots or derivatives
   - User can create child samples linked to the parent
   - Component: `AliquotDerivativeDialog`

2. **Form Reset**: 
   - Form returns to Step 1
   - User can accession another sample

## Configuration Dependencies

The workflow requires the following configured lists:

- **sample_types**: List of sample type options
- **sample_status**: List of status options (must include "Received")
- **matrix_types**: List of matrix options
- **qc_types**: List of QC type options (optional)
- **test_status**: List of test status options (must include "In Process")
- **container_types**: List of container type options
- **units**: List of measurement units for concentration and amount

## API Reference

### Endpoints Used

1. **GET /lists/{list_name}/entries**: Load dropdown options
   - `sample_types`, `sample_status`, `matrix_types`, `qc_types`, `container_types`
2. **GET /units**: Load available units
3. **GET /projects**: Load accessible projects
4. **GET /analyses**: Load available analyses
5. **POST /samples**: Create sample record
6. **POST /containers**: Create container record
7. **POST /contents**: Link sample to container
8. **POST /tests**: Create test records

## Related User Stories

- **US-1**: Sample Accessioning (Primary)
- **US-2**: Sample Status Management
- **US-3**: Create Aliquots/Derivatives
- **US-4**: QC Sample Handling
- **US-5**: Container Management
- **US-7**: Assign Tests to Samples

## Implementation Files

### Frontend
- `frontend/src/pages/AccessioningForm.tsx`: Main form component
- `frontend/src/components/accessioning/SampleDetailsStep.tsx`: Step 1 component
- `frontend/src/components/accessioning/TestAssignmentStep.tsx`: Step 2 component
- `frontend/src/components/accessioning/ReviewStep.tsx`: Step 3 component
- `frontend/src/services/apiService.ts`: API service methods

### Backend
- `backend/app/routers/samples.py`: Sample endpoints including `/accession`
- `backend/app/schemas/sample.py`: Request/response schemas
- `backend/models/sample.py`: Sample model
- `backend/models/test.py`: Test model
- `backend/models/container.py`: Container model

## Future Enhancements

Potential improvements for post-MVP:

1. **Manifest Import**: Bulk accessioning from manifest files
2. **Barcode Scanning**: Integration with barcode scanners for sample names
3. **Workflow Configuration**: Configurable workflow steps via UI
4. **Batch Accessioning**: Accession multiple samples in a single operation
5. **Template Support**: Save and reuse common accessioning configurations

