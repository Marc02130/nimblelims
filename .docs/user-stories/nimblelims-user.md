# User Stories for NimbleLIMS

User stories are written in Agile format: "As a [role], I want [feature] so that [benefit]." They are grouped by feature area and include acceptance criteria for clarity.

**MVP Release Bar:** Stories labeled **[MVP]** are required to ship a basic LIMS (sample tracking, test ordering, results entry). Stories labeled **[Shipped, Not MVP]** or **[Post-MVP]** are enhancements that are either already in the codebase or planned for after initial release.

**Note:** Estimates are in story points (Fibonacci scale) for planning in Cursor implementation. The system uses 17 permissions (with `test:configure` referenced in code but not yet in database).

## 1. Sample Tracking

- **US-1: Sample Accessioning** **[MVP]**  
  As a Lab Technician, I want to receive a sample by scanning the tube and filling a few sticky fields so that the sample, first container, and optional tests land in one transaction and I can scan the next tube.  
  *Acceptance Criteria*:  
  - Happy path is **atomic-receive** (tech sketch, PR 30): scan (or type) barcode; sticky sample type, matrix, project; optional tests; optional temperature; optional external id.  
  - **No sample-ID field.** `samples.name` is system-assigned from the name template.  
  - **No status picker.** System writes **Available for Testing**. Receipt is existing `received_date`.  
  - **No wizard. No aliquot dialog. No sample-detail redirect.** Stay on receive: toast, clear barcode, keep sticky fields, focus barcode.  
  - One DB transaction: sample + first container + contents + optional tests. Duplicate barcode → 409 on container; no orphan rows.  
  - Tests at receive are optional; status **Assigned/Pending**.  
  - Old `/samples` accession (typed sample name, status picker, review-to-Available, 3-step wizard, aliquot dialog) is **not** this packet’s happy path. Atomic-receive UAT **AR-01–AR-15** replaces it.  
  - API: POST /api/samples/receive; RBAC: sample:create.  
  *Priority*: High | *Estimate*: 8 points  
  *Related*: atomic-receive tech sketch

- **US-2: Sample Status Management** **[MVP]**  
  As a Lab Technician or Lab Manager, I want to update sample statuses throughout the lifecycle so that progress is tracked accurately.  
  *Acceptance Criteria*:  
  - Statuses: Received, Available for Testing, Testing Complete, Reviewed, Reported (from lists; existing UAT values remain valid).  
  - Additional sample dispositions: Quarantined, Rejected, Discarded.  
  - Direction: Sample.status tracks specimen state; Reviewed/Reported belong on the result/report (compatibility: both approaches work during transition).  
  - This packet’s UAT (AR-01–AR-15) only sets **Available for Testing**. It does not set Reviewed/Reported on Sample.status (Q1 parallel).  
  - Updates trigger audit events (not only modified_at).  
  - Filtered views by status/project.  
  - API: PATCH /samples/{id}/status; RBAC: sample:update.  
  - UAT compatibility: Existing five status names continue to work; product direction shifts review/release to result-level controls without breaking current workflows.  
  *Priority*: High | *Estimate*: 5 points  
  *Related*: Issues #22, #23

- **US-3: Create Aliquots/Derivatives** **[MVP]**  
  As a Lab Technician, I want to create aliquots or derivatives from parent samples during workflows so that sub-samples are linked and inherit properties.  
  *Acceptance Criteria*:  
  - Aliquot: Same sample_id, new container_id.  
  - Derivative: New sample_id/type, new container_id.  
  - Inherit project_id, client_id; configurable workflow steps.  
  - Example: DNA extraction from blood.  
  - API: POST /samples/aliquot or /derivative with parent_id; RBAC: sample:create.  
  - **Not in atomic-receive P0.** No aliquot UI this packet.  
  *Priority*: Medium | *Estimate*: 8 points

- **US-4: QC Sample Handling** **[Shipped, Not MVP]**  
  As a Lab Technician, I want to flag samples as QC types so that controls/blanks are integrated into batches.  
  *Acceptance Criteria*:  
  - qc_type from lists: Sample, Positive Control, Negative Control, Matrix Spike, Duplicate, Blank.  
  - Display in batch views for validation.  
  - API: Included in sample creation/update; no separate permission.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-5: Container Management** **[MVP]**  
  As a Lab Technician, I want to assign and manage hierarchical containers for samples so that physical storage is tracked.  
  *Acceptance Criteria*:  
  - Types: tube, plate, well, rack (from container_types table with capacity, material, dimensions, preservative).  
  - Self-referential (parent_container_id for plates/wells).  
  - Contents link: Multiple samples per container (pooling) with concentration/amount/units.  
  - Units table: id, name, description, active, audit fields, multiplier, type (list: concentration, mass, volume, molar).  
  - API: POST /containers; link via /contents; RBAC: sample:update.  
  *Priority*: High | *Estimate*: 8 points

- **US-6: Pooled Samples Creation** **[Shipped, Not MVP]**  
  As a Lab Technician, I want to add multiple contents to a container with concentration/amount calculations so that pooled samples are handled correctly.  
  *Acceptance Criteria*:  
  - Add contents: container_id, sample_id, concentration/units, amount/units.  
  - Calculations: Use multipliers for base unit conversions (e.g., average/sum rules; volume from concentration/amount).  
  - Base units: g/L for concentration, g for mass, L for volume, mol/L for molar.  
  - API: POST /contents; backend computes volumes.  
  *Priority*: Medium | *Estimate*: 5 points

## 2. Test Ordering

- **US-7: Assign Tests to Samples** **[MVP]**  
  As a Lab Technician, I want to order tests during accessioning so that analyses are linked to samples.  
  *Acceptance Criteria*:  
  - Select analysis_id → Create test instance with status 'Assigned/Pending' (atomic-receive L4). Later lifecycle may still use In Process / In Analysis / Complete (US-8).  
  - Analyses fields: method, turnaround_time, cost.  
  - API: POST /tests; RBAC: test:assign.  
  *Priority*: High | *Estimate*: 5 points

- **US-8: Test Status Management** **[MVP]**  
  As a Lab Technician or Lab Manager, I want to update test statuses so that analysis progress is visible.  
  *Acceptance Criteria*:  
  - Statuses: Assigned/Pending (create-at-receive and add-test; atomic-receive L4), then In Process, In Analysis, Complete (from lists). Do not drop the existing three UAT names.  
  - Fields: review_date, test_date, technician_id.  
  - API: PATCH /tests/{id}; RBAC: test:update.  
  *Priority*: Medium | *Estimate*: 3 points

## 3. Results Entry

- **US-9: Batch-Based Results Entry** **[MVP]**  
  As a Lab Technician, I want to enter results for a batch of containers so that analytes are populated efficiently.  
  *Acceptance Criteria*:  
  - Select batch/test → Display analytes per sample.  
  - Fields: raw_result, reported_result, qualifiers (from lists), calculated_result (stub for post-MVP).  
  - Validation: Based on analysis_analytes (data_type, ranges, sig figs).  
  - Update statuses on entry/completion.  
  - API: POST /results; RBAC: result:enter.  
  *Priority*: High | *Estimate*: 8 points

- **US-10: Results Review and Release** **[MVP]**  
  As a Lab Manager, I want to review and approve results at the test level so that quality is ensured before release.  
  *Acceptance Criteria*:  
  - Batch view for review; update test/result status to reviewed and reported states.  
  - Record review_date and reviewer.  
  - **Second-person review gate is tenant-configurable**: default OFF for pure R&D labs, default ON for GxP/CRO-release workflows.  
  - When second-person gate is ON: reviewer cannot be the same user who entered the result.  
  - When second-person gate is OFF: self-review is permitted (pure R&D use case).  
  - Direction: result-level review/release states (not only Sample.status = Reviewed/Reported).  
  - API: PATCH /tests/{id}/review; RBAC: result:review.  
  - UAT: When gate is ON, self-review is blocked; verify reviewer ≠ enterer enforcement.  
  - **Not in atomic-receive P0**: no schema flag for this gate (no new columns). AR-MU-02 stays catalog-only until Q2 lands a home.  
  *Priority*: High | *Estimate*: 8 points (increased for configurability + validation)  
  *Related*: Issues #22, #26

## 4. Batches and Plates

- **US-11: Create and Manage Batches** **[MVP + Shipped Enhancements]**  
  As a Lab Technician, I want to create batches of containers with sample prioritization so that group processing focuses on the most urgent samples first.  
  *Acceptance Criteria*:  
  - Add containers; statuses: Created, In Process, Completed.  
  - Workflow: Created → In Process (analysis) → Completed (review).  
  - Plates: As containers with wells (row/column).  
  - **Prioritization Criteria**:  
    - Samples sorted by expiration priority (days_until_expiration ASC NULLS LAST).  
    - Secondary sort by due date priority (days_until_due ASC NULLS LAST).  
    - Expiration calculation: `date_sampled + analysis.shelf_life - now()`.  
    - Due date inheritance: `COALESCE(sample.due_date, project.due_date)`.  
  - **Expired Sample Flagging**:  
    - Flag samples with `is_expired=true` when `days_until_expiration < 0`.  
    - Flag samples with `is_overdue=true` when `days_until_due < 0`.  
    - Display warning: "Expired: Testing invalid" for expired samples.  
    - Visual indicators: Red background for expired, orange for expiring soon (≤3 days).  
  - **Validation on batch creation**: Warn if batch contains expired/expiring samples.  
  - API: POST /batches; add via /batch-containers; GET /samples/eligible for prioritized list; RBAC: batch:manage.  
  - UI: Multi-step wizard with DataGrid showing prioritization columns, tooltips, ARIA labels.  
  *Priority*: Medium | *Estimate*: 8 points (increased for prioritization features)  
  *Note*: Basic batch creation is MVP; prioritization/expiration tracking are shipped enhancements.

## 5. Security and Authentication

- **US-12: User Authentication** **[MVP]**  
  As any user, I want to log in with username/password and verify email so that access is secure.  
  *Acceptance Criteria*:  
  - No default access; admin grants roles/permissions.  
  - JWT token on login; last_login tracked.  
  - API: POST /auth/login, /verify-email.  
  *Priority*: High | *Estimate*: 5 points

- **US-13: Role-Based Access Control** **[MVP]**  
  As an Administrator, I want to manage roles and granular permissions so that access is controlled.  
  *Acceptance Criteria*:  
  - 17 permissions (e.g., sample:create, result:review, batch:manage) via junctions.  
  - Roles: Admin (all), Lab Manager (review/manage), Technician (create/enter), Client (read own).  
  - API: CRUD /roles, /permissions (admin-only).  
  - Note: `test:configure` is referenced in code but not yet in database; endpoints use `config:edit` as fallback.  
  *Priority*: High | *Estimate*: 8 points

- **US-14: Project and Client Data Isolation** **[MVP]**  
  As a Client, I want to view only my projects/samples/results so that data privacy is maintained.  
  *Acceptance Criteria*:  
  - Project_users junction for access grants.  
  - Filters: client_id on users; RLS in DB.  
  - API: All queries scoped by user context.  
  *Priority*: High | *Estimate*: 5 points

## 6. Configurations

- **US-15: Configurable Lists** **[MVP]**  
  As an Administrator, I want to manage lists for statuses, types, etc., so that the system is flexible.  
  *Acceptance Criteria*:  
  - Lists/list_entries tables; modifiable via UI/API.  
  - Used for sample_type, status, qc_type, units type (concentration, mass, volume, molar).  
  - API: CRUD /lists; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-16: Units Management** **[MVP]**  
  As an Administrator, I want to configure units with multipliers for conversions so that measurements are standardized.  
  *Acceptance Criteria*:  
  - Units table: name (e.g., µg/µL), multiplier (relative to base like g/L), type (from lists).  
  - Used in contents/containers for concentration/amount_units.  
  - Backend handles conversions in calculations.  
  - API: CRUD /units; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-17: Analyses Management** **[MVP]**  
  As an Administrator, I want to manage analyses (test methods) so that the system supports our laboratory's testing capabilities.  
  *Acceptance Criteria*:  
  - CRUD operations for analyses (name, method, turnaround_time, cost).  
  - Unique name validation.  
  - Cannot delete if referenced by tests.  
  - API: CRUD /analyses; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-18: Analytes Management** **[MVP]**  
  As an Administrator, I want to manage analytes (measurable components) so that they can be assigned to analyses.  
  *Acceptance Criteria*:  
  - CRUD operations for analytes (name, description).  
  - Unique name validation.  
  - Cannot delete if referenced by analyses.  
  - API: CRUD /analytes; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-19: Analysis-Analyte Configuration** **[MVP]**  
  As an Administrator, I want to configure validation rules for analytes within analyses so that results entry is properly validated.  
  *Acceptance Criteria*:  
  - Assign analytes to analyses.  
  - Configure per-analyte rules: data_type, high/low values, significant_figures, is_required, default_value, reported_name, display_order.  
  - Support for list-based analytes (qualifiers).  
  - Validation during results entry based on rules.  
  - API: CRUD /analyses/{id}/analyte-rules; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-20: Users Management** **[MVP]**  
  As an Administrator, I want to manage users so that access is properly controlled.  
  *Acceptance Criteria*:  
  - CRUD operations for users (username, email, role assignment, client assignment).  
  - Password management (admin can reset).  
  - Filter by role or client.  
  - API: CRUD /users; RBAC: user:manage or config:edit.  
  *Priority*: High | *Estimate*: 5 points

- **US-21: Container Types Management** **[MVP]**  
  As an Administrator, I want to manage container types so that they are standardized before use.  
  *Acceptance Criteria*:  
  - CRUD operations for container types (name, capacity, material, dimensions, preservative).  
  - Types must exist before container instances can be created.  
  - API: CRUD /containers/types; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-22: Test Batteries Management** **[MVP]**  
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

- **US-23: Test Battery Assignment in Accessioning** **[MVP]**  
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
Total Estimate: ~126 points. 

**MVP Summary:** US-1, US-2, US-3, US-5, US-7, US-8, US-9, US-10, US-11 (basic), US-12, US-13, US-14, US-15, US-16, US-17, US-18, US-19, US-20, US-21, US-22, US-23 cover the release bar (sample tracking, test ordering, results entry, security, configuration).

---

# Post-MVP User Stories for LIMS

**Note:** This section documents user stories for **shipped features that are not the MVP release bar**. These enhancements are in the codebase and available for users who need them, but they build on the three-pillar MVP foundation.

## 1. Sample Tracking Enhancements

### US-24: Bulk Sample Accessioning **[Shipped, Not MVP]**
As a Lab Technician, I want to accession multiple samples at once with shared common fields so that repetitive data entry is minimized for batch submissions.
Acceptance Criteria:
Toggle for bulk mode in accessioning UI.
Common fields: sample_type, matrix, due_date, received_date, project_id, client_project_id, container_type, test battery/analyses.
Unique fields per sample: name, client_sample_id, container_name/barcode, overrides (e.g., temperature).
Auto-generation option for sequential names (e.g., prefix + number).
Single transaction creates all samples/containers/tests; validation for uniques across set.
API: POST /samples/bulk-accession; RBAC: sample:create.
Priority: Medium | Estimate: 8 points

### US-25: Client Project Management **[Shipped, Not MVP]**
As a Lab Manager, I want to group multiple NimbleLIMS projects under a client project so that ongoing submissions for the same client initiative can be tracked holistically.
Acceptance Criteria:
CRUD for client_projects (name, description, client_id, status).
Link NimbleLIMS projects via client_project_id FK.
Accessioning allows selection/creation of client project before NimbleLIMS project.
Reporting aggregates across linked projects.
API: CRUD /client-projects; RBAC: project:manage.
Priority: Medium | Estimate: 5 points


## 2. Batch Management Enhancements

### US-26: Cross-Project Batching **[Shipped, Not MVP]**
As a Lab Technician, I want to batch samples from multiple NimbleLIMS projects together if they have compatible test types so that shared processing steps like prep can be efficient.
Acceptance Criteria:
- Batch creation allows selection across accessible projects.
- Validation for compatibility (e.g., shared prep analysis like "EPA Method 8080 Prep").
- Option to split into sub-batches for divergent steps (e.g., cleanup/instrument runs).
- RLS enforces access to all included samples.
- **Expiration validation**: Validate-compatibility endpoint warns about expired/expiring samples.
- **Priority sorting**: Eligible samples from all projects sorted by expiration then due date.
- API: POST /batches with cross-project container_ids; POST /batches/validate-compatibility with expiration warnings; RBAC: batch:manage.
Priority: Medium | Estimate: 5 points

### US-27: Add QC Samples at Batch Creation **[Shipped, Not MVP]**
As a Lab Technician, I want to add QC samples directly during batch creation so that controls are integrated contextually.
Acceptance Criteria:
- Select qc_type (e.g., Blank, Blank Spike, Duplicate, Matrix Spike) and auto-generate QC sample/container.
- Link to batch with inherited project_id.
- Required for certain batch types (configurable).
- QC samples inherit `date_sampled` from parent sample for expiration tracking.
- API: POST /batches with qc_additions list; RBAC: batch:manage.
Priority: Medium | Estimate: 5 points


## 3. Results Management Enhancements

### US-28: Batch Results Entry **[Shipped, Not MVP]**
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
Total Estimate: ~31 points. 

## Post-MVP Features (Already Shipped)

### Custom Fields (EAV Model) **[Shipped, Not MVP]**  
  As an Administrator, I want to define custom attributes for samples, tests, results, projects, client_projects, and batches without schema changes so that the system can be customized for laboratory-specific requirements.  
  *Acceptance Criteria*:  
  - Admin interface for creating custom attribute configurations (entity_type, attr_name, data_type, validation_rules).  
  - Support for data types: text, number, date, boolean, select.  
  - Validation rules: min/max for numbers, length for text, options for select.  
  - Dynamic field rendering in forms based on configurations.  
  - Server-side validation against active configurations.  
  - Custom attributes stored in JSONB columns with GIN indexes for querying.  
  - List endpoints support filtering via `?custom.attr_name=value`.  
  - API: CRUD /admin/custom-attributes; RBAC: config:edit.  
  *Status*: Implemented (Post-MVP) | *Estimate*: 13 points

### US-29: Workflow Templates and Execution **[Shipped, Not MVP]**

As a Lab Technician or Lab Manager, I want to run predefined workflow templates from accessioning, batch details, or results entry so that repeatable process steps can be applied consistently with minimal clicks.

As an Administrator, I want to create and manage workflow templates (steps with actions and params) so that the lab can standardize and automate common workflows.

**Acceptance Criteria**:

- **Template management** (Administrator, config:edit):
  - Create workflow template: name (unique), description, active, template_definition (JSON with `steps` array).
  - Each step: `action` (one of update_status, validate_custom, create_qc, assign_tests, create_batch, enter_results, send_notification, accession_sample, link_container, review_result), optional `params` object.
  - Edit and soft-deactivate (delete sets active=false) templates.
  - List/filter templates by active status.
  - API: GET/POST /admin/workflow-templates, GET/PATCH/DELETE /admin/workflow-templates/{id}.

- **Execution** (workflow:execute):
  - Execute an active template with optional context (e.g. {} for accessioning, { batch_id } for batch, { batch_id, test_id } for results entry).
  - Execution runs all steps in order in a single transaction; invalid step action returns 400; step failure returns 500 and rolls back (no workflow instance created).
  - Successful run creates one workflow_instance with runtime_state (context, steps_run, completed).
  - API: POST /workflows/execute/{template_id} with body { name?, context? }.

- **UI**:
  - Admin: Workflow Templates page (DataGrid, Add/Edit/Deactivate, Execute-on-Entity dialog with context JSON).
  - Accessioning form: Apply Template dropdown + Apply (context {}); on success refresh lookup data and show success message.
  - Batch details view: Apply Template dropdown + Apply (context { batch_id }); on success refresh batch details.
  - Results entry: Apply Template dropdown + Apply (context { batch_id, test_id }); on success parent refreshes batch data.
  - Apply Template controls visible only when user has workflow:execute permission.
  - Loading states and error/success alerts for apply action.

- **RBAC**: config:edit required for template CRUD; workflow:execute required for execute. Unauthorized users receive 403.

*Priority*: Medium | *Estimate*: 8 points | *Status*: Implemented (Post-MVP)

Future: Instrument integration, automated calculations.

---

# SOP-Derived User Stories (Issues #22–#26)

Atomic-receive P0 (PR 30) is accession/order/results only. UAT for that packet follows the sketch, not US-31 receipt-event or US-38 remaining-qty.

These stories address sample identity, dispositions, audit trails, and result review/amendment requirements derived from laboratory SOP analysis.

## Sample Identity and Accessioning

- **US-30: Immutable Lab ID with Separate External ID** **[MVP]**  
  As a Lab Technician, I want the system to assign a unique, immutable sample ID while I scan the tube barcode, and to keep any submitter external ID separate, so that sample identity and tube identity cannot be mixed up.  
  *Acceptance Criteria*:  
  - Two identities (atomic-receive PR 30; Lab Ops L1 retracted):  
    - `samples.name` is the lab sample ID, **system-assigned** from the existing name template/sequence. Tech does **not** type it. Receive screen has **no sample-ID field**.  
    - `containers.name` is the scanned (or typed) tube barcode. Duplicate scan → HTTP 409 on the container only.  
    - `samples.name` 409 only if the generated sample ID itself collides.  
  - Submitter/external ID stored as-is in existing `client_sample_id` (optional; unique if present). Never mutated into the sample ID or barcode.  
  - Receipt **datetime** stored in existing `received_date` (not encoded in either identifier).  
  - Lookup is scan the tube. Mix-up is unacceptable if receive or lookup makes the tech hunt or type the sample ID.  
  - Aliquot later (not atomic-receive): another container + contents row on the **same** sample (new barcode, same sample ID).  
  - Derivative later (not atomic-receive): new sample with `parent_sample_id` (new system sample ID).  
  - Lab ID must not encode location, PHI, or other variable data.  
  - API: POST /api/samples/receive. Do **not** add `lab_id` or `external_id` columns.  
  - **Lab Ops gate**: Deiter retracted L1; two IDs accepted 2026-08-20. Receive must not show a sample-ID field.  
  *Priority*: High | *Estimate*: 8 points  
  *Related*: Issue #24

- **US-31: Receipt Event with Condition and Disposition** **[MVP]**  
  As a Lab Technician, I want to record comprehensive receipt details including condition, manifest match, and disposition so that acceptance/rejection decisions are documented.  
  *Acceptance Criteria*:  
  - Not in atomic-receive P0 receive body. P0 records receipt as `received_date` only. Do not seed a receipt-event table for that packet.  
  - Receipt event captures: **datetime** (date and time), who received, condition (intact/leaking/damaged/tampered), manifest match (yes/no/partial), temperature or "dry ice sufficient".  
  - Disposition at receipt: Accept, Reject, or Quarantine with reason.  
  - Manifest mismatch can still create a receipt event (discrepancy is recorded, not blocked).  
  - Rejected samples are **not hard-deleted**; record survives physical disposal.  
  - Quarantine is a real disposition (not a comment field); samples remain segregated until ID/quality checks resolve.  
  - API: POST /samples/receipt-event or extend POST /samples with receipt_event nested object.  
  *Priority*: High | *Estimate*: 5 points  
  *Related*: Issues #23, #24

- **US-32: Sample Dispositions (Quarantined, Rejected, Discarded)** **[MVP]**  
  As a Lab Technician or Lab Manager, I want to mark samples as Quarantined, Rejected, or Discarded so that disposition is first-class and auditable.  
  *Acceptance Criteria*:  
  - Add Quarantined, Rejected, Discarded to sample status/disposition options (list-backed).  
  - Quarantined: sample segregated until checks complete; cannot be used for test ordering.  
  - Rejected: sample not acceptable; reason required; record survives physical destruction.  
  - Discarded: disposal event with remaining quantity = 0; who, when, method, justification.  
  - Rejected and Discarded samples remain searchable by `samples.name` (not hard-deleted from database).  
  - Cancelled belongs on the **order**, not the sample (future: order cancellation story).  
  - "On hold" status: no public SOP found; remains optional/parked.  
  - API: PATCH /samples/{id} with status; POST /samples/{id}/disposal-event for Discarded.  
  - UAT: Rejected sample records survive deletion; quarantined samples blocked from test assignment; disposal leaves durable record.  
  *Priority*: High | *Estimate*: 5 points  
  *Related*: Issue #23

## Audit Trail and Data Integrity

- **US-33: Append-Only Audit Events** **[MVP]**  
  As a Lab Manager or Administrator, I want an append-only audit trail for all critical changes so that compliance requirements are met and data integrity is ensured.  
  *Not in atomic-receive P0.* New audit tables/events are out of AR-01–AR-15 (no new tables this packet).  
  *Acceptance Criteria*:  
  - Audit events table: entity type, entity_id, event_type (created/updated/deleted/reviewed/reported), old_value, new_value, changed_by (user_id), changed_at (timestamp with time zone), reason (required once result is reviewed/reported).  
  - Events captured for: sample, order/test, result, spec/analysis, user account changes.  
  - Append-only: admin users **cannot edit or delete** audit log entries.  
  - Users cannot disable audit logging.  
  - Unique users required: no shared lab login accounts permitted.  
  - Disabled users remain in historical audit records (not deleted).  
  - Server-generated timestamps (not user-editable without creating a new audit event).  
  - Reason field required for changes to reviewed/reported results.  
  - API: GET /audit-events with filters; no DELETE or PATCH endpoints for audit events.  
  - Database: append-only constraint; admin role cannot bypass.  
  - **Important**: Do NOT claim "21 CFR Part 11 certified" compliance. E-signatures with meaning and re-authentication are post-MVP.  
  - UAT: Verify admin cannot edit audit log; verify reason required for post-review changes; verify disabled user still appears on historical actions.  
  *Priority*: High | *Estimate*: 13 points  
  *Related*: Issue #25

- **US-34: Audit Event Reconstruction for Compliance** **[MVP]**  
  As a Lab Manager or Auditor, I want to reconstruct the complete history of any sample, test, or result so that regulatory compliance (ISO 20387, GTEx, 21 CFR) is supported.  
  *Not in atomic-receive P0.* Out of AR-01–AR-15.  
  *Acceptance Criteria*:  
  - History view shows all audit events for an entity in chronological order.  
  - Display: timestamp (with timezone), user, action, old→new values, reason (if provided).  
  - Filterable by entity type, date range, user, event type.  
  - Export capability for audit trail (CSV/JSON).  
  - API: GET /samples/{id}/audit-trail, /tests/{id}/audit-trail, /results/{id}/audit-trail.  
  - UI: Audit History tab on detail views; admin Audit Log page with global search.  
  *Priority*: Medium | *Estimate*: 5 points  
  *Related*: Issue #25

## Test Ordering and Results

- **US-35: Test Ordering Against Accepted Samples Only** **[MVP]**  
  As a Lab Technician, I want test ordering to be restricted to accepted/available samples so that tests are not assigned to quarantined or rejected specimens.  
  *Acceptance Criteria*:  
  - Test ordering (assign analysis to sample) requires sample status = Available for Testing (or equivalent accepted/available state).  
  - Quarantined or Rejected samples cannot have tests assigned (validation error).  
  - Catalog test (analysis) is required; free-text "other" is optional and should prompt confirmation.  
  - API: POST /tests validates sample status before creating test instance.  
  - UI: Test assignment form filters eligible samples to accepted/available only.  
  *Priority*: Medium | *Estimate*: 3 points  
  *Related*: Issue #26

- **US-36: Result Amendment After Reporting** **[MVP]**  
  As a Lab Manager, I want to amend a reported result so that corrections are tracked without overwriting the original value.  
  *Acceptance Criteria*:  
  - After a result is marked Reported: amendment creates a **new version** linked to the original.  
  - Original result remains retrievable and visible (not overwritten or soft-deleted).  
  - Amendment requires: reason, amended_by, amended_at.  
  - Both original and amended results are returned by API (with version/amendment markers).  
  - A transcription fix **before** Reported status is an audited change (via US-33), not necessarily a formal amendment.  
  - Silent overwrite is forbidden (validation error if attempted).  
  - API: POST /results/{id}/amend with new_value and reason; GET /results/{id}/history returns all versions.  
  - UI: Amendment form; result detail view shows "Original" and "Amended" versions with clear labeling.  
  - UAT: Verify original result remains after amendment; verify both versions retrievable; verify amendment without reason is rejected.  
  *Priority*: High | *Estimate*: 8 points  
  *Related*: Issue #26

- **US-37: Retest/Repeat Linked to Original Result** **[MVP]**  
  As a Lab Technician or Lab Manager, I want to create a retest order linked to the original test so that repeat analyses are traceable and the original result is preserved.  
  *Acceptance Criteria*:  
  - Retest creates a **new test/order** on the same sample with link to original test.  
  - Reason required for retest (e.g., "OOS investigation", "confirmatory").  
  - Original result remains visible and is not replaced.  
  - No automatic reflex-rules engine (clinical overkill for MVP).  
  - API: POST /tests/{id}/retest with reason; creates new test with parent_test_id.  
  - UI: Retest button on result detail; retest form prompts for reason.  
  - UAT: Verify original result visible after retest; verify retest linked to original.  
  *Priority*: Medium | *Estimate*: 5 points  
  *Related*: Issue #26

- **US-38: Aliquot Remaining Quantity Tracking** **[MVP]**  
  As a Lab Technician, I want to track remaining quantity when creating aliquots so that depletion is visible and over-aliquoting is prevented.  
  *Acceptance Criteria*:  
  - Parent sample has quantity and remaining_quantity fields.  
  - Creating aliquot decreases parent remaining_quantity by aliquot volume/amount.  
  - Cannot aliquot more than remaining quantity (validation error).  
  - Aliquot (later): new container barcode on the **same** sample ID. Derivative (later): new system sample ID. Not in atomic-receive P0.  
  - Parent history survives deleting a child aliquot.  
  - Remaining quantity = 0 signals depletion (optional link to Discarded disposition).  
  - API: POST /samples/aliquot validates remaining quantity; updates parent.  
  - UI: Aliquot form shows parent remaining quantity; validates against available amount.  
  - Parked: Numeric freeze-thaw limits (no public SOP found); robotic worklist integration.  
  *Priority*: Medium | *Estimate*: 5 points  
  *Related*: Issue #24 (aliquot identity)
