# CEO Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19 (product delta — confirm still Accept)  
**Status:** **Resubmitted for CEO review**  
**Prior verdict:** Accept (2026-07-12) — please re-confirm after product locks below  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Ask of CEO (this pass)

Re-review the **product delta since original Accept**. Confirm:

1. Still **high priority** / P0+P1 MVP, AI setup-only later.  
2. Delta below is **acceptable** (no re-open of closed strategy).  
3. Ready for Architecture / Security / UI re-accept, then implementation.

## Original verdict (2026-07-12) — still in force unless you reject delta

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** (pending re-confirm) |
| **Priority** | **High** — result import is table stakes |
| **MVP cut** | **P0 + P1** |
| **P2 AI timing** | After P0+P1; setup only |
| **Reviewer** | CEO / product |
| **Date completed** | 2026-07-12 |

## Product delta since original Accept (for re-confirm)

| Topic | Decision |
|-------|----------|
| Parser ↔ analysis | **M2M** `parser_analyses` (one ICP → RCRA-8 + RCRA-13) |
| Instruments | **Type** (vendor/model) + **instance** (serial); parsers key **instance** |
| Multi-import on a run | **`lims_run_imports`**; each import: instrument\|CRO + parser version |
| Analysis on run | **Required always** — no non-reportable / null-analysis path |
| Method-dev | **Deferred** to [orders/projects idea](../ideas/orders-and-projects.md) |
| Permissions | **`config:edit`** for instruments, CRO sources, data parsers |
| Versioning | **No JSON snapshot** on import; **version + active** on parser rows; edit → new version; activate prompt |
| Table name | **`data_parsers`** (rename from `instrument_parsers`) |
| ParserConfig (Q1) | **Schema-first proposal accepted** (Pydantic + validate all writers; AI same schema) |
| Setup tests (#10) | 1+ example, 1+ test, **persisted**; caps **10 files / 10 MB each**; activate only if **all** tests hard-error-free |
| Multi-tenant | **OOS** until real multi-org users |
| Template parsers | **DROP** `experiment_template_id` |

### Still out of scope / deferred ideas

- Lab buildings/rooms ([lab-locations](../ideas/lab-locations.md))  
- Rename today’s projects → orders + new lab projects ([orders-and-projects](../ideas/orders-and-projects.md))  
- Multi-tenant segregation  

## Original strategy (unchanged)

| Theme | Decision |
|-------|----------|
| Economics | One parser, many imports; AI setup-only |
| Correctness | Multi-file testing before activate |
| Scope key | Never analysis-only parsers |
| Priority | High |

## Conditions for implementation

1. Architecture + Security + UI **re-accept** this delta.  
2. Product open questions **closed** (2026-07-19).  
3. P2 only after P0+P1 ship.

## Verdict (this resubmission — fill in)

| Field | Value |
|-------|--------|
| **Re-confirm Accept?** | _Pending_ |
| **Delta issues / vetoes** | |
| **Reviewer** | CEO / product |
| **Date** | |

## Notes

_Original Accept 2026-07-12. Resubmitted 2026-07-19 after Q1 / #10b / #10c lock and full product delta above._
