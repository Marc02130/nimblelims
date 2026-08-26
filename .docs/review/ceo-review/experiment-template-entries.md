# CEO / Product Review: Experiment template entries

**Date:** 2026-08-10  
**Status:** **Accept with conditions**  
**Mode:** HOLD SCOPE (v1 spine locked; no catalog expansion)  
**Tech sketch:** [§0 locked foundation](../tech-sketch/experiment-template-entries.md)  
**Lab Ops:** [Accept L1–L9](../lab-ops-review/experiment-template-entries.md)  

## Executive summary

This is the right product cut for ELN data capture: **two base entry kinds**, a **real start path** (queue → select → fixed cohort), **aliquot/pool with full method matrix and execute**, and **LIMS Run** for instruments. Deferring materials, index sets, and accessioning rewrite keeps the phase shippable without undercutting lab credibility.

**Verdict: Accept with conditions** aligned with Lab Ops L1–L9.

## Scope freeze (v1)

| In | Out (ideas) |
|----|-------------|
| experiment_sample_data / experiment_data | Materials/lots |
| Queue + scan plate/tube + start experiment/run | Index sets / assignment entry |
| Header, Samples, Aliquot/pool plan+results (all methods) | Sequencer-specific sample sheet product |
| Grid + export + save/submit + write-back map | Accessioning manifest/verify rewrite |
| Template UI (entries, columns, deps, methods) | Full commercial-LIMS entry catalog |
| LIMS Run + analysis required | Mid-flight add samples to experiment |

## Conditions

| ID | Condition |
|----|-----------|
| **C1** | Do not drop any aliquot/pool **method** from v1 (Lab Ops L9) |
| **C2** | Ship queue/start for experiment **and** LIMS run in the same phase as entries (otherwise spine is unusable) |
| **C3** | Keep OOS list honest in UI/docs (no promising materials/index in this phase) |
| **C4** | Default experiment complete = all entries submitted |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (C1–C4 + Lab Ops L1–L9) |
| **Date** | 2026-08-10 |
| **Implement after** | UI + Architecture + Security Accept |
