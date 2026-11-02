# UAT: Shared reason rules (0121)

**Stem:** `shared-reason-rules`
**Rule:** every user-entered reason uses the void rules. Trimmed length 1–4000. Missing, empty, spaces, tab/newline, NBSP (U+00A0), and U+2007 are blank. ZWSP (U+200B) and BOM (U+FEFF) stay visible. The stored value is trimmed.
**Migration:** `0121_shared_reason_rules`
**API:** `POST /v1/lims-runs/{id}/fail`, `/reject`, `/value-choices`, `/substitute-instrument-type`, `/dose-response/fit/reset`, `POST /v1/lims-runs/data/{data_id}/exclude`
**Last run:** not yet run on this branch.

Blank set used in the steps: no `reason` key, `""`, `"   "`, `"\t\n"`, three NBSP, three U+2007.

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| SR-1 | Fail / reject reason | As `lab-manager`, on a running plate, POST `/fail` with each blank value. Repeat on `/reject`. Then POST `/fail` with 4001 `x`. Then POST `/fail` with `"  QC-H out of range  "`. On a second plate, fail with a reason of one ZWSP. | Each blank is **422** `fail_reason_required` and the run is not failed. 4001 is **422**. The trimmed reason is **200**, and `status_reason` is `QC-H out of range`. ZWSP is **200** and stored. |
| SR-2 | Accept value reason | On a published rerun, POST `/value-choices` for a sample with each blank value, then 4001 `x`, then `"Rerun is valid"`. | Each blank is **422** `acceptance_reason_required`. 4001 is **422**. No `result_acceptances` row exists until the valid reason, which is **200** and stored trimmed. |
| SR-3 | Substitute reason | On a started run, POST `/substitute-instrument-type` with each blank value. | Each blank is **422** `substitute_reason_required` (missing `reason` is now this code, not a field error). Length bars stay as IT-29-len. |
| SR-4 | Reset fit reason | On a run with `fit_in_progress = true`, POST `/dose-response/fit/reset` with each blank value, then 4001 `x`, then `"  worker crashed  "`. | Each blank is **422** `reset_fit_reason_required`, and 4001 is **422**. `fit_in_progress` stays true after both. The valid reason is **200**, the response `reason` is `worker crashed`, and the flag is false. |
| SR-5 | Exclusion reason (optional) | POST `/data/{id}/exclude` with no reason, `"   "`, NBSP, `"  outlier  "`, ZWSP, and 4000 `x`, un-excluding between attempts. Then try 4001 `x`. | Every attempt except 4001 is **200**. Blank values are stored as null. `"  outlier  "` is stored as `outlier`. ZWSP and 4000 `x` are stored. 4001 is **422** and no row is written. |
| SR-6 | DB CHECKs | As a DB owner, INSERT/UPDATE each reason column with each blank value (non-null blanks on nullable columns), with `x` × 4001, then with ZWSP, BOM, and `x` × 4000. Columns: `lims_runs.status_reason`, `result_acceptances.reason`, `lims_run_data_exclusions.reason`, `lims_run_type_substitutions.reason`. | Blanks and 4001 raise **23514** on `ck_lims_runs_status_reason`, `ck_result_acceptances_reason`, `ck_lims_run_data_exclusions_reason`, and `ck_lims_run_type_substitutions_reason`. NBSP-only is now refused on substitutions. ZWSP, BOM, 4000, and NULL (on the nullable columns) are accepted. |
| SR-7 | Upgrade preflight | On a copy of a database at 0120, store a blank exclusion reason or an NBSP-only substitution reason, then run `alembic upgrade head`. | Upgrade stops with `0121 refuses CHECK: <table>.<column>=<count>`. No row is changed. After fixing the row, the upgrade succeeds. |
| SR-8 | Downgrade | `alembic downgrade 0120_void_reason_4000`, then `alembic upgrade head`. | Downgrade drops the three new CHECKs and puts back the 0120 substitution CHECK (space/tab/newline only). Upgrade restores all four. |
| SR-9 | Earlier reasons unchanged | Re-run IT-37 (void), first-due / schedule, `maintenance_tracked`, and type deactivate reason bars from `uat-instrument-tracking.md`. | Same results as before 0121. |
