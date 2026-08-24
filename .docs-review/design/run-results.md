# Tech Review: LimsRun → Results (structured promotion)

**Date:** 2026-07-11  
**Branch:** `run-results`  
**Reviewer:** Engineering / Architecture  
**Status:** Design — open questions remaining for test creation / re-promote  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)

## 1. Problem

| Store | Shape | Use |
|-------|--------|-----|
| `lims_run_data.row_data` | Flexible JSONB columns | Instrument/CRO import |
| `results` | Relational: `test_id`, `analyte_id`, `raw_result`, … | Query, report, review |

**Goal:** On **run publish**, project mapped JSONB values into structured `results` for easy querying/reporting.

**Locked:**
- Write path when status transitions to **`published`**.
- **Opt-in:** only if `lims_runs.analysis_id` is set (FK → `analyses`). No analysis → publish without promote.

## 2. Current building blocks

- **LimsRun** lifecycle: standard vs CRO (`lifecycle_type`); import in `running` \| `results_received`.  
- **Publish:** `complete → published` requires `experiment:publish`.  
- **Results API:** create/update with `result:enter` (and related); supports custom fields on results entity.  
- **Analytes:** `name`, optional `custom_attributes`; **no first-class aliases yet**.  
- **Tests:** sample + analysis; results require existing `test_id`.

## 3. Target design

### 3.1 Promote-on-publish pipeline

```
transition_status(run, published)
    │
    ├─ if run.analysis_id is NULL:
    │     set status = published; return   # no promote
    │
    ├─ validate promotion readiness
    │     • analysis_id set (opt-in)
    │     • each data row sample_id present (or skip policy)
    │     • test for (sample, analysis): exist or create (open #7)
    │     • columns resolve to analytes (name | alias | map)
    │     • prefer analytes on analysis_analytes for that analysis
    │
    ├─ if invalid → abort status change (transaction)
    │
    ├─ set status = published (+ published_at)
    │
    └─ promote:
          for each lims_run_data row:
            test = find_or_create(sample_id, run.analysis_id)
            for each mapped JSONB key with value:
              resolve analyte_id
              upsert Result(test_id, analyte_id, raw_result=value, …)
              set lineage (lims_run_id, lims_run_data_id)
```

**Atomicity:** Prefer single DB transaction: status + all result writes. Partial promote after published is worse.

### 3.1b Schema: analysis on run

```
lims_runs.analysis_id  UUID NOT NULL REFERENCES analyses(id)   -- target; was nullable in first ship
```

- UI: **required** analysis on every run (no non-reportable / “none” option).  
- Optional template default `default_analysis_id` copied onto new runs.  
- **Missing analysis:** block create / start / import / publish — no `acknowledge_no_analysis` path (product lock 2026-07-19).

### 3.2 Mapping model

```json
{
  "promotion": {
    "enabled": true,
    "mode": "auto_analyte_or_alias" | "explicit_map",
    "column_map": {
      "Pb_ug_L": { "analyte_id": "uuid" },
      "Lead": { "analyte_id": "uuid" }
    },
    "skip_keys": ["units", "well", "sample_name"],
    "on_conflict": "update_raw" | "skip_if_exists" | "fail"
  }
}
```

Storage options:

- On **experiment template** (`template_definition` or dedicated JSONB/column)  
- Optional run-level override  

**Resolution order for a key:**

1. Explicit `column_map`  
2. Exact analyte `name` (casefold/normalize)  
3. Analyte **alias** list  
4. Else skip or fail (config)

### 3.3 Analyte aliases (schema sketch)

```
analyte_aliases (
  id, analyte_id FK,
  alias TEXT,  -- e.g. 'EtOH', 'C2H5OH'
  UNIQUE (lower(alias))  -- or unique per lab later
)
```

Or `analytes.aliases TEXT[]` with app-level uniqueness checks.

**Matching:** normalize (trim + casefold) then **exact membership** in the maintained list—not fuzzy/chemical AI in v1.  
AI-assisted resolution when list misses: [ideas/ai-analyte-resolution.md](../ideas/ai-analyte-resolution.md).

### 3.4 Result row shape (v1)

| Field | Source |
|-------|--------|
| `test_id` | Resolved from sample + analysis that includes analyte (open: how if multi-test) |
| `analyte_id` | Resolution above |
| `raw_result` | Stringify JSONB value |
| `reported_result` | null or copy raw (product) |
| `calculated_result` | null in v1 |
| `replicate` | **INT** (default 1) — distinguishes multi-row same analyte |
| `lims_run_id` | **FK** → promoting run (null if manually entered) |
| `entered_by` | Publishing user |
| `entry_date` | now |
| ~~`name`~~ | **Removed** (Decision #17) — not a named entity |

Do **not** dump unmapped JSONB into `custom_attributes` by default.  
Extra meta → **result custom fields** (Field Management already supports `results`).

### 3.5 Test resolution (Decided #7)

**Analysis / analyte = objects; test / result = instances.**

With **`run.analysis_id`** set:

1. **Find** test for `(sample_id, analysis_id)`, or  
2. **Create** test instance for that sample + analysis  

No “missing test” error when analysis is defined. Fail only if sample_id missing or analyte unresolved.

Analytes promoted should generally be members of that analysis (`analysis_analytes`); resolve columns via name + **analyte aliases**.

### 3.6 Cardinality + replicate

- One `(data_row, analyte)` → one result with a **`replicate`** int.  
- Multi-analyte columns on one JSONB object → many results.  
- Multiple data rows for same sample+analyte → multiple results with distinct **`replicate`**.  
  - If import/JSONB has replicate → use it.  
  - Else **`replicate = 1..n` by row order** among those rows (Decided #15).

### 3.7 Idempotency / conflicts (Decided #8)

| Case | Behavior |
|------|----------|
| Result already exists with **same `lims_run_id`** (this run re-published / data fixed) | **Update** `raw_result` (and related fields) |
| Result exists for same test+analyte+replicate but **other / null `lims_run_id`** (second run or manual) | **Fail promote** and **notify** — do not overwrite |

Conflict identity: roughly `(test_id, analyte_id, replicate)` + ownership check via `lims_run_id`.

### 3.8 API sketch

| Hook | Behavior |
|------|----------|
| Existing status transition to `published` | Call `ResultPromotionService.promote_run(run_id)` |
| `POST /v1/lims-runs/{id}/promotion/preview` | Dry-run without write (for UI modal) — see §3.11 |
| Template CRUD | Include `promotion` config |
| Admin Lims Runs settings | `promote_batch_size` (default **200**) |

### 3.11 Preview and errors (UX/API)

**Preview = “what would happen on publish”** for structured promote (dry-run, **no DB writes**).

Shown on the **Publish** confirmation when `analysis_id` is set (and available as API for tooling):

| Preview shows | Meaning |
|---------------|---------|
| Results **to create** | New rows: sample, analyte, raw value, replicate, matched how (name/alias) |
| Results **to update** | Same run already owns this test/analyte/replicate — will update raw |
| **Conflicts** | Another run (or manual result) owns that slot — publish would **fail** until resolved |
| Columns **skipped** | Not analytes (e.g. `units`) |
| Columns **unresolved** | No name/alias match — fix list or AI later |
| Analysis analytes **missing from file** | Expected on assay, no column in import |
| **Counts** | e.g. create 128 / update 12 / conflict 0 / unresolved 3 |

**Errors** = hard failures that **block publish** when analysis is set (preview shows them before user confirms):

- Conflicts with another run’s results  
- Missing `sample_id` on data rows  
- Fail-closed unresolved columns (if configured)  
- Zero promotable data with analysis set (optional policy)

**Warnings** = non-blocking (e.g. optional skipped columns). Missing analysis is an **error**, not a warning.

**Schema:** Drop **`results.name`** (Decision #17)—no synthetic name generation.

Permissions: **publish alone** is enough to create/update tests/results on this path (Decided #10).

### 3.9 Relation to dose-response

`dose_response_results` unchanged. Promotion is classic LIMS results only. DR may later feed calculated fields—out of v1.

### 3.10 Implementation phases

| Phase | Deliverable |
|-------|-------------|
| **P0** | Analyte aliases on analyte + admin UI |
| **P1** | `lims_runs.analysis_id` + UI + start-run warning |
| **P2** | `results.lims_run_id`, `results.replicate`; **drop `results.name`** (and unique) |
| **P3** | Promote service: ensure test, resolve analyte, update-vs-fail, publish hook |
| **P4** | Preview + conflict notification UX |
| **P5** | Optional map JSONB → result custom fields |

## 4. Testing

- Unit: key resolution (name, alias, map, conflict)  
- Integration: publish creates N results; RLS client isolation  
- Failure: missing test aborts publish; no half status  
- Idempotency: second promote respects on_conflict  

## 5. Risks

| Risk | Mitigation |
|------|------------|
| ~~Global unique `results.name`~~ | **Dropped** (Decision #17 / P2) |
| Large runs (10k rows × analytes) | Batch inserts; **admin-configurable batch size, default 200**; timeout; prefer sync transactional publish |
| Alias collisions | Unique constraint + admin validation |

## 6. Recommendation

Implement **publish-gated, transactional promotion** with **analyte aliases** and **strict test prerequisite**. Preview API before publish for UX.

---

Related: [ceo](../ceo-review/run-results.md) · [ui-review](../ui-review/run-results.md) · [security](../security-review/run-results.md)
