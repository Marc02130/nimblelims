# Security Review: Atomic receive AuthZ spine

**Date:** 2026-08-24  
**Status:** **Accept with conditions** (Heidi/Günter)  
**Stem:** `atomic-receive`  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md) §4b  
**Related:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [QA](../qa-review/atomic-receive.md)  
**Scope:** Feature packet (STRIDE) — receive path AuthZ only. DEEP CSO: skipped.  
**Not this packet:** IC50, dose-response, extract-hold, ELN execute.

## Gate

| Gate | State |
|------|--------|
| **AuthZ docs gate** | **Satisfied** — Heidi/Günter Accept with conditions on sketch §4b + this stamp (PR 68). |
| **Product implement** | **Provisional open for AR CORE** (Leadership 2026-08-26) — identity + 1..N vessels. Do **not** read PR 30 as license for results-entry / profile engine / work_order. |

Packet **design** Accepts still stand (CEO PR 30, Lab Ops L2–L4 / L1 retracted, scientific CSO, Architecture, UI). AuthZ conditions **S-AR-1..5** land with CORE code.

## Executive summary

Heidi / Günter locked receive AuthZ on 2026-08-24. Until that spine lived in the formal sketch, the AuthZ docs gate stayed open. Sketch **§4b** now states the spine; this stamp records it.

`POST /api/samples/receive` is **not** a second permission world. It uses the **same AuthZ as sample create** plus **project RLS** (`has_project_access` / `lims_app`). There is one receive API and one DB transaction for sample + **1..N containers** + contents each (+ optional tests). Orphan multi-call (create sample → create container → link) is refused. The UI must not be the AuthZ gate.

**Verdict: Accept with conditions.** Conditions **S-AR-1..5** land with **AR CORE** product implement. Not IC50.

## Surface delta

| Surface | Risk |
|---------|------|
| `POST /api/samples/receive` | Elevation if a separate receive permission or client-only path ships |
| 1..N containers + contents in the same call | Integrity: mid-sequence drop orphans sample without vessel(s) |
| Optional tests on the same txn | Same AuthZ as the receive commit — not a side door |
| Project sticky / `project_id` required | Disclosure or write if RLS is UI-only |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | Existing JWT. Same AuthZ as sample create (S-AR-1). |
| Tampering | One receive endpoint; one txn; no orphan multi-call substitute (S-AR-3, S-AR-4). |
| Repudiation | Existing sample-create audit path; receive is that write, not a silent second log. |
| Info disclosure | Project RLS (`has_project_access` / `lims_app`) on the receive service, not only the UI (S-AR-2, S-AR-5). |
| DoS | Out of scope (no new public flood surface in this packet). |
| Elevation | No separate receive permission; no client-only bypass; no second AuthZ spine (S-AR-1, S-AR-3, S-AR-5). |

## Findings / conditions

| ID | Severity | Status | Condition |
|----|----------|--------|-----------|
| **S-AR-1** | High | **Locked (sketch §4b)** | Receive uses the **same AuthZ as sample create**. No new receive permission. |
| **S-AR-2** | High | **Locked (sketch §4b)** | **Project RLS** on the receive path: `has_project_access` / `lims_app`. Enforce **inside** the receive service before/with the txn. |
| **S-AR-3** | High | **Locked (sketch §4b)** | **One path, one txn:** one `POST /api/samples/receive`. Sample + **1..N Containers** + Contents each (+ optional tests) in a **single DB transaction**. All intake vessels share that txn (not follow-up calls). Bounce a second receive API. |
| **S-AR-4** | High | **Locked (sketch §4b)** | **Refuse orphan multi-call.** Bounce create sample → create container → link as a receive substitute. Clients that drop mid-sequence are refused by design — there is no safe multi-call substitute. |
| **S-AR-5** | High | **Locked (sketch §4b)** | **No client bypass.** No client-only skip of AuthZ/RLS. Do not rely on the UI to gate project access. |

## Not in scope this review

- IC50 / dose-response
- Extract-hold dest type / ELN execute
- Deep `/cso` infra scan
- AR CORE product implementation (provisional open; AuthZ conditions land with code — not this docs fold)

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (Heidi/Günter) |
| **Date** | 2026-08-24 |
| **AuthZ docs gate** | **Satisfied** — sketch §4b + this stamp (PR 68) |
| **Product implement** | **Provisional open for AR CORE** (Leadership 2026-08-26) |
| **Deep `/cso`** | skipped |

```
SECURITY REVIEW: Accept with conditions
DEEP CSO: skipped
```
