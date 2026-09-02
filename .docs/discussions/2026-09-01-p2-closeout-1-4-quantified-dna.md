# Leadership Confirm: closeout 1.4 — Quantified DNA; OQ-WO-8 Closed (named asked-for LimsRun slot)

**Date:** 2026-09-02
**Stamp:** **Full Leadership Confirm OQ-WO-8 Closed** (Rolf, Deiter, Hans, Heidi, Günter). **CEO Confirm 1–6 stands** (PR **118** / `7612ab4`).
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)
**Closeout:** [`.docs/review/checklist/p2-closeout.md`](../review/checklist/p2-closeout.md) **1.4 / OQ-WO-8**
**Status:** **OQ-WO-8 Closed.** Named asked-for LimsRun slot is no longer pending. Docs-only. No product code. Not a UAT Result. Overall P2 remains unsigned / not Pass. Not IC50.

This fold does **not** rewrite signed UAT on `bf51b19`, `80f054b`, `9342439`, P1, or `02fe95f`. OQ-WO-7 remains Closed and its lookup remains unchanged. CEO Confirm 1–6 (Rolf, PR **118**) stands.

## Full Leadership Confirm — OQ-WO-8 Closed (2026-09-02)

**Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter). Named-slot is **Closed**, not pending.

Map / Route **names the asked-for LimsRun slot**. Eligibility is `asked.analysis_id` vs **that slot**, not “any chain that contains Qubit.” A WGS map with Qubit as process QC must **not** steal a Quantified DNA ask (**409** / wrong join).

Same OQ-WO-7 lookup after C3; **do not recode.** Product code may start **after** this fold is on `main` (not this fold).

## CEO Confirm 1–6 (Rolf) — stands

Already on `main` via PR **118**. Do **not** restamp 1–6.

1. **Quantified DNA is an assay ask.** It is concentration / data, not a tube-only SKU. A Test is data; do **not** mint `extracted = true/false`.
2. **Qubit is the asked-for LimsRun** (exactly one). Test `(DNA, Qubit)` is the ask.
3. **Wear the existing Qubit catalog analysis.** One `analysis_id`. Do **not** mint a second catalog analysis named Quantified DNA (that would split the same concentration into two Tests).
4. **Other QC may sit in the same route.** Nanodrop and other QC use their own `analysis_id`, Test, and params freeze. They are not a second asked-for.
5. **Extract stays an experiment.** No `analysis_id`. No boolean Result. Manual or robot does not make extract a LimsRun for this SKU.
6. **Do not code old 1.4.** Extract-only / zero-LimsRun routing is not this closeout. Map-save / Route **422** on 0 LimsRuns is right for Quantified DNA. WGS / WES / ELISA unchanged: Qubit stays process QC when one of those is the ask. Tube-only DNA is a later SKU.

## Punch (CEO; same 1–6 fold; stands)

Wear existing **Qubit**. Do **not** mint a second catalog analysis named Quantified DNA.

## Named asked-for LimsRun slot — Closed

**Closed** by Full Leadership Confirm (Rolf / Deiter / Hans / Heidi / Günter). Older “punch pending Leadership Confirm / not OQ-WO-8 Closed” copy is **superseded**.

Heidi / Günter punch, now Confirmed: Qubit-as-ask vs Qubit-as-QC — Route containment of Qubit would also match WGS maps that include Qubit as process QC (two-accept 409 / wrong process join). Map / Route must **name the asked-for LimsRun slot**, not “any chain that contains Qubit.” Eligibility is `asked.analysis_id` vs that named slot.

## OQ-WO-8 Closed

CEO Confirm 1–6 did **not** close OQ-WO-8. Full Leadership Confirm **does**. Old 1.4 (zero LimsRuns legal for Extracted DNA) stays **struck** for this SKU. Named-slot is no longer pending.

## OQ-WO-7 remains unchanged

After C3, Qubit start on DNA still freezes from the WO asked-for — same lookup as OQ-WO-7 (WO asked-for only if `asked.analysis_id == run.analysis_id`, else parent lineage, else `{}`). Do **not** recode.

## Gate

No product code in this fold. Product code may start **after** this fold is on `main`. Not IC50.
