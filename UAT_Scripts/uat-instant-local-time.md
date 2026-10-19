# UAT: instant timestamps in local time

Stem: `instant-local-time`

A LIMS run created at 7:23 PM US Eastern must not show Created 11:23 PM. The API sends instants as UTC with `Z`. The screen shows the browser's local time. Calendar dates stay lab days.

## Setup

- Lab timezone `America/New_York` (or the browser set to that zone).
- A user who can open runs, samples, tests, results, experiments, batches, and reagents.

## IT-1 LIMS run created time

1. Create a LIMS run in the evening, US Eastern (after 8:00 PM is the clearest case).
2. Open the run. **Created** shows that evening hour in local time, not the UTC hour.
3. In the network response, `created_at` ends in `Z` or `+00:00`. Example: 7:23 PM EDT is `…T23:23:00Z`, and the page shows 7:23 PM.

## IT-2 Other instant columns

On each of these, a created or updated time matches the local clock, and the JSON value has an offset:

- Samples list, Last Modified
- Tests list, Last Modified
- Results batch list, Created
- Experiments list, Started and Completed, and the experiment detail
- Runs list, Started and Created
- Batches detail, Created (Start Date and End Date stay calendar dates)
- Analyses, Analytes, Projects, Containers, Clients, Processes, experiment templates, workflow templates, lists admin
- Users, Last Login
- Dose-response Last fit. After a fit, `GET /v1/lims-runs/{id}/dose-response/summary` returns `last_fit_at` ending in `Z`, and the tab shows that instant in local time. With no fit, `last_fit_at` is null and the tab shows —.

## IT-3 Calendar dates do not shift

1. Receive a sample with received date today. The received date stays that calendar day. It does not move to yesterday in the evening.
2. Due date, test date, review date, result entry date, reagent Used on, and batch start and end dates stay the day that was entered.
3. With the lab zone `America/New_York` and the clock at 8 PM EDT on 2026-10-19, send `2026-10-20T00:00:00Z` as sample received or report, accession received, test test or review, `PATCH /tests/{id}/review`, result `entry_date` (POST, PATCH, and `POST /results/batch`), and batch start or end. Each stored value is naive `2026-10-19 00:00`, its day count is today, and GET of that row is **200**. `2026-10-19T23:30:00-04:00` stores the same lab day. `2026-10-21T00:00:00Z` and `2026-10-20T04:00:00Z` are lab tomorrow and are **422** on the future-checked fields. Batch start and end accept a later lab day. `2026-10-19` and `2026-10-19T00:00:00` stay `2026-10-19 00:00`.

## IT-4 Empty instants

A run that has not started shows Started as an em dash. A user who has never logged in shows Last Login as Never.
