# UAT: ELISA run gaps (import, link, reject, rerun, receipt)

**Stem:** `elisa-run-gaps`
**Script:** Marc's IL-6 serum ELISA test on main (`ELISA_test_script_main.md`), gaps TC-08, TC-14, TC-15, TC-17, TC-18.
**UI:** Sample Mgmt → **Receive** (`/receive`) · Experiments → **Runs** (`/runs/:id`)
**API:** `POST /samples/receive` · `POST /v1/lims-runs/{id}/import-file` · `POST /v1/lims-runs/{id}/reject` · `POST /v1/lims-runs/{id}/rerun` · `GET/POST /v1/lims-runs/{id}/value-choices` · publish `PATCH /v1/lims-runs/{id}/complete`
**Actors:** lab technician or lab manager (`experiment:manage` for import, reject, rerun, start) · reviewer (`experiment:publish` for publish and the accepted value)
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
| EG-1 | Receipt fields (TC-08) | On `/receive`, enter collection date (not in the future), volume µL, condition, thaw count, and the client sample ID. Receive. Open the sample. | The four values are on the sample. A future collection date, a negative volume, and a negative thaw count are refused and the form keeps what was typed. |
| EG-2 | Import from the run page (TC-14) | On the running run, **Import**. Pick the IL-6 parser. Upload `IL6-PLT-0001_Gen5.csv`. | The dialog reports imported, linked, and unmatched counts. The call is `POST /v1/lims-runs/{id}/import-file` with `parser_id` and the parser's `instrument_id`. Errors stay in the dialog. |
| EG-3 | Link and keep unmatched (TC-14) | Open the Data tab. | `IL6-SER-0001` is linked (D3 and D4). `STD-S1`, `QC-L-1`, and `BLANK` stay in the table with a reason (`No sample matches …`). Row count is 96. None of those rows are missing. |
| EG-4 | Publish linked results (TC-15) | Mark ready for review. Publish. Open Results for `IL6-SER-0001`. | Two results, replicates 1 and 2, raw value `0.063` (the `corr` column). No result is created for `STD-S1`. |
| EG-5 | Reject the plate (TC-18, SOP §13) | On a running or complete run, **Reject plate** with no reason, then with reason `QC-H out of range`. | Empty reason does not submit. With a reason, status is **failed**, the reason is on the run, and the imported rows are still there. Nothing is deleted. |
| EG-6 | Rerun and accepted value (SOP §13 and §15) | **Create rerun**. Start it (same cohort). Import a second file whose linked `corr` differs. Publish the rerun. On the rerun, pick the new value, enter a reason, **Accept**. | The rerun's `replaces_run_id` is the original. Publish is not 409; the preview counts the slot as held. After accept, Results shows the picked value. The other value is still on the acceptance row and in the original import. |

---

## Deferred

Plate calculation (4PL, back-calculation, %CV, QC pass/fail against kit nominals, LLOQ/ULOQ, dilution factor) is a later PR. This UAT does not score those.
