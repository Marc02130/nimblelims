# Leadership send: P2 route lock (ordered processes, analysis in chain, type handoff)

**Date:** 2026-08-30  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO)  
**Ask:** **CEO Confirmed** (all five asks). Still pending **Deiter / Hans / Heidi / Günter overwrite-or-confirm**. Not a merge stamp. Not a full Leadership lock. Overall P2 UAT remains unsigned.  
**Implement gate:** **OPEN for P2 coding on `feat/work-order-p2`.** Merge to `main` **held** until signed UAT Pass.  
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)

**Code:** `feat/work-order-p2`. Latest **signed** AC-P2 is `8cfa2a9` (per-AC; overall **not Pass**; PR **#92** honesty fold). **This commit** is `9342439` (`93424396ce3d02f01a8a8388abda39ae6ebf8010`): analysis is not a map field; Route matches a LIMS Run in the chain; process *x* → *x+1* emerging-type handoff; create-route UI shows types/analyses/emerging types.

**UAT:** do **not** rewrite `8cfa2a9` / `b005cfe` / `9c4f9da` / `3b56cfb` / P1. Live AC-P2 stamp on `9342439` in `UAT_Scripts/uat-post-receive-work-spine.md` covers analysis-in-chain + display + handoff and stays **unsigned**. Tobias restamps on this committed SHA. Overall P2 remains **not Pass**.

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

**CEO is the only live Confirm.** Round 1 above remains persona-applied history. Do **not** read Lab Ops / Security / Sci CSO round-1 cells as live clicks. Still pending **Deiter / Hans / Heidi / Günter overwrite-or-confirm**. Not a full Leadership lock. Not a merge stamp.

| Ask | CEO Confirm |
|-----|-------------|
| 1. Analysis in the route, not on the map | **Yes.** Analysis in the route, not on the map. Asked-for ELISA may Route onto extract → ELISA → report because ELISA is a LIMS Run in that chain — not because an admin picked ELISA on the map. One extract→assay→report route is the product. |
| 2. Overlap 409 | **Yes.** Two extract routes, same TAT, same inbound types, **different** LIMS Run analyses (ELISA vs NGS) both save. Two ELISA extracts colliding is the bug. |
| 3. Handoff 422 | **Yes.** Extract dest DNA → Qubit that only accepts plasma **must not save**. |
| 4. Dest mint stays Hold | **Hold.** Dest mint stays Hold. Handoff is catalog intent, not “blood became DNA at execute.” Do not sell daughters in P2 UAT. |
| 5. UAT restamp | **Restamp now.** Do not wait dest-type mint to score P2. QA restamps authoring + Route + freeze on committed SHA `9342439`. Do **not** UAT blood→DNA daughter. |

---

## Open questions to stamp

| ID | Status until you reply | Proposed |
|----|------------------------|----------|
| OQ-WO-4 | **CEO Confirm** — pending Deiter/Hans/Heidi/Günter overwrite-or-confirm. Not full Leadership Decided. | No map analysis field; Route matches a LIMS Run in the chain |
| OQ-TAT-1 | **CEO Confirm** — pending same. | 409 = TAT ∩ first-step types ∩ LIMS Run analyses |
| OQ-WO-5 | **CEO Confirm** (was Open) — pending same. Dest mint remains Hold. | Process *x* emerging type must be accepted by *x+1* |

Deiter / Hans / Heidi / Günter: overwrite round 1 if needed. Then QA restamps `UAT_Scripts/uat-post-receive-work-spine.md` on `9342439`. Live AC-P2 stays **unsigned**. Not IC50.
