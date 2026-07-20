# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12 · **Updated:** 2026-07-19  
**Status:** **In progress** — schema verified (re-check after versioning delta); remaining asks open  
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
| 4 | Approve **default/override** + store **version** `parser_id` **per import** (multi-instrument; active-only resolve; no JSON snapshot; no silent re-resolve) | _Pending_ — Decision #5 + #16 / schema `lims_run_imports` |
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
| Q9 | **Decided:** rename → **`data_parsers`** |
| Q5 | **Decided:** version_group + version + active; no import JSON snapshot |

## Risks to confirm

- CHECK constraints for XOR instrument/cro  
- Partial unique: one **active** version per `version_group_id`; UNIQUE `(version_group_id, version)`  
- Partial unique indexes for is_default among **active** versions  
- Immutability of `parser_config` enforced in app (no PATCH of definition)  
- Setup files: **persisted in P1** (`parser_setup_files`) — not ephemeral (product 2026-07-18); likely copy or re-link on new version  
- Pre-release: simple migrate/delete of old template parsers; **no** dual-write cutover  
- **Multi-tenant / org segregation: out of scope** — lab-global config; see [ideas/multi-tenant.md](../ideas/multi-tenant.md)

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
- **2026-07-19:** Product locked **Decision #5** — parser versioning + active; **reject** import-time config snapshot. Schema-changes updated; architecture should re-verify ask #1 against new columns/constraints.
