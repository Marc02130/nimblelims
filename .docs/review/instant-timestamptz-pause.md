# Instant timestamptz migration — draft, brought up to main

Resumed 2026-10-19 after Marc's ordered UAT work. This pull request stays a draft until CI is green. It is not ready for review until that run passes.

## Where it is

- Branch: `cursor/instant-timestamptz-f27f` (kept pushed, no rebase, no force-push).
- Pull request: https://github.com/Marc02130/nimblelims/pull/191 — still a draft. Not closed. Not merged. Not marked ready.
- `origin/main` at `7308594` (merge of #196) is merged into this branch.
- Feature commits already on the branch:
  - `c800270` Convert naive UTC instant columns to timestamptz (`USING col AT TIME ZONE 'UTC'` both ways).
  - `8da439c` Write server clocks as timezone-aware UTC, plus the naive-instant guard.
- The migration is now `0099_instant_timestamptz`. It revises `0098_batch_access_status`.
- #195 (`0097_list_entry_code`) and #196 (`0098_batch_access_status`) added no timestamp columns. `list_entries.code` is varchar. The batch probe is a function, not a column.
- Calendar columns stay `timestamp without time zone`. SQL `date` columns stay `date`.
- Views, materialized views, rules, and generated columns that depend on a converted column stop the migration. Indexes, defaults, triggers, and row level security policies stay.

## Two Alembic heads until one pull request merges

#197 (`0099_batch_update_qualifiers`) also revises `0098_batch_access_status` and is not on main. The revision ids differ, so the strings do not collide, but both branches are heads off `0098`. Whichever merges second has to be renumbered onto the new head. Do not rebase this branch to fix that.
