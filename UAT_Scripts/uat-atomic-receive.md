# UAT: Atomic receive (CORE happy path)

**Stem:** `atomic-receive`  
**Phase:** CORE implement shipped on branch `feat/atomic-receive-core` (Phases 1–4)  
**SoT:** PRD RQ-AR-* · SPEC §3 · `.docs/review/tech-sketch/atomic-receive.md`  
**QA review:** `.docs/review/qa-review/atomic-receive.md`  
**UI:** `/receive` (`AtomicReceive.tsx`) — sidebar **Receive**  
**API:** `POST /api/samples/receive`  
**Test data:** migration 0058 actors/projects + 0060 lists; catalog [atomic-receive/](atomic-receive/)  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000. UI click 2026-08-28: compose **down** after the run.  
**Build / commit:** API `ebac94e` (2026-08-27) · UI `33fbcb1` (2026-08-28, main merge of PR 75 wizard removal)  
**Executor:** Anton (API CORE 21/21, 2026-08-27) · Tobias (UI CORE click `/receive` as `alice-tech`, 2026-08-28)  
**Date:** 2026-08-27 (API) · 2026-08-28 (UI)  

**Run notes:** API stamp used Anton 21/21 on `ebac94e` (seed barcodes as catalog). UI click 2026-08-28 used catalog `NBIO-AR-0001` then `NBIO-AR-0002` as `alice-tech`. Matrix is not on the receive form (sample type is SoT). AR-VAL-01 remains Anton API only (UI required-field validation was not separately clicked).

This script is the **receive happy path** sign-off. The `/accessioning` wizard is removed (`uat-sample-accessioning.md` retired). `/accessioning` redirects to `/receive`. No 3-step wizard. Backend `POST /samples/accession` may still exist for pytest — not the UI happy path; do not treat that as a UI fail.

**CORE must-pass:** identity + **1..N vessels**, sticky project, Available for Testing, **zero Tests / zero Results** at receive, AuthZ (PR 68). Non-empty `analysis_ids` → **422**.
**Follow-on (not CORE blockers):** AR-RES-01/02 results-entry. **A-15 asked-for** is P1 on `/asked-for` (`uat-post-receive-work-spine.md`) — **not** on receive. Receive still mints zero Tests.

**This stamp:** **API CORE Accept (21/21)** (2026-08-27, `ebac94e`). **UI CORE Pass** (2026-08-28, `33fbcb1`). Do **not** collapse into one undifferentiated Pass.

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
- Sidebar **Sample Mgmt** for `alice-tech`: Receive, Samples, Tests, Containers, Batches, Results. **No Accessioning** item. **Receive** → `/receive` for users with `sample:create`.
- `/accessioning` redirects to `/receive`. No 3-step wizard.
- Not IC50. Compose down after the UI click.

## Cases — CORE must-pass

| ID | Steps | Expected | Pass/Fail | Notes |
|----|-------|----------|-----------|-------|
| AR-HV-01 | Log in as `alice-tech`. Open **Receive** (`/receive`). Scan `NBIO-AR-0001`. Sticky Plasma / Plasma (K2EDTA) / mAb-2301. Submit. Immediately scan `NBIO-AR-0002` without navigating away. | Both created. Stay on receive. Toast. Barcode clears and is focused. Type/matrix/project sticky. No sample-detail redirect. **No analysis picker.** No aliquot dialog. After each receive: **zero Tests**, **zero Results**. Extra barcodes would be more tubes of that sample. | **Pass** (API Pass / UI Pass) | API: Anton 21/21 (`ebac94e`). UI 2026-08-28 (`33fbcb1`): received `NBIO-AR-0001` then `NBIO-AR-0002`; stayed on `/receive`; toast `Received mAb-2301 PK Study-01/02 · 1 vessel`; barcode cleared; type/project/container sticky. No hop off receive. No aliquot dialog. |
| **AR-HV-MC** | Same sticky. Primary `NBIO-AR-MC-P`. Add additional barcodes `NBIO-AR-MC-A1` and `NBIO-AR-MC-A2`. Submit once. | **One** sample; **three** containers + contents → same sample; status Available for Testing; stay on form; **zero Tests**, **zero Results**. | **API Pass** | Anton 21/21. Tobias independent verify: 1 sample / 3 vessels. UI 2026-08-28: additional-barcodes field present (helper: not an aliquot). Three-vessel submit **not clicked** this UI run. |
| AR-HV-02 | Inspect `/receive` (no analysis picker). POST receive for `NBIO-AR-REFUSE-0001` with ELISA (Human IgG) in non-empty `analysis_ids`. Separately, confirm omitted or `[]` `analysis_ids` still succeed (AR-HV-01). | UI has **no analysis picker** and never sends `analysis_ids`. Non-empty `analysis_ids` → **422** before the transaction. No sample, container, contents, Test, or Result rows for `NBIO-AR-REFUSE-0001`. | **Pass** (API Pass / UI Pass) | API: Anton 21/21; non-empty `analysis_ids` → **422**. UI 2026-08-28: no analysis/test picker on `/receive`. |
| AR-HV-03 | Receive with temperature omitted. | Succeeds. Zero Tests. | **API Pass** | Anton 21/21. UI 2026-08-28: Temperature field present on `/receive`. Omit-temperature submit **not separately clicked**. |
| AR-HV-04 | Receive once with `client_sample_id`, once omitted. | Both succeed. Zero Tests. | **API Pass** | Anton 21/21. UI 2026-08-28: Client sample ID field present. Dual with/without submit **not separately clicked**. |
| AR-HV-05 | Type barcode `NBIO-AR-KB-0001` (no scanner). Submit. | Same success; `containers.name` = typed barcode; zero Tests. | **API Pass** | Keyboard. Anton 21/21. UI 2026-08-28: keyboard-only barcode submit **not separately clicked**. |
| AR-VAL-01 | Four POSTs/UI submits, each missing one required: barcode, type, matrix, project. | Each → **422** (or UI validation). No sample/container row. | **API Pass** | Anton 21/21 only. UI required-field validation **not separately clicked** 2026-08-28. Matrix is not on the form. |
| AR-DUP-01 | Replay `NBIO-AR-0001` after it exists. | **409**. Toast. Stay on receive. No second sample. | **Pass** (API Pass / UI Pass) | API: Anton 21/21; replay → **409**. UI 2026-08-28: replay `NBIO-AR-0001` → inline error + toast `Container barcode already exists: NBIO-AR-0001`; stayed on `/receive`. |
| AR-ID-01 | Inspect `/receive` form and AR-HV-01 response. | **No sample-ID field**. `samples.name` ≠ barcode (unless template coincides). `containers.name` = barcode. No status / tube-type / analysis fields. | **Pass** (API Pass / UI Pass) | API: Anton 21/21; names from template. UI 2026-08-28 fields: Primary barcode, additional barcodes (helper: not an aliquot), Sample type, Project, Container type, Temperature, Client sample ID. **No** lab Sample ID field. **No** analysis/test picker. **No** aliquot dialog. Names from template, not barcode. |
| AR-ST-01 | Inspect sample from `NBIO-AR-0001`. | Status = **Available for Testing**. `received_date` set. No Received hop. Zero Tests. | **API Pass** | QA4. Anton 21/21. Tobias independent verify: Available for Testing; `received_date` set; zero Tests. UI 2026-08-28: zero Tests at receive (WO-7). Observation (not a fail): `/samples/:id` still renders the Samples list (header says Edit Sample) rather than a detail hop from receive. |
| AR-TST-01 | Inspect the sample from `NBIO-AR-0009` immediately after receive, then add ELISA later via the separate tests UI/API. | Zero Tests and zero Results immediately after receive. The later explicit add creates the test with its normal pending status. | **Pass** (API Pass / UI Pass) | API: Anton 21/21; later `POST /tests/` ELISA. UI 2026-08-28: zero Tests minted at receive (WO-7). Later add-test path **not separately clicked** this UI run. |
| AR-TST-02 | DELETE that test (no results). | DELETE succeeds. | **API Pass** | QA6 / A-14. Anton 21/21. Not clicked 2026-08-28. |
| AR-TST-03 | After an explicitly added test has results, DELETE it. | **400**. Test and result remain. | **API Pass** | QA6 / A-14. Anton 21/21. Not clicked 2026-08-28. |
| AR-RBAC-01 | Log in as `david-cro`. Open Receive or POST `/samples/receive`. | No receive UI, or **403**. | **Pass** (API Pass / UI Pass) | API: Anton 21/21; `david-cro` POST → **403** (`sample:create` required). UI 2026-08-28: `david-cro` has **no Receive nav**. Direct `/receive` URL session-restore was **inconclusive** — noted; do **not** Fail UI CORE on that. |
| AR-MU-01 | alice receives on mAb; bob on CAR-T; then reverse project_id. | Happy path OK (zero Tests at receive); reverse → **403**. Observed this API run: reverse → **404** Project not found. **403 or 404 both refuse** (no row). | **API Pass** | QA8. Anton 21/21. Tobias independent verify: reverse project → **404** (refuse). Expected column still lists **403**; do not treat 404 as a silent spec rewrite. UI 2026-08-28: reverse-project POST **not clicked**. |

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
**UI CORE Pass** — Tobias, 2026-08-28, `33fbcb1` (clicked `/receive` as `alice-tech`).

Do **not** read this as one undifferentiated Pass. API Accept and UI Pass are separate dated stamps.

**CORE pass** requires CORE must-pass rows above (not AR-RES).  
QA1–QA6, QA8–QA10 in `.docs/review/qa-review/atomic-receive.md` apply to CORE. QA7 = results follow-on.

Verified holds (Anton API, 2026-08-27): HV-01 `NBIO-AR-0001` / `0002`; HV-MC 1 sample / 3 vessels; zero Tests (WO-7); `samples.name` from template; DUP 409; non-empty `analysis_ids` 422; `david-cro` POST 403; MU reverse **404** refuse. AR-VAL-01 is Anton 21/21 only.

Verified holds (Tobias UI, 2026-08-28, `33fbcb1`): `/accessioning` → `/receive`; no Accessioning nav; HV-01 stay-on-form + toast + sticky + barcode clear; DUP toast + stay; no sample-ID field; no analysis/test picker; no aliquot dialog; names from template; zero Tests at receive; `david-cro` no Receive nav. Direct `/receive` as `david-cro` inconclusive (not a UI CORE Fail). `/samples/:id` list render is an observation, not a fail. `/samples/accession` for pytest is not a UI fail. Not IC50. Compose down after the run.

### Concerns (non-blockers)

1. **AR-MU-01 status code (API stamp):** cross-client `project_id` returns **404** (project not visible under RLS), not **403**. Access still denied. Keep this API observation; do not treat 404 as a silent spec rewrite.
2. **`/samples/:id` (UI 2026-08-28):** still renders the Samples list (header says Edit Sample) rather than a detail hop from receive. Observation only — receive itself stayed on `/receive`.
3. **Create Sample** on Samples page correctly routes to `/receive` (regression check from post-merge fix).
4. Closed PR **#73** stamped API-only / “UI not run” on `ebac94e`. That UI-not-run language is **cleared** by this **UI CORE Pass** on `33fbcb1`. Do not revive “UI not Met.”

## Cutover

| Script | Status after CORE docs sync |
|--------|------------------------------|
| **`uat-atomic-receive.md`** | **Receive happy-path SoT** |
| `uat-sample-accessioning.md` | **Retired** — wizard removed; `/accessioning` redirects to `/receive` |
| `uat-sample-status-editing.md` | Do not require Reviewed/Reported on Sample.status for CORE (Q1 parallel) |
