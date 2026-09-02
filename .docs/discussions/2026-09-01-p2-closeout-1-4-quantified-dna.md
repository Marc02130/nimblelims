# Leadership send: closeout 1.4 — Quantified DNA is the asked-for

**Date:** 2026-09-01  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO) — Rolf, Deiter, Hans, Heidi, Günter  
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)  
**Closeout:** [`.docs/review/checklist/p2-closeout.md`](../review/checklist/p2-closeout.md) **1.4**  
**Living send:** [2026-08-30-p2-route-lock](2026-08-30-p2-route-lock.md)  
**Status:** **Marc lock, pending Leadership Confirm.** Not coded. Not a UAT Result. Not overall P2 Pass. Not IC50.

Does **not** rewrite Round 1, Round 2, Contents-grain Confirm, Deiter `02fe95f`, Tobias `9342439` / `8cfa2a9` / `bf51b19` / **AC-P2-OQ-WO-7 Pass** on `80f054b`, dest-type split, mint-only-at-execute, ELISA / second-tube Confirm, OQ-WO-6 extract close, or OQ-WO-7 Closed.

---

## Why this send

Closeout **1.4** was written as: asked-for **Extracted DNA** = DNA tube only; **zero** assay LimsRuns legal; map-save/Route **422** on zero LimsRuns is wrong for that ask.

That treated extracted DNA as a **product** (a tube). Labs produce **data**. If the client asked for quantified DNA, the ask is a concentration (or equivalent), not “a tube exists.”

Do **not** invent a boolean Result (`extracted = True/False`) on extract to fake a Test. Dest mint is the tube. A Test is data.

---

## Proposed lock (please Confirm)

1. **Quantified DNA is the asked-for.** Catalog analysis for that SKU. It is an **assay ask**, not a tube-only SKU. Cardinality 1 applies: asked-for analysis appears **once** among LimsRuns.
2. **Qubit is the asked-for LimsRun.** That LimsRun wears the Quantified DNA / Qubit `analysis_id` **once**. WO-7 Test `(DNA, Qubit)` at that LimsRun start. That Test **is** the ask.
3. **Other process QC may sit** (Nanodrop, TapeStation, …). Other `analysis_id`s, own Tests, own params freeze. **Not** a second asked-for. Do not invent a second asked-for for Nanodrop.
4. **Extract stays an experiment** (equipment; aliquot/pool execute; dest DNA). **No** asked-for `analysis_id` on extract. Hans’s punch stands: do not hang the panel analysis on extract. Extract-as-instrument LimsRun is **later**, if equipment is an instrument — then it emits instrument values, not a boolean.
5. **Do not code extract-only zero-LimsRun routes** for this SKU. Do not mint a Test for extract. Do not store `extracted = true` as a Result.
6. **WGS / WES / ELISA unchanged.** When those are the ask, Qubit / Nanodrop remain **process QC**, not the asked-for. Process QC is not an asked-for on those SKUs.

**Route shape for Quantified DNA:** extract (experiment, dest DNA) → Qubit LimsRun (the ask) → optional other QC LimsRuns.

---

## Asks

1. **Quantified DNA = assay ask.** Confirm: the SKU is quantified DNA (data), not “tube of DNA with zero LimsRuns.”  
2. **Qubit is the asked-for LimsRun.** Confirm: that LimsRun wears the asked-for `analysis_id` once; Test `(DNA, Qubit)` is the ask.  
3. **Other QC supporting.** Confirm: Nanodrop / etc. may sit; other analyses; own Tests; not a second asked-for.  
4. **Extract has no analysis_id.** Confirm: still experiment / equipment. No boolean Result on extract.  
5. **Do not code old 1.4.** Confirm: do **not** allow map-save/Route of extract-only (zero LimsRuns) for this SKU. Two ELISA LimsRuns still 422.  
6. **WGS QC unchanged.** Confirm: on a WGS/WES/ELISA ask, Qubit stays process QC, not the ask.

---

## What this overwrites (pending Confirm)

| Was (closeout 1.4 as written) | Proposed now |
|-------------------------------|--------------|
| Extracted DNA ask = DNA tube; **zero** assay LimsRuns legal | **Quantified DNA** ask = **Qubit** is the asked-for LimsRun (exactly one) |
| Map-save/Route 422 on 0 LimsRuns is **wrong** for that ask | 422 on 0 LimsRuns is **right** for this SKU — it is an assay ask |
| Qubit/Nanodrop **may sit** (not the ask) | Qubit **is** the ask; Nanodrop / other QC **may sit** as supporting |
| Code iff in-bar: allow extract-only route | **Do not code** extract-only / zero-LimsRun / boolean Test |

Leadership Confirm 2026-09-01 “Extracted DNA asked-for can have Qubit/Nanodrop” stays in spirit: Qubit is now **the** LimsRun for this SKU, not an optional extra on a tube-only ask.

---

## Out of this send

- Dest-follow (C2/C3) — already Tobias Pass `bf51b19`  
- OQ-WO-7 — **Closed.** AC-P2-OQ-WO-7 Pass on `80f054b`  
- Freeze skip NULL — Pass `bf51b19`  
- Cardinality 1 for ELISA / WGS — Pass `bf51b19`  
- Boolean `extracted = True/False` Result — **rejected**  
- P3 persist lock / IC50  
- Overall P2 Pass — stays **unsigned** until Leadership stamps it  

---

## Persona-applied (provisional — overwrite if you disagree)

Not a Confirm. For Leadership to Confirm.

| Ask | Lab Ops | CEO | Security CSO | Sci CSO |
|-----|---------|-----|----------------|---------|
| 1. Quantified DNA = assay ask | **Yes.** Tube-only is inventory; the order is a number | **Yes.** Labs sell data | Neutral | **Yes.** Result ledger needs an assay instance |
| 2. Qubit is the asked-for LimsRun | **Yes.** Instrument step is the work | **Yes.** One asked-for LimsRun | Neutral | **Yes.** Test `(DNA, Qubit)` is the ask |
| 3. Other QC supporting | **Yes.** Nanodrop is not a second order | **Yes.** Same as WGS supporting QC | Neutral | **Yes.** Other analysis, own Test |
| 4. Extract has no analysis_id | **Hard lock.** Equipment, dest mint | **Yes.** Do not fake a Test | Neutral | **Hard lock.** Boolean is not an analyte |
| 5. Do not code old 1.4 | **Yes.** Zero LimsRuns is the wrong SKU | **Yes.** Do not ship tube-only as this closeout | Neutral | **Yes.** Cardinality 1 for this assay |
| 6. WGS QC unchanged | **Yes.** Qubit on WGS is still process QC | **Yes.** Care about the asked-for only | Neutral | **Yes.** Do not steal WGS params (OQ-WO-7) |

---

## Coding if Confirmed (not this fold)

No code in this send.

If Confirm lands: catalog analysis **Quantified DNA** (or Qubit as that analysis) on **exactly one** LimsRun in the route; extract process first; other QC optional. Map-save/Route **422** if that analysis appears 0 or 2+ times — same as ELISA. Do **not** special-case zero LimsRuns. Do **not** recode dest-follow, OQ-WO-7, freeze skip, or cardinality.

---

Please Confirm 1–6, or overwrite.
