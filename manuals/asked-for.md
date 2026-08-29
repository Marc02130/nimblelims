# Manual: Asked-for (requested analysis)

**Status:** P1 lake (this stamp). Route / work_orders / WO-7 / param freeze at LimsRun start are **not** this stamp.  
**UI:** `/asked-for` — sidebar **Asked-for**, immediately after **Receive** · sample-detail **Asked-for** section  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../UAT_Scripts/uat-post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../.docs/review/requirements/post-receive-work-spine.md) **RQ-AF-***  
**Sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../.docs/review/tech-sketch/post-receive-work-spine.md) §3

P1 is the **asked-for lake**. After receive, an analyst records **requested analysis**. That does **not** assign a Test, mint a Test row, or start work.

---

## Product lock (do not drift)

| Lock | Rule |
|------|--------|
| Copy | **Asked-for** / **requested analysis** / **Record request**. Never “assign test,” “create test,” “start work,” or “order process.” No Start / Execute on `requested`. |
| Receive freeze | Non-empty `analysis_ids` on `POST /samples/receive` → **422**. Empty or omit → zero Tests. No analysis picker on `/receive`. |
| Lake ≠ Test | Asked-for create leaves `COUNT(tests)` unchanged. |
| Not this stamp | Route, `work_orders`, WO-7 Test-at-LimsRun-start, results persist, SOP Apply. |
| Params | `analysis_param_defs` and freeze onto a Test happen later (**LimsRun start**). Do **not** collect or assign params on receive. P1 records analysis + TAT; empty `params` `{}` is the P1 path. |

---

## Who

| Role | Access |
|------|--------|
| Lab tech / manager with `test:assign` and project access | Create and cancel while `status=requested` |
| `sample:read` | List / get rows for samples they can see |
| Client | Cannot write (**403**). No create CTA. |
| Hidden / other-project sample | **403**, not 404 |

---

## After receive

1. Receive on `/receive` (identity + 1..N vessels). Sample status **Available for Testing**. Zero Tests.  
2. Open **Asked-for** (`/asked-for`) or the sample-detail Asked-for section.  
3. **Record requested analysis**: pick sample(s), pick an active analysis, TAT ≥ 1.  
4. Save. Stay on `/asked-for`. Toast: requested analysis recorded. No navigation to Tests.

One operator action may target a **set** of samples (same analysis + TAT). API still writes one row per sample.

**Not on this surface:** TestForm, Create test, Start, Execute, Route, work order, results entry, analysis picker on receive.

---

## Status (P1)

| Status | Meaning |
|--------|---------|
| `requested` | Open requested analysis. P1 writes this. |
| `cancelled` | Cancelled while `requested`. Unique index ignores cancelled; re-create is allowed. |
| `routed` | **Not this stamp** (P2). P1 does not write it. |

---

## Errors

| Case | HTTP |
|------|--------|
| Duplicate open `(sample, analysis)` | **409** (full rollback) |
| No project access / client write / hidden sample | **403** |
| Discarded sample / inactive analysis / TAT &lt; 1 | **422** |
| Receive with non-empty `analysis_ids` | **422** (receive freeze; not an asked-for call) |

---

## Related docs

- Receive (CORE freeze): [atomic-receive.md](atomic-receive.md)  
- Intake stub: [accessioning-workflow.md](accessioning-workflow.md)  
- API: [api-endpoints.md](api-endpoints.md)  
- Nav: [navigation.md](navigation.md)  
- Spine (P2–P5 specified, not shipped): [requirements/post-receive-work-spine.md](../.docs/review/requirements/post-receive-work-spine.md)
