# UAT: instant columns are timestamptz

Stack: migration `0102_instant_timestamptz` after `0101_revoke_probe_execute`.

## What changed

- Instant columns (`created_at`, `modified_at`, `started_at`, `last_login`, and the rest of the audit clocks) are `timestamptz`.
- A stored UTC wall time does not shift. `2020-01-15 19:23:00` naive becomes `2020-01-15 19:23:00+00`.
- Lab days are SQL `date` (from `0100_calendar_dates`, after #198): `samples.received_date`, `samples.due_date`, `samples.report_date`, `samples.date_sampled`, `tests.test_date`, `tests.review_date`, `results.entry_date`, `projects.start_date`, `projects.due_date`, `batches.start_date`, `batches.end_date`.
- Reagent `used_on` and lot dates stay SQL `date`. Custom-attribute JSON is unchanged.
- API instants still end in `Z`. Screens still show them in the browser's local time.

## Automated checks

These run in pytest (`backend/tests/test_instant_timestamptz.py`) and in CI (`python backend/checks/naive_instants.py`):

1. Row counts of every public table match before the upgrade, after the upgrade, after downgrade, and after the second upgrade.
2. `users.last_login`, `samples.created_at`, `lims_runs.started_at`, and `results.created_at` round-trip to the same UTC instant.
3. `samples.received_date` and `results.entry_date` stay the SQL `date` `2020-01-15`.
4. `samples` triggers, indexes, row level security policies, and the `users.created_at` default are still present. Nothing is dropped.
5. A new naive `DateTime` column that is not in the calendar list fails the model check.
6. `datetime.utcnow()` or `datetime.now()` with no timezone in server code fails the source check. The same check catches `datetime.datetime.now()`, `datetime.datetime.utcnow()`, `from datetime import datetime as dt`, and `import datetime as d`.

## Bench spot check

1. Open a LIMS run created before this migration. Created time is the same local time as before, not shifted by the lab's offset.
2. A sample received date is the same calendar day as before.
3. Create a run. The API `created_at` ends with `Z`. The page shows that instant in the browser's local time.
