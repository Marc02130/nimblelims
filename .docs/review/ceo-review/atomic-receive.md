# CEO / Product Review: Atomic receive (AR CORE)

**Date:** 2026-08-26  
**Leadership lock:** 2026-08-26 — CORE receive creates **zero Tests**; **refuse** non-empty `analysis_ids`  
**Status:** Accept with conditions  
**Mode:** HOLD SCOPE  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../requirements/atomic-receive.md)  
**Lab Ops:** [`.docs/review/lab-ops-review/atomic-receive.md`](../lab-ops-review/atomic-receive.md)  
**Gate memo:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**Stamps:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md)  
**Security (AuthZ):** [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md) — docs gate satisfied (PR 68)

## Executive summary

Atomic receive CORE is the right product wedge: **identity + 1..N vessels in one transaction**, scan-first, two identities, sticky required project, Available for Testing on commit, AuthZ = sample create + project RLS on the whole txn.

HOLD SCOPE. Do **not** pull Test mint, results-entry, intake-profile engine, or `work_order` into this slice. **Refuse (sketch pick):** if `analysis_ids` is present and non-empty → **422**. Empty or omitted is the only accepted path. `_create_asked_for_tests` is a fail. Ignore is not the pick. Classic Test+Result with no LimsRun still exists — do not silently kill it in stories. Test at LimsRun start is WO-7, later.

**Merge hold.** UAT + dogfood required. **PR 71 stays draft.** Coding stays Grok Build. Not IC50.

## Scope freeze

| In (CORE) | Out |
|-----------|-----|
| One `POST /api/samples/receive` + **new** receive loop | Results entry as CORE must-pass |
| Sample + **1..N** 1×1 Containers + Contents, **one txn**; Contents → same Sample | Aliquot UI / daughter Samples |
| Primary + optional additional barcodes | Intake-profile engine / wizard revival |
| Any dup → **409** + full rollback; stay on the scan well | FieldDefinitions on receive body |
| System `samples.name`; **no sample-ID field** | `work_order` / routing / A-15 |
| Available for Testing; no Received hop | Second receive API |
| Sticky required project; never auto-create | Test mint at receive; ignore non-empty `analysis_ids` |
| Default tube off form; no tube picker | Mass/conc on Sample; Method = dest |
| **Refuse** present non-empty `analysis_ids` → **422**; zero Tests | IC50 |
| AuthZ = sample create + project RLS on whole txn | |
| Docs/UAT/dogfood before merge; PR 71 draft | |

## Conditions

| ID | Condition |
|----|-----------|
| **C1** | **Historical identity (retracted).** Two identities. No sample-ID field. |
| **C2** | Project required and session-sticky. Never auto-create. |
| **C3** | Default tube for **all** vessels, off the form. No tube picker. |
| **C4** | CORE creates **zero Tests**. **Refuse** present non-empty `analysis_ids` → **422**. Hide analyses picker. A-15 parked. DELETE-with-results → 400 for independently created tests. |
| **C5** | **1..N vessels** in one txn. Single-vessel-only fails CORE. Collision → **409** + full rollback. Extra vessels ≠ daughter Samples. |
| **C6** | Results-entry is **not** CORE acceptance. |
| **C7** | AuthZ = sample create + project RLS on the **whole txn**; one API; refuse orphan multi-call. |
| **C8** | Hold merge until UAT + dogfood. **PR 71 stays draft.** Fix remaining “first vessel” drift. |

## HOLD SCOPE — bounce

Orphan multi-call; single-vessel-only; sample-ID field / C1; Received hop; project auto-create; tube picker; analysis as work plan; `work_order` / extract-hold / wizard revival; second receive API; results as CORE ship; new tables; extra vessels as daughter Samples; mass/conc on Sample; Method = dest; IC50.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Mode** | **HOLD SCOPE** |
| **Date** | 2026-08-26 |
| **CORE implement** | Grok Build on **draft PR 71** — identity + **1..N** + **refuse `analysis_ids`** |
| **Merge** | **Hold** until UAT + dogfood. PR 71 stays draft. |
| **Results / work_order / Test mint** | **Out of CORE** |

**Bottom line:** CORE locks folded. Implement follows 1..N + refuse `analysis_ids`. PR 71 stays draft pending UAT + dogfood. Not IC50.
