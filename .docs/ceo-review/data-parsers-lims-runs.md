# CEO Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19  
**Verdict date:** 2026-07-19  
**Status:** **Accepted** (re-confirmed)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Verdict

| Field | Value |
|-------|--------|
| **Re-confirm Accept?** | **Yes — Accept** |
| **Delta issues / vetoes** | **None.** Delta strengthens correctness (versioning, all-clean activate, analysis required) without expanding MVP scope. |
| **Priority** | **High** — result import remains table stakes |
| **MVP cut** | **P0 + P1**; P2 AI after P0+P1 |
| **Reviewer** | CEO / product |
| **Date** | 2026-07-19 |

## Product delta (accepted as locked)

| Topic | Decision |
|-------|----------|
| Parser ↔ analysis | **M2M** `parser_analyses` |
| Instruments | **Type** + **instance**; parsers key instance |
| Multi-import | **`lims_run_imports`** + version `parser_id` |
| Analysis on run | **Required always** — no non-reportable path |
| Method-dev | Deferred to [orders/projects](../ideas/orders-and-projects.md) |
| Permissions | **`config:edit`** |
| Versioning | Version + active; no import JSON snapshot |
| Table name | **`data_parsers`** |
| ParserConfig | Schema-first **accepted** |
| Setup tests | Persist; **10 files / 10 MB**; activate only if **all** hard-error-free |
| Multi-tenant | OOS |
| Template parsers | DROP `experiment_template_id` |

## Strategy (unchanged)

| Theme | Decision |
|-------|----------|
| Economics | One parser, many imports; AI setup-only |
| Correctness | Multi-file testing before activate |
| Scope key | Never analysis-only parsers |
| Priority | High |

## Conditions for implementation

1. Architecture + Security + UI verdicts processed (same day resubmission).  
2. Product open questions remain closed (Q8 provisional OK).  
3. P2 only after P0+P1 ship.

## Notes

Original Accept 2026-07-12. Re-confirmed 2026-07-19 after full product delta. No strategy re-open.
