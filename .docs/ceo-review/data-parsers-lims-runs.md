# CEO Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Resubmitted for review** (tech sketch ready)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Ask of CEO / product

1. Confirm **value**: reusable parsers per analysis×instrument/CRO beat per-template-only parsing and always-on AI.  
2. Confirm **scope**: MVP = **P0+P1** (catalogs + manual parsers + multi-file test harness + run lineage). AI setup = **P2**.  
3. Confirm **run fields**: track instrument XOR CRO + stored `parser_id` (default + override).  
4. Confirm **parser testing**: 1+ examples, 1+ tests, engine gate before activate (Decision #10 provisional).  
5. Decide open product questions (permissions, non-reportable import, override rules)—see open-questions Q2–Q8, #10a–c.  
6. Priority relative to other roadmap (post run-results).

## Executive brief

**Problem:** Import is template-tied; CRO/lab file shapes repeat but aren’t first-class. Promote needs stable columns.

**Solution:** Parsers as **DB JSON instructions** keyed by analysis + instrument|CRO. Runs store source + which parser was used. Setup includes **user testing** (multi-file dry-run). AI only helps **create** config and **suggest edge tests**—never on daily import.

**Why it wins:** Set up once, reuse forever; auditable; cheap day-to-day; cleaner published Results.

**Risks:** Scope creep into equipment CMMS; concept overload (template vs parser vs analysis); AI over-promising.

## Phased ask

| Phase | Ship | Needs CEO OK? |
|-------|------|----------------|
| P0 | Instrument + CRO catalogs | Yes (MVP include) |
| P1 | Parsers + run lineage + test harness | Yes (MVP core) |
| P2 | AI draft + edge suggestions | Separate go/no-go after P1 |

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ |
| **Priority** | _Pending_ |
| **MVP cut** | _Pending_ (recommend P0+P1) |
| **P2 AI timing** | _Pending_ |
| **Reviewer** | |
| **Date completed** | |

## Notes / decisions

_Add product decisions here during review._
