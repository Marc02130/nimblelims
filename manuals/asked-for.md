# Manual: Asked-for (requested analysis)

**Status:** P1 lake shipped. **P2 Route / work_orders / WO-7** are on this slice.  
**UI:** `/asked-for` — sidebar **Asked-for** (listed after **Receive**; nav order only, not a work queue) · sample-detail **Asked-for** section · **Route** CTA on `requested`  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel` · `POST /v1/asked-for/{id}/route` · `POST /v1/asked-for/route`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../UAT_Scripts/uat-post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../.docs/review/requirements/post-receive-work-spine.md) **RQ-AF-***  
**Sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../.docs/review/tech-sketch/post-receive-work-spine.md) §3

P1 is the **asked-for lake**. An analyst records **requested analysis + TAT** against an already-received sample. That is all a saved row is: it does **not** assign a Test, mint a Test row or `work_order`, attach analytes, make type-a-number legal, or start work. **Route is a separate, later P2 action.**

**Receive ≠ order ≠ work.** This is a **later look-up**, not a step in the receive motion and not the click after a commit. Receive’s own happy path is to stay on `/receive` and scan the next tube ([atomic-receive.md](atomic-receive.md)); nothing at the bench waits on a request being typed.

---

## Product lock (do not drift)

| Lock | Rule |
|------|--------|
| Copy | **Asked-for** / **requested analysis** / **Record request**. Never “assign test,” “create test,” or “order process.” **Route** is allowed on `requested`. No Start / Execute on the asked-for page. |
| Receive freeze | Non-empty `analysis_ids` on `POST /samples/receive` → **422**. Empty or omit → zero Tests. No analysis picker on `/receive`. |
| Lake ≠ work | Asked-for create leaves `COUNT(tests)` and `COUNT(work_orders)` unchanged. Save is not scientific assignment or routing: no Test, no work order, no analytes, no legal number entry. |
| Not a queue | Asked-for is a look-up, not the after-receive click and not a Start queue. Do not document receive → asked-for as one motion. |
| Wrong pairings | The lake accepts them on purpose (e.g. Qubit on blood). Refusal is **routing** (`route_sample_type` **422**) on map save and Route. |
| Route | Explicit Route. Empty map → 200 `no_route`. Match mints queued `work_orders` and sets `routed`. The mint is planning, not work started. Still zero Tests. |
| Params | Freeze onto `tests.asked_for_params` at **LimsRun start** (WO-7). Do **not** collect params on receive. |

---

## Who

| Role | Access |
|------|--------|
| Lab tech / manager with `test:assign` and project access | Create and cancel while `status=requested` |
| `sample:read` | List / get rows for samples they can see |
| Client | Cannot write (**403**). No create CTA. |
| Hidden / other-project sample | **403**, not 404 |

---

## Recording a request (later look-up)

**Precondition, not step 1:** the sample was already received on `/receive` (identity + 1..N vessels), status **Available for Testing**, zero Tests. That receive loop is finished and stamped on its own ([`UAT_Scripts/uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md)).

1. Open **Asked-for** (`/asked-for`) or the sample-detail Asked-for section as its own task.  
2. **Record requested analysis**: pick sample(s), pick an active analysis, TAT ≥ 1. Leave params empty — `{}` is the P1 path.  
3. Save. Stay on `/asked-for`. Toast: requested analysis recorded. No navigation to Tests.  
4. `COUNT(tests)` and `COUNT(work_orders)` for those requests are still 0. Sample stays **Available for Testing**.

One operator action may target a **set** of samples (same analysis + TAT). API still writes one row per sample.

**Not on this surface:** TestForm, Create test, Start, Execute, results entry, analysis picker on receive. **Route** is on this page; it does not start a process or mint a Test.

---

## Routing later (P2)

Do not chain this section onto Receive or onto the save steps above. Return to `/asked-for` later when work planning happens.

1. For one `requested` row, choose **Route**. For several requested rows, select them and choose **Route selected**.
2. P2 matches each row’s analysis, current sample type, and TAT against the configured map at `/admin/routing-map`.
3. No match returns `no_route`; the row stays `requested`, with no `work_order` or Test.
4. A match creates a queued `work_order`, changes the row to `routed`, and still creates no Test. This queue mint does not mean work has started.
5. Experiments → **Work Orders** (`/work-orders`) is the work backlog. **Start process** instantiates and opens the existing ELN process; it is not a second execution engine.
6. A later LimsRun start creates or attaches the Test and freezes `asked_for_params` (WO-7). The lock is that a missing required Test returns **422** and refuses the whole run without creating that Test or publishing partial Results. That refuse is **not** verified as shipped on `9c4f9da`.

The routing type gate fails closed: every mapped process-definition step must accept the current sample type. An empty accepted-type set or incompatible step returns **422** `route_sample_type`. That code means the requested analysis and current sample type are the wrong pairing for a mapped step; it does not mean the sample is broken. Saving an otherwise valid Qubit-on-blood request in the lake does not bypass that gate.

---

## Status (P1)

| Status | Meaning |
|--------|---------|
| `requested` | Open requested analysis. P1 writes this. |
| `cancelled` | Cancelled while `requested`. Unique index ignores cancelled; re-create is allowed. |
| `routed` | P2 Route matched a map and minted a work order. Cancel after routed is **422**. |

---

## Errors

| Case | HTTP |
|------|--------|
| Duplicate open `(sample, analysis)` | **409** (full rollback) |
| No project access / client write / hidden sample | **403** (not 404) |
| Discarded sample / inactive analysis / TAT &lt; 1 | **422** |
| Receive with non-empty `analysis_ids` | **422** (receive freeze; not an asked-for call) |
| Route, no map match | **200** `no_route`, status stays `requested` |
| Route / map save, sample type not accepted on a step | **422** `route_sample_type` (wrong type pairing; sample is not broken) |
| Cancel after `routed` | **422** |

---

## Related docs

- Receive (CORE freeze; its happy path is staying on `/receive`): [atomic-receive.md](atomic-receive.md)  
- Intake stub: [accessioning-workflow.md](accessioning-workflow.md)  
- API: [api-endpoints.md](api-endpoints.md)  
- Nav: [navigation.md](navigation.md)  
- Spine requirements and phased status: [requirements/post-receive-work-spine.md](../.docs/review/requirements/post-receive-work-spine.md)
