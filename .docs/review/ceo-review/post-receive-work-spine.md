# CEO / Product Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Mode:** HOLD SCOPE  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Lab Ops:** [`.docs/review/lab-ops-review/post-receive-work-spine.md`](../lab-ops-review/post-receive-work-spine.md) — **Accept with conditions** (L1–L5). P1 OPEN. P2 was closed until L2–L4 folded into the sketch — **they are folded**.  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**PRD:** [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Stamps:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md) (WO-1…WO-7, FW-0/FW-2)  
**Opens:** Processing **X-5** (asked-for vs work_order). Does **not** reopen AR CORE.

---

## Executive summary

Atomic receive CORE is shipped. Tubes land as Available for Testing with **zero Tests**. That is honest intake. It is not a lab. The missing middle is the framework spine:

**asked-for → routing → `work_order` → Process / Experiment / LimsRun → Test at LimsRun start → results**

Plus two configuration surfaces that make the execute stack sellable: SOP+AI Apply must write a **process definition**, and ops must be able to **configure parsers** without an engineer.

This is the right product. Do not collapse it. Do not expand it.

| Layer | Is | Is not |
|-------|----|--------|
| Asked-for (P1) | Request: analysis + TAT + params | Work plan, Test, Process, LimsRun |
| Routing + `work_order` (P2) | What the lab must run (one process definition with ordered steps) | A Test row |
| Execute (shipped) | Process → Exp and/or LimsRun | A third engine |
| Test (WO-7) | Minted at **LimsRun start** | Minted at receive / asked-for / WO save / publish |
| SOP Apply (P4) | Writes a **process definition** | Blood → DNA daughter → Qubit E2E |

**HOLD SCOPE.** P1 is the lake. P2–P5 stay specified in this packet so the spine is locked; coding is **one phase per PR**. Do not pull dest-type, lots, intake profiles, projects→orders, or IC50 into this slice.

Lab Ops is not Hold/Revise. Gate clears for CEO Accept-with-conditions. Product **accepts L1–L5 as C1–C5**. L2–L4 are now in the sketch, so the Lab Ops *sketch* gate on P2 is satisfied. P2 **coding** still waits a named type-eligibility source plus OQ-WO-1 / OQ-WO-3.

**Premise (HOLD):** If we did nothing, techs keep minting Tests from `/tests` (`TestForm`) and treat that as the work plan. That re-opens WO-7 under the name we already banned at receive. A request log that does not pretend work started is the honest next screen after Receive.

---

## Scope freeze (v1)

Matches requirements §§3–5. Do not expand.

| In (must ship for the named phase) | Out (ideas / other packets) |
|------------------------------------|-----------------------------|
| **P1** `/asked-for` + sample-detail section; request rows only | Reopen CORE receive / analysis picker / non-empty `analysis_ids` |
| **P1** zero Tests, Results, Processes, Experiments, LimsRuns, work_orders on save | Mint Tests at asked-for or work_order save |
| **P1** copy: asked-for / requested analysis; no Start/Execute on `requested` | Treat asked-for as the worklist or Tests page with a new name |
| **P1** multi-sample one operator action (same analysis + TAT + params) | One-by-one click per tube as the only path |
| **P2** `routing_map` analysis × intake/current sample_type × TAT range → one process definition with ordered steps | Empty map mints work_orders; overlapping TAT first-match; unordered step bag |
| **P2** map save does not AND intake type across later-step allow-lists; first-step allowed types are informational | Reject maps because a later ordered step expects a transformed type |
| **P2** current type rejected with **422 `route_sample_type`** when an incompatible step starts | Infer dest mint from `sample_type_transitions`; describe the sample as broken |
| **WO-7** Test at LimsRun start; publish **refuses** if missing | Ensure-on-publish find-or-create |
| **P3** typed number → `reported_result` + `qualifiers`; unit from `analytes.units_default` | `results.unit_id`; type numbers into asked-for |
| **P4** Apply → process definition; human save; never silent auto-activate | Claim dest-type Hold is closed; SOP PDFs in git; IC50 |
| **P5** admin CRUD instruments / CRO / parsers; example + dry-run + activate | CMMS; user-uploaded executable parsers; LLM on production import |
| AuthZ: `test:assign` + sample/project RLS for asked-for; `config:edit` for routing/parsers | Client writes asked-for / routing / parsers; new `order:create` perm this phase |
| One execute substrate: Process / Experiment / LimsRun | Second workflow engine; rename `projects` → `orders` |

**Bounce (any phase PR):** requirements §6 plus Lab Ops locked list. A PR that violates those fails this stamp.

---

## Phase gates

| Slice | CEO | Meaning |
|-------|-----|---------|
| **P1 Asked-for** | **Implement OPEN** | Code against RQ-AF-* / SPEC P1 with **C1** in the same PR. OQ-AF-* already Decided (provisional). |
| **P2 Routing + work_order** | **Design accepted.** **Coding closed** until Arch names type-eligibility config (C2) and OQ-WO-1 / OQ-WO-3 are Decided. | L2–L4 are in the sketch (Lab Ops sketch gate cleared). Product default for OQ-WO-1 below. FK direction is Arch, not product. |
| **P3 Results persist** | **Design accepted.** **Coding closed** until OQ-RES-1 (Sci CSO). | Persist lock only. Not a results product. Not P1 UAT. |
| **P4 SOP+AI Apply** | **May proceed with C5 / L5.** | Closes the template-only lie. Dest-type Hold unchanged. OQ-SOP-2 before optional parser draft. |
| **P5 Parser setup UX** | **OPEN** (independent of P1). | Engine exists. This is ops skill-floor (R-8). Not a substitute for a work list. |
| **Extract-hold dest type** | **Not licensed** | Own stem. Blood → DNA daughter → Qubit on the daughter remains Hold. |

**Product default (OQ-WO-1):** auto-route when a map row matches; else stay `requested` with an explicit “configure routing” CTA. Empty map must **not** toast as success / work queued (AC-P2-2). Does not block P1.

---

## Conditions

Product accepts Lab Ops **L1–L5** as same-phase. C1–C5 **are** L1–L5. Additional C* freeze the lake, the bounce list, and P2 coding honesty.

| ID | Condition | Aligns |
|----|-----------|--------|
| **C1** | **Asked-for is a request lake, not the work plan.** Copy: “Asked-for” / “requested analysis,” never “assign test,” “create test,” “start work,” or “order process.” Saving asked-for creates **zero** Tests, Results, Processes, Experiments, LimsRuns, work_orders. **No Start / Execute CTA** on a `requested` row. UI is **not** `/receive`; receive still **422** on non-empty `analysis_ids`; do not call `_create_tests` / `_create_asked_for_tests` / `_create_tests_for_sample`. **Multi-sample:** one operator action (same analysis + TAT + params) can write asked-for for a **set** of received samples. API may remain one row per sample; the action is all-or-nothing **or** every per-sample failure is visible — never silent partial success. Show a computed due date from `tat_days`; keep `tat_days ≥ 1` (do not add STAT 0 this phase). Sidebar Sample Mgmt: **Asked-for immediately after Receive.** Do not reuse `TestForm`. | Lab Ops **L1** |
| **C2** | **Marc/Rolf authoring lock:** a map may name intake/current type for analysis × type × TAT matching, and map save / Route do not compare that type with every ordered step. Later steps may expect a transformed type. The planner displays the first ordered Experiment or LimsRun step’s allowed types for information only. At step start, current type must be accepted by that step; otherwise return `route_sample_type` (422), meaning wrong type for the step, not a broken sample. Do not infer dest mint from `sample_type_transitions`; dest-type Hold remains. Do not invent Qubit/blood testdata IDs. | Lab Ops **L2**, superseded authoring rule |
| **C3** | **Params travel.** Asked-for `params` snapshot onto the Test at **LimsRun start** (WO-7) and freeze. Tech does not re-type cell line / assay params to run the assay. Empty defs remain empty-object-only (OQ-AF-3). Uniqueness stays `(sample_id, analysis_id)` while open for P1. Do **not** expand uniqueness to param identity this phase. | Lab Ops **L3** |
| **C4** | **The process definition’s ordered steps are the work plan.** `work_orders.process_definition_id` is frozen at mint (WO-3). Start instantiates that definition via **existing** process AuthZ (`experiment:manage`). Route and process UI make step order apparent; no unordered bag and no second routing hop. | Lab Ops **L4**, singular-definition lock |
| **C5** | **SOP Apply writes a process definition. It does not close dest-type Hold.** Apply success / manuals / UAT: draft process definition with typed steps; human save; never silent auto-activate. **Do not** say the NCI extract → Qubit path is runnable. **Do not** UAT blood → DNA daughter → Qubit on the daughter in this packet. Dest type remains [extract-hold-dest-type](../requirements/extract-hold-dest-type.md) / [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md). No SOP PDF bodies in git. Not IC50. | Lab Ops **L5** |
| **C6** | **Do not sell P1 as a worklist.** P1 is a request log. The work list is P2 `work_order`. Classic `/tests` + `TestForm` still mints Tests (WO-4 type-a-number stays). Do not delete it in P1. P1 UAT and manuals: record requests on **Asked-for**, not TestForm. Revisit hiding Test-create only after dogfood. Domain processing PRD still says “ensure-on-publish”; this packet **supersedes** that — publish **422** if Test missing. | Product freeze / WO-7 |
| **C7** | **One phase per PR.** P1 tables + API + `/asked-for` + pytest + UAT script in PR 1. Do not land P2–P5 schema/UI in the P1 PR. Receive code freeze except bugs. | Completeness of spine, small diffs |
| **C8** | **AuthZ / RLS / client.** Asked-for write = `test:assign` + sample → project RLS (same as tests). Client role: read if they can read the sample; **no** create/cancel/route. Routing map and parser activate = `config:edit` only. Hidden sample → **403**, not 404. | RQ-AF-7/8, bounce #8 |
| **C9** | **With ship (P1):** `UAT_Scripts/uat-post-receive-work-spine.md` created at implement (P1 cases first). Do not use retired `uat-sample-accessioning.md`. Pytest: create, 409 dup, 403 RLS, 422 params, receive still 422 on `analysis_ids`, asked-for leaves tests count 0. Docs/manuals under `.docs/review/`. | Full-pipeline implement requirements |

Already normative (restated so implementers do not drop them): empty routing map mints **nothing**; TAT overlap **409** on save; WO does **not** create Tests; missing `analytes.units_default` → **422**; no `results.unit_id`; P5 AI draft is setup-only; production import = no LLM.

---

## HOLD SCOPE rigor (no expansion)

### Complexity

Five phases in one packet is the **spine lock**, not a five-PR merge. P1 is two tables (`asked_for`, `analysis_param_defs`), one service, one page + sample-detail panel, sidebar item. Reuse analysis dropdown (not TestForm), existing project RLS, existing `test:assign`. That is the minimum that records a request without lying.

P2 adds `routing_map` + `work_orders` and routes into **existing** `/v1/eln-processes`. Do not build a third engine. Do not add dest-type columns here.

### What already exists (reuse)

| Sub-problem | Exists | This packet |
|-------------|--------|-------------|
| Identity + vessels | AR CORE `/receive` | Do not touch except bugs |
| Test mint at accession | `_create_tests_for_sample` on **legacy** accession; receive already refuses | Must not be the asked-for path |
| Classic Test create | `POST /tests`, `TestForm`, `/tests` | Stays (WO-4). Not the request UI |
| Execute | Process / Experiment / LimsRun | Route into it |
| Parser engine | `data_parsers`, instruments, CRO, dry-run pieces | P5 is admin UX, not a new engine |
| SOP parse | `SopParseJob` → ExperimentTemplate only | P4 changes Apply target |
| Dest type | extract-hold packet; execute still copies parent type | Out |

### Minimum that ships value (P1 lake)

Receive a rack of plasma → one Asked-for action for ELISA, 5-day TAT → zero Tests → sample still Available for Testing. Duplicate same sample+analysis → 409. User without project access → 403. That is the lake.

### Deferred without blocking P1

Routing / work_order coding; dest-type execute; STAT `tat_days = 0`; uniqueness including param identity; hiding Test-create; projects→orders; lots/registration; intake-profile engine; wizard revival; P3 persist lock; SOP parser-draft bind.

### Failure modes (P1 must not be silent)

| Case | User sees |
|------|-----------|
| RLS-hidden sample | 403 |
| Duplicate open asked-for | 409 |
| Unknown / missing required param | 422 |
| `tat_days` < 1 | 422 |
| Discarded sample | 422 (v1) |
| Receive non-empty `analysis_ids` | 422, no rows |
| Multi-sample: one tube 409 | No silent success on the rest |
| Empty routing map (P2) | Stay `requested`; configure-routing CTA; not “queued” |
| Map overlap (P2) | 409 on save |
| Step start while current type is incompatible (P2) | 422 `route_sample_type` |
| Publish without Test (P2+) | 422 |
| Two writers on same Test (P3) | 409 |
| Missing `units_default` (P3) | 422, no row |
| SOP Apply auto-activate (P4) | Forbidden |
| Parser AI on import (P5) | Impossible (no call site) |

### State (asked-for)

```text
        create
           │
           ▼
      requested ──cancel──► cancelled  (re-create allowed; unique ignores cancelled)
           │
           │ P2 route (map match)
           ▼
        routed     (cancel after routed is P2: WO first)
```

P1 writes `requested` / `cancelled` only. No Start on `requested`.

### Dream-state delta (note only)

```text
  NOW                         THIS PACKET                         12-MONTH
  Receive, zero Tests   →    asked-for lake (P1)            →   request → route → WO
  Tests page = fake order    spine specified P2–P5               Process/Exp/LimsRun
  SOP Apply = template lie   P4 Apply = process definition       dest-type daughters
  Parser setup = eng ticket  P5 ops can activate                 ops-owned METHOD_CATALOG
```

This plan moves **toward** that by locking the spine and shipping the lake. Expanding dest-type, lots, or intake profiles into this packet would move **away** from honesty (we would claim hops that execute cannot perform).

### NOT expanding (will bounce)

- `work_order` / routing **code** in the P1 PR  
- Intake-profile engine / wizard revival / bulk intake UI  
- Compound registration / lots (WO-5/6)  
- Materials, multi-tenant, IC50 / dose-response  
- Extract-hold dest type / blood→DNA→Qubit E2E / invented Qubit/blood IDs  
- Rename `projects` → `orders`  
- New `results.unit_id`; asked-for columns on `samples`  
- Ensure-on-publish Test mint  
- LLM on production file import  
- Client write of asked-for / routing / parsers  

---

## Lab Ops note

Current Lab Ops artifact is **Accept with conditions (L1–L5)**. **Not Hold. Not Revise.**

- **P1 OPEN** — L1 is already RQ-AF-2/3 + bounce; copy, zero Tests, receive freeze, multi-sample land with the P1 PR (**C1**).  
- **P2 sketch gate:** Lab Ops closed P2 coding until L2–L4 were in the tech sketch. Marc/Rolf supersede the old L2 authoring rule: no chain-wide intake-type AND on map save or Route; gate current type at step start. L4 is ordered steps in one process definition. Params snapshot remains at LimsRun start.
- **P4** may write process definitions with **L5 / C5**. Dest-type Hold unchanged.  
- **P5** independent.

CEO does not replace Lab Ops. Product accepts L1–L5 as C1–C5.

Lab Ops watch items we freeze as product (non-blocking for P1, not expansions):

1. Classic Tests page still mints Tests — **C6**.  
2. Uniqueness `(sample_id, analysis_id)` while open — fine for empty-params P1; revisit when param defs are real — **C3**.  
3. `tat_days ≥ 1` vs STAT 0 — keep ≥ 1; show due date — **C1**.  
4. Asked-for requires Available for Testing; do not block a second analysis on a sample already in a process.  
5. Catalog gap for NCI blood→DNA→Qubit remains; do not invent IDs.

---

## Approaches considered (HOLD — not a reopen)

| Approach | Verdict |
|----------|---------|
| **A. Classic Tests as the order** | Rejected. Violates WO-7. Status quo hurt. |
| **B. Asked-for lake, then routing/`work_order` into existing execute (this packet)** | **Accepted.** Completeness of the spine in the packet; P1 is the implement lake. |
| **C. Skip P1, mint work_order from analysis at save** | Rejected. Empty map mints nothing, so there is no honest path; also collapses request ≠ work. |

HOLD SCOPE does not cherry-pick expansions. Approach B stands.

---

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (C1–C9; C1–C5 = L1–L5) |
| **Mode** | **HOLD SCOPE** |
| **Date** | 2026-08-28 |
| **Lab Ops** | Accept with conditions (L1–L5); P1 OPEN; P2 sketch gate cleared by L2–L4 fold |
| **P1 implement** | **OPEN** — asked-for lake with C1 / L1 in the same PR |
| **P2** | **Design accepted.** **Coding closed** until named type-eligibility source (C2) + OQ-WO-1 / OQ-WO-3 Decided |
| **P3** | Design accepted; coding waits OQ-RES-1 (Sci CSO) |
| **P4** | May proceed with C5 / L5; dest-type Hold unchanged |
| **P5** | **OPEN** (independent; admin UX) |
| **Not licensed** | Extract-hold dest type · blood → DNA → Qubit E2E · Qubit/blood testdata IDs · intake-profile engine · lots/registration · IC50 · minting Tests at asked-for or WO save · ensure-on-publish |

```
CEO REVIEW: Accept with conditions
MODE: HOLD SCOPE
LAB OPS: Accept with conditions (L1–L5)
```
