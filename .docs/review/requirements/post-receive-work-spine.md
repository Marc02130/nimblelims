# Requirements: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Spec **C2 Fail** on `02fe95f` is signed history (Deiter C1 **Pass**, dest mint Hold **Pass**). Leadership Confirmed that click — C1/C2 are **not** unsigned. **P1 shipped** on `main` (PR 81; UAT Pass). **Hold product merge.** Docs Confirm `84d2810` is not a new execute and not the click SHA. The dest-type split is **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter). UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute). Dest-follow execute txn is **`1572071`**. AC-P2-C2 and AC-P2-C3 are two unsigned clicks. Do **not** teach `570bbc0` as a product execute SHA. Same dest type = **same sample, additional container**; `_follow_destination_in_process` may retarget `container_id` only on that path. Different dest type = **new derivative sample** in a new container (`parent_sample_id`); the parent **Sample row** stays with its original type, Tests, and parent-type work. Type-changing execute mints and joins the destination sample + destination container pair on `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction; only that destination pair continues on the process. Route / Start / map-save mint zero daughters. Dest mint Hold is lifted only for type-changing execute. Do **not** write C2 or C3 Pass, rewrite the parent `sample_type`, or retarget the parent Sample onto the destination tube. C2 and C3 / extract-hold UAT 1.7 remain two clicks. **PATCH is not a path.** Deiter’s dest mint Hold **Pass** and `9342439` Dest-type mint Hold are Start-extract Blood / **0 DNA** history, not a live ban. OQ-WO-6 and freeze skip stay OPEN. Signed AC-P2-9..11: `9342439`. **Overall P2 unsigned / not Pass.** Not IC50.
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
5. Architecture / UI / Spec **Accept with conditions** on P2 @ `8cfa2a9`. P1 UAT Pass; PR 81 merged. Hold merge until UAT. Not IC50.
6. **Receive freeze:** non-empty `analysis_ids` still **422**.
7. Operator how-tos live in git-tracked [`/manuals/HOWTO.md`](../../../manuals/HOWTO.md). Do not put operator manuals back under `.docs/review/manuals/`.
8. **P2 ordered route (Leadership / Heidi / Günter; AC-P2-9..11 Pass on `9342439`; prior signed on `8cfa2a9`):** Route snapshots the ordered list, **zero Tests**. First Start = process[0] / `chain[0]` only — **Tobias-signed Pass** (`8cfa2a9`). Empty Route **422** Pass. Map overlap **409** / blood+qPCR **201** (not AND) Pass (`8cfa2a9`). Later-step type-gate **Met** on `9342439`. Deiter clicked `0077` at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Dest-follow execute on `1572071` is **unsigned** until Tobias (C2/C3 numbered on `570bbc0`). Do not teach dest-follow as shipped.
9. **WO-7 publish (Tobias-signed Pass @ `8cfa2a9` and history @ `b005cfe`; hold overall P2 QA):** refuse the **whole** publish (**422**) if a Test is missing — stay unpublished, zero Results. Do **not** fold first-start freeze into that Pass.
10. **Hans freeze (classic skip still OPEN / unsigned on `8cfa2a9`):** `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`. A write of `{}` onto `99b692d3` is not a skip Pass. **OQ-WO-6:** an earlier LimsRun must **not** share the asked-for `analysis_id` (extract is not a special assay).
11. **P2-4 / Heidi belt:** Route is `test:assign` and must **read** the mapped def/steps. Do not put `experiment:manage` on Route. **`0074`:** `is_admin() OR has_experiment_access()` is not catalog-visible. Mutate stays `config:edit`. Instantiate stays. **Still open** on `8cfa2a9`.
12. **No sample-type picker (Tobias-signed Pass on `8cfa2a9` — UI click-save):** ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409**. Empty Route **422** Pass. Two-accept **409** unsigned that SHA.
13. **Earlier LimsRun `analysis_id` (OQ-WO-6 stays OPEN — Leadership Confirm R2-3; Rolf/Deiter/Hans/Heidi/Günter):** Earlier LimsRun must **not** share asked-for `analysis_id`. Do not teach extract-as-special-assay. Type gates catch blood-on-Qubit. Blood→DNA is a derivative (`parent_sample_id`); dest mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. WO-7 mints Test at every LimsRun start for `(cohort sample, run.analysis_id)`. Any **earlier** LimsRun that reuses the asked-for panel analysis freezes that Test on the parent. Earlier LimsRun = own analysis or experiment-only.
14. **After `8cfa2a9` (Round 1 Leadership Confirm — Rolf/Deiter/Hans/Heidi/Günter; Round 2 Leadership Confirm R2-1…R2-4):** no map analysis picker. A route **may have multiple LimsRun analyses**. Asked-for assay → any route that **contains** that analysis. Map 409 = TAT ∩ first-step types ∩ LIMS Run analysis **sets**. Map 422 when process *x* emerging type is not accepted by *x+1* (**map-save only**). Dest mint Hold on `9342439` is Start-extract history, not a live ban. Live SHA `9342439` — **Tobias-signed AC-P2-9..11 Pass**; restamp notes honesty, **not** a merge vote. Freeze skip OPEN; OQ-WO-6 stays OPEN; parser at import; Route stays `test:assign`; overall P2 unsigned. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
15. **C2 Fail on `02fe95f` (Deiter click; Leadership Confirm) — signed history:** C1 **Pass**. C2 **Fail** — C1/C2 are **not** unsigned. Execute minted dest (`_execute_transfer` always inserts a new Sample) and never wrote the same-sample dest container onto `eln_process_samples`. `_join_minted_destination` and `_release_source_from_process` both **no-op** unless `entry.process_step_id` is set. Emptied-source assign **201** is leftover Contents at amount 0 / leftover process-join — **not** dest-follow. Later Start via `_continuing_assignments` rode the emptied parent; results would not be attributable to the dest vessel. **PATCH is not a path.** Dest mint **Hold Pass** is a different punch (still Blood, **0 DNA**; a new Sample with `dest_sample_type` is **not** this C2 fix). OQ-WO-6 and freeze skip stay OPEN. Hold merge. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md), “Leadership Confirm of Deiter’s Contents click”.
16. **Leadership Confirm — mint-only-at-execute (Rolf / Deiter / Hans / Heidi / Günter); dest-type split; C2/C3 numbered unsigned on `570bbc0`; execute txn is `1572071`:** same dest type = same sample, additional container; `_follow_destination_in_process` may retarget `container_id` only on that path. Emptied-source assign is **422** and later Start follows that dest container. Different dest type = new derivative Sample in a new container (`parent_sample_id`); only the parent Sample row stays, preserving its original type, Tests, and parent-type work. Type-changing execute mints and joins the destination pair and marks the inbound source assignment `removed` in the execute transaction; only the destination pair remains on this chain. Route / Start / map-save / asked-for mint **zero** daughters. Plan dest type is catalog intent, **not** a Sample. Receive still mints identity + first vessel — that is **not** dest mint. Dest mint Hold is lifted only for type-changing execute. C2 (same dest type) and C3 / extract-hold UAT 1.7 (different dest type) remain two execute clicks. In code on `1572071`; C2/C3 numbered on `570bbc0` and not QA-clicked. `570bbc0` does **not** inherit `1572071` C2 Pass or Fail. After execute, the process-sample is **only** that execute-minted dest (Günter). **No dest sample/container until aliquot/pool execute.** Do **not** write C2 or C3 Pass, and do not teach type-changing dest as parent `container_id` retarget. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md), “Leadership Confirm — mint-only-at-execute”.

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
WORK_ORDER (P2)  ordered process_definition[]     THIS PACKET
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
| **P2** | Routing + work_order | Test ordering / processing | Spec **C2 Fail** on `02fe95f` is signed history. Deiter C1 **Pass**, dest mint Hold **Pass**. Dest-follow execute SHA **`1572071`**; C2/C3 numbered unsigned on `570bbc0`. Do **not** teach `570bbc0` as a product execute SHA. OQ-WO-6 and freeze skip stay OPEN. `9342439` AC-P2-9..11 Pass stays signed history. Overall P2 **unsigned**. |
| **P3** | Results persist | Results entry | **CLOSED.** After P1 (may parallel P2 if Test exists via LimsRun or classic) |
| **P4** | SOP+AI → process definition | Processing (not MVP bar) | **CLOSED.** P2 process definition is the Apply target; blood→DNA→Qubit execute remains OOB and unsigned in this packet |
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
| **RQ-WO-2** | Routing map keys: **TAT day range + ordered `process_definition[]`**. No analysis or sample-type picker. A route **may contain multiple LimsRun analyses**. Asked-for assay matches **any** route that **contains** that analysis (plus first-step type + TAT). Route snapshots the ordered list, **zero Tests**. First Start instantiates process[0] / `chain[0]` only. Later Start following dest is the lock on **`1572071`**, **unsigned** until Tobias (C2/C3 numbered on `570bbc0`). Deiter C2 **Fail** on `4671ba8` / `02fe95f` is signed history — do not teach dest-follow as shipped. |
| **RQ-WO-3** | Mutate routing map = **`config:edit` only**. Empty map yields zero acceptable routes: **422**, no mint. |
| **RQ-WO-4** | Map save **409**s only when overlapping TAT, overlapping first-step allow-lists, **and** overlapping LimsRun analysis **sets** all hold. Two extract routes, same TAT and inbound types, ELISA vs NGS, both save. Route **409**s when two saved rows both accept this type **and** this asked-for analysis. No silent `first()`. |
| **RQ-WO-5** | Type gate is on process-definition steps for both `eln_experiment` and `lims_run`. Route compares current type with process[0]’s **first** Exp/LimsRun allow-list. Zero acceptable → **422** `route_sample_type`. Later processes/steps gate current type only when started; empty fails closed then. **No sample/container mint until aliquot/pool execute.** Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Plan may declare dest type; dest exists only after execute. Dest type on the plan is catalog intent until execute. P2 only **reads** declared dest for map-save handoff 422. |
| **RQ-WO-6** | Tech hits **Route**; asked-for save does not mint work. Eligible maps = TAT + first-step type + asked-for analysis **contained** in the chain. Exactly one acceptable row **snapshots the ordered list, mints one work order, zero Tests**, and sets asked-for `routed`. Zero → 422; two saved rows that both accept this type and this analysis → 409. P1 never writes `routed`. |
| **RQ-WO-7** | First Start = process[0] / `chain[0]` only (`experiment:manage`). Later Start following dest container after execute (`_continuing_assignments`) is the lock on **`1572071`**, **unsigned** (C2/C3 numbered on `570bbc0`). Bounce later Start following the parent/source tube or bare `wo.sample_id` when dests exist. Bounce **first Start minting later processes or their Tests**. Route is `test:assign`. **P2-4:** Route must **read** the mapped def/steps catalog-visible. Do not require `experiment:manage` on Route. **`0074` is not catalog-visible.** Mutate stays `config:edit`. |
| **RQ-WO-12** | **0077 C2 Fail (`02fe95f`, Deiter click; Leadership Confirm — not unsigned) is signed history.** Assignment is the **tube in hand**. C1 **Pass**: **422** if no vessel or 2+ without a pick; receive-tube **201**. C2 **Fail**: dest not on the process; emptied-source assign **201**; later Start rode the emptied parent; **PATCH is not a path**. Unsigned C2 numbered on **`570bbc0`**; execute **`1572071`** is same-type only: same dest type = same sample, additional container; `_follow_destination_in_process` may retarget `container_id` only on that path; emptied-source assign **422**. Unsigned **C3** numbered on `570bbc0`; execute **`1572071`** is the different-dest-type click: new derivative sample in a new container (`parent_sample_id`); the parent Sample row stays without a type rewrite or destination-container retarget. In both paths, execute adds the destination sample + container pair to `eln_process_samples` and marks the inbound source assignment `removed`. Dest mint Hold is lifted only for type-changing execute. Deiter Hold **Pass** remains Start-extract Blood / 0 DNA history. Test identity stays `(sample, analysis)`. Do not write C2 or C3 Pass. **Fail C3** if dest tube lands on the blood Sample, parent `container_id` is retargeted, or later Start follows blood. |
| **RQ-WO-11** | **L3 / SC5 / A5 / Hans:** Asked-for `params` are **order capture**. `if test: continue` is **not** a freeze. At **LimsRun start** for the asked-for analysis, **write** `asked_for.params` → `tests.asked_for_params`. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`. **OQ-WO-6:** any earlier LimsRun must **not** reuse the asked-for `analysis_id` (extract is not special). Do not claim freeze closed. Live SHA `9342439` — AC-P2-9..11 Pass; overall P2 unsigned. |
| **RQ-WO-8** | Work_order / Route does **not** create Tests. Tests are created at **LimsRun start** (WO-7) for the process being started. First Start must not mint Tests for later processes. Publish / `PATCH complete` **422s the whole run** if any Test is missing — including **empty plan**. Stay unpublished. Zero Results. |
| **RQ-WO-9** | Non-instrument analysis: LimsRun with `analysis_id` required; manual results OK; parser requires instrument XOR CRO (WO-4). Parser is chosen at **import**, not on the process step. **OQ-WO-6:** an earlier LimsRun must not share the asked-for `analysis_id`. |
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
| **RQ-SOP-4** | **L5:** SOP Apply does not stamp extract-hold execute. Blood → DNA daughter → Qubit on the daughter remains **OOB and unsigned** in this packet. Apply success copy must not claim that path is UAT-verified. |
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
- Extract-hold dest type / dest **mint** as a P2 C2 result (own stem: aliquot/pool **execute**, not plan submit). Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Dest exists only after execute. P4 must not present that execute as UAT-verified.

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
17. First Start minting later processes or their Tests (the ordered list itself is the lock)
18. Treat classic `/tests` NULL or default `{}` as a freeze; `if test: continue` is not a freeze. Teach skip-on-frozen-`{}` as a freeze — classic default `{}` and frozen `{}` are the same JSON, so `{}` is ambiguous until classic `/tests` leaves NULL or a freeze marker exists. An earlier LimsRun sharing the asked-for `analysis_id` (OQ-WO-6).
19. Publish skip-and-complete when a Test is missing
20. Admin-only Route / `experiment:manage` on Route / RLS that hides catalog-visible SOP def/steps (`created_by` or `has_experiment_access()`)
21. Map save or Route that ANDs one type across later processes (later **steps** of the process being started still type-gate at start)
22. Admin-authored routing-map sample type or any create-form type picker
23. First Start that instantiates the whole sequence at once
24. Silent `first()` when two saved rows both accept current type
25. Map save 409 that blocks extract-first vs Qubit-first for the same analysis and TAT
26. An earlier LimsRun in the chain sharing the asked-for `analysis_id` (OQ-WO-6; extract is not a special assay)
27. Dest mint at execute (new DNA Sample / dest-type rewrite) treated as the C2 fix. Equivalent aliquot is same sample, new container.
28. Assign that omits `container_id` when vessel count is 0 or 2+. Emptied-source assign **201** (Contents amount 0) — leftover of `02fe95f`; live lock on `1572071` is **422**. Later Start that follows inbound parent / `wo.sample_id` when dests exist. PATCH of `eln_process_samples` as dest-follow. Join/release that no-ops without `entry.process_step_id` on `02fe95f`.

## 7. Acceptance (product)

| ID | Criterion |
|----|-----------|
| AC-P1-1 | Receive a sample → record ELISA asked-for → zero Tests, zero work_orders |
| AC-P1-2 | Duplicate asked-for same sample+analysis → 409 |
| AC-P1-3 | User without project access → **403** on create **and** on `GET /asked-for` `list()` (dual-belt `has_project_access`, not RLS-only) |
| AC-P1-4 | Receive non-empty `analysis_ids` still **422** |
| AC-P2-1 | Matching route snapshots ordered `process_definition[]`, mints one work_order, **zero Tests**; asked-for = routed |
| AC-P2-2 | Zero acceptable map row → **422**, no work order |
| AC-P2-3 | Two saved rows that both accept current type → 409; no silent `first()` |
| AC-P2-4 | alice (`test:assign`) Routes a mapped def created by admin and can read its steps; not admin-only; not `experiment:manage` on Route; not `has_experiment_access()` as the SOP-read belt |
| AC-P2-5 | Publish / `PATCH complete` with a missing Test → 422 the whole run, stay unpublished, zero Results |
| AC-P2-6 | Map create has no sample-type selector; derives first Exp/LimsRun types of process[0]. Map save 409s only on overlapping TAT **and** overlapping first-step allow-lists |
| AC-P2-7 | First Start = process[0] only, no Tests for later processes. Later Start following dest container after execute is the lock on **`1572071`**, **unsigned** until Tobias (C2/C3 numbered on `570bbc0`) |
| AC-P2-8 | Classic `/tests` leaves `asked_for_params` NULL, or a freeze marker exists. Until then `{}` is ambiguous (not a verified freeze skip). Extract LimsRun does not share asked-for `analysis_id` |
| AC-P2-C1 | Assign is the tube in hand: `container_id` required. 0 vessels or 2+ without a pick → **422**, lab-readable, no silent pick. Receive tube assign → **201** with `container_id`. **Pass** on `02fe95f` (Deiter history; not restamped). |
| AC-P2-C2 | **Fail** on `02fe95f` (Deiter history). **Unsigned** (numbered on `570bbc0`; execute `1572071`): same dest type → same sample, new container; dest on process; emptied source **422**; Later Start follows dest container. Not Blood→DNA. |
| AC-P2-C3 | **Unsigned** (numbered on `570bbc0`; execute `1572071`): dest type DNA → new Sample + container (`parent_sample_id`); parent stays Blood; dest pair is the only active process assignment. Same click as extract-hold 1.7. |
| AC-P3-1 | Type `12.3` with units_default set → `reported_result` set; `qualifiers` NULL unless a list qualifier is chosen |
| AC-P3-2 | Missing units_default → 422, no row |
| AC-P4-1 | Apply creates process definition with at least one step; template-only Apply is gone as the success path |
| AC-P5-1 | Activate parser after dry-run pass; import a file with LLM disabled |

## 8. UAT

Script: `UAT_Scripts/uat-post-receive-work-spine.md` (P1 cases). **P1 Pass**; merged PR 81. UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute); dest-follow execute txn **`1572071`**: AC-P2-C2 and AC-P2-C3 **unsigned**. Do not use retired `uat-sample-accessioning.md`.
