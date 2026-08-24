# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12 · **Updated:** 2026-07-19  
**Verdict date:** 2026-07-19  
**Status:** **Accepted with conditions**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes (authoritative DB delta):** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask results

| # | Ask | Status |
|---|-----|--------|
| 1 | Verify schema (schema-changes only) | **Accept** — re-verified 2026-07-19 (rename, versioning, imports, M2M) |
| 2 | ParserConfig v1 + engine parity | **Accept** — Decision #1; engine **must** implement every model field in same phase as schema use |
| 3 | ParserEngine dual use (import + setup suite) | **Accept** — single code path required |
| 4 | Default/override + version `parser_id` per import | **Accept** — `lims_run_imports`; active-only resolve; no snapshot |
| 5 | Phase cut + DROP template FK + RENAME `data_parsers` | **Accept** |
| 6 | Product blockers | **None** (Q8 provisional OK) |

## Schema re-verify notes

**Sound:**

- XOR instrument/CRO on parsers and imports  
- Version unique + partial unique one active per `version_group_id`  
- M2M `parser_analyses` per version row  
- Import lineage via `lims_run_imports` + optional `lims_run_data.import_id`  
- No snapshot column (version FK is lineage)  
- `analysis_id` required on run aligns with import validity  

**Implementation conditions (non-blocking for Accept):**

| # | Condition |
|---|-----------|
| A1 | **Engine parity:** every `ParserConfig` field used by validators is honored by `ParserEngine` in P1 (no orphan keys). |
| A2 | **Immutability:** API forbids PATCH of `parser_config` / source FKs on existing version rows; “edit” = insert version. |
| A3 | **Setup files:** decide in impl — attach to **version row** (recommended: copy or re-link on new version) so historical version keeps fixtures; document choice in schema-changes checklist. |
| A4 | **`analysis_id` NOT NULL:** migration backfills or deletes null-analysis runs before NOT NULL (pre-release: delete OK). |
| A5 | **`is_default` (Q8):** app-enforced among active versions is fine; add partial unique later if races appear. |
| A6 | **RLS:** after RENAME, recreate policies on `data_parsers`; catalogs lab-config only (not client-writable). |
| A7 | **SOP parse:** stop writing template-linked parsers in the same release as DROP. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (A1–A7 above) |
| **Schema approach approved** | **Yes** |
| **ParserConfig v1 approved** | **Yes** |
| **Phase cut approved** | **Yes** — P0 catalogs → P1 parsers/import → P2 AI |
| **Reviewer** | Architecture |
| **Date completed** | 2026-07-19 |

## Notes

- 2026-07-18: Initial schema verify (pre-versioning).  
- 2026-07-19: Full delta Accept with implement conditions; ready for P0/P1 build when Security/UI/CEO also accepted.
