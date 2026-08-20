# P0 atomic-receive scenarios

IDs coordinated with Tobias. Payloads in [`payloads.json`](payloads.json). Sketch: two identities (PR 30). **No parent/child samples.**

Sticky defaults for Alice (mAb PK): sample type `Plasma`, matrix `Plasma (K2EDTA)`, project `mAb-2301 PK Study`.

## Result persist

Seed/enter typed values into `results.reported_result` and `qualifiers`. `raw_result` copies the same string. Do not send `unit_id`.

## AR-HV-01 High-volume unique barcodes

- **Actor:** `alice-tech`
- **Barcodes:** `NBIO-AR-0001` … `NBIO-AR-0024` (24 unique)
- **Sticky:** Plasma / Plasma (K2EDTA) / mAb-2301 PK Study
- **Expected:** 24 containers with `name` = barcode; 24 samples with template `samples.name` ≠ barcode; status Available for Testing; stay on receive (toast, clear barcode, keep sticky)
- **UI:** no sample-ID field; no redirect; no aliquot dialog

## AR-HV-02 Optional tests at receive

- **Actor:** `alice-tech`
- First 8 barcodes (`NBIO-AR-0001`–`0008`): `analysis_ids` = ELISA (Human IgG) (`analysis-elisa-001`), test status **Assigned/Pending**
- Remaining 16: `analysis_ids` = `[]`

## AR-HV-03 Optional temperature

- Odd barcodes (`0001`, `0003`, …): `temperature` = 4.0
- Even barcodes: omit `temperature` (null)

## AR-HV-04 Optional external id

- `NBIO-AR-0001`–`0004`: `client_sample_id` = `EXT-PK-001` … `EXT-PK-004` (globally unique)
- Others: omit `client_sample_id`

## AR-DUP-01 Duplicate barcode → 409 on container

- Replay `NBIO-AR-0001` after it exists
- **Expected:** HTTP 409 on `containers.name` unique constraint
- `samples.name` is **not** the collision key (template ID is a different string)

## AR-ID-01 System-assigned sample name

- Receive body has no `name`, `sample_name`, or `lab_id`
- After success, `samples.name` comes from the existing name template and is not equal to the barcode

## AR-ST-01 Status + received_date

- After commit: Sample Status = `Available for Testing` (one write, no Received hop)
- `received_date` is set (datetime, not date-only)

## AR-TST-01 Add test after receive

- Sample from `NBIO-AR-0009` (received with no tests)
- `POST /api/samples/{id}/tests` with ELISA (Human IgG)
- Expected: test status Assigned/Pending

## AR-TST-02 Remove test (no results)

- `DELETE` the test from AR-TST-01
- Expected: 2xx; test gone

## AR-TST-03 Refuse DELETE when results exist

- Enter a result on `NBIO-AR-0001` ELISA (see AR-RES-01 persist lock)
- `DELETE` that test → **400** Cannot delete test with results

## AR-RES-01 Result entry (unit present)

- Actor enterer: `alice-tech`
- Analyte: `IgG Concentration` (`analyte-igg-conc`, `units_default` set)
- Body: `reported_result` = `"12.4"`, `raw_result` = `"12.4"`, `qualifiers` = `<LOD` list entry **or** omit qualifier for a numeric happy path
- Qualifier variant in payloads: `reported_result`/`raw_result` = `"<0.05"`, qualifier `<LOD`
- **No `unit_id`.** Unit from `analytes.units_default`
- Expected: 2xx; row persisted as above

## AR-RES-02 Missing units_default → 422

- Analysis: Cell Viability (Trypan Blue)
- Analyte: `Total Cell Count` (`analyte-cell-count`, `units_default` NULL)
- Expected: **422**; no result row

## AR-MU-01 Two techs receiving

- `alice-tech` → `NBIO-AR-*` on mAb-2301 PK Study only
- `bob-tech` → `CART-AR-0001` … `CART-AR-0008` on CAR-T In-Process Testing; sticky PBMC / Cell Supernatant
- Neither tech's payload uses the other's `project_id`

## AR-MU-02 Reviewer ≠ enterer (US-10)

- Enterer: `alice-tech` (AR-RES-01)
- Reviewer: `carol-manager`
- When second-person gate is ON: Carol can review, Alice cannot review her own result
- **Gap:** no tenant setting column for that gate in current schema. Seed distinct users; do not invent a settings table.

## Not in P0

- Aliquot UI / another container on the same sample
- Derivative / `parent_sample_id` (0059 lifecycle rows are later-phase fixtures, not this receive set)
- US-31 receipt condition / manifest / disposition
- US-38 remaining quantity
- ELN, parsers, dose-response
