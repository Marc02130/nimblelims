# Manual: Asked-for (requested analysis)

**Status:** P1 lake shipped. P2 Route / work_orders / WO-7 surfaces are on `feat/work-order-p2`. Dest-follow execute SHA **`1572071`**. UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute). Signed AC-P2-9..11 history: `9342439`. Deiter Contents click on product `4671ba8` / assignment commit `02fe95f` (`0077`): C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Leadership Confirmed that click; C1/C2 are **not** unsigned. C2 Fail history: dest not on the process; emptied source still assignable (**201**) is leftover process-join; later Start rode the emptied parent; **PATCH is not a path**. Docs Confirm `84d2810` is not a new execute and not the click SHA. Tobias QA **Pass** on **`bf51b19`**: C1/C2/C3 dest-follow, cardinality 1, freeze skip NULL, Route two-accept **409**, seq-1 (two WOs; dest-cohort **1.2 / OQ-WO-7 not scored**). Execute joints remain **`1572071`**. Do **not** teach `570bbc0` as a product execute SHA. **OQ-WO-6 extract CLOSED** for the common path (not a forever ban). **Marc lock 2026-09-01:** care about the asked-for only. **Leadership Confirm 2026-09-01 (Rolf/Deiter/Hans/Heidi/Günter):** ELISA is not on DNA (do not hang ELISA on DNA dest after C3); second blood tube (Contents) own asked-for + route; two tubes → two process assignments (`container_id`). Extracted DNA may have Qubit/Nanodrop; extract-as-LimsRun later. **OQ-WO-6 still:** asked-for `analysis_id` once on assay LimsRun, not extract. **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** not recoded. After C3, DNA WGS freezes WO params, **not** `{}`. P2 on `main` (`5040f2d`). Closeout **1.4 / OQ-WO-8** is **Marc lock, pending Leadership Confirm:** Quantified DNA is the asked-for; Qubit is the asked-for LimsRun; other process QC supporting. Send: [`.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md`](../.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md). **Overall P2 unsigned / not Pass.** Stack down.
**UI:** `/asked-for` — sidebar **Asked-for** (listed after **Receive**; nav order only, not a work queue) · sample-detail **Asked-for** section · **Route** CTA on `requested`  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel` · `POST /v1/asked-for/{id}/route` · `POST /v1/asked-for/route`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../UAT_Scripts/uat-post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../.docs/review/requirements/post-receive-work-spine.md) **RQ-AF-***  
**Sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../.docs/review/tech-sketch/post-receive-work-spine.md) §3

**Current Quantified DNA lock — Leadership Confirm 2026-09-02:** Reuse existing **Qubit** on exactly one named asked-for LimsRun slot; Test `(DNA, Qubit)` is the ask. Do not create a Quantified DNA analysis. Extract stays experiment with no `analysis_id` or boolean Result. Zero LimsRuns → **422**. WGS/WES/ELISA keep Qubit as process QC. Route must compare against the named slot, not any chain containing Qubit. Old tube-only / zero-LimsRun 1.4 is struck.

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
| Wrong pairings | A map holds TAT + ordered `process_definition[]` + one named asked-for LimsRun slot selected from that route. There is no free-form catalog-analysis or sample-type picker. Route compares the request with the named slot, not any matching analysis elsewhere in the chain. For Quantified DNA the named slot uses existing Qubit; for WGS/WES/ELISA, Qubit remains process QC. Missing slot or zero LimsRuns → **422**. |
| Route | Explicit Route requires `test:assign` plus project access. **Tobias-signed Pass on `8cfa2a9`:** zero acceptable → **422**. Two-accept **409** unsigned that SHA. Exactly one mints a queued work order and sets `routed`. Route does not start processes. |
| Params | Freeze onto `tests.asked_for_params` at first LimsRun start. Freeze skip NULL is Tobias Pass on `bf51b19`. **OQ-WO-7 Closed:** lookup remains WO asked-for only when `asked.analysis_id == run.analysis_id`, else parent lineage, else `{}`; do not recode. **OQ-WO-8 Closed:** Quantified DNA uses existing Qubit in the named asked-for slot. |

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

**Precondition, not step 1:** the sample was already received on `/receive` (identity + 1..N vessels), status **Available for Testing**, zero Tests. That receive loop is finished and stamped on its own ([`UAT_Scripts/uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md)). Extra vessels on the same Sample are extra containers, not daughter Samples. **Leadership Confirm:** a second blood tube **may** carry a **different** asked-for + route than the first (open uniqueness remains `(sample, analysis)`). Two blood tubes → two process assignments (`container_id`).

1. Open **Asked-for** (`/asked-for`) or the sample-detail Asked-for section as its own task.  
2. **Record requested analysis**: pick sample(s), pick an active analysis, TAT ≥ 1. Leave params empty — `{}` is the P1 path.  
3. Save. Stay on `/asked-for`. Toast: requested analysis recorded. No navigation to Tests.  
4. `COUNT(tests)` and `COUNT(work_orders)` for those requests are still 0. Sample stays **Available for Testing**.

One operator action may target a **set** of samples (same analysis + TAT). API still writes one row per sample.

**Not on this surface:** TestForm, Create test, Start, Execute, results entry, analysis picker on receive. **Route** is on this page; it does not start a process or mint a Test.

---

## Routing later (P2)

Do not chain this section onto Receive or onto the save steps above. Return to `/asked-for` later when work planning happens.

1. For one `requested` row, choose **Route**. For several requested rows, select them and choose **Route selected**. Each asked-for Routes onto **its** map. Two tubes of the same Sample that are both in play keep **separate** process assignments (`container_id`) after Start. ELISA route and WGS/extract route stay apart.
2. P2 matches TAT and first-step type, then requires the requested analysis to equal the analysis of the map’s **named asked-for LimsRun slot**. For Quantified DNA, that slot is existing Qubit. A WGS route that merely contains Qubit as process QC is not eligible.
3. Zero acceptable rows returns **422**; two saved rows that both accept this type and this analysis return **409**. The row stays `requested`, with no work order or Test.
4. Exactly one acceptable row **snapshots the ordered list**, creates a queued work order, changes the row to `routed`, and still creates **zero Tests**.
5. Experiments → **Work Orders** is the backlog. **First Start instantiates `chain[0]` only** and assigns the receive **container-with-sample**. Deiter C1 **Pass** on `02fe95f` verifies no-vessel/two-vessel **422** and receive-tube **201**. Deiter C2 **Fail** on `02fe95f` is signed history. The dest-type split is **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter). C2 numbered on **`570bbc0`**; execute **`1572071`** is **same-type dest-follow only**; Tobias **Pass** on **`bf51b19`** (`570bbc0` does **not** inherit `1572071` C2 Pass or Fail): same dest type = same sample, additional container, and only this path may retarget `container_id`. **C3** numbered on `570bbc0`; execute **`1572071`** is the different-dest-type click; Tobias **Pass** on `bf51b19`: new derivative sample in a new container (`parent_sample_id`); the parent **Sample row** stays as lineage with its original type, Tests, and parent-type work. **Fail C3 if dest tube is on the blood sample.** Type-changing execute mints and joins the destination pair and marks the inbound source assignment `removed` in the same transaction; only the destination pair continues on the process. Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Dest type on the plan is catalog intent until execute; dest exists only after aliquot/pool execute. Do not rewrite or retarget the parent Sample for type-changing execute. C2 and C3 / extract-hold UAT 1.7 remain two clicks. Do not teach dest-follow as shipped. **PATCH is not a path**.
6. WO-7 lock: `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a freeze marker. Until then `{}` is **ambiguous**. First LimsRun start of the asked-for analysis **writes** `asked_for_params`. **OQ-WO-6 extract CLOSED.** Extract is a process. If any cohort sample lacks an active Test at publish, **422** refuses the whole run.

Publish refuse is Tobias-signed Pass on `8cfa2a9`; freeze skip NULL is Tobias Pass on `bf51b19`. **OQ-WO-7 Closed** on `80f054b`; its lookup remains unchanged. **OQ-WO-8 Closed** by Leadership Confirm 2026-09-02. Overall P2 remains unsigned; historical stamps remain signed history.

Route compares current type with the first ordered step and compares the requested analysis with the map’s named asked-for slot. Missing/invalid slot or zero LimsRuns returns **422**. Two acceptable rows return **409**; never silently use `first()`. Supporting-QC containment does not qualify a route. Map-save handoff and sequential-WO rules remain unchanged.

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
