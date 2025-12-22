# Containers Documentation

## Overview

Containers in the LIMS system represent physical storage vessels for samples. They enable tracking of where samples are stored, support hierarchical relationships (e.g., plates containing wells, racks containing tubes), and allow multiple samples to be pooled in a single container. Containers are essential for batch processing, plate-based workflows, and physical inventory management.

This documentation covers container types, structure, relationships, contents management, and integration with batches and samples.

## Container Types

Container types define the physical characteristics of containers. They are configurable by administrators and include:

### Fields

- **name**: Unique identifier for the container type (e.g., "96-well plate", "15mL tube")
- **description**: Optional description
- **capacity**: Numeric value representing capacity in base units
- **material**: Material composition (e.g., "polypropylene", "glass")
- **dimensions**: String describing dimensions (e.g., "8x12" for plates, "15x100mm" for tubes)
- **preservative**: Optional preservative information

### Common Container Types

- **Tubes**: Individual sample containers (e.g., 15mL, 50mL tubes)
- **Plates**: Multi-well plates (e.g., 96-well, 384-well)
- **Wells**: Individual wells within plates
- **Racks**: Storage racks holding multiple containers

**Implementation**: `backend/models/container.py::ContainerType`

## Container Structure

### Standard Fields

All containers inherit standard base model fields:
- **id**: UUID primary key
- **name**: Unique container identifier (can be barcode)
- **description**: Optional description
- **active**: Boolean flag for soft deletion
- **created_at**, **created_by**: Audit timestamp and user
- **modified_at**, **modified_by**: Audit timestamp and user

### Container-Specific Fields

- **row**: Integer (default: 1) - Row position for plate-based containers
- **column**: Integer (default: 1) - Column position for plate-based containers
- **concentration**: Numeric(15,6) - Concentration value for container contents
- **concentration_units**: FK to units.id - Unit for concentration measurement
- **amount**: Numeric(15,6) - Amount value for container contents
- **amount_units**: FK to units.id - Unit for amount measurement
- **type_id**: FK to container_types.id (required) - Container type
- **parent_container_id**: FK to containers.id (nullable) - Parent container for hierarchy

**Implementation**: `backend/models/container.py::Container`

## Hierarchical Relationships

Containers support self-referential parent-child relationships to model physical containment:

### Examples

1. **Plate → Wells**:
   - Parent: 96-well plate container
   - Children: 96 individual well containers (row/column positions)

2. **Rack → Tubes**:
   - Parent: Storage rack container
   - Children: Individual tube containers

3. **Freezer → Racks → Tubes**:
   - Multi-level hierarchy for complex storage

### Relationships

- **parent_container**: Reference to parent container (nullable)
- **child_containers**: List of child containers
- **container_type**: Reference to container type definition

**Use Cases**:
- Tracking physical location of samples
- Plate-based workflows (wells in plates)
- Storage organization (racks, freezers)
- Batch processing (grouping containers)

## Contents (Sample-Container Junction)

The `contents` table is a junction table linking samples to containers, enabling:

1. **Single Sample per Container**: Standard case (one-to-one)
2. **Pooled Samples**: Multiple samples in one container (many-to-one)
3. **Sample-Specific Measurements**: Concentration and amount per sample-container pair

### Contents Fields

- **container_id**: FK to containers.id (primary key)
- **sample_id**: FK to samples.id (primary key)
- **concentration**: Numeric(15,6) - Sample-specific concentration
- **concentration_units**: FK to units.id - Concentration unit
- **amount**: Numeric(15,6) - Sample-specific amount
- **amount_units**: FK to units.id - Amount unit
- **Unique Constraint**: (container_id, sample_id)

**Implementation**: `backend/models/container.py::Contents`

### Pooling Samples

Pooling allows multiple samples to be stored in a single container:

- Each sample-container relationship has its own concentration/amount values
- Useful for:
  - Quality control pools
  - Composite samples
  - Batch processing workflows
  - Volume-limited scenarios

**User Story**: US-6: Pooled Samples Creation

## Units and Measurements

Containers and contents use the units system for measurements:

### Unit Types

- **concentration**: Units like g/L, µg/µL, mg/mL
- **mass**: Units like g, mg, µg
- **volume**: Units like L, mL, µL
- **molar**: Units like mol/L, mmol/L

### Unit Structure

- **multiplier**: Relative to base unit (e.g., 0.001 for mg relative to g)
- **type**: FK to list_entries (concentration, mass, volume, molar)
- Base units implied by type (g/L for concentration, g for mass, L for volume)

### Conversions

Backend handles unit conversions using multipliers:
- Volume calculations: `volume = amount / concentration` (normalized to base units)
- Pooling calculations: Average/sum rules based on unit types

**Implementation**: `backend/models/unit.py::Unit`

## API Endpoints

### Container Types

**GET** `/containers/types`
- List all active container types
- No authentication required (public lookup)

**POST** `/containers/types`
- Create new container type
- Requires: `config:edit` permission

**PATCH** `/containers/types/{type_id}`
- Update container type
- Requires: `config:edit` permission

### Containers

**GET** `/containers`
- List containers with optional filters:
  - `type_id`: Filter by container type
  - `parent_id`: Filter by parent container
- Returns: List of ContainerResponse

**GET** `/containers/{container_id}`
- Get container with contents
- Returns: ContainerWithContentsResponse

**POST** `/containers`
- Create new container
- Requires: `sample:create` permission
- Validates: Container type exists, parent container exists (if specified)

**PATCH** `/containers/{container_id}`
- Update container
- Requires: `sample:update` permission

### Contents

**GET** `/containers/{container_id}/contents`
- Get container contents with pagination
- Query params: `page`, `size`
- Returns: ContentsListResponse

**POST** `/containers/{container_id}/contents`
- Add sample to container (create contents)
- Requires: `sample:create` permission
- Validates: Container exists, sample exists, no duplicate contents
- Implements: US-6: Pooled Samples Creation

**PATCH** `/containers/{container_id}/contents/{sample_id}`
- Update contents (concentration/amount)
- Requires: `sample:update` permission

**DELETE** `/containers/{container_id}/contents/{sample_id}`
- Remove sample from container
- Requires: `sample:update` permission

**Implementation**: `backend/app/routers/containers.py`

## Request/Response Schemas

### ContainerCreate

```python
{
    "name": str,                    # Required, 1-255 chars
    "description": Optional[str],
    "row": int,                     # Default: 1, min: 1
    "column": int,                  # Default: 1, min: 1
    "concentration": Optional[float], # Min: 0
    "concentration_units": Optional[UUID],
    "amount": Optional[float],      # Min: 0
    "amount_units": Optional[UUID],
    "type_id": UUID,                # Required
    "parent_container_id": Optional[UUID]
}
```

### ContentsCreate

```python
{
    "container_id": UUID,           # Required (in path)
    "sample_id": UUID,              # Required
    "concentration": Optional[float], # Min: 0
    "concentration_units": Optional[UUID],
    "amount": Optional[float],      # Min: 0
    "amount_units": Optional[UUID]
}
```

**Implementation**: `backend/app/schemas/container.py`

## Container Usage in the Application

This section describes how containers are used throughout the application from a user perspective, including workflows, UI interactions, and practical examples.

### 1. Sample Accessioning Workflow

Containers are created and linked to samples during the accessioning process.

#### Step-by-Step Process

1. **Navigate to Accessioning Form**
   - User goes to Sample Accessioning page
   - Form loads with three steps: Sample Details, Test Assignment, Review & Submit

2. **Enter Container Information (Step 1: Sample Details)**
   - User fills in sample information
   - Container fields are included in the same form:
     - **Container Name**: Unique identifier (e.g., barcode, tube number)
     - **Container Type**: Dropdown selection (e.g., "15mL tube", "96-well plate")
     - **Concentration**: Optional concentration value
     - **Concentration Units**: Dropdown (e.g., g/L, mg/mL)
     - **Amount**: Optional amount value
     - **Amount Units**: Dropdown (e.g., mL, µL)

3. **Submit Accessioning**
   - On form submission, the system:
     1. Creates the sample record
     2. Creates a new container with the specified details
     3. Links sample to container via contents table
     4. Creates test records for assigned analyses
   - All operations happen in sequence with error handling

4. **Post-Accessioning**
   - After successful accessioning, user can:
     - Create aliquots/derivatives (which create new containers)
     - View container details from sample view
     - Add container to a batch for processing

**Implementation**: `frontend/src/pages/AccessioningForm.tsx::handleSubmit()`

**API Sequence**:
```typescript
// 1. Create sample
const sample = await apiService.createSample(sampleData);

// 2. Create container
const container = await apiService.createContainer(containerData);

// 3. Link sample to container
await apiService.createContent({
  container_id: container.id,
  sample_id: sample.id,
  concentration: values.concentration,
  concentration_units: values.concentration_units,
  amount: values.amount,
  amount_units: values.amount_units,
});
```

### 2. Container Management Page

The Container Management page provides a centralized interface for viewing and managing all containers.

#### Features

**Container List View**:
- DataGrid displaying all containers with columns:
  - Name
  - Type (with material and dimensions)
  - Concentration (with units)
  - Amount (with units)
  - Number of samples (contents count)
  - Created date
- Clicking a row opens container details dialog
- Filtering and sorting capabilities

**Create Container**:
- "Create Container" button opens dialog
- Form fields:
  - Container name (required)
  - Container type dropdown (required)
  - Concentration and units
  - Amount and units
  - Parent container (optional, for hierarchies)
- Validation ensures required fields are filled
- Success message on creation

**Container Details Dialog**:
- Opens when clicking a container in the list
- Two-column layout:
  - **Left**: Container information
    - Name, type, concentration, amount
    - Created timestamp
    - Edit button
  - **Right**: Contents (samples in container)
    - List of samples with concentration/amount
    - "Add Sample" button
    - Remove sample buttons
- "Add Sample" dialog allows:
  - Selecting sample from dropdown
  - Entering concentration/amount for that sample
  - Creating contents relationship

**Implementation**: `frontend/src/pages/ContainerManagement.tsx`

### 3. Batch Workflow with Containers

Containers are essential for batch processing workflows.

#### Creating a Batch with Containers

1. **Create Batch**
   - User navigates to Batch Management
   - Clicks "Create Batch"
   - Enters batch name, description, type, status

2. **Add Containers to Batch**
   - In batch details view, "Containers" tab shows ContainerGrid component
   - User clicks "Add Container" button
   - Dialog opens with fields:
     - Container name
     - Container type
     - Row/Column (for plate-based containers)
     - Concentration and units
     - Amount and units
   - Container is created and added to batch via `batch_containers` junction

3. **View Batch Containers**
   - ContainerGrid displays containers in card grid layout
   - Each card shows:
     - Container name
     - Container type
     - Row/Column position (if applicable)
     - Concentration and amount
     - Number of samples
     - Edit and Delete buttons

4. **Edit/Remove Containers**
   - Edit button opens dialog with pre-filled values
   - Delete button removes container from batch (not deleted, just unlinked)
   - Changes are saved immediately

**Implementation**: `frontend/src/components/batches/ContainerGrid.tsx`

**API Endpoints Used**:
- `POST /batches/{batch_id}/containers` - Add container to batch
- `PATCH /containers/{container_id}` - Update container
- `DELETE /batches/{batch_id}/containers/{container_id}` - Remove from batch

### 4. Results Entry Using Containers

Containers in batches are used to identify samples during results entry.

#### Workflow

1. **Select Batch for Results Entry**
   - User navigates to Results Management
   - Selects a batch
   - System loads all containers in the batch

2. **Container-Based Sample Identification**
   - Results entry table displays:
     - Container name/position
     - Sample name (from contents)
     - Test information
     - Analyte fields for entry
   - Each row represents a sample-container pair

3. **Enter Results**
   - User enters results per analyte
   - Container information helps identify physical location
   - For plate-based workflows, row/column positions are displayed

**Use Case**: In a 96-well plate batch, results entry shows:
- Well position (A1, A2, B1, etc.)
- Sample in that well
- Test and analyte information
- Result entry fields

### 5. Container Details and Contents Management

Users can view and manage container contents (samples in containers).

#### Viewing Container Contents

**From Container Management**:
- Click container in list → Details dialog opens
- Contents section shows all samples in container
- Each entry displays:
  - Sample name
  - Concentration and amount with units
  - Remove button

**From Sample View** (future enhancement):
- Sample details could show container information
- Link to container details page

#### Adding Samples to Existing Containers

1. **Open Container Details**
   - Navigate to Container Management
   - Click on container row

2. **Add Sample Dialog**
   - Click "Add Sample" button in Contents section
   - Dialog opens with:
     - Sample dropdown (all accessible samples)
     - Concentration field
     - Concentration units dropdown
     - Amount field
     - Amount units dropdown

3. **Submit**
   - Creates contents relationship
   - Sample appears in contents list
   - Useful for pooling samples or adding samples to existing containers

**Implementation**: `frontend/src/components/containers/ContainerDetails.tsx`

### 6. Hierarchical Container Workflows

For complex storage scenarios, containers support parent-child relationships.

#### Example: Plate with Wells

1. **Create Parent Container (Plate)**
   - Container type: "96-well plate"
   - Name: "Plate-001"
   - No parent container

2. **Create Child Containers (Wells)**
   - For each well (A1 through H12):
     - Container type: "well"
     - Name: "Plate-001-A1", "Plate-001-A2", etc.
     - Parent container: Plate-001
     - Row: 1-8 (A-H)
     - Column: 1-12

3. **Add Samples to Wells**
   - Use contents API to link samples to individual well containers
   - Each well can contain one or more samples (pooling)

4. **Add Plate to Batch**
   - Add parent container (plate) to batch
   - System can traverse hierarchy to find all samples

**Use Case**: High-throughput screening with 96-well plates
- Single plate container represents physical plate
- 96 well containers represent individual wells
- Samples are linked to specific wells
- Batch processing handles entire plate

### 7. Container Search and Filtering

Users can find containers using various filters.

#### Available Filters

**In Container Management**:
- Filter by container type
- Filter by parent container
- Search by name (future enhancement)

**In Batch View**:
- Containers are filtered by batch membership
- Display only containers in selected batch

**API Filtering**:
```typescript
// Get containers by type
const containers = await apiService.getContainers({
  type_id: containerTypeId
});

// Get containers by parent
const childContainers = await apiService.getContainers({
  parent_id: parentContainerId
});
```

### 8. Container Lifecycle

Containers follow a lifecycle from creation to archival.

#### Lifecycle Stages

1. **Creation**
   - Created during accessioning or manually
   - Initially empty (no contents)
   - Active status

2. **Usage**
   - Samples added via contents
   - Linked to batches
   - Used in workflows

3. **Modification**
   - Container details can be updated
   - Contents can be added/removed
   - Concentration/amount can be updated

4. **Archival** (Soft Delete)
   - Container marked as inactive
   - Not deleted, but hidden from active views
   - Historical data preserved

**Note**: Container deletion is soft (active=false), preserving audit trail and historical relationships.

## Frontend Components

### Container Management Page

**Location**: `frontend/src/pages/ContainerManagement.tsx`

**Features**:
- DataGrid listing all containers
- Create/Edit container dialogs
- Container details view
- Contents management

**Components Used**:
- `ContainerForm`: Create/edit container form
- `ContainerDetails`: View container details and contents

### Container Form

**Location**: `frontend/src/components/containers/ContainerForm.tsx`

**Fields**:
- Container name (required)
- Container type (required, dropdown)
- Concentration and units
- Amount and units
- Parent container (optional)

**Validation**:
- Name required
- Type required
- Concentration/amount must be positive
- Units required if values provided

### Container Details

**Location**: `frontend/src/components/containers/ContainerDetails.tsx`

**Features**:
- Display container information
- List contents (samples in container)
- Add sample to container dialog
- Remove sample from container
- Edit container button

### Container Grid (Batch View)

**Location**: `frontend/src/components/batches/ContainerGrid.tsx`

**Purpose**: Display and manage containers within a batch

**Features**:
- Grid layout of containers
- Add container to batch
- Edit container details
- Remove container from batch
- Display container metadata (row/column, concentration, amount)

## Integration with Batches

Containers are linked to batches via the `batch_containers` junction table:

### Batch Container Relationship

- **batch_id**: FK to batches.id
- **container_id**: FK to containers.id
- **position**: Optional string (e.g., "A1", "well-1")
- **notes**: Optional notes about container in batch

### Batch Workflow

1. Create batch
2. Add containers to batch (via `/batches/{batch_id}/containers`)
3. Containers can be created during batch creation or added later
4. Batch view displays all containers in grid format
5. Results entry uses batch containers to identify samples

**Implementation**: `backend/models/batch.py::BatchContainer`

## Integration with Samples

### Accessioning Workflow

During sample accessioning:
1. Container is created (or existing container selected)
2. Sample is linked to container via contents table
3. Concentration and amount are recorded

**See**: `.docs/accessioning_workflow.md`

### Aliquot/Derivative Creation

When creating aliquots or derivatives:
- New container is created for the child sample
- Parent-child relationship maintained via `parent_sample_id`
- Container hierarchy can reflect physical relationship

## Validation Rules

### Container Validation

- **Name**: Must be unique across all containers
- **Type**: Must reference existing active container type
- **Parent**: If specified, must reference existing active container
- **Row/Column**: Must be >= 1
- **Concentration/Amount**: Must be >= 0 if provided
- **Units**: Must reference existing units with appropriate type

### Contents Validation

- **Unique Constraint**: Same sample cannot be in same container twice
- **Container**: Must exist and be active
- **Sample**: Must exist and be active
- **Concentration/Amount**: Must be >= 0 if provided
- **Units**: Must match unit type (concentration units for concentration, mass/volume for amount)

## Permissions

### Required Permissions

- **sample:create**: Create containers, add contents
- **sample:update**: Update containers, modify contents
- **sample:read**: View containers and contents
- **config:edit**: Manage container types

### Access Control

- Containers are not project-scoped (global entities)
- Access controlled via sample access (contents link to samples)
- Container types are public (lookup data)

## Use Cases

### 1. Plate-Based Workflows

**Scenario**: 96-well plate for batch testing

1. Create plate container (type: "96-well plate")
2. Create 96 well containers (type: "well")
   - Set parent_container_id to plate
   - Set row/column for each well (1-8 rows, 1-12 columns)
3. Add samples to wells via contents
4. Add plate to batch for processing

### 2. Storage Tracking

**Scenario**: Track sample location in freezer

1. Create freezer container (type: "freezer")
2. Create rack container (type: "rack", parent: freezer)
3. Create tube containers (type: "tube", parent: rack)
4. Link samples to tubes via contents

### 3. Pooled Samples

**Scenario**: Quality control pool

1. Create container (type: "pool tube")
2. Add multiple samples via contents
3. Each sample has its own concentration/amount
4. Backend calculates total volume using unit conversions

### 4. Batch Processing

**Scenario**: Process multiple containers together

1. Create batch
2. Add containers to batch
3. Batch view displays all containers
4. Results entry uses batch containers to identify samples

## Data Model Relationships

```
ContainerType (1) ──< (many) Container
Container (1) ──< (many) Container (parent_container_id)
Container (1) ──< (many) Contents
Sample (1) ──< (many) Contents
Container (many) ──< (many) Batch (via batch_containers)
Container (1) ──< (many) Unit (concentration_units, amount_units)
```

## Error Handling

### Common Errors

1. **400 Bad Request**:
   - Invalid container type ID
   - Invalid parent container ID
   - Duplicate contents (sample already in container)
   - Validation errors (negative values, etc.)

2. **403 Forbidden**:
   - Missing required permissions

3. **404 Not Found**:
   - Container not found
   - Container type not found
   - Sample not found (when adding contents)

## Related User Stories

- **US-5**: Container Management
- **US-6**: Pooled Samples Creation
- **US-11**: Create and Manage Batches

## Implementation Files

### Backend
- `backend/models/container.py`: Container, ContainerType, Contents models
- `backend/app/routers/containers.py`: Container API endpoints
- `backend/app/schemas/container.py`: Request/response schemas

### Frontend
- `frontend/src/pages/ContainerManagement.tsx`: Main container management page
- `frontend/src/components/containers/ContainerForm.tsx`: Create/edit form
- `frontend/src/components/containers/ContainerDetails.tsx`: Details view
- `frontend/src/components/batches/ContainerGrid.tsx`: Batch container grid

## Future Enhancements

Potential improvements for post-MVP:

1. **Barcode Integration**: Scan barcodes for container names
2. **Location Tracking**: GPS/room-level location tracking
3. **Capacity Management**: Automatic capacity checking
4. **Visual Plate Editor**: Drag-and-drop interface for plate layouts
5. **Container Templates**: Pre-configured container setups
6. **Automated Calculations**: Volume calculations from concentration/amount
7. **Container History**: Track container movements and changes
8. **Storage Maps**: Visual representation of storage locations

