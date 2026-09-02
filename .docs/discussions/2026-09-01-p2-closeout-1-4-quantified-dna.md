# Leadership Confirm: closeout 1.4 — Quantified DNA is the Qubit ask

**Date:** 2026-09-02
**Team:** Leadership — Rolf, Deiter, Hans, Heidi, Günter
**Stem:** [post-receive-work-spine](../review/requirements/post-receive-work-spine.md)  
**Closeout:** [`.docs/review/checklist/p2-closeout.md`](../review/checklist/p2-closeout.md) **1.4 / OQ-WO-8**
**Status:** **Leadership Confirm 1–6.** Living lock. Docs-only fold; no product code. Not a UAT Result. Overall P2 remains unsigned / not Pass. Not IC50.

This Confirm does **not** rewrite signed UAT on `bf51b19`, `80f054b`, `9342439`, P1, or `02fe95f`. OQ-WO-7 remains Closed and its lookup remains unchanged.

## Confirmed 1–6

1. **Quantified DNA is an assay ask.** It is concentration/data, not a tube-only SKU. A Test is data; do **not** mint `extracted = true/false`.
2. **Qubit is exactly one asked-for LimsRun.** Test `(DNA, Qubit)` is the ask.
3. **Wear the existing Qubit catalog analysis.** There is one `analysis_id`. Do **not** create a second catalog analysis named Quantified DNA; that would split one concentration into two Tests.
4. **Other QC may sit in the route.** Nanodrop and other QC use their own `analysis_id`, Test, and params freeze. They are not a second asked-for.
5. **Extract stays an experiment.** Manual or robot extraction has no `analysis_id` and no boolean Result. It does not become a LimsRun for this SKU.
6. **Do not code old 1.4.** Extract-only / zero-LimsRun routing is not this closeout. Map-save / Route **422** on zero LimsRuns is right for Quantified DNA. WGS / WES / ELISA are unchanged: Qubit remains process QC when one of those is the ask.

**Quantified DNA route:** extract experiment → Qubit LimsRun in the named asked-for slot → optional other QC LimsRuns.

## Heidi / Günter route-identity punch

Containment is insufficient. A WGS route may contain Qubit as process QC; matching “any route containing Qubit” would make both the Quantified DNA route and the WGS route acceptable, causing a two-accept **409** or the wrong process join.

The Map / Route contract must therefore **name the asked-for LimsRun slot**. Eligibility compares `asked.analysis_id` with the `analysis_id` of that named slot. It must not infer the asked-for slot from any matching analysis elsewhere in the chain. Supporting LimsRuns remain visible and retain their own Tests, but they are not eligible merely because they contain Qubit.

## Superseded closeout wording

The old closeout 1.4 claim — ~~Extracted DNA is a tube-only ask; zero assay LimsRuns are legal; 422 on zero LimsRuns is wrong~~ — is struck for this closeout. A later tube-only DNA SKU requires its own decision and is not Quantified DNA.

## OQ-WO-7 remains unchanged

After C3, Qubit start on DNA uses the existing frozen-params lookup: WO asked-for only when `asked.analysis_id == run.analysis_id`; otherwise parent lineage; otherwise `{}`. Do **not** recode or restamp it.

## Gate

This PR folds the Confirm before product coding. Future implementation must reuse Qubit, persist/name the asked-for LimsRun slot, retain **422** for zero LimsRuns, and avoid containment-only matching. No product code is part of this fold.
