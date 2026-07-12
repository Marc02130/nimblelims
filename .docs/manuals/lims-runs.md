# LIMS Runs

## Purpose

**LIMS Runs** are the structured LIMS component for capturing the execution of defined experimental protocols, particularly where data is imported from instruments or external parties (CROs), and where a formal review/publish lifecycle + optional analysis is required.

Primary goals:
- Support repeatable, data-driven work (CRO or in-house).
- Provide a clean lifecycle for ordering, data receipt, review, and publication.
- Enable structured data import with validation.
- Serve as a foundation for analysis (currently dose-response is the most mature example; the intent is to support other analyses).

**Important distinction**: An LIMS Run is **not** the same as a Batch.
- Batches are operational groupings for processing samples through tests and results entry.
- LIMS Runs represent execution of a protocol/template with focus on data capture, structure, lifecycle, and derived analysis.

## Core Entities

| Entity                        | Description                                                                 | Notes |
|-------------------------------|-----------------------------------------------------------------------------|-------|
| `ExperimentTemplate`          | Reusable protocol definition (shared with ELN Experiments)                  | Contains `lifecycle_type`, `template_definition`, parser/worklist config |
| `LimsRun`               | An instance of a template execution                                         | Strict status, data import, review lifecycle |
| `ExperimentData`              | Imported data rows (one row typically = one instrument reading / well)      | `row_data` (JSONB), optional `well_position`, `sample_id`, `container_id` |
| `InstrumentParser`            | Column mapping config for importing instrument files                        | Learned or defined per template |
| `RobotWorklistConfig`         | Configuration for generating robot transfer worklists                       | Currently generic CSV (source/dest/volume) |
| `LimsRunChecklist` / `LimsRunChecklistStep` | Sub-process tracking within a run (e.g. "Sample Prep", "Bioanalysis")     | Exists but not yet wired in main UI |

### LimsRun

- Table: `lims_runs`
- Status is a strict enum (`LimsRunStatus`) with two lifecycles controlled by the template's `lifecycle_type`.
- Key timestamps: `started_at`, `completed_at`, `published_at`, `canceled_at`.
- Special field: `fit_in_progress` (mutex for curve fitting).
- **`analysis_id`** (optional FK → `analyses`): **opt-in** for promote-on-publish. When set, publishing writes Tests/Results from imported data. When null, publish is data-only (non-reportable path).

### Lifecycle and Status (Current)

Controlled by `experiment_templates.lifecycle_type`:

**Standard** (typical in-house):
```
draft → running → complete → published
          └──────┴──► failed | canceled
```

**CRO** (external lab):
```
draft → ordered → running → results_received → complete → published
          └────────────────────────────┴──► failed | canceled
```

- `ordered`: Work sent to CRO / external party.
- `results_received`: Data returned by CRO (import allowed here).
- Import of data is only permitted in `running` or `results_received`.
- `complete → published` requires the `experiment:publish` permission.
- Cancel is allowed from any non-terminal state.

### Promote-on-publish (structured Tests / Results)

Shipped v1 — see [ideas/run-results.md](../ideas/run-results.md).

| Rule | Behavior |
|------|----------|
| **When** | Status → `published` **and** run has **`analysis_id`** |
| **If no analysis** | Publish still succeeds; **no** Tests/Results written (user warned at **start** unless they ack) |
| **Mapping** | JSONB column → analyte via **name** or **analyte alias** (casefold); known non-analyte keys (`units`, etc.) skipped |
| **Tests** | Find-or-create Test per `(sample_id, analysis_id)` |
| **Results** | Write `raw_result`, `replicate` (from JSONB or row order), `lims_run_id` lineage |
| **Conflicts** | Same run → update; other run / manual result owns triple → **409**, publish blocked |
| **Preview** | `GET /v1/lims-runs/{id}/promotion/preview` — dry-run; UI shows counts on Publish confirm |
| **Permissions** | **Publish alone** may create/update tests/results on this path |
| **Batch size** | Env `LIMS_PROMOTE_BATCH_SIZE` (default **200**) |

Instrument JSONB remains SoT for raw import; Results are the published structured projection.

## Data Model Characteristics

- Data is stored as flexible `row_data` (JSONB) per row (`lims_run_data`).
- Association to samples is lighter than ELN Experiments (direct `sample_id` on data rows).
- `TemplateWellDefinition` (added for dose-response) provides relational storage for well-level concentrations, roles, and replicate groups.
- This model currently has a bias toward plate/well-based instrument data.
- Structured LIMS **results** after publish: `results.lims_run_id`, `results.replicate`; results are **not** named entities (no global `name`).

## Relationship to Other Concepts

- **Templates**: Shared with ELN Experiments. `lifecycle_type` on the template selects the state machine.
- **Samples**: Linked via imported data rows. Less rich than `ExperimentSampleExecution` (no built-in role/replicate/conditions on the junction itself).
- **Batches**: Different concept. See warning above. Do not model a Run as "the batch of samples tested".
- **ELN Experiments**: Separate. Runs are the structured LIMS execution path. Future linking may be added.
- **Analyses / Analytes**: Catalog for reportable assays. Aliases on analytes support multi-CRO column names. Associating an analysis to a run is the promote opt-in.
- **Dose Response**: Specialized analysis on top of Runs (curve fitting, exclusions, review)—orthogonal to classic promote-to-results.

## In-House vs CRO

- Use `lifecycle_type = 'standard'` on the template for in-house work.
- Use `'cro'` when work is sent to an external organization and data will be returned later.
- The system already supports both paths through the same Run entity.

## Current Limitations (Flexibility)

- Status is a rigid enum. Adding new states requires:
  - Database enum alteration (messy in Postgres).
  - Updates to transition dictionaries.
  - Service, API, and UI changes.
- Data model leans toward wells + instrument rows. Not ideal for all ADME/PK time-course or non-plate data without stretching.
- Strong current coupling to dose-response features in UI and supporting tables.
- No generic "result columns + calculations" framework yet beyond dose-response.
- Processes/steps tracking exists in the database but is not surfaced in the main Run detail UI.
- Workflow engine has no actions for creating or advancing Runs.

## Status Design: Enums vs Lookup Tables

**Current approach for Runs**: Postgres `ENUM` + hardcoded transition maps in Python.

**Problems**:
- Adding states requires migrations and coordinated code changes.
- Less flexible for client-specific or experiment-type-specific phases.
- Harder to surface in UI configuration.

**ELN Experiments already use lookup tables** (`list_entries` for `experiment_status`). This is more flexible.

**Recommendation for LIMS Runs**:
Lookup tables (or an extension of the lists system) are generally a better long-term design for status when you want:
- Easier addition of states without DB migrations.
- Potential for per-template or per-client customization.
- Better auditability and UI-driven configuration.

You can still enforce strict state-machine rules in the application service layer (recommended). A hybrid approach works well:
- Status values in a lookup table.
- Allowed transitions defined per `lifecycle_type` (in the template JSON or a dedicated config table).

## Proposed Mental Model (Direction)

- **Experiment (ELN)**: Flexible notebook for processes, conditions, sample roles, and lineage.
- **LIMS Run (LIMS)**: Structured execution of a protocol. Focus on data import/capture, lifecycle (including CRO handoff), review/publish, and analysis.
- `lifecycle_type` on the template should influence both sides (reviews/approvals on Experiments + state machine on Runs).
- Runs should become more general-purpose for lab data work (in-house and CRO), not just dose-response.

## UI / API Surface

- Routes: `/runs`, `/runs/:id`, `/runs/:id/dose-response`
- Main pages: RunsManagement, LimsRunDetail (Overview / Data / Dose Response tabs)
  - Overview: select **Analysis**, start warning if none, **Publish** opens promotion preview when analysis is set
- API under `/v1/lims-runs` (including `GET …/promotion/preview`, publish = `PATCH …/complete`)

## Next Steps / Open Questions

- Clarify distinction from Batches in all documentation and UI.
- Decide on status implementation (enum vs lookup table) before adding many more phases.
- Define what "more flexible" data structures are needed for general ADME / non-dose-response work.
- Consider whether `LimsRun` should eventually be able to live inside (or be referenced by) an ELN Experiment.
- Follow-on ideas: [ai-data-import](../ideas/ai-data-import.md), [ai-data-analysis](../ideas/ai-data-analysis.md), [ai-analyte-resolution](../ideas/ai-analyte-resolution.md).

---

**Related Documents**
- [ideas/run-results.md](../ideas/run-results.md) — promote-on-publish design + shipped phases
- [open-questions/run-results.md](../open-questions/run-results.md) — decisions
- `.docs/manuals/processes.md`
- `.docs/design/gap-analysis-process-and-experiment.md`
- `.docs/manuals/experiments.md` (ELN side)
- `.docs/design/experiment-planning.md`
- `.docs/checklist/experiment-rework-prerequisites.md`
- `.docs/manuals/batches.md` (for contrast)