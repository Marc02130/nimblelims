# UI / UX Review: Experiment template entries

**Date:** 2026-08-10  
**Status:** **Accept with conditions**  
**Tech sketch:** [§0](../tech-sketch/experiment-template-entries.md)  
**Lab Ops:** L1–L9 · **CEO:** Accept w/ conditions  

## Executive summary

UI must make three things obvious: **(1) start cohort from queue**, **(2) entries as steps with save vs submit**, **(3) aliquot plan method → columns → execute**. Template builder is in scope; do not ship capture grids without start UX.

**Verdict: Accept with conditions.**

## Flows to ship

### A. Start experiment / LIMS run

```
Queue (filters: status, process, …)
  → multi-select and/or scan barcode
      plate → select all samples on plate
      tube  → select tube content sample(s)
  → Start
  → Header + Samples entries show cohort
```

### B. Work entries

```
Ordered entries
  → free edit + Save (entry only)
  → optional Submit (write-back if mapped; unlocks next if dependency)
  → RO sample fields always visible on sample grids
```

### C. Aliquot/pool

```
Plan entry (experiment_data)
  → choose method (all methods available)
  → columns for that method
  → Execute
  → Results entry (experiment_sample_data) + container updates
```

### D. Template authoring

```
Tables & forms / Entries
  → add base or predefined
  → columns: sample_field (RO) + FieldDefinitions
  → write-back: boolean + type-matched sample target (template only)
  → dependencies: require prior submit
  → aliquot: method set
```

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Queue + scan + start before “entries done” messaging |
| **U2** | Clear **Save** vs **Submit** labels; submit explains Sample update when mapped |
| **U3** | RO sample identity columns visually distinct (not editable) |
| **U4** | Aliquot method switcher shows **all** methods; columns update with method |
| **U5** | Dependency-locked next entry: clear “complete prior step” state |
| **U6** | Ad hoc add field: no write-back control (hidden/disabled) |
| **U7** | Empty states: no samples → prompt start from queue |

## Litmus (0–10)

| Dimension | Score |
|-----------|-------|
| Hierarchy | 8 |
| States (empty/save/submit/lock) | 8 if U1–U5 |
| Specificity | 8 |
| Consistency with Field Mgmt | 8 |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U7) |
| **Date** | 2026-08-10 |
