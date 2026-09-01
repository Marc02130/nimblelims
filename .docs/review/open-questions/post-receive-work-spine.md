# Open questions: post-receive-work-spine

**Status:** Living decision log  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| OQ-AF-1 | Asked-for UI: dedicated `/asked-for` vs sample-detail only? | **Decided (provisional)** | P1 | **Both:** `/asked-for` backlog + sample detail section. Not on receive. | 2026-08-28 | Leadership |
| OQ-AF-2 | Permission: new `order:create` vs reuse `test:assign`? | **Decided (provisional)** | P1 | Reuse **`test:assign`**. Do not add a permission this phase. | 2026-08-28 | Leadership |
| OQ-AF-3 | Param defs required in P1 or empty-object only? | **Decided (provisional)** | P1 | Table ships; OOB may have **zero** defs (working-note rows are **not seed**). Empty `params` OK. Unknown keys 422. | 2026-08-28 | Leadership |
| OQ-AF-6 | Conditional required (e.g. `protein_conc_mg_ml` only if `matrix=microsome`)? | **Decided** | P1 validation | **No built-in “required if” engine.** Params belong to the **analysis**. The person who sets up the analysis marks each key required or not. Unknown keys / missing required keys still 422. | 2026-08-28 | Leadership |
| OQ-AF-7 | Enum via `source_list_id` vs inline `allowed_values` jsonb? | **Decided (provisional)** | P1 schema | **Both columns.** Prefer list-backed when a Lists row exists; `allowed_values` for table-design / no list yet. | 2026-08-28 | Arch |
| OQ-TAT-1 | TAT overlap matching when two ranges overlap? | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Not Open. Not CEO-only. | P2 | **409 on save when overlapping TAT, overlapping first-step allow-lists, and overlapping LIMS Run analyses in the chains.** Extract-first vs Qubit-first for the same TAT is legal. Two routes with the same first-step types and different LIMS Run analyses for the same TAT are legal. No first-match. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md). | 2026-08-30 | Leadership |
| OQ-WO-1 | Auto-route on asked-for create vs explicit Route button? | **Decided** | P2 UX | **Tech hits Route.** Asked-for save never mints work. Route zero acceptable → 422; two saved rows that both accept current type → 409; exactly one mints. No silent `first()`. | 2026-08-29 | Leadership |
| OQ-WO-2 | work_order field list beyond route + status? | **Decided — superseded by ordered-route lock** | P2 | Snapshot ordered `process_definition[]`, asked-for/sample/analysis FKs, status. No due-date copy. | 2026-08-29 | Marc / Rolf / Leadership |
| OQ-WO-3 | Process-instance linkage for an ordered route? | **Decided — superseded** | P2 schema | Each started `eln_process` points to the work order and records its route position. Unique `(work_order_id, route_position)`. Start instantiates first pending definition only. | 2026-08-29 | Marc / Rolf / Leadership |
| OQ-WO-4 | Type eligibility on analysis vs execute steps? | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Round 1 only — do not restamp. | P2 L2 | No map type or analysis field. A route is an ordered process list and **may contain multiple LimsRun analyses**. Asked-for assay → **any** route whose chain **contains** that analysis (plus TAT + first-step type). Zero → 422; two rows that both accept this type **and** this analysis → 409. Later starts gate current type then. Dest-type mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history, not a live ban; Hold lifts for type-changing execute only. Route / Start / map-save still mint zero daughters. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md). | 2026-08-30 | Leadership |
| OQ-WO-5 | Must process *x+1* accept the type emerging from process *x*? | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Not Open. Not CEO-only. | P2 L4 | **Yes** at **map save** only. Emerging = aliquot/pool dest on *x* last Experiment if set; else last-step accepted types. Map save 422 if *x+1* first step does not accept it. **Mint is not this OQ.** Deiter Contents click on `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. On live `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**, not Tobias QA Pass; execute joints remain `1572071`. Tobias’s numbered C2/C3 QA restamp has no Result yet. No destination at Route/Start, 400 `source_amount_null`, and DNA scored as C2 are not dest-follow code punches. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md). | 2026-08-30 | Leadership |
| OQ-WO-6 | May extract wear the asked-for `analysis_id`? | **CLOSED (extract punch).** **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter) 2026-08-31. **Marc lock 2026-09-01** (pending Leadership overwrite): care about the asked-for only — common path extract does not wear the panel `analysis_id`; **not** a forever ban on extract-as-LimsRun. Round 2 “stays Open” is history — do not restamp R2-3 cells. | P2 WO-7 | **Common path:** extract is an **experiment** (equipment; aliquot/pool execute) on a process and does **not** wear the panel asked-for `analysis_id`. Cardinality 1 cannot land on extract. Extract cannot wear ELISA. Hans’s 1-count-on-extract freeze punch is **closed**. **Do not forever-ban** extract-as-LimsRun if equipment later is an instrument. **Assay ask:** exactly one asked-for LimsRun (the assay step). Supporting QC = other `analysis_id`s, own Tests, same route. **Extracted DNA ask (1.4):** DNA tube; **zero** assay LimsRuns is legal — do not 422 map-save/Route for missing assay LimsRun. Two ELISA LimsRuns still 422. Freeze skip NULL is **Tobias Pass** on `bf51b19` (not this OQ; not a merge hold). **1.2 dest-cohort lookup** after C3 is **Closed** (see OQ-WO-7 Tobias Pass). Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md). | 2026-08-31 | Leadership |
| OQ-WO-7 | WGS params on the DNA Test from the WO after C3? | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `(DNA, WGS)` has `asked_for_params` **`{library_kit: TruSeq}`** from blood work order **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`). **Was not recoded.** **CEO Accept (Rolf)** of Hans’s written UAT brief stands. Merged to `main` (`5040f2d`) with this OPEN — that history stands; do **not** pretend merge was held for it. Older “OPEN / AC unsigned until Tobias” copy in walls below is **superseded** — do not restamp those walls. Closeout **1.4** stays **OPEN**. Overall P2 **unsigned**. Not IC50. | — (Closed; not overall P2 Pass) | After C3, WGS LimsRun starts on DNA; asked-for WGS with params still on blood. Lookup by dest `sample_id` only used to freeze `{}` on Test `(DNA, WGS)`. Freeze from the **work order’s asked-for** (blood asked-for / WO cohort), **not** `{}`. Not Qubit. Not extract=LimsRun. Not dest-follow. Numbered AC: **AC-P2-OQ-WO-7**. Product SHA **`80f054b`**. Lookup: (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id` so Qubit/Nanodrop do not steal WGS `{library_kit: TruSeq}`; (2) else walk `parent_sample_id` for a routed asked-for of that analysis; (3) else `{}`; (4) freeze skip: write onto NULL; do not overwrite an already-frozen payload including locked empty `{}`. Pytest for this AC landed in `9f86d14`. **Pass (definition):** Test `(DNA, WGS)` has `{library_kit: TruSeq}` from the blood WO asked-for. **Fail:** `{}` / missing kit; WGS Test on blood; assay hung on extract. **Not a Fail:** no dest at Route/Start; `source_amount_null`; Qubit empty supporting freeze; 1.4; ELISA on a second blood tube. **Result Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `(DNA, WGS)` has `{library_kit: TruSeq}` from WO **`4ea9de0c`**. **`9f86d14` was not recoded.** Do **not** fold dest-follow, extract-as-LimsRun, freeze skip, cardinality, Route 409, closeout 1.4 as this work. Seq-1 on `bf51b19` did **not** score this. Leftover `9f86d14` is **not** a UAT click. **Not freeze skip.** Freeze skip NULL **Pass** on `bf51b19` stands. Closeout **1.4** stays OPEN separately. Do **not** invent overall P2 Pass. | 2026-09-01 | Tobias |
| OQ-RES-1 | Qualifiers shape for typed number? | **Decided** | P3 | **Typed token → `reported_result`.** `qualifiers` stays UUID FK to Result Qualifiers (`<LOD`, `ND`); NULL for a clean number. `raw_result` may copy the token on the manual path. **Reject** JSON `{"entered_as":…}` in `qualifiers` (type collision + destroys LOD/ND). No `results.unit_id`. Fold into RQ-RES-1 / AC-P3-1 (SC1–SC4). | 2026-08-28 | Sci CSO |
| OQ-SOP-1 | Apply always create process def, or user picks template vs process? | **Decided (provisional)** | P4 | **Always process definition** as success path. Template created only if an experiment step needs it. | 2026-08-28 | Leadership |
| OQ-SOP-2 | May Apply write inactive parser draft? | **Decided (provisional)** | P4 | **Yes, inactive and unbound** (S11). No bind to production runs. | 2026-08-28 | Security |
| OQ-IMP-1 | Is P5 blocked on anything in P1–P4? | **Decided** | P5 | **No.** May proceed in parallel after P1 if staffing allows. | 2026-08-28 | Leadership |

## Marc lock pending Leadership overwrite — 2026-08-31

Retained history (points 1–4). **Leadership Confirm** of the extract-process / 1-count grain landed the same day — see the next section. Do not read point 5 as live.

1. **One asked-for per process instance.** A process instance is bound to one asked-for row. Do not teach one process carrying two asked-for assays.
2. **Supporting QC = other analyses, own Tests.** Qubit / Nanodrop / etc. are **supporting LimsRuns after extract** that quantify DNA. **Process QC is not an asked-for.** Own Tests `(sample, analysis)`. Do **not** put Nanodrop on extract — extract is an **experiment** (equipment execute) on a process, **never** a LimsRun, and has **no** asked-for `analysis_id`.
3. **No route branching this phase.** Shared extract is **out of scope** as one WO splitting to two assays. P2 handling: Route **blood** for WGS (extraction → sequencing). That asked-for **owns WGS params**. C3 execute mints the DNA tube. A **C2 aliquot** of that DNA continues the WGS WO. **WES is a new asked-for on the DNA tube** (post-extraction → sequencing) and **owns WES params**; that tube is then **aliquoted or used up**. Two asked-fors, two param snapshots, two WOs. Do not teach dest auto-joining a second WO. Do not copy WGS params onto WES.
4. **Freeze is per Test `(sample, analysis)`.** First LimsRun start writes `asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. **OPEN** until classic `/tests` leaves NULL or a freeze marker exists. Do not close freeze skip. Do not teach skip-on-`{}` as shipped.
5. **OQ-WO-6 extract punch — superseded.** Live status is **CLOSED (extract punch)** under Leadership Confirm below. Strike “extract LimsRun must not share asked-for `analysis_id`.”

Click SHA for C2/C3 remains `570bbc0`. Tobias QA restamp stays **unsigned**. Deiter Met is Lab Ops only. `02fe95f` / `9342439` untouched. Route two-accept 409 stays OPEN/unsigned. No overall P2 Pass. Hold merge of `feat/work-order-p2` to `main`. Not IC50.

## Leadership Confirm — OQ-WO-6 extract is a process; exactly one asked-for LimsRun — 2026-08-31

**Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter). Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md). Round 2 R2-3 “stays Open” is history. Not Pass.

- Extract is an **experiment** (equipment; aliquot/pool execute; dest) on a process. **Never** a LimsRun. No asked-for `analysis_id`. LimsRun is instruments.
- Exactly **one** LimsRun in the route has the asked-for `analysis_id` — that LimsRun is the **assay step**.
- Extract (experiment on a process) and Qubit (supporting LimsRun) may sit in the chain.
- Map-save / Route **422** if asked-for analysis appears 0 or 2+ times among LimsRuns. Two ELISA LimsRuns refused.
- **OQ-WO-6 for extract CLOSES.** Hans’s 1-count-on-extract freeze punch is closed by this grain.
- Freeze skip stays **OPEN**. Tobias C2/C3 unsigned. Hold merge. Not IC50.

## Marc Confirm — supporting LimsRuns in the same route — 2026-08-31

**Marc Confirm.** Leadership Confirm of extract-as-process + exactly-one asked-for LimsRun still stands.

Qubit / Nanodrop / etc. are **supporting LimsRuns in the same route** as the asked-for assay. Other `analysis_id`s, own Tests. Asked-for analysis appears **once**, on the assay LimsRun. Do **not** invent a second asked-for for QC. Do **not** put Nanodrop on extract. Extract remains a **process**, not a LimsRun, no asked-for `analysis_id`. Freeze skip stays **OPEN**. `9342439` untouched. Hold merge. Not IC50.

## Leadership Confirm (Rolf, Marc) — supporting LimsRuns in the same route as the asked-for assay — 2026-08-31

**Leadership room Confirm (Rolf, Marc).** Qubit / Nanodrop / etc. sit as supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …). Sequencing is an example, not the only case. Other `analysis_id`s, own Tests, **own params freeze**. Asked-for analysis still appears **once**, on the assay LimsRun. Extract stays a **process**. Do not invent a second asked-for for QC. Do not put Nanodrop on extract. Freeze skip **OPEN**. Hold merge. Not IC50.

## Marc lock overwrite — sequential asked-fors, not DNA joining many WOs — 2026-08-31

**Not Leadership Confirm of branching.** OQ-WO-6 extract **CLOSED** still stands. Overwrites leftover “DNA sample may join many work orders” copy. Not Pass.

**No route branching this phase.** Route **blood** for WGS (extraction → sequencing); that asked-for **owns WGS params**. C3 execute mints DNA. A **C2 aliquot** of that DNA continues the WGS WO. **WES is a new asked-for on the DNA tube** (owns WES params); that tube is then **aliquoted or used up**. Two asked-fors, two param snapshots, two WOs. Do not teach dest auto-joining a second WO. Do not copy WGS params onto WES. Freeze skip **OPEN**. Hold merge. Not IC50.

## Marc lock overwrite — extract is experiment / equipment, never a LimsRun — 2026-08-31

**Not a restamp of OQ-WO-6 votes.** Extract **CLOSED** as not-a-LimsRun still stands. Overwrites “extract is a process” shorthand.

Extract uses **equipment**, not instruments. Extract is an **experiment** that may occupy a process. **Never a LimsRun.** No asked-for `analysis_id`. LimsRun is instruments / analysis / Tests. Do not author extract as a LimsRun.

**After extract**, when the asked-for is an **assay** (WGS / WES / ELISA / …), a **QC LimsRun** (Qubit, Nanodrop, or other QC instrument) may quantify the DNA. Own Test. **Process QC is not an asked-for.**

**If the asked-for is Extracted DNA:** they get a **tube of DNA**. No sequencing. **No other LimsRuns.** Extract may become a LimsRun later if the equipment is an instrument — not a forever ban.

## Marc lock overwrite — Extracted DNA asked-for is a tube — 2026-08-31

Asked-for **Extracted DNA** = DNA tube. No sequencing LimsRun. No other LimsRuns on that asked-for. Cardinality “exactly one asked-for LimsRun” does **not** apply to that asked-for (zero assay LimsRuns). Two ELISA LimsRuns still 422. Assay asked-fors still: extract experiment → optional QC LimsRun (not asked-for) → one assay LimsRun.

## Marc lock — care about the asked-for only — 2026-09-01

**Marc lock pending Leadership overwrite if Confirm has not landed for this exact wording.** Not Leadership Confirm. Not overall P2 Pass. Not IC50. Does **not** rewrite Confirm walls above or `9342439` / `02fe95f` / `570bbc0` unsigned Tobias C2/C3 history.

**Care about the asked-for only.** Extracted DNA ask = DNA tube (process however). Sequencing ask with blood = sequencing is the ask; extract is **route machinery**, not a second ask. Zero assay LimsRuns legal for Extracted DNA (**1.4**). One assay LimsRun when the ask is an assay. Do **not** forever-ban extract-as-LimsRun. OQ-WO-6 extract close stays in spirit for the common path (extract does not wear the panel `analysis_id`).

**1.2 dest-cohort lookup after C3 is OPEN post-merge, not a merge hold.** After Blood→DNA execute, the assay on the DNA dest looks up asked-for by dest `sample_id` and gets `{}` (wrong cohort). Freeze skip NULL is **Tobias Pass** on **`bf51b19`**. Older “freeze skip OPEN” in the Confirm walls above is **superseded** by that Pass — do not restamp those walls. **Merge bar Met** (Marc/CEO). Asked-for-only Marc lock from PR **111** still stands. `9342439` untouched. Do not restamp unsigned Tobias C2/C3 on `570bbc0`. Deiter Lab Ops Met on `570bbc0` stands.

## Marc lock — ELISA not on DNA; second tube own asked-for — 2026-09-01

**Marc lock pending Leadership overwrite if Confirm has not landed for this exact wording.** Not Leadership Confirm. Not overall P2 Pass. Not IC50. Does **not** rewrite Confirm walls above, asked-for-only lock, merge-bar Met closeout, or `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.

1. **ELISA not on DNA.** The panel/asked-for ELISA assay is **not** run on the DNA derivative as the intended matrix for that ask. Do **not** teach ELISA-on-DNA as the happy path for a blood ELISA ask. WGS / WES still use extract as route machinery to DNA; ELISA does not.
2. **Same blood Sample may have a second tube** with its **own asked-for + route**. Equivalent aliquot / extra receive container on the same Sample can carry a separate asked-for and a separate route (open uniqueness remains `(sample, analysis)`).
3. **Separate containers = separate process assignments.** Process holds a sample-in-a-container pair. Two tubes on the same Sample that are both in play are **two assignments** — do **not** collapse them into one process-sample row.

**OQ-WO-7 stays OPEN** (post-merge dest-cohort asked-for lookup after C3). **In-bar** for method complete / overall P2 Pass honesty — not a soft forever-defer. Do not close it. Asked-for-only lock, extract-as-process common path, supporting QC same-route, freeze skip Pass on `bf51b19` stand.

## Leadership Confirm — ELISA not on DNA; second tube; extract LimsRun later — 2026-09-01

**Leadership Confirm** (Rolf, Deiter, Hans, Heidi, Günter). Overwrites the Marc lock immediately above for this wording. Not overall P2 Pass. Not IC50. Does **not** rewrite Confirm walls above, merge-bar Met closeout, or `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.

1. **ELISA is not on DNA** (wrong matrix). Do **not** hang ELISA on the DNA dest after C3.
2. Same blood Sample, **second tube (Contents)** may carry its **own asked-for and route**. Two blood tubes → two process assignments (`container_id`). ELISA route and WGS/extract route stay apart.
3. Do **not** teach “extract can never be a LimsRun” as a forever ban. Hans’s punch: do not hang asked-for assay `analysis_id` on extract (panel Test would freeze on blood). **Extracted DNA asked-for can have Qubit/Nanodrop.** Extract-as-instrument LimsRun is later.
4. **OQ-WO-6 still:** asked-for `analysis_id` once on the assay LimsRun, not on extract.
5. **OQ-WO-7 stays OPEN** and is **in-bar** for the method. Blood WGS asked-for → C3 DNA → WGS start on DNA freezes `{library_kit: …}` from the **WO asked-for**, not `{}`. Not Qubit params.

**Standing UAT rule:** after **two** UAT attempts on the same issue, the next run needs a written “what we are testing and why” before the click — fixtures, Pass/Fail, and what is **not** a Fail.

## Science — OQ-WO-7 OPEN on the merge — 2026-09-01

**Science.** Does **not** rewrite Confirm walls, Tobias `bf51b19` per-AC Pass, or Leadership Confirm ELISA / second-tube. Not overall P2 Pass. Not IC50.

Per-AC on `bf51b19` **Pass**. **Overall P2 stayed unsigned.** We merged (`5040f2d`) with **OQ-WO-7 OPEN** (WGS params on the DNA Test from the WO after C3). Leftover **`9f86d14`** on **`80f054b`** **is** that Grok Build work. **Do not recode.** Remaining work is **Tobias**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. Clarifying the issue made the product better. Going forward the method remains **in-bar** (blocks “method complete” / overall P2 Pass honesty). Do **not** pretend `5040f2d` was held for it. Do **not** invent Tobias Pass.

## Hans UAT brief — AC-P2-OQ-WO-7 — 2026-09-01

**Hans.** Written “what we are testing and why” for the standing two-attempt UAT rule. Does **not** rewrite Tobias Results on `bf51b19`. Result **unsigned** until Tobias. Do **not** invent Pass/Fail. Not IC50. Mirror: [`UAT_Scripts/uat-post-receive-work-spine.md`](../../../UAT_Scripts/uat-post-receive-work-spine.md) **AC-P2-OQ-WO-7**.

**What / why:** After C3, WGS LimsRun starts on DNA; asked-for WGS with params still on blood. Lookup by dest `sample_id` freezes `{}` on Test `(DNA, WGS)`. Freeze from the work order’s asked-for. Not Qubit. Not extract=LimsRun. Not dest-follow.

**Fixture:** Receive blood → asked-for WGS with real param (e.g. `library_kit`) → Route extract (dest DNA) → optional Qubit → one WGS LimsRun → C3 execute → Later Start WGS on DNA.

**Pass:** Test `(DNA, WGS)` has `{library_kit: TruSeq}` from the blood WO asked-for.

**Fail:** `{}` / missing kit; WGS Test on blood; assay hung on extract.

**Not a Fail:** no dest at Route/Start; `source_amount_null`; Qubit empty supporting freeze; 1.4; ELISA on a second blood tube.

**Out of this AC:** dest-follow, extract-as-LimsRun, freeze skip, cardinality, Route 409, closeout 1.4.

## CEO Accept (Rolf) of Hans’s OQ-WO-7 UAT brief — 2026-09-01

**CEO Accept (Rolf)** of the written what/why **before Tobias**. Docs-only. Not a UAT Result. Not overall P2 Pass. Not IC50. Does **not** rewrite `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.

1. Accept the Hans brief above as the numbered AC **AC-P2-OQ-WO-7** (Pass / Fail / not-a-Fail as written).
2. **Grok Build codes first** was the remaining-work rule at this Accept. Leftover **`9f86d14`** on **`80f054b`** **is** that work (pytest in the same commit). **Do not recode.** Remaining work is **Tobias**, not a new design.
3. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps Pass/Fail. **In-bar** for method complete / overall P2 Pass honesty. Tobias clicks **AC-P2-OQ-WO-7** on `80f054b`. P2 already merged (`5040f2d`) with this OPEN — that history stands.
4. Closeout **1.4** (Extracted DNA zero assay LimsRuns) may stay OPEN separately.
5. Overall P2 Pass still **unsigned**. Do **not** invent Tobias Pass. Do **not** rewrite `bf51b19`.

## Leadership Confirm — leftover `9f86d14` on `80f054b` is OQ-WO-7 Grok Build — 2026-09-01

**Leadership Confirm** (Rolf, Deiter, Hans, Heidi, Günter). Docs-only honesty punch. Not a UAT Result. Not overall P2 Pass. Not IC50. Does **not** rewrite Tobias Results on `bf51b19`.

Leftover **`9f86d14`** on product SHA **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`) **is** the OQ-WO-7 Grok Build work. **Do not recode.** Tobias clicks **AC-P2-OQ-WO-7** on that SHA. Pytest landed in `9f86d14`. Remaining work is **Tobias**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. Lookup already on that SHA: (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id`; (2) else walk `parent_sample_id`; (3) else `{}`; (4) freeze skip write onto NULL; do not overwrite frozen including locked empty `{}`. Pass: `{library_kit: TruSeq}` from the blood WO asked-for. Fail: `{}` / missing kit; WGS Test on blood; assay hung on extract. Not a Fail: no dest at Route/Start; `source_amount_null`; Qubit empty supporting freeze; 1.4; ELISA on a second blood tube. Do **not** fold dest-follow, extract-as-LimsRun, freeze skip, cardinality, Route 409, closeout 1.4 as this work.

## Tobias Result — AC-P2-OQ-WO-7 Pass; OQ-WO-7 Closed — 2026-09-01

**Tobias.** Living Result. Docs-only fold. Does **not** rewrite Tobias Results on `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f`. Does **not** recode **`9f86d14`**. Not overall P2 Pass. Not IC50.

**AC-P2-OQ-WO-7 Pass** on product SHA **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`). Test **`55f9cad9`** `(DNA, WGS)` has `asked_for_params` **`{library_kit: TruSeq}`** from blood work order **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`). **Was not recoded.**

**OQ-WO-7 Closed.** Older “OPEN / AC unsigned until Tobias” copy in walls above is **superseded** — do not restamp those walls. Closeout **1.4** (Extracted DNA zero assay LimsRuns) stays **OPEN**. Overall P2 remains **unsigned**. Leadership did not stamp overall Pass.

Mirror: [`UAT_Scripts/uat-post-receive-work-spine.md`](../../../UAT_Scripts/uat-post-receive-work-spine.md) **AC-P2-OQ-WO-7**.

## Gate rule

- **P1:** Unblocked (OQ-AF-* decided, including AF-6: no conditional required).  
- **P2 live (Leadership Confirm 2026-09-01, Rolf/Deiter/Hans/Heidi/Günter; leftover `9f86d14` on `80f054b` is OQ-WO-7 Grok Build):** P2 is on `main`. Product SHA for **AC-P2-OQ-WO-7** is **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`). Per-AC **Pass** on `bf51b19` — do **not** rewrite those Results. Overall P2 **unsigned / not Pass**. Care about the asked-for only (PR **111** still stands). **ELISA is not on DNA** — do not hang ELISA on the DNA dest after C3. Second blood tube (Contents) may have own asked-for + route; two tubes → two process assignments (`container_id`); ELISA route and WGS/extract stay apart. Extracted DNA ask = DNA tube; **zero assay LimsRuns** legal (**1.4**); **Qubit/Nanodrop allowed** on that ask. Assay ask = **one** asked-for LimsRun. Extract typically a process (does not wear panel `analysis_id`); do **not** forever-ban extract-as-LimsRun. **OQ-WO-6 still:** asked-for `analysis_id` once on the assay LimsRun, not extract. Freeze skip NULL **Pass** on `bf51b19`. Tobias C1/C2/C3 **Pass** on `bf51b19`; `570bbc0` remains Lab Ops Met history. **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `(DNA, WGS)` has `{library_kit: TruSeq}` from blood WO **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`). **Was not recoded.** Lookup on `80f054b`: (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id`; (2) else walk `parent_sample_id`; (3) else `{}`; (4) freeze skip write onto NULL, do not overwrite frozen including locked empty `{}`. Pass/Fail/not-a-Fail stay the AC definition in Hans’s brief. Merged `5040f2d` with this OPEN is history. Closeout **1.4** stays OPEN separately. Do **not** invent overall P2 Pass. Not IC50.
- **P2 historical Confirm wall (do not restamp):** explicit Route; ordered `process_definition[]` (a route **may have multiple LimsRun analyses**). **Leadership Confirm (2026-08-31, Rolf/Deiter/Hans/Heidi/Günter):** extract is an **experiment** (equipment execute) on a process, no asked-for `analysis_id` on the common path; exactly **one** LimsRun in the route has the asked-for `analysis_id` when the ask is an assay; extract (experiment) then Qubit/Nanodrop QC LimsRun (process QC, **not** an asked-for) then the assay LimsRun may sit in the chain; map-save / Route **422** if an **assay** asked-for analysis appears 0 or 2+ times among LimsRuns; two ELISA LimsRuns refused. **OQ-WO-6 for extract CLOSES** for the common path. Round 1 Leadership Confirm of analysis-in-chain + overlap 409 + handoff 422 (OQ-WO-4 / OQ-TAT-1 / OQ-WO-5) — do not restamp those cells. **Round 2 Leadership Confirm** (R2-1…R2-4) remains history; R2-3 “OQ-WO-6 stays Open” is overwritten for the extract punch only. **Two-grain execute Confirm:** C2 same Sample + additional container; C3 derivative Sample + container with `parent_sample_id`; Route / Start / map-save / asked-for mint zero daughters. On `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**. Execute joints remain `1572071`. Receive amount often starts NULL, so set a tracked amount so execute can transfer; 400 `source_amount_null` is fixture setup. No destination at Route/Start and DNA scored as C2 are not failures. Keep: one asked-for per process instance; supporting QC = other analyses, own Tests; **no route branching** — WGS asked-for on blood owns WGS params (extract → seq); C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up (own params); freeze is per Test `(sample, analysis)` — first LimsRun start writes `asked_for_params`, later start does **not** overwrite (including frozen `{}`). Deiter `02fe95f` C2 Fail and `9342439` Hold history stay untouched. Overall P2 remains unsigned / not Pass. Not IC50.
- **P3:** OQ-RES-1 **Decided**. Persist lock waits SC1–SC4 already folding into RQ-RES-1.
- **P4:** OQ-SOP-2 Decided (inactive unbound). Extract-hold UAT **1.7** stays OOB execute (no Result stamp); dest mint Hold on `9342439` / `02fe95f` is Start-extract history, not a live ban on type-changing execute.
- **P5:** Unblocked.

Do not start a phase while its blocking rows are **Open**.
