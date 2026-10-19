# UAT: lab timezone has no fallback

Stem: `lab-timezone-no-fallback`. Migration `0105_lab_timezone_required` (revises `0104_current_lab_day`).

## Decision for Marc

There is no UTC or `America/New_York` default. A missing, blank, or NULL `lab_settings.timezone` fails. An administrator must save a real IANA zone before anyone else uses the app.

`public.current_lab_day()` uses `now()` only. A session cannot override the lab day with `SET lims.as_of` or `SET lims.allow_as_of`.

## Checks

1. `public.current_lab_day()` raises `lab timezone not configured: set lab_settings.timezone` when the setting is missing, blank, or NULL.
2. With `America/New_York`, a raw `INSERT` that omits `entry_date` stores today's date in that zone (the same day Python computes from `now()`).
3. As `lims_app`, `SET lims.allow_as_of = on` and `SET lims.as_of` do not change `current_lab_day()`.
4. `current_lab_day()` is owned by `lims_migrate` and is not `SECURITY DEFINER`.
5. `/auth/me` reports `timezone_configured=false` until an administrator saves a valid zone. A non-admin cannot `PATCH /v1/lab-settings`. An unknown name is **422** `invalid_timezone`.
6. After login with no zone, a non-admin sees the blocking message. An administrator is sent to the required setup step and cannot reach the rest of the app until the save succeeds.

Automated coverage: `backend/tests/test_current_lab_day_default.py`, `backend/tests/test_lab_timezone.py`, `frontend/src/App.test.tsx`.
