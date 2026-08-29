# Documentarian Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Reviewer persona:** Documentarian  
**Packet:**  
- Requirements: [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
- Tech sketch: [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
- Schema: [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
- PRD: [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
- Spec: [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
- Open questions: [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
- Checklist: [`.docs/review/checklist/post-receive-work-spine.md`](../checklist/post-receive-work-spine.md)  
**Related reviews:**  
- Lab Ops: [`.docs/review/lab-ops-review/post-receive-work-spine.md`](../lab-ops-review/post-receive-work-spine.md) — **Accept with conditions (L1–L5)**; implement gate **OPEN for P1 only**  
- CEO / UI / Architecture / Security / Scientific CSO / BA / QA / Developer — **not written** for this stem  
**Depends on (shipped):** atomic receive CORE; wizard removed (PR 75)  
**Stamps:** WO-1…WO-7, FW-0/FW-2; this packet **opens X-5**. It does **not** reopen CORE receive.

---

## 1. Executive summary

The spine packet is **documentable**. Core product docs exist (requirements, tech sketch, schema, PRD, SPEC, living OQ log). Lab Ops has spoken. P1 asked-for is the lake: record analysis + TAT + params after receive, **zero Tests**, UI **not** `/receive`. Wizard stays gone.

**P1 docs are ready to attach to a Cursor implement prompt if the DOC list below lands in the same PR.** That prompt is **mandatory docs + UAT + README** — not optional polish.

This stamp does **not** open product implement by itself. QA is **required** (test ordering / sample tracking / RLS). Architecture is **required** (new tables + RLS). Security should speak (AuthZ + RLS + client deny). Those artifacts are missing today. Documentarian does not invent them.

**Do not document P2–P5 as shipped in the P1 PR.** Routing, work_order, results persist, SOP Apply, parser setup stay specified-for-review. OQ-WO-1/3, OQ-RES-1, OQ-SOP-2 still **Open** and block those phases.

Living manuals are the real gap. After CORE:

| Doc | Today | Hurt if P1 ships without a sync |
|-----|--------|----------------------------------|
| [`atomic-receive.md`](../manuals/atomic-receive.md) | “A-15 parked; add tests via Tests workflow” | Techs will mint Tests on `/tests` and reopen WO-7 |
| [`accessioning-workflow.md`](../manuals/accessioning-workflow.md) | 12-line stub: work assignment is a later packet | No operator SoT for `/asked-for` |
| [`navigation.md`](../manuals/navigation.md) | Sample Mgmt has no Asked-for; still lists `AccessioningForm` as a live route | Sidebar/UAT will lie; wizard looks alive |
| Root `README.md` / `frontend/README.md` | “order tests (assign analyses)”; work assignment = Tests page | MVP copy collides with asked-for ≠ Test |
| `UAT_Scripts/uat-post-receive-work-spine.md` | **Missing** (create at implement, per requirements §8) | No merge gate |
| `uat-test-ordering.md` | “asked-for packet is still future”; wizard cases retired but still in the file | Dual order path |

**Verdict: Accept with conditions (DOC1–DOC9).** P1 Cursor hand-off may proceed **with this list in the implement prompt**, once Lab Ops (already open) and the required parallel reviews Accept / Accept-with-conditions. P2–P5 docs are listed in §4.2 and **must not** land as live manuals in the P1 PR.

---

## 2. Documentation quality assessment

| Dimension | Notes |
|-----------|--------|
| **Completeness** | **Core packet present:** requirements, sketch, schema, PRD, SPEC, OQs, checklist, Lab Ops. **Missing formal reviews** for this stem: CEO, UI, Architecture, Security, Scientific CSO, BA, QA, Developer (this file is the first docs-review). UAT script **correctly deferred** to implement (requirements §8). No operator manual for asked-for yet. Schema omits template sections **Data migration / backfill**, **Rollback**, **Open schema blockers**, **Implementation checklist**. |
| **Consistency** | Spine naming is coherent: asked-for ≠ Test ≠ work_order ≠ Process. L1 copy is in requirements, sketch, Lab Ops. **Drifts:** SPEC POST is single `sample_id` while RQ-AF-1 / L1 require one operator action on a **set** (API may stay one row per sample — **not written as a contract**). Schema lists **both** `work_orders.process_id` and `eln_processes.work_order_id` while OQ-WO-3 is **Open** (P2). RQ-WO-6 implies auto-route on save; OQ-WO-1 still **Open**. Framework stamps WO-7 bullet still says “TAT matching algorithm still open” while OQ-TAT-1 is **Decided (provisional)** refuse. Requirements **Status: Draft for formal review** after Lab Ops has already accepted P1. Checklist review boxes all empty (Lab Ops is done). Internal US-1 / US-7 / US-23 still mint Tests at accessioning. |
| **Cross-references** | Requirements ↔ sketch ↔ schema ↔ PRD ↔ SPEC ↔ OQs ↔ Lab Ops are linked. Open-questions index already lists this stem. `.docs/review/README.md` does not name `docs-review/`. Atomic-receive manuals/UAT still say A-15 is **parked** rather than “opened by `post-receive-work-spine` P1 (not on `/receive`)”. |
| **Living-doc hygiene** | OQ statuses and phase gate rule are correct: **P1 unblocked**; P2 blocked on OQ-WO-1/3; P3 on OQ-RES-1; P4 on OQ-SOP-2. Dest-type Hold stays on the extract-hold packet — do not fold it here. Checklist is a task list, not an OQ owner — good. Wizard-removed (PR 75) is already stamped on `uat-sample-accessioning.md` (retired) and the accessioning stub; **navigation.md was not fully cut over**. |
| **Review-artifact quality** | Lab Ops follows PACKET header + L* conditions + phase gate. This docs-review follows the Documentarian template. Other reviews: n/a until written. |
| **Cursor hand-off readiness** | **Yes with conditions, P1 only.** Implement prompt **must** include DOC1–DOC9 (docs + UAT + README). One phase per PR. Do not code P2–P5 in the P1 PR. Product implement still waits on required reviews (QA, Architecture, Security at minimum). |
| **Discoverability** | Stem is consistent (`post-receive-work-spine`). Findable from OQ index, requirements, Lab Ops. New `docs-review/` folder needs an index line. No `asked-for.md` manual yet — operators will not find the lake. |

### Locked for documentation (do not reopen)

- Receive stays dumb. No analysis picker. Non-empty `analysis_ids` → **422**. Zero Tests at receive.
- Wizard remains **removed** (PR 75). `/accessioning` redirects to `/receive`. Do not revive wizard UAT or manuals as live.
- Asked-for copy: “asked-for” / “requested analysis.” Never “assign test,” “create test,” “start work,” or “order process.” No Start/Execute on `requested`.
- Asked-for creates **zero** Tests, Results, Processes, Experiments, LimsRuns, work_orders.
- Test row at **LimsRun start** only (WO-7). P1 does not mint Tests.
- Do not UAT or manual blood → DNA daughter → Qubit (dest-type Hold; L5). Do not invent Qubit/blood testdata IDs.
- `uat-sample-accessioning.md` stays **retired**. Do not run it. Do not extend it.

---

## 3. Conditions (must land with implement)

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **DOC1** | **P1** | **Create** `UAT_Scripts/uat-post-receive-work-spine.md` in the P1 implement PR (not a prior docs-only PR). Header: stem, phase P1, links to requirements + Lab Ops L1 + this review. **Must-pass P1 cases** mapped to AC-P1-1 / AC-P1-2 / AC-P1-3 plus L1: receive → record ELISA asked-for for **one sample and a set** (same analysis + TAT + params) → **zero Tests, zero work_orders, no Start/Execute**; duplicate `(sample, analysis)` → **409**; no project access / missing `test:assign` / client create → **403**; receive still **422** on non-empty `analysis_ids`; copy never says assign/create test. Seed: existing 0058/0060 + ELISA; **do not** invent Qubit/blood IDs. **Out of P1 UAT:** routing, work_orders, results entry, SOP Apply, dest-type E2E. Do **not** use retired `uat-sample-accessioning.md`. | Full-pipeline merge gate. Requirements §8. QA process: `uat-{stem}.md`. |
| **DOC2** | **P1** | **Manuals (mandatory):** (1) New operator SoT [`.docs/review/manuals/asked-for.md`](../manuals/asked-for.md): who (`test:assign` + project access; client read-only), UI `/asked-for` + sample-detail section, **not** `/receive`, multi-sample one action, statuses `requested`/`cancelled` in P1 (`routed` is P2), cancel while requested, 409/403/422, **zero Tests**. (2) Update [`atomic-receive.md`](../manuals/atomic-receive.md): after-receive pointer is **Asked-for**, not “Tests workflow / A-15 parked.” Keep CORE freeze. (3) Update [`accessioning-workflow.md`](../manuals/accessioning-workflow.md) stub: wizard still removed; work assignment **P1 = asked-for lake**; classic `/tests` is **not** the order path (WO-4 type-a-number on an existing Test only). (4) Update [`navigation.md`](../manuals/navigation.md): Sample Mgmt item **Asked-for** after Receive; route `/asked-for`; AppBar title; accordion auto-expand; permission create=`test:assign`, view=`sample:read`; client cannot create. **Delete live `AccessioningForm` / “Accessioning” happy-path** — `/accessioning` is redirect-only. (5) Update [`workflow-accessioning-to-reporting.md`](../manuals/workflow-accessioning-to-reporting.md) Stage after receive = asked-for lake (zero Tests). | Named manuals are the operator path. Navigation still documents the removed wizard as a live route. |
| **DOC3** | **P1** | **README + API.** Root [`README.md`](../../../README.md): MVP “order tests (assign analyses)” must distinguish **asked-for (request)** from **Test (WO-7 at LimsRun start)**. Link `asked-for.md` + `uat-post-receive-work-spine.md`. [`frontend/README.md`](../../../frontend/README.md): replace “Work assignment is after receive (Tests page until order / work-order packets)” with Asked-for (`/asked-for`). [`api-endpoints.md`](../manuals/api-endpoints.md): P1 routes from SPEC (`POST/GET /api/v1/asked-for`, cancel, param-defs). 201 has no `tests`; 409 dup; 403 RLS/perm; 422 params/TAT; hidden sample **403** not 404. | Cursor hand-off requires README. API index is how agents find contracts. |
| **DOC4** | **P1** | **Pointer hygiene on existing UAT.** [`uat-atomic-receive.md`](../../../UAT_Scripts/uat-atomic-receive.md) + [`atomic-receive/README.md`](../../../UAT_Scripts/atomic-receive/README.md) + [`scenarios.md`](../../../UAT_Scripts/atomic-receive/scenarios.md): A-15 is **this packet (P1 asked-for)**, still **not on receive**; CORE remains zero Tests. [`uat-test-ordering.md`](../../../UAT_Scripts/uat-test-ordering.md): banner that the **order path is** `uat-post-receive-work-spine.md` / `/asked-for`; TestForm is **not** asked-for; do **not** un-retire wizard cases. [`uat-testing-log.md`](../../../UAT_Scripts/uat-testing-log.md): insert `uat-post-receive-work-spine` after `uat-atomic-receive` (depends on receive + analyses). [`uat-navigation-ui.md`](../../../UAT_Scripts/uat-navigation-ui.md): Asked-for after Receive; `/accessioning` is not a sidebar item. | Otherwise three scripts still teach “assign tests from TestForm / A-15 parked.” |
| **DOC5** | **P1** | **L1 terminology lock in every user-facing string this PR touches** (manuals, UAT, README, help if a help row is added, UI copy). Allowed: Asked-for, requested analysis, record request, cancel request. **Forbidden:** assign test, create test, start work, order process, Start/Execute on `requested`. Sidebar label **Asked-for** (not Tests, not Orders, not Projects). | If docs say Tests, WO-7 dies on arrival (Lab Ops L1). |
| **DOC6** | **P1** | **SPEC + schema close-out in the P1 PR.** SPEC: document multi-sample as **UI one action → N `POST /asked-for` rows** (or a `sample_ids[]` body if the API changes — pick one, write it, match pytest). P1 does **not** write work_orders. Schema-changes: fill **Alembic revision id(s)**; add **Backfill: none**; **Rollback** (drop P1 tables / forward-only reason); note OQ-WO-3 does **not** block P1 (P2 tables may be specified but not migrated in PR 1 unless Arch says otherwise — **P1 migration = `asked_for` + `analysis_param_defs` only**). | SPEC vs L1 is an implement trap. Schema template gaps block Arch and Alembic matching. |
| **DOC7** | **P1** | **Phase-scoped docs.** P1 PR must not publish live routing-map / work_order / results-persist / SOP-Apply-is-not-a-lie / parser-setup manuals. A one-line “P2–P5 specified, not shipped” in `asked-for.md` is enough. Do not claim dest-type Hold is closed (L5). Do not fold AR-RES into P1 UAT. | Sketch: one phase per PR. Lab Ops P2 closed until L2–L4 in sketch (already folded) **and** OQ-WO-1/3 Decided. |
| **DOC8** | **P1** | **Wizard stays removed (PR 75).** No new `/accessioning` wizard docs, no un-retiring `uat-sample-accessioning.md`, no Test Assignment step, no analysis picker on receive. Redirect mention only. | User lock + CORE bounce list. |
| **DOC9** | **P1** | **Living hygiene in the same PR:** checklist — tick Lab Ops + Documentarian; leave other reviews until those artifacts exist. Requirements **Status** no longer “Draft for formal review” once P1 implement starts (e.g. “P1 implementing / P2–P5 specified”). Index `docs-review/` in [`.docs/review/README.md`](../README.md). Optional: one-line in [framework-stamps](../../decision-logs/framework-stamps-2026-08-26.md) WO-7 bullets that TAT overlap is **refuse** (OQ-TAT-1). Internal US-1/US-7/US-23 “tests at accessioning” — rewrite or stamp superseded by asked-for (working notes, not merge-blocking). | Orphan checkboxes and “draft” status after Lab Ops Accept confuse the next agent. |

Already normative (restated so implementers do not drop them): empty routing map mints nothing; TAT overlap 409; client cannot write asked-for; no `results.unit_id`; no asked-for columns on `samples`; no projects→orders rename.

---

## 4. Required documentation updates for Cursor hand-off

**Cursor implement prompt (P1) must include:** update documentation, create/update UAT at `UAT_Scripts/uat-post-receive-work-spine.md`, and update README files. Absorb L1 and DOC1–DOC9 in the **same** PR. Do not implement P2–P5 in that PR.

### 4.1 P1 — must land with the asked-for PR

| # | Path | Action |
|---|------|--------|
| 1 | `UAT_Scripts/uat-post-receive-work-spine.md` | **Create.** P1 cases only (DOC1). |
| 2 | `.docs/review/manuals/asked-for.md` | **Create.** Operator SoT for the lake (DOC2). |
| 3 | `.docs/review/manuals/atomic-receive.md` | **Update.** After receive → Asked-for. A-15 no longer “parked.” CORE freeze unchanged. |
| 4 | `.docs/review/manuals/accessioning-workflow.md` | **Update stub.** Wizard removed; asked-for is the post-receive request path; `/tests` is not the order path. |
| 5 | `.docs/review/manuals/navigation.md` | **Update.** Asked-for after Receive. Strip live AccessioningForm / Accessioning flow. Redirect-only for `/accessioning`. |
| 6 | `.docs/review/manuals/workflow-accessioning-to-reporting.md` | **Update.** Stage after receive = asked-for; zero Tests. |
| 7 | `.docs/review/manuals/api-endpoints.md` | **Update.** P1 asked-for + param-defs contracts. |
| 8 | `README.md` | **Update.** Request vs Test language; links to manual + UAT. |
| 9 | `frontend/README.md` | **Update.** Work assignment = `/asked-for`, not Tests page. |
| 10 | `UAT_Scripts/uat-atomic-receive.md` | **Update pointer.** A-15 = this stem, not on receive. |
| 11 | `UAT_Scripts/atomic-receive/README.md` | Same pointer. |
| 12 | `UAT_Scripts/atomic-receive/scenarios.md` | Same pointer. |
| 13 | `UAT_Scripts/uat-test-ordering.md` | Banner: order path is asked-for UAT; do not un-retire wizard cases. |
| 14 | `UAT_Scripts/uat-testing-log.md` | Insert new script after atomic-receive. |
| 15 | `UAT_Scripts/uat-navigation-ui.md` | Asked-for nav case; no wizard sidebar item. |
| 16 | `.docs/internal/specs/post-receive-work-spine/SPEC.md` | Multi-sample contract (DOC6). |
| 17 | `.docs/review/schema-changes/post-receive-work-spine.md` | Alembic ids; backfill none; rollback; P1 tables only in PR 1. |
| 18 | `.docs/review/requirements/post-receive-work-spine.md` | Status line for P1 implementing. |
| 19 | `.docs/review/checklist/post-receive-work-spine.md` | Tick Lab Ops + Documentarian; P1 docs/UAT boxes when done. |
| 20 | `.docs/review/README.md` | Index `docs-review/`. |

**Do not:** revive `uat-sample-accessioning.md`; add analysis picker docs on `/receive`; UAT dest-type / Qubit-on-blood; type results on asked-for; write P2–P5 as live.

**Help (optional same PR):** if Help Management gets an Asked-for entry, keep L1 copy. Not a merge blocker.

### 4.2 Later phases — not the P1 PR

| Phase | When | Docs |
|-------|------|------|
| **P2** | After OQ-WO-1/3 Decided and L2–L4 in sketch (already folded) + reviews | Work-order docs: routing map (`config:edit`), TAT overlap 409, empty map mints nothing, intake/current type used for matching without chain-wide map-save AND, first ordered Experiment/LimsRun allowed types informational, `route_sample_type` 422 at incompatible step start, ordered process/step display, existing process AuthZ, **no Tests at WO save**. Update asked-for (`routed`, cancel-after-routed). Update `processes.md` with ordered steps. Update `lims-runs.md`: Test at **LimsRun start**, publish **422** if missing, and first-start freeze OPEN on `b005cfe`. UAT P2 cases stay in the same stem script. Dest-type Hold remains out. |
| **P3** | After OQ-RES-1 | Fold AR-RES into this stem UAT (or `uat-results-entry-review.md` with a pointer). Manual: typed number → `reported_result` + `qualifiers`; missing `units_default` → 422; no `results.unit_id`; two writers 409. **Not** results on asked-for. |
| **P4** | After OQ-SOP-2 for parser draft | `experiments.md` SOP Apply success path = **process definition** (template only if a step needs it). `processes.md` Apply. **L5 copy:** do not say NCI extract → Qubit is runnable. No SOP PDF bodies in git. |
| **P5** | Independent | Parser/instrument admin manuals: example + test + dry-run + activate; AI draft setup-only; production import no LLM. |

### 4.3 Cursor prompt fragment (paste into P1 implement)

```text
Mandatory with this PR (Documentarian DOC1–DOC9):
- Create UAT_Scripts/uat-post-receive-work-spine.md (P1 cases only).
- Create .docs/review/manuals/asked-for.md.
- Update manuals: atomic-receive.md, accessioning-workflow.md, navigation.md,
  workflow-accessioning-to-reporting.md, api-endpoints.md.
- Update README.md and frontend/README.md (asked-for ≠ Test; wizard stays removed).
- Point existing UAT (atomic-receive, test-ordering, testing-log, navigation-ui)
  at this stem. Do not un-retire uat-sample-accessioning.md.
- Copy lock: “asked-for / requested analysis” — never assign/create test or start work.
- SPEC: UI multi-sample → N POST rows (or sample_ids[] if you add it).
- Schema: Alembic ids; P1 tables only; backfill none; rollback note.
- One phase per PR. Do not implement P2–P5. Do not reopen /receive.
```

---

## 5. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (DOC1–DOC9) |
| **Date** | 2026-08-28 |
| **Docs ready for Cursor** | **Yes with conditions** — **P1 only** |
| **P1** | Docs list is implementable in the same PR. Lab Ops P1 gate already OPEN. Product implement still requires QA (required) + Architecture (schema) + Security (RLS/AuthZ) Accept / Accept-with-conditions. |
| **P2–P5** | **Not** licensed as live docs. Specify-only until those phase OQs are Decided and their reviews land. |
| **Not licensed** | Wizard revival · analysis picker on receive · Tests as the order path · dest-type E2E manuals/UAT · Qubit/blood testdata IDs · `results.unit_id` · projects→orders rename |

```
DOCUMENTARIAN REVIEW: Accept with conditions (DOC1–DOC9)
DOCS READY FOR CURSOR: Yes with conditions
```
