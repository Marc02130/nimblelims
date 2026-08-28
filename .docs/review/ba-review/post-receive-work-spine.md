# BA Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Reviewer persona:** Business Analyst  
**Packet:**  
- Requirements: [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
- Tech sketch: [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
- Schema: [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
- PRD: [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
- Spec: [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
- Open questions: [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
- User stories: [`.docs/internal/user-stories/sample-processing/USER-STORIES.md`](../../internal/user-stories/sample-processing/USER-STORIES.md) (US-7)  
**Related reviews:** [Lab Ops](../lab-ops-review/post-receive-work-spine.md) (Accept with conditions, L1–L5; P1 gate OPEN)  
**Stamps:** [framework-stamps-2026-08-26.md](../../decision-logs/framework-stamps-2026-08-26.md) (WO-1…WO-7, FW-0/FW-2). Packet opens **X-5**. Does not reopen CORE receive.

---

## 1. Executive summary

P1 asked-for is the correct MVP hole after CORE receive. Tubes land **Available for Testing** with **zero Tests**. The bench still has no honest place to record “ELISA, 5-day, these plasmas” without minting a Test and violating WO-7. **US-7 is rewritten for that job.** That is the right story. It is not yet a testable story.

The product ACs in requirements §7 (`AC-P1-1`…`AC-P1-3`) and US-7’s bullet list under-specify the lake that RQ-AF-1…10, L1, the spec, and the sketch already describe: cancel, client 403, params 422, list filters, copy / no Start, multi-sample, sample-status eligibility, cancelled-then-recreate. QA cannot write P1 UAT from US-7 as printed.

P2–P5 belong in this packet so the spine is reviewable. They are **not** this implement. There are **no** user stories for routing, `work_order`, persist lock, SOP Apply, or parser setup. P2 ACs miss L3/L4/WO-7. That is acceptable **only** if those phases do not start until stories + testable ACs + their Open OQs are closed. Do not code them in the P1 PR.

OQ-AF-1…3 and OQ-TAT-1 are statused correctly and do not block P1. Lab Ops watches that are product questions (multi-sample txn, PATCH vs cancel, uniqueness vs params, STAT `tat_days=0`, classic Tests fork) are **not** on the living log. Record them (BA7). Do not reopen dest-type, projects→orders, or analysis-on-receive.

**Verdict: Accept with conditions.** P1 may implement if BA1–BA7 land in the **same** P1 PR (docs + code). P2–P5 are not licensed by this stamp.

---

## 2. Requirements & scope assessment

| Dimension | Notes |
|-----------|--------|
| **Requirements completeness** | P1 lake is specified: entity, status (`requested` / `cancelled` in P1), uniqueness, AuthZ, RLS, params vs defs, not-on-receive, bounce list, non-goals. **Gaps vs sketch/Lab Ops:** (1) Sample.status = Available for Testing is in sketch §3.2 and Lab Ops watch #4, **not** in RQ-AF-*. (2) Multi-sample is L1 / RQ-AF-1 but spec POST is one `sample_id` with **no** per-row vs all-or-nothing rule. (3) No PATCH; only cancel — mutate-while-requested is unspecified. (4) Analysis-must-be-active is sketch-only. (5) Param-def **UI** is not in P1 RQs (table + PUT in spec) — keep it API-only. P2–P5 functional tables are enough to lock the spine, not enough to implement. |
| **User stories & AC** | **US-7 rewrite is the right P1 story** (request, not Test). ACs fail the testable bar — see §2.1. Product `AC-P1-1`…`3` are happy-path slogans, not Given/When/Then. P2–P5 have **no stories**. Adjacent stories still describe the old ordering world: US-1 “optional tests” at receive, US-8 “create-at-receive”, US-23 battery-at-accessioning, US-35 `POST /tests` as assign-analysis. Living UAT `uat-test-ordering.md` and `frontend/README.md` still title US-7 “Assign Tests to Samples”. |
| **MVP / scope control** | **Correct.** P1 = test-ordering hole. P3 = persist lock on an **existing** Test (results-entry hygiene), not a results product, and **must not** enter P1. P4/P5 explicitly not the MVP bar. Non-goals and bounce list prevent receive reopen, Test-at-order, third engine, projects rename, dest-type pretend. Risk: one-packet sketch tempts a five-phase PR. Sketch “one phase per PR” is normative — keep it. Do not sell P1 as a worklist (Lab Ops). |
| **Open-questions hygiene** | **P1 OQs are clean** (AF-1/2/3 Decided provisional). Gate rule correctly leaves P2 on OQ-WO-1/3, P3 on OQ-RES-1, P4 parser draft on OQ-SOP-2. **Missing rows** for Lab Ops watches and P1 edge cases — BA7. Do not treat checklist tasks as OQ owners. Domain sample-processing PRD still says “ensure-on-publish” in the WO-7 diagram; **this packet supersedes** (publish refuses). |
| **Traceability** | RQ-AF-1…10 ↔ spec HTTP ↔ sketch P1 ↔ schema `asked_for` + `analysis_param_defs` + `uq_asked_for_open` line up. L1 is folded into RQ-AF-1/2/3 and sketch §3.2. **Breaks:** US-7 and §7 ACs do not trace to RQ-AF-6/7/9/10 or L1 multi-sample. Sketch eligibility rule has no RQ id. `RQ-WO-11` is inserted out of number order (cosmetic). X-5 is opened as this packet — good. |
| **Prioritization & practicality** | Right CRO shape: rack of plasmas, one analysis + TAT, no lie that work started, reuse `test:assign`, no new permission (OQ-AF-2). Empty param defs in P1 is practical. Classic TestForm stays (WO-4) so P1 does not delete type-a-number; P1 UAT must not use it as the order path. STAT/`tat_days=0` and param-identity uniqueness are correctly **not** P1. |

### 2.1 US-7 and product AC quality (P1)

US-7 as written covers: surface (`/asked-for` + sample detail), analysis + TAT + optional params, `requested`, zero Tests, duplicate 409, not on receive, `test:assign` + RLS, WO-7 timing, `POST /api/v1/asked-for`.

**Missing vs RQ / L1 / spec (must become AC — BA1):**

| Need | Source | In US-7 / AC-P1-* today? |
|------|--------|--------------------------|
| Zero Tests **and** zero Results, Process, Experiment, LimsRun, work_order | RQ-AF-2, L1, AC-P1-1 (Tests/WO only) | Partial |
| Copy: requested analysis; never assign/create test, start work, order process; **no Start/Execute** on `requested` | L1 | No |
| Multi-sample one operator action; API one row per sample | L1, RQ-AF-1 | No |
| Cancel while `requested`; not after `routed` (P2) | RQ-AF-10, spec | No |
| Cancelled then same (sample, analysis) recreate → 201 | Sketch §8, unique ignores cancelled | No |
| Unknown param key / missing required def → 422; empty `{}` when zero defs | RQ-AF-6, OQ-AF-3 | No |
| Client cannot POST; client with project access can GET | RQ-AF-7, PRD §1, spec | No |
| Missing `test:assign` → 403 (not only foreign project) | RQ-AF-7 | Partial (AC-P1-3 is project only) |
| RLS-hidden sample → **403 not 404** | Spec errors | No |
| List: by sample, project, analysis, status `requested` | RQ-AF-9 | No |
| Receive still **422** on non-empty `analysis_ids`; UI not on `/receive` | RQ-AF-3, bounce #1 | Partial (“not on the receive form”) |
| `tat_days` integer ≥ 1 else 422 | RQ-AF-1 | No |
| Analysis inactive / unknown → 422 | Sketch | No |
| Sample not Available for Testing → 422 | Sketch, Lab Ops watch #4 | No |

`AC-P1-2` must say **open** duplicate (cancelled does not 409). `AC-P1-1` must name role (`test:assign`), status `requested`, and ELISA as a **catalog analysis that exists** — not a magic string.

### 2.2 P1 RQ ↔ story ↔ AC (trace)

| RQ | US-7 | Product AC | Implement notes |
|----|------|------------|-----------------|
| RQ-AF-1 | Partial (no multi-sample, no copy) | AC-P1-1 thin | L1 + BA2 |
| RQ-AF-2 | Zero Tests only | AC-P1-1 | Broaden to full zero-mint |
| RQ-AF-3 | Not on receive form | Missing receive 422 | Bounce #1 is the AC |
| RQ-AF-4 | Yes | AC-P1-2 (missing “open”) | Unique partial index |
| RQ-AF-5 | `requested` only | No | P1 must not write `routed` |
| RQ-AF-6 | “optional params” | No 422 AC | OQ-AF-3 |
| RQ-AF-7 | `test:assign` | AC-P1-3 project only | Client write 403 |
| RQ-AF-8 | Project RLS | AC-P1-3 | Mirror tests |
| RQ-AF-9 | No | No | Spec GET query params |
| RQ-AF-10 | No | No | Cancel endpoint exists in spec |

### 2.3 P2–P5 (specified, not this implement)

| Phase | Stories | Product AC hole | OQ gate |
|-------|---------|-----------------|--------|
| **P2** | None | Missing: TAT overlap 409, empty map mints nothing (AC-P2-2 is the exception — keep), L3 params snapshot at LimsRun start, L4 chain N→N+1 from WO snapshot, Test **not** at WO save, publish 422 if Test missing, WO statuses, cancel-routed-requires-WO-first | OQ-WO-1, OQ-WO-3 **Open**. Lab Ops: P2 coding **closed** until L2–L4 in sketch (now folded — still do not code until OQs + stories). |
| **P3** | US-9 is the old results product, not persist lock | Missing two-writers **409** (RQ-RES-3). `AC-P3-1/2` OK as persist happy/fail | **OQ-RES-1 Open** — blocks P3 |
| **P4** | None | Missing human save / never silent activate; L5 dest-type copy | OQ-SOP-2 Open for parser draft only. Dest-type Hold is a **different** packet. |
| **P5** | None | Missing `config:edit`, instrument XOR CRO, example+test+dry-run | OQ-IMP-1 Decided — may parallel P1 **after staffing**, not inside the P1 PR |

---

## 3. Conditions (must land with P1 implement)

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **BA1** | **P1** | **Make P1 ACs testable.** Expand requirements §7 `AC-P1-*` **and** US-7 acceptance criteria to cover the table in §2.1 (zero-mint, copy / no Start, cancel, recreate after cancel, params 422, client GET-only, `test:assign` 403, RLS 403-not-404, list filters, receive `analysis_ids` 422, `tat_days` ≥ 1, inactive analysis 422, Available for Testing 422). Write them as lab-user checks a UAT script can execute, not architecture slogans. New script remains `UAT_Scripts/uat-post-receive-work-spine.md` (P1 cases first) — create at implement, not a docs-only PR. | US-7 rewrite is the right story with the wrong AC list. Tobias cannot gate P1 from three one-liners. |
| **BA2** | **P1** | **Multi-sample is one operator action; API stays one row per sample; per-row success/fail.** Same analysis + TAT + params across a set of received samples (L1). No bulk-all-or-nothing endpoint in P1 unless Arch adds one. UI shows a summary of created vs 409/403/422. Do not require the tech to submit once per tube. Record as **OQ-AF-4 Decided (provisional)** on the living log. | Lab Ops requires the rack action. Spec POST is single-row. Leaving txn semantics unstated will fork implementations. Per-row matches “API still one row per sample” without inventing a bulk contract. |
| **BA3** | **P1** | **Promote eligibility to an RQ.** Asked-for create requires `Sample.status = Available for Testing` → **422** otherwise (discarded / quarantined / rejected / other). **Process membership does not block** a second analysis on that sample (Lab Ops watch #4; Decision #24 is process membership, not Sample.status). Align US-35 language: asked-for is this packet’s assign-analysis path; classic `POST /tests` remains WO-4 type-a-number on an existing Test/sample until a later ops tweak — it is **not** the P1 happy path. | Rule lives only in the sketch today. US-35 still says test ordering = `POST /tests`. |
| **BA4** | **P1** | **No PATCH of asked-for in P1.** Mutate = cancel while `requested`, then recreate (unique ignores `cancelled`). Cancel when status ≠ `requested` → **409** or **422** (pick one in spec; pytest both shapes). Record as **OQ-AF-5 Decided (provisional)**. | Spec has cancel only. Unspecified PATCH will appear as “edit TAT” scope. |
| **BA5** | **P1** | **Param defs are a table + GET (PUT = `config:edit`). No param-def admin UI in P1.** OOB may have zero defs; `params: {}` is the success path. Unknown keys still 422. Do not build a Field Management surface for `analysis_param_defs` in this PR. | OQ-AF-3. PUT in the spec is not a license for a config app. |
| **BA6** | **P1** | **Happy-path SoT is rewritten US-7, not legacy test-assign.** P1 UAT and manuals: record requests on **Asked-for** (sidebar after Receive). Do **not** implement US-23 battery-at-accessioning, US-1 “optional tests at receive”, or `uat-test-ordering.md` TC-TEST-ASSIGN-001 / battery-at-intake as this packet. Do not revive `/accessioning` wizard analysis picker. Classic `/tests` TestForm **stays** (WO-4, Lab Ops watch #1) and is **not** the ordering happy path. Retired `uat-sample-accessioning.md` stays retired. | Stale US-1 / US-8 / US-23 / US-35 / frontend README / `uat-test-ordering.md` still title US-7 “Assign Tests.” Implementers will mint Tests. |
| **BA7** | **P1 docs** | **Record unrecorded product questions on** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md) **before or with the P1 PR:** OQ-AF-4 (BA2), OQ-AF-5 (BA4), OQ-AF-6 (BA3 eligibility), **OQ-AF-7** uniqueness `(sample, analysis)` vs param identity — **Open, does not block P1**, blocks real param defs / two ELISA cell lines; **OQ-TAT-2** STAT / `tat_days=0` — **Deferred**, P1 stays ≥ 1, computed due-date display is **not** P1 required; **OQ-AF-8** classic Tests-page fork — **Deferred**, keep TestForm. Update the OQ gate rule so P1 stays unblocked. | Lab Ops watches #1–#3 are product questions sitting only in a review. BA does not leave them unrecorded. |

Already normative (restated so they are not dropped): L1 copy / zero-mint / not-on-receive; bounce list §6; empty routing map does not exist in P1 and P1 **must not** call routing; P1 does not write `routed`; client cannot create; no `results.unit_id`; no asked-for columns on `samples`.

---

## 4. Deferred / out-of-scope items

**Not P1 — do not code in the P1 PR:**

- Routing map, `work_order`, auto-route vs Route button (OQ-WO-1), FK direction (OQ-WO-3), L2 type gate, L3 params snapshot, L4 chain walk, WO-7 LimsRun-start tighten / remove ensure-on-publish.
- P3 persist lock (OQ-RES-1). Do not type numbers on asked-for. Do not fold AR-RES into P1 UAT.
- P4 SOP Apply → process definition (L5). Dest-type Hold unchanged. No blood → DNA → Qubit UAT. No SOP PDF bodies. Not IC50.
- P5 parser setup UX (may staff-parallel **after** P1, not inside it).
- Batteries on asked-for (rewrite US-23 later; do not put batteries on receive).
- Hide/delete classic Test create. Computed due date from `tat_days`. STAT/`tat_days=0`. Uniqueness including param identity.
- Projects → orders. Intake-profile engine. Wizard revival. Compound/lots. Materials. Multi-tenant. Extract-hold dest type.

**Before P2 / P3 / P4 / P5 coding (not P1 conditions):** add sample-processing user stories with testable ACs for that phase; close that phase’s Open OQs; P2 still needs Lab Ops L2–L4 in the sketch (folded 2026-08-28 — re-check before the P2 PR). Domain [sample-processing PRD](../../internal/prd/sample-processing/PRD.md) WO-7 diagram still says ensure-on-publish — **this packet wins**; fold the domain PRD/SPEC on the P2 docs pass, not as a P1 blocker.

**Watch (non-blocking):** `RQ-WO-11` numbering; checklist Reviews still unchecked for Lab Ops (done) and this BA; US-8 status names still assume create-at-receive.

---

## 5. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (BA1–BA7) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** |
| **P1** | **OPEN** if BA1–BA7 land with the P1 PR (AC/US-7, multi-sample per-row, eligibility RQ, no PATCH, no param UI, SoT vs stale US-7 UAT, OQ rows). L1 remains Lab Ops same-phase. |
| **P2** | **CLOSED** for this BA stamp until stories + testable ACs exist **and** OQ-WO-1 / OQ-WO-3 are Decided. Lab Ops still closed P2 coding on L2–L4 (now in sketch — not a license to skip stories). |
| **P3** | **CLOSED** until OQ-RES-1 and a persist-lock story/AC (not a new results product). |
| **P4** | Stories + L5 copy required before coding. Not MVP. Dest-type Hold unchanged. |
| **P5** | Stories + ACs before coding. Independent of P1; **not** the P1 PR. |
| **Not licensed** | Extract-hold dest type · blood → DNA → Qubit E2E · mint Tests at asked-for or WO save · analysis on `/receive` · battery-at-accessioning · projects→orders · PATCH asked-for · param-def admin UI |

```
BA REVIEW: Accept with conditions (BA1–BA7)
IMPLEMENT GATE: OPEN (P1 only)
```
