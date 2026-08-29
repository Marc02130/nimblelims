# UAT: Post-receive work spine — P1 asked-for

**Stem:** `post-receive-work-spine`  
**Phase:** P1 asked-for lake (P2–P5 **not** in this stamp)  
**SoT:** `.docs/review/requirements/post-receive-work-spine.md` RQ-AF-* · [HOWTO.md](../manuals/HOWTO.md) §3  
**UI:** `/asked-for` (sidebar **Asked-for**, immediately after Receive) + sample-detail Asked-for section  
**API:** `POST /api/v1/asked-for` · `GET /api/v1/asked-for` · `POST /api/v1/asked-for/{id}/cancel`  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000. Compose **down** after the run. Not IC50. P1 lake only.  
**Build / commit:** `c649245` (`c6492455200fa69c2093865615f82ada23b8d2b1`, 2026-08-28)  
**Executor:** Tobias (clicked `/receive` then `/asked-for` as `alice-tech`) + API AC-P1-3/4  
**Date:** 2026-08-28  
**Do not use** retired `uat-sample-accessioning.md`. Receive freeze: non-empty `analysis_ids` still **422**.

P1 records **requested analysis**. It does **not** assign a Test, mint a Test row, or start work. Copy: “Asked-for” / “requested analysis”. No Start / Execute.

**Out of this stamp:** Route, work_orders, WO-7 Test-at-LimsRun-start, `analysis_param_defs` on receive, results persist, SOP Apply, parser dry-run UX, Qubit/blood path.

**This stamp:** **P1 Pass** on `c649245` — AC-P1-1..4. Merged to `main` (PR **#81**, `af5b388`). Do **not** write P2–P5 Pass. Do **not** collapse with receive CORE stamps (`uat-atomic-receive.md`).

---

## Fixtures

| Need | Seed |
|------|--------|
| Actor | `lab-tech` / `alice-tech` with `test:assign` + sample/project access |
| Client | `client` / `david-cro` — cannot POST asked-for |
| Receive | One Available-for-Testing sample via `/receive` (ELISA-ready; **no** analyses on receive) |
| Analysis | Existing ELISA (Human IgG) from 0058. Do **not** invent Qubit/blood IDs |

**This run:** receive barcode `NBIO-AF-P1-0001` → sample name `mAb-2301 PK Study-04`. Sticky Plasma / mAb-2301 PK Study / Cryovial. Hidden-sample API used `CAR-T-Batch-001`.

---

## AC-P1-1 — Receive → ELISA requested analysis → zero Tests

**Result:** **Pass** (click, 2026-08-28, `c649245`)

**Steps**
1. Log in as lab-tech. Sidebar Sample Mgmt: **Asked-for** is immediately after **Receive**.
2. Receive a sample on `/receive` (empty analyses; UI never sends `analysis_ids`). Status **Available for Testing**. Tests grid count for that sample is 0.
3. Open `/asked-for` → **Record requested analysis**. Multi-select the received sample. Pick ELISA. TAT ≥ 1 (default from analysis TAT is fine). Do **not** enter assay params (params freeze at LimsRun start later; not on receive).
4. Save.

**Expect**
- Row `status=requested`. Copy is “requested analysis”, never “assign test” / “start work”.
- No Start / Execute / Route CTA.
- `COUNT(tests)` for that sample unchanged (0). Asked-for does not start work.
- Sample detail shows the asked-for row under **Asked-for**.

**Verified holds (Tobias click, `alice-tech`):**
- Sidebar Sample Mgmt: **Receive**, then **Asked-for** immediately after.
- `/receive`: no analysis/asked-for picker, no lab Sample ID, no aliquot dialog. Received `NBIO-AF-P1-0001`; stayed on `/receive`; barcode cleared; sticky Plasma / mAb-2301 PK Study / Cryovial.
- `/asked-for` copy: “After receive, record what was asked for. This does not assign a test or start work.” CTA **RECORD REQUESTED ANALYSIS**. Modal: “Record a requested analysis. This does not assign a test or start work.” No Start / Execute anywhere.
- Recorded ELISA (Human IgG) on `mAb-2301 PK Study-04` (the receive of `NBIO-AF-P1-0001`). Grid shows requested row; after cancel+resave: one requested + one cancelled (1–2 of 2).
- Tests Management still 3 seed tests only (not minted for the new receive). No `work_orders` table.

**Observation (not a fail):** sample picker by raw barcode `NBIO-AF-P1-0001` showed “No options”; recording used the sample name.

## AC-P1-2 — Duplicate 409

**Result:** **Pass** (click, 2026-08-28, `c649245`)

**Steps**
1. Repeat AC-P1-1 save for the same sample + ELISA while the first row is still `requested`.

**Expect**
- **409**. No second open row. Cancel the first, then re-save → **201**.

**Verified holds:** second save same sample+ELISA while requested → banner “An open asked-for already exists for this sample and analysis” (**409**). Cancel first, resave → new requested row.

## AC-P1-3 — Cross-project 403

**Result:** **Pass** (API, 2026-08-28, `c649245`)

**Steps**
1. As lab-tech, POST `/api/v1/asked-for` with a sample_id from a project the user cannot access (or a hidden sample).

**Expect**
- **403** with project-permission wording, **not 404**.
- Client role POST → **403** even if the role were granted `test:assign`.

**Verified holds:**
- `alice-tech` POST `/v1/asked-for` on hidden `CAR-T-Batch-001` → **403** “Access denied: insufficient project permissions” (not 404).
- `david-cro` POST on alice sample → **403** “Client role cannot record asked-for” (seed still has `test:assign`).

## AC-P1-4 — Receive freeze (regression)

**Result:** **Pass** (API, 2026-08-28, `c649245`)

**Steps**
1. `POST /api/samples/receive` with non-empty `analysis_ids`.

**Expect**
- **422** `analysis_ids must be empty`. Zero samples/tests created. Params / param-defs are not on this call.

**Verified holds:** `POST /samples/receive` with non-empty `analysis_ids` → **422** “analysis_ids must be empty for Atomic Receive CORE”. No refuse barcode row.

---

## Out of scope this stamp

Route, work_orders, LimsRun Test mint (WO-7), param defs on receive, results persist, SOP Apply rewrite, parser dry-run UX, Qubit/blood path.

---

## Sign-off

**P1 Pass** — Tobias, 2026-08-28, `c649245` — AC-P1-1..4.

Click: `/receive` then `/asked-for` as `alice-tech`. API: AC-P1-3/4. Local compose; down after the run. Not IC50. P1 lake only.

Do **not** read this as P2–P5 Pass. Do **not** collapse this stamp with Atomic Receive **CORE** Pass (`uat-atomic-receive.md`). P1 is on `main` (PR **#81**).
