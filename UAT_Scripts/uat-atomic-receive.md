# UAT: Atomic receive (CORE happy path)

**Stem:** `atomic-receive`  
**Phase:** CORE implement shipped on branch `feat/atomic-receive-core` (Phases 1–4)  
**SoT:** PRD RQ-AR-* · SPEC §3 · `.docs/review/tech-sketch/atomic-receive.md`  
**QA review:** `.docs/review/qa-review/atomic-receive.md`  
**UI:** `/receive` (`AtomicReceive.tsx`) — sidebar **Receive**  
**API:** `POST /api/samples/receive`  
**Test data:** migration 0058 actors/projects + 0060 lists; catalog [atomic-receive/](atomic-receive/)  
**Env:** Marc checkout `/Users/marcbreneiser/Code/nimblelims/` compose; up for the run, then down. Compose is **down** now.  
**Build / commit:** `ebac94e` (main merge of `feat/atomic-receive-core`)  
**Executor:** Anton (CORE API 21/21) · Tobias (independent verify of the listed holds)  
**Date:** 2026-08-27  

This script is the **receive happy path** sign-off. Do **not** use `uat-sample-accessioning.md` (wizard) as receive SoT.

**CORE must-pass:** identity + **1..N vessels**, sticky project, Available for Testing, **zero Tests / zero Results** at receive, AuthZ (PR 68). Non-empty `analysis_ids` → **422**.
**Follow-on (not CORE blockers):** AR-RES-01/02 results-entry. **A-15 asked-for / work-plan is parked.**

**This stamp (2026-08-27):** **API CORE Accept (21/21)**. **UI CORE not run / not Met.** Nobody clicked `/receive` on this build. Merge to `main` at `ebac94e` is **not** a UI stamp.

---

## ID map (old → shared)

| Old | Shared |
|-----|--------|
| AR-01 + AR-03 | AR-HV-01 |
| AR-02 | AR-HV-02 |
| AR-07 | AR-HV-03 |
| (new) | AR-HV-04 |
| AR-04 | AR-HV-05 |
| (new multi-vessel) | **AR-HV-MC** |
| AR-06 | AR-VAL-01 |
| AR-05 | AR-DUP-01 |
| AR-08 | AR-ID-01 |
| (was in AR-01) | AR-ST-01 |
| AR-09 | AR-TST-01 |
| AR-10 | AR-TST-02 |
| AR-13 | AR-TST-03 |
| AR-11 | AR-RES-01 *(follow-on)* |
| AR-12 | AR-RES-02 *(follow-on)* |
| AR-14 | AR-RBAC-01 |
| AR-15 | AR-MU-01 |

## Fixture lock (Anton / 0058 + 0060)

| Need | Seed |
|------|------|
| Actors | `alice-tech` / `alice123` (mAb-2301 PK); `bob-tech` / `bob123` (CAR-T); `david-cro` / `david123` (AR-RBAC-01) |
| Name template | Assigns `samples.name` with no typed sample ID |
| Container type (sticky, required) | **1×1 only** (`rows=1` and `columns=1`, e.g. Cryovial 2mL). Plates (`8×12`, etc.) refused. Same type for all vessels on the commit. |
| Sample status | Available for Testing |
| Test status | Assigned/Pending — **only after a later explicit add-test**, never minted at receive |
| Analysis A (`units_default` set) | ELISA (Human IgG) / IgG Concentration — used after receive, not on the receive body |
| Analysis B (`units_default` missing) | Cell Viability (Trypan Blue) / Total Cell Count — used after receive, not on the receive body |
| Alice wave (AR-HV-01) | `NBIO-AR-0001` … `NBIO-AR-0024`. Human sign-off: `0001` then `0002`. Bodies omit `analysis_ids` (empty `[]` also OK). |
| Multi-vessel (AR-HV-MC) | Primary `NBIO-AR-MC-P` + additional `NBIO-AR-MC-A1`, `NBIO-AR-MC-A2` (same sample, one commit) |
| Keyboard barcode (AR-HV-05) | `NBIO-AR-KB-0001` |
| Alice sticky | Sample type Plasma / project mAb-2301 PK Study / 1×1 container type (e.g. Cryovial) |
| Bob wave (AR-MU-01) | `CART-AR-0001` … `CART-AR-0008`; sticky PBMC / Cell Supernatant / CAR-T In-Process Testing |
| Client / no receive (AR-RBAC-01) | `david-cro` → no Receive nav or **403** on POST |
| Aliquots | None in CORE. Multi-tube receive ≠ aliquot UI. |

### Barcode 1:1

| Case | Barcode(s) |
|------|------------|
| AR-HV-01 first + second | `NBIO-AR-0001` then `NBIO-AR-0002` (two commits) |
| **AR-HV-MC** | Primary `NBIO-AR-MC-P` + additional `NBIO-AR-MC-A1`, `NBIO-AR-MC-A2` (**one** commit) |
| AR-DUP-01 | replay `NBIO-AR-0001` |
| AR-HV-02 | `NBIO-AR-REFUSE-0001` (POST with non-empty `analysis_ids` → 422) |
| AR-TST-01 | `NBIO-AR-0009` (received with omitted/`[]` `analysis_ids`; add ELISA later) |
| AR-HV-05 | `NBIO-AR-KB-0001` |
| AR-RBAC-01 | `NBIO-AR-CLIENT-0001` (optional) |

## Preconditions

- App running with CORE receive code (Phases 1–4).
- Seed: 0058 + 0060.
- Unique constraint on `containers.name`.
- Sidebar shows **Receive** → `/receive` for users with `sample:create`.
- Merge to `main` landed at `ebac94e`. **Merge is not a UI stamp.** Not IC50.

## Cases — CORE must-pass

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as `alice-tech`. Open **Receive** (`/receive`). Scan `NBIO-AR-0001`. Sticky Plasma / Plasma (K2EDTA) / mAb-2301. Submit. Immediately scan `NBIO-AR-0002` without navigating away. | Both created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. **No analysis picker.** No aliquot dialog. After each receive: **zero Tests**, **zero Results**. Extra barcodes would be more tubes of that sample. | API Pass / UI not run | QA2, QA5, QA6. Anton 21/21. Tobias independent verify: `NBIO-AR-0001` / `0002` exist; status Available for Testing; `received_date` set; zero Tests. UI stay-on-form / toast / hop-off / aliquot dialog **not run**. |
| **AR-HV-MC** | Same sticky. Primary `NBIO-AR-MC-P`. Add additional barcodes `NBIO-AR-MC-A1` and `NBIO-AR-MC-A2`. Submit once. | **One** sample; **three** containers + contents → same sample; status Available for Testing; stay on form; **zero Tests**, **zero Results**. | API Pass / UI not run | RQ-AR-2/3, A-18. Anton 21/21. Tobias independent verify: 1 sample / 3 vessels (`NBIO-AR-MC-P`, `A1`, `A2`). Stay on form **not run**. |
| AR-HV-02 | Inspect `/receive` (no analysis picker). POST receive for `NBIO-AR-REFUSE-0001` with ELISA (Human IgG) in non-empty `analysis_ids`. Separately, confirm omitted or `[]` `analysis_ids` still succeed (AR-HV-01). | UI has **no analysis picker** and never sends `analysis_ids`. Non-empty `analysis_ids` → **422** before the transaction. No sample, container, contents, Test, or Result rows for `NBIO-AR-REFUSE-0001`. | API Pass / UI not run | QA6 / WO-7 / A-15 parked. Anton 21/21. Tobias independent verify: non-empty `analysis_ids` → **422** (`analysis_ids must be empty for Atomic Receive CORE`). No analysis picker **not run**. |
| AR-HV-03 | Receive with temperature omitted. | Succeeds. Zero Tests. | API Pass | Anton 21/21. UI not run. |
| AR-HV-04 | Receive once with `client_sample_id`, once omitted. | Both succeed. Zero Tests. | API Pass | Anton 21/21. UI not run. |
| AR-HV-05 | Type barcode `NBIO-AR-KB-0001` (no scanner). Submit. | Same success; `containers.name` = typed barcode; zero Tests. | API Pass / UI not run | Keyboard. Anton 21/21. |
| AR-VAL-01 | Four POSTs/UI submits, each missing one required: barcode, type, matrix, project. | Each → **422** (or UI validation). No sample/container row. | API Pass / UI not run | Anton 21/21 only. Not independently re-run by Tobias. |
| AR-DUP-01 | Replay `NBIO-AR-0001` after it exists. | **409**. Toast. Stay on receive. No second sample. | API Pass / UI not run | QA3. Anton 21/21. Tobias independent verify: replay `NBIO-AR-0001` → **409** (`Container barcode already exists`). Toast / stay on receive **not run**. |
| AR-ID-01 | Inspect `/receive` form and AR-HV-01 response. | **No sample-ID field**. `samples.name` ≠ barcode (unless template coincides). `containers.name` = barcode. No status / tube-type / analysis fields. | API Pass / UI not run | QA2. Anton 21/21. Tobias independent verify: `samples.name` from template, not the barcode. No sample-ID field on `/receive` **not run**. |
| AR-ST-01 | Inspect sample from `NBIO-AR-0001`. | Status = **Available for Testing**. `received_date` set. No Received hop. Zero Tests. | API Pass | QA4. Anton 21/21. Tobias independent verify: Available for Testing; `received_date` set; zero Tests. Received hop (UI) **not run**. |
| AR-TST-01 | Inspect the sample from `NBIO-AR-0009` immediately after receive, then add ELISA later via the separate tests UI/API. | Zero Tests and zero Results immediately after receive. The later explicit add creates the test with its normal pending status. | API Pass | QA6. Anton 21/21. Tobias independent verify: zero Tests after receive (WO-7). Later add-test path not separately restated. |
| AR-TST-02 | DELETE that test (no results). | DELETE succeeds. | API Pass | QA6 / A-14. Anton 21/21. Not independently re-run by Tobias. |
| AR-TST-03 | After an explicitly added test has results, DELETE it. | **400**. Test and result remain. | API Pass | QA6 / A-14. Anton 21/21. Not independently re-run by Tobias. |
| AR-RBAC-01 | Log in as `david-cro`. Open Receive or POST `/samples/receive`. | No receive UI, or **403**. | API Pass / UI not run | QA8. Anton 21/21. Tobias independent verify: `david-cro` POST → **403** (`sample:create` required). Receive nav **not run**. |
| AR-MU-01 | alice receives on mAb; bob on CAR-T; then reverse project_id. | Happy path OK (zero Tests at receive); reverse → **403**. Observed this run: reverse → **404** Project not found. **403 or 404 both refuse** (no row). | API Pass | QA8. Anton 21/21. Tobias independent verify: reverse project → **404** (refuse). Expected column still lists **403**; do not treat 404 as a silent spec rewrite. |

### Follow-on (not CORE UAT blockers)

| ID | Steps | Expected | Notes |
|----|-------|----------|-------|
| AR-RES-01 | After explicit ELISA add on a received sample, typed number on IgG | Persist lock: `reported_result` + qualifiers | Results slice — not minted at receive. **Parked / not run** this stamp. |
| AR-RES-02 | After explicit viability add, typed number on analyte missing `units_default` | **422** | Results slice. **Parked / not run** this stamp. |

### Automated only (pytest)

| ID | Steps | Expected |
|----|-------|----------|
| AR-T1 | Phases 1–3 pytest (`test_atomic_receive_phase*.py`) | Rollback / 409 / RBAC / **non-empty `analysis_ids` → 422** with zero rows / empty or omitted `analysis_ids` → 201 with `tests: []` / field hygiene |

## Sign-off

**API CORE Accept (21/21)** — Anton, 2026-08-27, `ebac94e`.  
**UI CORE not Met / not run** — nobody clicked `/receive` on this build. Bench fail remains hop off receive, aliquot dialog, or a sample-ID field. Merge to `main` is **not** a UI stamp.

Do **not** read this as a single undifferentiated Pass or as CORE UI sign-off.

**CORE pass** requires CORE must-pass rows above (not AR-RES).  
QA1–QA6, QA8–QA10 in `.docs/review/qa-review/atomic-receive.md` apply to CORE. QA7 = results follow-on.

Verified holds (Anton + Tobias, 2026-08-27): HV-01 `NBIO-AR-0001` / `0002`; HV-MC 1 sample / 3 vessels; zero Tests (WO-7); `samples.name` from template; DUP 409; non-empty `analysis_ids` 422; `david-cro` POST 403; MU reverse 404 refuse. AR-VAL-01 is Anton 21/21 only.

## Cutover

| Script | Status after CORE docs sync |
|--------|------------------------------|
| **`uat-atomic-receive.md`** | **Receive happy-path SoT** |
| `uat-sample-accessioning.md` | **Demoted** — legacy wizard only; not receive sign-off |
| `uat-sample-status-editing.md` | Do not require Reviewed/Reported on Sample.status for CORE (Q1 parallel) |
