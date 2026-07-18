# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12 · **Updated:** 2026-07-18  
**Status:** **In progress** — schema verified; remaining asks open  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes (authoritative DB delta):** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask of architecture

| # | Ask | Status |
|---|-----|--------|
| 1 | **Verify schema** using **only** [schema-changes/data-parsers-lims-runs.md](../schema-changes/data-parsers-lims-runs.md) | **Done — verified** (2026-07-18) |
| 2 | Approve **ParserConfig v1** + engine parity — tech sketch §5 / open Q1 | _Pending_ |
| 3 | Approve **ParserEngine** dual use: production import + setup test suite | _Pending_ |
| 4 | Approve **default/override** + store `parser_id` (no silent re-resolve) | _Pending_ |
| 5 | Approve **phase cut** P0/P1/P2 + **DROP `experiment_template_id`** | _Pending_ (DROP already decided in open Q15 / schema-changes; confirm) |
| 6 | Lock **Q1** + schema blockers in schema-changes §7 | _Pending_ |

## Sketch summary

| Area | Where to review |
|------|-----------------|
| **DB tables/columns/constraints** | **[schema-changes/…](../schema-changes/data-parsers-lims-runs.md)** |
| Engine, APIs, setup flows | [tech-sketch/…](../tech-sketch/data-parsers-lims-runs.md) |
| Product scope / priority | [ceo-review/…](../ceo-review/data-parsers-lims-runs.md) (Accepted) |
| Decisions still open | [open-questions/…](../open-questions/data-parsers-lims-runs.md) |

## Priority open questions for this review

| # | Topic |
|---|--------|
| **Q1** | Canonical ParserConfig + AI must emit same schema |
| **#10** | Multi-file testing; AI edges judged by engine |
| Q9 | Keep table name `instrument_parsers` |
| Q5 | Snapshot config on import (lean defer) |

## Risks to confirm

- CHECK constraints for XOR instrument/cro  
- Partial unique indexes for is_default  
- Whether setup files are ephemeral in P1  

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _In progress_ (not final Accept until 2–6 done) |
| **Schema approach approved** | **Yes** — verified against schema-changes doc (2026-07-18) |
| **ParserConfig v1 approved** | _Pending_ |
| **Phase cut approved** | _Pending_ |
| **Reviewer** | Architecture |
| **Date completed** | |

## Notes

- **2026-07-18:** Schema verified using schema-changes doc only (ask #1).
