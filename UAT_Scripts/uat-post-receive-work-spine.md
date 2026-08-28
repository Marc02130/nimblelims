# UAT: Post-receive work spine — P1 asked-for

**Stem:** `post-receive-work-spine`  
**Phase:** P1 asked-for lake (P2–P5 **not** in this stamp)  
**SoT:** `.docs/review/requirements/post-receive-work-spine.md` RQ-AF-* · [asked-for.md](../.docs/review/manuals/asked-for.md)  
**UI:** `/asked-for` (sidebar **Asked-for**, immediately after Receive) + sample-detail Asked-for section  
**API:** `POST /api/v1/asked-for` · `GET /api/v1/asked-for` · `POST /api/v1/asked-for/{id}/cancel`  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000  
**Do not use** retired `uat-sample-accessioning.md`. Receive freeze: non-empty `analysis_ids` still **422**.

P1 records **requested analysis**. It does **not** assign a Test, mint a Test row, or start work. Copy: “Asked-for” / “requested analysis”. No Start / Execute.

**Out of this stamp:** Route, work_orders, WO-7 Test-at-LimsRun-start, `analysis_param_defs` on receive, results persist, SOP Apply, parser dry-run UX, Qubit/blood path.

**This stamp:** _(fill on dogfood / UAT pass — hold merge to `main` until pass)_

---

## Fixtures

| Need | Seed |
|------|--------|
| Actor | `lab-tech` / `alice-tech` with `test:assign` + sample/project access |
| Client | `client` / `david-cro` — cannot POST asked-for |
| Receive | One Available-for-Testing sample via `/receive` (ELISA-ready; **no** analyses on receive) |
| Analysis | Existing ELISA (Human IgG) from 0058. Do **not** invent Qubit/blood IDs |

---

## AC-P1-1 — Receive → ELISA requested analysis → zero Tests

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
- **422** `analysis_ids must be empty`. Zero samples/tests created. Params / param-defs are not on this call.

---

## Out of scope this stamp

Route, work_orders, LimsRun Test mint (WO-7), param defs on receive, results persist, SOP Apply rewrite, parser dry-run UX, Qubit/blood path.
