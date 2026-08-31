# Manual: Asked-for (requested analysis)

**Status:** P1 lake shipped. P2 Route / work_orders / WO-7 surfaces are on `feat/work-order-p2`. Live product SHA **`1572071`**. Signed AC-P2-9..11 history: `9342439`. Deiter Contents click on product `4671ba8` / assignment commit `02fe95f` (`0077`): C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Leadership Confirmed that click; C1/C2 are **not** unsigned. C2 Fail history: dest not on the process; emptied source still assignable (**201**) is leftover process-join; later Start rode the emptied parent; **PATCH is not a path**. Docs Confirm `84d2810` is not a new execute and not the click SHA. Live AC-P2-C2 on `1572071` is **unsigned** until Tobias (dest-follow in the execute txn — in code, not QA-clicked; do not teach dest-follow as shipped). Freeze skip **OPEN**; **OQ-WO-6 stays OPEN**. **Overall P2 unsigned / not Pass.** Hold product merge.
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
| Wrong pairings | Map create has no sample-type or analysis picker. A row holds TAT + ordered `process_definition[]`. A route **may have multiple LimsRun analyses**. Map save 409s when TAT, first-step allow-lists, **and** LIMS Run analysis **sets** overlap. Route assigns when current type is on the first process’s first ordered step **and** the asked-for analysis is **contained** in the route. |
| Route | Explicit Route requires `test:assign` plus project access. **Tobias-signed Pass on `8cfa2a9`:** zero acceptable → **422**. Two-accept **409** unsigned that SHA. Exactly one mints a queued work order and sets `routed`. Route does not start processes. |
| Params | Lock: freeze onto `tests.asked_for_params` at the **first LimsRun start** of the asked-for analysis (WO-7). `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until then `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`. **OQ-WO-6:** an earlier LimsRun must **not** share the asked-for `analysis_id` (extract is not special). Freeze skip stays **unsigned**. |

---

## Who

| Role | Access |
|------|--------|
| Lab tech / manager with `test:assign` and project access | Create and cancel while `status=requested`; Route a requested row |
| `sample:read` | List / get rows for samples they can see |
| Client | Cannot create, cancel, or Route (**403**, not 404). No create/Route CTA. |
| Hidden / other-project sample | **403**, not 404 |

Route itself does **not** require `experiment:manage`. **Start process** and LimsRun start do; publish requires `experiment:publish`.

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
2. P2 matches TAT, then keeps **any** route whose first process / first ordered Experiment/LimsRun accepts current type **and** whose chain **contains** a LimsRun for the asked-for analysis (the route may have other analyses).
3. Zero acceptable rows returns **422**; two saved rows that both accept this type and this analysis return **409**. The row stays `requested`, with no work order or Test.
4. Exactly one acceptable row **snapshots the ordered list**, creates a queued work order, changes the row to `routed`, and still creates **zero Tests**.
5. Experiments → **Work Orders** is the backlog. **First Start instantiates `chain[0]` only** and assigns the receive **container-with-sample**. Deiter C1 **Pass** on `02fe95f` verifies no-vessel/two-vessel **422** and receive-tube **201**. Deiter C2 **Fail** on `02fe95f` is signed history. Live C2 on **`1572071`** is **same-type dest-follow only** and remains unsigned until Tobias: same dest type = same sample, additional container. Different dest type = new derivative sample in a new container (`parent_sample_id`); the parent **Sample row** stays as lineage with its original type and parent-type work. For either grain, execute puts the destination sample + destination container pair on `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction. Do not rewrite or retarget the parent Sample for type-changing execute. Do not teach dest-follow as shipped. **PATCH is not a path**.
6. WO-7 lock: `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a freeze marker. Until then `{}` is **ambiguous**. First LimsRun start of the asked-for analysis **writes** `asked_for_params`. **OQ-WO-6:** an earlier LimsRun must **not** share that `analysis_id`. If any cohort sample lacks an active Test at publish, **422** refuses the whole run.

Publish refuse is **Tobias-signed Pass** on `8cfa2a9` (carol **422** `test_missing`) and remains history on `b005cfe`. Freeze skip stays **OPEN** — a write of `{}` onto `99b692d3` is not a skip Pass (`{}` is ambiguous). Empty Route **422** / map overlap **409** / 201-not-AND are Pass on `8cfa2a9`. Later-step type-gate **Met** on `9342439` (qPCR-on-blood / still-Blood **422**; not dest-type E2E). Overall P2 Pass remains unsigned; historical `9c4f9da` / `b005cfe` stamps remain signed history.

Route compares current type with the first process’s first ordered Experiment/LimsRun allow-list and requires the asked-for analysis **among** the LimsRun analyses in the route. No acceptable row returns **422**; type or missing-analysis refusal uses `route_sample_type`. Two saved rows that both accept this type and this analysis return **409**. Never silently use `first()`. Map save 409s when overlapping TAT, overlapping first-step allow-lists, **and** overlapping LimsRun analyses all hold; extract-first and Qubit-first for the same TAT must save when types or analyses differ. Map save and Route do not AND inbound type across later processes or steps. Map save **422**s when the type emerging from process *x* is not accepted by process *x+1*. Start instantiates only the first process. Same-type Later Start follow is the lock on **`1572071`**, **unsigned** until Tobias. Different dest type mints a derivative sample with `parent_sample_id`; the parent Sample row stays, while the destination sample + container pair replaces the inbound source assignment on the process in the execute transaction. Deiter C2 **Fail** on `02fe95f` is signed history. The dest mint Hold **Pass** on `02fe95f` is Start-extract Blood / **0 DNA** history, not a ban on type-changing execute minting a derivative.

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
| Route, zero acceptable rows | **422**, status stays `requested`; type or missing LIMS Run analysis uses `route_sample_type` |
| Route, two saved rows both accept current type and asked-for analysis | **409**; no silent `first()` |
| Map save, overlapping TAT + overlapping first-step allow-lists + overlapping LIMS Run analyses | **409** |
| Map save, overlapping TAT, disjoint first-step lists or disjoint LIMS Run analyses | **201** (extract-first vs Qubit-first, or two analyses sharing extract types, is legal) |
| Later step start, current sample type not accepted or allow-list empty | **422** `route_sample_type` |
| Map save, process *x* emerging type not accepted by process *x+1* | **422** `route_sample_type` |
| Cancel after `routed` | **422** |

---

## Related docs

- Receive (CORE freeze; its happy path is staying on `/receive`): [atomic-receive.md](atomic-receive.md)  
- Intake stub: [accessioning-workflow.md](accessioning-workflow.md)  
- API: [api-endpoints.md](api-endpoints.md)  
- Nav: [navigation.md](navigation.md)  
- Spine requirements and phased status: [requirements/post-receive-work-spine.md](../.docs/review/requirements/post-receive-work-spine.md)
