# Experiments (ELN)

## Purpose

The **Experiments** system is the Electronic Lab Notebook (ELN) component of NimbleLIMS. It is designed for tracking complex, multi-step, often manual or semi-structured laboratory processes.

Typical use cases:
- Multi-step sample preparation workflows (e.g. NGS library prep, extraction protocols)
- Process chaining and lineage tracking
- Capturing experimental conditions, notes, and sample roles per step
- Linking to downstream tests/results when needed
- Workflow-orchestrated lab work

It is **not** primarily for high-volume instrument data import or curve fitting/analysis.

## Core Entities

| Entity                        | Description                                                                 | Key Characteristics |
|-------------------------------|-----------------------------------------------------------------------------|---------------------|
| `ExperimentTemplate`          | Reusable definition of an experiment (protocol structure)                   | `template_definition` (JSONB), `lifecycle_type`, `active` |
| `Experiment`                  | An instance/run of a template or ad-hoc experiment                          | Links to template, flexible status, started/completed dates |
| `ExperimentDetail`            | Free-form steps, protocol entries, notes, or links between experiments      | `detail_type`, `content` (JSONB), `sort_order` |
| `ExperimentSampleExecution`   | Association between an experiment and samples (or aliquots)                 | `role_in_experiment`, `processing_conditions` (JSONB), `replicate_number`, optional `test_id`/`result_id` |

### ExperimentTemplate

- Stored in `experiment_templates`.
- `template_definition` (JSONB) holds protocol steps, transfer steps, result expectations, etc.
- `lifecycle_type` (currently `'standard'` or `'cro'`) — intended to influence review/approval requirements on the Experiment side as well as Runs.
- Can be created manually or via SOP upload + AI extraction.

### Experiment

- Uses `BaseModel` (has `active` soft-delete, global name uniqueness).
- Status is **flexible** via FK to `list_entries` (the `experiment_status` list).
  - Seeded values: Draft, In Progress, Completed, On Hold, Cancelled.
  - Workflows can update status via `update_experiment_status` action.
- Can exist without a template (ad-hoc).
- Has `started_at` / `completed_at`.

### Details and Sample Executions

- **Details** (`ExperimentDetail`): Key-value or structured content. Used for protocol steps, conditions, and `experiment_link` lineage.
- **Sample Executions**: Rich junction table. Supports:
  - Role in experiment
  - Processing conditions (JSONB)
  - Replicates
  - Direct linkage to Tests/Results for promotion of data

## Status and Lifecycle

Currently:
- Status lives on the `Experiment` (`status_id` → list_entries).
- The list is configurable/extensible.

Planned direction:
- `lifecycle_type` on the template should also drive Experiment behavior (e.g. whether certain review/approval steps are mandatory before a status can be reached).
- This allows "standard" (lighter) vs more controlled lifecycles with required sign-offs.

## Relationship to Other Concepts

- **Templates**: Reusable blueprints. One template can be used by many Experiments.
- **Workflows**: Full support (`create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`).
- **Samples**: Bidirectional linking via executions. Sample detail pages show "Participated in these Experiments".
- **Experiment Runs (LIMS)**: Separate concept. See `.docs/experiment-runs.md`. Not the same as an ELN Experiment.

## UI

- Sidebar: "All Experiments" and "Experiment Templates" (under Experiments accordion).
- List + detail with tabs: Overview, Sample Executions, Details/Steps, Lineage, Linked Processes.
- "My Experiments" filter via `?mine=true`.
- Templates management at `/experiments/templates` (includes SOP upload, mandatory review sign-off, activation guard).

## Current Limitations

- Status is relatively loose (list-driven) with no built-in state machine or mandatory review enforcement on the ELN side yet.
- Lineage is currently a linked list via detail rows (not a formal DAG).
- No direct parent/child relationship to Experiment Runs (as of now).
- Name uniqueness is global (via `BaseModel`).

## Design Goals (Current Thinking)

- Keep Experiments as the flexible **ELN** tool for process work.
- Use `lifecycle_type` on templates to control required reviews/approvals on Experiments.
- Maintain clear separation from the more structured LIMS Experiment Runs.

---

**Related Documents**
- `.docs/experiment-runs.md`
- `.docs/experiment-planning.md`
- `.docs/experiment-rework-prerequisites.md`
- `.docs/workflow-accessioning-to-reporting.md` (workflow actions)