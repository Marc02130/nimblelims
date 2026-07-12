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
lims_runs.analysis_id  UUID NULL REFERENCES analyses(id)
```

- UI: required for “reportable assay” runs; optional for pure instrument/DR-only runs.  
- Optional template default `default_analysis_id` copied onto new runs.

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
analytes.aliases  TEXT[]  -- or separate analyte_aliases(analyte_id, alias) UNIQUE(alias)
```

Unique alias globally (or per lab/client scope later) to avoid ambiguous resolution.

### 3.4 Result row shape (v1)

| Field | Source |
|-------|--------|
| `test_id` | Resolved from sample + analysis that includes analyte (open: how if multi-test) |
| `analyte_id` | Resolution above |
| `raw_result` | Stringify JSONB value |
| `reported_result` | null or copy raw (product) |
| `calculated_result` | null in v1 |
| `entered_by` | Publishing user |
| `entry_date` | now |
| `name` | Generated unique (existing BaseModel constraint) |
| Lineage | New nullable FKs preferred: `source_lims_run_id`, `source_lims_run_data_id` |

Do **not** dump unmapped JSONB into `custom_attributes` by default.  
Extra meta → **result custom fields** (Field Management already supports `results`).

### 3.5 Test resolution

With **`run.analysis_id`** fixed:

| Strategy | Behavior |
|----------|----------|
| **Find** | Existing test for `(sample_id, analysis_id)` |
| **Create** | If missing, create test for that sample + analysis (open **#7** — lean create for smoother publish) |
| **Fail** | If missing, block publish |

Analytes promoted should generally be members of that analysis (`analysis_analytes`); extras via explicit map only if product allows.

### 3.6 Cardinality

- One `(data_row, analyte)` → one result.  
- Multi-analyte columns on one JSONB object → many results.  
- Multiple data rows for same sample+analyte (replicates): **on_conflict** policy (last wins / fail / average later).

### 3.7 Idempotency / re-publish

Published runs are terminal today (no transition out of `published`). Re-promote only if:

- New API “re-promote published run”, or  
- Future unpublish  

v1 can assume **once** on first publish. If results already exist for source lineage, apply `on_conflict`.

### 3.8 API sketch

| Hook | Behavior |
|------|----------|
| Existing status transition to `published` | Call `ResultPromotionService.promote_run(run_id)` |
| `POST /v1/lims-runs/{id}/promotion/preview` | Dry-run without write (for UI modal) |
| Template CRUD | Include `promotion` config |

Permissions: publish permission + result create (lab only).

### 3.9 Relation to dose-response

`dose_response_results` unchanged. Promotion is classic LIMS results only. DR may later feed calculated fields—out of v1.

### 3.10 Implementation phases

| Phase | Deliverable |
|-------|-------------|
| **P0** | Analyte aliases model + admin API/UI |
| **P1** | `lims_runs.analysis_id` FK + UI selection list (+ optional template default) |
| **P2** | Template column map / auto-alias resolve + preview API |
| **P3** | Promote service + hook on publish when `analysis_id` set (transactional) |
| **P4** | Lineage FKs + result UI badge |
| **P5** | Optional map JSONB → result custom fields |

## 4. Testing

- Unit: key resolution (name, alias, map, conflict)  
- Integration: publish creates N results; RLS client isolation  
- Failure: missing test aborts publish; no half status  
- Idempotency: second promote respects on_conflict  

## 5. Risks

| Risk | Mitigation |
|------|------------|
| Global unique `results.name` | Robust name generator |
| Large runs (10k rows × analytes) | Batch inserts; timeout; async promote only if publish can wait |
| Alias collisions | Unique constraint + admin validation |

## 6. Recommendation

Implement **publish-gated, transactional promotion** with **analyte aliases** and **strict test prerequisite**. Preview API before publish for UX.

---

Related: [ceo](../ceo-review/run-results.md) · [design-review](../design-review/run-results.md) · [security](../security-review/run-results.md)
