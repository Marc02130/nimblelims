# UAT: Atomic receive

**Stem:** `atomic-receive`  
**Phase:** P0 receive loop (docs ahead of implement)  
**Requirements:** [PR 30 sketch](https://github.com/Marc02130/nimblelims/pull/30); US-1 / US-7 / US-8 / US-30 on merged [PR 32](https://github.com/Marc02130/nimblelims/pull/32) (`main`).  
**QA review:** `.docs/qa-review/atomic-receive.md`  
**Test data:** [PR 35](https://github.com/Marc02130/nimblelims/pull/35) (`testdata/atomic-receive-p0`). Same IDs as this script. No third scheme.  
**Env:**  
**Build / commit:**  
**Executor:**  
**Date:**  

Replaces the **receive happy path** in `uat-sample-accessioning.md` when this packet ships. Do not run the old wizard cases (typed sample name, status Received, In Process, aliquot dialog) as the atomic-receive sign-off.

Receive UAT of `/api/samples/receive` is catalog-only until that endpoint exists. AR-RES-01/02 stay catalog-only until then. Packet implement gate is **OPEN** (product code may start). This script is not an implement-gate close.

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

## Fixture lock (Anton / PR 35)

| Need | Seed |
|------|------|
| Actors | `alice-tech` / `alice123` (mAb-2301 PK); `bob-tech` / `bob123` (CAR-T); `david-cro` / `david123` (AR-RBAC-01) |
| Name template | Assigns `samples.name` with no typed sample ID |
| Default tube (off form) | Cryovial 2mL |
| Sample status | Available for Testing |
| Test status | Assigned/Pending |
| Analysis A (`units_default` set) | ELISA (Human IgG) / IgG Concentration |
| Analysis B (`units_default` missing) | Cell Viability (Trypan Blue) / Total Cell Count |
| Alice wave (AR-HV-01) | `NBIO-AR-0001` … `NBIO-AR-0024`. Human sign-off: first two tubes are enough for the sticky loop. |
| Keyboard barcode (AR-HV-05) | `NBIO-AR-KB-0001` (not in the 0001–0024 wave) |
| Alice sticky | Plasma / Plasma (K2EDTA) / mAb-2301 PK Study |
| Bob wave (AR-MU-01) | `CART-AR-0001` … `CART-AR-0008`; sticky PBMC / Cell Supernatant / CAR-T In-Process Testing |
| Client / no receive (AR-RBAC-01) | `david-cro` → 403 |
| Two techs (AR-MU-01) | alice → mAb only; bob → CAR-T only; foreign `project_id` → **403** |
| Aliquots | None in P0. Do not use 0059 lifecycle samples as receive fixtures. |

## Preconditions

- App running. Load PR 35 seed (0058 actors/projects + 0060 lists).
- Unique constraint on `containers.name`.
- Qualifier list entries: `<LOD`, `ND`.
- No parent/child aliquot fixtures in P0.

## Cases

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as `alice-tech`. Open receive. Scan `NBIO-AR-0001`. Sticky Plasma / Plasma (K2EDTA) / mAb-2301. Leave tests empty (or follow catalog overlay). Submit. Immediately scan `NBIO-AR-0002` without navigating away. | Both created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. No aliquot dialog. Catalog wave is 24 tubes; two is the human loop. | | QA2, QA5 |
| AR-HV-02 | Receive with ELISA (Human IgG) attached (catalog: first 8 of the wave). | Tests created, status assigned/pending (not In Process). | | QA6 |
| AR-HV-03 | Receive with temperature omitted (catalog: even barcodes). | Succeeds. Temperature not required. | | |
| AR-HV-04 | Receive once with `client_sample_id` (`EXT-PK-001` on `NBIO-AR-0001`), once omitted. | Both succeed. External ID stored as-is when present; not required. | | |
| AR-HV-05 | Type barcode `NBIO-AR-KB-0001` (no scanner). Same alice sticky. Same POST as scan. Submit. | Same success as AR-HV-01 first tube. `containers.name` = `NBIO-AR-KB-0001` and is unique. | | Keyboard fallback |
| AR-VAL-01 | Four POSTs, each missing one required field: barcode, type, matrix, project. | Each → **422**. No sample or container row. | | |
| AR-DUP-01 | Replay `NBIO-AR-0001` after it exists. | **409** on `containers.name` only. Toast. Stay on receive. No second sample. `samples.name` was never the barcode. | | QA3 |
| AR-ID-01 | Inspect the receive form and the AR-HV-01 payload/response. | **No sample-ID field** on the form or body. `samples.name` is template-generated and **not** the barcode. `containers.name` = barcode. | | QA2 |
| AR-ST-01 | Inspect the sample from AR-HV-01. | Status = **Available for Testing**. `received_date` set. No Received hop. Request had no status field. | | QA4 |
| AR-TST-01 | Open the sample from `NBIO-AR-0009` (received with no tests). Add ELISA (Human IgG). | POST succeeds. Test status assigned/pending. | | QA6 |
| AR-TST-02 | Delete the test from AR-TST-01 (no results). | DELETE succeeds. | | QA6 |
| AR-TST-03 | DELETE the ELISA test on `NBIO-AR-0001` after AR-RES-01. | **400**. Test and result remain. | | QA6 |
| AR-RES-01 | On IgG Concentration (`units_default` present), enter a typed number and optional qualifier `<LOD` or `ND`. Do not pick a unit. Catalog-only until `/receive` exists. | Result saved. Assert **`reported_result`** equals the typed value and **`qualifiers`** is set. `raw_result` may copy the same value. No `unit_id`. Unit from `analytes.units_default`. | | QA7 |
| AR-RES-02 | On Total Cell Count (no `units_default`), enter a typed number. Catalog-only until `/receive` exists. | **422**. No result row. | | QA7 |
| AR-RBAC-01 | Log in as `david-cro`. Open receive or POST `/api/samples/receive`. | No receive UI, or **403**. | | QA8 |
| AR-MU-01 | `alice-tech` receives `NBIO-AR-*` on mAb-2301. `bob-tech` receives `CART-AR-0001` on CAR-T. Alice POSTs Bob's `project_id` (or the reverse). | Each tech only sees/creates in their project. Foreign project → **403**, no row. | | QA8 |

### Out of P0 receive (do not seed as must-pass)

| ID | Why parked |
|----|------------|
| AR-MU-02 | US-10 second-person review (reviewer ≠ enterer). Later / Q1. Not a receive gate. |

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
