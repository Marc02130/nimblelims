# `.docs/review/` — review documentation

**Reorg (2026-08-26):** Formerly `.docs-review/`. Parent index: [`.docs/README.md`](../README.md).

This tree is **review + process** only: stamps, tech sketches, cycle requirements, schema deltas, open-question logs, checklists, development-process. It does **not** host published operator manuals.

**Git how-tos:** [`/manuals/`](../../manuals/) ([`HOWTO.md`](../../manuals/HOWTO.md)).  
**Local legacy operator manuals (not on git):** `.docs/manuals/`.  
Umbrella PRD and domain PRDs/specs live under local `.docs/internal/` (not committed).

## Layout

| Directory | Purpose |
|-----------|---------|
| [`development-process/`](development-process/) | How we build |
| [`manuals/`](manuals/) | Pointer only — operator manuals left this tree |
| [`requirements/`](requirements/) | Cycle feature requirements |
| [`tech-sketch/`](tech-sketch/) | How before architecture/UI review |
| [`schema-changes/`](schema-changes/) | Per-cycle DB delta |
| [`checklist/`](checklist/) | Implementation checklists |
| [`open-questions/`](open-questions/) | Decision logs |
| `*-review/` | Formal review artifacts |

## Skills

Artifacts written by `/nimble-*-review` skills → this tree. Packet rules: `.grok/skills/nimble-reviews/PACKET.md`. Teams: `.grok/teams/`.
