# UAT: Post-receive work spine — P1 asked-for

**Stem:** `post-receive-work-spine`  
**Phase:** P1 asked-for lake (P2–P5 not in this stamp)  
**SoT:** `.docs/review/requirements/post-receive-work-spine.md` RQ-AF-* · developer-review D1–D11  
**UI:** `/asked-for` (sidebar **Asked-for**, immediately after Receive) + sample-detail Asked-for section  
**API:** `POST /api/v1/asked-for` · `GET /api/v1/asked-for` · `POST /api/v1/asked-for/{id}/cancel` · `GET/PUT /api/analyses/{id}/param-defs`  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000  
**Do not use** retired `uat-sample-accessioning.md`. Receive freeze: non-empty `analysis_ids` still **422**.

P1 records **requested analyses**. It does **not** create Tests, Results, Processes, Experiments, LimsRuns, or work orders. Copy: “Asked-for” / “requested analysis”. No Start / Execute.

**This stamp:** _(fill on dogfood / UAT pass)_

---

## Fixtures

| Need | Seed |
|------|------|
| Actor | `lab-tech` / `alice-tech` with `test:assign` + sample/project access |
| Client | `client` / `david-cro` — cannot POST asked-for |
| Receive | One Available-for-Testing sample via `/receive` (ELISA-ready, no analyses on receive) |
| Analysis | Existing ELISA (Human IgG) from 0058. Do **not** invent Qubit/blood IDs |
| Params | Empty catalog is OOB (`params: {}`) |

---

## AC-P1-1 — Receive → ELISA asked-for → zero Tests / WOs

**Steps**
1. Log in as lab-tech. Sidebar Sample Mgmt: **Asked-for** is immediately after **Receive**.
2. Receive a sample on `/receive` (empty analyses). Status **Available for Testing**. Tests grid count for that sample is 0.
3. Open `/asked-for` → **Record requested analysis**. Multi-select the received sample. Pick ELISA. TAT ≥ 1 (default from analysis TAT is fine). Leave params empty if no defs.
4. Save.

**Expect**
- Row `status=requested`. Copy is “requested analysis”, never “assign test” / “start work”.
- No Start / Execute CTA.
- `COUNT(tests)` for that sample unchanged (0). No work_order table/UI.
- Sample detail dialog shows the asked-for row under **Asked-for**.

## AC-P1-2 — Duplicate 409

**Steps**
1. Repeat AC-P1-1 save for the same sample + ELISA while the first row is still `requested`.

**Expect**
- **409**. No second open row. Cancel the first, then re-save → **201**.

## AC-P1-3 — Cross-project 403

**Steps**
1. As lab-tech, POST `/api/v1/asked-for` with a sample_id from a project the user cannot access (or a hidden sample).

**Expect**
- **403** with project-permission wording, **not 404**.
- Client role POST → **403** even if the role were granted `test:assign`.

## AC-P1-4 — Receive freeze (regression)

**Steps**
1. `POST /api/samples/receive` with non-empty `analysis_ids`.

**Expect**
- **422** `analysis_ids must be empty`. Zero samples/tests created.

---

## Out of scope this stamp

Route, work_orders, LimsRun Test mint (WO-7), results persist, SOP Apply rewrite, parser dry-run UX, Qubit/blood path.
