# Leadership send: P2 route lock (ordered processes, analysis in chain, type handoff)

**Date:** 2026-08-30  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO)  
**Ask:** Round 1 remains **Leadership Confirmed** (Rolf, Deiter, Hans, Heidi, Günter; all five asks). Round 2 is **Leadership Confirm** (Rolf, Deiter, Hans, Heidi, Günter; R2-1…R2-4). **Contents grain / `0077` remains a Leadership Confirm** (Rolf, Deiter, Hans, Heidi, Günter) — process assignment is a **sample in a container**. Leadership later **Confirmed Deiter’s click**: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** on product `4671ba8` / `02fe95f`. C1/C2 are **not** unsigned. Docs Confirm `84d2810` is not a new execute and not the click SHA. Not a Tobias QA Pass and not a merge stamp. Grok Build owns dest-join / source-remove. Overall P2 UAT remains unsigned / not Pass.
**Implement gate:** **OPEN for P2 coding on `feat/work-order-p2`.** Merge to `main` **held** until signed UAT Pass.  
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)

**Code:** `feat/work-order-p2`. Latest **signed** AC-P2 is `8cfa2a9` (per-AC; overall **not Pass**; PR **#92** honesty fold). **This commit** is `9342439` (`93424396ce3d02f01a8a8388abda39ae6ebf8010`): analysis is not a map field; Route matches a LIMS Run in the chain; process *x* → *x+1* emerging-type handoff; create-route UI shows types/analyses/emerging types.

**UAT:** do **not** rewrite `8cfa2a9` / `b005cfe` / `9c4f9da` / `3b56cfb` / P1. Tobias signed **AC-P2-9..11 Pass** on `9342439` (local compose, down after; docs merge `50c1f24` does not change the click SHA). Deiter / Hans / Heidi / Günter confirmed that restamp (honesty, **not** a merge vote): later-step type-gate **Met**; AC-P2-11 / handoff Pass is **map-save only**; dest mint **Hold** on that SHA is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute; freeze skip **OPEN**; extract `analysis_id` **OPEN**; Route stays `test:assign`. Overall P2 remains **not Pass**.

**Dest-type Hold (dated to `9342439` / `02fe95f` Start-extract):** that restamp is tube still Blood, **0 DNA** — catalog handoff, not “blood became DNA at Start.” It is **not** a live ban on type-changing aliquot/pool execute. Route / Start / map-save still mint **zero** daughters. Authoring may still **read** a declared dest on the template for handoff 422. Hold lifts for type-changing execute only.

---

## What changed vs the last signed lock

| Was (PR #91 / `b005cfe` history) | Proposed now |
|----------------------------------|--------------|
| Map row = analysis + TAT + processes | Map row = TAT + ordered processes. **No analysis picker.** |
| Route: analysis + TAT, then first-step type | Route: TAT, first-step type, **and** asked-for analysis is a **LIMS Run somewhere in the route** |
| Map 409 = same analysis + overlapping TAT + overlapping first-step types | Map 409 = overlapping TAT + overlapping first-step types + **overlapping LIMS Run analyses** |
| AC-P2-5 chain-AND (every step accepts inbound type) | **Removed.** Later steps may accept dest types. |
| No process-to-process type handoff | Process *x* emerging type must be accepted by process *x+1* |
| Dest-type Hold | **Unchanged at execute.** Handoff uses **declared** dest on the last experiment of *x*, else last-step accepted types. |

Bench example: extract (plasma in, aliquot dest DNA) → Qubit (DNA). Map save **422**s if Qubit does not accept DNA. Route of a **plasma** sample for **Qubit** succeeds only if Qubit is a LIMS Run in that chain **and** plasma is on extract’s first step. Execute still will not mint the daughter until dest-type Hold closes.

---

## Proposed lock (please confirm)

1. A route is TAT + ordered `process_definition[]`. No admin sample-type or analysis picker. UI shows each process’s allowed types, LIMS Run analyses, and emerging types.
2. Assign on Route when (a) current sample type is on the **first process’s first** Experiment/LIMS Run allow-list **and** (b) the asked-for analysis matches a LIMS Run in the route. Zero → **422**. Two rows that both accept this type **and** this analysis → **409**. Never `first()`.
3. Map save **409** only when TAT, first-step types, **and** LIMS Run analyses all overlap. Extract-first vs Qubit-first for the same TAT is legal.
4. Map save **422** when the type emerging from process *x* is not accepted by process *x+1*. Emerging = aliquot/pool `default_dest_sample_type` on the last Experiment/LIMS Run of *x* if set; else that last step’s accepted types.
5. Start instantiates the next pending process only. Later process/step start gates **current** sample type. Dest-type **mint** remains Hold.

---

## Asks (please answer)

1. **Analysis in the route, not on the map.** Confirm: asked-for ELISA may Route onto extract → ELISA → report because ELISA is a LIMS Run in that chain — not because an admin picked ELISA on the map.  
2. **Overlap 409.** Confirm: two extract routes, same TAT, same inbound types, **different** LIMS Run analyses (ELISA vs NGS) both save.  
3. **Handoff 422.** Confirm: extract dest DNA → Qubit that only accepts plasma **must not save**.  
4. **Dest mint stays Hold.** Confirm: this handoff is catalog intent, not “blood became DNA at execute.”  
5. **UAT restamp.** Restamp P2 on this lock after commit, **without** waiting for dest-type mint? Or hold restamp until daughters exist?

---

## Feedback (Leadership) — round 1

**Not a merge stamp.** Overall P2 Pass stays unsigned. Gate for **coding** this lock: open. Gate for **merge:** UAT.

Personas applied from existing spine stamps (Lab Ops L2/L4, CEO ordered-route, Sci CSO dest Hold). **Please overwrite** if you disagree.

### Roll-up

| Ask | Lab Ops | CEO | Security CSO | Sci CSO |
|-----|---------|-----|----------------|---------|
| 1. Analysis in chain | **Yes.** Map is the work plan, not an assay picker | **Yes.** One extract→assay→report route is the product | Neutral (no new AuthZ) | **Yes.** Assay identity lives on the LimsRun |
| 2. Overlap 409 | **Yes.** Same TAT + types + **same assays** is the collision | **Yes.** Two ELISA extracts colliding is the bug; ELISA vs NGS is not | Neutral | **Yes.** Do not 409 two methods that share extract |
| 3. Handoff 422 | **Yes — this is L4.** Do not author extract→Qubit if Qubit cannot take dest DNA | **Yes.** Refuse nonsense routes at save | Neutral | **Yes.** Dest on the extract template is scientific intent |
| 4. Dest mint Hold | **Hard lock.** Handoff ≠ daughter. NCI extract→Qubit still cannot execute | **Hold.** Do not sell daughters in P2 UAT | **Hold.** No new write-back of sample type on execute | **Hard lock.** Do not claim matrix/type changed |
| 5. Restamp now? | **Restamp authoring + Route + freeze.** Do **not** UAT blood→DNA daughter | **Restamp.** Do not wait dest mint to score P2 | Restamp OK if execute still does not rewrite type | **Restamp** the lock; dest E2E is a different packet |

**Consensus (provisional, for Leadership to confirm):** adopt the proposed lock. QA restamps P2 on a **committed** SHA of this lock. Do not fold dest-type mint into that restamp. Do not rewrite signed `b005cfe` / `9c4f9da` / `3b56cfb` / P1.

### Lab Ops (Deiter)

L2 said “do not AND inbound type across later steps.” That still holds. Inspecting **emerging dest** of process *x* against process *x+1* is not chain-AND; it is the handoff L4 asked for. Qubit-first on blood still refuses at Route. Extract-first + later Qubit **saves** only when dest DNA is declared and Qubit accepts DNA. Execute still will not mint the daughter — techs must not be told the tube is DNA. Display types/analyses/emerging on create-route is required or they will author blind.

### CEO / Product

The map is an ordered job, not “pick ELISA.” Analysis-in-chain is the 10-star shape: one route covers extract + assay + report. Overlap 409 on assays (not on TAT alone) keeps two methods legal. Restamp now; waiting for dest mint is how P2 never lands. Do not market P2 as extract-then-Qubit E2E.

### Security CSO

No new permission. `config:edit` still writes the map; Route stays `test:assign`; Start stays `experiment:manage`. Handoff 422 is a catalog consistency check, not a silent sample rewrite. Dest mint remains out — that would be a new write on `samples.sample_type` / lineage and needs its own STRIDE.

### Scientific CSO

`default_dest_sample_type` on the last experiment’s aliquot/pool is the extract method’s product type. Checking it at map save is valid. Do **not** read `sample_type_transitions` as a substitute dest. Do not infer DNA because the SOP title says extract. Fitted results still do not belong on asked-for. Dest-type Hold: params freeze and publish-refuse are orthogonal.

---

## CEO Confirm — 2026-08-30 (Rolf)

Rolf’s Confirm of all five asks. Round 1 above remains persona-applied history. Do **not** read Lab Ops / Security / Sci CSO round-1 cells as live clicks. Full Leadership Confirm is the next section. Not a merge stamp.

| Ask | CEO Confirm |
|-----|-------------|
| 1. Analysis in the route, not on the map | **Yes.** Analysis in the route, not on the map. Asked-for ELISA may Route onto extract → ELISA → report because ELISA is a LIMS Run in that chain — not because an admin picked ELISA on the map. One extract→assay→report route is the product. |
| 2. Overlap 409 | **Yes.** Two extract routes, same TAT, same inbound types, **different** LIMS Run analyses (ELISA vs NGS) both save. Two ELISA extracts colliding is the bug. |
| 3. Handoff 422 | **Yes.** Extract dest DNA → Qubit that only accepts plasma **must not save**. |
| 4. Dest mint stays Hold | **Hold.** Dest mint stays Hold. Handoff is catalog intent, not “blood became DNA at execute.” Do not sell daughters in P2 UAT. |
| 5. UAT restamp | **Restamp now.** Do not wait dest-type mint to score P2. QA restamps authoring + Route + freeze on committed SHA `9342439`. Do **not** UAT blood→DNA daughter. |

---

## Leadership Confirm — 2026-08-30 (live clicks)

**Full Leadership Confirm** of all five asks + OQ-WO-4 / OQ-TAT-1 / OQ-WO-5. Rolf (CEO Confirm above), then Deiter, Hans, Heidi, Günter. Round 1 remains persona-applied history. Dest-type mint Hold on this round is Start-extract / catalog-handoff history (`9342439`), not a live ban on type-changing execute. Not a merge stamp. Tobias signed **AC-P2-9..11 Pass** on `9342439` after this Confirm. Restamp notes (Deiter / Hans / Heidi / Günter) after that click are in the section below — honesty, **not** a merge vote. Overall P2 remains **not Pass**.

### Deiter (Lab Ops)

**Confirm 1–5.** Analysis in the chain. 409 = TAT ∩ first-step types ∩ LimsRun analyses. Handoff 422 if *x* dest is not accepted by *x+1*. Dest mint Hold. Restamp `9342439` now; no daughter E2E. OQ-WO-4 / OQ-TAT-1 / OQ-WO-5 signed.

**Punch:** handoff 422 is **authoring**, not a runnable extract→Qubit. The tube is still blood until dest mint. Later-step type-gate (Qubit-on-blood at start) is **not** dest-type E2E — still click it on this SHA.

### Hans (Sci CSO)

**Confirm 1–5.** Assay identity lives on the LimsRun in the chain, not a map picker. Handoff 422 is catalog intent (`default_dest_sample_type` on the last step of *x*, else that step’s accepted types — not SOP title, not `sample_type_transitions`). Dest mint Hold. Restamp now; no daughter E2E.

**Punch:** analysis-in-chain does **not** close extract sharing the asked-for `analysis_id`. Extract LimsRun must not be ELISA or it freezes the panel Test at process 1. Later-step type-gate is still current type and still unsigned — click it; it is not dest-type E2E. Freeze skip (`{}` vs NULL) stays open.

### Heidi (Arch)

**Confirm 1–5.** Same lock.

**Punches that stay open — not this restamp:** classic `/tests` must leave `asked_for_params` NULL (or a freeze marker); skip-on-`{}` is not a freeze. Extract LimsRun must not share the asked-for `analysis_id`. Derive first-step types and chain LimsRun analyses at read; do **not** keep `routing_map.analysis_id` as a required create field. Later-step type-gate is current type at start — still click it. First Start = `chain[0]` only. Route stays `test:assign`.

### Günter (Sec CSO)

**Confirm 1–5.** No silent `first()`. Handoff 422 is catalog intent. Dest mint Hold — no execute rewrite of `sample_type`. Freeze skip and extract sharing stay open.

---

## Open questions to stamp

| ID | Status | Proposed |
|----|--------|----------|
| OQ-WO-4 | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Dest mint remains Hold. Round 1 only — do not restamp. | No map analysis field; Route matches a LIMS Run in the chain |
| OQ-TAT-1 | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Round 1 only — do not restamp. | 409 = TAT ∩ first-step types ∩ LIMS Run analyses |
| OQ-WO-5 | **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter). Dest mint remains Hold. Round 1 only — do not restamp. | Process *x* emerging type must be accepted by *x+1* |
| OQ-WO-6 | **OPEN.** Leadership Confirm that it **stays Open** (R2-3; Rolf/Deiter/Hans/Heidi/Günter). | Earlier LimsRun in the chain must **not** share asked-for `analysis_id`. Do not teach extract-as-special-assay. |

Tobias signed **AC-P2-9..11 Pass** on `9342439`. Overall P2 remains **not Pass**. Freeze skip and OQ-WO-6 still **OPEN**. Dest-type mint **Hold**. Not IC50.

---

## Leadership notes on Tobias `9342439` restamp — 2026-08-30

Deiter / Hans / Heidi / Günter. **Restamp honesty, not a merge vote.** Confirmed Tobias’s click on `9342439`. Do **not** write overall P2 Pass. Hold product merge. Not IC50.

| Note | Status |
|------|--------|
| Later-step type-gate | **Met** on `9342439`: qPCR-on-blood / still-Blood start **422** `route_sample_type` (current type vs that step; sample not dead). **Not** dest-type E2E. |
| AC-P2-11 / handoff | **Pass is map-save only.** Dest mint stays **Hold** — no execute rewrite of `sample_type`; tube still Blood; 0 DNA daughters. |
| Freeze skip (`{}` vs NULL) | **OPEN** |
| Extract sharing asked-for `analysis_id` | **OPEN** |
| Route permission | stays `test:assign` |
| Overall P2 | **unsigned / not Pass** |

---

## Round 2 — Marc product honesty (send back for review) — 2026-08-30

Not a merge stamp. Do **not** rewrite Tobias `9342439` / `8cfa2a9` Results. Do **not** rewrite Hans/Heidi punches above. Overall P2 stays **not Pass**. Dest-type mint **Hold**.

**What this round is:** fold how Route and WO-7 actually work, so “extract” is not treated as a special assay.

### Product (please confirm)

1. **Available routes = contain the analysis.** For one asked-for assay, every map whose chain has that analysis as a LimsRun is eligible (plus TAT + first-step type). A route **may have multiple analyses** (extract QC + Qubit + ELISA). Asked-for ELISA matches extract→Qubit→ELISA because ELISA is **in** the chain, not because the map is “an ELISA row.” One asked-for row still mints one work order.
2. **Extract is not a special sample kind.** Blood → extracted DNA is a **derivative** (new sample, new type). DNA tube → plated aliquot is the **same sample** (equivalent). Plate → indexed library is a **derivative** again. Type gates on process steps catch blood-on-Qubit. Dest-type **mint** (actually creating the DNA row) remains Hold.
3. **WO-7 punch is Test identity, not extract science.** `_mint_tests_at_start` keys `(cohort sample, run.analysis_id)`. Any **earlier** LimsRun in the chain that reuses the asked-for analysis mints/freezes the panel Test on the parent (usually blood). Extract is only the usual process 1. A correct extract is often experiment-only (dest DNA), or a LimsRun with its **own** analysis (not the panel). Same rule for library prep vs sequencing.
4. **Parser is not on the process.** An analysis may have many parsers (instrument XOR CRO). Process LimsRun step stores `analysis_id` only. Parser is chosen at **import**.

### Asks

| # | Confirm? |
|---|----------|
| R2-1 | Asked-for assay → any route that **contains** that LimsRun analysis. Multi-analysis routes are the product. |
| R2-2 | Type gates (not extract-as-assay) catch blood-in-Qubit. Dest mint stays Hold. |
| R2-3 | OPEN punch stays: **earlier LimsRun must not share asked-for `analysis_id`**. Do not teach “extract is special.” |
| R2-4 | Parser chosen at import, not at process authoring. |

Freeze skip (`{}` vs NULL) stays OPEN. Route two-accept 409 still unsigned from `8cfa2a9`. Map save same-types / different-analyses / same TAT 201 unsigned on the `9342439` click. Overall P2 unsigned.

---

## CEO Confirm — Round 2 — 2026-08-30 (Rolf)

Rolf’s Confirm of R2-1…R2-4. Round 1 remains **Leadership Confirmed**. This section is **CEO Confirm history**. Do **not** read it as the live Round 2 status. Full Leadership Confirm of Round 2 is the next section. Not a merge stamp. Do **not** rewrite Tobias `9342439` / `8cfa2a9` Results. Freeze skip stays **OPEN**. Dest mint **Hold**. Overall P2 remains **not Pass**. Not IC50.

| Ask | CEO Confirm |
|-----|-------------|
| R2-1. Asked-for assay → any route that **contains** that LimsRun analysis | **Yes.** Asked-for assay → any route whose chain **contains** that LimsRun analysis. Multi-analysis routes are the product. One asked-for row → one work order. |
| R2-2. Type gates catch blood-on-Qubit; dest mint Hold | **Yes.** Extract is not a special assay. Type gates catch blood-on-Qubit. Dest mint **Hold**. |
| R2-3. OQ-WO-6 stays OPEN | **Yes.** OQ-WO-6 stays **OPEN** — earlier LimsRun must not share asked-for `analysis_id`. Do not teach “extract is special.” |
| R2-4. Parser at import | **Yes.** Parser chosen at import, not process authoring. Process LimsRun stores `analysis_id` only. |

Send: this file, Round 2. OQ-WO-4 / OQ-TAT-1 / OQ-WO-5 stay **Leadership Confirm** from round 1.

---

## Leadership Confirm — Round 2 — 2026-08-30 (live clicks)

**Full Leadership Confirm** of R2-1…R2-4. Rolf (CEO Confirm above), then Deiter, Hans, Heidi, Günter. Round 1 remains **Leadership Confirmed**. Round 2 CEO Confirm remains history. Dest-type mint Hold in this round is Start-extract / catalog history, not a live ban on type-changing execute. OQ-WO-6 stays **OPEN** (Leadership Confirm that it stays Open). Freeze skip (`{}` vs NULL) stays **OPEN**. Route two-accept 409 and map-save same-types / different-analyses stay unsigned. Do **not** rewrite Tobias `9342439` / `8cfa2a9` Results. Not a merge stamp. Overall P2 remains **not Pass**. Hold merge. Not IC50.

### Roll-up

| Ask | Lab Ops | CEO | Security CSO | Sci CSO |
|-----|---------|-----|----------------|---------|
| R2-1. Contain = Route matching | **Yes.** Available routes = any chain that contains that LimsRun analysis; multi-analysis is the product | **Yes.** Asked-for assay → any route whose chain **contains** that LimsRun analysis. Multi-analysis routes are the product. One asked-for row → one work order | **Yes.** Contain is Route matching: asked-for assay → any chain that has that LimsRun analysis. Multi-analysis routes are the product; each LimsRun keeps its own analysis_id | **Yes.** Contain is Route matching, not Test identity: multi-analysis chains are the product, but each LimsRun keeps its own analysis_id |
| R2-2. Type gates; dest mint Hold | **Yes.** Extract is not a special assay — type gates catch blood-on-Qubit; dest mint stays Hold | **Yes.** Extract is not a special assay. Type gates catch blood-on-Qubit. Dest mint **Hold** | **Yes.** Type gates catch blood-on-Qubit; dest mint stays Hold | **Yes.** Type gates catch blood-on-Qubit; dest mint stays Hold (DNA from blood is a new sample, not a type rewrite) |
| R2-3. OQ-WO-6 stays OPEN | **Yes — stays Open.** Earlier LimsRun must not share asked-for analysis_id | **Yes.** OQ-WO-6 stays **OPEN** — earlier LimsRun must not share asked-for `analysis_id`. Do not teach “extract is special.” | **Yes — stays Open.** Earlier LimsRun must not reuse asked-for analysis_id (WO-7 would mint the panel Test on the parent) | **Yes — stays Open.** An earlier LimsRun that reuses asked-for analysis_id would freeze the panel Test on the parent |
| R2-4. Parser at import | **Yes.** Parser is import, not process authoring | **Yes.** Parser chosen at import, not process authoring. Process LimsRun stores `analysis_id` only | **Yes.** Parser is import, not authoring | **Yes.** Parser is import, not authoring |

**Consensus:** Leadership Confirm of R2-1…R2-4. OQ-WO-6 **stays OPEN**. Do not rewrite `9342439` Pass. No overall P2 Pass. Hold merge. Not IC50.

### Deiter (Lab Ops)

**Confirm R2-1…4.** Available routes = any chain that contains that LimsRun analysis; multi-analysis is the product. Extract is not a special assay — type gates catch blood-on-Qubit; dest mint stays Hold. Earlier LimsRun must not share asked-for analysis_id (OQ-WO-6 OPEN). Parser is import, not process authoring. Do not rewrite `9342439` Pass. Two-accept 409 and map-save same-types/different-analyses stay unsigned. Freeze skip stays OPEN. One asked-for still mints one WO — starting extract QC must not look like ELISA is on the tube. No overall P2 Pass. Hold merge. Not IC50.

### Hans (Sci CSO)

**Confirm R2-1…4.** Contain is Route matching, not Test identity: multi-analysis chains are the product, but each LimsRun keeps its own analysis_id. Type gates catch blood-on-Qubit; dest mint stays Hold (DNA from blood is a new sample, not a type rewrite). OQ-WO-6 stays OPEN: an earlier LimsRun that reuses asked-for analysis_id would freeze the panel Test on the parent. Parser is import, not authoring. Do not rewrite `9342439` Pass. Freeze skip (`{}` vs NULL) stays OPEN. Starting extract QC must not look like ELISA is on the tube. No overall P2 Pass. Hold merge. Not IC50.

### Heidi (Arch)

**Confirm R2-1…4.** Contain is Route matching: asked-for assay → any chain that has that LimsRun analysis. Multi-analysis routes are the product; each LimsRun keeps its own analysis_id. Type gates catch blood-on-Qubit; dest mint stays Hold. OQ-WO-6 stays OPEN — earlier LimsRun must not reuse asked-for analysis_id (WO-7 would mint the panel Test on the parent). Parser is import, not process authoring. Do not rewrite `9342439` Pass. Freeze skip (`{}` vs NULL) stays OPEN. One asked-for still mints one WO. Starting extract QC must not look like ELISA is on the tube. No overall P2 Pass. Hold merge. Not IC50.

### Günter (Sec CSO)

**Confirm R2-1…4.** Contain is Route matching: asked-for assay → any chain that has that LimsRun analysis. Multi-analysis routes are the product; each LimsRun keeps its own analysis_id. Type gates catch blood-on-Qubit; dest mint stays Hold. OQ-WO-6 stays OPEN — earlier LimsRun must not reuse asked-for analysis_id (WO-7 would mint the panel Test on the parent). Parser is import, not authoring. Do not rewrite `9342439`. Freeze skip stays OPEN. Hold merge. Not IC50.

---

## Contents grain / `0077` — Leadership Confirm — 2026-08-30 (live clicks)

**Full Leadership Confirm** that process assignment is a **sample in a container**. Rolf, Deiter, Hans, Heidi, Günter. Round 1 and Round 2 above are unchanged — this section does **not** rewrite them, and Round 1 / Round 2 live-clicks stay as written. Product SHA `4671ba8`; the assignment commit is `02fe95f` (migration `0077` in that commit). **Dest mint stays Hold.** Do **not** rewrite Tobias `9342439` / `8cfa2a9` / P1 Results. **OQ-WO-6 stays OPEN.** Freeze skip (`{}` vs NULL) stays **OPEN**. Route stays `test:assign`. Not a merge stamp. Overall P2 remains **not Pass**. Hold product merge to `main`. Not IC50.

### Deiter click — Contents grain

Deiter (Lab Ops), 2026-08-30, product `4671ba8` / assignment commit `02fe95f`: AC-P2-C1 **Pass**; AC-P2-C2 **Fail** — execute mints dest, does not join dest or remove source, emptied-source assign is a **201 mix-up**, and **PATCH is not a path**; dest mint Hold **Pass** — Start extract remains **Blood**, with **0 DNA**. Docs Confirm `84d2810` is not a new execute and not the click SHA. This is not a Tobias QA Pass. No overall P2 Pass.

### Product being confirmed (their words)

1. **Assign is the tube in hand.** `eln_process_samples.container_id` is required. A sample may sit in many vessels; only a **container-with-sample** goes on the process. No vessel → **422**. Two tubes for the same sample and no pick → **422**. **No silent pick** — never `first()`.
2. **Equivalent aliquot = same sample, new container.** After an equivalent aliquot, the dest container-with-sample stays on the process and the emptied inbound source comes off. **Later Start follows the dest container, not the dest type.**
3. **Dest-type mint stays Hold.** No DNA daughter; the type does **not** change. Start extract still leaves the tube **Blood**.

### Roll-up

| Grain | Lab Ops (Deiter) | CEO (Rolf) | Sci CSO (Hans) | Arch (Heidi) | Sec CSO (Günter) |
|-------|------------------|------------|----------------|--------------|------------------|
| Assign = tube in hand (`container_id` required) | **Yes.** The tech assigns the tube in hand, not an abstract sample | **Yes.** Contents grain is the product | **Yes.** Which vessel was measured is scientific | **Yes.** `container_id` NOT NULL is the grain | **Yes.** No silent pick; refuse, do not guess |
| 0 vessels / 2+ vessels → **422**, no silent pick | **Yes.** Lab-readable refusal beats a wrong tube | **Yes.** Refuse at assign | **Yes.** A guessed vessel is a wrong measurement | **Yes.** 422 both ways; never `first()` | **Yes.** Ambiguity resolves to 422, not to a pick |
| Equivalent aliquot = same sample, new container; later Start follows dest **container** | **Yes.** Tube→plate is the same material in a new vessel | **Yes.** Follow the vessel that carries the work | **Yes.** Same sample, new vessel — not a new identity | **Yes.** Follow is by container, not by type | **Yes.** Follow is a join, not a rewrite |
| Dest-type mint stays **Hold** (`_execute_transfer` new Sample) | **Hard lock.** Do not tell a tech the tube is DNA | **Hold.** Do not sell daughters in P2 UAT | **Hard lock.** Blood→DNA is a derivative, a different packet | **Punch.** `_execute_transfer` inserting a Sample with `dest_sample_type` **is** dest mint at execute | **Hold.** Minting identity at execute needs its own STRIDE |
| OQ-WO-6 OPEN; freeze skip OPEN; overall P2 not Pass | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

**Consensus:** Leadership Confirm of the Contents grain at `4671ba8` / `02fe95f`. Deiter later clicked C1 **Pass**, C2 **Fail**, and dest mint Hold **Pass** on that product/assignment SHA pair. `_execute_transfer` is not closed and must not be taught as the equivalent aliquot. OQ-WO-6 and freeze skip stay **OPEN**. No overall P2 Pass. Hold merge. Not IC50.

### Deiter (Lab Ops)

**Confirm the Contents grain.** Assign is the **tube in hand** — a container that holds the sample, not a naked sample id. No vessel is **422**. Two tubes for the same sample with no pick is **422**, lab-readable, and the app must **not** pick one for me. After an equivalent aliquot the work rides the **new vessel**; the emptied source comes off the process. Later Start follows that **container**.

**Punch:** do not teach the equivalent aliquot as a type change. The later Deiter click records C1 **Pass**, C2 **Fail**, and dest mint Hold **Pass**. Start extract leaves the tube **Blood**, with **0 DNA**. Execute still mints dest and does not join dest or remove source; emptied-source assign is a **201 mix-up**; **PATCH is not a path**. Test stays `(sample, analysis)`; the container records **which vessel was measured**, and a concentration write-through hits **that** container. Hold merge.

### Hans (Sci CSO)

**Confirm the Contents grain.** Which vessel was measured is scientific metadata, so the process must carry the container, not just the sample. An **equivalent aliquot is the same sample in a new container** — no new identity, no type rewrite. Blood→DNA is a **derivative** and a different packet.

**Punch:** **AC-P2-C2 must not mint a DNA daughter** and must not rewrite `sample_type`. If a click produces a new Sample row carrying `dest_sample_type`, that is **dest mint**, still **Hold**, and it is not what C2 tests. Extract-hold UAT **1.7 is OOB execute**, not this P2 Contents click — keep the struck DNA-daughter teaching struck and label 1.7 **OOB**. Test identity stays `(sample, analysis)`; the container is which vessel was measured, and conc write-through hits that container. OQ-WO-6 stays **OPEN**. No overall P2 Pass.

### Heidi (Arch)

**Confirm the Contents grain.** `eln_process_samples.container_id` required is the right grain: assignment is a Contents pair. Follow-on Start reads non-`removed` dest assignments and follows the dest **container**, not the dest **type**.

**Punch — dest mint is still open in code.** `_execute_transfer` still inserts a **new Sample** with `dest_sample_type` (which can be DNA). Deiter C2 **Fail** records that execute mints dest and does not join dest or remove source. That is **dest mint at execute** — a write of identity — and the target equivalent aliquot remains **same sample, new container**. Do not teach C2 or PATCH as a shipped dest-follows path. Route stays `test:assign`. Freeze skip stays **OPEN**.

### Günter (Sec CSO)

**Confirm the Contents grain.** No new permission — Route stays `test:assign`, Start stays `experiment:manage`. Assign refusing on 0 or 2+ vessels is the correct failure mode: **no silent pick**, never `first()`, 422 with a lab-readable code.

**Punch:** minting a Sample at execute is a **write of identity**, not a join, and needs its own threat model before anything scores it. **Dest mint stays Hold** — no execute rewrite of `sample_type`, no new DNA row taught as shipped. Extract-hold **1.7 is OOB**, not this P2 click. OQ-WO-6 stays **OPEN**. Hold product merge to `main`. Not IC50.

### Open questions after this Confirm

| ID | Status |
|----|--------|
| OQ-WO-4 / OQ-TAT-1 / OQ-WO-5 | **Leadership Confirm — Round 1 only. Do not restamp.** OQ-WO-5 remains the Round 1 handoff Confirm; **`0077` / dest mint is not closed through that row.** |
| OQ-WO-6 | **OPEN.** Earlier LimsRun must not share asked-for `analysis_id`. |
| Freeze skip (`{}` vs NULL) | **OPEN.** |
| Dest-type mint (`_execute_transfer` new Sample with `dest_sample_type`) | **Hold.** Not closed by this Confirm. |
| AC-P2-C1 / AC-P2-C2 | Deiter click at `4671ba8` / `02fe95f`: C1 **Pass**; C2 **Fail**. Not unsigned. Not a Tobias QA Pass. |
| Overall P2 | **unsigned / not Pass.** Hold merge to `main`. |

---

## Leadership Confirm of Deiter’s Contents click — 2026-08-30

**Full Leadership Confirm** of Deiter’s click. Rolf, Hans, Heidi, Günter. Round 1, Round 2, and the Contents-grain Confirm above stay as written — this section does **not** rewrite them. Deiter remains the click. Product SHA `4671ba8` / assignment commit `02fe95f`. Wilhelmina folded the C2 Fail into sketch **`a3741d1`** and requirements **`60a9447`**. Docs Confirm `84d2810` is not a new execute and not the click SHA. Do **not** rewrite Tobias `9342439` / `8cfa2a9` / P1 Results. Do **not** invent a Tobias Pass for C1/C2. C1/C2 are **not** unsigned. Grok Build owns dest-join / source-remove. Not a merge stamp. Overall P2 remains **not Pass**. Hold product merge to `main`. Not IC50.

| Slice | Confirm |
|-------|---------|
| AC-P2-C1 | **Pass** (Deiter click, `4671ba8` / `02fe95f`) |
| AC-P2-C2 | **Fail** (Deiter click; Leadership restamp of that Fail on `02fe95f`) |
| Dest mint Hold | **Pass** — still Blood, **0 DNA**. Different punch from C2 Fail. |
| Overall P2 | **unsigned / not Pass** |

**Consensus:** Confirm Deiter C1 **Pass**, C2 **Fail**, dest mint Hold **Pass**. C1/C2 are signed. Dest never lands on `eln_process_samples`; emptied-source assign **201** is leftover amount-0 Contents / leftover process-join, not dest-follow. Later Start via `_continuing_assignments` rides the emptied parent. **PATCH is not a path.** Dest mint Hold is a different punch. Coding stays **Grok Build**. OQ-WO-6 and freeze skip stay **OPEN**. Hold merge. Not IC50.

### Rolf (CEO)

**Confirm Deiter’s click.** C1 **Pass**. C2 **Fail**. Dest mint Hold **Pass** (still Blood, 0 DNA). QA restamps that Fail on `02fe95f` — do not treat C1/C2 as unsigned. Docs Confirm `84d2810` is not a new execute. No overall P2 Pass. Hold merge. Not IC50. Grok Build owns dest-join / source-remove.

### Hans (Sci CSO)

**Confirm the Fail holds.** Dest not on the process; emptied source still assignable (201) is the mix-up. Later Start would still follow the parent tube; results would not be attributable to the dest vessel. Dest mint Hold remains a different punch (still Blood, 0 DNA). Do not rewrite `9342439`. No overall P2 Pass.

### Heidi / Mathilda / Wilhelmina (Arch / Dev)

**Confirm the Fail holds.** Execute never writes the same-sample dest container onto `eln_process_samples`; join/release no-op without `entry.process_step_id`, so later Start via `_continuing_assignments` rides the emptied parent. Emptied-source assign **201** is leftover Contents at amount 0 (`_contents_for_sample` does not require remaining volume) — it must **422**, not dest-follow. Follow has to land in the **execute txn**: retarget `container_id`, or remove source then insert the dest pair. PATCH of `eln_process_samples` is not a path. Dest mint Hold stays Hold — a new Sample with `dest_sample_type` is not this fix. Equivalent aliquot is same sample, new container. Coding stays Grok Build.

### Günter (Sec CSO)

**Confirm the Fail holds.** Emptied-source assign 201 is a leftover process-join — the wrong tube stays on the instance. Dest never lands on `eln_process_samples`. Dest mint Hold is a different punch. Hold product merge to `main`. Not IC50.

---

## Honesty fold — dest-follow on `1572071` (unsigned until Tobias) — 2026-08-31

Short note. Does **not** rewrite Round 1, Round 2, Contents-grain Confirm, or Deiter click Results above.

Dest-follow is **in code** on product SHA **`1572071`** (`15720716c7cc927f1b498602ea87dec8a2bee85b`). Live AC-P2-C2 is **same-type dest-follow only** and remains **unsigned** until Tobias clicks:

- Same dest type = **same sample, additional container**.
- `_follow_destination_in_process` may retarget `container_id` only on the same-sample additional-container path.
- Different dest type = **new derivative sample** in a new container (`parent_sample_id`). The parent **Sample row** stays for lineage, keeps its original type, and keeps work attributable to the parent type. Do not rewrite `sample_type` or retarget the parent Sample onto the destination tube.
- For both destination grains, the destination sample + destination container pair lands on `eln_process_samples` in the execute transaction; the inbound source assignment becomes `removed`. “Parent stays” never means the parent process assignment stays.
- Dest mint Hold is lifted only for type-changing execute. Deiter’s dest mint Hold **Pass** on `02fe95f` and dest-type mint Hold on `9342439` remain history of Start extract still Blood / **0 DNA**, not a ban on type-changing derivative mint. Route / Start / map-save still mint **zero** daughters.
- Test identity remains `(sample, analysis)`; the process container records which vessel carries the work.

Deiter C2 **Fail** on `02fe95f` stands as signed history. Do **not** write C2 Pass. Do **not** teach dest-follow as shipped. OQ-WO-6 and freeze skip stay **OPEN**. Overall P2 unsigned. Hold product merge to `main`. Not IC50.

---

## Leadership Confirm — dest-type split — 2026-08-31

**Full Leadership Confirm** from Rolf, Deiter, Hans, Heidi, and Günter. This Confirm does **not** rewrite Round 1, Round 2, the Contents-grain Confirm, Deiter `02fe95f` Results, or Tobias `9342439` AC-P2-9..11 Pass Results. It is not a C2 Pass or an overall P2 Pass.

1. **Same type:** aliquot/pool destination is the same Sample in an additional container. The `1572071` `container_id` retarget belongs only to this same-type C2 path.
2. **Different type:** aliquot/pool execute mints a new Sample in a new container with `parent_sample_id`. The parent Sample row stays; its `sample_type`, Tests, and work attributable to the parent type stay on that parent. Retargeting the parent onto the destination tube would put a DNA tube on the Blood Sample and is forbidden.
3. **Execute transaction:** for a type-changing destination, execute mints and joins the destination Sample + destination container pair and marks the inbound process assignment `removed`. Günter’s lock: after the later Start, the process sample is only that execute-minted destination pair.
4. **Mint boundary:** dest mint Hold lifts only for type-changing aliquot/pool execute. Route, Start, and map-save still mint zero daughters. The live lock is the destination type declared on the aliquot/pool entry.
5. **Two clicks:** same-type C2 dest-follow and extract-hold UAT 1.7 DNA-daughter execute remain separate clicks. Live C2 on `1572071` remains unsigned until Tobias; extract-hold 1.7 remains OOB with no Result stamp.
6. **Historical Hold:** `9342439` Dest-type mint Hold is history of Start extract (still Blood, 0 DNA) and Route/Start minting zero daughters. It is not a live ban on type-changing execute.

OQ-WO-6 and freeze skip stay **OPEN**. Deiter C2 **Fail** on `02fe95f` stays signed history. Overall P2 remains unsigned / not Pass. Hold product merge to `main`. Not IC50.

---

## Live restamp SHA pinned to `570bbc0` — 2026-08-31

Docs-only honesty fold (Rolf). Does **not** rewrite Round 1, Round 2, the Contents-grain Confirm, Deiter `02fe95f` Results, or Tobias `9342439` AC-P2-9..11 Pass Results. Not a Pass and not a merge vote.

The two preceding 2026-08-31 sections are retained verbatim as sent. Where they read “live … `1572071`” or “1.7 remains OOB with no Result stamp”, this section supersedes them: the live restamp SHA is `570bbc0` and 1.7 is the AC-P2-C3 click.

1. **Live click SHA is `570bbc0`** (`570bbc01ff50fdac2d529448ceb95683c535401f` — docs/uat split of C2 and C3 into numbered clicks). The live dest-follow stamp heading in [`UAT_Scripts/uat-post-receive-work-spine.md`](../../UAT_Scripts/uat-post-receive-work-spine.md) now reads `570bbc0`.
2. **`1572071` is the implementation SHA**, not the current click SHA. It may still be cited as where the dest-follow execute-txn work landed. No live block claims it as the live restamp.
3. **C2 and C3 are two unsigned clicks.** AC-P2-C2 is same dest type (tube → plate). AC-P2-C3 is different dest type (Blood → DNA), the same click as extract-hold UAT **1.7**. Neither is Pass. Do not teach Pass.
4. **The split is the dest type on the aliquot/pool entry.** Same type → same Sample, extra container, `container_id` retarget. Different type → new derivative Sample with `parent_sample_id`; the parent Sample stays with its own type; the inbound assignment is `removed`. Route / Start / map-save still mint **zero** daughters.
5. **Hold-as-ban stays punched (PR 103).** `9342439` Dest-type mint Hold and Deiter’s `02fe95f` Hold **Pass** remain Start-extract still Blood / **0 DNA** **history**. No doc carries a live “dest mint Hold” ban on type-changing aliquot/pool execute.
6. **`02fe95f` C2 Fail and the `9342439` Pass Results are byte-stable.** Nothing in this fold re-scores them.

OQ-WO-6 and freeze skip stay **OPEN**. Overall P2 remains unsigned / not Pass. Hold product merge to `main`. Not IC50.

---

## Wilhelmina punch — `570bbc0` is UAT numbering, not execute — 2026-08-31

Docs-only. Does **not** rewrite Round 1, Round 2, the Contents-grain Confirm, Deiter `02fe95f` Results, or Tobias `9342439` AC-P2-9..11 Pass Results. The preceding “Live restamp SHA pinned to `570bbc0`” section is retained as sent; this punch supersedes any reading of `570bbc0` as a product execute SHA.

1. **`570bbc0` is the UAT split + pytest**, not a new execute. Do **not** teach it as a product execute SHA.
2. **C2/C3 dest-follow execute remains `1572071`.** Unsigned C2/C3 clicks are numbered on `570bbc0`; the execute txn is `1572071`.
3. **C2** retargets `container_id` on the same sample. **C3** mints a derivative (`parent_sample_id`) + dest container, joins dest, and marks source `removed`. Parent `sample_type` is not rewritten; the dest tube is not the parent sample.
4. Do **not** write Pass. Route / Start / map-save still mint **zero** daughters. PATCH is not a path.
5. Hold merge until QA clicks C1/C2/C3. OQ-WO-6 and freeze skip stay **OPEN**.

Not IC50.

---

## Marc lock — no dest until aliquot/pool execute — 2026-08-31

Docs-only. Does **not** rewrite Round 1, Round 2, the Contents-grain Confirm, Deiter `02fe95f` Results, or Tobias `9342439` AC-P2-9..11 Pass Results. The Wilhelmina punch above is retained as sent. Not Pass.

1. **No sample/container mint until aliquot/pool execute.** Route / Start / map-save / receive / asked-for mint **zero**. Plan may declare dest type; dest exists only after execute. Dest type on the plan is catalog intent until execute. Do **not** teach dest existing at Route / Start / map-save.
2. **C2 execute** = extra container, same sample. **C3 execute** = new derivative; parent Sample stays. **Fail C3 if dest tube is on the blood sample.**
3. **`570bbc0` does not inherit C2 Pass or Fail.** It is the UAT split + pytest, not a new execute. Live C2/C3 remain **unsigned** until Tobias. Execute txn remains `1572071`.
4. Hold-as-ban stays punched. OQ-WO-6 and freeze skip stay **OPEN**. Hold merge. Not IC50.

---

## Leadership Confirm — mint-only-at-execute — 2026-08-31

**Full Leadership Confirm** from Rolf, Deiter, Hans, Heidi, and Günter. Does **not** rewrite Round 1, Round 2, the Contents-grain Confirm, Deiter `02fe95f` Results, or Tobias `9342439` AC-P2-9..11 Pass Results. The Marc lock and Wilhelmina punch above are retained as sent. Not Pass. Not a merge vote.

1. **Dest sample/container exists only after aliquot/pool execute.** Route / Start / map-save / asked-for mint **zero** daughters. Plan dest type is catalog intent, **not** a Sample.
2. **Receive still mints identity + first vessel.** That is **not** dest mint. A tech must **not** scan DNA before extract execute.
3. **C2 and C3 are execute clicks**, unsigned until Tobias. `570bbc0` does **not** inherit `1572071` C2 Pass or Fail (UAT split + pytest; execute joints still `1572071`). Same click as extract-hold 1.7 for C3. Two clicks.
4. **C2 execute:** extra container, same sample; dest joins; source off; emptied-source **422**; later Start follows dest.
5. **C3 execute:** new derivative (`parent_sample_id`); parent stays Blood; dest sample + container on the process; inbound source **removed**. **Fail C3** if dest tube lands on the blood Sample, parent `container_id` is retargeted, or later Start follows blood.
6. **Günter:** after execute, the process-sample is **only** that execute-minted dest.

OQ-WO-6 and freeze skip stay **OPEN**. Hold merge to `main`. Not IC50.

---

## Marc lock — one asked-for per process (pending Leadership overwrite) — 2026-08-31

**Marc lock pending Leadership overwrite.** Docs-only. **Not Leadership Confirm.** If Leadership later Confirms, that is a later fold. Does **not** rewrite Round 1, Round 2, Contents-grain Confirm, Deiter `02fe95f` Results, Tobias `9342439` AC-P2-9..11 Pass, dest-type split Confirm, mint-only-at-execute Confirm, or the `570bbc0` restamp notes. Not Pass. Not a merge vote. Not IC50.

1. **One asked-for per process instance.** A process instance is bound to one asked-for row. Do not teach one process carrying two asked-for assays. Round 2 “extract QC + Qubit + ELISA” is Route matching (a chain may list several LimsRun analyses). It is **not** two asked-for assays on one process.
2. **Supporting QC = other analyses, own Tests.** QC is not a second asked-for on the same process. QC analyses get their own Tests `(sample, analysis)`. Do not fold QC into the asked-for `analysis_id` on the extract LimsRun.
3. **DNA extract once (C3).** Type-changing execute mints the DNA Sample once. That DNA sample may **join many work orders**, each with **one asked-for**. Do not teach extract-every-WO. Do not teach one DNA sample = one WO forever.
4. **Freeze is per Test `(sample, analysis)`.** First LimsRun start writes `asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. Freeze skip stays **OPEN** until classic `/tests` leaves NULL or a freeze marker exists. Do not close freeze skip. Do not teach skip-on-`{}` as shipped.
5. **OQ-WO-6 stays OPEN** until extract LimsRun **cannot** share asked-for `analysis_id`. Analysis-in-chain does not close it. Extract must not be the panel assay or it freezes the panel Test on the parent (usually blood).

Click SHA for C2/C3 remains `570bbc0`. Tobias QA restamp stays **unsigned** until Tobias Results land. Deiter Met is Lab Ops only. C2 leftover inbound volume is not Fail; emptying is an edge. `02fe95f` / `9342439` untouched. Hold Pass is Start-extract still Blood / 0 DNA history, not a ban on C3. Route two-accept 409 stays OPEN/unsigned. No overall P2 Pass. Hold merge of `feat/work-order-p2` to `main`.

---

## Leadership Confirm — OQ-WO-6 extract is a process; exactly one asked-for LimsRun — 2026-08-31

**Full Leadership Confirm** from Rolf, Deiter, Hans, Heidi, and Günter. Docs-only. Does **not** rewrite Round 1, Round 2 (including R2-3 “OQ-WO-6 stays Open” history), Contents-grain Confirm, Deiter `02fe95f` Results, Tobias `9342439` AC-P2-9..11 Pass, dest-type split Confirm, mint-only-at-execute Confirm, or the `570bbc0` restamp notes. The Marc lock — one asked-for per process (pending overwrite) above is retained for points 1–4; this Confirm **overwrites** that lock’s OQ-WO-6 extract wording. Not Pass. Not a merge vote. Not IC50.

### Confirmed product

1. **Extract is a process.** Experiment / aliquot-pool **execute**; derivative dest (C3 DNA dest is that execute). Manual or robot does **not** make it a LimsRun. Extract has **no** asked-for `analysis_id`. Do **not** teach extract as a LimsRun that may carry “other analyses.”
2. **Exactly one asked-for LimsRun** in the route. That LimsRun’s `analysis_id` is the asked-for analysis. That LimsRun is the **assay step** (e.g. ELISA), not extract / library prep.
3. **Extract and Qubit may still sit in the chain:** extract as **process**, Qubit as **supporting LimsRun** (other analysis, own Test). A route may list several LimsRun analyses; only one of them is the asked-for assay.
4. **Map-save / Route 422** if the asked-for analysis appears **0 or 2+** times among LimsRuns. Two ELISA LimsRuns are **refused** — they would share one Test `(sample, ELISA)`. That is **not** QC.
5. **OQ-WO-6 for extract CLOSES.** Cardinality 1 cannot land on extract because extract is not a LimsRun. Extract cannot wear ELISA. Hans’s punch (1-count on extract still freezes the panel Test on blood) is **closed** by this grain. Strike leftover “extract LimsRun must not share asked-for `analysis_id`” as if extract were a LimsRun. Remaining OPEN on `analysis_id` is **not** extract-as-ELISA.
6. **Keep prior lock:** one asked-for per process instance; DNA extract once (C3); that DNA sample may join many work orders, each with one asked-for. Supporting QC = other analyses, own Tests (Qubit), not a second asked-for on the same process.

**Freeze skip** (`{}` vs NULL) stays **OPEN**. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a freeze marker. Do **not** teach skip-on-`{}` as freeze. Tobias C2/C3 remain **unsigned**. Deiter Met on `570bbc0` is Lab Ops only. `9342439` / `02fe95f` / `8cfa2a9` untouched. No overall P2 Pass. Hold merge of `feat/work-order-p2` to `main`. Not IC50.

### Roll-up

| Ask | Lab Ops (Deiter) | CEO (Rolf) | Sci CSO (Hans) | Arch (Heidi) | Sec CSO (Günter) |
|-----|------------------|------------|----------------|--------------|------------------|
| Extract is a process, not a LimsRun; no asked-for `analysis_id` | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Exactly one asked-for LimsRun = assay step | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Extract (process) + Qubit (supporting LimsRun) may sit in the chain | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Map-save / Route **422** on asked-for count 0 or 2+; two ELISA LimsRuns refused | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| OQ-WO-6 extract punch **CLOSED**; Hans 1-count-on-extract freeze **closed** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Freeze skip OPEN; no overall P2 Pass; hold merge | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

**Consensus:** Leadership Confirm of the extract-is-a-process grain and the exactly-one asked-for LimsRun gate. OQ-WO-6 for extract **CLOSED**. Freeze skip stays **OPEN**. Do not rewrite `9342439`. Tobias C2/C3 unsigned. Hold merge. Not IC50.

### Deiter (Lab Ops)

**Confirm.** Extract is the process on the bench — aliquot/pool execute, DNA dest — not a LimsRun. The ELISA tube is the assay LimsRun. Qubit can sit as a supporting run. Two ELISA LimsRuns is a mix-up; refuse 422. Do not tell a tech extract “is ELISA.” Freeze skip stays OPEN. Hold merge.

### Hans (Sci CSO)

**Confirm.** Assay identity lives on exactly one LimsRun. Extract has no `analysis_id`, so it cannot freeze the panel Test on blood. The old 1-count-on-extract punch is closed by this grain. Two ELISA LimsRuns would share one Test `(sample, ELISA)` — that is not QC. Qubit is a different analysis, own Test. Freeze skip (`{}` vs NULL) stays OPEN.

### Heidi (Arch)

**Confirm.** Cardinality 1 is counted among **LimsRuns** only. Extract is `eln_process` / experiment execute, not a run row. Map-save and Route **422** when asked-for `analysis_id` appears 0 or 2+ times on LimsRuns. Do not keep a required `analysis_id` on extract. Freeze skip stays OPEN. Route stays `test:assign`.

### Günter (Sec CSO)

**Confirm.** No silent `first()` when two ELISA LimsRuns share one Test. Refuse 422; do not guess which run is the assay. Extract is not a write of Test identity. Freeze skip stays OPEN. Hold product merge to `main`. Not IC50.

### Rolf (CEO)

**Confirm.** One extract→assay→report route is still the product: extract as process, Qubit optional as supporting LimsRun, ELISA as the one asked-for assay LimsRun. OQ-WO-6 extract punch closes. Do not sell freeze skip as shipped. No overall P2 Pass. Hold merge. Not IC50.

---

## Marc Confirm — supporting LimsRuns in the same route (Qubit / Nanodrop) — 2026-08-31

**Marc Confirm.** Docs-only. Does **not** rewrite the Leadership Confirm wall above (extract-as-process + exactly-one asked-for LimsRun still stands). Does **not** rewrite Round 1, Round 2, `9342439`, `02fe95f`, or `570bbc0` restamp notes. Not Pass. Not IC50.

1. **Qubit / Nanodrop / etc. are supporting LimsRuns in the same route** as the asked-for assay. They are other `analysis_id`s with their **own** Tests `(sample, analysis)`.
2. Asked-for analysis still appears **once**, on the **assay** LimsRun. Supporting runs do not take that `analysis_id`.
3. **Extract remains a process**, not a LimsRun, and has **no** asked-for `analysis_id`. Do **not** put Nanodrop (or Qubit) on extract. Do **not** invent a second asked-for for QC.
4. Freeze skip (`{}` vs NULL) stays **OPEN**. Hold merge of `feat/work-order-p2` to `main`. Not IC50.

---

## Leadership Confirm (Rolf, Marc) — supporting LimsRuns in the same route as the asked-for assay — 2026-08-31

**Leadership room Confirm (Rolf, Marc).** Docs-only. Does **not** rewrite the extract-as-process + exactly-one asked-for LimsRun Confirm wall above. Does **not** rewrite Round 1, Round 2, `9342439`, `02fe95f`, or `570bbc0` restamp notes. Not Pass. Not IC50.

The Marc Confirm immediately above is retained. This Confirm is the **general** supporting-QC rule — sequencing is one example, not the only path.

1. Qubit / Nanodrop / etc. sit as **supporting LimsRuns in the same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …).
2. Supporting runs are other `analysis_id`s with their **own** Tests `(sample, analysis)` and their **own** params freeze. Do **not** invent a second asked-for for QC. Do **not** put Nanodrop on extract.
3. The asked-for analysis still appears **once**, on the **assay** LimsRun.
4. **Extract stays a process**, not a LimsRun, no asked-for `analysis_id`.
5. Freeze skip (`{}` vs NULL) stays **OPEN**. Hold merge of `feat/work-order-p2` to `main`. Not IC50.

