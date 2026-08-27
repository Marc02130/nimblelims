# Architecture Review: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept** (on CORE, **with conditions**)  
**Scope:** AR CORE — identity + **1..N** vessels; **refuse `analysis_ids`**; **no Test mint at receive**  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../requirements/atomic-receive.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [CEO](../ceo-review/atomic-receive.md) · [UI](../ui-review/atomic-receive.md) · [Security](../security-review/atomic-receive.md)  
**Gate memo:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**WO-7:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md)  
**Schema:** no new tables / no new columns for CORE (no `schema-changes/atomic-receive.md`)

## Executive summary

Historical packet Architecture **Accept** (PR 30) still stands for two identities, short receive body, existing tables, 409 on `containers.name`, and Available for Testing.

This stamp is the **CORE fold**. Implement follows PRD **1..N**, not “first vessel.” One `POST /samples/receive`, one txn: Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample** (true extra vessels, not daughter Samples). Any barcode collision (in the request or in the DB) → **409 + full rollback**. AuthZ = sample create + project RLS (PR 68) on the **whole txn**. Mass/conc stay off Sample.

**WO-7 hole closed for CORE.** `_create_asked_for_tests` is a **fail**. Empty `analysis_ids` as happy path is **not** enough. CORE **refuses** `analysis_ids` — **no Test mint at receive**. **Refuse (sketch pick):** if `analysis_ids` is present and non-empty → **422** (do not mint Tests, do not persist asked-for analyses). Empty or omitted is the only accepted path. Do **not** ignore. Do not add `work_order` or a new asked-for store in this packet. Classic Test+Result with no LimsRun still exists — do not silently kill it in stories. Test row at LimsRun start is **WO-7**, a later packet.

Results persist lock remains **design SoT for a follow-on slice**, not a CORE ship condition. Coding stays Grok Build. **Hold merge** until UAT + dogfood. **PR 71 stays draft.** Not IC50.

**Verdict: Accept** on CORE **with these conditions**.

## CORE architecture (locked)

| Lock | Detail |
|------|--------|
| **One API** | `POST /api/samples/receive` only |
| **One txn** | Sample + **1..N** 1×1 Containers + Contents (each → same Sample). **Zero Tests.** |
| **Vessels** | Primary barcode required + optional additional barcodes. Extra vessels are **not** daughter Samples. |
| **Identities** | `containers.name` = barcode; `samples.name` = system template. C1 gone. |
| **Collision** | Any barcode collision in request or DB → **409** + full rollback |
| **Status** | Available for Testing; `received_date`; no Received hop; no `status_history` |
| **AuthZ** | Same as sample create + project RLS (`has_project_access` / `lims_app`) on the **whole txn** |
| **`analysis_ids`** | **Refuse.** Present and non-empty → **422**. Empty or omitted only. `_create_asked_for_tests` is a fail. Ignore is not the pick. |
| **Tables** | Existing only. No new tables/columns. No `results.unit_id`. Mass/conc stay off Sample. |
| **Merge** | Hold until UAT + dogfood. PR 71 stays draft. |

## Bounce (fails Architecture CORE Accept)

- Orphan multi-call (create sample → create container → link)
- Single-vessel-only
- Sample-ID field / C1
- Received hop
- Project auto-create
- Tube picker
- Analysis as work plan / `_create_asked_for_tests` / ignore non-empty `analysis_ids`
- `work_order` / extract-hold / wizard revival
- Second receive API
- Results as CORE ship
- New tables
- Extra vessels as daughter Samples
- Mass/conc on Sample
- Method = dest
- IC50
- Partial commit on barcode collision
- AuthZ regression vs PR 68

## Follow-on (not CORE)

Typed number → `results.reported_result` + `qualifiers`; `raw_result` may copy. Unit from `analytes.units_default`; missing → 422. No `results.unit_id`. **Not** a CORE UAT or ship blocker.

Test at **LimsRun start** (WO-7). Classic Test+Result with no LimsRun still exists.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** (with conditions) |
| **Date** | 2026-08-26 |
| **Named scope** | AR CORE — identity + **1..N** vessels; refuse `analysis_ids` |
| **Schema** | No new tables / no new columns |
| **Merge** | Hold until UAT + dogfood. PR 71 stays draft. |
| **Not licensed** | Results-entry implement · extract-hold · work_order · Test mint at receive · IC50 |

```
ARCHITECTURE REVIEW: Accept
SCOPE: AR CORE (identity + 1..N vessels; refuse analysis_ids)
CONDITIONS: hold merge until UAT + dogfood; PR 71 stays draft
```
