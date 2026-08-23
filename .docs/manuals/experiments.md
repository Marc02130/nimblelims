# Experiments (ELN)

## Purpose

The **Experiments** system is the Electronic Lab Notebook (ELN) component of NimbleLIMS. It is designed for tracking complex, multi-step, often manual or semi-structured laboratory processes.

Typical use cases:
- Multi-step sample preparation workflows (e.g. NGS library prep, extraction protocols)
- Process chaining and lineage tracking
- Capturing experimental conditions, notes, and sample roles per step
- Linking to downstream tests/results when needed
- Workflow-orchestrated lab work

Experiments **can** capture certain instrument-based QC data (e.g. Tapestation, Qubit, and similar quality control uploads).

It is **not** the primary home for large-scale result data analysis or dose-response curve fitting (see LIMS Runs).

## Core Entities

| Entity                        | Description                                                                 | Key Characteristics |
|-------------------------------|-----------------------------------------------------------------------------|---------------------|
| `ExperimentTemplate`          | Reusable definition of an experiment (ordered **entries**)                  | `template_definition` (JSONB: `entries[]`, plate layout, …), `lifecycle_type`, `active` |
| `Experiment`                  | An instance of a template (or ad-hoc)                                       | Links to template, flexible status, started/completed dates, fixed sample cohort after start |
| `Entry`                       | Capture / action block on an experiment                                     | Instantiated from template; kinds below |
| `ExperimentSampleExecution`   | Sample ↔ experiment association (cohort)                                    | Role, conditions, replicates |

### ExperimentTemplate

- Stored in `experiment_templates`.
- **Authoring UI** (`/experiments/templates`): **Basic Info** + **Tables & forms** only (Protocol/Transfer/Result Columns tabs removed).
- `template_definition.entries[]` declares ordered entry blocks (type, name, `predefined_entry_key`, sample RO columns, field definition IDs, dependencies).
- On save, legacy `protocol_steps` / `transfer_steps` / `result_columns` are cleared and `mandatory_review_count` is set to 0.
- New templates seed **Experiment header** + **Samples** presets.
- SOP upload may pre-fill basic fields; author **Tables & forms** for the reusable body.
- `lifecycle_type`: `'standard'` \| `'cro'`.

### Experiment

- Uses `BaseModel` (has `active` soft-delete, global name uniqueness).
- Status is **flexible** via FK to `list_entries` (`experiment_status` list).
- Can exist without a template (ad-hoc).
- Has `started_at` / `completed_at`.
- **Cohort is fixed after start** — samples selected at start only (no mid-flight add).

## Experiment Entries (Data Capture)

### Entry kinds

| Kind | Product meaning | Layout | Rows |
|------|-----------------|--------|------|
| **`experiment_sample_data`** | Per-sample process data | **Table** | One row per sample in the experiment cohort |
| **`experiment_data`** | Experiment-level / purpose tables (incl. **Experiment Header**) | **Table only** (no form layout) | Multi-row free rows (`row_key`); user adds rows |
| **`predefined_action`** | Built-in behavior | Special UI | e.g. **Aliquot / pool** plan + execute |
| Legacy | `sample_data` → sample data; `experiment_detail` → experiment data | — | Normalized on write |

**Experiment Header** = experiment data with `predefined_entry_key = experiment_header` (same kind as other experiment data tables; not a separate “Overview” product type).

### Columns

| Column source | Used on | Storage |
|---------------|---------|---------|
| **Sample RO columns** (`config.sample_columns`) | experiment_sample_data | Read from `samples` (template chips); capture UI may still lag on full RO projection |
| **Entry field definitions** | experiment_sample_data, experiment_data | `field_definitions` with `entity_type` = `experiment_sample_data` \| `experiment_data`, `is_materialized_column = false`; linked via `entry_field_definitions`; values in `entry_field_values` (typed cells) |
| **Aliquot plan** | aliquot_pool_plan | Plan lines in entry `config` + execute service — not FieldDefinition columns |

**Custom Fields** (`/admin/custom-fields`) = extend **DB entities** (Sample, Test, …).  
**Not** for defining entry table columns. Entry columns are created from the **template** dialog: **Create field** (scoped entity type) or **Add existing field**.

### Values

- Typed columns on `entry_field_values`: text, number, list, date, boolean (`value_json` only for complex cases).
- Sample-scoped: `sample_id` set; `row_key` null.
- Experiment-data multi-row: **`row_key`** set (migration `0057`); `DELETE /v1/entries/{id}/rows/{row_key}` removes a row.
- **Save** = upsert values only. **Submit** = mark complete + Sample write-back for mapped columns (allowlist).

### Runtime UI

- `EntryCapturePanel` on experiment detail (Entries).
- **Instantiate from template** if entries not yet created (also auto on create when template has `entries`).
- Sample data: table by cohort. Experiment data: multi-row table + Add/Delete row. Aliquot: `AliquotPlanEditor`.

### Aliquot / pool destination sample type

The **Aliquot / pool plan** entry has two separate controls:

- **Method** is one concrete Deiter IN method. It implies exactly one mint
  operation (`aliquot` or `pool`) and controls every line's input columns.
- **Default dest sample type** is optional. **Same as parent.** is always
  available. Catalog choices are the destinations shared by the selected source
  samples for the entry's mint operation.

Each plan line can **Use entry default**, explicitly clear to **Same as
parent.**, or select a catalog-allowed destination override. Type values cannot
be entered as free text. The concrete method is locked after plan lines are
saved; changing it requires canceling the experiment, and cancellation does not
remove already-minted daughters.

All lines in one pool group must have source samples of the same sample type.
The destination selector remains unavailable and a warning identifies the pool
when its source types differ. Saving and executing also enforce this rule.

Execute resolves line override → entry default → parent, without prompting
again. `aliquot_by_target_concentration` requires a prior numeric concentration
result on the source sample plus destination volume or target amount; the plan
does not accept free-typed source concentration. Execute-minted daughters join
the current process and populate the read-only **Aliquots / pools** entry after
execute. Matrix behavior is unchanged.

## Starting an experiment (cohort)

**Canonical product rules:** [open-questions/experiments.md Decision #24](../open-questions/experiments.md)

### Eligibility (required — not yet fully enforced in code)

When adding samples to an experiment:

1. **`Sample.status` = Available for Testing** (list `sample_status`).  
2. **If the experiment is under a process:** sample must be on that process (`eln_process_samples`, not `removed`).  
3. Selection is **explicit** (never auto-start entire process).  
4. After start, cohort is **locked**.

Scan/resolve of a sample that fails these gates must **not** enter the selected cohort (clear error).

### Product target start UX (Sapio-aligned dual list)

**Canonical:** [Decision #24](../open-questions/experiments.md). Early labs often **lack barcode scanners**.

1. **Process accordion** — click step/experiment to **Start** (not a permanent panel on experiment detail).  
2. **Ephemeral dialog — dual list (primary):**

   | Available (eligible) | `<<` `<` `>` `>>` | Selected |
   |----------------------|-------------------|----------|
   | Process samples + **Available for Testing** | Move | Cohort (starts empty) |

3. **Optional scan/paste** — only moves **eligible** samples into Selected.  
4. **Start** — dialog **closes** (disappears); experiment has fixed cohort; **no** “add samples” UI left on experiment detail (avoids expecting mid-flight adds).  
5. **Process sample update** — for each selected sample on the process: `eln_process_samples.status → in_progress`, `current_step_id → this step`. Global `Sample.status` unchanged.

**Do not** keep dual-list / `StartCohortPanel` always visible on experiment detail after start (or as a standing tab control that implies samples can be added anytime).

### Current NimbleLIMS implementation

| Piece | Status |
|-------|--------|
| Create experiment from template | Yes |
| Dual-list `StartExperimentDialog` from process **Start** | **Yes** (Decision #24) |
| Server gates: Available for Testing + process membership | **Yes** on start / link / resolve-scan annotate |
| Process sample → `in_progress` + `current_step_id` on start | **Yes** |
| Permanent add-samples panel on experiment detail | **Removed** — ad hoc start is one-shot dialog only |

## Processes

See [processes.md](processes.md). Processes group ordered steps (`eln_experiment` \| `lims_run`). Sample journey: `GET /v1/samples/{id}/journey`.

## Status and Lifecycle

Status for Experiments uses a flexible list (`experiment_status`). `lifecycle_type` on the template can influence review behavior.

## Relationship to Other Concepts

- **Templates**: Reusable blueprints; many Experiments per template.
- **Workflows**: `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, etc.
- **Samples**: Cohort via `ExperimentSampleExecution`.
- **LIMS Runs**: Separate instrument import/promote path — [lims-runs.md](lims-runs.md).

## UI map

| Route | Purpose |
|-------|---------|
| `/experiments` | Experiment list + detail (Overview, Sample Executions, Entries/`EntryCapturePanel`, Lineage, …) |
| `/experiments/templates` | Template CRUD: Basic Info + Tables & forms; Create field for entry columns |
| `/experiments/processes` | Process definitions + instances |

Permission: `experiment:manage` for manage surfaces.

## APIs (entries — high level)

| Endpoint | Role |
|----------|------|
| `GET/POST /v1/experiments/{id}/entries` | List / create entries |
| `POST /v1/experiments/{id}/entries/instantiate` | From template |
| `PUT /v1/entries/{id}/values` | Save cells (`sample_id` and/or `row_key`) |
| `DELETE /v1/entries/{id}/rows/{row_key}` | Delete experiment_data table row |
| `POST /v1/entries/{id}/submit` | Submit + write-back |
| `GET /v1/entries/{id}/grid` | Wide grid (sample RO + field cols) |
| `GET /v1/entries/dest-sample-types` | Allowed destination sample types for `source_sample_id` + `operation` |
| Aliquot plan / execute | Under `/v1/entries/...` |

## Design Goals

- Template-driven **entries** as the ELN body (tables + predefined actions).
- Sapio-aligned **start**: process → choose experiment → select from queue → instance + cohort.
- Clear separation from **LIMS Runs**.
- Containers/amount: solute mass only; see [open-questions/containers.md](../open-questions/containers.md).
