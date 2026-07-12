# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Resubmitted for review** — **tech sketch attached**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask of architecture

1. Approve **schema evolution** of `instrument_parsers` + new catalogs + lims_runs FKs.  
2. Approve **ParserConfig v1** fields and `extra=forbid` + engine parity (delimiter/encoding).  
3. Approve **ParserEngine** dual use: production import + setup test suite.  
4. Approve **default/override** resolution and “store parser_id, don’t silent re-resolve.”  
5. Approve **phase cut** P0/P1/P2 and migration/compat with template parsers.  
6. Lock or refine **Q1** (schema-first AI/config contract) and **#10** test harness details.

## Sketch summary

| Area | Proposal |
|------|----------|
| Catalogs | `instruments`, `cro_sources` |
| Parser row | analysis + instrument XOR cro; `parser_config` JSONB; is_default |
| Run | instrument_id XOR cro_source_id; parser_id stored |
| Engine | Extend `InstrumentDataService`; single contract |
| Setup | Multi-file examples/tests; activate gate; P2 AI draft + edge fixtures |
| Legacy | Template parser fallback; nullable template FK |

Full detail: **tech sketch** (data model, API sketch, flows, migration).

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
