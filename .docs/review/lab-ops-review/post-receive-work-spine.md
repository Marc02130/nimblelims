# Lab Ops Review (SVP): Post-receive work spine

**Date:** 2026-08-28  
**Status:** **Accept with conditions**  
**Reviewer persona:** SVP Lab Ops (Deiter)  
**Packet:**  
- Requirements: [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
- Tech sketch: [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
- Schema: [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
- PRD: [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
- Spec: [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
- Open questions: [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Related:**  
- Framework stamps: [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md) (WO-1…WO-7, FW-0/FW-2)  
- Dest-type Hold: [`.docs/review/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) · [extract-hold-dest-type Lab Ops](extract-hold-dest-type.md)  
- AR CORE Lab Ops: [atomic-receive.md](atomic-receive.md)

---

## 1. Executive summary

Atomic receive CORE is shipped. Tubes land as **Available for Testing** with **zero Tests**. That is correct accessioning. It is **not** a lab. The missing middle is: what was asked, what the bench must do, then execute on Process / Experiment / LimsRun.

**The spine is the right lab shape.** Do not collapse it:

| Layer | Is | Is not |
|-------|----|--------|
| Asked-for (P1) | Request: analysis + TAT + params | Work plan, Test, Process, LimsRun |
| Routing + `work_order` (P2) | Ordered `process_definition[]` work plan | A Test row or unordered bag |
| Execute (shipped) | Process → Exp and/or LimsRun | A third engine |
| Test (WO-7) | Minted at **LimsRun start** | Minted at receive / asked-for / WO save / publish |
| SOP Apply (P4) | Writes a **process definition** | Blood → DNA daughter → Qubit E2E |

P1 as a **lake** is bench-honest: a tech can record “ELISA, 5-day, these plasmas” without lying that work has started. That is how a CRO request actually arrives. **Asked-for must not be the work plan.** Extract-then-assay is the work. If `/asked-for` looks like today’s Tests page, techs will treat it as Tests and we have re-opened WO-7 under a new name.

**Qubit-on-blood must refuse.** If Qubit is first, Route compares the blood sample’s current type with the derived first-step DNA allow-list and refuses before mint. If Qubit is later, its step start refuses while current type is still blood. Named error, not a broken sample. Map authoring has no sample-type picker and must not read `sample_type_transitions` as proof that an earlier step minted DNA.

**SOP Apply must not claim dest-type Hold is fixed.** P4 closing the template-only lie is necessary and welcome. It does not mint a DNA daughter. NCI 23113 → 22975 remains Hold. Do not seed routing or UAT that pretends otherwise.

**Verdict: Accept with conditions.** P1 may implement. P2 must take L2–L4 into the sketch before coding (step-start type gate, params travel, ordered process steps). P4 may write process definitions with L5 copy. Dest-type E2E is a different packet.

---

## 2. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| **Bench reality** | **8** | Request ≠ work is how SOP labs operate. P1 lake without a work list is honest **if** copy does not imply work started. P2 is the “what’s next?” queue (L-OPS-5). Multi-sample asked-for is how a rack is ordered (L1). |
| **Material & sample integrity** | **8** | Does not reopen receive. Does not mint Tests on the parent at order time. Qubit-on-blood refuse (L2) is the integrity gate. Dest type stays out — correctly. |
| **Chemistry / sequencing** | **6** | ELISA params catalog may be empty OOB (acceptable for P1). Qubit path is named but dest-type Hold still blocks dsDNA HS on a daughter. No indexing/pooling in this packet. |
| **Gating & compliance habits** | **8** | Zero acceptable route 422; ambiguous route 409; TAT overlap 409; publish refuses missing Test. |
| **Template → instance** | **7** | Routing snapshots ordered process-definition ids; first starts now, later definitions start later (L4). |
| **Competitive floor** | **7** | Order line + routing pack + work list is table-stakes vs commercial LIMS. P1 alone is a request log — do not sell it as a worklist. Parser setup (P5) is the ops skill-floor fix (R-8). |
| **Containers / amount** | **N/A (6 contextual)** | Vessels already exist from AR. Amount/volume/pool execute is extract-hold / entries — out of this packet. |
| **Cohort / queue** | **6** | Explicit Route snapshots ordered definitions. First process starts first; later starts advance. |
| **Instrument boundary** | **8** | Assay = LimsRun with analysis; extract = Experiment; parser import = no LLM; Test at LimsRun start (WO-7). Classic type-a-number remains (WO-4) on an existing Test only. |

**Overall lab readiness:** **7.5/10** for the spine with conditions. **P1 is implementable.** P2 is not, until L2–L4 are in the sketch.

---

## 3. Conditions (must land with the named phase)

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **L1** | **P1** | **Asked-for is a request lake, not the work plan.** Copy: “Asked-for” / “requested analysis,” never “assign test,” “create test,” “start work,” or “order process.” Saving asked-for creates **zero** Tests, Results, Processes, Experiments, LimsRuns, work_orders. **No Start / Execute CTA** on a `requested` row. UI is **not** `/receive`; receive still **422** on non-empty `analysis_ids`; do not call `_create_tests` / `_create_asked_for_tests`. **Multi-sample:** one operator action (same analysis + TAT + params) can write asked-for for a **set** of received samples (rack of plasma ELISA). API may remain one row per sample. | If this page is Tests with a new name, WO-7 is dead on arrival. One-by-one click per tube fails a real rack. |
| **L2** | **P2** | No map type picker. Match analysis + TAT, then current type against each row’s first process / first Experiment-LimsRun list. Zero acceptable → 422; multiple → 409. Map save/Route do not inspect later processes/steps. Later starts gate current type; empty fails closed. Dest-type Hold remains. | Refuses invalid first assignment without blocking extract-first + later Qubit routes. |
| **L3** | **P2** | **Params travel.** Asked-for `params` snapshot onto the Test at **LimsRun start** (WO-7) and freeze. Tech does not re-type cell line / assay params to run the assay. Empty defs remain empty-object-only (OQ-AF-3). | Framework stamp: params travel. Cell line on the order that dies at the bench is a side process. |
| **L4** | **P2** | **Ordered `process_definition[]` is the work plan.** Snapshot at mint. Start instantiates first process only; later starts advance in order under existing AuthZ. UI shows process and step order. | Otherwise sequence and handoff are ambiguous. |
| **L5** | **P4** | **SOP Apply writes a process definition. It does not close dest-type Hold.** Apply success / manuals / UAT: draft process definition with typed steps; human save; never silent auto-activate. **Do not** say the NCI extract → Qubit path is runnable. **Do not** UAT blood → DNA daughter → Qubit on the daughter in this packet. Dest type remains [extract-hold-dest-type](../requirements/extract-hold-dest-type.md) / [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md). | Selling point is “Apply is not a lie.” Selling point is **not** “daughters exist.” |

Already normative: empty map / zero acceptable routes → **422** and no mint; multiple acceptable routes or TAT overlap → **409**; WO does not create Tests; publish **422** if Test missing; client cannot write routing.

---

## 4. Lab Ops stance on open questions

| ID | Stance |
|----|--------|
| **OQ-WO-1** | **Superseded:** explicit Route; zero acceptable 422, multiple 409, exactly one mints. |
| **OQ-WO-3** | **Superseded:** each process instance links to WO + route position; UI shows one ordered route. |
| **OQ-RES-1** (qualifiers shape) | Sci CSO. Bench bar: the number the tech typed is what review/publish shows. No results column on asked-for. |
| **OQ-SOP-2** (inactive parser draft) | Accept **inactive, unbound**. Never auto-bind to production runs. |

---

## 5. Risks / watch items (non-blocking)

1. **Classic Tests page still mints Tests.** Muscle memory will keep using it as the order path. Do not delete classic type-a-number (WO-4). P1 UAT and manuals: record requests on **Asked-for**, not TestForm. Sidebar item after Receive is the intended CTA. Revisit hiding Test-create as a later ops tweak if dogfood shows the fork.
2. **Uniqueness `(sample_id, analysis_id)`** while open. Two ELISA requests with different cell lines cannot coexist. Fine for P1 empty-params. Breaks when param defs are real — then uniqueness must include the param identity or the tech will cancel/recreate and lose history.
3. **`tat_days > 0`.** Same-day / STAT is often calendar-day 0. Confirm 1 = “due tomorrow” vs “standard 1-day including today.” Display a computed due date; techs do not think in integer ranges.
4. **Asked-for required status = Available for Testing.** Correct vs discarded. Do not block a second analysis on a sample already in a process (Decision #24 eligibility is process membership, not Sample.status).
5. **P3 is persist lock, not a results product.** Do not type numbers into asked-for. Do not pull results-entry into P1 UAT.
6. **Catalog gap for the named NCI path remains:** no whole-blood intake, no DNA daughter, no Qubit analysis in 0058/0059. Do not invent those IDs in this packet ([extract-then-qubit testdata gap](../open-questions/extract-then-qubit-testdata-gap.md)).
7. **P5 may parallel P1** (OQ-IMP-1). Good. Still not a substitute for dest-type or for a work list.

---

## 6. Locked for this packet (do not reopen)

- Receive stays dumb. No analysis picker. Non-empty `analysis_ids` → **422**.
- Asked-for ≠ Test ≠ work_order ≠ Process.
- Test row at **LimsRun start** only (WO-7). Publish refuses if missing.
- Empty routing map mints nothing. Overlapping TAT refuses on save.
- Qubit-on-blood refuses. Dest-type Hold is a **different** packet.
- One execute substrate: Process / Experiment / LimsRun. No third engine.
- SOP Apply: human save of a process definition; never silent auto-activate; no SOP PDF bodies in git; not IC50.
- Parser production import: no LLM.
- No `results.unit_id`. No asked-for columns on `samples`. No projects→orders rename.

---

## 7. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1–L5) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** |
| **P1** | **OPEN** — L1 is already the PRD principle + RQ-AF-2/3 bounce; copy, zero Tests, receive freeze, and multi-sample action land with the P1 PR |
| **P2** | Marc/Rolf supersede singular-definition L4: ordered `process_definition[]`; first process starts first; later processes start later. L2 has zero→422 / multiple→409. |
| **P3** | Persist lock OK for Lab Ops; wait OQ-RES-1 (Sci CSO). Not licensed as “type results on asked-for.” |
| **P4** | Apply → process definition **may** proceed with **L5**. Dest-type Hold **unchanged**. |
| **P5** | **OPEN** (independent; admin UX). |
| **Not licensed by this stamp** | Extract-hold dest type · blood → DNA → Qubit E2E · Qubit/blood testdata IDs · intake-profile engine · lots/registration · IC50 · minting Tests at asked-for or WO save |

```
LAB OPS REVIEW: Accept with conditions (L1–L5)
IMPLEMENT GATE: OPEN (P1 only)
```
