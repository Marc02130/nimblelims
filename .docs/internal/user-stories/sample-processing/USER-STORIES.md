# User stories — Sample processing

User stories in Agile form: "As a [role], I want [feature] so that [benefit]."

**MVP Release Bar:** Stories labeled **[MVP]** are required for basic LIMS (sample tracking, test ordering, results entry). **[Shipped, Not MVP]** / **[Post-MVP]** are enhancements.

**Formal review SoT** stays under `.docs/review/`. These files are local working notes (`.docs/internal/`).

**Domain PRD:** [`../../prd/sample-processing/PRD.md`](../../prd/sample-processing/PRD.md) · **Spec:** [`../../specs/sample-processing/SPEC.md`](../../specs/sample-processing/SPEC.md)

---

- **US-P-C: Process holds a sample in a container** **[MVP]**  
  As a Lab Technician, I want the process to track **which tube or well** of a sample is in this SOP, so leftover tubes and plated wells of the same sample are not all “in the process.”  
  *Acceptance Criteria*:  
  - A sample may have many containers. Only a **Contents** row (sample + 1×1 container) is assigned to a process.  
  - Assign without a container → refused.  
  - After aliquot/pool execute, dest container-with-sample continues; inbound source assignment is removed.  
  - Later work-order Start uses continuing assignments, not the original asked-for parent vessel.  
  *Priority*: High  
  *Related*: sample-processing PRD §4.1

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

- **US-6: Pooled Samples Creation** **[Shipped, Not MVP]**  
  As a Lab Technician, I want to add multiple contents to a container with concentration/amount calculations so that pooled samples are handled correctly.  
  *Acceptance Criteria*:  
  - Add contents: container_id, sample_id, concentration/units, amount/units.  
  - Calculations: Use multipliers for base unit conversions (e.g., average/sum rules; volume from concentration/amount).  
  - Base units: g/L for concentration, g for mass, L for volume, mol/L for molar.  
  - API: POST /contents; backend computes volumes.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-7: Asked-for (order analyses after receive)** **[MVP]**  
  As a Lab Technician, I want to record which analyses were requested on a received sample so that the lab has a request without pretending work has started.  
  *Acceptance Criteria*:  
  - After `/receive`, on `/asked-for` or sample detail, select analysis + TAT days (+ optional params).  
  - Creates `asked_for` with status `requested`. **Zero Tests.**  
  - Duplicate open (sample, analysis) → 409.  
  - Not on the receive form. `test:assign` + project RLS.  
  - Test row still created at **LimsRun start** (WO-7), not here.  
  - API: POST /api/v1/asked-for.  
  *Priority*: High | *Estimate*: 5 points  
  *Related*: post-receive-work-spine P1

- **US-8: Test Status Management** **[MVP]**  
  As a Lab Technician or Lab Manager, I want to update test statuses so that analysis progress is visible.  
  *Acceptance Criteria*:  
  - Statuses: Assigned/Pending (create-at-receive and add-test; atomic-receive L4), then In Process, In Analysis, Complete (from lists). Do not drop the existing three UAT names.  
  - Fields: review_date, test_date, technician_id.  
  - API: PATCH /tests/{id}; RBAC: test:update.  
  *Priority*: Medium | *Estimate*: 3 points

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

### US-28: Batch Results Entry **[Shipped, Not MVP]**
As a Lab Technician, I want to enter results for multiple tests/samples in a batch at once so that data entry is efficient for grouped processing.
Acceptance Criteria:
Tabular UI for batch with rows for tests/samples and columns for analytes.
Auto-fill common fields; real-time validation including QC checks.
Atomic submit updates all results and statuses.
Failing QC flags or blocks batch approval (configurable).
API: POST /results/batch; RBAC: result:enter.
Priority: Medium | Estimate: 8 points

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

