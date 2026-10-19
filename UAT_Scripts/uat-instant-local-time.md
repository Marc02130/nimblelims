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
- Dose-response last fit, when a fit exists

## IT-3 Calendar dates do not shift

1. Receive a sample with received date today. The received date stays that calendar day. It does not move to yesterday in the evening.
2. Due date, test date, review date, result entry date, reagent Used on, and batch start and end dates stay the day that was entered.

## IT-4 Empty instants

A run that has not started shows Started as an em dash. A user who has never logged in shows Last Login as Never.
