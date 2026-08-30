# Product Requirements Document (PRD) for NimbleLIMS

## 1. Introduction

### 1.1 Purpose
This Product Requirements Document (PRD) outlines the requirements for NimbleLIMS, an API-first Laboratory Information Management System (LIMS). NimbleLIMS is purpose-built for BioTech and Pharma startups.

**Platform principle — framework first:** Every lab runs the same spine — **Sample → Tests → Results → Reports** — but each lab does it slightly differently (intake style, when tests are ordered, process-driven vs backlog-driven work, review gates, fields). NimbleLIMS is a **configurable framework**: product behavior is driven by **configuration stored in the database**, not by one hard-coded lab SOP. Out of the box we ship **opinionated defaults** so a startup can operate without configuring everything; defaults are seed/config, not forever hard-coding.

See: [`.docs/discussions/2026-08-25-framework-driven-lims-accessioning.md`](../../discussions/2026-08-25-framework-driven-lims-accessioning.md) · [what-is-a-good-framework](../../discussions/2026-08-25-what-is-a-good-framework.md) · [framework stamps](../../decision-logs/framework-stamps-2026-08-26.md). Docs root: [`.docs/README.md`](../../README.md).

**MVP Definition:** The minimum viable product for **release** focuses on three core pillars that enable a startup lab to operate:
1. **Track samples** (accessioning and sample status/lineage)
2. **Order tests** (assign analyses to samples)
3. **Enter results** (capture and review test outcomes)

This MVP emphasizes essential functionality **and** configuration surfaces so those pillars are not one-path-only. The system is API-first using PostgreSQL, Python (FastAPI with SQLAlchemy), and React. There are no customers yet; the release bar is basic LIMS capability on a framework foundation.

### 1.2 Project Overview
NimbleLIMS enables BioTech and Pharma startup labs to manage compound and biological samples from receipt to results. Shipped configuration-shaped capabilities (FieldDefinitions / Field Management, lists, process definitions, experiment templates/entries, data parsers, workflow templates, etc.) are early proof of the framework approach. Hard-coded single paths (especially unfinished accessioning “wizard modes”) are **debt**, not the product vision. Deep adjacent features (dose-response, advanced containers, etc.) remain labeled as post-release enhancements where they are not release-critical.

### 1.3 Stakeholders
- **Lab Technician**: Handles daily sample accessioning (identity + first vessel), starts work (LimsRun / process) which creates Test rows, enters results with validation, and updates sample/test statuses throughout the workflow.
- **Lab Manager**: Oversees lab operations, reviews and approves test results, manages batch processing workflows, and monitors sample throughput.
- **Administrator**: Manages users, roles, permissions, and system configurations (analyses, analytes, test batteries, container types, lists).
- **CRO Partner**: Views shared project samples and test results within assigned collaborations; maintains data privacy boundaries.

*Note:* The codebase includes optional shipped capabilities (dose-response curve fitting, ELN experiment tracking) available for labs with those needs, but daily role work centers on the three-pillar MVP.

### 1.4 Version History
- Version 1.0: Initial draft based on planning discussions (October 21, 2025).
- Version 1.1: Added admin configuration features (analyses, analytes, users, roles management) - December 2025.
- Version 1.2: Added assay panels feature (grouped analyses with sequence ordering) - December 2025.
- Version 1.3: Added EAV (Entity-Attribute-Value) model for custom fields configurability - December 2025.
- Version 1.4: Repositioned for BioTech and Pharma startups; updated seed data with drug discovery assays - August 2026.
- Version 1.5: Defined MVP release bar (3 pillars: sample tracking, test ordering, results entry); labeled shipped features as adjacent enhancements - August 20, 2026.
- Version 1.6: Added SOP-derived requirements (Issues #22–#26): immutable lab ID, sample dispositions (quarantine/reject/discard), append-only audit trail, result review/amendment, status model reconciliation, second-person review configurability - August 20, 2026.
- Version 1.7: Framework-first platform principle; OOB defaults vs hard-coded paths; accessioning flexibility via DB-backed profiles (discussion 2026-08-25) - August 25, 2026.
- Version 1.8: Work-order / routing layer; teams (Leadership/Dev/QA/Docs); docs reorg under `.docs/` - August 26, 2026.
- Version 1.9: **WO-7 fold** — Test row is created at **LimsRun start** (refuse publish if missing), not at accession or bare order. Accessioning assigns identity + first vessel only. Sequencing: AR P0 -> work-order packet -> registration/lots -> intake profiles. August 26, 2026.
- Version 1.10: Post-receive work spine opened — asked-for (lake) → work_order → results persist → SOP+AI process apply → parser setup. Wizard removed. August 28, 2026.

## 2. Goals and Objectives

### 2.0 Framework principles (product)

| Principle | Detail |
|-----------|--------|
| **Same spine** | Sample → (Order/asked-for) → Work order → Process/Exp/LimsRun → Results → Reports |
| **Different how** | Intake configs, field sets, routing maps, process packs, review gates, analysis params |
| **Config in DB** | Joints admin-editable (`config:edit`); sidebar active configs = config:edit (FW-1b) |
| **OOB defaults** | Atomic receive intake; example type transitions / process packs — not empty shell |
| **One execute substrate** | Route into Process / Experiment / LimsRun — no parallel workflow engine |
| **Process = sample in a container** | A sample may have many vessels. Only **Contents** (sample + container) is assigned to a process |
| **AuthZ unchanged** | Configuration never bypasses RLS / sample-create AuthZ |

### 2.1 Business Goals
- Provide BioTech and Pharma startups with **basic LIMS capability** to track samples, order tests, and enter results—the foundation for lab operations.
- Sell a **framework**, not a single hard-coded SOP: labs configure how they run the shared spine.
- Ensure data security and IP protection with role-based access and CRO-partner isolation.
- Enable labs to start **immediately** via OOB defaults, then adapt configuration as their SOPs diverge.
- Extend with customer-driven enhancements (dose-response, ELN depth, instrument integration) on the same framework substrate.

### 2.2 User Goals
- Efficiently accession compounds and biological samples with lineage tracking (aliquots, derivatives)—via the lab’s configured intake profile (default: high-throughput scan receive).
- Assign analyses (or test batteries) to samples and/or drive work through processes—without ambiguous “what’s next?” queues (work-model config is a follow-on; see accessioning A-15).
- Enter and review results with validation rules (data types, ranges, significant figures).
- Securely share sample and test data with external CRO partners while maintaining IP boundaries.
- Admins configure fields, lists, intake profiles, process definitions, and gates without waiting for a code change.

### 2.3 Success Metrics
- 100% coverage of MVP release bar: sample tracking, test ordering, results entry.
- User satisfaction: <5 minutes for sample accessioning on the **OOB default** profile; consistent results entry workflow.
- A second intake style can be expressed as **configuration** (not a fork) when Leadership opens that packet.
- Performance: API responses <500ms; handle 1,000+ samples without degradation.
- Security: No unauthorized data access; role-based isolation; config mutate least-privilege.

## 3. MVP Release Definition

### 3.1 MVP Release Bar (In Scope for Initial Release)
The release bar is **basic LIMS capability** for a startup lab with **no customers yet**. The product needs fundamental functionality that can be extended when specific customer requirements emerge.

| Pillar | Core Capability | What's Required |
|--------|----------------|-----------------|
| **1. Track samples** | Sample accessioning, status management, basic lineage | Receive samples, assign identifiers, track workflow status (Received → Available for Testing → Testing Complete → Reviewed → Reported), link aliquots/derivatives to parents |
| **2. Order tests** | Ask for work; Test exists when execute starts | Work-order / asked-for analysis is the request (WO packet). **WO-7:** a `tests` row is created at **LimsRun start** (refuse publish if missing) -- **not** at accession and **not** on a bare order. A-15 parked. |
| **3. Enter results** | Capture and review test outcomes | Enter raw results per test/analyte with validation; review and approve results; update test/sample statuses |

**Supporting infrastructure required for MVP:**
- **Security & Auth**: User authentication, RBAC with core permissions (sample:create, test:assign, result:enter, result:review, etc.), project/client data isolation
- **Configuration**: Manage analyses, analytes, test batteries, container types, lists (statuses, types), users, roles
- **Containers**: Track physical storage (tubes, plates, wells) with hierarchical nesting; link samples to containers
- **Batches**: Group containers for processing workflows (Created → In Process → Completed)

### 3.2 Shipped But Not MVP (Already in Codebase, Post-Release Enhancement)
These features are **implemented and on main** but are **not the release bar**. They demonstrate platform capability and remain available for users who need them, but they are enhancements beyond the three-pillar MVP:

| Feature Area | What's Shipped | Status |
|-------------|----------------|--------|
| **ELN (Experiments/Processes/Entries)** | Full experiment management with templates, typed process steps (eln_experiment \| lims_run), sample journey, entry capture (Tables & forms), process definitions | **Shipped/In-Tree, Not MVP** — enhances lab workflow orchestration beyond basic sample-test-result |
| **LimsRuns / Data Parsers** | Instrument/CRO data import with configurable parsers, promote-on-publish to structured Results, replicate/lineage tracking | **Shipped/In-Tree, Not MVP** — enhances results entry with instrument integration; manual entry is the MVP path |
| **Dose-Response / IC50 / 4PL** | Curve fitting via R calculator microservice, percent-inhibition normalization, curve curator UI with batch approve/reject, data point knockout | **Shipped/In-Tree, Not MVP** — specialized assay analysis for screening campaigns; basic result values are the MVP |
| **Workflow Templates** | Reusable JSON workflow definitions with actions (update_status, create_qc, assign_tests, etc.), execution with context, apply from accessioning/batch/results entry | **Shipped/In-Tree, Not MVP** — automation layer beyond manual workflows |
| **Custom Fields (EAV)** | Admin-configurable custom attributes for samples/tests/results/projects/batches with validation rules, dynamic forms, JSONB storage | **Shipped/In-Tree, Not MVP** — extensibility beyond fixed schema; core fields are the MVP |
| **Field Management** | Unified admin UI for OOB + Custom fields, list-backed selects via source lists, validation rules | **Shipped/In-Tree, Not MVP** — advanced configuration beyond basic lists |
| **Containers (Advanced)** | Multi-element containers (plates/racks), single-element (wells/tubes), contents with solute mass/concentration, rows×columns type shape, nested hierarchies, pooled samples | **Partially MVP** — basic tube/plate tracking is MVP; advanced pooling/aliquot calculations are post-release refinement |
| **Materials/Lots** | Reagent/kit tracking with lot traceability | **Not Shipped, Parked** — deferred until customer chemistry ops needs |
| **Client Projects** | Hierarchical grouping of LIMS projects under client projects | **Shipped/In-Tree, Not MVP** — organizational feature for multi-project tracking |
| **Multi-Tenancy** | Org-scoped data segregation beyond client-level RLS | **Not Shipped, Parked** — deferred until multiple organizations use the product |
| **Advanced Reporting/Export** | PDF reports, complex multi-parameter calculations | **Not Shipped, Out of Scope** — basic data access via API/UI is MVP |

### 3.3 Out of Scope / Parked Until Customer Request
Work that is explicitly **not required** to release a basic LIMS and should **not pull new requirements or open questions** until a real customer asks:

- **Instrument integration (automated)**: LimsRuns/parsers exist but are not the release path; manual results entry is sufficient for MVP
- **Advanced dose-response workflows**: Curve fitting is shipped but not required; basic result values are the release bar
- **Workflow orchestration engines**: Templates exist but are not required; manual workflows are the MVP path
- **Speculative container/aliquot models**: Advanced pooling, solute mass calculations, multi-element auto-spawn beyond basic tube/plate tracking
- **Materials/lot tracking**: Reagent traceability deferred until customer chemistry ops requirements exist
- **Multi-tenancy**: Org segregation beyond client-level RLS deferred until multi-org production use
- **Custom fields**: EAV model shipped but not required; fixed schema fields are the MVP
- **Client projects**: Hierarchical project grouping shipped but not required for basic LIMS operation

**Product discipline:** These adjacent features must be labeled as **not MVP** in all documentation and must **not** spawn new requirements, user stories, or open questions until a specific customer need is validated.

## 4. Scope (Detailed Feature Breakdown)

### 4.1 Sample Tracking (MVP Release Bar + Shipped Enhancements)
**MVP Core:**
- **Accessioning**: Receive identity + first vessel (atomic receive P0). **Do not assign tests / create `tests` rows at intake** (WO-7; A-15 parked). Inspect / receipt-event / review-release are later packets, not AR P0.
- **Receipt Event**: Datetime (not date-only), who received, condition (intact/leaking/damaged/tampered), manifest match, accept|reject|quarantine + reason. Manifest mismatch can still create a receipt event.
- **Identity Management**: 
  - Submitter/external ID stored as-is (no mutation).
  - Separate immutable `lab_id` (barcode) assigned by lab; never changes.
  - Duplicate lab barcode rejected (no collision algorithm; system refuses duplicates).
  - Receipt timestamp is a field, not encoded in the identifier.
  - Each aliquot gets a **new** lab_id (not shared with parent).
  - Lab ID must not encode location or PHI.
  - Typed entry acceptable; scan supported but not mandated.
- **Status management**: Received, Available for Testing, Testing Complete, Reviewed, Reported (existing UAT values remain valid).
  - **Direction**: Sample.status tracks specimen state; Reviewed/Reported belong on result/report (compatibility path: both approaches work during transition).
  - **Additional dispositions**: Quarantined (segregated until checks complete), Rejected (not acceptable; reason required), Discarded (disposal event with remaining qty = 0).
  - Rejected/Discarded samples **not hard-deleted**; records survive physical destruction.
  - **Cancel** belongs on the order, not the sample.
  - "On hold": no public SOP found; remains optional/parked.
- **Aliquots/Derivatives**: Linked via parent_sample_id; inheritance of project/client; created in workflows (e.g., DNA extraction).
  - Parent remaining_quantity decreases; cannot aliquot more than remaining.
  - Child has new lab_id; parent history survives deleting child.
- **Containers (basic)**: Tubes and plates with hierarchical nesting (self-referential); contents linking samples to containers.

**Shipped Enhancements (Not MVP):**
- Advanced pooled samples with concentration/amount calculations using unit conversions
- Multi-element container auto-spawn, solute mass vs diluent modeling, derived volume calculations
- QC sample types with batch integration (Blank, Control, Spike, Duplicate)
- Bulk accessioning with common/unique fields and sequential name generation

**Parked (Out of MVP):**
- Forensic chain-of-custody every-handoff forms
- Live freezer probe integration and mapping
- Numeric freeze-thaw limits (no public SOP specifying "max N")
- After-hours accessioning SOP (no public procedure found)
- Duplicate-barcode collision algorithm (product refuses; no resolution algorithm sourced)
- CGT chain of identity / ISBT 128 (autologous cell therapy; not in research MVP)
- CLIA retention clocks, 21 CFR 58.195 hardcoded retention math

### 4.2 Test Ordering (MVP Release Bar)

**WO-7 (Leadership 2026-08-26):** A **`tests` row is created or attached at LimsRun start** -- **not at accessioning**, **not on a bare order**, **not at publish**. Publish **refuses** if the Test is missing (no find-or-create). Accessioning is identity + first vessel only. Optional `analysis_ids` on receive that mint Test rows are **struck**.

**MVP Core:**
- **Asked-for work** (analysis / battery / TAT) lives on the **work order** (WO packet -- after AR P0). That is the request, not the Test instance.
- **Test instance** = execute-time row: created or attached when a LimsRun **starts**. Publish **refuses** if the Test is missing (Hans/Heidi/Gunter punch). Status lifecycle starts there.
- Test batteries, if used, expand on the **work order / routing map**, not by minting Tests at intake.
- **A-15 parked:** do not treat Tests as the process work-queue; Process / Experiment / LimsRun remain execute SoT.

**Sequencing:** AR P0 (Marc green-light) -> work-order packet -> registration/lots -> intake profiles. Not IC50.

### 4.3 Results Entry (MVP Release Bar + Shipped Enhancements)
**MVP Core:**
- **Entry**: Batch/plate-based entry: Select batch (container collection), test; display analytes for entry.
- **Fields**: raw_result, reported_result, qualifiers, unit (where applicable; qualitative coded values may omit unit), analyst, **server timestamp** (not user-editable without audit trail).
- **Validation**: Per analyte (data type, ranges, sig figs).
- **Test Ordering**: Only against existing, accepted/available samples (not quarantined or rejected; not unknown ID). Catalog test required.
- **Review and Release**:
  - Result-level review/release states (direction: not only Sample.status = Reviewed/Reported).
  - **Second-person review gate is tenant-configurable**: default OFF for pure R&D, default ON for GxP/CRO-release.
  - When gate is ON: reviewer ≠ enterer (same user blocked from reviewing own result).
  - When gate is OFF: self-review permitted (pure R&D use case).
  - Lab manager reviews at test/result level; updates review statuses.
- **Amendment**:
  - After Reported: amendment creates a **new version** linked to original; both remain retrievable.
  - Silent overwrite forbidden; reason required for amendment.
  - A transcription fix **before** Reported is an audited change, not necessarily a formal amendment.
- **Retest**: Linked new order on same sample, reason required, original result kept. No reflex-rules engine.
- **OOS/Failing Results**: Flag result vs spec (pass/fail/unknown); keep failing data (no silent delete); reason + investigation link. Full OOS module (Phase I/II investigation) is post-MVP.
- **Cancel After Reported**: Blocked or becomes amendment (label as unverified practice / open question if not sourced in SOP).

**Shipped Enhancements (Not MVP):**
- Batch results entry with tabular UI and atomic submit
- QC validation with failing QC flags/blocks (optional "block report if QC failed" for GxP/CLIA tenants)
- LimsRun promote-on-publish: structured Results from instrument/CRO data (import remains flexible JSONB)
- Replicate tracking, conflict resolution (same-run update vs other-run fail), lineage via lims_run_id

**Parked (Out of MVP):**
- Full OOS/OOT investigation module (Director-gated Phase I/II, Material Review Board)
- Reflex-rules engine (automatic additional testing; clinical overkill)
- Instrument data parsers (LimsRuns exist but not MVP path; manual entry is release bar)
- Westgard multi-rules, control charts (QC depth beyond basic pass/fail)

### 4.4 Audit Trail and Data Integrity (MVP Required)
**GxP-Ready Data Model (Not a Part 11 Certification Claim):**
- **Append-only audit events** on sample, order/test, result, spec/analysis, user account changes.
- **Event fields**: entity_type, entity_id, event_type (created/updated/deleted/reviewed/reported), old_value, new_value, changed_by (user_id), changed_at (timestamp **with time zone**), reason (required once result is reviewed/reported).
- **Immutable log**: Admin users **cannot edit or delete** audit events.
- **User accountability**: Unique users required (no shared lab login); disabled users remain in historical records (not deleted).
- **Server timestamps**: System-generated (not user-editable without creating new audit event).
- **Reason on GxP changes**: Reason field required for changes to reviewed/reported results.
- **History reconstruction**: GET endpoints for audit trails per entity; export capability (CSV/JSON).
- **Do NOT claim "21 CFR Part 11 certified"**: FDA does not certify software. E-signatures with meaning (review/approval/authorship) and re-authentication (11.50, 11.200) are post-MVP.

**Post-MVP (GxP-Path Later):**
- E-signatures with meaning and re-authentication
- Signature bound to record (11.70)
- Printouts showing if data changed since original entry (Annex 11 §8.2)
- Validated backup/restore evidence pack
- Audit-trail review workspace

### 4.5 Security and Auth (MVP Required)
- RBAC with 17 permissions (e.g., sample:create, result:enter, batch:manage, result:review)
- User auth: Username/password + email verification
- **Unique users**: No shared lab login accounts permitted (data integrity requirement).
- Client isolation: View own projects/samples only; project_users junction for access
- Row-Level Security (PostgreSQL RLS policies) for multi-tenant data protection
- **Disabled users**: Account deactivation (not deletion); historical actions remain attributed

### 4.6 Configurable Elements (MVP Required + Shipped Enhancements)
**MVP Core:**
- **Lists**: Statuses, types, matrices (admin-editable via UI/API)
- **Analyses**: Admin-configurable with methods, turnaround times, costs
- **Analytes**: Admin-configurable; linked to analyses via validation rules
- **Analysis-Analyte Rules**: Validation (data types, ranges, significant figures, required flags)
- **Test Batteries**: Groups of analyses with sequence ordering and optional flags
- **Container Types**: Pre-setup by administrators (tube, plate, well, rack)
- **Users & Roles**: CRUD for users, roles, permissions

**Shipped Enhancements (Not MVP):**
- **Custom Fields (EAV)**: Admin-configurable attributes for samples, tests, results, projects, batches with dynamic forms, JSONB storage, validation rules
- **Field Management**: Unified UI for OOB + Custom fields, list-backed selects via source lists
- **Workflow Templates**: Reusable JSON workflows with actions (update_status, create_qc, assign_tests), execution with context
- **Name Templates**: Configurable entity naming with placeholders ({SEQ}, {PROJECT}, etc.)
- **Client Projects**: Hierarchical grouping of LIMS projects

### 4.7 Status Model Reconciliation and Compatibility

**Background**: The current Sample.status list (`Received → Available for Testing → Testing Complete → Reviewed → Reported`) mixes **sample lifecycle** with **result review/release** states. SOP analysis shows these are distinct concerns.

**Product Direction**:
- **Sample.status**: Tracks specimen state (Received, Available for Testing, Quarantined, Rejected, Discarded, etc.).
- **Result/Report states**: Review and release tracking belongs on the result/report entity (not Sample.status).
- **Testing Complete**: This reflects order/work status, not specimen identity. Direction is to track testing progress on test/order entities.

**Compatibility Path (Does Not Break UAT)**:
- The existing five status names (`Received`, `Available for Testing`, `Testing Complete`, `Reviewed`, `Reported`) remain valid list values.
- Product implementation shifts review/release controls to result-level (US-10, US-36) without removing the UAT-familiar status names.
- Free-form status updates (any `sample:update` user can set status) are **not** second-person review; product direction adds proper review gates on results (tenant-configurable).
- **Open question for Tobias**: When can UAT stop treating `Reviewed`/`Reported` as Sample.status values and rely on result-level review/release instead?

**Additional Sample Dispositions (From SOP Analysis)**:
- **Quarantined**: Segregated until ID/quality checks complete; cannot be used for test ordering.
- **Rejected**: Not acceptable; reason required; record survives physical destruction.
- **Discarded**: Disposal event with remaining quantity = 0; who, when, method, justification.

**Cancel vs Disposition**:
- **Cancel** belongs on the **order**, not the sample (no public SOP for order cancellation found; unverified practice).
- **On hold**: No public SOP found; remains optional/parked.

**UAT Validation**:
- Verify existing five status names continue to work.
- Verify result-level review/release operates independently of Sample.status.
- Verify quarantined samples blocked from test assignment.
- Verify rejected/discarded samples remain searchable (not hard-deleted).

### 4.8 Data Model (MVP Required)
- Normalized Postgres schema with standard fields (id UUID, name unique, description, active, audit timestamps/users)
- **Key tables**: Samples, Containers, Contents, Analyses, Analytes, Analysis_Analytes, Tests, Results, Batches, Projects, Clients, Users, Roles, Permissions, Lists, **Audit_Events**
- **New/Updated Sample fields**:
  - `lab_id`: Immutable unique barcode assigned by lab (indexed, unique constraint)
  - `external_id`: Submitter/client identifier stored as-is (no mutation)
  - `received_datetime`: Timestamp with timezone (not date-only)
  - `receipt_condition`: Enum (intact/leaking/damaged/tampered) or list FK
  - `manifest_match`: Boolean or enum (yes/no/partial)
  - `disposition_reason`: Text field for reject/quarantine justification
  - `remaining_quantity`: Numeric (decreases with aliquoting; 0 = depleted)
- **Audit_Events table** (append-only):
  - `id`, `entity_type`, `entity_id`, `event_type`, `old_value` (JSONB), `new_value` (JSONB), `changed_by` (user_id FK), `changed_at` (timestamp with timezone), `reason` (text, required for reviewed/reported changes)
  - Database constraint: no UPDATE or DELETE on audit_events (append-only enforcement)
- **Result versioning** (for amendments):
  - Results table: add `version` (integer), `parent_result_id` (self-referential FK), `amendment_reason` (text)
  - Original result: version=1, parent_result_id=null
  - Amended result: version=2+, parent_result_id points to original
- Relationships: Normalized with FKs (e.g., samples → projects, tests → samples/analyses, audit_events → users)

## 5. Out of Scope for MVP Release (Defer Until Customer Need)
The following are explicitly **not required** to ship a basic LIMS and should be deferred until specific customer requirements are validated:

- **Automated instrument integration**: LimsRuns/parsers are shipped in the codebase but are **not the MVP release path**; manual results entry is sufficient for the release bar. Instrument data import is an enhancement for labs with high-volume automated workflows.
- **Advanced dose-response workflows**: Curve fitting (4PL, IC50) is shipped but not required; basic result values (raw_result, reported_result) are the release bar. Dose-response analysis is an enhancement for drug discovery screening campaigns.
- **Workflow orchestration engines**: Workflow templates are shipped but not required; manual workflows (accessioning → test assignment → results entry → review) are the MVP path.
- **ELN/experiment management**: Full experiment tracking with templates, processes, entries is shipped but not required; basic sample-test-result tracking is the release bar. ELN features enhance lab workflow orchestration beyond core LIMS.
- **Speculative container/aliquot models**: Advanced pooling calculations, solute mass vs diluent modeling, multi-element auto-spawn are shipped refinements; basic tube/plate tracking with parent_sample_id lineage is the MVP.
- **Materials/lot tracking**: Reagent and kit traceability is parked until customer chemistry ops requirements exist.
- **Multi-tenancy**: Org-scoped data segregation beyond client-level RLS is parked until multiple organizations use the product in production.
- **Custom fields (EAV model)**: Shipped but not required; fixed schema fields (samples, tests, results) are the MVP. Custom fields are an extensibility enhancement.
- **Client projects**: Hierarchical grouping of LIMS projects is shipped but not required for basic LIMS operation.
- **Result calculations/formulas**: calculated_result is a stub; manual entry of final values is the MVP.
- **Advanced reporting/export**: PDF reports, complex exports are out of scope; basic data access via API/UI is the MVP.
- **Multi-factor auth or third-party OAuth**: Username/password with RBAC is the MVP.
- **Mobile app; full internationalization**: Web UI only; English is the MVP.
- **Performance optimizations for >10,000 samples**: Handle 1,000+ samples is the MVP bar.

**Reconciliation Note:** The codebase contains LimsRuns/parsers, dose-response/IC50, ELN experiments, workflow templates, and custom fields. These are **in the tree** and **shipped** but are **not the release bar**. They demonstrate platform extensibility and remain available for users who need them, but the MVP release focuses on the three-pillar foundation: sample tracking, test ordering, results entry.

## 6. User Roles and Permissions

| Role            | Description                                                                 | Key Permissions (Examples) |
|-----------------|-----------------------------------------------------------------------------|----------------------------|
| Administrator  | Manages system, users, and configs.                                        | All (17): user:manage, role:manage, config:edit, project:manage, sample:*, test:*, result:*, batch:*. |
| Lab Manager    | Oversees operations, reviews results.                                       | result:review, batch:manage, test:assign. |
| Lab Technician | Handles daily tasks like accessioning and entry.                            | sample:create, result:enter, test:assign. |
| Client         | Views own data.                                                             | sample:read (own), result:read (own). |

Permissions managed via roles, permissions, and role_permissions tables (17 total permissions: sample:create, sample:read, sample:update, test:assign, test:update, result:enter, result:review, result:update, result:delete, batch:manage, batch:read, batch:update, batch:delete, project:manage, user:manage, role:manage, config:edit).

**Note**: The code references `test:configure` permission in several places, but this permission is not currently created in the database. Endpoints that reference it use `require_any_permission(["config:edit", "test:configure"])`, which effectively requires `config:edit` permission.

## 7. Functional Requirements (Detailed Workflows & APIs)
These functional requirements support the MVP release bar (sample tracking, test ordering, results entry) plus shipped enhancements that remain in the codebase.

### 7.1 Workflows
- **Sample Accessioning**:
  - Receive shipment; inspect/note anomalies; enter data (double-entry optional); assign tests; review/release.
  - Required fields: due_date, received_date (timestamp), sample_type, status, matrix, temperature.
- **Aliquots/Derivatives Creation**:
  - Workflow step: Select parent; create child with new container_id (aliquot) or sample_id/type (derivative).
  - Inherit project/client; update statuses.
- **Test Ordering**:
  - At accessioning: Assign analysis_id to sample → create test instance.
- **Results Entry**:
  - Select batch/container; choose test; enter per analyte with validation.
  - Update test/sample statuses on completion/review.
- **Batch Processing**:
  - Create batch; add containers; status flow: Created → In Process (analysis) → Completed (review).
- **Pooled Samples** (Pending Refinement): Add multiple contents to container; calculate concentration/amount (e.g., average/sum rules).

### 7.2 API Endpoints (High-Level)
- `/samples`: CRUD with filters (project_id, status).
- `/tests`: Assign to samples; update status.
- `/results`: Enter/review per test/analyte.
- `/batches`: Create/add containers; manage status.
- `/auth`: Login, verify email.
- `/analyses`: CRUD for analyses (admin: config:edit or test:configure).
- `/analytes`: CRUD for analytes (admin: config:edit or test:configure).
- `/analyses/{id}/analyte-rules`: Configure validation rules (admin).
- `/test-batteries`: CRUD for test batteries and battery-analyses junctions (admin: config:edit or test:configure).
- `/users`: CRUD for users (admin: user:manage or config:edit).
- `/roles`: CRUD for roles and permissions (admin: user:manage or config:edit).
- `/lists`: CRUD for lists and entries (admin: config:edit).
- `/containers/types`: CRUD for container types (admin: config:edit).
- All endpoints secured via JWT with RBAC checks.

## 8. Non-Functional Requirements

### 8.1 Security
- RBAC with granular permissions; RLS in Postgres for row-level access.
- Data isolation: Clients see only own projects (via client_id, project_users).
- Encryption: Password hashes (bcrypt); sensitive data at rest (Postgres defaults).

### 8.2 Performance
- Handle 500 concurrent users; <1s query times.
- Indexing on FKs (e.g., project_id, sample_id).

### 8.3 Usability
- React UI: Intuitive forms for workflows; real-time validation.
- Accessibility: WCAG 2.1 compliant.

### 8.4 Reliability
- Audit trails on all tables.
- Error handling: Graceful API failures with codes.

### 8.5 Scalability
- Normalized schema; UUIDs for distributed potential.

## 9. Data Model Overview

### 9.1 Key Tables and Fields
- **Samples**: id (UUID), name, description, active, audit fields, due_date, received_date, report_date, sample_type (FK list), status (FK), matrix (FK), temperature, parent_sample_id, project_id, qc_type (FK).
- **Containers**: id, name (barcode optional), row, column, concentration, amount, type_id (FK container_types), parent_container_id.
- **Contents**: container_id, sample_id, concentration, amount.
- **Analyses**: id, name, method, turnaround_time, cost.
- **Analysis_Analytes** (Junction): analysis_id, analyte_id, data_type, high/low, sig_figs, etc.
- **Test_Batteries**: id, name, description, active, audit fields.
- **Battery_Analyses** (Junction): battery_id, analysis_id, sequence (int >=1), optional (bool).
- **Tests**: id, sample_id, analysis_id, battery_id (nullable), status, review_date, test_date, technician_id.
- **Results**: id, test_id, analyte_id, raw_result, reported_result, qualifiers, etc.
- **Batches**: id, name, type, status, dates.
- **Batch_Containers** (Junction): batch_id, container_id.
- **Projects**: id, name, description, start_date, client_id, status.
- **Project_Users** (Junction): project_id, user_id, access_level.
- **Clients**: id, name, description, billing_info (JSONB), status; linked to locations, people, contacts.
- **Users**: id, username, password_hash, email, role_id, client_id, last_login.
- **Roles/Permissions**: As defined in Section 4.
- **Lists/List_Entries**: For configurable values.

Relationships: Normalized with FKs (e.g., samples → projects, tests → samples/analyses).

## 10. Assumptions and Dependencies
- Assumptions: Labs use standard workflows; no custom hardware needed for MVP.
- Dependencies: Postgres 15+, Python 3.10+, React 18+; libraries like FastAPI, SQLAlchemy, JWT.
- Risks: Schema changes post-MVP; ensure thorough testing for security.

## 11. Appendices
- Glossary: LIMS (Laboratory Information Management System), RBAC (Role-Based Access Control), etc.
- References: Discussions with Grok AI for schema/workflows.

---

# Post-MVP Product Requirements Document (PRD) for LIMS

**Note:** This section documents **shipped features that are not the MVP release bar**. These features are in the codebase and available for users who need them, but they are **enhancements** built on the three-pillar MVP foundation (sample tracking, test ordering, results entry). They do not define the minimum viable product for release.
## 1. Introduction
### 1.1 Purpose
This PRD outlines post-MVP enhancements for the LIMS, focusing on efficiency for high-volume workflows like bulk accessioning and batch results entry.
### 1.2 Project Overview
Extends MVP with bulk features, cross-project batching, and client project grouping for real-world scalability.
### 1.3 Stakeholders

Same as MVP, with emphasis on Lab Technicians for bulk efficiency.

### 1.4 Version History

Version 1.0: Initial post-MVP draft (December 28, 2025).
Version 1.1: Added custom fields (EAV model) for configurability - December 2025.

## 2. Goals and Objectives
### 2.1 Business Goals

Improve throughput for batch-heavy labs.
Enhance QC integration and validation.

### 2.2 User Goals

Reduce repetition in multi-sample workflows.
Group and process across projects efficiently.

### 2.3 Success Metrics

Reduced accessioning time for batches (<2 min for 5 samples).
100% QC coverage in batches.

## 3. Scope
### 3.1 In Scope

Bulk accessioning with common/uniques.
Client projects for grouping.
Cross-project batching with compatibility.
QC addition at batch.
Batch results entry with validation.

### 3.2 Out of Scope

Full automation (e.g., AI validation).
External integrations.

## 4. Functional Requirements
### 4.1 Bulk Accessioning

UI: Toggle, common fields, unique table.
Backend: Atomic multi-create.

### 4.2 Client Projects

Hierarchy: One client project → many LIMS projects.
Access: Inherited via RLS.

### 4.3 Advanced Batching

Cross-project: Compatible tests only.
QC: Auto-generate at creation.

### 4.4 Batch Results

Tabular entry; QC flags/blocks.

### 4.5 Custom Fields (Post-MVP)

**Purpose**: Enable administrators to define custom attributes for various entity types without schema changes, providing flexibility for laboratory-specific requirements.

**Functional Requirements**:

1. **Custom Field Definition**:
   - Administrators can create custom attribute configurations via admin interface
   - Each configuration specifies:
     - Entity type (samples, tests, results, projects, client_projects, batches)
     - Attribute name (unique within entity type)
     - Data type (text, number, date, boolean, select)
     - Validation rules (min/max for numbers, length for text, options for select)
     - Description (optional)
   - Configurations can be activated/deactivated (soft-delete)
   - Requires `config:edit` permission

2. **Custom Field Usage**:
   - Custom fields appear in relevant forms/views based on entity type
   - Dynamic rendering: Fields rendered based on data type (TextField, NumberField, DatePicker, Checkbox, Select)
   - Real-time validation: Client-side validation using Yup schema based on validation rules
   - Server-side validation: Backend validates against active configurations before saving
   - Unknown attributes are rejected with clear error messages

3. **Entity Support**:
   - **Samples**: Custom fields in accessioning form (SampleDetailsStep)
   - **Tests**: Custom attributes displayed in results entry table
   - **Results**: Custom fields for result metadata (e.g., reviewer notes)
   - **Projects**: Custom fields for project-specific metadata
   - **Client Projects**: Custom fields for client project metadata
   - **Batches**: Custom fields for batch-specific metadata (e.g., instrument serial)

4. **Querying**:
   - List endpoints support filtering by custom attributes: `?custom.attr_name=value`
   - Uses PostgreSQL JSONB operators for efficient querying
   - GIN indexes on custom_attributes columns for performance

5. **Bulk Mode**:
   - Custom fields can be included in bulk unique fields table
   - Supports per-sample custom attributes in bulk accessioning

**Technical Implementation**:
- Database: `custom_attributes_config` table for configurations
- Storage: JSONB columns on entity tables for actual values
- Validation: Server-side validation in `app.core.custom_attributes.validate_custom_attributes()`
- UI: `CustomFieldsManagement.tsx` for admin management, `CustomAttributeField.tsx` for dynamic rendering

### 4.6 Workflow Templates (Post-MVP)

**Purpose**: Allow administrators to define reusable workflow templates and authorized users to execute them with context (e.g. sample, batch, test) to automate repeatable steps.

**Functional Requirements**:

1. **Template Management** (requires config:edit):
   - CRUD for workflow templates (name, description, active, template_definition).
   - template_definition: JSON with `steps` array; each step has `action` (from a fixed list) and optional `params`.
   - Valid actions: update_status, validate_custom, create_qc, assign_tests, create_batch, enter_results, send_notification, accession_sample, link_container, review_result.
   - Soft-deactivate on delete (active=false).
   - Unique template names.

2. **Execution** (requires workflow:execute):
   - Execute an active template with optional context (e.g. batch_id, sample_id, test_id).
   - Steps run in order in a single transaction; on step failure, transaction rolls back and no workflow instance is created.
   - One workflow_instance record per successful run with runtime_state (context, steps_run, completed).
   - Inactive or missing template returns 404.

3. **UI Integration**:
   - Admin: Workflow Templates management page (list, create, edit, deactivate, execute-from-list with context dialog).
   - Apply Template dropdown + Apply button on Accessioning (context {}), Batch details (context batch_id), and Results Entry (context batch_id, test_id); success refreshes relevant data.

**Permissions**: config:edit for template CRUD; workflow:execute for execution. See US-29.

## 5. Non-Functional Requirements
### 5.1 Security

Extend RLS for client projects.

### 5.2 Performance

Handle 50-sample bulks <5s.

## 6. Data Model Enhancements

New: client_projects.
Updates: projects (client_project_id), samples (client_sample_id).

## 7. Assumptions and Dependencies

Builds on MVP; Alembic for migrations.