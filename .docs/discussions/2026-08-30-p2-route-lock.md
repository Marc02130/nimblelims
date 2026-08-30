# Leadership send: P2 route lock (ordered processes, analysis in chain, type handoff)

**Date:** 2026-08-30  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO)  
**Ask:** Round 1 remains **Leadership Confirmed** (Rolf, Deiter, Hans, Heidi, Günter; all five asks). Round 2 is **CEO Confirm** (R2-1…R2-4) pending Deiter / Hans / Heidi / Günter overwrite-or-confirm. Not a full Leadership lock for Round 2. Not a merge stamp. Overall P2 UAT remains unsigned.  
**Implement gate:** **OPEN for P2 coding on `feat/work-order-p2`.** Merge to `main` **held** until signed UAT Pass.  
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)

**Code:** `feat/work-order-p2`. Latest **signed** AC-P2 is `8cfa2a9` (per-AC; overall **not Pass**; PR **#92** honesty fold). **This commit** is `9342439` (`93424396ce3d02f01a8a8388abda39ae6ebf8010`): analysis is not a map field; Route matches a LIMS Run in the chain; process *x* → *x+1* emerging-type handoff; create-route UI shows types/analyses/emerging types.

**UAT:** do **not** rewrite `8cfa2a9` / `b005cfe` / `9c4f9da` / `3b56cfb` / P1. Tobias signed **AC-P2-9..11 Pass** on `9342439` (local compose, down after; docs merge `50c1f24` does not change the click SHA). Deiter / Hans / Heidi / Günter confirmed that restamp (honesty, **not** a merge vote): later-step type-gate **Met**; AC-P2-11 / handoff Pass is **map-save only**; dest mint **Hold**; freeze skip **OPEN**; extract `analysis_id` **OPEN**; Route stays `test:assign`. Overall P2 remains **not Pass**.

**Dest-type Hold:** execute still does **not** mint a DNA daughter. Authoring may still read a declared aliquot/pool dest on a template.

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

**Full Leadership Confirm** of all five asks + OQ-WO-4 / OQ-TAT-1 / OQ-WO-5. Rolf (CEO Confirm above), then Deiter, Hans, Heidi, Günter. Round 1 remains persona-applied history. Dest-type mint remains Hold. Not a merge stamp. Tobias signed **AC-P2-9..11 Pass** on `9342439` after this Confirm. Restamp notes (Deiter / Hans / Heidi / Günter) after that click are in the section below — honesty, **not** a merge vote. Overall P2 remains **not Pass**.

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
| OQ-WO-6 | **OPEN.** CEO Confirm that it **stays Open** (R2-3). Pending Deiter / Hans / Heidi / Günter overwrite-or-confirm. | Earlier LimsRun in the chain must **not** share asked-for `analysis_id`. Do not teach extract-as-special-assay. |

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

Rolf’s Confirm of R2-1…R2-4. Round 1 remains **Leadership Confirmed**. This is **CEO Confirm only** — pending Deiter / Hans / Heidi / Günter overwrite-or-confirm. Not a full Leadership lock for Round 2. Not a merge stamp. Do **not** rewrite Tobias `9342439` / `8cfa2a9` Results. Freeze skip stays **OPEN**. Dest mint **Hold**. Overall P2 remains **not Pass**. Not IC50.

| Ask | CEO Confirm |
|-----|-------------|
| R2-1. Asked-for assay → any route that **contains** that LimsRun analysis | **Yes.** Asked-for assay → any route whose chain **contains** that LimsRun analysis. Multi-analysis routes are the product. One asked-for row → one work order. |
| R2-2. Type gates catch blood-on-Qubit; dest mint Hold | **Yes.** Extract is not a special assay. Type gates catch blood-on-Qubit. Dest mint **Hold**. |
| R2-3. OQ-WO-6 stays OPEN | **Yes.** OQ-WO-6 stays **OPEN** — earlier LimsRun must not share asked-for `analysis_id`. Do not teach “extract is special.” |
| R2-4. Parser at import | **Yes.** Parser chosen at import, not process authoring. Process LimsRun stores `analysis_id` only. |

Send: this file, Round 2. OQ-WO-4 / OQ-TAT-1 / OQ-WO-5 stay **Leadership Confirm** from round 1.
