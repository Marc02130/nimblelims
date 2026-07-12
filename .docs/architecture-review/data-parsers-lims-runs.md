# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Awaiting review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**As-is code:** `InstrumentParser`, `InstrumentDataService`, `LimsRunService.import_data`, SOP parse

## Ask of architecture

1. Confirm **parsers as JSONB instructions** + single generic engine (no plugin code).  
2. Confirm **schema evolution** of `instrument_parsers` (add analysis_id, instrument_id, cro_source_id; relax template FK).  
3. Confirm **lims_runs** FKs: `instrument_id`, `cro_source_id`, `parser_id` and resolution rules.  
4. Migration strategy from template-scoped parsers.  
5. API surface sketch and phase boundaries (P0/P1/P2).  
6. Interaction with promote-on-publish (field_name stability).

## Current state

| Component | Today |
|-----------|--------|
| `instrument_parsers` | `experiment_template_id` required; `parser_config` JSONB |
| Import | Resolves parser **only** via template |
| Run | Has `analysis_id`; no instrument/CRO/parser_id |
| Engine | `InstrumentDataService(parser_config)` |
| AI | SOP parse → template + parser + worklist |

## Target architecture (for review)

```
instruments / cro_sources  (light catalogs)
        │
        ▼
parsers (analysis_id + instrument_id | cro_source_id, parser_config JSONB)
        │
        │  FK parser_id (stored)
        ▼
lims_runs (analysis_id, instrument_id|cro_source_id, parser_id)
        │
        │  import uses parser_config
        ▼
lims_run_data  →  publish promote (existing)
```

**Import resolution:** use stored `run.parser_id`; if null, resolve default and **persist**, or 400.

**Engine:** one code path reads JSONB; no dynamic code load.

## Risks / tradeoffs

| Topic | Options | Lean |
|-------|---------|------|
| Snapshot config on import | FK only vs JSONB copy | FK for MVP |
| Template FK | Keep nullable legacy | Yes |
| Table rename | keep `instrument_parsers` vs `data_parsers` | Keep name or alias |
| Unique constraint | (analysis, instrument) unique default | is_default + unique partial index |

## Open architecture questions

**Log:** [open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md)

**Priority for this review:** **Q1** — canonical `ParserConfig` / JSON Schema shared by engine, API, UI, and AI; validate before save; dry-run sample file; `schema_version` evolution.

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ |
| **Schema approach approved** | _Pending_ |
| **Phase cut approved** | _Pending_ |
| **Reviewer** | |
| **Date completed** | |

## Notes

_Add architecture decisions during review._
