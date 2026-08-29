# `.docs/review/` — review documentation

**Reorg (2026-08-26):** Formerly `.docs-review/`. Parent index: [`.docs/README.md`](../README.md).

This tree is **review + process** only: stamps, tech sketches, cycle requirements, schema deltas, open-question logs, checklists, development-process. 

## Start here (operator)

Spine packet (P2–P5 specified, **not** this P1 stamp): [requirements/post-receive-work-spine.md](requirements/post-receive-work-spine.md) · [tech-sketch/post-receive-work-spine.md](tech-sketch/post-receive-work-spine.md). UAT: `UAT_Scripts/uat-post-receive-work-spine.md` (hold merge until pass).

Do **not** document Route / work_orders / WO-7 as shipped in P1. Do **not** put `analysis_param_defs` on receive.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`development-process/`](development-process/) | How we build |
| [`requirements/`](requirements/) | Cycle feature requirements |
| [`tech-sketch/`](tech-sketch/) | How before architecture/UI review |
| [`schema-changes/`](schema-changes/) | Per-cycle DB delta |
| [`checklist/`](checklist/) | Implementation checklists |
| [`open-questions/`](open-questions/) | Decision logs |
| `*-review/` | Formal review artifacts (includes [`docs-review/`](docs-review/)) |

## Skills

Artifacts written by `/nimble-*-review` skills → this tree. Packet rules: `.grok/skills/nimble-reviews/PACKET.md`. Teams: `.grok/teams/`.
