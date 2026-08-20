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

## 4. Batches and Plates through US-29 unchanged from living docs; see prior PR 32 for US-11–US-29.

# SOP-Derived User Stories (Issues #22–#26)

Atomic-receive P0 (PR 30) is accession/order/results only. UAT for that packet follows the sketch, not US-31 receipt-event, US-33/34 new audit tables, or US-38 remaining-qty.

- **US-30** two identities as in PR 32: `samples.name` system-assigned; `containers.name` is the scan; 409 on container; no sample-ID field.
- **US-31 / US-33 / US-34 / US-38**: not in this packet’s UAT (no new tables).
- **US-7 / US-8**: Assigned/Pending at create.
