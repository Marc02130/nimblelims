# Leadership team review — Atomic receive CORE (requirements + spec)

**Date:** 2026-08-26  
**Updated:** 2026-08-26 (CORE locks folded — **refuse `analysis_ids`**; hold merge / PR 71 draft)  
**Team:** Leadership (Lab Ops + CEO/product + Security consume)  
**Packet:** Sample accessioning AR CORE  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../review/requirements/atomic-receive.md)  
**Design SoT:** [`.docs/review/tech-sketch/atomic-receive.md`](../review/tech-sketch/atomic-receive.md)

---

## Roll-up verdict

| Review | Verdict | Gate |
|--------|---------|------|
| **Lab Ops** | **Accept with conditions** (L2–L3; L1 retracted; L4 Test-at-receive superseded) | CORE only; merge hold |
| **CEO / Product** | **Accept with conditions** (HOLD SCOPE) | CORE coding open; **PR 71 draft** |
| **Security (AuthZ)** | **Accept with conditions** (S-AR-1..5) — docs gate satisfied (PR 68) | Conditions land **with** CORE code |
| **Architecture** | **Accept** on CORE **with conditions** (1..N; refuse `analysis_ids`; hold merge) | Formal stamp 2026-08-26 |
| **UI** | **Accept** on CORE **with conditions** (new receive loop; 1..N; 409 stays on scan well) | Formal stamp 2026-08-26 |
| **Scientific CSO** | **N/A for CORE** | No assay/results/QC in this slice; classic Test+Result still exists |

**Leadership team:** **APPROVE CORE for implement** against sketch + requirements. **Refuse `analysis_ids`.** Results-entry, intake-profile engine, and work_order remain **out**. **PR 71 stays draft** pending UAT + dogfood.

---

## Formal artifacts

| Artifact | Path |
|----------|------|
| Lab Ops | [`.docs/review/lab-ops-review/atomic-receive.md`](../review/lab-ops-review/atomic-receive.md) |
| CEO | [`.docs/review/ceo-review/atomic-receive.md`](../review/ceo-review/atomic-receive.md) |
| Security | [`.docs/review/security-review/atomic-receive.md`](../review/security-review/atomic-receive.md) |
| Architecture | [`.docs/review/architecture-review/atomic-receive.md`](../review/architecture-review/atomic-receive.md) — **Accept** on CORE |
| UI | [`.docs/review/ui-review/atomic-receive.md`](../review/ui-review/atomic-receive.md) — **Accept** on CORE |
| Prior gate memo | [2026-08-26-ar-core-plan-leadership.md](2026-08-26-ar-core-plan-leadership.md) |

---

## Scope freeze

**IN:** Identity + **1..N vessels** (primary + optional additional barcodes), one txn, system sample name, Available for Testing, sticky required project, tube off form, AuthZ = sample create + project RLS on the whole txn, new receive UI, **refuse** non-empty `analysis_ids`, docs/UAT/dogfood with ship.

**OUT:** Results-entry as CORE must-pass; aliquot/derivative; profile engine; work_order/routing; wizard revival; FieldDefinitions on AR body; second receive API; Test mint at receive; ignore non-empty `analysis_ids`; Method = dest; IC50.

---

## Same-phase conditions (must land with code)

| Source | IDs | Essence |
|--------|-----|---------|
| Lab Ops | **L2–L3**; L4 superseded | Sticky required project; default tube off form; **zero Tests** at receive; DELETE-with-results → 400 for independently created tests |
| CEO | **HOLD SCOPE** | 1..N + refuse `analysis_ids` + results carve + AuthZ + docs/UAT; PR 71 draft |
| Security | **S-AR-1..5** | Same AuthZ as sample create; RLS in service; one API/txn; refuse orphan multi-call; no client bypass |
| Architecture / UI | Accept + conditions | Hold merge until UAT + dogfood |

---

## Implement gate

```
LEADERSHIP TEAM: APPROVE CORE
IMPLEMENT: Grok Build on draft PR 71 (identity + 1..N + refuse analysis_ids)
MERGE: HOLD until UAT + dogfood — PR 71 stays draft
LAB OPS: Accept with conditions (L2–L3; L4 Test-at-receive superseded)
CEO: Accept with conditions (HOLD SCOPE)
SECURITY: Accept with conditions (S-AR-1..5 land with code)
ARCHITECTURE: Accept on CORE (with conditions)
UI: Accept on CORE (with conditions)
NOT OPEN: results-entry · profile engine · work_order · extract-hold · Test mint at receive · IC50
```

---

## Team comment (for ISSUES)

**Leadership team (formal):** Lab Ops + CEO Accept-with-conditions on CORE; Architecture + UI **Accept** on CORE **with conditions** (1..N, not first vessel; **refuse** `analysis_ids`; hold merge / PR 71 draft); `_create_asked_for_tests` is a fail; classic Test+Result still exists; HOLD SCOPE — do not revive wizard or smuggle work_order/results into the AR PR. Not IC50.
