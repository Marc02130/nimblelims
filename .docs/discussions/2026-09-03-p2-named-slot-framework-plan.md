# Implementation plan: named asked-for LimsRun slot (framework-first)

**Date:** 2026-09-03  
**Status:** Plan — configurable joints, not assay-name code. **Not** overall P2 Pass. Not IC50.  
**Authority:** Full Leadership Confirm #2 + named-slot brief.  
**Related:** [P2 closeout 1.4 send](2026-09-01-p2-closeout-1-4-quantified-dna.md) · [framework review](2026-09-02-framework-review-accessioning-asked-for-routing-processing.md) · [FW-0](../decision-logs/framework-stamps-2026-08-26.md)

Does **not** recode OQ-WO-7, dest-follow, freeze skip, extract-as-LimsRun, or mint a second catalog analysis for any SKU.

---

## 1. Principle

**No `if analysis == WGS` / `if analysis == Qubit`.** Those names are **catalog rows** and **UAT fixtures**. Product code matches **UUIDs the admin already stored**.

| Joint | Where it lives | Who sets it |
|-------|----------------|-------------|
| What can be asked | `analyses` + param defs | `config:edit` |
| What was asked | `asked_for.analysis_id` + `params` + `tat_days` | Tech (`test:assign`) |
| How the lab does it | `routing_map`: TAT + ordered process defs + **named slot** | `config:edit` |
| What the tube is | `samples.sample_type` + first-step allow-list | Receive + process-step types |
| Which vessel is worked | `eln_process_samples.container_id` | First Start, not Route |

WGS with ten ADME/DMPK packs = **ten map rows** that all **name** the same analysis on different chains (and/or different TAT / inbound types). One analysis, many routes. Params (kit, species, matrix) stay on the asked-for and freeze at LimsRun start — they do **not** pick the map unless a later packet adds param-based routing (out of this slice).

---

## 2. What is hard-coded today (the smell)

`routing_map` already has `analysis_id` and `sample_type_id`, but create **ignores** them. Types are derived from the first typed step. Analyses are **whatever LimsRun steps appear in the chain**. Route accepts a row when `_asked_for_lims_run_count(chain, asked.analysis_id) == 1` (containment). Map-save **409**s when TAT ∩ first-step types ∩ **analysis SET intersection** all hold.

That last rule is what collapses “one analysis, many packs” into **one saveable map** whenever two WGS chains share inbound type and TAT. Containment is what lets a WGS+Qubit-QC pack steal Quantified DNA. Neither is a catalog joint; both are matching **if-statements over derived lists**.

UAT will still say “Qubit / WGS” because those are the **examples**. The implementation must not.

---

## 3. Configurable joint to add

**Named asked-for LimsRun slot** on the map, authored, persisted.

**Prefer:** `routing_map.asked_for_step_id` → `eln_process_definition_steps.id`  
Must be a LimsRun step **in this map’s chain**, with a non-null `analysis_id`.

**Denorm (optional, for index/read):** keep `routing_map.analysis_id` as a **copy of that step’s analysis_id**, written on save from the chosen step. Stop treating it as ignored. **Never** set it from `analyses[0]` / first LimsRun in the chain.

**Admin UI (`/admin/routing-map`):** after the ordered process list, a required control: **Asked-for LimsRun** = dropdown of LimsRun steps in the chain (label: process name + step + analysis name from catalog). No free-text “Quantified DNA.” No hidden default to the first LimsRun.

`config:edit` only. Same AuthZ as today.

---

## 4. Matching algorithm (generic)

On **Route** of asked-for `A` for sample type `T` and TAT `D`:

1. TAT: `D` inside `tat_range`.  
2. Type: `T` is on the **first process’s first** Experiment/LimsRun allow-list (live list, not denorm).  
3. Slot: `A.analysis_id == slot_step.analysis_id` (the persisted named slot). **Not** “`A.analysis_id` appears anywhere in the chain.”

Then:

| Count | Result |
|-------|--------|
| 0 | **422** — no work order, stays `requested` |
| 1 | Mint that map’s chain onto one `work_order` |
| 2+ | Return **candidates** (map id, TAT, chain names, slot analysis name). Mint **nothing** until `POST .../route` with `routing_map_id`. No `first()`. |

Picker UI is a **list of map rows** (already-authored config). Not an analysis picker. Not a sample-type picker.

Batch Route (`asked_for_ids`) stays N independent Routes. If any id needs a pick, that id does not mint until `routing_map_id` is posted; do not silent-pick.

---

## 5. Map-save rules (generic)

Still **422** (this map is nonsense):

- Chain empty / no LimsRun.  
- Named slot missing, not in chain, or not a LimsRun with `analysis_id`.  
- The **slot’s** `analysis_id` appears **0 or 2+** times among LimsRuns in **this** chain (cardinality **per map**, not per catalog).

Still **409** only for a **duplicate pack**:

- Overlapping TAT, overlapping first-step types, **and the same ordered `process_definition_ids`**.

**Stop** 409 on “analysis SET intersection.” Two different chains that both name the same analysis (STAT WGS vs standard WGS; two Qubit-ask packs) **must save**. Extract-first vs Qubit-first for the same TAT stays legal because first-step types and/or slots differ.

Handoff 422 (process *x* emerging type vs *x+1*) unchanged.

---

## 6. What we do **not** implement as code

- Special cases for WGS, WES, ELISA, Qubit, Nanodrop, Quantified DNA.  
- A second analysis row named Quantified DNA (admin wears existing Qubit as the slot).  
- Param-based map matching (kit/species as routing keys) — later packet if ever.  
- Route binding `container_id` (tube pick remains First Start).  
- Auto-route on asked-for save.  
- Recoding OQ-WO-7 lookup.  
- Dest-follow, freeze skip, extract-as-LimsRun.

---

## 7. Backfill (fail closed)

Existing maps have ignored `analysis_id` / no slot.

| Chain | Migration |
|-------|-----------|
| Exactly **one** LimsRun step in the chain | Set `asked_for_step_id` to that step (unambiguous). |
| **Zero** LimsRuns | Leave null; map-save/Route already 422. |
| **Two or more** LimsRuns | Leave null. Route **422** until an admin opens the map and **names** the slot. Do not guess `first()`. |

No product `if` on analysis names during backfill.

---

## 8. Files (Heidi map, still generic)

| Area | Files |
|------|--------|
| Schema | Alembic: `asked_for_step_id` (FK, nullable for backfill). Model `RoutingMap`. |
| Match / save | `backend/app/services/routing_service.py` — eligibility, overlap, Route 2+ candidates; `work_order` schemas + router (`routing_map_id` on Route). |
| Admin | `RoutingMapManagement.tsx` — slot dropdown; copy: “name the asked-for LimsRun,” not “analysis somewhere in the chain.” |
| Tech | `AskedFor.tsx` + `apiService` — if Route returns candidates, show picker then POST `routing_map_id`. |
| Tests | `test_work_order_p2.py`: two maps, **same** analysis UUID, different chains, overlapping TAT/types → **save both**; Route with one slot match → mint A not B; 0 → 422; 2+ → no mint until `routing_map_id`; two LimsRuns of the **slot** analysis on one map → 422. **Do not** key tests on the strings `"WGS"` / `"Qubit"` except as fixture **names**. |
| UAT | `AC-P2-OQ-WO-8` already written — fixtures may use Qubit/WGS as **examples**. |

---

## 9. Slice order

1. Alembic + model + backfill (fail closed).  
2. Map-save: require slot; cardinality on **slot analysis** only; overlap 409 = duplicate **chain**, not analysis-set.  
3. Route eligibility = slot; 0/1 behavior.  
4. Route 2+ candidates + POST `routing_map_id` + picker UI.  
5. Pytest.  
6. Tobias `AC-P2-OQ-WO-8` on that SHA. Per-AC only. Then overall P2 is still Leadership + Tobias overall — not this slice alone.

---

## 10. How the examples sit on this (not in code)

Admin authors:

- Map: TAT 5–10, blood first step, chain extract → Qubit LimsRun, **slot = Qubit step**.  
- Map: TAT 5–10, blood first step, chain extract → Qubit QC → WGS LimsRun, **slot = WGS step**.  

Same generic matcher. Quantified DNA asked-for (`analysis_id` = Qubit UUID) hits the first. WGS asked-for hits the second. A third WGS pack (different extract process, same TAT, same blood) **also saves**; Route shows a picker. No Python branch knows those names.
