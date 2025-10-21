# User Stories for LIMS MVP

User stories are written in Agile format: "As a [role], I want [feature] so that [benefit]." They are prioritized for MVP development, grouped by feature area, and include acceptance criteria for clarity. These stories cover the core scope: sample tracking, test ordering, results entry, security, and configurations. Estimates are in story points (Fibonacci scale) for planning in Cursor implementation. Total ~15 permissions are referenced where relevant.

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
  - ~15 permissions (e.g., sample:create, result:review) via junctions.  
  - Roles: Admin (all), Lab Manager (review/manage), Technician (create/enter), Client (read own).  
  - API: CRUD /roles, /permissions (admin-only).  
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

## Prioritization and Roadmap
- **Sprint 1 (Core Data Model)**: US-1, US-5, US-7, US-12 (Foundation: Samples, containers, tests, auth).  
- **Sprint 2 (Workflows)**: US-3, US-6, US-9, US-11 (Aliquots, pooling, results, batches).  
- **Sprint 3 (Security/Configs)**: US-13, US-14, US-15, US-16 (RBAC, isolation, lists/units).  
- **Sprint 4 (Reviews/Polish)**: US-2, US-4, US-8, US-10 (Statuses, QC, reviews).  
Total Estimate: ~84 points. Post-MVP: Add workflows configurability, calculations.