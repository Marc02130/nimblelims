# Requirements: Post-receive work spine

**Date:** 2026-08-28  
**Status:** P1 shipped. P2 `b005cfe` has signed per-AC history; publish-refuse Pass. First-start freeze is in code; ordered-route lock in code. Overall P2 unsigned/not Pass pending UAT restamp. Hold product merge. Current lock: analysis + TAT + ordered `process_definition[]`; map-save 409 only when TAT **and** first-step allow-lists overlap; Route 409 when two saved rows both accept current type. Not IC50.
**Stem:** `post-receive-work-spine`  
**Leadership sequencing (2026-08-28):** order (asked-for) → work_order → results → SOP+AI → process → instrument import config  
**Do not implement P2+ until those phase reviews Accept / Accept-with-conditions and open questions that block the named phase are Decided.**

**Domain PRD:** [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)

**Depends on (shipped):** atomic receive CORE (`/receive`, zero Tests). Wizard removed (PR 75). Process / Experiment / LimsRun execute substrate. `data_parsers` catalog (import engine). SOP parse → ExperimentTemplate only (lie to close in P4).

**Stamps:** WO-1…WO-7, FW-0/FW-2, WO-7 Test at LimsRun start. This packet **opens X-5**. It does **not** reopen CORE receive.

**Param catalog examples (not seed):** [`.docs/decision-logs/2026-08-28-analysis-param-defs.md`](../../decision-logs/2026-08-28-analysis-param-defs.md) — table-design rows + run-start JSON shape for Heidi.

**Room locks (2026-08-28):**

1. **P1 lake** = asked-for records **requested analysis + TAT + params**. Bounce Test / Result / Process / Experiment / LimsRun / work_order mint, second workflow engine, analysis picker on `/receive`, silent Order→work.
2. **Heidi:** `GET /asked-for` `list()` must **dual-belt `has_project_access`** (same as create), **not RLS-only**. `analysis_param_defs` RLS may be any logged-in user; mutate stays `config:edit` in the router. P1 must **not** write status `routed` (`routed` is P2). Type × analysis eligibility is **P2 (L2)**, not this PR.
3. **Params** on `asked_for` are **order capture**, not the Test snapshot. Freeze still happens at LimsRun start (WO-7 / P2). Bounce Start/Execute CTA, silent Order→work, analysis picker on `/receive`, README that equates asked-for with Test assign. Classic `/tests` type-a-number stays.
4. **Mathilda U1 / U2:** asked-for ≠ Test assign. Label params as order capture, not Test snapshot.
5. Architecture / UI / Spec **Accept with conditions** on P2. P1 UAT Pass; PR 81 merged. Hold product merge. Not IC50.
6. **Receive freeze:** non-empty `analysis_ids` still **422**.
7. Operator how-tos live in git-tracked [`/manuals/HOWTO.md`](../../../manuals/HOWTO.md). Do not put operator manuals back under `.docs/review/manuals/`.
8. **P2 ordered route:** each `routing_map` row and work-order snapshot hold an ordered `process_definition[]`. This is not one definition and not an unordered bag. Start instantiates the first process only; later processes start later in route order.
9. **WO-7 publish (Tobias-signed Pass @ `b005cfe`):** refuse the **whole** publish (**422**) if a Test is missing — stay unpublished, zero Results, no Test remint. Do **not** fold first-start freeze into that historical Pass.
10. **Freeze:** first LimsRun start wins. Do not overwrite `asked_for_params` on an existing Test. Guard is in code; UAT restamp unsigned.
11. **P2-4 / Heidi belt:** Route is `test:assign`; do not put `experiment:manage` on Route. Process metadata is catalog-visible so the UI can show ordered `process_definition[]` and derive the first process / first Experiment-LimsRun allow-list. Mutate stays `config:edit`; each process start stays `experiment:manage`.
12. **Heidi/Leadership overlap lock:** no map sample-type picker. Map save **409**s only when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold. Extract-first and Qubit-first for the same TAT are legal. Route: match analysis + TAT, then current type against each candidate’s first process / first step. Zero acceptable → 422; two saved rows that both accept current type → 409; no silent `first()`. Map save does not chain-AND later processes/steps.

---

## 1. Problem

Receive registers identity + vessels. The bench question after that is **what was asked for** and **what the lab must do**. Today those are missing:

| Gap | Today | Hurt |
|-----|--------|------|
| Asked-for | Tests page can mint a Test; receive refuses analyses | Test is treated as the work plan (WO-7 violation if used as “order”) |
| Work list | No `work_order` | Tech guesses extract vs assay |
| Results persist | Classic results exist; persist lock not a reviewed slice | Typed number vs unit/qualifiers drift |
| SOP + AI | Apply writes ExperimentTemplate only | Selling point is a lie |
| Parser setup | Engine exists; ops skill floor high (R-8) | Labs cannot configure import without eng |

## 2. Spine (normative)

```text
RECEIVE          identity + 1..N vessels          SHIPPED
ASKED-FOR (P1)   analysis + TAT + params          SHIPPED (PR 81)
ROUTING (P2)     analysis × TAT; first-step type gate     THIS PACKET
WORK_ORDER (P2)  ordered process_definition[]      THIS PACKET
EXECUTE          Process → Exp and/or LimsRun     SHIPPED (route into it)
TEST (WO-7)      created at LimsRun start         THIS PACKET (timing lock)
RESULTS (P3)     persist lock                     THIS PACKET
SOP+AI (P4)      Apply → process definition       THIS PACKET
PARSER SETUP (P5) instruments / CRO / parsers     THIS PACKET (config UX)
```

**Name collision:** `asked-for` is **not** a rename of `projects`. The “projects → orders” idea stays parked. Asked-for ≠ Test assign. Classic `/tests` type-a-number stays (WO-4).

## 3. Phases (implement in order)

| Phase | Name | MVP pillar | Implement when |
|-------|------|------------|----------------|
| **P1** | Asked-for (lake) | Test ordering | **Shipped** (PR 81; UAT Pass 2026-08-28) |
| **P2** | Routing + work_order | Test ordering / processing | `b005cfe` per-AC signed history; overall unsigned/not Pass. Ordered `process_definition[]`; map-save 409 only on TAT **and** first-step allow-list overlap; Route 409 when two saved rows both accept current type. Hold product merge. |
| **P3** | Results persist | Results entry | **CLOSED.** After P1 (may parallel P2 if Test exists via LimsRun or classic) |
| **P4** | SOP+AI → process definition | Processing (not MVP bar) | **CLOSED.** P2 process definition is the Apply target; extract-hold dest type still Hold for blood→DNA→Qubit E2E |
| **P5** | Instrument import configuration | Processing (parsers shipped) | **CLOSED this cycle.** Independent of P1 |

P1 is the **lake**. P2–P5 are specified here so reviews see the path. Coding agents implement **one phase per PR**. Coding stays Grok Build. Not IC50.

## 4. Functional requirements

### 4.1 P1 — Asked-for (lake)

| ID | Requirement |
|----|-------------|
| **RQ-AF-1** | After receive, a user with `test:assign` and sample/project access can record **asked-for** rows: `sample_id`, `analysis_id`, `tat_days` (integer ≥ 1), optional `params`. **L1:** one action may target a **set** of samples (same analysis + TAT + params); API still one row per sample. Copy: requested analysis, never “assign test” / “start work.” No Start/Execute on `requested`. Asked-for ≠ Test assign. |
| **RQ-AF-2** | Asked-for does **not** create Test, Result, Process, Experiment, LimsRun, or work_order rows. No second workflow engine. No silent Order→work. |
| **RQ-AF-3** | UI is **not** `/receive`. Surface: Sample Mgmt item **Asked-for** (`/asked-for`) plus a section on sample detail. Receive never sends `analysis_ids`. Non-empty `analysis_ids` still **422**. Classic `/tests` type-a-number stays. |
| **RQ-AF-4** | Active uniqueness: one open asked-for per `(sample_id, analysis_id)`. Duplicate → **409**. |
| **RQ-AF-5** | Status: `requested` \| `routed` \| `cancelled`. P1 only writes `requested` / `cancelled`. P1 must **not** write status `routed`. `routed` is P2. |
| **RQ-AF-6** | **Three-layer param bind** (see also RQ-WO-11). `asked_for.params` are **order capture**, not the Test snapshot. (1) **Catalog:** `analysis_param_defs` belong to an **analysis** (`config:edit`). Setup person picks which keys exist and which are **required** (boolean). **No “required if …” rules** (OQ-AF-6). (2) **Order:** user fills `asked_for.params` JSON for that analysis (same keys). (3) **Execute (P2):** LimsRun start copies that JSON onto **`tests.asked_for_params` and freezes**. P1 may ship with zero defs = empty object only. Unknown key or missing required def → **422**. Param **units** live on the def (`unit` display), not on `results`. Fitted IC50 / Hill / CLint / fu / % remaining are **results**, not params. Example keys/values: [analysis-param-defs working note](../../decision-logs/2026-08-28-analysis-param-defs.md) — **not seed**. |
| **RQ-AF-7** | Write/cancel AuthZ = `test:assign` + **dual-belt `has_project_access`** (same helper as create). Client role cannot create. Mutate routing/config is **not** this permission. |
| **RQ-AF-8** | `GET /asked-for` `list()` must **dual-belt `has_project_access`** (same as create), **not RLS-only**. `asked_for` still FORCE RLS via sample → project. `analysis_param_defs` RLS may be any logged-in user; mutate stays `config:edit` in the router. No new AuthZ path / permission. |
| **RQ-AF-9** | List views: by sample, by project, by analysis, status `requested`. |
| **RQ-AF-10** | Cancel is allowed while `requested`. Cancel after `routed` is P2 (must cancel or complete the work_order first). |
| **RQ-AF-11** | Type eligibility is **P2 (L2 / OQ-WO-4)**, not this PR. Gate is on **steps** (experiment and LimsRun), not on the analysis. |

### 4.2 P2 — Routing map + work_order

| ID | Requirement |
|----|-------------|
| **RQ-WO-1** | Entity name is **`work_order`** (WO-1). |
| **RQ-WO-2** | Routing map row: **analysis + TAT day range + ordered `process_definition[]`**. Admin selects no sample type. UI must preserve process order and display the first process plus its first ordered Experiment/LimsRun allow-list. Prefer derive-on-read; any stored display copy refreshes on sequence/first-step change. |
| **RQ-WO-3** | Mutate routing map = **`config:edit` only**. Empty map yields zero acceptable routes: **422**, no mint. |
| **RQ-WO-4** | Map save **409**s only when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold. Extract-first and Qubit-first for the same TAT are legal. Route **409**s when two saved rows both accept the sample’s current type. No silent `first()`. |
| **RQ-WO-5** | Map save performs no sample-type gate or chain-wide AND. Route compares current type with the **first process’s first ordered Experiment/LimsRun** allow-list for every analysis + TAT candidate. Zero acceptable rows returns **422** and mints nothing; type mismatch uses `route_sample_type`. Later processes/steps gate current type only when started; empty fails closed then. Dest-type Hold remains out. |
| **RQ-WO-6** | Tech hits **Route**; asked-for save does not mint work. Exactly one acceptable row snapshots its ordered `process_definition[]`, mints one work order, and sets asked-for `routed`. Zero → 422; two saved rows that both accept current type → 409. P1 never writes `routed`. |
| **RQ-WO-7** | Route is `test:assign`; process starts use `experiment:manage`. Work-order start instantiates **the first process only**. A later start advances to the next snapshot definition in order; Route does not mint a process-of-processes. UI shows process and step order. Each later start gates current type then. |
| **RQ-WO-11** | **L3 / SC5 / A5:** Asked-for `params` are **order capture**. At **LimsRun start**, insert Test if missing; copy `asked_for.params` → `tests.asked_for_params` (jsonb) and **freeze**. **First start wins** — do not overwrite `asked_for_params` on an existing Test. Tech does not re-type cell line / method params to run the assay. Empty defs → `{}`. Not receive, not publish, not result columns. P1 does not write the Test snapshot. |
| **RQ-WO-8** | Work_order does **not** create Tests. Tests are created at **LimsRun start** (WO-7). Publish / `PATCH complete` **422s the whole run** if any Test is missing — including **empty plan** (0 data rows, never calls `ensure_test`). Stay unpublished. Zero Results. Bounce swallow-into-`plan.errors` and mark published. No ensure-on-publish find-or-create. Start-mint is not WO-7 Pass. |
| **RQ-WO-9** | Non-instrument analysis: LimsRun with `analysis_id` required; manual results OK; parser requires instrument XOR CRO (WO-4). |
| **RQ-WO-10** | Work_order status: `queued` \| `in_progress` \| `completed` \| `cancelled`. |

### 4.3 P3 — Results persist lock

| ID | Requirement |
|----|-------------|
| **RQ-RES-1** | Typed token lands in `results.reported_result`. `raw_result` **may** copy. **`qualifiers` is the existing UUID FK** to Result Qualifiers (`<LOD`, `ND`); **NULL** for a clean number. Do **not** write JSON into `qualifiers` (SC1). |
| **RQ-RES-2** | Unit comes from `analytes.units_default`. If missing → **422**. Do **not** add `results.unit_id`. No unit picker. |
| **RQ-RES-3** | Two writers on the same Test (classic entry vs LimsRun publish) → **409**. |
| **RQ-RES-4** | P3 does not mint Tests at asked-for or receive. |

**North star (not this spine’s job):** SOP + example execution files → vectorize → MCP drafts process + parser. [ai-sop-north-star](ai-sop-north-star.md). P4/P5 below are **interim** and must not restate “admin authors parsers.”

### 4.4 P4 — SOP + AI → process definition (interim)

| ID | Requirement |
|----|-------------|
| **RQ-SOP-1** | Human **Apply** of a SOP parse job creates (or updates a draft) **`eln_process_definition`** with typed steps (`eln_experiment` \| `lims_run`), not only an ExperimentTemplate. |
| **RQ-SOP-2** | Apply is **never** silent auto-activate. User reviews and saves. |
| **RQ-SOP-3** | Optional: Apply may create an **inactive** `data_parsers` draft from extracted `parser_config`. Production import stays deterministic. |
| **RQ-SOP-4** | **L5:** Does **not** ship extract-hold dest type. Blood → DNA daughter → Qubit on the daughter remains **Hold**. Apply success copy must not claim that path is runnable. |
| **RQ-SOP-5** | No SOP PDF bodies in git. No IC50. |

### 4.5 P5 — Parser activate (interim)

North star authors parsers at SOP via MCP. Until that ships, P5 is **review / dry-run / activate** of drafts — not “admin invents parser JSON.”

| ID | Requirement |
|----|-------------|
| **RQ-IMP-1** | Catalog remains analysis + (instrument XOR CRO). Mutate/activate = `config:edit`. |
| **RQ-IMP-2** | Dry-run harness on example + test files; activate only if tests pass. |
| **RQ-IMP-3** | Day-to-day import = no LLM (G4). Authoring-time AI belongs to [ai-sop-north-star](ai-sop-north-star.md), not a separate admin “wizard.” |
| **RQ-IMP-4** | Sidebar shows **active** parsers; activate = `config:edit` (FW-1b). |
| **RQ-IMP-5** | Not CMMS, not executable parsers. |

## 5. Non-goals (all phases)

- Reopen CORE receive / analysis picker on `/receive` / non-empty `analysis_ids` accepted (still **422**)
- Mint Tests / Results / Processes / Experiments / LimsRuns / work_orders at asked-for save
- Silent Order→work
- Second workflow engine beside Process / Experiment / LimsRun
- Type × analysis eligibility in P1 (L2 is P2)
- P1 write of status `routed`
- Equate asked-for with Test assign (README / copy)
- Treat P1 `params` as the Test snapshot (they are **order capture**; freeze is WO-7 / P2)
- Hide classic `/tests` type-a-number (WO-4 stays)
- Rename `projects` → `orders`
- Intake-profile engine, bulk intake UI, wizard revival
- Compound registration / lots (WO-5/6)
- Materials module, multi-tenant, IC50 / dose-response
- Extract-hold dest type (own stem; P4 must not pretend it is done)

## 6. Bounce (any phase PR)

1. Analysis picker on `/receive`
2. Test / Result / Process / Experiment / LimsRun / work_order created at asked-for save
3. Ensure-on-publish invents a Test
4. Map save 409 on overlapping TAT **alone** (must also overlap first-step allow-lists)
5. Empty routing map mints work_orders
6. LLM on production file import
7. SOP Apply auto-activates a live process without a human save
8. Client role writes asked-for / routing / parsers
9. New `results.unit_id`
10. Silent Order→work
11. `GET /asked-for` `list()` RLS-only (no `has_project_access` belt)
12. README / copy that equates asked-for with Test assign
13. P1 write of status `routed`
14. Type × analysis eligibility in the P1 PR (L2 is P2)
15. Start / Execute CTA on asked-for
16. P1 `params` labeled or stored as the Test snapshot
17. Process-of-processes / `uuid[]` chain documented as unordered bag / completing N starts N+1 / `start` of `[0]` only
18. Overwrite `asked_for_params` on an existing Test
19. Publish skip-and-complete when a Test is missing (swallow `ensure_test` 422 **or** empty plan / 0 data rows that never calls `ensure_test`)
20. Admin-only Route / `experiment:manage` on Route / RLS that hides catalog-visible SOP def/steps (`created_by` or `has_experiment_access()`)
21. Map save or Route that ANDs one type across later processes or steps
22. Admin-authored routing-map sample type or any create-form type picker
23. Route UI that hides/reorders `process_definition[]`, or Start that instantiates the whole sequence at once
24. Silent `first()` when two saved rows both accept current type
25. Map save 409 that blocks extract-first vs Qubit-first for the same analysis and TAT

## 7. Acceptance (product)

| ID | Criterion |
|----|-----------|
| AC-P1-1 | Receive a sample → record ELISA asked-for → zero Tests, zero work_orders |
| AC-P1-2 | Duplicate asked-for same sample+analysis → 409 |
| AC-P1-3 | User without project access → **403** on create **and** on `GET /asked-for` `list()` (dual-belt `has_project_access`, not RLS-only) |
| AC-P1-4 | Receive non-empty `analysis_ids` still **422** |
| AC-P2-1 | Exactly one acceptable row mints one work order with ordered `process_definition[]`; asked-for = routed |
| AC-P2-2 | No acceptable map row → **422**, no work order; UI says configure routing |
| AC-P2-3 | Ordered `process_definition[]` is preserved. Route: zero acceptable rows → 422; two saved rows that both accept current type → 409; exactly one snapshots the route. Start instantiates first process only; later processes start later and gate current type then |
| AC-P2-4 | alice (`test:assign`) Routes a mapped def created by admin and can read its steps; not admin-only; not `experiment:manage` on Route; not `has_experiment_access()` as the SOP-read belt |
| AC-P2-5 | Publish / `PATCH complete` with a missing Test (including empty plan / 0 data rows after Test delete) → 422 the whole run, stay unpublished, zero Results |
| AC-P2-6 | Map create has no sample-type selector; UI shows ordered processes and derives first-process / first-step types. Map save 409s only on overlapping TAT **and** overlapping first-step allow-lists; extract-first vs Qubit-first for the same TAT saves |
| AC-P3-1 | Type `12.3` with units_default set → `reported_result` set; `qualifiers` NULL unless a list qualifier is chosen |
| AC-P3-2 | Missing units_default → 422, no row |
| AC-P4-1 | Apply creates process definition with at least one step; template-only Apply is gone as the success path |
| AC-P5-1 | Activate parser after dry-run pass; import a file with LLM disabled |

## 8. UAT

Script: `UAT_Scripts/uat-post-receive-work-spine.md` (P1 cases). **P1 Pass**; merged PR 81. Do not use retired `uat-sample-accessioning.md`.
