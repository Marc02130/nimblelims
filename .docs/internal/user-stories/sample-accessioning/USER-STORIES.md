# User stories — Sample accessioning

User stories in Agile form: "As a [role], I want [feature] so that [benefit]."

**MVP Release Bar:** Stories labeled **[MVP]** are required for basic LIMS (sample tracking, test ordering, results entry). **[Shipped, Not MVP]** / **[Post-MVP]** are enhancements.

**Formal review SoT** stays under `.docs/review/`. These files are local working notes (`.docs/internal/`).

**P0 focus:** atomic receive (US-1). Unfinished wizard modes deferred. A-15 / process work-queue parked.

**Domain PRD:** [`../../prd/sample-accessioning/PRD.md`](../../prd/sample-accessioning/PRD.md) · **Spec:** [`../../specs/sample-accessioning/SPEC.md`](../../specs/sample-accessioning/SPEC.md)

---

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

- **US-23: Test Battery Assignment in Accessioning** **[MVP]**  
  As a Lab Technician, I want to assign a test battery to a sample during accessioning so that all analyses in the battery are automatically created as sequenced tests.  
  *Acceptance Criteria*:  
  - Select test battery during accessioning workflow.  
  - System creates tests for all analyses in battery (ordered by sequence).  
  - Optional analyses can be skipped (future enhancement).  
  - Battery assignment can be combined with individual analysis assignments.  
  - API: POST /samples/accession with battery_id; auto-creates tests.  
  *Priority*: Medium | *Estimate*: 5 points

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

