# Processes

## Purpose

Processes are a higher-level organizational concept that group one or more **Experiments** into an ordered sequence of work.

Key characteristics:
- Order matters.
- A process represents a logical workflow or pipeline (e.g., sample prep → QC → library prep → pooling).
- Samples can be assigned to a process and progressively moved through the experiments that make up the process.

Processes sit above individual Experiments and provide structure for multi-step experimental work.

## Core Concepts

| Concept     | Description                                                                 |
|-------------|-----------------------------------------------------------------------------|
| **Process** | An ordered collection of Experiments.                                       |
| **Step**    | An individual Experiment within a Process (position in the sequence matters). |
| **Sample Assignment** | Samples are assigned to a Process via `ProcessSample`, then queued into specific Steps (Experiments) where `ExperimentSampleExecution` tracks detailed per-experiment data. |

### Process vs. Experiment

- An **Experiment** is a single unit of work (with entries, data, samples, details, etc.).
- A **Process** is the container and sequencer for multiple related Experiments.
- The same Experiment Template can potentially be used in multiple Processes.

## Current Implementation (Phase 1 — backend)

ELN Processes are first-class (distinct from LIMS run sub-processes).

| Layer | Detail |
|-------|--------|
| Tables | `eln_processes`, `eln_process_steps`, `eln_process_samples` (migration `0047`) |
| API | `/v1/eln-processes` (CRUD, steps, sample assign/advance) |
| Permission | `experiment:manage` |
| Checklist | [`.docs/experiments/checklist.md`](experiments/checklist.md) |

**Naming:** ELN uses `eln_*` prefixes and `/v1/eln-processes`. LIMS run checklists remain at `/v1/experiment-runs/{id}/processes` and `/v1/processes/{id}` (tables `experiment_processes` / `process_steps`).

**Still informal / legacy:**

- `ExperimentDetail` with `detail_type = "experiment_link"` still exists and **coexists** with ELN Processes (no forced migration in Phase 1).
- No dedicated Process UI yet (Phase 2).
- Entries / write-back are Phase 2.

See [`.docs/experiments.md`](experiments.md) for `experiment_link` lineage and [checklist](experiments/checklist.md) for remaining work.

## Target Design

### Process Structure

- A Process has an ordered list of Experiments (or references to Experiment Templates + instances).
- Each step in the process can have its own configuration (e.g., which entries are active, sample requirements).
- Processes can carry high-level metadata (name, description, overall status, owner, etc.).

### Sample Flow

1. Samples are assigned to a Process (tracked in `ProcessSample`).
2. Samples (from the process) are queued into the first (or chosen) Experiment/step in the process.
3. As work completes in one experiment, samples can be advanced/queued into subsequent experiments in the defined order.
4. Per-experiment sample details (roles, conditions, replicates) continue to be tracked via `ExperimentSampleExecution`.
5. The process provides visibility into overall progress across all its steps.

### UI Requirements

A dedicated process management UI is needed with at least the following capabilities:

- Create and edit Processes
- Define the ordered sequence of Experiments within a Process (from templates or existing experiments)
- Assign samples to a Process
- Queue / move samples between experiments within the process
- View process-level status and progress
- Manage sample state per step (e.g., "queued", "in progress", "complete" at the process step level)

## Data Model Considerations

Proposed direction (subject to design):

- Introduce a `Process` model (or reuse/enhance existing structures).
- A junction or ordering table that maintains the ordered list of experiments belonging to a process.
- `ProcessSample` table to track samples assigned to a Process (separate from per-experiment tracking via `ExperimentSampleExecution`).
- Junction table for ordered experiments within a process (e.g. `process_experiments` with `sort_order`).
- Process-level metadata and status.

Current lineage via `experiment_link` details may be superseded or augmented by explicit process ordering.

## Relationship to Other Concepts

- **Experiments**: Building blocks. A Process is made of Experiments.
- **Experiment Runs (LIMS)**: Kept separate. Processes are part of the ELN / experimental workflow layer.
- **Workflow Templates**: Different concern. Workflow templates are general automation sequences. Processes are specifically about sequencing Experiments and moving samples through them.
- **Batches**: Operational grouping for testing/results. Processes are experimental workflow constructs.
- **Samples**: Assigned to processes; can flow through multiple experiments.

## Current Limitations

- No first-class Process concept.
- Linking is only a loose linked-list via detail records.
- No UI support for process creation or sample queuing across experiments.
- No clear way to manage ordered multi-experiment workflows with shared samples.

## Design Goals

- Make Processes first-class so that complex, ordered experimental work can be modeled explicitly.
- Provide clear UI and backend support for sample assignment and progression through a process.
- Keep Processes in the ELN domain (distinct from LIMS Experiment Runs).
- Allow flexibility: some labs may use simple single-experiment workflows; others will need rich multi-step processes.

## Open Questions

- Should Processes be able to contain both ELN Experiments and references to Experiment Runs?
- How should process-level status aggregate from the individual experiments/steps?
- Do we need versioning or templating of Processes themselves (reusable process definitions)?
- How do process steps interact with the new "Entries" model inside individual Experiments?
- What permissions model applies at the process level vs. individual experiment level?

---

**Related Documents**

- [`.docs/design-review-process-and-experiment.md`](design-review-process-and-experiment.md)
- [`.docs/gap-analysis-process-and-experiment.md`](gap-analysis-process-and-experiment.md)
- [`.docs/experiments.md`](experiments.md)
- [`.docs/experiment-runs.md`](experiment-runs.md)
- [`.docs/experiment-planning.md`](experiment-planning.md)
- [`.docs/experiment-rework-prerequisites.md`](experiment-rework-prerequisites.md)
- [`.docs/workflow-accessioning-to-reporting.md`](workflow-accessioning-to-reporting.md) (for contrast with Workflow Templates)