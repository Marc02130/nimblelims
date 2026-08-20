# UAT: Atomic receive

**Stem:** `atomic-receive`  
**Phase:** P0 receive loop (docs ahead of implement)  
**Requirements:** [PR 30 sketch](https://github.com/Marc02130/nimblelims/pull/30); US-2 / US-30 alignment pending BA  
**QA review:** `.docs/qa-review/atomic-receive.md`  
**Env:**  
**Build / commit:**  
**Executor:**  
**Date:**  

Replaces the **receive happy path** in `uat-sample-accessioning.md` when this packet ships. Do not run the old wizard cases (typed sample name, status Received, In Process, aliquot dialog) as the atomic-receive sign-off.

## Preconditions

- App running. Logins from `AGENTS.md`: `admin` / `admin123`, `lab-tech` / `labtech123`, `client` / `client123`.
- Seeded: sample type, matrix, at least one project the lab-tech can access, one project they cannot.
- Sample **name template** assigns `samples.name` without a typed sample ID.
- Default **tube** container type (off the form).
- Sample status list includes **Available for Testing**.
- Test status list includes **Assigned/Pending** (or the agreed slug from implement).
- Unique constraint on `containers.name`.
- Analysis A: analyte with `units_default` set.
- Analysis B: analyte with `units_default` missing (for AR-12).
- Qualifier list entries: `<LOD`, `ND` (optional for AR-11).

Anton owns realistic seed coverage for the above.

## Cases

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-01 | Log in as lab-tech. Open receive. Scan a new barcode. Set type, matrix, project. Leave tests empty. Omit temperature. Submit. | 201. Stay on receive. Toast. `containers.name` = barcode. `samples.name` is template-generated and **not** the barcode. Status = Available for Testing. `received_date` set. Container type = default tube. Contents row exists. No tests. | | QA2, QA4, QA5 |
| AR-02 | Same as AR-01 with a new barcode. Attach analysis A at receive. | Tests created, status assigned/pending (not In Process). | | QA6 |
| AR-03 | Immediately after AR-01 or AR-02, do not navigate away. Confirm type/matrix/project still set. Barcode field empty and focused. Scan a **second** new barcode. Submit. | Second sample created. Sticky fields reused. Still on receive. No sample-detail page. No aliquot dialog. | | QA5 |
| AR-04 | Type a new barcode on the keyboard (no scanner). Same fields as AR-01. Submit. | Same as AR-01. | | Keyboard fallback |
| AR-05 | Rescan or retype a barcode from AR-01. Submit. | **409**. Toast. Stay on receive. No second sample. No orphan contents/tests. | | QA3 |
| AR-06 | Submit with barcode empty, or type/matrix/project missing. | **422**. No sample or container row. | | |
| AR-07 | Receive with temperature omitted (AR-01 covers). Optionally send temperature `4`. | Both succeed. Temperature not required. | | |
| AR-08 | Inspect the receive form. | **No sample-ID / sample name input.** Lookup is the barcode field only. | | QA2 |
| AR-09 | Open the sample from AR-01. Add analysis A. | POST succeeds. Test status assigned/pending. | | QA6 |
| AR-10 | Delete the test from AR-09 (no results). | DELETE succeeds. | | QA6 |
| AR-11 | On a test with analysis A (units_default present), enter raw value and optional qualifier `<LOD` or `ND`. Do not pick a unit. | Result saved. Unit taken from `analytes.units_default`. No unit picker on the form. | | QA7 |
| AR-12 | On a test with analysis B (no units_default), enter a raw value. | **422**. No result row. | | QA7 |
| AR-13 | DELETE the test used in AR-11 (has results). | **400**. Test and result remain. | | QA6 |
| AR-14 | Log in as client. Open receive or POST `/api/samples/receive`. | No receive UI, or **403**. | | QA8 |
| AR-15 | As lab-tech, POST `/api/samples/receive` with `project_id` of a project not in `project_users`. | **403**. No row. | | QA8 |

### Automated only (implement gate, not a human skip)

| ID | Steps | Expected |
|----|-------|----------|
| AR-T1 | Pytest: insert sample, then fail container insert (or unique violation) inside the same txn. | Zero leftover sample, container, contents, tests. |

## Sign-off

Pass / Fail — signature

QA1–QA10 in `.docs/qa-review/atomic-receive.md` must be met for a full-pipeline merge. This script is the human UAT pass, not a substitute for pytest AR-T1.

## Cutover

| Old script | After atomic-receive ships |
|------------|----------------------------|
| `uat-sample-accessioning.md` | Not the receive happy path. Keep only until this script records a pass, then mark superseded. |
| `uat-sample-status-editing.md` | Do not require Reviewed/Reported on Sample.status for this packet (Q1 parallel). |
