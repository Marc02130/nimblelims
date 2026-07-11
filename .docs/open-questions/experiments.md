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
| 1 | Can an ELN Process reference LIMS Experiment Runs (link/promote instrument steps)? | **Open** | Phase 3 (Run link / sample journey) | — Phase 1–2: ELN templates only; no Run FK | | | |
| 2 | Process status: own list vs strictly derived from steps? | **Decided (provisional)** | — | Optional `status_id` + seeded list `eln_process_status` (Draft, In Progress, On Hold, Completed, Cancelled). Not auto-derived yet. | 2026-07-11 | | Enough for MVP; derivation can be added later without schema break |
| 3 | Can a Process override or extend entry config from member templates? | **Decided (provisional)** | — | Phase 2: **No override.** Entries come only from ExperimentTemplate `template_definition.entries`. Process does not patch field sets. | 2026-07-11 | | Keeps one source of truth on templates |
| 4 | Write-back conflict rules when multiple steps/entries update the same Sample attribute | **Decided (provisional)** | — | **Last write wins.** Previous Sample value stored on `EntryFieldValue.write_back_previous`. Allowlist only (`SAMPLE_WRITE_BACK_COLUMNS`). | 2026-07-11 | | Simple, auditable enough for v1; stricter rules need product input |
| 5 | Workflow integration depth for Processes | **Decided (provisional)** | — | Phase 2 actions only: `create_process`, `add_step_to_process`, `assign_samples_to_process`, `instantiate_process_step`. No deep orchestration / gates. | 2026-07-11 | | Matches “new actions only” recommendation |
| 6 | Reusable Process Templates — when? | **Open** | Phase 3 (Process Templates) | — Reviews lean Phase 3 | | | |
| 7 | How is process progress / sample step surfaced to non-admin users? | **Open** | Phase 3 (journey UI / reporting) | — Phase 2: manage UI requires `experiment:manage` only | | | |
| 8 | Should instantiate-step auto-create ExperimentSampleExecution rows for process samples? | **Open** | Phase 3 polish / sample journey | — Phase 2: assign at process level only; step instantiate creates Experiment + entries, does not auto-link all process samples into the experiment | | | |
| 9 | Entry capture: who can edit values (experiment:manage only vs lab roles / status gates)? | **Open** | Hardening / multi-role UX | — Currently `experiment:manage` | | | |
| 10 | Deprecate or coexist long-term with `ExperimentDetail` `experiment_link` lineage? | **Open** | Phase 3 cleanup | — Phase 1–2: **coexist**; no forced migration | | | |

---

## Phase gate summary

| Phase | Scope (summary) | Open blockers before coding |
|-------|-----------------|----------------------------|
| **1** Process MVP | Done | None remaining |
| **2** Entries + Process UI | Done (API + Process UI + entry capture) | None remaining for shipped slice; Q4/Q5 provisional OK |
| **3** Templates + cross-system visibility | **Not started** | **#1, #6, #7** (and ideally #8, #10) |

---

## Phase 3 — resolve before implementation

Answer at least:

1. **#6 Process Templates** — Yes/no for Phase 3; if yes: instance-only clone vs first-class `process_templates` table?
2. **#1 Process ↔ Runs** — Link only (FK/junction), promote results, or stay strictly separate with a read-only journey view?
3. **#7 Visibility** — Who sees process/sample position (all lab roles, project members, clients)?

Optional but valuable before Phase 3 code:

4. **#8** Auto sample-exec on step instantiate?
5. **#10** Lineage coexistence end-state?

---

## Related

- Checklist: [`.docs/checklist/experiment-checklist.md`](../checklist/experiment-checklist.md)
- Processes: [`.docs/processes.md`](../processes.md)
- Experiments (ELN): [`.docs/experiments.md`](../experiments.md)
- Runs (LIMS): [`.docs/experiment-runs.md`](../experiment-runs.md)
