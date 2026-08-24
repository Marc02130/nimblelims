# Architecture Review: Experiment template entries

**Date:** 2026-08-10  
**Status:** **Accept with conditions**  
**Tech sketch:** [§0](../tech-sketch/experiment-template-entries.md)  
**Schema:** [schema-changes](../schema-changes/experiment-template-entries.md) — no new value tables for substrate  
**Lab Ops:** L1–L9 (incl. **all** aliquot methods)  

## Ask results

| # | Ask | Status |
|---|-----|--------|
| 1 | Logical kinds on entries + EAV values | **Accept** |
| 2 | Grid (wide) + export (long) + values upsert + submit | **Accept — required** |
| 3 | Write-back config on entry column; submit-only | **Accept** |
| 4 | Cohort fixed at start; no mid-flight sample add | **Accept** |
| 5 | Aliquot execute: container amounts + new samples | **Accept — transactional** |
| 6 | All aliquot methods in v1 | **Accept** (product non-negotiable) |
| 7 | No volume stored; mass/count in amount | **Accept — enforce in services** |

## Architecture

```
Template.template_definition.entries[]
        │ instantiate
        ▼
entries (type, config, predefined_entry_key)
  ├── entry_field_definitions (+ write_back_target)
  └── entry_field_values (typed; sample_id for sample kind)

Queue select → experiment_sample_executions (fixed cohort)
        │
        ├── GET …/grid
        ├── PUT …/values          (save)
        ├── POST …/submit         (write-back + complete)
        └── POST …/execute        (aliquot/pool predefined)

Containers / contents  ←── aliquot execute updates
LIMS Run + analysis_id ←── instrument path only
```

## Aliquot methods (v1 — full matrix)

Implement as **method enum + column profile + calc rules**, not separate entry types:

| Method | Input emphasis | Persist |
|--------|----------------|---------|
| By mass | amount (mass) to move | amount on plan/execute |
| By volume | volume + conc → **mass** | amount (mass) + conc |
| Target mass | dest mass | amount |
| Target volume | dest vol + conc → mass | amount + conc |
| Target concentration | target conc + mass or vol rule | amount + conc |

All methods share execute: reduce source contents amount; create dest container/sample/contents.

## Conditions

| ID | Condition |
|----|-----------|
| **A1** | Types `experiment_sample_data` / `experiment_data` (+ legacy aliases) |
| **A2** | `GET …/grid`, `GET …/export`, `PUT …/values`, `POST …/submit` |
| **A3** | Write-back only on submit; config-eligible Sample targets; type match |
| **A4** | Never persist volume as amount; convert volume+conc → mass+conc |
| **A5** | Aliquot execute in one DB transaction (source reduce + dest create) |
| **A6** | All method modes supported in v1 API/UI (method flag + column set) |
| **A7** | Entry dependency checks before start next / complete experiment |
| **A8** | Tests: grid empty/full, submit write-back, each aliquot method path, pool multi-content tube |
| **A9** | No migration required for EAV substrate; container amount semantics enforced in service |

## Failure modes (critical)

| Path | Failure | Handling |
|------|---------|----------|
| Execute without source amount | Underflow | 400; no partial write |
| Volume stored as amount | Data corruption | Reject / convert |
| Submit write-back bad target | Integrity | 400; target must be eligible |
| Dual submit same sample field | Expected | Last write wins + audit |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (A1–A9) |
| **Date** | 2026-08-10 |
| **Schema** | No new EAV tables; aliquot uses existing containers/contents + new samples |
