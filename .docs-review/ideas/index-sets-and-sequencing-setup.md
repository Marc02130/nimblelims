# Idea: Index sets, index assignment, and sequencer sample sheets

**Status:** Placeholder — **not** full product in experiment-entries v1  
**Date:** 2026-08-10  
**Related:** ELN entries; LIMS runs; NGS library prep processes; [experiment-template-entries](../tech-sketch/experiment-template-entries.md)

## One-liner

1. **Index sets** — first-class catalog of barcode/index sequences (and dual-index pairs) for NGS.  
2. **Index assignment** — strong candidate for a **predefined experiment entry** (behavior: assign unique indexes to samples in the cohort).  
3. **Sample sheets** — sequencer-specific export/upload formats for **flow cell loading**; good future entry; **v1 can use generic `experiment_data`** for plan/capture until dedicated formatters exist.

## Why

All sequencers need sample sheets; formats differ by vendor/platform. Index collisions and set management are lab SoT, not free-text fields alone.

## v1 vs later

| Capability | v1 (entries foundation) | Later |
|------------|-------------------------|--------|
| Capture prep notes / loading plan | **`experiment_data`** (generic columns) | Dedicated flow-cell loading entry |
| Index set catalog + uniqueness rules | — | **Build** |
| Index assignment entry | — | Predefined entry on `experiment_sample_data` |
| Sequencer-specific sample sheet export | — | Format plugins (Illumina, etc.) |

## Direction (later cycle)

1. Index set CRUD (name, chemistry, indexes/pairs, retired flags).  
2. Assignment rules (unique within run/pool, reserved indexes).  
3. Entry: assign indexes to samples in experiment.  
4. Sample sheet generators per sequencer family.  
5. Optional validate-before-LIMS-run / before submit.

## Non-goals now

- Implementing Illumina bcl sample sheet in the foundation sketch.  
- Replacing LIMS Run for instrument primary data.

## Open when prioritized

- Where indexes live on Sample vs only on experiment values  
- Multi-pool / multi-lane flow cell model  
