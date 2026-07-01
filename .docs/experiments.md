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

It is **not** the primary home for large-scale result data analysis or dose-response curve fitting (see Experiment Runs).

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

## Processes

See the dedicated document [`.docs/processes.md`](processes.md) for full details.

**Summary**: Processes are ordered collections of Experiments. They provide structure for multi-step work where sample flow and sequencing matter. A future UI will support creating processes, assigning samples to them, and queuing samples through the experiments that make up the process.

## Experiment Entries (Data Capture)

Experiments capture data through **entries**. Entry types include:

- Table data display
- Action entries (aliquoting, re-racking, QC data review (pass/fail), etc.)
- Sample-specific data entries
- Experiment-specific data entries

**Rules for entries:**

- Most entries are **predefined** (e.g. flowcell loading, pooling/aliquoting, index assignment). Predefined entries can be added to experiment templates.
- Only **sample data entries** and **experiment detail entries** are free-form/custom.
- Sample data entries and experiment detail entries have their columns defined in the template.
- Sample data entries must be able to write back to the core Sample table (e.g. updating concentration, volume, etc.).
- Sample and experiment data entries use experiment-specific tables (not generic EAV for everything).

This gives templates strong control over the structured parts of an experiment while still allowing per-experiment customization where needed.

## Status and Lifecycle

Status for Experiments uses a flexible list (`experiment_status` via `list_entries`). This is configurable and extensible — some labs do not require sign-off for every experiment.

**Benefits of the flexible list approach (preferred for ELN Experiments):**
- Labs can define their own statuses without code changes.
- No forced workflow for simple or internal work.
- Easy to evolve per organization.

A more rigid state machine (with enforced transitions) has benefits in other contexts (see Experiment Runs), such as:
- Preventing invalid operations (e.g. data import before prerequisites met).
- Clear audit trail with automatic timestamps on transitions.
- UI can reliably offer "next actions" and block invalid paths.
- Useful when external parties (CROs) or regulated processes are involved.

For ELN-style Experiments, the list-based approach gives the right balance of structure and flexibility.

`lifecycle_type` on the template can still influence behavior (e.g. whether certain review/approval steps become mandatory before advancing).

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

- The "entries" system described above is not yet implemented. Current implementation uses loose `ExperimentDetail` + `ExperimentSampleExecution`.
- Process management UI (creating processes, ordering experiments, assigning/queuing samples) does not exist yet.
- Lineage between experiments is currently implemented as `experiment_link` detail rows (linked-list style). A more explicit ordered process model would be clearer.
- No direct relationship model between Experiments and Experiment Runs yet (intentionally kept separate per current direction).
- Name uniqueness is global (via `BaseModel`).
- Sample write-back and experiment-specific tables for data entries need to be designed and built.

## Design Goals (Current Thinking)

- Experiments are the core of the **ELN** for process-oriented work.
- Use a flexible list-based status for Experiments (configurable per lab). `lifecycle_type` on templates can add required reviews/approvals where needed.
- Support rich, template-driven **entries** for data capture and actions (predefined entries + custom sample/experiment detail entries with write-back).
- Processes are explicitly managed collections of ordered, linked Experiments.
- Maintain clear separation from **Experiment Runs** (LIMS side). QC instrument uploads (Tapestation, Qubit, etc.) can live in Experiments; large structured result sets and analysis stay with Runs.
- Provide UI support for process creation, sample assignment to processes, and queuing samples into experiments within a process.

---

**Related Documents**
- `.docs/processes.md`
- `.docs/design-review-process-and-experiment.md`
- `.docs/gap-analysis-process-and-experiment.md`
- `.docs/experiment-runs.md`
- `.docs/experiment-planning.md`
- `.docs/experiment-rework-prerequisites.md`
- `.docs/workflow-accessioning-to-reporting.md` (workflow actions)

---

*Feedback incorporated from review (2026-06-30). See updated sections above on Purpose (QC data), Processes, Entries, Status/Lifecycle, Limitations, and Design Goals.*
