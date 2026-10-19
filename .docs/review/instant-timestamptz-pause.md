# Instant timestamptz migration — draft, brought up to main

Resumed 2026-10-19 after Marc's ordered UAT work. This pull request stays a draft until CI is green. It is not ready for review until that run passes.

## Where it is

- Branch: `cursor/instant-timestamptz-f27f` (kept pushed, no rebase, no force-push).
- Pull request: https://github.com/Marc02130/nimblelims/pull/191 — still a draft. Not closed. Not merged. Not marked ready.
- `origin/main` at `1d642b7` (merge of #197) is merged into this branch. That includes #196 (`7308594`).
- Feature commits already on the branch:
  - `c800270` Convert naive UTC instant columns to timestamptz (`USING col AT TIME ZONE 'UTC'` both ways).
  - `8da439c` Write server clocks as timezone-aware UTC, plus the naive-instant guard.
- The migration is `0100_instant_timestamptz`. It revises `0099_batch_update_qualifiers`.
- #195, #196, and #197 added no timestamp columns. `list_entries.code` is varchar. The batch probe is a function. The qualifier move changes list membership, not column types.
- Calendar columns stay `timestamp without time zone`. SQL `date` columns stay `date`.
- Views, materialized views, rules, and generated columns that depend on a converted column stop the migration. Indexes, defaults, triggers, and row level security policies stay.
- Batch status start and end writes from #197 stay lab-day calendar values. `modified_at` on that route is timezone-aware UTC.

## Revision chain

#197 landed on main as `0099_batch_update_qualifiers` while this branch still had `0099_instant_timestamptz`, both revising `0098_batch_access_status`. This branch is renumbered to `0100` so there is one head. Do not rebase.
