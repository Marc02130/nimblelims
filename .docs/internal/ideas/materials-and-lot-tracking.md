# Idea: Materials and lot tracking

**Status:** Placeholder — **not** in experiment-entries v1  
**Date:** 2026-08-10  
**Related:** Containers/contents (samples, cells, compounds); aliquot/pool; [accessioning-and-workflows-revisit.md](accessioning-and-workflows-revisit.md); ELN predefined entries

## One-liner

Add first-class **materials** (reagents, kits, enzymes, media, etc.) with **lot/batch** identity, quantity on hand, and use against experiments/runs — separate from sample accessioning and from container *vessel* material (plastic type).

## Current state (NimbleLIMS)

| Exists | Does not exist as inventory |
|--------|-----------------------------|
| `containers` / `contents` (samples in vessels; solute mass only — diluent is **not** mass; see [open-questions/containers.md](../open-questions/containers.md)) | Reagent/material catalog |
| `container_types.material` (vessel composition string) | Lot numbers, expiry, remaining qty for consumables |
| Commented sketch `lot_number` on Sample | Material consume/deduct on step execute |

## Why

Labs need lot traceability for QC, CAPA, and regulated work. Aliquot/pool and prep SOPs often consume kit lots; that is **not** Sample write-back and not “container amount of sample.”

## Direction (later cycle)

1. Material definition (type, units, storage).  
2. Lot/batch records (lot id, expiry, received qty, remaining).  
3. Optional link from experiment entry or process step: “lot used.”  
4. Consume on execute (optional) vs document-only use.  
5. Reports: which lots touched which samples/experiments.

## Non-goals for experiment-entries foundation

- Building material UI in the same phase as experiment_sample_data / experiment_data / aliquot plan.  
- commercial-LIMS-style full materials module day one.

## Open when prioritized

- Material vs compound-as-sample (drug discovery) boundary  
- Integration with dose-response well contents (compound sample vs reagent lot)  
