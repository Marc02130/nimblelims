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
| 1 | Can an ELN Process reference LIMS Runs (link/promote instrument steps)? | **Open** | Phase 3 (Run link / hybrid definitions) | Options under discussion — see below / chat. Phase 1–2: ELN templates only; no Run FK. Direction lean: typed process steps. | | | |
| 2 | Process status: own list vs strictly derived from steps? | **Decided (provisional)** | — | Optional `status_id` + seeded list `eln_process_status` (Draft, In Progress, On Hold, Completed, Cancelled). Not auto-derived yet. | 2026-07-11 | | Enough for MVP; derivation can be added later without schema break |
| 3 | Can a Process override or extend entry config from member templates? | **Decided (provisional)** | — | Phase 2: **No override.** Entries come only from ExperimentTemplate `template_definition.entries`. Process does not patch field sets. | 2026-07-11 | | Keeps one source of truth on templates |
| 4 | Write-back conflict rules when multiple steps/entries update the same Sample attribute | **Decided (provisional)** | — | **Last write wins.** Previous Sample value stored on `EntryFieldValue.write_back_previous`. Allowlist only (`SAMPLE_WRITE_BACK_COLUMNS`). | 2026-07-11 | | Simple, auditable enough for v1; stricter rules need product input |
| 5 | Workflow integration depth for Processes | **Decided (provisional)** | — | Phase 2 actions only: `create_process`, `add_step_to_process`, `assign_samples_to_process`, `instantiate_process_step`. No deep orchestration / gates. | 2026-07-11 | | Matches “new actions only” recommendation |
| 6 | Reusable Process definitions (first-class) — shape and when? | **Decided** | Phase 3 implementation of process definitions | See **Decision #6** below. Processes are **always defined** (first-class reusable definitions). Experiments remain ad hoc **or** template-based. | 2026-07-11 | Product | Product rule: multi-step work is governed by a definition; single experiments stay flexible |
| 7 | How is process progress / sample step surfaced to non-admin users? | **Decided** | Phase 3 journey UI | See **Decision #7** below. Progress is visible to anyone with access to the relevant samples; client isolation enforced (no cross-client progress). | 2026-07-11 | Product | Sample-scoped visibility, not manage-permission-only |
| 8 | Should instantiate-step auto-create ExperimentSampleExecution rows for process samples? | **Open** | Phase 3 polish / sample journey | — Phase 2: assign at process level only; step instantiate creates Experiment + entries, does not auto-link all process samples into the experiment | | | |
| 9 | Entry capture: who can edit values (experiment:manage only vs lab roles / status gates)? | **Open** | Hardening / multi-role UX | — Currently `experiment:manage` | | | |
| 10 | Deprecate or coexist long-term with `ExperimentDetail` `experiment_link` lineage? | **Open** | Phase 3 cleanup | — Phase 1–2: **coexist**; no forced migration | | | |

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

### Out of scope for this decision (still open)

- Whether a definition step may point at a **LIMS Run** template/path (**#1**).
- Who may browse definitions vs start instances (**#7**, **#9**).
- Versioning UI (publish v1/v2)—default assumption: snapshot instantiate; explicit versioning can follow.

### Rationale

- Multi-step lab work is SOP-driven; a definition is the unit of reuse and governance.
- Single experiments still need ad hoc flexibility (troubleshooting, one-offs).
- Matches CEO “orchestrate how we do work” without forcing every experiment through a template.
- Aligns mental model: **ExperimentTemplate → Experiment**, **ProcessDefinition → Process instance**.

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
| **3** Definitions + cross-system visibility | **Not started** | **#1** (and ideally #8, #10). **#6 and #7 Decided** |

---

## Phase 3 — resolve before implementation

Answer at least:

1. ~~**#6 Process definitions**~~ — **Decided**.
2. **#1 Process ↔ LIMS Runs** — see options explanation (typed steps lean); lock Decision #1.
3. ~~**#7 Visibility**~~ — **Decided** (sample-scoped; no cross-client).

Optional but valuable before Phase 3 code:

4. **#8** Auto sample-exec on step instantiate?
5. **#10** Lineage coexistence end-state?

---

## Related

- Checklist: [`.docs/checklist/experiment-checklist.md`](../checklist/experiment-checklist.md)
- Processes: [`.docs/processes.md`](../processes.md)
- Experiments (ELN): [`.docs/experiments.md`](../experiments.md)
- Runs (LIMS): [`.docs/lims-runs.md`](../lims-runs.md)
