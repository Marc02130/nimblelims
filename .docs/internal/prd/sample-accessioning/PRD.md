# PRD: Sample accessioning

**Domain:** Sample accessioning (intake)  
**Status:** Framework-first + OOB CORE · **Leadership team: IMPLEMENT GATE OPEN (CORE only)** 2026-08-26  
**Spec:** [../../specs/sample-accessioning/SPEC.md](../../specs/sample-accessioning/SPEC.md)  
**Issues:** [ISSUES.md](ISSUES.md)  
**Umbrella:** [../nimblelims-prd.md](../nimblelims-prd.md)  
**Leadership reviews:** [lab-ops](../../../review/lab-ops-review/atomic-receive.md) · [ceo](../../../review/ceo-review/atomic-receive.md) · [team rollup](../../../discussions/2026-08-26-ar-core-leadership-team-review.md)  
**Gate memo:** [../../../discussions/2026-08-26-ar-core-plan-leadership.md](../../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**Discussions:** [../../../discussions/2026-08-25-framework-driven-lims-accessioning.md](../../../discussions/2026-08-25-framework-driven-lims-accessioning.md) · [../../../discussions/2026-08-25-work-orders-assay-params-compounds.md](../../../discussions/2026-08-25-work-orders-assay-params-compounds.md)  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Design SoT:** `.docs/review/tech-sketch/atomic-receive.md`  
**Team:** Leadership  

---

## 0. Framework posture (Leadership)

```text
RECEIVE (this domain)     → identity + 1..N vessels (same sample, one txn)
ORDER / ASKED-FOR         → analysis, TAT, params (not intake’s job to complete work)
ROUTING → WORK_ORDER      → process chain (processing domain)
EXECUTE                   → Process / Experiment / LimsRun
RESULTS                   → follow-on slice (not CORE acceptance)
```

| Stamp | Application here |
|-------|------------------|
| FW-0 | Fixed identity/AuthZ spine; intake **profiles** are configurable joints |
| FW-1 | **OOB = atomic receive only**; labs configure own intake configs; sidebar = active configs |
| FW-1b | Activate sidebar configs = **`config:edit` only** |
| FW-2 | Intake profiles ≠ Workflow Templates |
| WO-* | Work orders / routing / Test timing are **not** solved inside accessioning |

**Leadership:** Do **not** center “assign analysis at receive” as the work model. Receive registers specimen + vessel(s). Work plan comes later via order + routing. Results-entry is **not** a CORE requirement.

**Implement gate:** **OPEN for AR CORE only** (Lab Ops + CEO Accept-with-conditions; identity + 1..N vessels + field align + docs/UAT with ship). Not profile engine, not work_order, not results-entry.

---

## 1. Problem

Labs share intake purpose but differ in method. The wizard tried multi-mode flexibility without DB profiles and failed. Multi-call create orphans samples without vessels. Atomic receive is the coherent **OOB default profile** — requirements below define CORE; the intake-profile engine is deferred.

## 2. Goals

### 2.1 Framework (narrative / later packets)

| ID | Goal |
|----|------|
| F1 | Intake configs stored in DB; admin-owned (`config:edit`) |
| F2 | Profile defines steps, fields, sticky set, identity rules, post-success UX |
| F3 | OOB default = atomic scan-receive — usable without prior config |
| F4 | Prefer one receive service parameterized by profile; AuthZ = sample create + project RLS |
| F5 | Future modes = new profiles after AR works — not unfinished wizard |
| F6 | Analysis/tests at receive are not the lab work plan (A-15 / work-orders) |

### 2.2 Atomic receive CORE (OOB / P0) — product goals

| ID | Goal |
|----|------|
| G1 | Barcode scan — no sample-ID field on this profile |
| G2 | One txn: sample + **1..N containers** + contents for each (+ optional asked-for analyses only if present) |
| G3 | System lab sample ID; each barcode = a container name (unique; 409 on any dup) |
| G4 | Sticky type / matrix / project |
| G5 | Prefer omit analysis assignment on default receive; if present = “asked for” only |
| G6 | Status → **Available for Testing** |
| G7 | UX: **one primary barcode** required + **optional additional barcodes** on the same commit (default tube type off-form) |

---

## 3. Requirements — AR CORE

Normative product requirements for the first implement slice. Spec owns contracts and acceptance tests. Issues A-5…A-18 track gaps until these land.

### 3.1 In scope (must)

| ID | Requirement | Maps |
|----|-------------|------|
| **RQ-AR-1** | System shall expose **one** receive commit: `POST /api/samples/receive` plus a **new receive UI loop** (not the wizard forever). | A-5 |
| **RQ-AR-2** | Receive shall create Sample + **1..N Containers** + Contents for each in a **single DB transaction**. Partial commit is forbidden. | A-6, A-18 |
| **RQ-AR-3** | Tech shall supply a **primary barcode** (required) and may supply **additional barcodes** (0..N) for the same sample on that commit. | A-18, G7 |
| **RQ-AR-4** | Each barcode shall become `containers.name` exactly as scanned. Any duplicate (in request or DB) → **409** and full rollback. No timestamp-suffix barcode hacks. | A-6 |
| **RQ-AR-5** | `samples.name` shall be assigned by the **existing name template/sequence**. Receive UI shall have **no sample-ID field**. | A-9, G1, G3 |
| **RQ-AR-6** | On success, Sample.status shall be **Available for Testing** only; set `received_date`. No Received hop; no status picker. | A-7, G6 |
| **RQ-AR-7** | `project_id` shall be **required** and **sticky**. System shall **never** auto-create a project per tube. | A-8, G4 |
| **RQ-AR-8** | Container type shall be the **default tube**, applied to all vessels on the call, **off the form** (no type picker on the scan loop). | A-10 |
| **RQ-AR-9** | Receive body shall **omit** `due_date`, `qc_type`, and `client_id`. | A-11 |
| **RQ-AR-10** | Default UX shall **prefer omit** analysis assignment. If `analysis_ids` are present, they mean **asked-for only** (Assigned/Pending) — not the lab work plan. | A-13, G5 |
| **RQ-AR-11** | AuthZ shall be **identical to sample create** + **project RLS**. No separate receive permission, no client bypass, no second receive API, no orphan multi-call substitute. | AuthZ / PR 68 |
| **RQ-AR-12** | After success, UI shall **stay on receive**: toast, clear barcode field(s), keep sticky type/matrix/project, focus primary barcode. No sample-detail redirect; no aliquot dialog. | G4, G7 |
| **RQ-AR-13** | With ship: receive happy-path UAT is `uat-atomic-receive.md`; wizard UAT is demoted as receive SoT; docs paths use `.docs/review/` + `.docs/internal/`. | A-16, A-17 |

### 3.2 Out of scope (not CORE requirements)

| ID | Non-requirement | Notes |
|----|-----------------|-------|
| **NR-AR-1** | Results entry (`POST /tests/{id}/results`) / AR-RES as CORE must-pass | Design persist lock remains for a **follow-on** slice |
| **NR-AR-2** | Aliquot UI / derivative sample mint | Later process |
| **NR-AR-3** | Intake-profile engine / modes / manifest / bulk-as-mode (A-1–A-4) | After AR CORE |
| **NR-AR-4** | FieldDefinitions on default receive body (A-12) | Extensibility later |
| **NR-AR-5** | Work orders / routing / A-15 / Process·Exp·LimsRun | Processing domain |
| **NR-AR-6** | Wizard revival as framework | Bounce |
| **NR-AR-7** | Sidebar multi-config activate shell (FW-1b UX) | Needs profile engine |

**Light ride (optional with CORE, not a reason to expand scope):** A-14 legacy DELETE-with-results → 400 if touching the same test path.

### 3.3 Bounce conditions (fails requirements gate)

Any of these fails Leadership / product acceptance of CORE:

1. Multi-call create left as the supported receive story  
2. Single-vessel-only API/UI (no additional barcodes)  
3. Sample-ID field, user-typed `samples.name`, or barcode = sample name (C1)  
4. Status = Received (or any hop) before Available for Testing; status picker  
5. Project auto-create / optional project  
6. Container type picker on the scan loop  
7. Analysis presented or accepted as “what’s next” / work plan  
8. `work_order`, routing, Process/Exp/LimsRun, or aliquot UI in the AR PR  
9. Intake-profile engine or second receive API/permission  
10. Results-entry treated as CORE ship blocker  
11. New tables, `results.unit_id`, or `status_history`  
12. Client can receive / foreign-project write succeeds (AuthZ regression)  
13. Partial commit on any barcode collision  
14. Wizard kept as the forever receive path  

---

## 4. Non-goals (domain)

- Work orders / process routing (processing)  
- Solving A-15 inside intake  
- Intake-profile engine in the same code slice as AR CORE  
- Wizard revival as “framework”  
- Compound registration uniqueness (WO-5 deferred)  
- Results-entry / review ceremony as CORE acceptance  

## 5. Default path locks

| Aspect | Lock |
|--------|------|
| Commit | One POST / one DB txn |
| Vessels | **1..N** containers; primary + optional additional barcodes; Contents → same sample |
| Project | Sticky + required; no auto-create |
| AuthZ | Sample create + project RLS (PR 68) |
| Product code | **Provisional open for AR CORE** — Leadership 2026-08-26; results / profile / work_order still gated |

## 6. Acceptance criteria (product)

Trace to SPEC §AC for testable detail.

| ID | Criterion |
|----|-----------|
| **AC-AR-1** | Lab tech can receive with primary barcode only → Sample + 1 Container + Contents; status Available for Testing; stay on form |
| **AC-AR-2** | Lab tech can receive with primary + ≥1 additional barcodes → Sample + N Containers + Contents; one txn |
| **AC-AR-3** | Duplicate barcode (any vessel) → 409; zero rows from that attempt |
| **AC-AR-4** | Receive UI has no sample-ID field; `samples.name` ≠ barcode unless template happens to match |
| **AC-AR-5** | Project sticky + required; client role cannot receive; foreign project denied |
| **AC-AR-6** | Default path works with empty `analysis_ids`; optional asked-for tests land Assigned/Pending only |
| **AC-AR-7** | Tube type not on form; no status picker; no aliquot dialog; no detail redirect |
| **AC-AR-8** | UAT happy path uses atomic-receive script after ship |

**Framework (docs-level, not CORE code):** AF1–AF4 — profiles described; OOB = AR; future modes as profiles; activate = `config:edit`.

## 7. Shipped vs target

| Piece | Status |
|-------|--------|
| Wizard | Unfinished mode shell — not framework |
| Legacy `/accession` + multi-call | Shipped legacy (not CORE happy path) |
| AR docs + AuthZ Accept | Signed |
| `POST /samples/receive` + UI | **Not implemented** — CORE requirements open |
| Results-entry | Design lock; **follow-on** requirements later |
| Intake-profile engine | Narrative; packet later |

## 8. References

- Spec: [../../specs/sample-accessioning/SPEC.md](../../specs/sample-accessioning/SPEC.md)  
- Issues: [ISSUES.md](ISSUES.md)  
- Leadership gate: [../../../discussions/2026-08-26-ar-core-plan-leadership.md](../../../discussions/2026-08-26-ar-core-plan-leadership.md)  
- Tech sketch: `.docs/review/tech-sketch/atomic-receive.md`  
- Security: `.docs/review/security-review/atomic-receive.md`  
