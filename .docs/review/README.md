# `.docs/review/` — review documentation

**Reorg (2026-08-26):** Formerly `.docs-review/`. Parent index: [`.docs/README.md`](../README.md).

This tree is **review + manuals + process** only: stamps, tech sketches, cycle requirements, schema deltas, open-question logs, checklists, development-process, operator manuals.

Umbrella PRD and domain PRDs/specs live under [`.docs/internal/`](../internal/).

## Start here (operator)

| Path | Role |
|------|--------|
| [manuals/atomic-receive.md](manuals/atomic-receive.md) | CORE receive (`/receive`). Non-empty `analysis_ids` → **422**. Zero Tests. |
| [manuals/asked-for.md](manuals/asked-for.md) | **P1 lake:** after receive, record **requested analysis**. Does **not** assign a Test or start work. |
| [manuals/accessioning-workflow.md](manuals/accessioning-workflow.md) | Wizard removed; `/accessioning` redirects to `/receive`. |
| [manuals/navigation.md](manuals/navigation.md) | Sidebar: Receive → **Asked-for** → Samples → Tests … |
| [manuals/api-endpoints.md](manuals/api-endpoints.md) | `POST /samples/receive` freeze + `POST /v1/asked-for` |
| [manuals/processes.md](manuals/processes.md) | Process start is **not** asked-for. |
| [manuals/lims-runs.md](manuals/lims-runs.md) | Params freeze at LimsRun start (later stamp), **not** on receive. |

Spine packet (P2–P5 specified, **not** this P1 stamp): [requirements/post-receive-work-spine.md](requirements/post-receive-work-spine.md) · [tech-sketch/post-receive-work-spine.md](tech-sketch/post-receive-work-spine.md). UAT: `UAT_Scripts/uat-post-receive-work-spine.md` (hold merge until pass).

Do **not** document Route / work_orders / WO-7 as shipped in P1. Do **not** put `analysis_param_defs` on receive.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`development-process/`](development-process/) | How we build |
| [`manuals/`](manuals/) | Operator handbooks |
| [`requirements/`](requirements/) | Cycle feature requirements |
| [`tech-sketch/`](tech-sketch/) | How before architecture/UI review |
| [`schema-changes/`](schema-changes/) | Per-cycle DB delta |
| [`checklist/`](checklist/) | Implementation checklists |
| [`open-questions/`](open-questions/) | Decision logs |
| `*-review/` | Formal review artifacts (includes [`docs-review/`](docs-review/)) |

## Skills

Artifacts written by `/nimble-*-review` skills → this tree. Packet rules: `.grok/skills/nimble-reviews/PACKET.md`. Teams: `.grok/teams/`.
