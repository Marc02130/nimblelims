# CEO Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Awaiting review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Ask of CEO / product

1. Confirm **value**: reusable parsers per analysis×instrument/CRO beat per-template-only parsing and always-on AI.  
2. Confirm **scope**: MVP = catalogs + manual parsers + run lineage (no AI required). AI setup = phase 2.  
3. Confirm **run fields**: always track instrument XOR CRO + stored parser_id (default + override).  
4. Decide open questions Q1–Q6 in requirements (especially permissions and non-reportable import).  
5. Priority relative to other roadmap (post run-results).

## Executive brief (for reviewer)

**Problem:** Import is tied to experiment templates; CRO/lab file shapes repeat but aren’t first-class. Promote-on-publish needs stable columns.

**Solution:** Parsers as **DB JSON instructions** keyed by analysis + instrument|CRO. Runs store source + which parser was used. AI only helps **create** the parser from a sample text file.

**Why it wins:** Set up once, reuse forever; auditable; cheap day-to-day; strengthens published Results quality.

**Risks:** Scope creep into full equipment CMMS; confusing three concepts (template vs parser vs analysis); AI over-promising.

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ |
| **Priority** | _Pending_ |
| **MVP cut** | _Pending_ |
| **Reviewer** | |
| **Date completed** | |

## Notes / decisions

_Add product decisions here during review._
