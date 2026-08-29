# QA Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Reviewer persona:** Testing / QA Lead (Tobias)  
**Packet:**  
- Requirements: [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
- Tech sketch: [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
- Schema: [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
- PRD: [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
- Spec: [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
- Open questions: [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Related reviews:** [Lab Ops Accept with conditions (L1–L5)](../lab-ops-review/post-receive-work-spine.md). CEO / UI / Arch / Security / Sci CSO / BA not present at this stamp.  
**UAT script (create at implement):** [`UAT_Scripts/uat-post-receive-work-spine.md`](../../UAT_Scripts/uat-post-receive-work-spine.md)  
**Retired:** [`UAT_Scripts/uat-sample-accessioning.md`](../../UAT_Scripts/uat-sample-accessioning.md) — wizard gone; do not run. Receive SoT remains [`uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md).

---

## 1. Executive summary

This packet is **required QA** (test ordering + sample lifecycle + RLS + results path later). P1 is the **lake**: after CORE receive (identity + 1..N vessels, **zero Tests**), a tech records what was asked. That is test-ordering in the framework sense. It is **not** a Test row (WO-7).

**P1 is testable.** Product ACs AC-P1-1 / AC-P1-2 / AC-P1-3 map 1:1 to happy path, duplicate **409**, and RLS **403**. Lab Ops **L1** (copy, zero mint, multi-sample, not `/receive`) is the UAT shape. Sketch §3.4 already names the pytest gate. OQ-AF-1…3 are **Decided (provisional)** — P1 is unblocked.

**Gaps that would fail UAT if left implicit** (conditions, not a Revise):

1. **L1 multi-sample failure mode** is unspecified. One operator action must write one row per sample; mixed 409/403 in the set must not silent-skip and toast success.
2. **403 vs 404** for RLS-hidden samples must be **403** (SPEC). Receive UAT saw **404** on hidden projects (AR-MU-01). Do not copy that leak into asked-for.
3. Product ACs do not list **422** / **cancel** / **copy** / **receive freeze**. Those are in RQ-AF-* and bounce; they **must** be P1 must-pass UAT, not “nice pytest.”
4. **Classic Tests / TestForm** still mints Tests. P1 UAT happy path is **Asked-for**, never TestForm, never the retired wizard.

**P2–P5 are not this PR.** Later scenarios inherit zero-acceptable Route 422, route ambiguity 409, ordered process starts, WO-7, persist lock, and SOP Apply ≠ dest-type. Do not invent Qubit/blood testdata IDs.

QA review is **not** a substitute for the post-implement UAT pass.

---

## 2. Testability & coverage assessment

| Dimension | Notes |
|-----------|--------|
| **Testability** | AC-P1-1…3 are concrete (status codes, zero Tests, zero work_orders). RQ-AF-4/6/7/10 and L1 are equally concrete once multi-sample failure and 403-not-404 are locked (QA3, QA5). P2 AC-P2-3 is untestable until type-eligibility config exists — Lab Ops L2; not a P1 blocker. P3 AC-P3-1 waits OQ-RES-1 (qualifiers shape). |
| **Sample lifecycle** | Receive (shipped) → Available for Testing, zero Tests → **asked-for `requested`** (this phase) → routing/WO (P2) → Process/LimsRun → Test at LimsRun start (WO-7) → results (P3). P1 must not skip ahead. Sample.status stays **Available for Testing**. Second analysis on the same sample is allowed (unique is `(sample_id, analysis_id)`, not one row per sample). |
| **Core flows** | Accessioning covered by existing AR UAT (regression AF-REC-01). Test ordering *request* is this packet. Results, execute, parsers **out of P1 UAT**. |
| **Negative paths** | 409 duplicate open pair; 403 RLS / missing `test:assign` / client write; 422 TAT, params, inactive analysis, non-AFT status; receive non-empty `analysis_ids` still 422. Concurrent duplicate → one 201, one 409. Cancel then re-create allowed. |
| **UAT readiness** | Lab-tech (`alice-tech`) happy path + multi-sample; `bob-tech` foreign-project 403; `david-cro` client cannot create; admin/`config:edit` for param-def 422 fixture. Reuse 0058 ELISA + AR receive actors. New barcodes `NBIO-AF-*` so we do not collide with AR-HV. |
| **Docs & Cursor** | Implement **must** create `UAT_Scripts/uat-post-receive-work-spine.md` (QA11) and update manuals listed there. Wizard UAT stays retired. |
| **Traceability** | Suggested cases AF-* map to AC-P1-*, RQ-AF-*, L1, bounce list. Pytest AF-T1 maps to sketch §3.4. |
| **Results integrity** | **Out of P1.** Do not enter results on asked-for. AR-RES remains follow-on / P3. |
| **Security / RBAC / RLS** | `test:assign` + sample→project RLS. Client read-only. `config:edit` for param defs, not `test:assign`. FORCE RLS on `asked_for`. Hidden sample → **403**, not 404. |

**P1 AC → case map**

| AC | Must-pass case | Expected |
|----|----------------|----------|
| AC-P1-1 | AF-HV-01 | Receive → ELISA asked-for `requested`; **zero Tests**; **zero work_orders** (table absent or count 0) |
| AC-P1-2 | AF-DUP-01 | Second open `(sample, analysis)` → **409**; still one row; still zero Tests |
| AC-P1-3 | AF-RBAC-01 | No project access → **403**; no row |

---

## 3. Conditions (must land with the named phase)

P1 conditions **QA1–QA12** land with the P1 PR. QA13–QA15 bind later PRs; they do **not** block P1 coding.

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **QA1** | **P1** | **Zero mint.** Saving asked-for creates **zero** Tests, Results, Processes, Experiments, LimsRuns, and work_orders. Response has **no** `tests` array implying work started. Do **not** call `_create_tests` / `_create_asked_for_tests`. Sample.status remains **Available for Testing**. | AC-P1-1, RQ-AF-2, WO-7, L1. If this page mints Tests, the packet is a rename of TestForm. |
| **QA2** | **P1** | **Happy path (AC-P1-1).** After CORE receive of a plasma on mAb-2301, `alice-tech` records ELISA (Human IgG) (`analysis-elisa-001`), `tat_days=5`, `params={}`. Row `status=requested`. GET tests for that `sample_id` count **0**. Work_orders count **0** (or table does not exist yet). | Product AC. Empty params is OQ-AF-3. |
| **QA3** | **P1** | **L1 multi-sample.** One operator action (same analysis + TAT + params) on a **set** of ≥2 received samples writes **one asked-for row per sample**, all `requested`, still zero Tests. API may stay one row per sample (N POSTs or `sample_ids[]`). **No silent skip:** if any sample would 409/403/422, do not toast full success. Prefer one transaction (all succeed or none). If N POSTs, UI shows which samples failed. Mixed-set UAT is a must-pass. | L1. One-by-one per tube fails a rack. Partial rack order is a mix-up. |
| **QA4** | **P1** | **409 duplicate (AC-P1-2).** Second **open** asked-for for the same `(sample_id, analysis_id)` → **409**. Partial unique index is the race gate: concurrent POSTs → one **201**, one **409**, exactly one open row. Different `analysis_id` on the same sample → **201** (second request). | RQ-AF-4. Unique is the pair, not one analysis per sample. |
| **QA5** | **P1** | **403 AuthZ/RLS (AC-P1-3).** (a) User without project access (`bob-tech` on alice’s sample) → **403**, **not 404**, no row. (b) Missing `test:assign` → **403**. (c) Client (`david-cro` / `client`) cannot POST or cancel; no create CTA. Client **may** GET rows they can `sample:read`. `config:edit` is **not** required to create asked-for and **cannot** be used as a substitute for `test:assign`. RLS-hidden ids do not leak existence via 404. | SPEC errors table. Receive AR-MU-01 returned 404 — do not copy. RQ-AF-7/8. Bounce #8. |
| **QA6** | **P1** | **422 validation.** `tat_days` missing or `< 1` → 422. Unknown param key → 422. Required def missing → 422. Inactive analysis → 422. Sample.status **not** Available for Testing (e.g. Testing Complete) → 422. With **zero** param defs, only `params={}` is legal; any key → 422. Empty `{}` is 201. Param-def **write** is `config:edit` only. | RQ-AF-6, sketch §3.2. OOB may have zero defs — fixture the unknown-key case in pytest if no seed def. |
| **QA7** | **P1** | **Receive freeze + surface.** UI is **`/asked-for`** plus a section on sample detail. **Not** `/receive`. Receive UI has **no** analysis picker and never sends `analysis_ids`. Non-empty `analysis_ids` on receive still **422** before the txn (AF-REC-01). `/accessioning` still redirects to `/receive`. **Do not** run retired `uat-sample-accessioning.md`. Analysis dropdown on Asked-for is **not** TestForm. | RQ-AF-3, bounce #1, L1, OQ-AF-1. |
| **QA8** | **P1** | **Lake copy (L1) + cancel.** Visible copy: “Asked-for” / “requested analysis.” Never “assign test,” “create test,” “start work,” or “order process.” **No Start / Execute CTA** on a `requested` row. Cancel while `requested` succeeds; row `cancelled`; unique ignores it; re-create same pair → **201**. Cancel of already-cancelled → 422 (or documented idempotent 200 with still-cancelled — pick one and UAT it). Routed cancel is **P2**, not this PR. | L1, RQ-AF-5/10. |
| **QA9** | **P1** | **Lists + nav.** GET `/asked-for` filters `sample_id`, `project_id`, `analysis_id`, `status=requested`. RLS: alice does not see bob’s project rows. Sidebar **Sample Mgmt**: **Asked-for** immediately **after Receive**. Accordion auto-expands on `/asked-for`. Client has no create control. | RQ-AF-9, sketch §3.3. |
| **QA10** | **P1** | **Pytest gate (sketch §3.4) before merge to the feature branch’s CI.** Minimum: create 201 + zero Tests; 409 dup; 403 RLS (hidden sample); 422 params + TAT; receive non-empty `analysis_ids` still 422 and zero rows; cancel + re-create; concurrent unique; second analysis on same sample 201. FORCE RLS on `asked_for`. Audit: `created_by` / `modified_by` set; cancel updates `modified_*`. | Sketch §3.4. Human UAT does not replace this. |
| **QA11** | **P1** | **Docs + UAT at implement (Cursor must-include).** Create [`UAT_Scripts/uat-post-receive-work-spine.md`](../../UAT_Scripts/uat-post-receive-work-spine.md) with P1 must-pass AF-* cases below. Update manuals: [accessioning-workflow.md](../manuals/accessioning-workflow.md), [workflow-accessioning-to-reporting.md](../manuals/workflow-accessioning-to-reporting.md), [navigation.md](../manuals/navigation.md), [api-endpoints.md](../manuals/api-endpoints.md), [atomic-receive.md](../manuals/atomic-receive.md) (pointer: asked-for is this packet, not receive). Header-note [`uat-test-ordering.md`](../../UAT_Scripts/uat-test-ordering.md): request path is Asked-for; wizard cases stay retired; classic TestForm is **not** the P1 happy path (WO-4 type-a-number remains for later). Do **not** use `uat-sample-accessioning.md`. | Process docs + UAT gate. |
| **QA12** | **P1** | **Fixtures.** Do **not** invent Qubit / whole-blood / DNA-daughter testdata IDs. Use 0058 ELISA (`analysis-elisa-001`) + CORE receive. New barcodes `NBIO-AF-*` (do not reuse consumed `NBIO-AR-*`). Actors: `alice-tech` / `alice123` (mAb-2301); `bob-tech` / `bob123` (CAR-T, 403); `david-cro` / `david123` (client). Optional qPCR (`analysis-qpcr-001`) for second-analysis case. Param defs: empty OOB unless a documented ELISA `cell_line` seed lands — then UAT says so. | Extract-then-qubit testdata Hold. AR barcode collision. |
| **QA13** | **P2** | Map row = analysis + TAT + ordered `process_definition[]`; no type picker. Assert UI order, first-process / first-step derived display, zero acceptable → 422, two acceptable → 409, no `first()`, first-process-only Start, later-start advancement and type gates, no later chain-AND. Preserve signed `b005cfe` chain-AND as history. First-start freeze remains OPEN. | Marc/Rolf superseding lock. |
| **QA14** | **P3** | **Hold UAT until OQ-RES-1.** Then fold AR-RES-01/02: typed number → `reported_result` + `qualifiers`; missing `units_default` → 422, no row; two writers **409**; **no** `results.unit_id`; **no** results column on asked-for. | OQ-RES-1 Open. Lab Ops: persist lock, not a results product. |
| **QA15** | **P4 / P5** | P4: Apply → process definition with ≥1 typed step; human save; never silent auto-activate; **L5** — success copy / UAT must **not** claim NCI extract → DNA daughter → Qubit is runnable; no SOP PDFs in git. P5: dry-run pass then activate; production import with LLM disabled; `config:edit` mutate; client cannot write parsers. | L5, RQ-SOP-*, RQ-IMP-*, bounce #6–8. |

Already normative (restated so implementers do not drop them): empty routing map mints nothing; client cannot write asked-for / routing / parsers; P1 does not call routing; uniqueness ignores `cancelled`.

---

## 4. Suggested UAT scenarios (high level)

**Script (at implement):** `UAT_Scripts/uat-post-receive-work-spine.md`. P1 cases first. Follow the UAT template in [`.docs/review/development-process/uat/README.md`](../development-process/uat/README.md).

**P1 must-pass**

| ID | Persona | Steps | Expected | Traces |
|----|---------|-------|----------|--------|
| **AF-HV-01** | `alice-tech` | Receive a new `NBIO-AF-0001` plasma on mAb-2301 (CORE `/receive`). Open **Asked-for** (`/asked-for`). Select that sample. Analysis ELISA (Human IgG). TAT 5. Params empty. Save. | Row `requested`. Sample still **Available for Testing**. **Zero Tests**, **zero Results**, **zero work_orders**. No Start/Execute. Copy is asked-for / requested analysis. Stay on asked-for or show the new row — **not** redirected to Tests or a process. | AC-P1-1, QA1, QA2, QA8 |
| **AF-HV-L1** | `alice-tech` | Receive `NBIO-AF-0002` and `NBIO-AF-0003`. On `/asked-for`, multi-select both. Same ELISA / TAT 5 / `{}`. **One** Save. | Two asked-for rows (one per sample), both `requested`. Zero Tests on both. | L1, QA3 |
| **AF-HV-L1b** | `alice-tech` | In a set of 2, one sample already has open ELISA asked-for. Save the set. | Not a silent full success. Either all-or-nothing (zero new rows, 409) **or** UI names the failed sample. No extra Test. | QA3, QA4 |
| **AF-HV-02** | `alice-tech` | On the AF-HV-01 sample, record **qPCR** (different analysis). | **201**, second `requested` row. ELISA row still open. Still zero Tests. | QA4 (pair uniqueness) |
| **AF-DUP-01** | `alice-tech` | Repeat ELISA on AF-HV-01 sample. | **409**. Still one open ELISA row. Zero Tests. | AC-P1-2, QA4 |
| **AF-CXL-01** | `alice-tech` | Cancel the AF-HV-01 ELISA. Confirm `cancelled`. Record ELISA again. | Cancel ok. Re-create **201** `requested`. Still zero Tests. | QA8, RQ-AF-10 |
| **AF-VAL-01** | `alice-tech` | TAT `0` or omitted; `params` with a bogus key against empty defs. | Each → **422**. No row. | QA6 |
| **AF-ST-01** | `alice-tech` | PATCH AF-HV-02 sample (or a spare) to **Testing Complete**. POST asked-for. | **422**. No row. | QA6 |
| **AF-RBAC-01** | `bob-tech` | POST asked-for for alice’s sample / project. | **403** (not 404). No row. | AC-P1-3, QA5 |
| **AF-RBAC-02** | `david-cro` | Open `/asked-for` or POST create/cancel on a readable sample if any. | No create CTA, or **403**. GET may list own-project rows only. | QA5, bounce #8 |
| **AF-REC-01** | `alice-tech` | Inspect `/receive` (no analysis picker). POST receive with non-empty `analysis_ids`. | **422**. No sample/container/Test. `/asked-for` is a **separate** nav item after Receive. `/accessioning` redirects. | QA7, bounce #1 |
| **AF-COPY-01** | `alice-tech` | Inspect `/asked-for` and sample-detail Asked-for section on a `requested` row. | No “assign/create test,” “start work,” “order process.” No Start/Execute. Not TestForm. | L1, QA8 |
| **AF-LST-01** | `alice-tech` | List: by this sample; by mAb-2301; by ELISA; `status=requested`. Then as bob. | Alice filters work. Bob does not see alice’s rows. | QA9 |

**P1 automated only (pytest, not a human case)**

| ID | Expected |
|----|----------|
| **AF-T1** | Sketch §3.4 + QA10: 201/409/403/422, zero Tests, receive freeze, cancel+recreate, concurrent unique, audit fields, FORCE RLS |

**Follow-on (not P1 must-pass)**

| ID | Phase | Notes |
|----|-------|--------|
| AF-WO-* | P2 | Ordered `process_definition[]`; no type picker; zero acceptable 422; multiple 409; first process starts first; later starts advance/gate; first-start freeze OPEN; publish missing-Test 422 |
| AF-RES-* | P3 | Fold AR-RES-01/02 after OQ-RES-1. Not on asked-for. |
| AF-SOP-* / AF-IMP-* | P4/P5 | Apply process def; L5 no dest-type E2E; parser dry-run + activate; no LLM on import |

### Out of this packet (do not fail P1 UAT on)

- Work_order / routing map / Route button (OQ-WO-1 Open)
- Qubit-on-blood, extract-hold dest type, blood → DNA → Qubit E2E, Qubit/blood testdata IDs
- Results entry / `qualifiers` shape / `results.unit_id`
- SOP Apply / parser setup / LLM draft
- Hiding classic TestForm (muscle memory; WO-4 stays; not a P1 fail)
- STAT `tat_days=0` (check is `> 0`; Lab Ops watch item, not a P1 change)
- Uniqueness including param identity (Lab Ops watch; empty-params P1 is fine)
- Wizard `/accessioning` happy path (`uat-sample-accessioning.md` **retired**)
- Minting Tests at asked-for or WO save

### Personas

| Persona | Login | Focus |
|---------|-------|--------|
| Lab tech | `alice-tech` / `alice123` | Receive + asked-for lake, multi-sample, cancel |
| Lab tech (foreign project) | `bob-tech` / `bob123` | 403 |
| CRO client | `david-cro` / `david123` | No create; read-only if project access |
| Admin | `admin` / `admin123` | `config:edit` param defs (pytest/UAT fixture only) |

Classic `lab-tech` / `client` logins are acceptable extras; **0058 actors are the SoT** so RLS cases match AR.

---

## 5. Docs & Cursor readiness (implement prompt must include)

1. Create **`UAT_Scripts/uat-post-receive-work-spine.md`** with P1 must-pass AF-* (QA11). Do not revive wizard UAT.
2. Manuals: navigation (Asked-for after Receive), accessioning-workflow + workflow (after receive → asked-for, still zero Tests), api-endpoints (`POST/GET /asked-for`, cancel, param-defs), atomic-receive (A-15 unparked **as this packet**, not as receive).
3. Pytest per QA10 / sketch §3.4.
4. Honor **QA1–QA12** and Lab Ops **L1**. Do not implement P2–P5 in the P1 PR.
5. Awareness: classic Tests page still exists; P1 UAT does not use it as the request path.

---

## 6. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (QA1–QA12 for P1; QA13–QA15 recorded for later phases) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** (matches Lab Ops). P2 closed until OQ-WO-1/3 Decided and L2–L4 stay in the sketch. P3 Hold on OQ-RES-1. P4/P5 not this PR. |
| **UAT pass** | Still required after implement, before merge to `main`. Source: new `uat-post-receive-work-spine.md` P1 must-pass. Not a substitute: this review. |
| **Not licensed** | Extract-hold dest type · blood → DNA → Qubit E2E · minting Tests at asked-for · results on asked-for · wizard UAT |

```
QA REVIEW: Accept with conditions
IMPLEMENT GATE: OPEN (P1 only)
```
