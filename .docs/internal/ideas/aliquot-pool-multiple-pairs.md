# Idea: More than one aliquot/pool pair on an experiment

**Status:** Parked — **not** this cycle  
**Date:** 2026-09-14  
**Now:** `WRAPPER_CATALOG` (`backend/models/wrappers.py`; FE `frontend/src/components/experiments/wrappers.ts`). Aliquot/pool is wrapper id `aliquot_pool`, **cardinality 1**, atomic pair. API **409** `wrapper_at_capacity` if a second instance is created. UI Add disables while the wrapper is present. n-instances / `source_from` predecessor stay here.  
**Related:** E-10 [ISSUES-experiments.md](../prd/sample-processing/ISSUES-experiments.md); [extract-hold-dest-type](../../review/tech-sketch/extract-hold-dest-type.md); [configurable-entries-framework](../../review/tech-sketch/configurable-entries-framework.md) §4.1 / §10; requirements path §7 (second add after first execute)

## One-liner

Allow **1 or more** sequential mint pairs on one experiment (e.g. extract then aliquot) without half-pairs, without a third kind, and without `if aliquot`. Until that lands, cardinality is **1**.

## Why (parked)

Requirements §7 already describes aliquot → execute → **separate add for pool**. Bench extract-then-aliquot is the same shape. One pair cannot do both: **one mint op per plan instance** (aliquot XOR pool) is locked.

The singleton today is **not** a lab SOP. It is two fixed `predefined_entry_key` values (`aliquot_pool_plan` / `aliquots_pools`) treated as “the pair exists.” Add disables while either key is present. Execute writes minted ids onto **every** dest with that key.

## Direction when prioritized (framework-first)

Do **not** suffix keys (`aliquot_pool_plan_2`) or special-case aliquot. Same joint as named-slot: wrapper **type** vs **instance**.

| Piece | Rule |
|-------|------|
| `predefined_entry_key` | Wrapper **type** (like `analysis_id`) |
| Cardinality | Catalog property of the wrapper (`1` vs `n`), not an aliquot `if`. Header stays 1; aliquot/pool would become `n` |
| Instance | `pair_id` on both halves (`config` is enough). Mate = same experiment + mate key + **same `pair_id`** |
| Atomic pair | One Add still creates **both** halves. No plan-only / dest-only |
| Open pair | At most **one unfinished** pair at a time: Add off while a pair is open; on after **execute-complete** or delete both |
| Other entries | Header / notes / samples stay free. This is not a global sequential experiment engine |
| Order of **other** work | Existing template `depends_on` (submit gate). Point at **instance** (`pair_id` / entry id), not type key. Extend to **execute** if both pairs are template-authored (mint is execute, not submit) |
| Source set | Required once n > 1. Plan config `source_from`: **`start_cohort`** or **predecessor dest** (`pair_id` / dest entry). Resolve at plan/execute. Execute: source must be **in that set**, not merely on the experiment |

### Source-from (the missing joint)

Today the picker is start cohort. Minted dests also join `ExperimentSampleExecution`, so originals **and** daughters are both legal sources. After extract, a second plan can still pick parent blood unless scoped.

| Intent | `source_from` |
|--------|----------------|
| Extract Blood → DNA, then aliquot **that DNA** | predecessor dest |
| Two independent splits of the **same** start samples | `start_cohort` both times |
| Pool several extract dests | predecessor dest |

Do not infer “second pair = dests” (`if n>=2`). Do not key off method. Method ≠ dest type ≠ source-from. Dest-follow (process assignment) is a different layer: process holds dest; experiment cohort still holds parent + dest.

Template time has no sample ids: author `start_cohort` or “dests of **this** template’s other pair.” Instance resolve after predecessor execute-complete.

### Code that must stop matching by type key alone

`hasAliquotPair` / Add disable; `ensure_aliquot_pair_in_entries`; DELETE mate = first sibling with the other key; execute stamps **all** `aliquots_pools`; POST half-pair fills “the” missing key; `depends_on` dict keyed by `predefined_entry_key`.

## Now (enforced)

- Catalog: `WRAPPER_CATALOG["aliquot_pool"]` — keys, `cardinality: 1`, `atomic_pair`, `mint`, `source_from: start_cohort`. Header and Samples are rows with cardinality 1 (no mint).
- UI: **+ Aliquot/pool** / Add disabled while the wrapper is at capacity; re-enables after delete. Not a lifetime lock.
- API: **409** `wrapper_at_capacity` (`wrapper_id: aliquot_pool`) if a second plan or dest role is POSTed, or a template declares two of either key. First add still completes the mate (E-10).

## Non-goals now

- Implementing n pairs, `pair_id`, or `source_from`.
- Dual mint (aliquot and pool on one plan entry).
- A third entry kind or a new plan object.
- Unique DB index on `(experiment_id, predefined_entry_key)` until cardinality is a catalog row (would cement 1).
- Reopening dest-follow, named-slot, OQ-WO-7.

## Open when prioritized

1. Independent n (two start-cohort splits) and chained n (predecessor dest) both in, or only chained?
2. Template-authored N pairs vs ad hoc Add after first execute-complete (or both)?
3. Instance label so two “Aliquot / pool plan” rows are distinguishable.
4. `depends_on` → execute + instance id, vs only open-pair Add (second pair added after first execute).
