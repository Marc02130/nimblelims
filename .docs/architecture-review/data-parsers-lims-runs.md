# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Resubmitted for review** — **tech sketch attached**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes (authoritative DB delta):** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask of architecture

1. **Verify schema** using **only** [schema-changes/data-parsers-lims-runs.md](../schema-changes/data-parsers-lims-runs.md) (ADD/ALTER/CHECK/index/RLS/out-of-scope)—do not reconstruct from seven narrative docs.  
2. Approve **ParserConfig v1** (app JSONB contract) + engine parity — tech sketch §5 / open Q1.  
3. Approve **ParserEngine** dual use: production import + setup test suite.  
4. Approve **default/override** resolution and “store parser_id, don’t silent re-resolve.”  
5. Approve **phase cut** P0/P1/P2 and migration/compat with template parsers.  
6. Lock or refine **Q1** and remaining schema blockers listed in schema-changes §7.

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
| **Verdict** | _Pending_ |
| **Schema approach approved** | _Pending_ |
| **ParserConfig v1 approved** | _Pending_ |
| **Phase cut approved** | _Pending_ |
| **Reviewer** | |
| **Date completed** | |

## Notes

_Add architecture decisions during review._
