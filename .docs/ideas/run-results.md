# Idea: Promote LimsRun JSONB data → Results

**Status:** Exploratory — outline for refinement (not implementation-ready)  
**Branch:** `run-results`  
**Date:** 2026-07-11

## One-liner

Let lab users **map selected columns** from **LimsRun instrument data** (`lims_run_data.row_data` JSONB) into formal **`results`** rows (parented by **tests** / analytes), when the assay is set up so that path is valid.

## Motivation

| World | What it is good for | Gap |
|-------|---------------------|-----|
| **LimsRun + `lims_run_data`** | Flexible instrument/CRO import; parser-mapped columns in JSONB; plate/well context | Not the LIMS “official result” ledger used for reporting, review, client-facing results |
| **`results` (+ `tests`)** | Structured, test/analyte-scoped outcomes (`raw_result`, `reported_result`, …); status/review culture of classic LIMS | Today often entered separately from run import |

Users already import rich tables into a run. They should not re-type the same numbers into Results when the assay (tests on samples) is already set up.

## Current model (grounding)

### LimsRun side

- **`lims_runs`** — run instance of an experiment template; lifecycle (draft → … → published).
- **`lims_run_data`** — one row per instrument reading / well (typical).
  - `row_data` **JSONB** — columns after `parser_config` mapping  
  - optional `sample_id`, `container_id`, `well_position`
- Distinct from **dose-response** results (`dose_response_results`) — analysis layer on runs, not classic `results`.

### Classic LIMS side

- **`tests`** — ordered work on a sample (analysis, status, …).
- **`results`** — child of test; requires `test_id`, `analyte_id`; holds raw/reported/calculated strings (+ optional JSONB `custom_attributes`).
- Manual / batch results entry UIs already exist.

### Bridge (weak today)

- `ExperimentSampleExecution.result_id` can point at a Result (ELN path).
- LimsRun data rows do **not** currently own a first-class “promoted to result_id” link.

## Sketch of the idea (v0)

```
LimsRun (has imported lims_run_data rows)
    │
    │  user selects column mapping (when assay/setup allows)
    │  e.g. row_data["concentration"] → Result.raw_result
    │       row_data["analyte_code"]  → resolve Analyte
    │       sample_id on row         → find/create Tests?
    ▼
results (parent test_id + analyte_id)
```

### Preconditions (“if the assay is set up”)

Rough product gate — refine later:

1. Run has data rows with `sample_id` (or resolvable sample).  
2. Sample has (or will have) **Tests** for the analyses that should receive results.  
3. Mapping is defined: JSONB keys → result fields and/or analytes.  
4. User has permission to enter/update results (lab roles — not lab-client config edit; align with Decision #9 for data capture).

### Who defines the mapping?

Open — candidates:

| Option | Description |
|--------|-------------|
| **A. Per template** | Experiment template (or parser_config / new `result_promotion_config`) stores default column → result field / analyte map |
| **B. Per run (user UI)** | On a run, user picks columns and targets, then “Promote” |
| **C. Both** | Template defaults + run-time override |

First instinct: **C** — setup once per assay (template), allow override at promote time.

## Design tensions to refine

### 1. Cardinality

- One `lims_run_data` row may be **one well / one reading**.  
- One `result` is typically **one analyte on one test**.  
- Mapping may be **1 row → many results** (multi-analyte panel in one import row) or **many rows → one result** (replicates / average).  
**Need a rule.**

### 2. What is “source of truth” after promote?

| Option | Meaning |
|--------|---------|
| Results copy (snapshot) | Run JSONB remains instrument SoT; results are a published slice |
| Results own reported value | Edits to results do not write back to run (likely default) |
| Bidirectional | High risk; avoid v1 |

Decision **#1g** for process/run boundary already leans: **LimsRun stays SoT for instrument data**. Promotion = copy/project into results, not replace the run.

### 3. When is promote allowed?

- Only after run `complete` / `published`?  
- From `running` / `results_received` (CRO)?  
- Re-promote = update existing results or create new versions?

### 4. Test creation

If sample has no test yet:

- Fail promote until tests exist?  
- Auto-create tests from sample’s ordered analyses / test battery?  
- Require explicit test selection in the promote UI?

### 5. Analyte resolution

How does a JSONB column become `analyte_id`?

- Column name matches analyte name/code  
- Explicit map: key `IC50` → analyte UUID  
- One column → one analyte always (simple assays)

### 6. Field mapping surface

Results today are mostly **scalar strings** (`raw_result`, `reported_result`, `calculated_result`) + qualifier list entry — not arbitrary columns.

So “select columns” likely means:

- Map **one** JSONB key → `raw_result` (and/or reported)  
- Optionally map another → qualifier / custom_attributes  
- Or map **multiple keys → multiple analytes** (multiple result rows)

Not “copy whole JSONB object into results” without a shape.

### 7. Relationship to dose-response

Dose-response already materializes structured analysis in `dose_response_results`.  
This idea is about **classic sample/test results**, not replacing DR. Clarify: promotion is for LIMS reporting results; DR stays separate analysis product.

### 8. Process / ELN

If a process step is `lims_run`, promotion might be a step-complete action. Out of scope for first cut unless we need it for journey UX.

## Possible UX (strawman)

1. Open LimsRun → Data tab.  
2. **Promote to results** (enabled when setup OK).  
3. Wizard:  
   - Confirm samples / tests coverage  
   - Mapping table: JSONB key → target (analyte + result field)  
   - Preview N result rows that would be created/updated  
4. Confirm → create/update results; show audit “promoted from run X”.

## Non-goals (v0 idea)

- Replacing free-form results entry  
- Auto-promote on every import without user action (unless product later wants “rules engine”)  
- Writing results back into `row_data`  
- Full EAV for results columns (unless FieldDefinitions for results is a later track)

## Fit with existing workstreams

| Workstream | Overlap |
|------------|---------|
| LimsRun / parsers | Source data + column names known after parse |
| Results / batches | Destination UX and permissions |
| FieldDefinitions | Future: richer result attributes; not required for scalar raw/reported |
| SOP RAG | Unrelated; assay “setup” might eventually be AI-assisted |
| Decision #1g | Instrument SoT remains run; promotion is explicit projection |

## Open questions (for outline refinement)

1. Template-level map vs run-level only vs both?  
2. Snapshot vs update-on-repromote?  
3. Required run status before promote?  
4. Auto-create missing tests?  
5. Multi-analyte from one row — required in v1?  
6. Permissions: same as result entry, or also need run publish?  
7. Audit / lineage: store `lims_run_id` + `lims_run_data_id` on result (new columns or custom_attributes)?  
8. Env lab vs CRO: same feature both lifecycles?  

## Suggested next step

1. Product pass on open questions (especially cardinality + test creation + SoT).  
2. Thin outline / requirements doc under `requirements/` or checklist.  
3. CEO / design / eng / security reviews when scope is stable.  
4. Spike: one template map + promote API dry-run preview.

---

**Author notes:** First-pass product instinct — instrument import stays flexible in JSONB; official reportable values live on Results; bridge is **user-driven (or template-default) column selection** when tests exist. Refine before committing to schema.
