# `manuals/` — operator documentation

Git-tracked how-tos. Start with [HOWTO.md](HOWTO.md). Vendor PDFs stay out (`/manuals/**/*.pdf` is gitignored).

Review stamps stay under [`.docs/review/`](../.docs/review/). Local scratch copies of old trees: `.docs/manuals/` (gitignored, not these files).

## Start here

| Path | Role |
|------|------|
| [HOWTO.md](HOWTO.md) | Lab path: receive ≠ order ≠ work. Receive loop (stay on `/receive`); requested analysis is a later look-up; route / execute / results are later packets |
| [atomic-receive.md](atomic-receive.md) | CORE receive (`/receive`). Non-empty `analysis_ids` → **422**. Zero Tests. |
| [asked-for.md](asked-for.md) | P1 lake: a **later look-up** that records **requested analysis + TAT** for already-received samples. Does **not** assign a Test or start work. |
| [accessioning-workflow.md](accessioning-workflow.md) | Wizard removed; `/accessioning` redirects to `/receive`. |
| [navigation.md](navigation.md) | Sidebar order: Receive, **Asked-for**, Samples, Tests … (nav order only — not a work queue) |
| [api-endpoints.md](api-endpoints.md) | `POST /samples/receive` freeze + `POST /v1/asked-for` |

## Domain handbooks

| Path | Role |
|------|------|
| [dev-setup.md](dev-setup.md) | Local / Docker setup |
| [admin-setup.md](admin-setup.md) | First login, password, admin |
| [backend-auth.md](backend-auth.md) | JWT, RBAC, CSRF |
| [ids-and-configuration.md](ids-and-configuration.md) | Name templates, sequences, lists |
| [lists.md](lists.md) | Lists and list entries |
| [containers.md](containers.md) | Container types, contents, inventory |
| [batches.md](batches.md) | Batches |
| [processes.md](processes.md) | ELN processes (not asked-for) |
| [experiments.md](experiments.md) | Experiments |
| [lims-runs.md](lims-runs.md) | LIMS Runs; params freeze at start (later), not on receive |
| [workflow-accessioning-to-reporting.md](workflow-accessioning-to-reporting.md) | End-to-end workflow |
| [useful-command-line.md](useful-command-line.md) | CLI notes |
