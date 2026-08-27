# Requirements: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** CORE locks folded. Implement follows **1..N** + **refuse `analysis_ids`**. PR 71 stays **draft** pending UAT + dogfood. Not IC50.  
**Stem:** `atomic-receive`  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Architecture:** [`.docs/review/architecture-review/atomic-receive.md`](../architecture-review/atomic-receive.md) — **Accept** on CORE (with conditions)  
**UI:** [`.docs/review/ui-review/atomic-receive.md`](../ui-review/atomic-receive.md) — **Accept** on CORE (with conditions)  
**Security:** [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md) (PR 68)  
**WO-7:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md)  
**Leadership:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)

Coding stays Grok Build. **Hold merge** until UAT + dogfood. **PR 71 stays draft.**

## 1. Purpose

Atomic receive CORE is identity + **1..N vessels** in one transaction. One `POST /samples/receive` creates Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample**. Extra barcodes are extra vessels on the **same** Sample, not daughter Samples. No Test mint at receive.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| One `POST /samples/receive`, one txn: Sample + **1..N** 1×1 Containers + Contents → same Sample | Architecture / Leadership 2026-08-26 |
| Extra barcodes = more 1×1 Contents on the **same** Sample, **not** daughter Samples | Architecture CORE fold |
| Implement follows PRD **1..N**, not stale “first vessel” | Architecture / Leadership 2026-08-26 |
| Any barcode collision (request or DB) → **409 + full rollback** | Architecture / Lab Ops |
| AuthZ = sample create + project RLS (PR 68) on the **whole txn** | Heidi/Günter PR 68 |
| **WO-7 hole closed for CORE:** `_create_asked_for_tests` is a **fail**. Empty `analysis_ids` as happy path is **not** enough. CORE **refuses** `analysis_ids` — **no Test mint at receive** | WO-7 + Leadership 2026-08-26 |
| **Refuse (sketch pick):** if `analysis_ids` is present and non-empty → **422** (do not mint Tests, do not persist asked-for analyses). Empty or omitted is the only accepted path. Do **not** ignore | Sketch pick (this fold) |
| Do not add `work_order` or a new asked-for store in this packet | WO-7 / Leadership |
| Classic Test+Result with no LimsRun still exists — do not silently kill it in stories | WO-7 / CSO |
| Test row at LimsRun start is **WO-7**, a later packet | framework-stamps WO-7 |
| UI: new receive loop, not the wizard. Scan primary + optional extra barcodes. Sticky project/type/matrix. No sample-ID, no tube picker, no analysis-as-work-plan, no Received hop. Collision → 409, stay on the scan well | UI CORE fold |
| Hold merge until UAT + dogfood; PR 71 stays draft. Architecture Accept + UI Accept on CORE **with these conditions** | Leadership / this fold |
| Not IC50 | Marc |

## 3. Goals

- One API, one txn, **1..N** 1×1 vessels, all Contents → one Sample.
- Collision → 409 + full rollback. Stay on the scan well.
- AuthZ = sample create + project RLS on the whole txn.
- **Refuse** present non-empty `analysis_ids` → 422. Zero Tests at receive.
- New receive loop. Sticky project/type/matrix. No sample-ID, tube picker, analysis-as-work-plan, Received hop.
- Docs/UAT/dogfood before merge. PR 71 remains draft.

## 4. Non-goals

Orphan multi-call; single-vessel-only; sample-ID field / C1; Received hop; project auto-create; tube picker; analysis as work plan; `_create_asked_for_tests`; ignore non-empty `analysis_ids`; `work_order` / extract-hold / wizard revival; second receive API; results as CORE ship; new tables; extra vessels as daughter Samples; mass/conc on Sample; Method = dest; IC50; new asked-for store.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| **AC-AR-1** | `POST /api/samples/receive` is the only receive API. One DB transaction. |
| **AC-AR-2** | Primary barcode required. Optional additional barcodes (0..N). Each barcode → 1×1 Container + Contents → **the same Sample**. |
| **AC-AR-3** | Extra barcodes are **not** daughter Samples and **not** aliquot. |
| **AC-AR-4** | Any barcode collision in the request or in the DB → **409** + **full rollback**. Zero sample / container / contents rows. |
| **AC-AR-5** | `samples.name` from existing name template. Receive UI has **no sample-ID field**. C1 gone. |
| **AC-AR-6** | Status = **Available for Testing**; `received_date` set; no Received hop; no status picker. |
| **AC-AR-7** | `project_id` required and sticky. Never auto-create a project. |
| **AC-AR-8** | Default tube type for **all** vessels, off the form. No tube picker. |
| **AC-AR-9** | AuthZ = sample create + project RLS (PR 68) on the **whole txn**. Foreign project → 403, no row. |
| **AC-AR-10** | **`analysis_ids` omitted or `[]`:** accept; **zero Tests**. **`analysis_ids` present and non-empty:** **422**; do not mint Tests; do not persist asked-for analyses. |
| **AC-AR-11** | `_create_asked_for_tests` is a **fail**. Ignore is **not** accepted. |
| **AC-AR-12** | After success: stay on receive; toast; clear barcode field(s); sticky type/matrix/project; focus primary. |
| **AC-AR-13** | Collision 409: stay on the scan well. No partial commit. |
| **AC-AR-14** | No new tables / columns. Mass/conc stay off Sample. No `results.unit_id`. No `status_history`. |
| **AC-AR-15** | Classic Test+Result with no LimsRun still exists (not CORE receive; do not kill in stories). Test at LimsRun start = WO-7 later packet. |
| **AC-AR-16** | PR 71 stays **draft** until UAT + dogfood. |

## 6. Bounce (this packet / PR 71)

1. Orphan multi-call  
2. Single-vessel-only  
3. Sample-ID field / C1  
4. Received hop  
5. Project auto-create  
6. Tube picker  
7. Analysis as work plan / Test mint at receive / ignore non-empty `analysis_ids`  
8. `work_order` / extract-hold / wizard revival  
9. Second receive API  
10. Results as CORE ship  
11. New tables  
12. Extra vessels as daughter Samples  
13. Mass/conc on Sample  
14. Method = dest  
15. IC50  

## 7. Path exercised

Scan primary → optional extra barcodes → sticky project/type/matrix → one commit → Sample + N 1×1 Contents on that Sample → Available for Testing → stay on receive. Non-empty `analysis_ids` → 422, no row. Dup barcode → 409, stay on scan well.

## 8. Sign-off

| Review | Verdict |
|--------|--------|
| Architecture | **Accept** on CORE **with conditions** (1..N; refuse `analysis_ids`; hold merge / PR 71 draft) |
| UI | **Accept** on CORE **with conditions** (new loop; 409 stays on scan well; hold merge / PR 71 draft) |
| Security | **Accept with conditions** (PR 68) — AuthZ docs gate satisfied |
| Lab Ops | **Accept with conditions** (L2–L3; L1 retracted; L4 Test-at-receive superseded) |
| CEO | **Accept with conditions** (HOLD SCOPE) |

**Implement:** Grok Build on draft PR 71. **Merge hold** until UAT + dogfood. Not IC50.
