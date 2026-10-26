# UAT: ELISA run gaps (import, link, fail, rerun, receipt)

**Stem:** `elisa-run-gaps`
**Script:** Marc's IL-6 serum ELISA test on main (`ELISA_test_script_main.md`), gaps TC-08, TC-14, TC-15, TC-17, TC-18.
**UI:** Sample Mgmt → **Receive** (`/receive`) · Experiments → **Runs** (`/runs/:id`)
**API:** `POST /samples/receive` · `POST /v1/lims-runs/{id}/import-file` · `POST /v1/lims-runs/{id}/fail` (`/reject` is the same action) · `PATCH /v1/lims-runs/{id}/cancel` · `POST /v1/lims-runs/{id}/rerun` · `GET/POST /v1/lims-runs/{id}/value-choices` · publish `PATCH /v1/lims-runs/{id}/complete`
**Actors:** lab technician or lab manager (`experiment:manage` for import, fail, cancel, rerun, start) · reviewer (`experiment:publish` for publish and the accepted value)
**Pack:** IL-6 ELISA test pack v2. Gen5 file `IL6-PLT-0001_Gen5.csv`. Parser `sample_col` is `Sample Name`. Client sample id `IL6-SER-0001` is wells D3 and D4, corrected OD `0.063`.
**Not in this build:** 4PL standard curve, back-calculated concentration, duplicate CV, kit QC ranges, LLOQ/ULOQ. Alias the column to store (for example `corr`) before publish.

Record per row: Pass / Fail / Incomplete, commit SHA, and where the evidence is (screen or API JSON).

---

## Setup

1. Lab timezone is set.
2. Receive sample `IL6-SER-0001` (client sample ID) with collection date, volume µL, condition, and thaw count from the pack manifest.
3. Analysis for the IL-6 assay. Analyte alias `corr` so publish has a column to store. Active parser for that analysis, instrument set, config from the pack (`skip_rows` 20, `sample_col` Sample Name).
4. Draft LIMS run on that analysis. Cohort includes `IL6-SER-0001`. Start the run.

---

## Bars

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| EG-1 | Receipt fields (TC-08) | On `/receive`, enter collection date (not in the future), volume µL, condition, thaw count, and the client sample ID. Receive. Open the sample. | The four values are on the sample. A future collection date, a negative volume, a volume above 10,000,000 µL, a non-number volume, and a negative thaw count are refused and the form keeps what was typed. |
| EG-2 | Import from the run page (TC-14) | On the running run, **Import**. Pick the IL-6 parser. Upload `IL6-PLT-0001_Gen5.csv`. | The dialog reports imported, linked, and unmatched counts. The call is `POST /v1/lims-runs/{id}/import-file` with `parser_id` and the parser's `instrument_id`. Errors stay in the dialog. |
| EG-3 | Link and keep unmatched (TC-14) | Open the Data tab. Also import a known sample that was not added to this run, and a plate id that is one sample's client id and another sample's name. | `IL6-SER-0001` is linked (D3 and D4). `STD-S1`, `QC-L-1`, and `BLANK` stay in the table with a reason (`No sample matches …`). The sample that is not on the run stays with **Not on this run**. The id that matches two different samples on the run is not linked. If only the client-ID sample is on the run, the row links to it and shows a note. If only the name sample is on the run, the row is not linked and the note says the client sample ID belongs to a sample not on this run. Row count includes those rows. None of those rows are missing. |
| EG-4 | Publish linked results (TC-15) | Mark ready for review. Publish. Open Results for `IL6-SER-0001`. | Two results, replicates 1 and 2, raw value `0.063` (the `corr` column). No result is created for `STD-S1`. |
| EG-5 | Fail the run (TC-18, SOP §13) | On a running run with no import, confirm **Cancel Run** is shown. Import a file. Confirm **Cancel Run** is gone. Call `PATCH /v1/lims-runs/{id}/cancel`. Then **Fail run** with no reason, then with reason `QC-H out of range`. | Cancel returns **422** `run_has_imported_data` and the message says to fail the run. Empty reason does not submit. With a reason, status is **failed**, the reason is on the run, `failed_by` on `GET /v1/lims-runs/{id}` is the user who failed it, and the imported rows are still there. Nothing is deleted. |
| EG-6 | Rerun and accepted value (SOP §13 and §15) | **Create rerun**. Start it (same cohort). Import a second file whose linked `corr` differs. Publish the rerun. On the rerun, pick the new value, enter a reason, **Accept**. Then pick the failed run's value without the failed-run checkbox, then with it. | The rerun's `replaces_run_id` is the original. Publish is not 409; the preview counts the slot as held. After accept, Results shows the picked value. The other value is still on the acceptance row and in the original import. The failed-run value cannot be accepted until the checkbox is ticked and a reason is entered. |
| EG-7 | Older run canceled after import | Use a run that was canceled after data was imported (before this build) and has a rerun. Open the rerun's **Accepted value**. | The old run shows as `canceled, counts as failed`. Accepting its value needs the failed-run checkbox and a reason. The old run's status stays `canceled`. |
| EG-8 | Publish and fail at the same time | On a run that is ready for review, send `PATCH /v1/lims-runs/{id}/complete` (as a publisher) and `POST /v1/lims-runs/{id}/fail` with a reason at the same moment (two terminals). Repeat on a second run in the other order. | One call succeeds and the other is **400** `Cannot transition from 'published' to 'failed'` (or from `failed` to `published`). The run ends in the status of the call that succeeded; a failed run has no `published_at` and no promoted Results. If a call waited longer than the lock timeout it is **409** `run_busy` and changed nothing. A fail on an already published run does not write `status_reason`, `rejected_at`, or `failed_by`. |
| EG-9 | File import after the instrument is retired | Start a file import on a running run with an in-service instrument. While the file is parsing (or while the import waits on the run lock), retire that instrument. | Import is **422** `instrument_retired`. No rows are stored. The same refuse applies when the instrument is the one resolved from the parser rather than sent as `instrument_id`. |

---

## Deferred

Plate calculation (4PL, back-calculation, %CV, QC pass/fail against kit nominals, LLOQ/ULOQ, dilution factor) is a later PR. This UAT does not score those.
