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

## Full Leadership Confirm #2 — 2026-09-03

**Full Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter). Not CEO-only. Not a UAT Result. Not overall P2 Pass.

1. Keep **no route branching**. WGS asked-for on blood owns WGS params; C3 DNA still serves WGS; a C2 aliquot continues WGS; WES is a new asked-for on the DNA tube. Tobias Seq-1 Pass of two WOs is not this Confirm.
2. Keep **asked-for only** from PR 111.
3. Strike all remaining live or pending-overwrite copy that says “Extracted DNA = DNA tube; zero assay LimsRuns legal.” Quantified DNA wears existing Qubit.

OQ-WO-8 remains Closed as historical decision state from PR 119. This send does not reopen or restamp it. OQ-WO-7 remains Closed and unchanged.

## Named-slot product brief — in-bar for Tobias

**Hole today:** `_acceptable_maps` in `backend/app/services/routing_service.py` uses `_asked_for_lims_run_count(chain, analysis_id) == 1`. That checks containment anywhere in the chain. A WGS map with Qubit only as process QC can therefore steal a Quantified DNA ask.

**Product lock:**

- Persist the map author’s named asked-for LimsRun slot, preferably as a `routing_map` FK to the selected assay `eln_process_definition_steps` LimsRun. An author-named `routing_map.analysis_id` is an acceptable fallback; deriving `analyses[0]` is not.
- Eligibility is `asked.analysis_id` against that slot’s `analysis_id`, not chain containment.
- Map-save remains **422** when the named slot analysis appears 0 or 2+ times among route LimsRuns.
- Wear existing Qubit. Do not mint a second catalog analysis named Quantified DNA.
- A WGS map with Qubit only as process QC must not accept a Quantified DNA ask.
- After filtering: **0** acceptable maps → **422**; **1** → Route mints; **2+** → return candidates and require the tech to pick one. Mint only after the chosen `routing_map_id` is posted. No silent `first()`.
- Keep the OQ-WO-7 lookup after C3 unchanged.

**Heidi file map:** `routing_service.py` create/update/eligibility and chosen assignment; `backend/models/work_order.py` plus Alembic if a new column is used; routing schemas and `work_orders` router; `RoutingMapManagement.tsx`; `AskedFor.tsx` and API service; `test_work_order_p2.py` and a UI test. Do not touch destination follow, freeze skip, unrelated cardinality, or extract-as-LimsRun.

## Closeout honesty

This docs fold supplies the Brief and unsigned UAT AC only. Overall P2 remains blocked in this order:

1. Named-slot and 2+ picker product.
2. Tobias executes the named-slot AC on that product SHA.
3. Tobias records overall Pass on the named-slot SHA, or one overall Result folding `bf51b19` + `80f054b` + that SHA.
4. Leadership records overall Pass.

A per-AC Pass is not overall P2 Pass.

## Product and Tobias QA stamps — 2026-09-03

**Product:** `feat/p2-named-slot` @ **`6244bf6`** (`6244bf6e742c4ed0f046ff8770e2b8c112446fb3`), Alembic **`0079`**.

**AC-P2-OQ-WO-8 Result:** **Pass** (Tobias, 2026-09-03, `6244bf6`).

- The persisted named slot is `routing_map.asked_for_step_id`.
- Eligibility compares `asked.analysis_id` with that slot, not chain containment.
- One named Qubit match mints; zero acceptable maps returns **422**.
- Two or more acceptable maps return **409** `route_pick_required`; the picker mints only after the selected `routing_map_id` is posted.
- WGS+Qubit-as-process-QC does not steal a Quantified DNA ask.

Deiter Lab Ops supplied this Pass/Fail boundary. Heidi Architecture **Accept** and Günter CSO **Accept** `6244bf6` as supporting context for Tobias’s click. Hans did not stamp a Science Accept in this burst; none is claimed.

**Tobias overall P2 Result (QA): Pass** on `6244bf6`, folding per-AC Pass on `bf51b19`, OQ-WO-7 Pass on `80f054b`, and OQ-WO-8 Pass on `6244bf6`.

This does not rewrite those earlier signed Results, OQ-WO-8 Closed history from PR 119, or Confirm #2 / Brief from PR 120. OQ-WO-7 remains Closed and was not recoded.

**Leadership overall Pass remains unsigned / not Pass.** Do not derive a Leadership stamp from Tobias’s QA Result. Not IC50.
