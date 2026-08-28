# `.docs/decision-logs/` — Leadership stamps

Short **already-decided** locks (framework FW/WO, docs reorg, cross-cutting product stamps). Committed.

This tree is **not** the cycle/feature open-questions folder. Do not merge them.

## Decision-logs vs open-questions

| Tree | Role |
|------|------|
| [`.docs/decision-logs/`](./) | **Leadership stamps** — short decided locks (FW/WO, reorg, framework). Already decided. Committed. |
| [`.docs/review/open-questions/`](../review/open-questions/) | **Cycle/feature gates** — open questions that block a packet/phase until **Decided**. Formal review process. Committed. |

**Rule:** a new Leadership lock (FW/WO/reorg) goes in `decision-logs/`. A packet that cannot start until questions are answered goes in `review/open-questions/`. When an OQ is Decided, leave it there as Decided (do not move it to decision-logs unless it is a cross-cutting Leadership stamp). When saying "fold into docs," name the tree: `review` / `internal` / `decision-logs` / `discussions`.

Parent index: [`.docs/README.md`](../README.md). Discussions that produced stamps: [`.docs/discussions/`](../discussions/).

## Current stamps

| File | What it locks |
|------|----------------|
| [framework-stamps-2026-08-26.md](framework-stamps-2026-08-26.md) | FW-0–FW-2, WO-1–WO-7 (framework / work-order / intake) |
| [2026-08-26-docs-reorg-and-teams.md](2026-08-26-docs-reorg-and-teams.md) | Docs reorg (`.docs/review` · `.docs/internal`) + Grok teams |
| [2026-08-26-ar-multi-container.md](2026-08-26-ar-multi-container.md) | Atomic receive: 1..N containers in one transaction |
| [extract-hold-dual-map-kickback.md](extract-hold-dual-map-kickback.md) | Extract-hold dual-map kick-back (implement paused; OQ walk stamps) |
| [2026-08-28-analysis-param-defs.md](2026-08-28-analysis-param-defs.md) | Working note: `analysis_param_defs` catalog + example run-start snapshots (fold into internal PRD/SPEC; **not seed**) |
