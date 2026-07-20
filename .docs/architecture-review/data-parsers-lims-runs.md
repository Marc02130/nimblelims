# Architecture Review: Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12 · **Updated / resubmitted:** 2026-07-19  
**Status:** **Resubmitted for architecture (design) review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes (authoritative DB delta):** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask of architecture (this pass)

Re-verify and **accept or condition** the full design. Product open questions are **closed**. Prior ask #1 (schema) was verified 2026-07-18 — **re-check** after rename + versioning + `lims_run_imports`.

| # | Ask | Status |
|---|-----|--------|
| 1 | **Verify schema** using **only** [schema-changes](../schema-changes/data-parsers-lims-runs.md) | Was verified 2026-07-18 — **re-verify** full delta |
| 2 | Approve **ParserConfig v1** + engine parity — tech sketch §5 / **Decision #1 accepted** | _Pending re-accept_ |
| 3 | Approve **ParserEngine** dual use: production import + setup test suite | _Pending_ |
| 4 | Approve **default/override** + store **version** `parser_id` per import (`lims_run_imports`; active-only; no snapshot) | _Pending_ |
| 5 | Approve **phase cut** P0/P1/P2 + **DROP template FK** + **RENAME → data_parsers** | _Pending_ |
| 6 | Confirm **no open product blockers** for P0/P1 | Product: **closed** 2026-07-19 |

## Authoritative sources

| Area | Doc |
|------|-----|
| **DB delta** | [schema-changes/…](../schema-changes/data-parsers-lims-runs.md) |
| Engine / APIs / flows | [tech-sketch/…](../tech-sketch/data-parsers-lims-runs.md) |
| Product | [ceo-review](../ceo-review/data-parsers-lims-runs.md) · [open-questions](../open-questions/data-parsers-lims-runs.md) |

## Locked product decisions (architecture must implement)

| ID | Decision |
|----|----------|
| #1 | **ParserConfig schema-first** (Pydantic + JSON Schema; validate all writers; AI same schema) |
| #5 | Version rows + `active`; no import JSON snapshot |
| #6 | **analysis_id required** on every run |
| #9 | Table **`data_parsers`** (rename from `instrument_parsers`) |
| #10 / 10b / 10c | Persist setup files; **10 files, 10 MB each**; activate only if **all** hard-error-free |
| #11 / #17 | Instrument\|CRO + **M2M** `parser_analyses` |
| #15 | DROP `experiment_template_id` |
| #16 | Multi-instrument imports via **`lims_run_imports`** |
| Q2 | Instrument **type + instance** |
| Q3 | Permission **`config:edit`** |
| Q7 | Lab-global catalogs; multi-tenant OOS |
| Q8 | `is_default` provisional |

## Schema highlights to re-verify

- RENAME `instrument_parsers` → **`data_parsers`**  
- `version_group_id`, `version`, `active` + partial unique one active per group  
- XOR `instrument_id` / `cro_source_id`  
- `parser_analyses`, `parser_setup_files`, `lims_run_imports`  
- `lims_runs.analysis_id` target **NOT NULL**  
- No `parser_config_snapshot`  

## Risks to confirm

- Immutability of version rows in app  
- Default uniqueness among **active** versions  
- Setup files attached per version vs group  
- RLS after rename  
- Pre-release delete of template-scoped rows  

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ (Accept / Accept with conditions / Reject) |
| **Schema approach approved** | _Re-verify_ |
| **ParserConfig v1 approved** | Product accepted Decision #1 — _arch confirm_ |
| **Phase cut approved** | _Pending_ |
| **Reviewer** | Architecture |
| **Date completed** | |

## Notes

- **2026-07-18:** Schema verified (pre-versioning/rename).  
- **2026-07-19:** Product closed Q1, #10b, #10c; full delta resubmitted for architecture re-accept.
