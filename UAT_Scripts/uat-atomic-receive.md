# UAT: Atomic receive (CORE happy path)

**Stem:** `atomic-receive`  
**Phase:** CORE implement shipped on branch `feat/atomic-receive-core` (Phases 1–4)  
**SoT:** PRD RQ-AR-* · SPEC §3 · `.docs/review/tech-sketch/atomic-receive.md`  
**QA review:** `.docs/review/qa-review/atomic-receive.md`  
**UI:** `/receive` (`AtomicReceive.tsx`) — sidebar **Receive**  
**API:** `POST /api/samples/receive`  
**Test data:** migration 0058 actors/projects + 0060 lists; catalog [atomic-receive/](atomic-receive/)  
**Env:** local docker compose (`lims-*` healthy); http://localhost:3000 + :8000  
**Build / commit:** `ebac94e` (main)  
**Executor:** Grok browse UAT (`/browse`) + API curl  
**Date:** 2026-08-27  

**Run notes:** Seed barcodes `NBIO-AR-0001`/`0002`/`MC-*`/`KB-0001` were already consumed from dogfood. Browser happy-path used `NBIO-AR-0010`/`0011`, `NBIO-AR-MC2-*`, `NBIO-AR-KB-0010`. Matrix is no longer on the receive form (sample type is SoT); AR-VAL-01 exercised barcode / sample type / project / container type.

This script is the **receive happy path** sign-off. Do **not** use `uat-sample-accessioning.md` (wizard) as receive SoT.

**CORE must-pass:** identity + **1..N vessels**, sticky project, Available for Testing, **zero Tests / zero Results** at receive, AuthZ (PR 68). Non-empty `analysis_ids` → **422**.
**Follow-on (not CORE blockers):** AR-RES-01/02 results-entry. **A-15 asked-for / work-plan is parked.**

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
- Hold merge until this UAT + dogfood pass. PR 71 stays draft. Not IC50.

## Cases — CORE must-pass

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as `alice-tech`. Open **Receive** (`/receive`). Scan `NBIO-AR-0001`. Sticky Plasma / Plasma (K2EDTA) / mAb-2301. Submit. Immediately scan `NBIO-AR-0002` without navigating away. | Both created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. **No analysis picker.** No aliquot dialog. After each receive: **zero Tests**, **zero Results**. Extra barcodes would be more tubes of that sample. | **Pass** | Used `NBIO-AR-0010`/`0011` (0001/0002 already taken). Toast `Study-08`/`09`; sticky Plasma / mAb / Cryovial; stay on `/receive`; barcode cleared. |
| **AR-HV-MC** | Same sticky. Primary `NBIO-AR-MC-P`. Add additional barcodes `NBIO-AR-MC-A1` and `NBIO-AR-MC-A2`. Submit once. | **One** sample; **three** containers + contents → same sample; status Available for Testing; stay on form; **zero Tests**, **zero Results**. | **Pass** | Used `NBIO-AR-MC2-*`. Toast `Study-10 · 3 vessels`. Three containers → one sample id. |
| AR-HV-02 | Inspect `/receive` (no analysis picker). POST receive for `NBIO-AR-REFUSE-0001` with ELISA (Human IgG) in non-empty `analysis_ids`. Separately, confirm omitted or `[]` `analysis_ids` still succeed (AR-HV-01). | UI has **no analysis picker** and never sends `analysis_ids`. Non-empty `analysis_ids` → **422** before the transaction. No sample, container, contents, Test, or Result rows for `NBIO-AR-REFUSE-0001`. | **Pass** | UI: no analysis picker. API `NBIO-AR-REFUSE-0010` → 422 `analysis_ids must be empty…`; no container row. `[]` → 201 `tests: []`. |
| AR-HV-03 | Receive with temperature omitted. | Succeeds. Zero Tests. | **Pass** | Covered by AR-HV-01 (temp blank). |
| AR-HV-04 | Receive once with `client_sample_id`, once omitted. | Both succeed. Zero Tests. | **Pass** | UI `CLIENT-UAT-0010` on `KB-0010` stored in DB; omit also 201. **Note:** GET `/samples/{id}` returns `client_sample_id: null` even when DB has value (response serialization quirk; receive path OK). |
| AR-HV-05 | Type barcode `NBIO-AR-KB-0001` (no scanner). Submit. | Same success; `containers.name` = typed barcode; zero Tests. | **Pass** | Used `NBIO-AR-KB-0010` (KB-0001 taken). |
| AR-VAL-01 | Four POSTs/UI submits, each missing one required: barcode, type, matrix, project. | Each → **422** (or UI validation). No sample/container row. | **Pass** | Matrix removed from form. UI empty barcode blocks POST. API: missing barcode/type/project/ctype → 422; plate 8×12 → 400 not 1×1. |
| AR-DUP-01 | Replay `NBIO-AR-0001` after it exists. | **409**. Toast. Stay on receive. No second sample. | **Pass** | Browser + API: 409 `Container barcode already exists`; toast; stayed on `/receive`. |
| AR-ID-01 | Inspect `/receive` form and AR-HV-01 response. | **No sample-ID field**. `samples.name` ≠ barcode (unless template coincides). `containers.name` = barcode. No status / tube-type / analysis fields. | **Pass** | Form fields: barcode(s), sample type, project, container type, temp, client sample id only. Name template `mAb-2301 PK Study-NN`. |
| AR-ST-01 | Inspect sample from `NBIO-AR-0001`. | Status = **Available for Testing**. `received_date` set. No Received hop. Zero Tests. | **Pass** | Samples grid + status UUID → Available for Testing; `received_date` set. |
| AR-TST-01 | Inspect the sample from `NBIO-AR-0009` immediately after receive, then add ELISA later via the separate tests UI/API. | Zero Tests and zero Results immediately after receive. The later explicit add creates the test with its normal pending status. | **Pass** | Receive `NBIO-AR-0009` → `tests: []`. Later `POST /tests/` ELISA → Assigned/Pending. |
| AR-TST-02 | DELETE that test (no results). | DELETE succeeds. | **Pass** | DELETE 200; tests total → 0. |
| AR-TST-03 | After an explicitly added test has results, DELETE it. | **400**. Test and result remain. | **Pass** | DELETE → 400 `Cannot delete test that has results`; test GET still 200. |
| AR-RBAC-01 | Log in as `david-cro`. Open Receive or POST `/samples/receive`. | No receive UI, or **403**. | **Pass** | No Receive nav; `/receive` redirected to dashboard. API POST → 403 `sample:create` required. |
| AR-MU-01 | alice receives on mAb; bob on CAR-T; then reverse project_id. | Happy path OK (zero Tests at receive); reverse → **403**. | **Pass*** | Happy paths 201 `tests: []`. Cross-project → **404** `Project not found` (RLS hides project; denied, not 403). |

### Follow-on (not CORE UAT blockers)

| ID | Steps | Expected | Notes |
|----|-------|----------|-------|
| AR-RES-01 | After explicit ELISA add on a received sample, typed number on IgG | Persist lock: `reported_result` + qualifiers | Results slice — not minted at receive |
| AR-RES-02 | After explicit viability add, typed number on analyte missing `units_default` | **422** | Results slice |

### Automated only (pytest)

| ID | Steps | Expected |
|----|-------|----------|
| AR-T1 | Phases 1–3 pytest (`test_atomic_receive_phase*.py`) | Rollback / 409 / RBAC / **non-empty `analysis_ids` → 422** with zero rows / empty or omitted `analysis_ids` → 201 with `tests: []` / field hygiene |

## Sign-off

**CORE Pass** — 2026-08-27 — Grok browse + API (`ebac94e`)

**CORE pass** requires CORE must-pass rows above (not AR-RES).  
QA1–QA6, QA8–QA10 in `.docs/review/qa-review/atomic-receive.md` apply to CORE. QA7 = results follow-on.

### Concerns (non-blockers)

1. **AR-MU-01 status code:** cross-client `project_id` returns **404** (project not visible under RLS), not **403**. Access still denied.
2. **`client_sample_id` on GET:** value persists in DB and on receive, but `GET /samples/{id}` serializes `client_sample_id: null` (list/detail response gap).
3. **Create Sample** on Samples page correctly routes to `/receive` (regression check from post-merge fix).

## Cutover

| Script | Status after CORE docs sync |
|--------|------------------------------|
| **`uat-atomic-receive.md`** | **Receive happy-path SoT** |
| `uat-sample-accessioning.md` | **Demoted** — legacy wizard only; not receive sign-off |
| `uat-sample-status-editing.md` | Do not require Reviewed/Reported on Sample.status for CORE (Q1 parallel) |
