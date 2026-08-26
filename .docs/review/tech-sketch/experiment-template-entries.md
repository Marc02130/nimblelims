# Tech sketch: Experiment template entries (table / form places)

**Date:** 2026-07-28 · **Updated:** 2026-08-10  
**Status:** **Accepted with conditions** (2026-08-10) — Lab Ops L1–L9 (all aliquot methods); CEO/UI/Arch/Security Accept; **implement gate open**  
**Requirements:** [`.docs-review/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md) §4.3 Entries  
**Open questions:** [`.docs-review/open-questions/experiments.md`](../open-questions/experiments.md) (Decision #23 + session locks below)  
**Schema changes:** [`.docs-review/schema-changes/experiment-template-entries.md`](../schema-changes/experiment-template-entries.md)  
**Reviews:** [Lab Ops](../lab-ops-review/experiment-template-entries.md) · [CEO](../ceo-review/experiment-template-entries.md) · [UI](../ui-review/experiment-template-entries.md) · [Architecture](../architecture-review/experiment-template-entries.md) · [Security](../security-review/experiment-template-entries.md)  
**Ideas (OOS):** local `.docs-internal/ideas/accessioning-and-workflows-revisit.md` (not committed) · local `.docs-internal/ideas/materials-and-lot-tracking.md` (not committed) · local `.docs-internal/ideas/index-sets-and-sequencing-setup.md` (not committed)  
**Reference:** Sapio Experiments Guide (external reference; PDF is not present in this repository snapshot)
**Related manuals:** [experiments.md](../manuals/experiments.md), [processes.md](../manuals/processes.md), [lims-runs.md](../manuals/lims-runs.md)  
**Process:** Lab Ops first, then other reviews ([lab-ops-review/README.md](../lab-ops-review/README.md))

---

## 0. LOCKED FOUNDATION (product decisions through 2026-08-10)

> **Do not reopen without product decision.**  
> This section is the authoritative lock from Q&A sets A–H.  
> Sketch scope = **two base kinds + columns/population + v1 predefined wrappers + template UI** — not full Sapio catalog.

**Coherence fold (2026-08-24):** §0 is the current source of truth. Later `sample_table` / `experiment_table` examples are historical substrate language, not API kinds and not the aliquot/pool design. The current mint proof is the atomic `aliquot_pool_plan` + `aliquots_pools` wrapper pair in [configurable-entries-framework.md](configurable-entries-framework.md) and [extract-hold-dest-type.md](extract-hold-dest-type.md).

### 0.1 Two entry kinds (product names)

| Kind | Meaning | Rows |
|------|---------|------|
| **`experiment_sample_data`** | Sample-oriented capture/display for one purpose on the experiment | **Table**: one row per sample in the experiment cohort. Many such entries per experiment, each with its own columns. |
| **`experiment_data`** | Purpose-specific experiment **tables** (plans, **Experiment Header**, operation lines) | **Table only — no form layout.** Multi-row free rows (`row_key`); user adds rows. Optional `sample_id` for purpose subsets is secondary to free multi-row. |

Legacy API strings `sample_data` / `experiment_detail` **alias →** these names on read/write normalization.

**Multiplicity:** One experiment can have **many** entries of each kind.  
**Experiment Header** = `experiment_data` + `predefined_entry_key = experiment_header` (not a separate kind).

**LIMS Runs:** Own **instrument** file → results → promote. **No** ELN instrument entry. **Analysis required** on every LIMS Run.

### 0.1b Start cohort (queue) — not per entry

**Full rules:** [open-questions Decision #24](../open-questions/experiments.md) (2026-08-12).

| Rule | Detail |
|------|--------|
| When | **Start of experiment** or **start of LIMS run** only — not on individual entries |
| Eligibility | **`Sample.status` = Available for Testing**; if under process → sample on **`eln_process_samples`** (not removed). Server-enforced. |
| UI (product target) | **Start dialog only** (process accordion click): dual list Available ↔ Selected; then dialog **gone**. **Not** a permanent panel on experiment detail. Scan optional. |
| UI (current) | Ephemeral `StartExperimentDialog` from process/ad hoc Start; permanent add-samples panel removed |
| On start | Process samples selected → `in_progress` + `current_step_id` = this step |
| After start | Cohort **fixed**; experiment detail has **no** add-samples control |
| Process auto-link | **No** — explicit select only |
| Inside experiment | Selected samples on `experiment_sample_data` entries |

### 0.2 Storage (not “one JSON blob”)

| Layer | Table / mechanism |
|-------|-------------------|
| Entry shell | `entries` (`entry_type`, name, `config` JSONB for layout/population hints only) |
| Columns | `entry_field_definitions` → `field_definitions` with `entity_type` ∈ {`experiment_sample_data`, `experiment_data`}, **not** Custom Fields on Sample/Test |
| Cells | `entry_field_values` **typed columns** + **`row_key`** for multi-row experiment_data (migration `0057`) |
| Sample key | `sample_id` for experiment_sample_data; `row_key` for free experiment_data rows |

**No new physical tables** named `experiment_sample_data` / `experiment_data` — those are **entry types** (logical).  
**Custom Fields** admin = DB entities only. Entry columns: template **Create field** / Add existing (`is_materialized_column = false`).

### 0.3 Grid read contract (UI — wide rows)

**Endpoint (canonical):**

```http
GET /v1/entries/{entry_id}/grid
```

**Auth:** same as entry read (today `experiment:manage`; refine with Decision #9 later).  
**RLS:** samples only if visible; no cross-client leakage.

**Response schema (locked shape):**

```json
{
  "entry_id": "uuid",
  "experiment_id": "uuid",
  "entry_type": "experiment_sample_data",
  "name": "Prep measurements",
  "columns": [
    {
      "key": "client_sample_id",
      "kind": "sample_field",
      "field_definition_id": null,
      "label": "Client Sample ID",
      "data_type": "text",
      "editable": false,
      "sort_order": 0
    },
    {
      "key": "<field_definition_uuid>",
      "kind": "field_definition",
      "field_definition_id": "<uuid>",
      "label": "Concentration",
      "data_type": "number",
      "editable": true,
      "sort_order": 1,
      "write_back_target": null
    }
  ],
  "rows": [
    {
      "row_id": "optional-stable-id",
      "sample_id": "uuid",
      "cells": {
        "client_sample_id": {
          "value": "S-001",
          "display": "S-001",
          "value_type": "text"
        },
        "<field_definition_uuid>": {
          "value": 12.5,
          "display": "12.5",
          "value_type": "number",
          "value_id": "uuid-of-entry_field_value-if-exists"
        }
      }
    }
  ],
  "row_count": 1,
  "meta": {
    "row_policy": "experiment_samples",
    "empty_reason": null
  }
}
```

| Rule | Detail |
|------|--------|
| **experiment_sample_data rows** | Exactly the samples **in** the experiment (selected at start). Order: link/`created_at`, then `sample_id`. **No** mid-experiment sample adds in v1. |
| **experiment_data rows** | Only rows created by user/code; **not** auto-filled from full sample list. `sample_id` optional per row. |
| **cells** | Keyed by column `key` (sample_field key or field_definition_id string). Missing → omit or null. |
| **display** | Server resolves list FKs to list entry **names**. |
| **empty_reason** | e.g. `no_samples_on_experiment` when kind is experiment_sample_data and none selected. |

**Write path (cell model):**

```http
PUT /v1/entries/{entry_id}/values   # Save — entry values only; no Sample write-back
POST /v1/entries/{entry_id}/submit  # Submit — mark complete; apply write-back maps; may unlock next entry
```

Body for values: list of `{ field_definition_id, sample_id?, value_* }`. Reject writes to non-editable `sample_field` columns.

### 0.4 Export / report list contract (stable, long-form)

For reporting, BI, and stable integrations — **long (normalized) rows**, not wide pivot. Survives column set changes without breaking column positions.

**Endpoint (canonical):**

```http
GET /v1/entries/{entry_id}/export
GET /v1/experiments/{experiment_id}/entries/export   # optional: all entries on experiment
```

Query params (v1):

| Param | Default | Notes |
|-------|---------|--------|
| `format` | `json` | `json` \| `csv` |
| `include_inactive_fields` | `false` | If true, include columns no longer on entry |
| `sample_id` | — | Optional filter |

**JSON item shape (one object per cell — locked):**

```json
{
  "experiment_id": "uuid",
  "experiment_name": "string",
  "entry_id": "uuid",
  "entry_name": "string",
  "entry_type": "experiment_sample_data",
  "sample_id": "uuid | null",
  "client_sample_id": "string | null",
  "field_definition_id": "uuid | null",
  "field_name": "string",
  "field_display_name": "string",
  "column_kind": "field_definition | sample_field",
  "data_type": "text | number | list | date | boolean | json",
  "value_text": null,
  "value_number": 12.5,
  "value_list_entry_id": null,
  "value_list_entry_name": null,
  "value_date": null,
  "value_boolean": null,
  "value_json": null,
  "display_value": "12.5",
  "modified_at": "iso-8601",
  "modified_by": "uuid | null"
}
```

**CSV:** same fields as header row; one line per cell. UTF-8. Stable column order as table above.

**experiment_sample_data:** export includes one row per (sample × column that has a value or all columns with nulls — **v1: emit all configured columns per sample**, nulls empty, so grids rehydrate). Prefer **all configured columns × all experiment samples** for complete export even if never saved (empty cells).

**experiment_data:** one row per stored cell (or per configured field if experiment-scoped form with no sample).

### 0.5 Access story (single picture)

```text
                    ┌─────────────────────────────┐
                    │ entry_field_values (typed)  │
                    │ + sample_id / field def     │
                    └─────────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                                       ▼
   GET …/grid (wide)                      GET …/export (long)
   UI tables / capture                    Reports, BI, ETL, scripts
   columns[] + rows[].cells               one record per cell
```

| Consumer | Use |
|----------|-----|
| React EntryCapturePanel | `/grid` + `PUT …/values` |
| Sample journey / detail embeds | `/grid` for one entry |
| Internal reports / future dashboards | `/export?format=json` or `csv` |
| Ad-hoc SQL | Join `entry_field_values` ↔ `entries` ↔ `field_definitions` ↔ `samples` (same as export) |

### 0.6 Columns

| Column kind | On | Editable | Storage |
|-------------|-----|----------|---------|
| **sample_field** (RO) | `experiment_sample_data` (required capability) | **No** | Projection from Sample/related (accessioning SoT). Examples: client_sample_id, client, subject/patient, biotype, received_date |
| **field_definition** | Both kinds | Yes (unless marked RO) | `entry_field_values` typed cells |
| **Ad hoc on instance** | Both kinds | Yes | Existing FieldDefinitions only; **never** write-back |
| **Template-authored** | Both kinds | Yes | May set write-back map (below) |

Admin defines FieldDefinitions. Template picks columns + write-back. Instance may add existing fields without write-back.

### 0.7 Write-back to Sample

| Rule | Detail |
|------|--------|
| Default | **Off** |
| What | Only **experiment-derived** FieldDefinition columns — never accessioning identity fields |
| Map | On **entry column**: `write_back_enabled` + **target Sample field** (dropdown, **type-matched**, from **config-eligible** sample fields so new sample fields can be included without code change) |
| Timing | **On entry submit only**; **Save** = entry values only (long-running steps) |
| Conflict | **Last write wins** + audit previous (`write_back_previous`); expected across processing steps |
| Not via write-back | Container amount/conc/location; volume |

### 0.8 Containers, amount, aliquot/pool

**Canonical locks:** [`.docs-review/open-questions/containers.md`](../open-questions/containers.md) (2026-08-11).

| Rule | Detail |
|------|--------|
| Nesting | Multi-element parent (plate/rack/box) → single-element children (well/tube) → `Contents` only on children |
| Container type | **`rows` × `columns`** (integers ≥ 1). **Not** free-text `dimensions`. `element_count = rows * columns`. 1×1 = tube/well; e.g. 8×12 = plate |
| Contents eligibility | **Only single-element types** (`rows=1` and `columns=1`) may have `Contents`. Multi-element = structure only |
| Contents | samples (cells/compounds-as-samples later); multi-content on one **1×1** vessel (pool tube / multi-sample well) allowed |
| **Amount** | **Solute mass or count only — never volume.** **Liquid/diluent is not mass** (Option A) |
| Contents amount | `Contents.amount` is the per-Sample mass/count contribution in its 1×1 vessel |
| Vessel amount + conc | On a 1×1 Container: `amount` = compatible-unit sum of Contents rows; `concentration` = vessel inventory concentration. `Contents.concentration` is not the concentration SoT. Multi-element has no liquid inventory |
| Volume | **Not stored.** \( V = m_{\text{solute}} / C \) when units allow. Inbound volume+conc → mass; store amount+conc |
| Diluent | Changes concentration (derived volume); does **not** increase stored solute amount |
| Pool in tube | 1 tube (1×1), **x** content rows (x samples) |
| Aliquot/pool **plan** | `experiment_data`: amounts to remove from source / add to dest; **all methods in v1** (by mass, by volume→store mass, target mass, target volume, target concentration, …) — columns/UI switch by method |
| Aliquot/pool **execute** | Reduce source contents amount; create dest 1×1 containers; **create new dest samples**; seed dest contents with amount (+ source conc when applicable); keep vessel amount/conc consistent |
| Aliquot/pool **results** | `experiment_sample_data` for resulting aliquots/pools |

### 0.9 v1 predefined entries (+ LIMS)

| Predefined | Kind | Behavior |
|------------|------|----------|
| **Experiment header** | `experiment_data` | Start context |
| **Samples** | `experiment_sample_data` | Display cohort from queue selection |
| **Aliquot/pool plan** | `experiment_data` | Plan lines + **execute** behavior |
| **Aliquots/pools** | `experiment_sample_data` | Post-execute sample view |
| Plating / LH plan, flow-cell notes | `experiment_data` (generic) for now | Upload/automation file as plan data |
| Instrument primary data | **LIMS Run** | Analysis required; no ELN instrument entry |

**Predefined = functionality** (e.g. execute aliquot), not only a default column pack. Columns depend on method.

**Aliquot/pool atomic pair:** one Add action creates the plan and destination entries together; the destination starts empty. A concrete method selects exactly one mint operation and `METHOD_CATALOG` immediately attaches plan columns plus destination FieldDefinitions. Destination quantitative cells project or write through in the same transaction to the owner described in [mass-concentration-contents.md](mass-concentration-contents.md); never Sample and never a second ledger.

**Non-mint wrappers:** Header, instrument-used, reagent-used, and review are kind + FieldDefinitions only. They do not use `METHOD_CATALOG`. Instrument primary data remains on the LIMS Run.

**Out of v1 / ideas:** materials/lots, index sets + assignment entry, sequencer-specific sample sheets, accessioning manifest/verify revisit.

### 0.10 Lifecycle (entry + experiment)

| Rule | Detail |
|------|--------|
| Edit | **Free edit** until experiment done |
| Save | Entry values only |
| Submit entry | Optional unless template dependency requires it; applies write-back; marks step complete |
| **Entry dependencies** | **Template design**: entry B may require entry A submitted before B can start |
| Experiment complete | **Default: all entries submitted** required |
| Template activation sign-off | **Keep** current transfer-step / mandatory review sign-off for now |

### 0.11 Template UI (in scope for this sketch)

Author on Experiment Template:

- Ordered entries (base kinds + predefined wrappers)
- Columns (sample_field + FieldDefinitions)
- Write-back map (template only)
- Entry dependencies (submit gates)
- Method for aliquot/pool when predefined

Instance: queue start, grid, save/submit, execute aliquot where applicable.

### 0.12 Review order

1. **Lab Ops**  
2. Architecture / eng, CEO, UI, Security  

### 0.13 Open / later (non-blocking for foundation review)

- Exact config UI for write-back-eligible sample fields  
- ~~Formal `element_count` on container type~~ → **Decided:** `rows` × `columns` on type (`element_count = rows * columns`); see open-questions/containers.md (implement pending)  
- Polymorphic contents beyond sample (cells, compounds) schema evolution  
- `experiment_data` multi-row `row_id` if needed beyond cells  
- Accessioning workflow revisit (idea)  

---

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

> **Historical substrate detail:** §§2–15 preserve the implementation history that led to §0. Where these sections say `sample_table` / `experiment_table`, show two sample-table aliquot entries, permit mid-flight cohort growth, or close the gate, §0 and the 2026-08-24 coherence packets supersede them. Do not implement those stale shapes.

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
| Transfer Steps / Protocol Steps / Result Columns **tabs** | **Removed from UI** (2026-08-11, dev) — entries-only authoring |
| Transfer-based mandatory sign-off | **Removed from UI**; saves force `mandatory_review_count: 0` and empty legacy arrays |
| `robot_worklist_configs` | Keep for robot CSV export (separate from template authoring tabs) |
| Old types `sample_data` / `experiment_detail` | Map → `experiment_sample_data` / `experiment_data` |

**Dev:** No production users. Template authoring = Basic Info + Tables & forms. SOP extract may still write legacy JSON keys; UI ignores them and re-save clears them.

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

The experiment cohort is fixed after start. Re-query may refresh values for that fixed cohort; it must not expose a mid-flight add path.

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
| **Q15** | **Superseded** | Atomic predefined pair: plan = `experiment_data`; destinations = `experiment_sample_data`; see §0.9 |
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

**Historical gate note:** the 2026-07-29 Lab Ops Hold below applied to the incomplete generic-table proposal. It is superseded by the 2026-08-10 Accepted-with-conditions header and the narrower 2026-08-24 mint-proof packets. The broader configurable framework is still **mint proof + open holes** and awaits Design Group re-stamp; coding remains Grok Build / paused unless Marc instructs.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| **Lab Ops (SVP)** | lab workflow | Customer lab fit | 1 | **HOLD** | Catalog, aliquot derivatives, plates, materials, submit/lock, Q8 |
| CEO Review | plan review | Scope & product | 1 | SUPERSEDED for gate | Tech Accept only; not sufficient alone |
| UI / Design | plan review | UX | 1 | SUPERSEDED for gate | Tables & forms OK as UI for substrate |
| Eng / Architecture | plan review | Architecture | 1 | SUPERSEDED for gate | Engine OK; product incomplete |
| Security | plan review | Threat model | 1 | SUPERSEDED for gate | Stand when design re-locks |

**Historical verdict (superseded):** NOT CLEARED on 2026-07-29. Retained as review history, not the current status line.
