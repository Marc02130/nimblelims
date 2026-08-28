# `.docs/` — NimbleLIMS documentation root

**Reorg (2026-08-26):** Former `.docs-review/` and `.docs-internal/` now live under this single root.

| Path | Former | Role |
|------|--------|------|
| [`.docs/review/`](review/) | `.docs-review/` | Review spine: stamps, sketches, cycle requirements, manuals, process, OQs |
| [`.docs/internal/`](internal/) | `.docs-internal/` | Working PRDs, specs, design, ideas, user stories, SOP packs, private |
| [`.docs/discussions/`](discussions/) | (from internal) | Multi-persona Leadership discussions |
| [`.docs/decision-logs/`](decision-logs/) | (from internal) | Short stamps (e.g. framework FW/WO) |

**Agents / skills:** Prefer these paths. Do not write new artifacts under the old `.docs-review/` or `.docs-internal/` names.

**Operator start here:** [review/README.md](review/) (receive freeze + asked-for lake) · [review/manuals/asked-for.md](review/manuals/asked-for.md)

**Teams:** See [`.grok/teams/README.md`](../.grok/teams/README.md) (Leadership / BA / Dev / QA / Docs).

**Framework SoT:** [decision-logs/framework-stamps-2026-08-26.md](decision-logs/framework-stamps-2026-08-26.md) · [discussions/2026-08-25-what-is-a-good-framework.md](discussions/2026-08-25-what-is-a-good-framework.md)

## Decision-logs vs open-questions

Two different trees. Do not merge them.

| Tree | Role |
|------|------|
| [`.docs/decision-logs/`](decision-logs/) | **Leadership stamps** — short decided locks (FW/WO, reorg, framework). Already decided. Committed. |
| [`.docs/review/open-questions/`](review/open-questions/) | **Cycle/feature gates** — open questions that block a packet/phase until **Decided**. Formal review process. Committed. |

**Rule:** a new Leadership lock (FW/WO/reorg) goes in `decision-logs/`. A packet that cannot start until questions are answered goes in `review/open-questions/`. When an OQ is Decided, leave it there as Decided (do not move it to decision-logs unless it is a cross-cutting Leadership stamp). When saying "fold into docs," name the tree: `review` / `internal` / `decision-logs` / `discussions`.
