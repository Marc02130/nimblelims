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
| **When** | Write results on **publish**, only if run has **`analysis_id`** |
| **Opt-in** | **`lims_runs.analysis_id`** + UI analysis list — not a separate promote flag |
| **Start guard** | If no analysis at **run start**, **warn** (no Tests/Results on publish) and offer associate / create analysis / continue without |
| **Objects vs instances** | Analysis/Analyte = catalog; Test/Result = instances. Analysis on run ⇒ **ensure** tests for samples |
| **What** | **`raw_result`** (+ **`replicate` int**); calculated deferred |
| **Map** | JSONB column → analyte (name + **maintained alias list on analyte**) → value; no pattern match |
| **AI later** | If no match / missing analysis analyte — see [ai-analyte-resolution.md](ai-analyte-resolution.md) |
| **Shape** | Multi-analyte → **many result rows**; multi-row same analyte → **`replicate`** (from JSONB or **row order**) |
| **Batch size** | Admin Lims Runs setting; **default 200** |
| **Conflicts** | Same run → **update**; other run same sample/analyte/replicate → **fail + notify** |
| **Lineage** | **`results.lims_run_id`** FK |
| **No result `name`** | Drop BaseModel name/uniqueness on results — not a named entity |
| **Preview** | Dry-run of **what would happen on publish** (creates/updates/conflicts) |
| **Permissions** | **Publish alone** enough for promote writes |
| **SoT** | Run keeps instrument data; results = published projection |
| **No** | Dump unmapped keys into `custom_attributes` |
| **Extensibility** | Result/test **custom fields** already in Field Management |

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

Import allowed in `running` / `results_received`. **Structured results written at `published` only when `analysis_id` is set.**

## Product policy closed

See [open-questions/run-results.md](../open-questions/run-results.md). Remaining work is implementation detail.

## Implementation phases (tech)

| Phase | Focus |
|-------|--------|
| P0 | Analyte aliases on analyte |
| P1 | `analysis_id` on lims_runs + UI + start warning |
| P2 | `results.lims_run_id`, `results.replicate` |
| P3 | Ensure test instance; promote on publish; update vs fail |
| P4 | Preview / notify UX |

## Non-goals (v1)

- General run calculation engine  
- Replacing dose-response tables  
- Write-back results → JSONB  
- Client-user publish/promote  
