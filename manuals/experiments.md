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

**Not the same as:** an ELN **Process** (ordered SOP; sidebar **Processes**), a **LimsRun** (sidebar **Runs** — every run has an analysis), or a LimsRun **checklist** (`/v1/processes`). Extract on the common path is an **experiment** (instrument / aliquot-pool execute), not the asked-for LimsRun. Operator SoT: [HOWTO.md](HOWTO.md) § Later execution.

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
| **`reagent`** | Default reagents, plus any the tech adds | One lot picker per reagent | The saved list filters each picker; a use of a reagent not on it is **422** `reagent_not_on_experiment` |
| Legacy/runtime compatibility | `sample_data`, `experiment_detail`, `predefined_action`, `display_table` | — | Kept for existing templates |

**Experiment Header** = experiment data with `predefined_entry_key = experiment_header` (same kind as other experiment data tables).

Sample and experiment data are the two table kinds. **Reagent** is its own entry type (`predefined_entry_key = reagents`, wrapper `reagents`, cardinality 1). A lab manager or an administrator authors the template (`experiment:manage`). A configuration editor does not. The author stores `config.allowed_reagent_ids` from the Admin reagent catalog. Creating an experiment copies that default list onto the experiment entry, and those snapshotted defaults count as on the experiment. A later edit of the template leaves existing experiments on the defaults they had at creation. On a template experiment, **Add reagent** posts `/v1/experiments/{id}/reagents` and appends that active catalog reagent to the experiment entry. A reload still shows it. Adding the same id again is idempotent and does not duplicate the row. An inactive reagent is **422** `reagent_inactive` and the list stays as it was. Each listed reagent has its own lot picker, limited to that reagent's usable lots (lots of an inactive reagent are not usable), and **Record** posts `/v1/reagent-uses` with `experiment_id`. After a listed reagent is inactivated, the row still shows that reagent's name. A reagent that is not on the saved list is **422** `reagent_not_on_experiment` and the lot quantity stays unchanged. The tech adds it first. An ad hoc experiment with no reagent entry gets one when the first reagent is added; until then an experiment use is `reagent_not_on_experiment`. **Remove** sends `PATCH /v1/experiments/{id}/reagents` with `{reagent_id, active: false}`. That includes a template default. The id leaves `config.allowed_reagent_ids` and the lot picker, and is stored on `config.removed_reagent_ids`. Recorded uses stay. Adding the reagent again restores it. A second remove leaves the lists as they are. `PATCH` with `active` true is **422** `reagent_remove_required`. A lab technician may remove and restore (`experiment:manage`); a client and a configuration editor are **403**. There is no DELETE route. A use of a removed reagent is **422** `reagent_not_on_experiment`. The experiment lot row sends **Used on** and an optional **Note** on `/v1/reagent-uses`, matching the LIMS run dialog. An empty **Used on** sends the browser's calendar date. Both fields clear after a saved **Record**. A server-side fallback (API caller omits `used_on`) uses today in the lab timezone stored on `lab_settings`, and lot expiry is checked against that date. The lab timezone is required. It is stored in `lab_settings.timezone` and set by an administrator at the required post-login step, or with `PATCH /v1/lab-settings`. There is no environment fallback. `current_lab_day()` raises until it is set. If the saved zone becomes invalid while the API is running, calls that need the lab date return **503** `lab_timezone_invalid`, and an administrator can still PATCH the zone. A `used_on` after the lab's today is **422** `used_on_in_future`. A use on or before the effective expiry passes; a use after it is **422** `lot_expired`. A `used_on` before the lot's received date, when that date is set, is **422** `used_on_before_receipt`. The usable-lots filter and quantity on hand stay on the lab's today. The **Used on** picker stops at the browser's today. A bad date is still **422** `invalid_date`. An over-draw is **422** `insufficient_amount`. A unit other than the lot's is **422** `incompatible_units`. The sentences stay. Check order on an experiment use: the saved list (`reagent_not_on_experiment`), then the catalog active flag (`reagent_inactive`), then the lot rules. An off-list reagent is `reagent_not_on_experiment` even when it is also inactive. A reagent that is inactive at use time and is already on the list is **422** `reagent_inactive`, including when its lot is still usable. A LIMS-run-only use skips the list check. A LIMS-run use of an inactive reagent is **422** `reagent_inactive`, and the lot quantity stays unchanged. Entries capture process data; sample identity stays on Sample.

### Columns

| Column source | Used on | Storage |
|---------------|---------|---------|
| **Sample RO columns** (`config.sample_columns`) | experiment_sample_data | Read from `samples` (template chips); capture UI may still lag on full RO projection |
| **Entry field definitions** | experiment_sample_data, experiment_data | `field_definitions` with `entity_type` = `experiment_sample_data` \| `experiment_data`, `is_materialized_column = false`; linked via `entry_field_definitions`; values in `entry_field_values` (typed cells) |
| **Aliquot plan** | aliquot_pool_plan | Plan lines plus kind-scoped fields attached from `METHOD_CATALOG`; current runtime still stores plan lines in entry `config` |

**Schema → Columns** (`/admin/schema/columns`) adds a real column on **Samples**, and on a table created from Schema → Tables. Other built-in lab tables (including Test) are browsed here; Add field is off. The Custom Fields page is gone; `/admin/custom-fields` redirects to Schema. Lists, list items, and units (`lists`, `list_entries`, `units`) are not schema tables — edit list values at Admin → Lists and units at Admin → Units.  
**Not** for defining entry table columns. Entry columns are created from the **template** dialog: **Create field** (scoped entity type) or **Add existing field**.

### Values

- Typed columns on `entry_field_values`: text, number, list, date, boolean (`value_json` only for complex cases).
- Sample-scoped: `sample_id` set; `row_key` null.
- Experiment-data multi-row: **`row_key`** set (migration `0057`); `DELETE /v1/entries/{id}/rows/{row_key}` removes a row.
- **Save** = upsert values only. **Submit** = mark complete + Sample write-back for mapped columns (allowlist).

### Runtime UI

- `EntryCapturePanel` on experiment detail (Entries).
- **Instantiate from template** if entries not yet created (also auto on create when template has `entries`).
- Sample data: table by cohort. Experiment data: multi-row table + Add/Delete row. Aliquot: `AliquotPlanEditor`. Reagent: the saved `config.allowed_reagent_ids` list, one lot picker per reagent filtered to that reagent's usable lots. **Remove** sets that reagent inactive on the experiment (`PATCH` `active: false`); the picker drops it and recorded uses stay. Add it again to restore it. Each row has **Used on** (empty sends the browser's date; the picker stops at that day) and an optional **Note**; both clear after a saved **Record**. With every reagent removed and lots already recorded, the panel says the recorded lots stay listed rather than "No reagents yet". Recording a lot of a reagent that is not on that list is **422** `reagent_not_on_experiment`.

### Aliquot / pool destination sample type

One **Add aliquot/pool** (template **+ Aliquot/pool** or ad hoc **Add aliquot/pool**) creates the `aliquot_pool_plan` (`experiment_data`) and empty `aliquots_pools` (`experiment_sample_data`) entries together — wrapper `aliquot_pool` in `WRAPPER_CATALOG`, **cardinality 1**. The UI must not offer plan-only or destination-only authoring. **Either half is the pair:** deleting the dest entry removes both, same as deleting the plan. API **POST** of either side (`aliquot_pool_plan` or `aliquots_pools`) creates the mate (**201**; GET includes both). A second instance while the wrapper exists is **409** `wrapper_at_capacity`. **DELETE** of either inactivates both. After the pair is gone, Add re-enables — one wrapper instance at a time, not a lifetime lock. E-10 UAT §7 is **Pass** (Tobias QA, 2026-09-14 22:28 ET, `dc7ee92`; **7.1–7.8 Pass** on `e5a8fdd` not rescored + Deiter **double-Add Pass** on `dc7ee92`, **409** `wrapper_at_capacity`). Prior overall **Fail** on `e5a8fdd` is **history**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). **Tobias dogfood Ready=Yes** on **`dc7ee92`** (`/workspace/dogfood-e10-dc7ee92/READY.md`). Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay history. §§1–6 stay `008baf2`. Selecting a concrete method immediately attaches both `METHOD_CATALOG` maps: plan columns and destination FieldDefinitions. The destination entry is populated only after execute.

The **Aliquot / pool plan** entry has three separate controls:

- **Method** is one concrete Deiter IN method. It implies exactly one mint
  operation (`aliquot` or `pool`) and controls every line's input columns.
  On an aliquot method, a line that keeps the parent's type is an **aliquot**
  (same sample, new container) and needs no transition; a line that changes
  the type is a **derivative** (new child sample with `parent_sample_id`) and
  must be an active `derivative` row in Sample type transitions. Dest options
  show as **Same as parent (aliquot).** and **<type> (derivative)**.
- **Default dest sample type** is optional on the **template** and the runtime
  plan. **Same as parent.** is always available. Template choices are dests in
  the transition catalog for the method’s mint op (`derivative` rows for an
  aliquot method, `pool` rows for a pool method). Runtime choices are dests
  for the selected source × operation. Execute still refuses off-catalog dests.
- **Default dest container type** is optional. **Same as source.** is always
  available. Only **1×1** vessel types (tube, vial, well) are listed; 96-well
  / multi-position types are not offered. Dest init does **not** prompt for
  container type. Method ≠ dest sample type ≠ dest container type.

Each plan line can **Use entry default**, explicitly clear to **Same as
parent.** (sample type) or **Same as source.** (container type), or select a
catalog-allowed destination override. Type values cannot be entered as free
text. The concrete method is locked after plan lines are saved; changing it
requires canceling the experiment, and cancellation does not remove
already-minted daughters.

All lines in one pool group must have source samples of the same sample type.
The destination selector remains unavailable and a warning identifies the pool
when its source types differ. Saving and executing also enforce this rule.

Execute resolves dest **sample** type line override → entry default → parent,
and dest **container** type line override → entry default → source vessel,
without prompting again. Missing dest container type after that resolve is
**422** `dest_container_type_required`. A plate as dest mint is **422**
`dest_container_type_not_1x1`. `aliquot_by_target_concentration` requires a prior numeric concentration
result on the source sample plus destination volume or target amount; the plan
does not accept free-typed source concentration. Execute-minted daughters join
the current process and populate the read-only **Aliquots / pools** entry after
execute. Matrix behavior is unchanged.

Destination quantitative cells are not an inventory ledger. Per-row mass/count projects or writes through to `Contents.amount`; total mass and vessel inventory concentration project or write through to the 1×1 Container in the same transaction. Sample never owns mass/concentration, and `Contents.concentration` is not the inventory-concentration SoT. See [mass-concentration-contents.md](../.docs/review/tech-sketch/mass-concentration-contents.md).

Normalization offers an eligible prior Result only: same analysis/designated concentration analyte, approved/reviewed first or otherwise latest by entry date. No match or unit mismatch refuses. Publishing the Result writes its value/unit to the bound 1×1 `Container.concentration` in the same transaction.

Non-mint wrappers (Header, instrument-used, reagent-used, review) use a kind plus FieldDefinitions only; they do not use `METHOD_CATALOG`. Instrument primary files and Results remain on the LIMS Run.

**Instruments used on an experiment:** the catalog is lab-wide under **Admin → Instruments** (`/admin/instruments`). Types are the configurable list `instrument_types` (seeded Plate reader, qPCR, LC-MS, Liquid handler, Balance, Centrifuge). Vendor, model, serial, asset tag, optional location, status (`in_service` / `out_of_service` / `retired`), and optional **Track maintenance** live on each instrument. Nothing is deleted: retire with `active` or status.

On an experiment template, add an **Instruments** entry (**Tables & forms → Type → Instruments**, or **+ Instruments**) and define slots (`config.slots`: key, label, instrument_type_id, required, run_import). A LIMS run template needs one typed `run_import` slot. Creating the experiment copies the slots onto the experiment entry. On the experiment, **Add instrument** saves any eligible catalog instrument (`POST /v1/experiments/{id}/instruments`). **Record use** posts `/v1/instrument-uses` with `experiment_id` and `slot_key` when slots exist. A use with neither a LIMS run nor an experiment is **422** `use_target_required`.

A new import or a new instrument use is refused (**422**) when the instrument is inactive, retired, out of service, or down (an open downtime row). Overdue maintenance and a missing schedule block only when **Track maintenance** is on. `GET /v1/instruments/{id}/eligibility` returns the same stop and the flag. LIMS runs do **not** have an `instrument_id` column; the instrument is recorded on the import and on `instrument_uses`. An import on a run with an instrument writes that use row automatically. See [HOWTO.md](HOWTO.md) for the lab path (setup, maintenance, downtime, the run block, and recording use).

Storage browse/move remains outside Experiments. An entry may request an explicit one-shot put-away write-through; it is not a storage entry.

## Starting an experiment (cohort)

**Canonical product rules:** [open-questions/experiments.md Decision #24](../.docs/review/open-questions/experiments.md)

### Eligibility

When adding samples to an experiment:

1. **`Sample.status` = Available for Testing** (list `sample_status`).  
2. **If the experiment is under a process:** sample must be on that process (`eln_process_samples`, not `removed`).  
3. **If the experiment is a process step:** current sample type must be on that step’s accepted list (`eln_process_definition_step_accepted_sample_types`). Mismatch → **422** `route_sample_type`. Standalone experiments are not gated by this table. Inbound types are **not** on the experiment template or an entry.  
4. Selection is **explicit** (never auto-start entire process).  
5. After start, cohort is **locked**.

Scan/resolve of a sample that fails these gates must **not** enter the selected cohort (clear error).

### Product target start UX (product-target dual list)

**Canonical:** [Decision #24](../.docs/review/open-questions/experiments.md). Early labs often **lack barcode scanners**.

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

Permission: `experiment:manage` for manage surfaces. A lab manager or an administrator authors experiment templates. A configuration editor does not, and is not granted `experiment:manage`.

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
- Two product kinds with predefined wrappers; no third action kind.
- product-target **start**: process → choose experiment → select from queue → instance + cohort.
- Clear separation from **LIMS Runs**.
- Containers/amount: solute mass only; see [open-questions/containers.md](../.docs/review/open-questions/containers.md).
