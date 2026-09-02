# CEO Confirm: closeout 1.4 — Quantified DNA is the Qubit ask

**Date:** 2026-09-02
**Stamp:** **CEO Confirm 1–6 (Rolf)** plus Qubit-reuse punch
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)
**Closeout:** [`.docs/review/checklist/p2-closeout.md`](../review/checklist/p2-closeout.md) **1.4 / OQ-WO-8**
**Status:** **CEO Confirm 1–6 (Rolf).** Docs-only. No product code. Not a UAT Result. **OQ-WO-8 stays OPEN** until Deiter / Hans / Heidi / Günter stamp. Overall P2 remains unsigned / not Pass. Not IC50.

This fold punches PR **117** / `3e1856b` back from a room-wide closeout. It does **not** rewrite signed UAT on `bf51b19`, `80f054b`, `9342439`, P1, or `02fe95f`. OQ-WO-7 remains Closed and its lookup remains unchanged.

## CEO Confirm 1–6 (Rolf)

1. **Quantified DNA is an assay ask.** It is concentration / data, not a tube-only SKU. A Test is data; do **not** mint `extracted = true/false`.
2. **Qubit is the asked-for LimsRun** (exactly one). Test `(DNA, Qubit)` is the ask.
3. **Wear the existing Qubit catalog analysis.** One `analysis_id`. Do **not** mint a second catalog analysis named Quantified DNA (that would split the same concentration into two Tests).
4. **Other QC may sit in the same route.** Nanodrop and other QC use their own `analysis_id`, Test, and params freeze. They are not a second asked-for.
5. **Extract stays an experiment.** No `analysis_id`. No boolean Result. Manual or robot does not make extract a LimsRun for this SKU.
6. **Do not code old 1.4.** Extract-only / zero-LimsRun routing is not this closeout. Map-save / Route **422** on 0 LimsRuns is right for Quantified DNA. WGS / WES / ELISA unchanged: Qubit stays process QC when one of those is the ask. Tube-only DNA is a later SKU.

## Punch (CEO; same fold)

Wear existing **Qubit**. Do **not** mint a second catalog analysis named Quantified DNA.

## Named asked-for LimsRun slot — punch pending Leadership Confirm

**Not** part of CEO Confirm 1–6. **Not** OQ-WO-8 Closed.

Heidi / Günter punch: Qubit-as-ask vs Qubit-as-QC — Route containment of Qubit would also match WGS maps that include Qubit as process QC (two-accept 409 / wrong process join). Map / Route must **name the asked-for LimsRun slot**, not “any chain that contains Qubit.”

This punch waits Deiter / Hans / Heidi / Günter. Do not code it as closed.

## OQ-WO-8 stays OPEN

CEO Confirm 1–6 does **not** close OQ-WO-8. Leave **OPEN** until Deiter / Hans / Heidi / Günter stamp. Old 1.4 (zero LimsRuns legal for Extracted DNA) is **struck** for this SKU, but the OQ remains OPEN.

## OQ-WO-7 remains unchanged

After C3, Qubit start on DNA still freezes from the WO asked-for — same lookup as OQ-WO-7 (WO asked-for only if `asked.analysis_id == run.analysis_id`, else parent lineage, else `{}`). Do **not** recode.

## Gate

No product code until Deiter / Hans / Heidi / Günter stamp OQ-WO-8. Named-slot is a pending punch, not this CEO Confirm. Not IC50.
