# CEO Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Accepted** (CEO product review complete)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** |
| **Priority** | **High** — result import is table stakes for a modern LIMS; manual entry is not acceptable as the primary path |
| **MVP cut** | **P0 + P1** (catalogs, manual parsers, multi-file test harness, run lineage) |
| **P2 AI timing** | **After P0+P1 complete** — AI only for setup cost reduction, never for every result file |
| **Reviewer** | CEO / product |
| **Date completed** | 2026-07-12 |

## Responses to review asks

### 1. Value — reusable parsers vs always-on AI

**Confirmed.**

- An **instrument** reliably outputs the same file shape over time.  
- A **CRO** has its own data system that generates reports (stable per CRO source).  
- NimbleLIMS relies on that **consistency** to minimize cost: **create a parser once**, then run **deterministic import** forever.  
- **AI is not** used to parse every result file; AI (later) only helps **author** the parser.

### 2. Scope — P0+P1 before AI (P2)

**Confirmed.** P0 and P1 are **critical** and must be complete before AI parser config (P2). That sequencing is correct.

### 3. Scope key — analysis × instrument/CRO (not analysis alone)

**Confirmed** (and rationale locked).

- Result **formats and column names** vary by **instrument (model/vendor)** and by **CRO**.  
- A parser based **only on analysis** would have to handle every format/name variant → too complex and unmaintainable.  
- Therefore parsers (and run tracking of source) are **analysis + instrument** or **analysis + CRO**.

This also supports run fields: **instrument XOR CRO** + stored **`parser_id`** (default + override).

### 4. Parser testing — multi-file + edges

**Confirmed (elevated).**

- **Results are why NimbleLIMS exists.**  
- Multiple testing and edge cases are required so imported results are **correct**, not merely “parsed.”  
- Aligns with Decision #10: 1+ examples, 1+ tests, engine gate; AI edge suggestions in P2.

### 5. Open questions before implementation

**Confirmed process:** remaining open product/architecture questions will be **resolved before implementation starts** (per phase gate).

*Note:* Product later locked Q3 (`config:edit`), Q4 (block cross-analysis override), Q5 (versioning, no snapshot), Q6 (**no non-reportable runs**; method-dev deferred to lab projects). Remaining open questions still gate implementation where listed.

### 6. Roadmap priority

**High priority.** Manual data entry is a non-starter for modern LIMS; **result import is expected**. Ship this after/alongside core run-results; do not deprioritize as optional polish.

## Strategic summary

| Theme | Decision |
|-------|----------|
| Economics | Consistency of instrument/CRO outputs → one parser, many imports; AI setup-only |
| MVP | P0+P1; no AI required to unlock value |
| Correctness | Multi-file user testing + edges before activate |
| Scope key | Never analysis-only parsers |
| Priority | High — import is core product |

## Conditions / follow-ups

1. Architecture + security + UI reviews still required before implementation.  
2. Close blocking open questions (see open-questions log) before P0/P1 build.  
3. Do not start P2 until P0+P1 accepted and schema contract (Q1) locked.

## Notes

_No further CEO notes at this time._
