# Architecture Review: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept**  
**Scope:** AR CORE — identity + **1..N vessels** (not results, not extract-hold, not IC50)  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [CEO](../ceo-review/atomic-receive.md) · [UI](../ui-review/atomic-receive.md) · [Security](../security-review/atomic-receive.md)  
**Gate memo:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**Schema:** no new tables / no new columns for CORE (no `schema-changes/atomic-receive.md`)

## Executive summary

Historical packet Architecture **Accept** (PR 30) still stands for two identities, short receive body, existing tables, 409 on `containers.name`, and Available for Testing.

This stamp is the **CORE fold**. Implement follows PRD **1..N**, not “first vessel.” One `POST /samples/receive`, one txn: Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample** (true extra vessels, not daughter Samples). Any barcode collision (in the request or in the DB) → **409 + full rollback**. AuthZ = sample create + project RLS (PR 68). Mass/conc stay off Sample.

Results persist lock remains **design SoT for a follow-on slice**, not a CORE ship condition. Coding stays Grok Build. Not IC50.

**Verdict: Accept** on CORE.

## CORE architecture (locked)

| Lock | Detail |
|------|--------|
| **One API** | `POST /api/samples/receive` only |
| **One txn** | Sample + **1..N** Containers + Contents (each → same Sample) (+ optional asked-for tests) |
| **Vessels** | Primary barcode required + optional additional barcodes. Extra vessels are **not** daughter Samples. |
| **Identities** | `containers.name` = barcode; `samples.name` = system template. C1 gone. |
| **Collision** | Any barcode collision in request or DB → **409** + full rollback |
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
- Second receive API
- Results-entry as CORE ship
- New tables / `results.unit_id` / `status_history`
- Mass/conc on Sample
- Partial commit on barcode collision
- IC50 / dose-response / parsers / ELN

## Follow-on (not CORE)

Typed number → `results.reported_result` + `qualifiers`; `raw_result` may copy. Unit from `analytes.units_default`; missing → 422. No `results.unit_id`. **Not** a CORE UAT or ship blocker.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** |
| **Date** | 2026-08-26 |
| **Named scope** | AR CORE — identity + **1..N** vessels |
| **Schema** | No new tables / no new columns |
| **Not licensed** | Results-entry implement · extract-hold · work_order · IC50 |

```
ARCHITECTURE REVIEW: Accept
SCOPE: AR CORE (identity + 1..N vessels)
```
