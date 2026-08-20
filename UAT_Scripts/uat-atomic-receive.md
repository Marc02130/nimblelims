# UAT: Atomic receive

**Stem:** `atomic-receive`  
**Phase:** P0 receive loop (docs ahead of implement)  
**Requirements:** [PR 30 sketch](https://github.com/Marc02130/nimblelims/pull/30); US-2 / US-30 alignment pending BA  
**QA review:** `.docs/qa-review/atomic-receive.md`  
**Test data:** Anton fixtures share these IDs  
**Env:**  
**Build / commit:**  
**Executor:**  
**Date:**  

Replaces the **receive happy path** in `uat-sample-accessioning.md` when this packet ships. Do not run the old wizard cases (typed sample name, status Received, In Process, aliquot dialog) as the atomic-receive sign-off.

## ID map (old → shared)

| Old | Shared |
|-----|--------|
| AR-01 + AR-03 | AR-HV-01 |
| AR-02 | AR-HV-02 |
| AR-07 | AR-HV-03 |
| (new) | AR-HV-04 |
| AR-04 | AR-HV-05 |
| AR-06 | AR-VAL-01 |
| AR-05 | AR-DUP-01 |
| AR-08 | AR-ID-01 |
| (was in AR-01) | AR-ST-01 |
| AR-09 | AR-TST-01 |
| AR-10 | AR-TST-02 |
| AR-13 | AR-TST-03 |
| AR-11 | AR-RES-01 |
| AR-12 | AR-RES-02 |
| AR-14 | AR-RBAC-01 |
| AR-15 | AR-MU-01 |

## Preconditions

- App running. Logins from `AGENTS.md`: `admin` / `admin123`, `lab-tech` / `labtech123`, `client` / `client123`. Second lab-tech for AR-MU-01.
- Seeded: sample type, matrix, at least one project lab-tech A can access, one project they cannot, one project for lab-tech B.
- Sample **name template** assigns `samples.name` without a typed sample ID.
- Default **tube** container type (off the form).
- Sample status list includes **Available for Testing**.
- Test status list includes **Assigned/Pending** (or the agreed slug from implement).
- Unique constraint on `containers.name`.
- Analysis A: analyte with `units_default` set.
- Analysis B: analyte with `units_default` missing (for AR-RES-02).
- Qualifier list entries: `<LOD`, `ND` (optional for AR-RES-01).
- No parent/child aliquot fixtures in P0.

Anton owns realistic seed coverage for the above.

## Cases

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as lab-tech A. Open receive. Scan a new barcode. Set type, matrix, project. Leave tests empty. Submit. Immediately scan a **second** new barcode without navigating away. | First and second samples created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. No aliquot dialog. | | QA2, QA5 |
| AR-HV-02 | Receive a new barcode with analysis A attached. | Tests created, status assigned/pending (not In Process). | | QA6 |
| AR-HV-03 | Receive with temperature omitted. | Succeeds. Temperature not required. | | |
| AR-HV-04 | Receive once with `client_sample_id` set, once omitted. | Both succeed. External ID stored as-is when present; not required. | | |
| AR-HV-05 | Type a new barcode on the keyboard (no scanner). Same sticky fields. Submit. | Same success as AR-HV-01 first tube. | | Keyboard fallback |
| AR-VAL-01 | Submit with barcode empty, or type/matrix/project missing. | **422**. No sample or container row. | | |
| AR-DUP-01 | Rescan or retype a barcode already received. | **409** on `containers.name` only. Toast. Stay on receive. No second sample. `samples.name` was never the barcode. | | QA3 |
| AR-ID-01 | Inspect the receive form and the AR-HV-01 payload/response. | **No sample-ID field** on the form or body. `samples.name` is template-generated and **not** the barcode. `containers.name` = barcode. | | QA2 |
| AR-ST-01 | Inspect the sample from AR-HV-01. | Status = **Available for Testing**. `received_date` set. No Received hop. Request had no status field. | | QA4 |
| AR-TST-01 | Open a sample received with no tests. Add analysis A. | POST succeeds. Test status assigned/pending. | | QA6 |
| AR-TST-02 | Delete the test from AR-TST-01 (no results). | DELETE succeeds. | | QA6 |
| AR-TST-03 | DELETE a test that has results (after AR-RES-01). | **400**. Test and result remain. | | QA6 |
| AR-RES-01 | On a test with analysis A (`units_default` present), enter a typed number and optional qualifier `<LOD` or `ND`. Do not pick a unit. | Result saved. Assert **`reported_result`** equals the typed number and **`qualifiers`** is set. `raw_result` may copy the same value. Do not assert a new column. Unit from `analytes.units_default`. No unit picker. | | QA7 |
| AR-RES-02 | On a test with analysis B (no `units_default`), enter a typed number. | **422**. No result row. | | QA7 |
| AR-RBAC-01 | Log in as client. Open receive or POST `/api/samples/receive`. | No receive UI, or **403**. | | QA8 |
| AR-MU-01 | Two lab-techs, each with their own sticky project. Each receives a unique barcode. Lab-tech A POSTs `project_id` they are not on. | Each tech only sees/creates in their project. Foreign project → **403**, no row. | | QA8 |

### Out of P0 receive (do not seed as must-pass)

| ID | Why parked |
|----|------------|
| AR-MU-02 | US-10 second-person review (reviewer ≠ enterer). Later packet. Q1 parallel. |

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
