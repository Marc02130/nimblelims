# UAT: Atomic receive (CORE happy path)

**Stem:** `atomic-receive`  
**Phase:** CORE implement shipped on branch `feat/atomic-receive-core` (Phases 1–4)  
**SoT:** PRD RQ-AR-* · SPEC §3 · `.docs/review/tech-sketch/atomic-receive.md`  
**QA review:** `.docs/review/qa-review/atomic-receive.md`  
**UI:** `/receive` (`AtomicReceive.tsx`) — sidebar **Receive**  
**API:** `POST /api/samples/receive`  
**Test data:** migration 0058 actors/projects + 0060 lists; catalog [atomic-receive/](atomic-receive/)  
**Env:**  
**Build / commit:**  
**Executor:**  
**Date:**  

This script is the **receive happy path** sign-off. Do **not** use `uat-sample-accessioning.md` (wizard) as receive SoT.

**CORE must-pass:** identity + **1..N vessels**, sticky project, Available for Testing, zero Tests at receive, 422 for non-empty `analysis_ids`, AuthZ.
**Follow-on (not CORE blockers):** AR-RES-01/02 results-entry.

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
| Default tube (off form) | Prefer Tube / cryovial / conical — resolved server-side |
| Sample status | Available for Testing |
| Test status | Assigned/Pending |
| Analysis A (`units_default` set) | ELISA (Human IgG) / IgG Concentration |
| Analysis B (`units_default` missing) | Cell Viability (Trypan Blue) / Total Cell Count |
| Alice wave (AR-HV-01) | `NBIO-AR-0001` … `NBIO-AR-0024`. Human sign-off: `0001` then `0002`. |
| Multi-vessel (AR-HV-MC) | Primary `NBIO-AR-MC-P` + additional `NBIO-AR-MC-A1`, `NBIO-AR-MC-A2` (same sample, one commit) |
| Keyboard barcode (AR-HV-05) | `NBIO-AR-KB-0001` |
| Alice sticky | Plasma / Plasma (K2EDTA) / mAb-2301 PK Study |
| Bob wave (AR-MU-01) | `CART-AR-0001` … `CART-AR-0008`; sticky PBMC / Cell Supernatant / CAR-T In-Process Testing |
| Client / no receive (AR-RBAC-01) | `david-cro` → no Receive nav or **403** on POST |
| Aliquots | None in CORE. Multi-tube receive ≠ aliquot UI. |

### Barcode 1:1

| Case | Barcode(s) |
|------|------------|
| AR-HV-01 first + second | `NBIO-AR-0001` then `NBIO-AR-0002` (two commits) |
| **AR-HV-MC** | Primary `NBIO-AR-MC-P` + additional `NBIO-AR-MC-A1`, `NBIO-AR-MC-A2` (**one** commit) |
| AR-DUP-01 | replay `NBIO-AR-0001` |
| AR-HV-02 | `NBIO-AR-0009` (POST with a valid non-empty `analysis_ids` value; refused) |
| AR-HV-05 | `NBIO-AR-KB-0001` |
| AR-RBAC-01 | `NBIO-AR-CLIENT-0001` (optional) |

## Preconditions

- App running with CORE receive code (Phases 1–4).
- Seed: 0058 + 0060.
- Unique constraint on `containers.name`.
- Sidebar shows **Receive** → `/receive` for users with `sample:create`.

## Cases — CORE must-pass

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as `alice-tech`. Open **Receive** (`/receive`). Scan `NBIO-AR-0001`. Sticky Plasma / Plasma (K2EDTA) / mAb-2301. Submit. Immediately scan `NBIO-AR-0002` without navigating away. | Both created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. No analyses picker. No aliquot dialog. | | QA2, QA5, QA6 |
| **AR-HV-MC** | Same sticky. Primary `NBIO-AR-MC-P`. Add additional barcodes `NBIO-AR-MC-A1` and `NBIO-AR-MC-A2`. Submit once. | **One** sample; **three** containers + contents → same sample; status Available for Testing; stay on form. | | RQ-AR-2/3, A-18 |
| AR-HV-02 | Inspect the UI, then POST receive with ELISA (Human IgG) in non-empty `analysis_ids`. | UI has no analyses picker. API returns **422 before the transaction**. No Sample, Container, Contents, or Test row is created. | | QA6 / Architecture lock |
| AR-HV-03 | Receive with temperature omitted. | Succeeds. | | |
| AR-HV-04 | Receive once with `client_sample_id`, once omitted. | Both succeed. | | |
| AR-HV-05 | Type barcode `NBIO-AR-KB-0001` (no scanner). Submit. | Same success; `containers.name` = typed barcode. | | Keyboard |
| AR-VAL-01 | Four POSTs/UI submits, each missing one required: barcode, type, matrix, project. | Each → **422** (or UI validation). No sample/container row. | | |
| AR-DUP-01 | Replay `NBIO-AR-0001` after it exists. | **409**. Toast. Stay on receive. No second sample. | | QA3 |
| AR-ID-01 | Inspect `/receive` form and AR-HV-01 response. | **No sample-ID field**. `samples.name` ≠ barcode (unless template coincides). `containers.name` = barcode. No status / tube-type fields. | | QA2 |
| AR-ST-01 | Inspect sample from `NBIO-AR-0001`. | Status = **Available for Testing**. `received_date` set. No Received hop. | | QA4 |
| AR-TST-01 | Inspect a successfully received sample from AR-HV-01, then add ELISA later via the separate tests UI/API. | Zero Tests immediately after receive. The later explicit add creates the test with its normal pending status. | | QA6 |
| AR-TST-02 | DELETE that test (no results). | DELETE succeeds. | | QA6 / A-14 |
| AR-TST-03 | After a test has results, DELETE it. | **400**. Test and result remain. | | QA6 / A-14 |
| AR-RBAC-01 | Log in as `david-cro`. Open Receive or POST `/samples/receive`. | No receive UI, or **403**. | | QA8 |
| AR-MU-01 | alice receives on mAb; bob on CAR-T; then reverse project_id. | Happy path OK; reverse → **403**. | | QA8 |

### Follow-on (not CORE UAT blockers)

| ID | Steps | Expected | Notes |
|----|-------|----------|-------|
| AR-RES-01 | Typed number on ELISA / IgG for a received sample | Persist lock: `reported_result` + qualifiers | Results slice |
| AR-RES-02 | Typed number on analyte missing `units_default` | **422** | Results slice |

### Automated only (pytest)

| ID | Steps | Expected |
|----|-------|----------|
| AR-T1 | Phases 1–3 pytest (`test_atomic_receive_phase*.py`) | Rollback / 409 / RBAC / non-empty `analysis_ids` refused with 422 and zero rows / field hygiene |

## Sign-off

Pass / Fail — signature

**CORE pass** requires CORE must-pass rows above (not AR-RES).  
QA1–QA6, QA8–QA10 in `.docs/review/qa-review/atomic-receive.md` apply to CORE. QA7 = results follow-on.

## Cutover

| Script | Status after CORE docs sync |
|--------|------------------------------|
| **`uat-atomic-receive.md`** | **Receive happy-path SoT** |
| `uat-sample-accessioning.md` | **Demoted** — legacy wizard only; not receive sign-off |
| `uat-sample-status-editing.md` | Do not require Reviewed/Reported on Sample.status for CORE (Q1 parallel) |
