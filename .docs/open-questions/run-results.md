# Open Questions — LimsRun → Results

**Status:** Living decision log  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)  
**Reviews:** [CEO](../ceo-review/run-results.md) · [Design](../design-review/run-results.md) · [Tech](../design/run-results.md) · [Security](../security-review/run-results.md)  
**Branch:** `run-results`

## Gate rule

Do not implement a phase until questions that block it are **Decided** (or provisional with written default).

| Status | Meaning |
|--------|---------|
| **Open** | Blocks related work |
| **Decided (provisional)** | Ship temporary rule |
| **Decided** | Locked |
| **Deferred** | Out of scope for named phase |

---

## Questions

| # | Question | Status | Blocks | Decision | Date | Owner | Rationale |
|---|----------|--------|--------|----------|------|-------|-----------|
| 1 | When are structured results written from run data? | **Decided** | Whole feature | **On run publish** (`→ published`) | 2026-07-11 | Product | Official moment; matches publish permission |
| 2 | What value field is filled in v1? | **Decided** | Mapping | **`raw_result`** from JSONB value; calculated deferred | 2026-07-11 | Product | No general run calc engine |
| 3 | How do JSONB columns resolve to analytes? | **Decided (provisional)** | Mapping | Name match + **aliases** + optional template map | 2026-07-11 | Product | Multi-CRO column names |
| 4 | Cardinality: multi-analyte columns? | **Decided** | Promote service | **One column → one result row** per sample/test; multi-analyte = multi-row | 2026-07-11 | Product | Matches results model |
| 5 | Instrument vs results SoT? | **Decided** | Integrity | Run JSONB remains instrument SoT; results = published projection | 2026-07-11 | Product | Align Decision #1g |
| 6 | Always promote on publish, or opt-in? | **Decided** | Publish hook | See **Decision #6**. Promote when run has **`analysis_id` set** and status → **published**. No analysis → publish without promoting to tests/results. | 2026-07-11 | Product | Analysis association is the opt-in; clear assay setup |
| 7 | Missing tests on sample: block publish vs auto-create? | **Open** | Promote readiness | With analysis FK: lean find-or-create test for (sample, analysis) — confirm | | | |
| 8 | Re-promote / existing results: update, skip, or fail? | **Open** | Idempotency | | | | |
| 9 | Alias storage: on analyte, template only, or both? | **Open** | P0 aliases | Lean **both** (analyte defaults + template override) | | | |
| 10 | Permissions: publish alone vs publish + result:enter? | **Open** | AuthZ | Security wants explicit model | | | |
| 11 | Lineage: first-class FKs on results? | **Open** | Schema | Lean yes (`source_lims_run_id`, `source_lims_run_data_id`) | | | |
| 12 | Unmapped JSONB keys → custom_attributes? | **Decided** | Scope | **No** by default | 2026-07-11 | Product | Prefer Field Management for meta |
| 13 | Dose-response integration? | **Deferred** | — | Separate tables; not classic promote v1 | 2026-07-11 | | |
| 14 | Replicates: multiple rows same sample+analyte? | **Open** | on_conflict | | | | |

---

## Phase gate

| Phase | Scope | Open blockers |
|-------|--------|---------------|
| **P0** | Analyte aliases | **#9** |
| **P1** | Template promotion config + preview; analysis selection UX | — |
| **P2** | Promote on publish when `analysis_id` set (transactional) | **#7**, **#8**, **#10**, **#11**, **#14** |
| **P3** | UI lineage / polish | — |

---

## Decision #1 — Write on publish

**Status:** Decided · **Date:** 2026-07-11

Structured `results` rows are created/updated when the LimsRun transitions to **`published`**, not on import and not on complete alone.

---

## Decision #2 — raw_result v1

**Status:** Decided · **Date:** 2026-07-11

Promotion fills **`raw_result`**. `calculated_result` is out of scope until a calc product exists.

---

## Decision #4 — Multi-row multi-analyte

**Status:** Decided · **Date:** 2026-07-11

Each mapped analyte column produces its own result row (infinite rows per test allowed by the model).

---

## Decision #5 — Dual SoT roles

**Status:** Decided · **Date:** 2026-07-11

- **Instrument truth:** `lims_run_data`  
- **Reportable structured truth:** `results` after publish  

No write-back from results to JSONB in v1.

---

## Decision #12 — No JSONB dump to custom_attributes

**Status:** Decided · **Date:** 2026-07-11

Do not auto-copy unmapped keys into `results.custom_attributes`. Use result Field Management / custom fields for defined meta.

---

## Decision #6 — Opt-in via Analysis association

**Status:** Decided · **Date:** 2026-07-11

### Product rule

| Condition | On publish |
|-----------|------------|
| LimsRun has **`analysis_id`** (FK → `analyses`) selected in UI | **Promote** run data → **tests** + **results** for each sample on the data rows |
| LimsRun has **no** `analysis_id` | Publish only — **no** structured results written |

There is no separate “promote_on_publish” boolean. **Associating the run with an analysis is the opt-in.**

### Implications

1. **Schema:** `lims_runs.analysis_id` nullable FK to `analyses.id`.  
2. **UI:** Analysis selection list on create/edit run (required for structured reporting path).  
3. **Test target:** For each distinct `sample_id` in `lims_run_data`, results hang off a **test** for that sample under the chosen analysis (find existing or create — see open **#7**).  
4. **Analyte scope:** Prefer analytes on that analysis (via `analysis_analytes`) when resolving columns; aliases still apply.  
5. **Template default:** Optional default `analysis_id` from template for convenience; run can override.

### Rationale

- Analysis is already the LIMS assay unit linking samples → tests → analytes.  
- Makes “this run is for this assay” explicit for multi-CRO and multi-analyte panels.  
- Runs used only for plate QC / dose-response / non-reportable work stay free of forced results by leaving analysis unset.

---

## Related

- LimsRun lifecycle: [../manuals/lims-runs.md](../manuals/lims-runs.md)  
- Experiments #9 lab-only data: [experiments.md](experiments.md)  
