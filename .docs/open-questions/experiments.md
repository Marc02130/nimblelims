# Open Questions — Experiments / Processes / Entries

**Status:** Living decision log  
**Checklist:** [`.docs/checklist/experiment-checklist.md`](../checklist/experiment-checklist.md)  
**Requirements:** [`.docs/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md)

## Gate rule

**Do not start a new phase (or a major feature within a phase) until every open question marked as blocking that work is resolved and recorded here.**

- Provisional answers used to ship earlier work must be labeled **Decided (provisional)** or **Decided**.
- Implementation may proceed only against **Decided** rows for the scope being built.
- New questions discovered mid-implementation are added here; if they block the current slice, pause coding and resolve them first.

See also: `AGENTS.md` → *Open questions gate*.

---

## How to use this doc

| Status | Meaning |
|--------|---------|
| **Open** | No product/eng decision yet — blocks related work |
| **Decided (provisional)** | Shipped with a temporary rule; revisit before next major expansion |
| **Decided** | Locked for current roadmap |
| **Deferred** | Explicitly out of scope until named phase |

When resolving: fill **Decision**, **Date**, **Owner**, and one line of **Rationale**. Move any checklist note to match.

---

## Questions

| # | Question | Status | Blocks | Decision | Date | Owner | Rationale |
|---|----------|--------|--------|----------|------|-------|-----------|
| 1 | Can an ELN Process reference LIMS Runs (link/promote instrument steps)? | **Decided** | Phase 3 hybrid definitions | See **Decision #1** below. **Option C** typed process steps in Phase 3 v1 (**1h-A**); defaults 1a–1g. | 2026-07-11 | Product | Real SOPs mix notebook + instrument steps |
| 2 | Process status: own list vs strictly derived from steps? | **Decided (provisional)** | — | Optional `status_id` + seeded list `eln_process_status` (Draft, In Progress, On Hold, Completed, Cancelled). Not auto-derived yet. | 2026-07-11 | | Enough for MVP; derivation can be added later without schema break |
| 3 | Can a Process override or extend entry config from member templates? | **Decided (provisional)** | — | Phase 2: **No override.** Entries come only from ExperimentTemplate `template_definition.entries`. Process does not patch field sets. | 2026-07-11 | | Keeps one source of truth on templates |
| 4 | Write-back conflict rules when multiple steps/entries update the same Sample attribute | **Decided (provisional)** | — | **Last write wins.** Previous Sample value stored on `EntryFieldValue.write_back_previous`. Allowlist only (`SAMPLE_WRITE_BACK_COLUMNS`). | 2026-07-11 | | Simple, auditable enough for v1; stricter rules need product input |
| 5 | Workflow integration depth for Processes | **Decided (provisional)** | — | Phase 2 actions only: `create_process`, `add_step_to_process`, `assign_samples_to_process`, `instantiate_process_step`. No deep orchestration / gates. | 2026-07-11 | | Matches “new actions only” recommendation |
| 6 | Reusable Process definitions (first-class) — shape and when? | **Decided** | Phase 3 implementation of process definitions | See **Decision #6** below. Processes are **always defined** (first-class reusable definitions). Experiments remain ad hoc **or** template-based. | 2026-07-11 | Product | Product rule: multi-step work is governed by a definition; single experiments stay flexible |
| 7 | How is process progress / sample step surfaced to non-admin users? | **Decided** | Phase 3 journey UI | See **Decision #7** below. Progress is visible to anyone with access to the relevant samples; client isolation enforced (no cross-client progress). | 2026-07-11 | Product | Sample-scoped visibility, not manage-permission-only |
| 8 | Should instantiate-step auto-create ExperimentSampleExecution rows for process samples? | **Open** | Phase 3 polish / sample journey | — Phase 2: assign at process level only; step instantiate creates Experiment + entries, does not auto-link all process samples into the experiment | | | |
| 9 | Entry capture: who can edit values (experiment:manage only vs lab roles / status gates)? | **Decided** | Hardening / multi-role UX | See **Decision #9** below. **Lab personnel only** edit experimental / entry data. Clients do **not** edit lab data; if client ordering ships later, clients may **create orders** only. | 2026-07-11 | Product | Lab SoT for data integrity; ordering is a separate client capability |
| 10 | Deprecate or coexist long-term with `ExperimentDetail` `experiment_link` lineage? | **Open** | Lineage cleanup (not Phase 3) | — Phase 1–3: **coexist** with ELN Processes. See explanation under **#10 notes** below. | | | |

---

## Decision #6 — Processes are defined; Experiments may be ad hoc

**Status:** Decided  
**Date:** 2026-07-11

### Product rule

| Entity | Definition model |
|--------|------------------|
| **Experiment** | **Ad hoc** *or* **from ExperimentTemplate** (unchanged). Single units of work stay flexible. |
| **Process** | **Always defined.** No free-form “blank process” as the long-term model. A running process is an **instance** of a first-class reusable **process definition** (template). |

Wording used by product: processes are first-class and re-usable; experiments can be ad hoc or defined (templates); **processes will be defined**.

### Chosen shape (implementation target)

**First-class process definitions** (not “clone only,” not soft-flag on instance, not Workflow-as-template-only):

| Concept | Role |
|---------|------|
| **Process definition** (name TBD in schema: e.g. `eln_process_templates` / `eln_process_definitions`) | Reusable protocol: ordered steps, each step → `experiment_template_id` (+ label/metadata). Library of multi-step SOPs. |
| **Process instance** (`eln_processes` today) | One execution of a definition for a cohort of samples / time window. Created **from** a definition. |
| **Snapshot on instantiate** | Instance steps copy the definition’s step list at create time; later definition edits do not rewrite in-flight instances. |

### Implications for current Phase 1–2 code

What shipped today allows **ad hoc** process create (name + pick templates) without a parent definition. That is **provisional** and **not** the end state.

| Phase 1–2 (provisional) | Target (this decision) |
|-------------------------|-------------------------|
| `POST /v1/eln-processes` with free-form steps | Create **process definition** first; instantiate instances from it |
| Process UI “New process” builds instance from scratch | UI: manage **definitions** + **start process from definition** |
| No `process_template_id` / definition FK on instance | Instance **requires** definition FK (or migrate legacy ad hoc rows) |

**Migration approach (when Phase 3 builds this):**

1. Add process definition tables + APIs + UI.
2. Add optional then required `process_definition_id` (name TBD) on `eln_processes`.
3. One-time: for any ad hoc instances, auto-create a definition snapshot (“Legacy: {name}”) or mark `definition_id` nullable only for pre-cutover rows.
4. Disable free-form instance create in API/UI after cutover (or keep admin-only escape hatch—product can tighten later).

### Out of scope for this decision (resolved elsewhere / later)

- Definition steps may be LIMS Runs: **yes** — see **Decision #1**.
- Who sees progress: **Decision #7**. Who may edit entries: **#9** still open.
- Versioning UI (publish v1/v2)—default assumption: snapshot instantiate; explicit versioning can follow.

### Rationale

- Multi-step lab work is SOP-driven; a definition is the unit of reuse and governance.
- Single experiments still need ad hoc flexibility (troubleshooting, one-offs).
- Matches CEO “orchestrate how we do work” without forcing every experiment through a template.
- Aligns mental model: **ExperimentTemplate → Experiment**, **ProcessDefinition → Process instance**.

---

## Decision #1 — Typed process steps (Option C) in Phase 3 v1

**Status:** Decided  
**Date:** 2026-07-11

### Product rule

ELN **process definitions** may include steps that materialize either:

| `step_kind` | Materializes | Notes |
|-------------|--------------|--------|
| `eln_experiment` | ELN **Experiment** (+ entries from template) | Notebook / manual / structured entry work |
| `lims_run` | **LimsRun** | Instrument / CRO assay; data stays on the run |

**Not chosen:** journey-only (A), soft-link-only (B), hard containment (D), merge Experiment+LimsRun (E).

### Sequencing (**1h-A**)

Phase 3 **first definition release** includes **full hybrid typed steps** (both kinds).  
Not “ELN-only definitions first, Runs later.” Schema and UI designed for polymorphism from the start.

### Locked defaults (1a–1g)

| ID | Decision |
|----|----------|
| **1a** | Only two step kinds: `eln_experiment` \| `lims_run` |
| **1b** | Step stores `experiment_template_id` + **required `execution_mode`** (do not infer mode from template alone) |
| **1c** | **Lazy** LimsRun create — placeholder until “Start step” (not eager create of all runs at process start) |
| **1d** | **Current run + history** per step instance (retest/refit); not single immutable run forever |
| **1e** | Run samples should be a **subset of process cohort** when linked; plate subset OK; validate where practical |
| **1f** | **Soft** advance warnings if Run not complete/published (hard gates later if needed) |
| **1g** | **LimsRun remains source of truth** for instrument data; no auto-promote to Entry/Sample in v1 |

### Distinct from run-internal checklists

| Entity | Role |
|--------|------|
| ELN process definition / instance steps | Pipeline across experiments **and** LimsRuns |
| `lims_run_checklists` / `lims_run_checklist_steps` | Checklist **inside** one LimsRun (unchanged) |

### Implementation notes (Phase 3)

1. Process definition steps: `step_kind`, `experiment_template_id`, `execution_mode`, sort_order, label.
2. Instance steps: snapshot of definition; for `lims_run`, track `current_lims_run_id` + history junction/table.
3. “Start step”: branch create Experiment vs create LimsRun (lazy for runs).
4. Sample journey (#7): surface step kind + status for samples the viewer can access.
5. Promote/write-back from Run → later phase if needed.

### Rationale

- Real protocols mix notebook and instrument work; definitions must encode both.
- Lazy create avoids noisy draft/ordered runs for unstarted steps.
- Soft gates reduce false progress without blocking early adoption.
- Keeping instrument SoT on LimsRun avoids dual-write drift with Entries.

---

## Decision #7 — Progress visibility is sample-scoped

**Status:** Decided  
**Date:** 2026-07-11

### Product rule

| Actor | Can see process / sample progress? |
|-------|-------------------------------------|
| **Anyone with access to the sample(s)** | **Yes** — progress for those samples (which process, which step, status) |
| **Other clients’ orgs** | **No** — client isolation (same as samples / RLS) |
| **Users without sample access** | **No** — not a global “all processes” feed for everyone |

Not limited to `experiment:manage`. Lab techs, managers, and **clients** see journey/progress for **their** samples only.

### Implementation implications (Phase 3 journey)

- Journey/progress APIs filter by sample visibility (project/client RLS), not only `experiment:manage`.
- Manage actions (create definition, start process, advance samples, edit entries) stay gated by write permissions (today `experiment:manage`; refine with #9 later).
- Client users: read-only progress on samples they can already see; never another client’s processes.

### Rationale

- “Where is my sample?” is the product value; hiding it behind manage roles breaks the journey.
- Multi-tenant safety stays non-negotiable: sample access already encodes client boundaries.

---

## Phase gate summary

| Phase | Scope (summary) | Open blockers before coding |
|-------|-----------------|----------------------------|
| **1** Process MVP | Done | None remaining |
| **2** Entries + Process UI | Done (API + Process UI + entry capture) | None remaining for shipped slice; Q4/Q5 provisional OK |
| **3** Definitions + hybrid steps + journey | **Ready to start** | **#1, #6, #7 Decided.** #8 / #9 / #10 optional polish — do not block definition + typed-step v1 |

---

## Phase 3 — status

| Decision | Status |
|----------|--------|
| **#6** Process definitions first-class | **Decided** |
| **#1** Typed steps (C) + 1a–1g + **1h-A** hybrid in v1 | **Decided** |
| **#7** Sample-scoped progress visibility | **Decided** |

**Phase 3 status:** shipped (definitions, typed steps, journey). Remaining open polish:

- **#8** Auto sample-exec on step instantiate  
- **#10** Lineage coexistence end-state (`experiment_link` vs Processes)

---

## Decision #9 — Lab personnel edit data; lab clients do not (orders later)

**Status:** Decided  
**Date:** 2026-07-11

### Terminology

**Client** = customer of the **lab** (e.g. environmental lab’s industrial customer; CRO’s sponsor). Not “SaaS tenant of the NimbleLIMS vendor.” Lab deployments (on-prem or hosted) still isolate **lab clients** from each other via `client_id` / project RLS—required for multi-client labs and CROs.

### Product rule

| Actor | Edit experimental data (entries, results, process capture)? | Other |
|-------|------------------------------------------------------------|--------|
| **Lab personnel** (admin, lab manager, lab tech — System client / lab roles) | **Yes** | Manage processes/experiments per existing RBAC (`experiment:manage` today for process/entry APIs) |
| **Lab client users** (sponsor / customer org logins) | **No** — never edit lab/entry/sample experimental data | May later **create orders** if/when client ordering is enabled (ordering ≠ editing lab data); may view **their** sample journey (#7) |

### Implementation implications

- Entry value upsert, write-back, process step start/advance, and similar **data mutation** stay lab-side.
- Do not grant clients `experiment:manage` (or equivalent) for entry capture as a shortcut.
- Future **client ordering** is a separate feature surface (create order / request work), not opening entry grids to clients.
- Refine which lab roles get `experiment:manage` vs narrower “entry:write” later if needed — still **lab only**.

### Rationale

- Lab remains source of truth for measured/captured data.
- Clients need visibility of progress (#7) and may need to place work requests later, without contaminating lab SoT.

---

## #10 notes — What is `experiment_link`?

**Not a separate table.** It is a **usage of** `ExperimentDetail`:

| Piece | Role |
|-------|------|
| Table | `experiment_details` (`ExperimentDetail` model) |
| `detail_type` | `"experiment_link"` |
| `content` (JSONB) | e.g. `{ "linked_experiment_id": "<uuid>" }` |
| API | `POST .../link` / workflow action `link_experiments` |
| Lineage | `get_experiment_lineage` walks details with this type and collects linked experiment IDs |

### How it works (pre-Process model)

Before first-class **ELN Processes**, multi-experiment chaining was a **linked list of detail rows**:

```
Experiment A  --(detail experiment_link)-->  Experiment B  --(detail)-->  Experiment C
```

- No process entity, no ordered process steps, no process-level sample assignment.
- No hard gates (“B cannot start until A completes”).
- Scientist / workflow wires the chain manually.

### How Processes relate

| Old (`experiment_link`) | New (ELN Process) |
|-------------------------|-------------------|
| Ad hoc link between two experiments | Ordered steps on a process definition/instance |
| Stored as free-form detail JSONB | First-class `eln_process_steps` (+ typed LimsRun steps) |
| Lineage UI on experiment detail | Process UI + sample journey |

**Current policy (Phases 1–3):** **coexist** — Process is the preferred multi-step model; `experiment_link` still works for simple A→B links and is not force-migrated.

**#10 remains Open** until product chooses: keep forever as lightweight A→B, or deprecate after Processes cover lineage fully.

---

## Related

- Checklist: [`.docs/checklist/experiment-checklist.md`](../checklist/experiment-checklist.md)
- Processes: [`.docs/manuals/processes.md`](../manuals/processes.md)
- Experiments (ELN): [`.docs/manuals/experiments.md`](../manuals/experiments.md)
- Runs (LIMS): [`.docs/manuals/lims-runs.md`](../manuals/lims-runs.md)
