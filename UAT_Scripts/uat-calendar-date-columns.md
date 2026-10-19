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
8. `GET` responses for those lab-day fields are `YYYY-MM-DD`, not `YYYY-MM-DDT00:00:00`. `POST /projects` stores `due_date` the same way `PATCH` does, for a date-only body and for an offset body.
9. A raw `INSERT` into `results` that omits `entry_date` stores today's date in the saved lab zone. A blank, NULL, or missing `lab_settings.timezone` raises `lab timezone not configured: set lab_settings.timezone`. There is no UTC fallback. `SET lims.as_of` / `SET lims.allow_as_of` as `lims_app` does not change the lab day. Downgrade of `0104` restores `CURRENT_DATE` and drops `public.current_lab_day()`.
10. After login with no saved zone, `/auth/me` has `timezone_configured=false`. A non-admin sees a blocking message that an administrator must set the lab timezone. An administrator is sent to the required setup step and saves a real IANA zone through `PATCH /v1/lab-settings`. An unknown name is **422** `invalid_timezone`.

Automated coverage: `backend/tests/test_calendar_date_columns.py`, `backend/tests/test_date_only_lab_day.py`, `backend/tests/test_batch_status_calendar.py`, `backend/tests/test_current_lab_day_default.py`, `backend/tests/test_lab_timezone.py`, `frontend/src/__tests__/localDate.test.ts`, `frontend/src/App.test.tsx`.
