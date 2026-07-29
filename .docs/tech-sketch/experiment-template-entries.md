# Tech sketch: Experiment template entries (table / form places)

**Date:** 2026-07-28 · **Reviewed:** 2026-07-29  
**Status:** **Revise — Hold implementation** (Lab Ops 2026-07-29). Tech reviews were premature for implement gate.  
**Requirements:** [`.docs/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md) §4.3 Entries — **needs entry catalog + workflow brief before code**  
**Open questions:** [`.docs/open-questions/experiments.md`](../open-questions/experiments.md) (Q11–Q16 partial; **Q17–Q22 open** block implement)  
**Schema changes:** [`.docs/schema-changes/experiment-template-entries.md`](../schema-changes/experiment-template-entries.md)  
**Reviews:** [Lab Ops](../lab-ops-review/experiment-template-entries.md) (**Hold**) · [CEO](../ceo-review/experiment-template-entries.md) · [UI](../ui-review/experiment-template-entries.md) · [Architecture](../architecture-review/experiment-template-entries.md) · [Security](../security-review/experiment-template-entries.md)  
**Reference:** [`manuals/Sapio Experiments Guide.pdf`](../../manuals/Sapio%20Experiments%20Guide.pdf)  
**Related manuals:** [experiments.md](../manuals/experiments.md), [processes.md](../manuals/processes.md)  
**Process:** [development-process/README.md](../development-process/README.md) — **lab ops gate required**

## 1. Problem (technical)

| Today | Gap |
|-------|-----|
| Template editor has Protocol Steps / Transfer Steps / Result Columns | **No Entries authoring UI** — cannot declare table/form places on a template |
| `template_definition.entries` is supported on instantiate | JSON-only; opaque to lab managers |
| `Entry` + `EntryFieldValue` + capture panel exist | Only useful if entries already exist (API or empty instantiate) |
| `sample_data` table shows sample **UUID prefix** | Not client_sample_id / biotype / chosen Sample metadata |
| `display_table` is a stub (“read-only”) | No column source model (Sample vs FieldDef vs static) |
| Protocol + Transfer are **two numbered step lists** | Confusing; not the same as instance runtime procedure/entries |
| Creating Experiment from template | Instantiates entries if declared; does **not** surface protocol/transfer as instance work |

**Product need (locked in conversation):**  
Template authors need **places to display and capture data** on experiment instances:

1. **Starting samples** — samples selected for the experiment, with **chosen metadata columns from Sample**  
2. **Sample manipulation** — per-sample editable table (`sample_data`, optional write-back)  
3. **Experiment details** — experiment-level form (`experiment_detail`)  
4. Optional later: predefined actions, generic display tables  

**Process context (unchanged):**  
Process steps still choose template + kind (ELN experiment \| LIMS run). This sketch is about the **interior** of an ELN experiment template: ordered entry blocks.

## 2. Goals / non-goals (technical)

**Goals**

- First-class **Entries** authoring on Experiment Template UI  
- Single ordered list of **entry blocks** on the template (not a second parallel “transfer steps” numbering system for capture)  
- Typed entry blocks with a clear contract in `template_definition.entries`  
- **Sample roster** display: rows = samples linked to the experiment; columns = selected Sample fields (OOB + FieldDefinition-backed)  
- **sample_data** / **experiment_detail** continue to use FieldDefinitions as columns  
- Instance UI shows real sample labels/metadata; instantiate path remains the source of entry shells  
- Align labels: template = recipe; experiment = instance of recipe  

**Non-goals (this cycle)**

- Merging ELN Experiment and LimsRun models  
- Full predefined_action execution (aliquot/pool engines)  
- Process-level override of entry config (already **Decided provisional Q3**: no)  
- Stricter write-back than last-write-wins allowlist (Q4)  
- Replacing process step model or plate handoff to LIMS runs  
- Multi-tenant org segregation  
- Auto-promote LimsRun data into Entries  
- Fully redesigning SOP AI extraction of protocol/transfer (can stay for sign-off/worklist until procedure merge is a later phase)

### 2b. ELN building blocks (product refine 2026-07-29)

**Core idea:** An experiment is composed of **ordered entries**. Two building-block types carry **custom columns** and **population rules**. These replace the mental model of loose “protocol / transfer steps.”

| Building block | API `entry_type` | UI label | What it is |
|----------------|------------------|----------|------------|
| **Sample table** | `sample_table` | Sample table | One **row per sample** in scope; **columns chosen per entry** (custom FieldDefinitions + optional Sample fields) |
| **Experiment table** | `experiment_table` | Experiment table | **Experiment-scoped** fields/rows; **columns chosen per entry** (custom FieldDefinitions) |

**Do not call them `sample_detail` / `experiment_detail` in product UI.**  
Legacy code/API names `sample_data` / `experiment_detail` map to these; P0 renames to `sample_table` / `experiment_table` (aliases during transition OK — no prod users).

**What already exists (storage):**

| Layer | Exists? | Role |
|-------|---------|------|
| `entries` | Yes | Block instance on an experiment |
| `entry_field_definitions` | Yes | Which columns (FieldDefinitions) hang on this entry |
| `entry_field_values` | Yes | Cell values (`sample_id` set for sample tables) |
| Column picker on **template** UI | **No** | Authoring gap |
| **Population rules** (how rows appear) | **No** | Product gap — e.g. aliquot plan filled from samples on the experiment |

So: **tables for values exist**; **authoring + population config** are what we build. Naming shifts to match the product.

#### Columns (per entry)

On each entry declaration, the author **selects which columns to display** for that block:

| Column kind | Sample table | Experiment table |
|-------------|--------------|------------------|
| **Custom** (FieldDefinition) | Yes — primary | Yes — primary |
| **Sample system fields** (OOB / Path-1 allowlist) | Yes — often read-only display (client id, biotype, …) | No |
| Write-back to Sample | Optional per custom column | No |

Same Field Management catalog as the rest of the app (list-backed, scalars, validation).

#### Population (how the entry is filled with data)

Declared in `config` on the entry. **Population is first-class**, not implied magic.

| `config.row_source` | Meaning | Typical use |
|---------------------|---------|-------------|
| **`experiment_samples`** | One row per sample linked to the experiment (`ExperimentSampleExecution`) | Aliquot **plan**, results, starting sample metadata |
| **`empty`** | No rows until user/API adds (future) | Ad hoc capture |
| **`none`** | Experiment table: single form (no sample rows) | Conditions, kit lot, notes |

**Aliquot plan example (correct product shape):**

```
Entry 1  sample_table  "Aliquot plan"
           row_source: experiment_samples
           columns: [client_sample_id (sample field), dest_well, volume_ul, … custom]
           → when samples are brought into the experiment, plan rows appear

Entry 2  sample_table  "Aliquot results"
           row_source: experiment_samples
           columns: [measured_volume, recovery_pct, pass_fail, …]

Entry 3  experiment_table  "Run conditions"
           row_source: none
           columns: [operator, kit_lot, start_time]
```

Transfer/aliquot is **not** a separate Transfer Steps system. It is a **sample table** populated from experiment samples, with plan columns. Results are another sample table (or the same samples, different columns).

#### Legacy surfaces

| Surface | Status |
|---------|--------|
| Transfer Steps tab | Transitional (sign-off / SOP extract only) |
| Protocol Steps | Optional free-text until folded into entry descriptions |
| `robot_worklist_configs` | Keep for robot CSV export |
| Old types `sample_data` / `experiment_detail` | Map → `sample_table` / `experiment_table` |

**Dev:** No production users. Prefer correct names and population rules. Keep working: template CRUD, sign-off, SOP apply, experiment create, entry capture, process start, worklist export while renaming.

See **Decision #15 / #16** in open-questions.

## 3. Component diagram

```
┌─────────────────────────────────────────────────────────────┐
│ ExperimentTemplate                                          │
│  template_definition.entries[]                              │
│    { entry_type, name, columns[], config.row_source }       │
└────────────────────────────┬────────────────────────────────┘
                             │ create experiment / start process step
                             │ instantiate + apply row_source
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Experiment                                                  │
│  sample_executions[]  ──► rows for sample_table             │
│  entries[]            ──► sample_table | experiment_table   │
└────────────────────────────┬────────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
   sample_table                          experiment_table
   rows ← row_source                     columns ← FieldDefs
   columns ← FieldDefs + sample fields   row_source: none (form)
```

## 4. Entry types (contract)

### 4.1 Building blocks (P0)

| `entry_type` | Rows | Columns | Writable cells |
|--------------|------|---------|----------------|
| **`sample_table`** | From `config.row_source` (default `experiment_samples`) | Per-entry selection: custom FieldDefs + optional Sample system fields | Custom columns yes; Sample system fields usually display-only; optional write-back on custom |
| **`experiment_table`** | None (single form) unless multi-row later | Per-entry FieldDefs | Yes |

| Legacy type (code today) | Maps to |
|--------------------------|---------|
| `sample_data` | `sample_table` |
| `experiment_detail` | `experiment_table` |
| `sample_roster` (sketch earlier) | **`sample_table`** with only Sample system columns + read-only |
| `display_table` | Defer / rare; prefer sample_table or experiment_table read-only flag |
| `predefined_action` | Later phase |

### 4.2 Declaration JSON (`template_definition.entries[]`)

```json
{
  "entries": [
    {
      "name": "Aliquot plan",
      "entry_type": "sample_table",
      "sort_order": 0,
      "config": {
        "row_source": "experiment_samples"
      },
      "columns": [
        {
          "kind": "sample_field",
          "key": "client_sample_id",
          "sort_order": 0,
          "visible": true,
          "editable": false
        },
        {
          "kind": "field_definition",
          "field_definition_id": "…",
          "sort_order": 1,
          "visible": true,
          "editable": true,
          "write_back_target": null
        },
        {
          "kind": "field_definition",
          "field_definition_id": "…",
          "sort_order": 2,
          "visible": true,
          "editable": true
        }
      ]
    },
    {
      "name": "Aliquot results",
      "entry_type": "sample_table",
      "sort_order": 1,
      "config": { "row_source": "experiment_samples" },
      "columns": [
        { "kind": "sample_field", "key": "client_sample_id", "sort_order": 0, "editable": false },
        { "kind": "field_definition", "field_definition_id": "…", "sort_order": 1, "editable": true }
      ]
    },
    {
      "name": "Experiment conditions",
      "entry_type": "experiment_table",
      "sort_order": 2,
      "config": { "row_source": "none" },
      "columns": [
        { "kind": "field_definition", "field_definition_id": "…", "sort_order": 0, "editable": true }
      ]
    }
  ]
}
```

**Backward-compatible accept:** still accept legacy `fields[]` + `entry_type: sample_data|experiment_detail` and normalize to `columns` + new types on save.

### 4.3 Sample system field keys (`kind: sample_field`)

Server allowlist (fail closed), same as prior roster list:

| Key kind | Examples |
|----------|----------|
| OOB scalar | `client_sample_id`, `received_date`, `due_date`, `temperature`, `date_sampled` |
| OOB list FK | `status`, `sample_type`, `matrix`, `qc_type`, `specimen_biotype_id` |
| Path-1 sample columns | FieldDefinition-backed sample columns when present |

Display: resolve list FKs to list entry **names**.

### 4.4 Custom columns (`kind: field_definition`)

| Field | Required | Notes |
|-------|----------|-------|
| `field_definition_id` | Yes | Active FieldDefinition |
| `sort_order` | No | Default array index |
| `visible` | No | Default true |
| `editable` | No | Default true for field_definition; false for sample_field |
| `write_back_target` | No | `sample_table` only; must be in `SAMPLE_WRITE_BACK_COLUMNS` |

### 4.5 Population runtime

When `row_source = experiment_samples`:

1. Load sample ids from `experiment_sample_executions` for the experiment  
2. Render one grid row per sample (stable order: execution created_at / sample id)  
3. Load `entry_field_values` for those samples; empty cells until edited  
4. Sample system columns projected from Sample (not stored as entry values unless write-back)

When samples are **added later** to the experiment, sample tables re-query executions — new rows appear (no re-instantiate of entry shell required).

When `row_source = none` (experiment_table): render a form of editable FieldDefinition columns; values have `sample_id = null`.

### 4.6 Instantiate behavior

`EntryService.instantiate_from_template`:

1. Read `template_definition.entries` (normalize legacy types/fields)  
2. Create `Entry` shells: type, name, sort_order, config (incl. `row_source`)  
3. Link FieldDefinitions for `kind: field_definition` columns  
4. Store sample_field column keys in `entry.config.columns` (or equivalent)  
5. **Do not** pre-create empty value rows for every sample (lazy on first save is fine); grid still shows rows from `row_source`  

**Idempotency:** keep `skip_if_exists`.

## 5. Runtime flows

### 5.1 Author template entries

```
Template UI → Tables & forms
  → Add entry: Sample table | Experiment table
  → Sample table:
       row_source (default experiment_samples)
       column picker: Sample system fields + FieldDefinitions
  → Experiment table:
       column picker: FieldDefinitions only
  → Reorder → Save
```

Permission: `experiment:manage`.

### 5.2 Create experiment / start process step

```
create_experiment / process start (eln_experiment)
  → Experiment
  → instantiate entry shells from template
  → link samples (executions) — when present, sample_table rows appear via row_source
```

### 5.3 Lab works instance

```
Experiment → Tables & forms
  sample_table + experiment_samples:
    rows = linked samples
    sample_field columns projected; field_definition columns editable
  experiment_table:
    form / single-row fields
  Save → upsert entry values (+ write-back if configured)
```

### 5.4 Sample labels

Prefer including `client_sample_id` as a sample_field column; else short id + tooltip UUID.

## 6. API surface

| Area | Change |
|------|--------|
| Template CRUD | Validate `entries[]` (types, columns, row_source, allowlists) |
| Instantiate / list entries | New types; normalize legacy |
| `GET /v1/entries/{id}/grid` (or `/table`) | Unified read for sample_table: columns meta + rows with cells (sample projections + stored values) |
| `PUT …/values` | Unchanged shape; reject non-editable columns; reject experiment_table sample_id |

**Prefer one grid endpoint** over separate “roster” vs “capture” APIs: same table, mixed column kinds.

### 6.1 Grid read contract

`GET /v1/entries/{entry_id}/grid`

```json
{
  "entry_type": "sample_table",
  "row_source": "experiment_samples",
  "columns": [
    { "key": "client_sample_id", "kind": "sample_field", "label": "Client Sample ID", "editable": false, "data_type": "text" },
    { "key": "<field_def_id>", "kind": "field_definition", "label": "Dest well", "editable": true, "data_type": "text" }
  ],
  "rows": [
    {
      "sample_id": "…",
      "cells": {
        "client_sample_id": { "display": "S-001", "value": "S-001" },
        "<field_def_id>": { "display": "B1", "value": "B1" }
      }
    }
  ]
}
```

Server owns allowlist, list name resolution, RLS.

## 7. UI sketch

### 7.1 Template editor — **Tables & forms** tab

1. Basic Info  
2. **Tables & forms** (primary)  
3. Protocol Steps (demoted; optional)  
4. Transfer Steps (demoted / hide when entries present)  
5. Result Columns (run-oriented; secondary)

Author UX:

- Cards: name, **Sample table** | **Experiment table**, column summary, row_source chip  
- Add → type → column multi-select (Sample fields + FieldDefs for sample tables)  
- Empty: “Add sample and experiment tables that appear when this template is run.”

### 7.2 Experiment instance

| Type | Render |
|------|--------|
| `sample_table` | Data grid from `/grid`; empty state if no samples and row_source=experiment_samples |
| `experiment_table` | Form from columns |

Empty states: no entries on template; no samples for sample_table; no columns configured.

## 8. Data model / migrations

See [schema-changes/experiment-template-entries.md](../schema-changes/experiment-template-entries.md).

**Summary:** P0 is **mostly contract + UI + API validation**. `entries.config` JSONB already exists. New type string `sample_roster` in app allowlist. Optional later: first-class template entry tables if JSONB becomes painful (not P0).

## 9. Permissions & security

| Action | Who |
|--------|-----|
| Author template entries | `experiment:manage` (lab) |
| Edit entry values | Lab only — Decision #9 |
| View roster / values | Same as experiment visibility (RLS) |
| Clients | No entry edit; no template manage |

**Write-back:** unchanged allowlist + last-write-wins (Q4). Roster is display-only — no write path.

**PII:** Sample metadata on roster follows sample RLS; no new cross-client projection.

## 10. Phase mapping

| Phase | Scope | Exit criteria |
|-------|--------|----------------|
| **P0** | Types `sample_table` / `experiment_table`; per-entry **column picker** (custom + sample fields); **`row_source`** (at least `experiment_samples` / `none`); template Tables & forms tab; instance grid API + UI; validate on template write; docs | Author aliquot plan + results + conditions → create experiment → link samples → plan rows populate → edit/save |
| **P1** | Richer sample fields; hide Transfer tab when entries present; SOP maps into entries; seed example template | Dogfood prep SOP |
| **P2** | Multi-row experiment_table if needed; predefined_action; drop legacy types/tabs | — |

**Explicitly not P0:** hard-delete Transfer tab day one; process auto-link samples (Q8).

## 11. Compatibility

| Existing data | Behavior |
|---------------|----------|
| Templates without `entries` | Unchanged; instantiate no-ops |
| Templates with existing entries JSON | Continue to work; new validation must accept current field shape |
| Experiments with entry rows | Unchanged capture |
| Transfer/protocol JSON | Unchanged |

## 12. Testing

| Layer | Cases |
|-------|-------|
| Unit / schema | Accept sample_table/experiment_table + columns; reject bad types/keys |
| Service | Instantiate links field columns; grid rows from experiment_samples |
| API | Grid projection + values; 403 without manage; RLS |
| Frontend | Tables & forms save round-trip; empty then populated after link samples |
| UAT | Aliquot plan + results + conditions path |

## 13. Open technical / product questions

Logged in [open-questions/experiments.md](../open-questions/experiments.md):

| # | Status | Decision (2026-07-29) |
|---|--------|------------------------|
| **Q11** | **Decided** (refined) | Entries = runtime; transfer plan = sample table, not Transfer Steps tab |
| **Q12** | **Superseded** | Roster is sample_table + sample_field columns, not separate type |
| **Q13** | **Decided** | Server Sample field allowlist for `kind: sample_field` |
| **Q14** | **Decided** | No forced sample picker; empty sample_table until samples linked |
| **Q15** | **Decided** | Plan = sample_table (row_source=experiment_samples); results = another sample_table |
| **Q16** | **Decided** | Product names **Sample table** / **Experiment table** (`sample_table` / `experiment_table`); not sample_detail / experiment_detail |

Related still open: **Q8** (auto sample executions from process).

## 14. Review outcomes (2026-07-29)

| Review | Verdict |
|--------|---------|
| **CEO** | Accept with conditions C1–C4 |
| **UI** | Accept with conditions U1–U6 |
| **Architecture** | Accept with conditions A1–A7 |
| **Security** | Accept with conditions S1–S6 |

### Implementation must-haves (refined after building-block lock)

| ID | Condition |
|----|-----------|
| B1 | Types **`sample_table`** / **`experiment_table`** (alias legacy sample_data / experiment_detail) |
| B2 | Per-entry **columns[]**: custom FieldDefs + sample_field allowlist |
| B3 | **`row_source`**: at least `experiment_samples` and `none` |
| B4 | `GET /entries/{id}/grid` — server projection + values; sample rows only from experiment executions |
| B5 | Validate entries on template write (fail closed) |
| B6 | Upsert only editable field_definition cells |
| B7 | Template **Tables & forms** authoring + instance capture |
| B8 | Exit demo: aliquot plan + results + conditions |
| B9 | experiment:manage + RLS isolation tests |
| B10 | Entry shell snapshot at instantiate; sample rows dynamic from executions |

Prior review IDs A*/U*/S*/C* still apply in spirit; B1–B10 are the implement checklist.

## 15. Implementation notes

| Area | Files (indicative) |
|------|---------------------|
| Types | `backend/models/entry.py` (`ENTRY_TYPES`) |
| Instantiate + grid + upsert | `entry_service.py` |
| Template validation | `app/schemas/template_entries.py` |
| API | `routers/entries.py` |
| Template UI | `ExperimentTemplatesManagement.tsx` |
| Capture UI | `EntryCapturePanel.tsx` |
| Manuals | `experiments.md` |

**Gate:** **CLOSED for implementation.** Lab Ops **Revise/Hold** (2026-07-29). Complete entry catalog + 2–3 SOP workflow briefs + Q17–Q22 before re-open. Generic `sample_table` / `experiment_table` remain a **substrate**, not the full lab product.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| **Lab Ops (SVP)** | lab workflow | Customer lab fit | 1 | **HOLD** | Catalog, aliquot derivatives, plates, materials, submit/lock, Q8 |
| CEO Review | plan review | Scope & product | 1 | SUPERSEDED for gate | Tech Accept only; not sufficient alone |
| UI / Design | plan review | UX | 1 | SUPERSEDED for gate | Tables & forms OK as UI for substrate |
| Eng / Architecture | plan review | Architecture | 1 | SUPERSEDED for gate | Engine OK; product incomplete |
| Security | plan review | Threat model | 1 | SUPERSEDED for gate | Stand when design re-locks |

**VERDICT:** **NOT CLEARED** — Lab Ops Hold. Do not implement Phase 4 until Lab Ops Accept (or Accept with conditions) after requirements revise.
