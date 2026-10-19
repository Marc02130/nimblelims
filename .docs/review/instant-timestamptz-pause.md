# Instant timestamptz migration — paused

Paused 2026-10-19 before review. Do not continue this work until Marc says to.

## Where it stopped

- Branch: `cursor/instant-timestamptz-f27f` (kept pushed).
- Head when paused: `34affe0` (merge of `origin/main` at `7334b8c` / #190 into the timestamptz commits).
- Feature commits already on the branch:
  - `c800270` Convert naive UTC instant columns to timestamptz (`0097_instant_timestamptz`, `USING col AT TIME ZONE 'UTC'` both ways).
  - `8da439c` Write server clocks as timezone-aware UTC, plus the naive-instant guard.
- Pull request: https://github.com/Marc02130/nimblelims/pull/191 — opened, then marked draft. Not closed. Not merged.
- Local pytest before the main merge: 1090 passed. The merge added no code conflicts. CI on #191 was not confirmed green when this pause started.
- A later date-only lab-day fix (#189 UAT round 29) is a separate branch off `main`. It is not part of this migration.
