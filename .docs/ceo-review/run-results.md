# CEO Review: LimsRun → Results (structured promotion)

**Date:** 2026-07-11  
**Branch:** `run-results`  
**Reviewer:** CEO / Product Strategy  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)

## Executive Summary

**Verdict: High-value, correctly scoped product bridge. Ship it.**

LimsRuns solve **import flexibility** (instrument/CRO files → JSONB rows). Classic **Results** solve **query, report, and client-facing LIMS outcomes** (test + analyte + raw). Today those worlds barely touch—labs re-enter or live forever in unqueryable JSONB.

Promoting run data into **structured `results` rows when the run is published** is the right product moment: publish already means “this data is ready for official use,” matches `experiment:publish`, and avoids polluting results with draft/partial imports.

**Bottom line:** This is not a science feature; it is a **data product** feature. Env labs and CROs pay for clean, reportable results without killing flexible import. Prioritize after core run import is solid.

## Market fit

| Segment | Why this matters |
|---------|------------------|
| **Env lab** | Multi-analyte panels; clients expect structured results, not CSV dumps |
| **CRO / sponsor handoff** | Import CRO file on run; publish → sponsor-visible structured results (with client RLS) |
| **Biotech internal** | Dose-response stays specialized; classic assays still need Results ledger |

**What wins:** One-click (or automatic-on-publish) path from instrument table → queryable results; analyte aliases so CRO column soup maps to one catalog.  
**What loses:** Promoting too early (draft noise); silent overwrite of reviewed results; dumping junk into `custom_attributes`.

## Locked product rules (this review)

| Rule | Decision |
|------|----------|
| **When data is written to results** | **On run publish**, only if run has **`analysis_id`** |
| **Opt-in** | Associate LimsRun with an **Analysis** (new FK + UI list)—not a separate promote flag |
| **What is written** | Primarily **`raw_result`** from mapped JSONB values onto **tests** for that analysis |
| **Column → analyte** | JSONB key resolves via analyte **name** and **aliases** (multi-CRO) |
| **Cardinality** | One mapped analyte column per sample → one result row (multi-analyte = multi-row) |
| **Instrument SoT** | `lims_run_data` remains instrument truth; results are the **published structured projection** |
| **Who runs it** | Lab personnel (result enter / publish rights)—not lab client config |

## Strategic opportunities

1. **Publish = structure** — Make “Publish run” the moment the lab’s official results ledger updates.  
2. **Assay setup as product** — Template promotion map + analyte aliases become reusable CRO kits.  
3. **Reporting without JSONB** — SQL/BI on `results`/`tests`/`samples` instead of parsing `row_data`.  
4. **Client portal later** — Structured results + #7 journey already fit client-scoped visibility.

## Scope

### Do first (v1)

- Promotion **triggered on publish** (configurable map on template; optional dry-run/preview before publish).  
- Map JSONB keys → analytes (name + aliases) → create/update `results.raw_result`.  
- Require assay setup: sample has tests; analytes belong to analysis as needed.  
- Lineage: record source run (and ideally data row) for audit.  
- Fail publish (or block promote step) with clear errors if mapping/tests incomplete—**don’t** publish half-structured.

### Defer

- General calculation engine on runs  
- Auto-filling `calculated_result` (unless value already in file)  
- Replacing dose-response tables  
- Bidirectional sync results ↔ JSONB  
- Client-user-triggered promote  

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Publish succeeds but results wrong/missing | High | Pre-publish validation; preview; atomic promote-with-publish or compensating fail |
| Overwrite human-edited results | High | Policy: first-write vs skip-if-edited vs require confirm |
| Duplicate results on re-publish | Medium | Idempotent key (test + analyte [+ source run]) |
| Wrong analyte via bad alias | Medium | Alias admin UX; conflict detection if two analytes claim same alias |
| Scope creep into full ETL platform | Medium | v1 = raw_result + aliases + publish hook only |

## Open strategic questions

1. On re-publish / re-promote: update existing results or fail if already promoted?  
2. Missing tests: block publish vs **auto-create** test for (sample, analysis)? (lean create)

## Recommendations

1. **Promote on publish when `analysis_id` is set**—analysis association is the opt-in.  
2. **Invest in analyte aliases** as a first-class lab catalog feature—high leverage for multi-CRO.  
3. **Keep Field Management on results** for extra meta; do not dump unmapped JSONB into custom_attributes.  
4. **Measure:** % of analysis-linked published runs that produce ≥1 result; alias/map error rates.

**CEO score: 8.5/10** — clear customer value, fits existing lifecycle, bounded scope if publish-gated.

---

Related: [design-review](../design-review/run-results.md) · [tech](../design/run-results.md) · [security](../security-review/run-results.md)
