# Instant timestamptz migration — draft, brought up to main

Resumed 2026-10-19 after Marc's ordered UAT work. This pull request stays a draft until CI is green. It is not ready for review until that run passes.

## Where it is

- Branch: `cursor/instant-timestamptz-f27f` (kept pushed, no rebase, no force-push).
- Pull request: https://github.com/Marc02130/nimblelims/pull/191 — still a draft. Not closed. Not merged. Not marked ready.
- `origin/main` at `bc2b341` (merge of #198) is merged into this branch. The probe-revoke branch is merged as well so this chain can run. That pull request must merge before this one. Until it does, this diff includes its commits.
- Feature commits already on the branch:
  - `c800270` Convert naive UTC instant columns to timestamptz (`USING col AT TIME ZONE 'UTC'` both ways).
  - `8da439c` Write server clocks as timezone-aware UTC, plus the naive-instant guard.
- The migration is `0102_instant_timestamptz`. It revises `0101_revoke_probe_execute`.
- #195, #196, and #197 added no timestamp columns. `list_entries.code` is varchar. The batch probe is a function. The qualifier move changes list membership, not column types.
- Calendar columns are SQL `date` from `0100_calendar_dates`. Reagent SQL `date` columns stay `date`.
- Views, materialized views, rules, and generated columns that depend on a converted column stop the migration. Indexes, defaults, triggers, and row level security policies stay.
- Batch status start and end writes from #197 stay lab-day calendar values. `modified_at` on that route is timezone-aware UTC.

## Revision chain

The chain is `0100_calendar_dates` → `0101_revoke_probe_execute` → `0102_instant_timestamptz`. One Alembic head. Do not rebase.
