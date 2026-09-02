# Requirements: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Spec **C2 Fail** on `02fe95f` is signed history (Deiter C1 **Pass**, dest mint Hold **Pass**). Leadership Confirmed that click — do not rewrite it. **P1 shipped** on `main` (PR 81; UAT Pass). P2 on `main` (`5040f2d`). **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). On live SHA **`570bbc0`**, Deiter’s C1/C2/C3 execute click is **Met for Lab Ops identity only**: same-type plate, DNA new Sample, and Later Start following the destination. It is not Tobias QA Pass. Dest-follow execute joints remain **`1572071`** and have **no Tobias Result**; Tobias’s QA restamp stays unsigned until execute Results land on the same numbered ACs. The two execute grains are **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter): same dest type = **same sample, additional container**; different dest type = **new derivative sample** in a new container (`parent_sample_id`) while the parent Sample row stays Blood. Route / Start / map-save / asked-for mint zero daughters. Receive identity + first vessel is not dest mint. 400 `source_amount_null` is a fixture gap: receive often leaves Contents amount NULL, so set a tracked amount so execute can transfer. Emptying is not required. **PATCH of `eln_process_samples` is not a path.** `9342439` Hold is Start-extract Blood / 0 DNA history, not a ban on C3. Freeze skip and Route two-accept 409 stay OPEN. **OQ-WO-6 for extract CLOSED** (Leadership Confirm 2026-08-31). Closeout **1.4 / OQ-WO-8** is **Closed** (**Full Leadership Confirm**; Quantified DNA; Qubit is the asked-for LimsRun; named asked-for LimsRun slot, not contains-Qubit). **No overall P2 Pass.** Not IC50.  
**Leadership Confirm (2026-08-31, Rolf / Deiter / Hans / Heidi / Günter):** extract is a **process** (experiment / aliquot-pool execute; derivative dest), not a LimsRun; no asked-for `analysis_id` on extract; exactly **one** LimsRun in the route has the asked-for `analysis_id` (assay step); extract (process) and Qubit (supporting LimsRun) may sit in the chain; map-save / Route **422** if asked-for analysis appears 0 or 2+ times among LimsRuns; two ELISA LimsRuns refused. Hans’s 1-count-on-extract freeze punch is closed. Keep: one asked-for per process instance; **no route branching** — WGS asked-for on blood owns WGS params (extract → seq); C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up (own params); freeze skip OPEN. Do not rewrite `9342439`. Tobias C2/C3 unsigned. Hold merge. Not IC50.
**Leadership Confirm (Rolf, Marc, 2026-08-31):** Qubit / Nanodrop / etc. are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …). Sequencing is an example, not the only case. Other `analysis_id`s, own Tests, own params freeze. Asked-for analysis appears **once**, on the assay LimsRun. Extract stays a process. Do not invent a second asked-for for QC. Do not put Nanodrop on extract.
**Marc lock (2026-09-01, pending Leadership overwrite):** Care about the asked-for only. Extracted DNA ask = DNA tube (process however; zero assay LimsRuns legal — **1.4**). Sequencing ask with blood = sequencing is the ask; extract is route machinery. One assay LimsRun when the ask is an assay. Do not forever-ban extract-as-LimsRun. OQ-WO-6 extract close stays in spirit for the common path. Freeze skip NULL is **Tobias Pass** on `bf51b19` (older freeze skip OPEN in room locks below is superseded — do not restamp those walls). **OQ-WO-7 OPEN / AC unsigned** until Tobias stamps. Leftover **`9f86d14`** on **`80f054b`** **is** this Grok Build work. **Do not recode.** Remaining work is **Tobias**. Overall P2 unsigned. Not IC50. `9342439` / `02fe95f` untouched.
**Leadership Confirm (2026-09-01, Rolf / Deiter / Hans / Heidi / Günter):** **ELISA is not on DNA** (wrong matrix) — do not hang ELISA on the DNA dest after C3. Same blood Sample **second tube (Contents)** may carry its **own asked-for and route**; two blood tubes → two process assignments (`container_id`); ELISA route and WGS/extract stay apart. Do **not** teach “extract can never be a LimsRun” as a forever ban (Hans: do not hang asked-for assay `analysis_id` on extract). **Extracted DNA asked-for can have Qubit/Nanodrop**; extract-as-instrument LimsRun is later. **OQ-WO-6 still:** asked-for `analysis_id` once on the assay LimsRun, not extract. **OQ-WO-7 stays OPEN:** blood WGS → C3 DNA → WGS start freezes `{library_kit: …}`, not `{}` / not Qubit params. Standing UAT rule: after two attempts on the same issue, next click needs written “what we are testing and why.” Not IC50. Do not rewrite `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.
**Science (2026-09-01):** Per-AC on `bf51b19` Pass. Overall P2 stayed unsigned. Merged (`5040f2d`) with **OQ-WO-7 OPEN**. Leftover **`9f86d14`** on **`80f054b` is** the Grok Build work. **Do not recode.** Remaining work is **Tobias**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. Do not invent Tobias Pass. Not IC50.
**CEO Accept (Rolf, 2026-09-01):** Accept Hans’s written what/why as **AC-P2-OQ-WO-7** before Tobias. “Grok Build codes first” is **done** (`9f86d14` on `80f054b`). Remaining work is **Tobias**. Result unsigned. OQ-WO-7 stays **OPEN / AC unsigned** until Tobias stamps. Do not rewrite `bf51b19`. Not IC50.
**Tobias Result (2026-09-01):** **AC-P2-OQ-WO-7 Pass** on `80f054b`. Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** (WO asked-for same `analysis_id`, else parent lineage, else `{}`) **was not recoded.** **OQ-WO-7 Closed.** Overall P2 unsigned. Older OPEN walls above are history — do not restamp. Do not rewrite `bf51b19`. Not IC50.
**CEO Confirm 1–6 (Rolf, 2026-09-02) — closeout 1.4 / OQ-WO-8 (1–6 stands):** Quantified DNA is an assay ask (data); Qubit is the asked-for LimsRun (exactly one). Wear existing Qubit `analysis_id`; do **not** mint a second catalog analysis named Quantified DNA. Test `(DNA, Qubit)` is the ask. Other QC may sit (own analysis_id / Test). Extract stays experiment; no boolean Result. Old 1.4 (zero LimsRuns) **struck**. **422 on 0 LimsRuns is right.** WGS/WES/ELISA: Qubit stays process QC. Tube-only DNA later SKU. Named asked-for LimsRun slot was a punch pending Leadership Confirm on that fold (not part of 1–6).
**Full Leadership Confirm (2026-09-02, Rolf / Deiter / Hans / Heidi / Günter) — OQ-WO-8 Closed:** Named-slot is no longer pending. Map / Route **names the asked-for LimsRun slot**. Eligibility is `asked.analysis_id` vs **that slot**, not “any chain that contains Qubit.” A WGS map with Qubit as process QC must **not** steal a Quantified DNA ask (409 / wrong join). Same OQ-WO-7 lookup after C3; **do not recode.** No product code in this fold. Product code may start after this fold is on `main`. Not IC50. Send: [2026-09-01-p2-closeout-1-4-quantified-dna](../../discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md).
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
8. **P2 ordered route (Leadership / Heidi / Günter; AC-P2-9..11 Pass on `9342439`; prior signed on `8cfa2a9`):** Route snapshots the ordered list, **zero Tests**. First Start = process[0] / `chain[0]` only — **Tobias-signed Pass** (`8cfa2a9`). Empty Route **422** Pass. Map overlap **409** / blood+qPCR **201** (not AND) Pass (`8cfa2a9`). Later-step type-gate **Met** on `9342439`. Deiter clicked `0077` at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. On `570bbc0`, Deiter’s C1/C2/C3 execute click is **Lab Ops Met**, not QA Pass; dest-follow joints remain `1572071`. Tobias’s numbered C2/C3 QA restamp has no execute Result yet. Do not teach Lab Ops Met as Tobias Pass.
9. **WO-7 publish (Tobias-signed Pass @ `8cfa2a9` and history @ `b005cfe`; hold overall P2 QA):** refuse the **whole** publish (**422**) if a Test is missing — stay unpublished, zero Results. Do **not** fold first-start freeze into that Pass.
10. **Hans freeze (classic skip still OPEN / unsigned on `8cfa2a9`):** Freeze is **per Test** `(sample, analysis)`. First LimsRun start writes `asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. `if test: continue` is **not** a freeze. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, do **not** close freeze skip and do **not** teach skip-on-`{}` as shipped. A write of `{}` onto `99b692d3` is not a skip Pass. **OQ-WO-6 for extract is CLOSED** (Leadership Confirm 2026-08-31) — freeze skip stays OPEN separately.
11. **P2-4 / Heidi belt:** Route is `test:assign` and must **read** the mapped def/steps. Do not put `experiment:manage` on Route. **`0074`:** `is_admin() OR has_experiment_access()` is not catalog-visible. Mutate stays `config:edit`. Instantiate stays. **Still open** on `8cfa2a9`.
12. **No sample-type picker (Tobias-signed Pass on `8cfa2a9` — UI click-save):** ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409**. Empty Route **422** Pass. Two-accept **409** unsigned that SHA.
13. **OQ-WO-6 extract punch CLOSED — Leadership Confirm (2026-08-31, Rolf/Deiter/Hans/Heidi/Günter):** Extract is a **process** (experiment / aliquot-pool execute; derivative dest), not a LimsRun. Manual or robot does not make it a LimsRun. Extract has **no** asked-for `analysis_id`. Cardinality 1 cannot land on extract. Extract cannot wear ELISA. Hans’s punch (1-count on extract still freezes the panel Test on blood) is **closed**. Strike “extract LimsRun must not share asked-for `analysis_id`.” A route has **exactly one** LimsRun whose `analysis_id` is the asked-for analysis — that LimsRun is the **assay step**. Extract (process) and Qubit (supporting LimsRun, own Test) may sit in the chain. Qubit / Nanodrop are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …; own params freeze). Map-save / Route **422** if asked-for analysis appears 0 or 2+ times among LimsRuns. Two ELISA LimsRuns refused (they would share one Test `(sample, ELISA)` — not QC). Type gates catch blood-on-Qubit. Blood→DNA is a derivative (`parent_sample_id`); dest mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. WO-7 mints Test at LimsRun start for `(cohort sample, run.analysis_id)`. Round 2 R2-3 “stays Open” is history. Freeze skip stays OPEN. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
14. **After `8cfa2a9` (Round 1 Leadership Confirm — Rolf/Deiter/Hans/Heidi/Günter; Round 2 Leadership Confirm R2-1…R2-4 history):** no map analysis picker. A route **may have multiple LimsRun analyses**. Live matching: exactly **one** LimsRun carries the asked-for analysis (assay step). Map 409 = TAT ∩ first-step types ∩ LIMS Run analysis **sets**. Map 422 when process *x* emerging type is not accepted by *x+1* (**map-save only**), **and** map-save / Route **422** when asked-for analysis count among LimsRuns is 0 or 2+. Dest mint Hold on `9342439` is Start-extract history, not a live ban. Live SHA `9342439` — **Tobias-signed AC-P2-9..11 Pass**; restamp notes honesty, **not** a merge vote. Freeze skip OPEN; **OQ-WO-6 extract CLOSED**; parser at import; Route stays `test:assign`; overall P2 unsigned. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
15. **C2 Fail on `02fe95f` (Deiter click; Leadership Confirm) — signed history:** C1 **Pass**. C2 **Fail** — C1/C2 are **not** unsigned. Execute minted dest (`_execute_transfer` always inserts a new Sample) and never wrote the same-sample dest container onto `eln_process_samples`. `_join_minted_destination` and `_release_source_from_process` both **no-op** unless `entry.process_step_id` is set. Emptied-source assign **201** is leftover Contents at amount 0 / leftover process-join — **not** dest-follow. Later Start via `_continuing_assignments` rode the emptied parent; results would not be attributable to the dest vessel. **PATCH is not a path.** Dest mint **Hold Pass** is a different punch (still Blood, **0 DNA**; a new Sample with `dest_sample_type` is **not** this C2 fix). Freeze skip stays OPEN. Hold merge. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md), “Leadership Confirm of Deiter’s Contents click”.
16. **Leadership Confirm — two grains at execute (Rolf / Deiter / Hans / Heidi / Günter):** C2 same dest type = same sample, additional container; inbound assignment `removed` even with leftover volume; Later Start follows that destination. Emptying is not required; amount 0 **422** is an edge, not the AC. C3 different dest type = new derivative Sample in a new container (`parent_sample_id`); parent stays Blood; only the destination pair remains active; Later Start follows DNA. Route / Start / map-save / asked-for mint zero daughters. No destination before execute is intended, not dest-follow Fail. DNA scored as C2 is the wrong AC. Receive often leaves Contents amount NULL: set a tracked amount so execute can transfer; 400 `source_amount_null` is a fixture gap, not dest-follow Fail. Deiter’s C1/C2/C3 execute click on `570bbc0` is **Lab Ops Met**, not Tobias QA Pass. Execute joints remain `1572071`; Tobias restamps these numbered ACs and has no Result yet. `9342439` Hold remains history, not a ban on C3.
17. **Marc lock (2026-08-31) kept; OQ-WO-6 extract overwritten by Leadership Confirm; “join many WOs” overwritten by sequential asked-fors:** (1) One asked-for per process instance — do not teach one process carrying two asked-for assays. (2) Supporting QC = other analyses, own Tests `(sample, analysis)` — Qubit is a supporting LimsRun; extract is a process with no asked-for `analysis_id`. (3) **No route branching this phase.** Route **blood** for WGS (extraction → sequencing); that asked-for **owns WGS params**. C3 execute mints DNA. A **C2 aliquot** of that DNA continues the WGS WO. **WES is a new asked-for on the DNA tube** (owns WES params); that tube is then **aliquoted or used up**. Two asked-fors, two param snapshots, two WOs. Do not teach dest auto-joining a second WO. Do not copy WGS params onto WES. (4) Freeze per Test: first start writes; later start does not overwrite including frozen `{}`; skip-on-`{}` stays OPEN. (5) **OQ-WO-6 for extract CLOSED** — see room lock 13. Click SHA C2/C3 remains `570bbc0`. `9342439` / `02fe95f` untouched. Tobias C2/C3 unsigned. Hold merge. Not IC50.

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
| **P2** | Routing + work_order | Test ordering / processing | Spec **C2 Fail** on `02fe95f` is signed history. On `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**, not QA Pass. Execute joints remain `1572071`; Tobias QA restamp has no C2/C3 Result yet. Freeze skip and Route two-accept 409 stay OPEN. **OQ-WO-6 extract CLOSED** (Leadership Confirm). Keep one asked-for per process; **no route branching** — WGS on blood, C2 DNA aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up. `9342439` AC-P2-9..11 Pass stays signed history. Overall P2 **unsigned**. |
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
| **RQ-WO-2** | Routing map keys: **TAT day range + ordered `process_definition[]`**. No analysis or sample-type picker. A route **may contain multiple LimsRun analyses**. **Leadership Confirm:** extract is a **process** (not a LimsRun). Exactly **one** LimsRun in the route has the asked-for `analysis_id` — that LimsRun is the **assay step**. Extract (process) and Qubit (supporting LimsRun) may sit in the chain. Map-save / Route **422** if asked-for analysis appears 0 or 2+ times among LimsRuns. Route snapshots the ordered list, **zero Tests**. First Start instantiates process[0] / `chain[0]` only. Later Start following dest is on execute joints **`1572071`**. Deiter’s `570bbc0` execute click is **Lab Ops Met**; Tobias QA restamp is unsigned. Deiter C2 **Fail** on `4671ba8` / `02fe95f` stays signed history. |
| **RQ-WO-3** | Mutate routing map = **`config:edit` only**. Empty map yields zero acceptable routes: **422**, no mint. |
| **RQ-WO-4** | Map save **409**s only when overlapping TAT, overlapping first-step allow-lists, **and** overlapping LimsRun analysis **sets** all hold. Two extract routes, same TAT and inbound types, ELISA vs NGS, both save. Route **409**s when two saved rows both accept this type **and** this asked-for analysis. No silent `first()`. |
| **RQ-WO-5** | Type gate is on process-definition steps for both `eln_experiment` and `lims_run`. Route compares current type with process[0]’s **first** Exp/LimsRun allow-list. Zero acceptable → **422** `route_sample_type`. Later processes/steps gate current type only when started; empty fails closed then. **No sample/container mint until aliquot/pool execute.** Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Plan may declare dest type; dest exists only after execute. Dest type on the plan is catalog intent until execute. P2 only **reads** declared dest for map-save handoff 422. |
| **RQ-WO-6** | Tech hits **Route**; asked-for save does not mint work. Eligible maps = TAT + first-step type + asked-for analysis on **exactly one** LimsRun in the chain (assay step). Map-save / Route **422** if that analysis appears **0 or 2+** times among LimsRuns. Two ELISA LimsRuns refused. Exactly one acceptable **map row** **snapshots the ordered list, mints one work order, zero Tests**, and sets asked-for `routed`. Two saved rows that both accept this type and this analysis → 409. P1 never writes `routed`. **Marc lock kept:** a process instance is bound to **one** asked-for row. Do not teach one process carrying two asked-for assays. |
| **RQ-WO-7** | First Start = process[0] / `chain[0]` only (`experiment:manage`). Later Start follows the execute-minted destination through `_continuing_assignments` on joints **`1572071`**. Deiter’s `570bbc0` click is **Lab Ops Met**; Tobias QA restamp has no Result. Bounce Later Start following the parent/source tube or bare `wo.sample_id` when destinations exist. Bounce **first Start minting later processes or their Tests**. Route is `test:assign`. **P2-4:** Route must **read** the mapped def/steps catalog-visible. Do not require `experiment:manage` on Route. **`0074` is not catalog-visible.** Mutate stays `config:edit`. |
| **RQ-WO-12** | **0077 C2 Fail (`02fe95f`, Deiter click; Leadership Confirm) is signed history.** Assignment is the tube in hand. On live `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**, not Tobias QA Pass. Tobias’s restamp remains unsigned. C2 same type: same sample, additional container, destination active on process, inbound assignment `removed` even with leftover volume, Later Start follows destination; a new Sample is C2 Fail. Emptying is not required; amount 0 **422** is an edge. C3 DNA: new derivative Sample + container (`parent_sample_id`), parent stays Blood, destination pair only active assignment, Later Start follows DNA; destination on Blood Sample, parent `container_id` retarget, or Later Start following Blood is C3 Fail. **DNA extract once:** type-changing execute mints the DNA Sample once. **No route branching:** a C2 aliquot of that DNA continues WGS; **WES is a new asked-for on the DNA tube**, which is then **aliquoted or used up**. Do not teach dest auto-joining a second WO. Do not copy WGS params onto WES. No destination at Route/Start and DNA scored as C2 are not failures. Receive often leaves amount NULL; set a tracked amount so execute can transfer. 400 `source_amount_null` is fixture setup, not dest-follow Fail. **PATCH of `eln_process_samples` is not a path.** Hold history is not a ban on C3. |
| **RQ-WO-11** | **L3 / SC5 / A5 / Hans:** Asked-for `params` are **order capture**. Freeze is **per Test** `(sample, analysis)`. First LimsRun start **writes** `asked_for.params` → `tests.asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. `if test: continue` is **not** a freeze. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, do **not** close freeze skip and do **not** teach skip-on-`{}` as shipped. **OQ-WO-6 for extract CLOSED** (Leadership Confirm): extract is a process, not a LimsRun; exactly one asked-for LimsRun is the assay step. Live SHA `9342439` — AC-P2-9..11 Pass; overall P2 unsigned. Freeze skip OPEN. |
| **RQ-WO-8** | Work_order / Route does **not** create Tests. Tests are created at **LimsRun start** (WO-7) for the process being started. First Start must not mint Tests for later processes. Publish / `PATCH complete` **422s the whole run** if any Test is missing — including **empty plan**. Stay unpublished. Zero Results. |
| **RQ-WO-9** | Non-instrument analysis: LimsRun with `analysis_id` required; manual results OK; parser requires instrument XOR CRO (WO-4). Parser is chosen at **import**, not on the process step. Extract is a **process** and has no asked-for `analysis_id`. Qubit / Nanodrop / etc. are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …) — other `analysis_id`s, own Tests, own params freeze — not a second asked-for, not on extract. **OQ-WO-6 extract CLOSED.** |
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
18. Teach skip-on-`{}` as a freeze or close freeze skip. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. NULL = not frozen yet; `{}` after first start = locked empty; later start does **not** overwrite including frozen `{}`. Until classic `/tests` leaves NULL or a freeze marker exists, skip stays OPEN. `if test: continue` is not a freeze.
19. Publish skip-and-complete when a Test is missing
20. Admin-only Route / `experiment:manage` on Route / RLS that hides catalog-visible SOP def/steps (`created_by` or `has_experiment_access()`)
21. Map save or Route that ANDs one type across later processes (later **steps** of the process being started still type-gate at start)
22. Admin-authored routing-map sample type or any create-form type picker
23. First Start that instantiates the whole sequence at once
24. Silent `first()` when two saved rows both accept current type
25. Map save 409 that blocks extract-first vs Qubit-first for the same analysis and TAT
26. Teaching extract as a LimsRun, or extract wearing ELISA / asked-for `analysis_id`. Map-save or Route that accepts asked-for analysis count **0 or 2+** among LimsRuns. Two ELISA LimsRuns in one route (they would share one Test `(sample, ELISA)` — not QC).
27. Dest mint at execute (new DNA Sample / dest-type rewrite) treated as the C2 fix. Equivalent aliquot is same sample, new container.
28. Assign that omits `container_id` when vessel count is 0 or 2+. Emptied-source assign **201** (Contents amount 0) — leftover of `02fe95f`; live lock on `1572071` is **422**. Later Start that follows inbound parent / `wo.sample_id` when dests exist. PATCH of `eln_process_samples` as dest-follow. Join/release that no-ops without `entry.process_step_id` on `02fe95f`.
29. One process instance carrying two asked-for assays. Folding supporting QC into the asked-for `analysis_id`. Teaching extract-every-WO or one DNA sample = one work order forever. Teaching extract as a LimsRun that carries “other analyses.”

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
| AC-P2-7 | First Start = process[0] only, no Tests for later processes. Later Start following the execute-minted destination is on **`1572071`**; Deiter `570bbc0` execute is Lab Ops Met, Tobias QA restamp unsigned |
| AC-P2-8 | Classic `/tests` leaves `asked_for_params` NULL, or a freeze marker exists. Until then skip-on-`{}` stays OPEN (not a verified freeze skip). **OQ-WO-6 extract CLOSED:** extract is a process, not a LimsRun. Exactly one asked-for LimsRun is the assay step. |
| AC-P2-C1 | Assign is the tube in hand: `container_id` required. 0 vessels or 2+ without a pick → **422**, lab-readable, no silent pick. Receive tube assign → **201** with `container_id`. **Pass** on `02fe95f` stays history; live `570bbc0` is **Lab Ops Met** (Deiter), not Tobias QA Pass. |
| AC-P2-C2 | **Fail** on `02fe95f` stays history. On `570bbc0`: **Lab Ops Met** (Deiter), not QA Pass; Tobias restamp **unsigned**. Numbered fair click: set a tracked amount so execute can transfer; same dest type → same sample, new container; destination on process; inbound assignment `removed`; Later Start follows destination. Leftover inbound volume is not a Fail — emptying is not required. Amount 0 is an edge (**422**), not the AC. No destination at Start, DNA execute, and 400 `source_amount_null` fixture gap are not C2 Fail. |
| AC-P2-C3 | On `570bbc0`: **Lab Ops Met** (Deiter), not QA Pass; Tobias restamp **unsigned**. Numbered fair click: execute DNA → new Sample + container (`parent_sample_id`); parent stays Blood; destination pair only active assignment; Later Start follows DNA. Parent Blood at Start and no destination at Route are not C3 Fail. Same click as extract-hold 1.7. |
| AC-P3-1 | Type `12.3` with units_default set → `reported_result` set; `qualifiers` NULL unless a list qualifier is chosen |
| AC-P3-2 | Missing units_default → 422, no row |
| AC-P4-1 | Apply creates process definition with at least one step; template-only Apply is gone as the success path |
| AC-P5-1 | Activate parser after dry-run pass; import a file with LLM disabled |

## 8. UAT

Script: `UAT_Scripts/uat-post-receive-work-spine.md` (P1 cases). **P1 Pass**; merged PR 81. On live **`570bbc0`**, Deiter C1/C2/C3 execute is **Lab Ops Met**, not Tobias QA Pass. Execute joints remain **`1572071`**. Tobias restamps the same numbered C2/C3 ACs; his execute Results are not yet present, so the QA restamp remains unsigned. Do not use retired `uat-sample-accessioning.md`.
