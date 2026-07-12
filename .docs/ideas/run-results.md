# Idea: Promote LimsRun JSONB data → Results

**Status:** Reviewed (CEO / design / tech / security) — open questions remain for implementation  
**Branch:** `run-results`  
**Date:** 2026-07-11

## One-liner

On **LimsRun publish**, map instrument **`lims_run_data.row_data` (JSONB)** columns into structured **`results`** rows (parent **test** + **analyte**, value → **`raw_result`**) for query, report, and reuse—when the assay is set up.

## Goal

Get run data into a **structured format** for easy querying, reporting, and use—without losing flexible JSONB import.

| Layer | Role |
|-------|------|
| Run JSONB | Flexible instrument/CRO import (SoT for raw instrument table) |
| Results | Official structured ledger (test/analyte/raw) after **publish** |

## Reviews & decisions

| Doc | Link |
|-----|------|
| CEO | [../ceo-review/run-results.md](../ceo-review/run-results.md) |
| Design | [../design-review/run-results.md](../design-review/run-results.md) |
| Tech | [../design/run-results.md](../design/run-results.md) |
| Security | [../security-review/run-results.md](../security-review/run-results.md) |
| Open questions | [../open-questions/run-results.md](../open-questions/run-results.md) |

### Locked

| Topic | Decision |
|-------|----------|
| **When** | Write results on **publish** |
| **What** | **`raw_result`** (calculated deferred) |
| **Map** | JSONB column → analyte (name + **aliases** + optional template map) → value |
| **Shape** | Multi-analyte columns → **many result rows** |
| **SoT** | Run keeps instrument data; results = published projection |
| **No** | Dump unmapped keys into `custom_attributes` |
| **Extensibility** | Result/test **custom fields** (Field Management already supports `tests` / `results`) for defined meta |

## Mapping sketch

```
LimsRun.analysis_id = Analysis "Metals Panel"
lims_run_data:
  sample_id = S1
  row_data  = { "Pb_ug_L": "12.3", "Arsenic": "0.4", "units": "ug/L" }

aliases: Pb_ug_L → analyte Lead
publish →
  ensure Test(S1, Metals Panel)
  result(that test, analyte Lead,    raw_result="12.3")
  result(that test, analyte Arsenic, raw_result="0.4")
  units skipped (not an analyte)

LimsRun with analysis_id NULL → publish only, no results written
```

## Run lifecycle (context)

**Standard:** `draft → running → complete → published` (+ failed/canceled)  
**CRO:** `draft → ordered → running → results_received → complete → published`  

Import allowed in `running` / `results_received`. **Structured results written at `published`.**

## Still open (see open-questions)

- Missing tests: block vs auto-create (lean find-or-create for sample+analysis)  
- Re-promote / conflict policy  
- Alias storage shape  
- Publish vs result:enter permissions  
- Lineage FK columns  

## Implementation phases (tech)

| Phase | Focus |
|-------|--------|
| P0 | Analyte aliases |
| P1 | Template promotion config + preview |
| P2 | Transactional promote on publish |
| P3 | Lineage UI |

## Non-goals (v1)

- General run calculation engine  
- Replacing dose-response tables  
- Write-back results → JSONB  
- Client-user publish/promote  
