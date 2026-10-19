# UAT: calendar columns are SQL date

Stem: `calendar-date-columns`. Migration `0100_calendar_dates` (revises `0099_batch_update_qualifiers`).

## Decision for Marc

A naive non-midnight timestamp is read as lab-zone wall time. `2026-10-19 02:00` is 2026-10-19, including in America/New_York.

That disagrees with the earlier reading that seeded `utcnow()` values are UTC wall time. Under that reading, `2026-10-19 02:00` is 22:00 on 2026-10-18 in America/New_York. The backfill does not use `((col AT TIME ZONE 'UTC') AT TIME ZONE lab_zone)::date`. Midnight and non-midnight rows both keep `col::date`. Downgrade writes midnight and does not restore the old clock time.

## Checks

1. After upgrade, `samples.received_date`, `samples.due_date`, `samples.report_date`, `samples.date_sampled`, `tests.test_date`, `tests.review_date`, `results.entry_date`, `projects.start_date`, `projects.due_date`, `batches.start_date`, and `batches.end_date` are SQL `date`.
2. A row stored as `2026-10-19 00:00:00` is `2026-10-19`. A row stored as `2026-10-19 02:00:00` is also `2026-10-19`.
3. Project create with `start_date` `2026-10-19T03:30:00Z` while the lab zone is America/New_York stores 2026-10-18. `due_date` `2026-10-21T00:00:00Z` stores 2026-10-20.
4. Completing every test through `POST /results/batch` sets `batches.end_date` to the lab's today, not the UTC date.
5. A QC sample created with a batch has `received_date` equal to the lab's today.
6. Batch and project forms submit `YYYY-MM-DD` from the picker. They do not call `toISOString()`.
7. Reagent `used_on` and lot dates stay SQL `date`. Instant columns are unchanged.

Automated coverage: `backend/tests/test_calendar_date_columns.py`, `backend/tests/test_date_only_lab_day.py`, `backend/tests/test_batch_status_calendar.py`, `frontend/src/__tests__/localDate.test.ts`.
