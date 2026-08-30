# Processes

## Purpose

Processes are a higher-level organizational concept that group one or more **Experiments** into an ordered sequence of work.

Key characteristics:
- Order matters.
- A process represents a logical workflow or pipeline (e.g., sample prep → QC → library prep → pooling).
- Samples can be assigned to a process and progressively moved through the experiments that make up the process.

Processes sit above individual Experiments and provide structure for multi-step experimental work.

**Asked-for does not start a process.** Recording **requested analysis** does not execute or mint a Test. A routing-map row authors TAT + ordered `process_definition[]`, with no analysis or sample-type picker. A route **may have multiple LimsRun analyses**. Map save **409**s when overlapping TAT, overlapping first-step allow-lists, **and** overlapping LIMS Run analysis **sets** all hold; extract-first and Qubit-first for the same TAT are legal. Route assigns when current type is on the first process’s first Experiment/LimsRun list **and** the asked-for analysis is **contained** in the route: zero acceptable → **422**, two saved rows that both accept this type and this analysis → **409**, exactly one → queued work order. Never silently use `first()`. Map save **422**s when the type emerging from process *x* is not accepted by process *x+1*. **Start process** requires `experiment:manage` and instantiates only the first process. A process assignment is the **tube in hand** — a **container that holds a sample** (`eln_process_samples.container_id` required). A sample may have many containers; only one container-with-sample is in the process. Deiter C1 **Pass** on `4671ba8` / `02fe95f`: no-vessel assign → **422** `process_container_required`; two-vessel assign with no pick → **422**; receive-tube assign → **201**. There is **no silent pick** — never `first()`. Deiter C2 **Fail**: execute mints dest, does **not** join dest or remove source; emptied-source assign is a **201 mix-up**; **PATCH is not a path**. Do not teach dest-follows as shipped. **OQ-WO-6** stays **OPEN**: an earlier LimsRun must not share the asked-for `analysis_id`.

**Equivalent aliquot vs dest mint.** The target equivalent aliquot is the **same sample in a new container**: no new sample identity, no `sample_type` rewrite. It is **not shipped**: Deiter C2 **Fail** (Leadership Confirm on `02fe95f`) records dest not on the process; execute never writes the same-sample dest container onto `eln_process_samples`; emptied source still assignable (**201**) is leftover amount-0 Contents / leftover process-join; later Start via `_continuing_assignments` rides the emptied parent. **PATCH is not a path.** Dest mint Hold **Pass** is a different punch — still **Blood**, **0 DNA**; a new Sample with `dest_sample_type` is not this fix. Coding stays **Grok Build** (dest-join / source-remove). Extract-hold UAT step **1.7** is **OOB entry execute** and must not teach a DNA daughter.

**Test identity is `(sample, analysis)`.** The container on the process records **which vessel was measured**; a concentration write-through hits that container. The container is not a Test key.

Contents grain is **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter). Deiter clicked product `4671ba8` / assignment commit `02fe95f` (migration `0077`): C1 **Pass**, C2 **Fail**, dest mint Hold **Pass**. Leadership Confirmed that click — C1/C2 are **not** unsigned. Docs Confirm `84d2810` is not a new execute and not the click SHA. Overall P2 remains **unsigned / not Pass**. Route stays `test:assign`.

### Product rule (Decision #6)

| Entity | How it is defined |
|--------|-------------------|
| **Experiment** | **Ad hoc** *or* from an **ExperimentTemplate** |
| **Process** | **Always defined** — first-class reusable **process definition**; a running process is an **instance** of that definition |

Phase 1–2 shipped ad hoc process create as a provisional MVP; Phase 3 made definitions first-class. See [open-questions/experiments.md](../.docs/review/open-questions/experiments.md) Decision #6.

## Core Concepts

| Concept     | Description                                                                 |
|-------------|-----------------------------------------------------------------------------|
| **Process** | An ordered collection of Experiments.                                       |
| **Step**    | An individual Experiment within a Process (position in the sequence matters). |
| **Sample Assignment** | `ELNProcessSample`: **queued** on assign → **in_progress** when experiment starts → **queued** on next step after advance → **completed** on last step. Separate from `Sample.status` (e.g. Available for Testing). See Decision #24. |

### Process vs. Experiment

- An **Experiment** is a single unit of work (with entries, data, samples, details, etc.).
- A **Process** is the container and sequencer for multiple related Experiments.
- The same Experiment Template can potentially be used in multiple Processes.

## Current Implementation (Phase 1–3)

ELN Processes are first-class (distinct from LIMS run checklists). Definitions → instances (Decision #6); typed steps (Decision #1); sample journey (Decision #7).

| Layer | Detail |
|-------|--------|
| Tables | Definitions: `eln_process_definitions`, `eln_process_definition_steps`. Instances: `eln_processes`, `eln_process_steps`, `eln_process_samples`, `eln_process_step_lims_runs` (migrations `0047` + `0051`) |
| API | `/v1/eln-process-definitions`, `/v1/eln-processes`, `GET /v1/samples/{id}/journey` |
| Step kinds | `eln_experiment` (creates Experiment) · `lims_run` (lazy LimsRun + history; soft advance gates) |
| UI | `/experiments/processes` — Instances + Definitions tabs; start step; sample assign; journey panel. **Also:** Samples list (`/samples`) → select rows → **Assign to process** |
| Permission | Manage: `experiment:manage`. Journey: sample visibility (RLS) |
| Checklist | [`.docs/review/checklist/experiment-checklist.md`](../.docs/review/checklist/experiment-checklist.md) |

**Naming:** ELN uses `eln_*` prefixes and `/v1/eln-processes`. LIMS run checklists remain at `/v1/lims-runs/{id}/processes` and `/v1/processes/{id}` (tables `lims_run_checklists` / related).

**Legacy coexistence:**

- `ExperimentDetail` with `detail_type = "experiment_link"` still **coexists** with ELN Processes.
- Phase 1–2 ad hoc instances were backfilled to snapshot definitions in `0051`.

See [experiments.md](experiments.md) for `experiment_link` lineage and [checklist](../.docs/review/checklist/experiment-checklist.md) for remaining work.

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

### Starting work from a process (product target — product-target)

**Locked:** [open-questions Decision #24](../.docs/review/open-questions/experiments.md).

1. Open the **process** instance.  
2. Steps under an **accordion**.  
3. **Click** step/experiment to start → **start dialog opens** (not a permanent experiment-detail panel).  
4. **Dual list (primary; no barcode required):**
   - **Available:** process samples with **Sample.status = Available for Testing**  
   - **Selected:** empty → `<< < > >>` / search  
   - Optional scan only for eligible samples  
5. **Start** → create/start experiment instance + cohort; dialog **closes**.  
6. **Process sample rows** for selected samples: `status = in_progress`, `current_step_id = this step` (assign alone leaves them **queued**).  
7. Experiment detail shows cohort as **read-only** (no add-samples UI).  
8. **Advance** sample after a step → **queued** on next step, or **completed** if last step.

Nimble today: process assignment exists; cohort UI is still a standing panel on experiment detail without gates or process status updates.

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
- **LIMS Runs (LIMS)**: Kept separate. Processes are part of the ELN / experimental workflow layer.
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
- Keep Processes in the ELN domain (distinct from LIMS LIMS Runs).
- Allow flexibility: some labs may use simple single-experiment workflows; others will need rich multi-step processes.

## Open Questions

- Should Processes be able to contain both ELN Experiments and references to LIMS Runs?
- How should process-level status aggregate from the individual experiments/steps?
- Do we need versioning or templating of Processes themselves (reusable process definitions)?
- How do process steps interact with the new "Entries" model inside individual Experiments?
- What permissions model applies at the process level vs. individual experiment level?

---

**Related Documents**

- `.docs/internal/design/process-and-experiment-structural.md`
- `.docs/internal/design/gap-analysis-process-and-experiment.md`
- [experiments.md](experiments.md)
- [`lims-runs.md`](lims-runs.md)
- `.docs/internal/design/experiment-planning.md`
- [`.docs/review/checklist/experiment-rework-prerequisites.md`](../.docs/review/checklist/experiment-rework-prerequisites.md)
- [`workflow-accessioning-to-reporting.md`](workflow-accessioning-to-reporting.md) (for contrast with Workflow Templates)