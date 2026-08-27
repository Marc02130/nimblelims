# Architecture Review: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept** (condition: refuse-or-ignore / no Test mint; locked pick **422 if `analysis_ids` non-empty**)  
**Scope:** AR CORE — identity + **1..N vessels** (not results, not extract-hold, not IC50)  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [CEO](../ceo-review/atomic-receive.md) · [UI](../ui-review/atomic-receive.md) · [Security](../security-review/atomic-receive.md)  
**Gate memo:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**Schema:** no new tables / no new columns for CORE (no `schema-changes/atomic-receive.md`)

## Executive summary

Historical packet Architecture **Accept** (PR 30) still stands for two identities, short receive body, existing tables, 409 on `containers.name`, and Available for Testing.

This stamp is the **CORE fold**. Implement follows PRD **1..N**, not “first vessel.” One `POST /samples/receive`, one txn: Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample** (true extra vessels, not daughter Samples). Any barcode collision (in the request or in the DB) → **409 + full rollback**. AuthZ = sample create + project RLS (PR 68). Mass/conc stay off Sample.

**Accept holds only with refuse-or-ignore (no Test mint).** Recorded from the **2026-08-26 chat punch**. Locked pick: **refuse**. **`analysis_ids` non-empty → 422.** Do not ignore. Do not mint Tests. Do not persist asked-for analyses. Do not call `_create_asked_for_tests`. Silent drop would hide a client that still thinks Tests were created. UI sends none. Empty or omitted is the only accepted CORE path — and even then, do not mint Tests.

Results persist lock remains **design SoT for a follow-on slice**, not a CORE ship condition. Coding stays Grok Build. PR 71 stays draft until UAT + dogfood. Not IC50.

**Verdict: Accept** on CORE (with the refuse-or-ignore / 422 condition).

## CORE architecture (locked)

| Lock | Detail |
|------|--------|
| **One API** | `POST /api/samples/receive` only |
| **One txn** | Sample + **1..N** Containers + Contents (each → same Sample). **Zero Tests.** |
| **Vessels** | Primary barcode required + optional additional barcodes. Extra vessels are **not** daughter Samples. |
| **Identities** | `containers.name` = barcode; `samples.name` = system template. C1 gone. |
| **Collision** | Any barcode collision in request or DB → **409** + full rollback |
| **`analysis_ids`** | Non-empty → **422**. Do not ignore. Do not mint. (2026-08-26 chat punch) |
| **Status** | Available for Testing; `received_date`; no Received hop; no `status_history` |
| **AuthZ** | Same as sample create + project RLS (`has_project_access` / `lims_app`) |
| **Tables** | Existing only. No new tables/columns. No `results.unit_id`. Mass/conc stay off Sample. |

## Bounce (fails Architecture CORE Accept)

- `work_order` / extract-hold / wizard revival
- Orphan multi-call (create sample → create container → link)
- Single-vessel-only API/UI
- Sample-ID field / user-typed sample name / C1
- Received hop or status picker
- Project auto-create
- Tube picker on the scan loop
- Analysis as work plan
- Test mint at receive / `_create_asked_for_tests` / `analysis_ids` as work plan / ignore or silent-drop of `analysis_ids`
- Second receive API
- Results-entry as CORE ship
- New tables / `results.unit_id` / `status_history`
- Mass/conc on Sample
- Partial commit on barcode collision
- IC50 / dose-response / parsers / ELN

## Follow-on (not CORE)

Typed number → `results.reported_result` + `qualifiers`; `raw_result` may copy. Unit from `analytes.units_default`; missing → 422. No `results.unit_id`. **Not** a CORE UAT or ship blocker. Classic Test+Result with no LimsRun still exists — do not kill it in stories. Test row at LimsRun start is WO-7.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** (refuse-or-ignore / no Test mint; locked pick 422 if `analysis_ids` non-empty) |
| **Date** | 2026-08-26 |
| **Condition source** | 2026-08-26 chat punch |
| **Named scope** | AR CORE — identity + **1..N** vessels |
| **Schema** | No new tables / no new columns |
| **Not licensed** | Results-entry implement · extract-hold · work_order · IC50 |

```
ARCHITECTURE REVIEW: Accept
SCOPE: AR CORE (identity + 1..N vessels)
CONDITION: Accept holds only with refuse-or-ignore (no Test mint). 2026-08-26 chat punch. Locked pick: 422 if analysis_ids non-empty.
```
