# UAT: batch update, status dates, whole-run fits, qualifier lists

Stem: `batch-update-qualifiers`. Migration `0099_batch_update_qualifiers` (revises `0098_batch_access_status`).

SCORE.md from the UAT on `9895daf` was not in the repository. The steps below follow Marc's written order.

## Roles that receive `batch:update`

Administrator, Lab Manager, and Lab Technician. Those are the seeded roles that already have `batch:manage`.

Client and Configuration Editor do not receive `batch:update`. `batch:delete` is not granted.

## TC-BATCH-UPDATE-001 — status writes a lab day

1. Sign in as `lab-manager` (or `admin`).
2. Open a batch and set its status to the `batch_status` entry named **In Process**.
3. `start_date` is midnight of the lab's calendar day. `end_date` is unchanged.
4. Set the status to **Completed**. `end_date` is midnight of that same lab day. `start_date` stays.
5. A status entry that is not on `batch_status` does not write either date.

## TC-FIT-001 — one live fit per compound

1. Fit a run that has two compounds.
2. Fit the whole run again (no single-compound filter).
3. Each compound has one result with `superseded_by` empty. The earlier rows point at that result.

## TC-QUAL-001 — one qualifier list

1. `GET /lists/result_qualifiers/entries` includes `<LOD`, `ND`, and `Normal`.
2. The list named `Result Qualifiers` is inactive.
3. A result that already pointed at `<LOD` still points at the same entry id.

## Dev reagent uses — operator step, not CI

Do not run this in CI. It was not run against the dev database when this change was added. There were no row ids in the repo, so the script selects active `reagent_uses` with `used_on = 2026-10-28` and expects exactly four.

Dry run (prints the rows, writes nothing). Export `LIMS_APP_PASSWORD` first; the shell expands it in the URL:

```bash
export LIMS_APP_PASSWORD
cd backend
DATABASE_URL="postgresql://lims_app:${LIMS_APP_PASSWORD}@localhost:5432/lims_db" \
  python scripts/neutralize_dev_reagent_uses.py
```

Apply, only after the dry run shows those four rows on the dev database. Export `LIMS_APP_PASSWORD` first:

```bash
export LIMS_APP_PASSWORD
cd backend
DATABASE_URL="postgresql://lims_app:${LIMS_APP_PASSWORD}@localhost:5432/lims_db" \
  python scripts/neutralize_dev_reagent_uses.py --apply
```

Replace `DATABASE_URL` if the dev database is not the local Compose database. `--apply` sets `active` false, sets `quantity_used` to 0, and adds the quantity back when the lot's `quantity_remaining` is not null. A second apply exits 0 and writes nothing. If the count is not 4, the script refuses unless `--allow-count` is passed.

## Not run here

The command above is the test that cannot run in this environment: this agent cannot reach the dev database.
