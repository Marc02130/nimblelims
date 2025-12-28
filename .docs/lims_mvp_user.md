# User Stories for LIMS MVP

User stories are written in Agile format: "As a [role], I want [feature] so that [benefit]." They are prioritized for MVP development, grouped by feature area, and include acceptance criteria for clarity. These stories cover the core scope: sample tracking, test ordering, results entry, security, and configurations. Estimates are in story points (Fibonacci scale) for planning in Cursor implementation. The system uses 17 permissions (with `test:configure` referenced in code but not yet in database).

## 1. Sample Tracking

- **US-1: Sample Accessioning**  
  As a Lab Technician, I want to accession new samples including inspection notes, test assignment, and optional double-entry so that samples are accurately entered and ready for testing.  
  *Acceptance Criteria*:  
  - Form fields: due_date, received_date, sample_type, status, matrix, temperature, anomalies notes.  
  - Assign tests from manifest at entry.  
  - Double-entry validation for key fields (optional toggle).  
  - Review step before release (updates status to 'Available for Testing').  
  - API: POST /samples with validation; RBAC: sample:create permission.  
  *Priority*: High | *Estimate*: 8 points

- **US-2: Sample Status Management**  
  As a Lab Technician or Lab Manager, I want to update sample statuses throughout the lifecycle so that progress is tracked accurately.  
  *Acceptance Criteria*:  
  - Statuses: Received, Available for Testing, Testing Complete, Reviewed, Reported (from lists).  
  - Updates trigger audit logs.  
  - Filtered views by status/project.  
  - API: PATCH /samples/{id}/status; RBAC: sample:update.  
  *Priority*: High | *Estimate*: 5 points

- **US-3: Create Aliquots/Derivatives**  
  As a Lab Technician, I want to create aliquots or derivatives from parent samples during workflows so that sub-samples are linked and inherit properties.  
  *Acceptance Criteria*:  
  - Aliquot: Same sample_id, new container_id.  
  - Derivative: New sample_id/type, new container_id.  
  - Inherit project_id, client_id; configurable workflow steps.  
  - Example: DNA extraction from blood.  
  - API: POST /samples/aliquot or /derivative with parent_id; RBAC: sample:create.  
  *Priority*: Medium | *Estimate*: 8 points

- **US-4: QC Sample Handling**  
  As a Lab Technician, I want to flag samples as QC types so that controls/blanks are integrated into batches.  
  *Acceptance Criteria*:  
  - qc_type from lists: Sample, Positive Control, Negative Control, Matrix Spike, Duplicate, Blank.  
  - Display in batch views for validation.  
  - API: Included in sample creation/update; no separate permission.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-5: Container Management**  
  As a Lab Technician, I want to assign and manage hierarchical containers for samples so that physical storage is tracked.  
  *Acceptance Criteria*:  
  - Types: tube, plate, well, rack (from container_types table with capacity, material, dimensions, preservative).  
  - Self-referential (parent_container_id for plates/wells).  
  - Contents link: Multiple samples per container (pooling) with concentration/amount/units.  
  - Units table: id, name, description, active, audit fields, multiplier, type (list: concentration, mass, volume, molar).  
  - API: POST /containers; link via /contents; RBAC: sample:update.  
  *Priority*: High | *Estimate*: 8 points

- **US-6: Pooled Samples Creation**  
  As a Lab Technician, I want to add multiple contents to a container with concentration/amount calculations so that pooled samples are handled correctly.  
  *Acceptance Criteria*:  
  - Add contents: container_id, sample_id, concentration/units, amount/units.  
  - Calculations: Use multipliers for base unit conversions (e.g., average/sum rules; volume from concentration/amount).  
  - Base units: g/L for concentration, g for mass, L for volume, mol/L for molar.  
  - API: POST /contents; backend computes volumes.  
  *Priority*: Medium | *Estimate*: 5 points

## 2. Test Ordering

- **US-7: Assign Tests to Samples**  
  As a Lab Technician, I want to order tests during accessioning so that analyses are linked to samples.  
  *Acceptance Criteria*:  
  - Select analysis_id → Create test instance with status 'In Process'.  
  - Analyses fields: method, turnaround_time, cost.  
  - API: POST /tests; RBAC: test:assign.  
  *Priority*: High | *Estimate*: 5 points

- **US-8: Test Status Management**  
  As a Lab Technician or Lab Manager, I want to update test statuses so that analysis progress is visible.  
  *Acceptance Criteria*:  
  - Statuses: In Process, In Analysis, Complete (from lists).  
  - Fields: review_date, test_date, technician_id.  
  - API: PATCH /tests/{id}; RBAC: test:update.  
  *Priority*: Medium | *Estimate*: 3 points

## 3. Results Entry

- **US-9: Batch-Based Results Entry**  
  As a Lab Technician, I want to enter results for a batch of containers so that analytes are populated efficiently.  
  *Acceptance Criteria*:  
  - Select batch/test → Display analytes per sample.  
  - Fields: raw_result, reported_result, qualifiers (from lists), calculated_result (stub for post-MVP).  
  - Validation: Based on analysis_analytes (data_type, ranges, sig figs).  
  - Update statuses on entry/completion.  
  - API: POST /results; RBAC: result:enter.  
  *Priority*: High | *Estimate*: 8 points

- **US-10: Results Review**  
  As a Lab Manager, I want to review and approve results at the test level so that quality is ensured.  
  *Acceptance Criteria*:  
  - Batch view for review; update test status to Complete.  
  - Record review_date.  
  - API: PATCH /tests/{id}/review; RBAC: result:review.  
  *Priority*: High | *Estimate*: 5 points

## 4. Batches and Plates

- **US-11: Create and Manage Batches**  
  As a Lab Technician, I want to create batches of containers so that group processing is supported.  
  *Acceptance Criteria*:  
  - Add containers; statuses: Created, In Process, Completed.  
  - Workflow: Created → In Process (analysis) → Completed (review).  
  - Plates: As containers with wells (row/column).  
  - API: POST /batches; add via /batch-containers; RBAC: batch:manage.  
  *Priority*: Medium | *Estimate*: 5 points

## 5. Security and Authentication

- **US-12: User Authentication**  
  As any user, I want to log in with username/password and verify email so that access is secure.  
  *Acceptance Criteria*:  
  - No default access; admin grants roles/permissions.  
  - JWT token on login; last_login tracked.  
  - API: POST /auth/login, /verify-email.  
  *Priority*: High | *Estimate*: 5 points

- **US-13: Role-Based Access Control**  
  As an Administrator, I want to manage roles and granular permissions so that access is controlled.  
  *Acceptance Criteria*:  
  - 17 permissions (e.g., sample:create, result:review, batch:manage) via junctions.  
  - Roles: Admin (all), Lab Manager (review/manage), Technician (create/enter), Client (read own).  
  - API: CRUD /roles, /permissions (admin-only).  
  - Note: `test:configure` is referenced in code but not yet in database; endpoints use `config:edit` as fallback.  
  *Priority*: High | *Estimate*: 8 points

- **US-14: Project and Client Data Isolation**  
  As a Client, I want to view only my projects/samples/results so that data privacy is maintained.  
  *Acceptance Criteria*:  
  - Project_users junction for access grants.  
  - Filters: client_id on users; RLS in DB.  
  - API: All queries scoped by user context.  
  *Priority*: High | *Estimate*: 5 points

## 6. Configurations

- **US-15: Configurable Lists**  
  As an Administrator, I want to manage lists for statuses, types, etc., so that the system is flexible.  
  *Acceptance Criteria*:  
  - Lists/list_entries tables; modifiable via UI/API.  
  - Used for sample_type, status, qc_type, units type (concentration, mass, volume, molar).  
  - API: CRUD /lists; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-16: Units Management**  
  As an Administrator, I want to configure units with multipliers for conversions so that measurements are standardized.  
  *Acceptance Criteria*:  
  - Units table: name (e.g., µg/µL), multiplier (relative to base like g/L), type (from lists).  
  - Used in contents/containers for concentration/amount_units.  
  - Backend handles conversions in calculations.  
  - API: CRUD /units; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-17: Analyses Management**  
  As an Administrator, I want to manage analyses (test methods) so that the system supports our laboratory's testing capabilities.  
  *Acceptance Criteria*:  
  - CRUD operations for analyses (name, method, turnaround_time, cost).  
  - Unique name validation.  
  - Cannot delete if referenced by tests.  
  - API: CRUD /analyses; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-18: Analytes Management**  
  As an Administrator, I want to manage analytes (measurable components) so that they can be assigned to analyses.  
  *Acceptance Criteria*:  
  - CRUD operations for analytes (name, description).  
  - Unique name validation.  
  - Cannot delete if referenced by analyses.  
  - API: CRUD /analytes; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-19: Analysis-Analyte Configuration**  
  As an Administrator, I want to configure validation rules for analytes within analyses so that results entry is properly validated.  
  *Acceptance Criteria*:  
  - Assign analytes to analyses.  
  - Configure per-analyte rules: data_type, high/low values, significant_figures, is_required, default_value, reported_name, display_order.  
  - Support for list-based analytes (qualifiers).  
  - Validation during results entry based on rules.  
  - API: CRUD /analyses/{id}/analyte-rules; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-20: Users Management**  
  As an Administrator, I want to manage users so that access is properly controlled.  
  *Acceptance Criteria*:  
  - CRUD operations for users (username, email, role assignment, client assignment).  
  - Password management (admin can reset).  
  - Filter by role or client.  
  - API: CRUD /users; RBAC: user:manage or config:edit.  
  *Priority*: High | *Estimate*: 5 points

- **US-21: Container Types Management**  
  As an Administrator, I want to manage container types so that they are standardized before use.  
  *Acceptance Criteria*:  
  - CRUD operations for container types (name, capacity, material, dimensions, preservative).  
  - Types must exist before container instances can be created.  
  - API: CRUD /containers/types; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-22: Test Batteries Management**  
  As an Administrator, I want to create and manage test batteries (grouped analyses) so that common test combinations can be assigned efficiently during accessioning.  
  *Acceptance Criteria*:  
  - CRUD operations for test batteries (name, description).  
  - Add/remove analyses to/from batteries with sequence ordering (integer >= 1).  
  - Mark analyses as optional within batteries.  
  - Unique battery names; at least one analysis required.  
  - Cannot delete if referenced by tests (409 Conflict).  
  - API: CRUD /test-batteries and /test-batteries/{id}/analyses; RBAC: config:edit or test:configure.  
  - UI: Material-UI DataGrid with expandable rows, search/filter, sequence management.  
  *Priority*: Medium | *Estimate*: 8 points

- **US-23: Test Battery Assignment in Accessioning**  
  As a Lab Technician, I want to assign a test battery to a sample during accessioning so that all analyses in the battery are automatically created as sequenced tests.  
  *Acceptance Criteria*:  
  - Select test battery during accessioning workflow.  
  - System creates tests for all analyses in battery (ordered by sequence).  
  - Optional analyses can be skipped (future enhancement).  
  - Battery assignment can be combined with individual analysis assignments.  
  - API: POST /samples/accession with battery_id; auto-creates tests.  
  *Priority*: Medium | *Estimate*: 5 points

## Prioritization and Roadmap
- **Sprint 1 (Core Data Model)**: US-1, US-5, US-7, US-12 (Foundation: Samples, containers, tests, auth).  
- **Sprint 2 (Workflows)**: US-3, US-6, US-9, US-11 (Aliquots, pooling, results, batches).  
- **Sprint 3 (Security/Configs)**: US-13, US-14, US-15, US-16, US-17, US-18, US-19, US-20, US-21, US-22 (RBAC, isolation, lists/units, analyses/analytes, users, container types, test batteries).  
- **Sprint 4 (Reviews/Polish)**: US-2, US-4, US-8, US-10, US-23 (Statuses, QC, reviews, battery assignment).  
Total Estimate: ~126 points. Post-MVP: Add workflows configurability, calculations.


# Post-MVP User Stories for LIMS
This document outlines user stories for post-MVP enhancements to the LIMS, building on the core MVP features. These stories focus on efficiency improvements like bulk processing, advanced batching, and hierarchical project grouping. They are written in Agile format and include acceptance criteria, priorities, and estimates. These extend the 17 MVP permissions without introducing new ones unless specified.
## 1. Sample Tracking Enhancements

### US-24: Bulk Sample Accessioning
As a Lab Technician, I want to accession multiple samples at once with shared common fields so that repetitive data entry is minimized for batch submissions.
Acceptance Criteria:
Toggle for bulk mode in accessioning UI.
Common fields: sample_type, matrix, due_date, received_date, project_id, client_project_id, container_type, test battery/analyses.
Unique fields per sample: name, client_sample_id, container_name/barcode, overrides (e.g., temperature).
Auto-generation option for sequential names (e.g., prefix + number).
Single transaction creates all samples/containers/tests; validation for uniques across set.
API: POST /samples/bulk-accession; RBAC: sample:create.
Priority: Medium | Estimate: 8 points

### US-25: Client Project Management
As a Lab Manager, I want to group multiple NimbleLIMS projects under a client project so that ongoing submissions for the same client initiative can be tracked holistically.
Acceptance Criteria:
CRUD for client_projects (name, description, client_id, status).
Link NimbleLIMS projects via client_project_id FK.
Accessioning allows selection/creation of client project before NimbleLIMS project.
Reporting aggregates across linked projects.
API: CRUD /client-projects; RBAC: project:manage.
Priority: Medium | Estimate: 5 points


## 2. Batch Management Enhancements

### US-26: Cross-Project Batching
As a Lab Technician, I want to batch samples from multiple NimbleLIMS projects together if they have compatible test types so that shared processing steps like prep can be efficient.
Acceptance Criteria:
Batch creation allows selection across accessible projects.
Validation for compatibility (e.g., shared prep analysis like "EPA Method 8080 Prep").
Option to split into sub-batches for divergent steps (e.g., cleanup/instrument runs).
RLS enforces access to all included samples.
API: POST /batches with cross-project container_ids; RBAC: batch:manage.
Priority: Medium | Estimate: 5 points

### US-27: Add QC Samples at Batch Creation
As a Lab Technician, I want to add QC samples directly during batch creation so that controls are integrated contextually.
Acceptance Criteria:
Select qc_type (e.g., Blank, Blank Spike, Duplicate, Matrix Spike) and auto-generate QC sample/container.
Link to batch with inherited project_id.
Required for certain batch types (configurable).
API: POST /batches with qc_additions list; RBAC: batch:manage.
Priority: Medium | Estimate: 5 points


## 3. Results Management Enhancements

### US-28: Batch Results Entry
As a Lab Technician, I want to enter results for multiple tests/samples in a batch at once so that data entry is efficient for grouped processing.
Acceptance Criteria:
Tabular UI for batch with rows for tests/samples and columns for analytes.
Auto-fill common fields; real-time validation including QC checks.
Atomic submit updates all results and statuses.
Failing QC flags or blocks batch approval (configurable).
API: POST /results/batch; RBAC: result:enter.
Priority: Medium | Estimate: 8 points


## Prioritization and Roadmap

Sprint 5 (Bulk and Grouping): US-24, US-25 (Bulk accessioning, client projects).
Sprint 6 (Advanced Batching): US-26, US-27 (Cross-project batching, QC at batch).
Sprint 7 (Results Efficiency): US-28 (Batch results entry).
Total Estimate: ~31 points. Future: Instrument integration, automated calculations.##