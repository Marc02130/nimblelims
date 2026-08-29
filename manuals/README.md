# `manuals/` — review documentation

**Git how-tos:** [`/manuals/`](../../manuals/) ([`HOWTO.md`](../../manuals/HOWTO.md)). 

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
