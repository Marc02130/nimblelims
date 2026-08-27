# Leadership team review — Atomic receive CORE (requirements + spec)

**Date:** 2026-08-26  
**Team:** Leadership (Lab Ops + CEO/product + Security consume)  
**Packet:** Sample accessioning AR CORE  
**Requirements:** [`.docs/internal/prd/sample-accessioning/PRD.md`](../internal/prd/sample-accessioning/PRD.md) (RQ-AR-*, NR-AR-*)  
**Spec:** [`.docs/internal/specs/sample-accessioning/SPEC.md`](../internal/specs/sample-accessioning/SPEC.md) (§3 + AC-AR-*)  
**Design SoT:** [`.docs/review/tech-sketch/atomic-receive.md`](../review/tech-sketch/atomic-receive.md)

---

## Roll-up verdict

| Review | Verdict | Gate |
|--------|---------|------|
| **Lab Ops** | **Accept with conditions** (L2–L4; L1 retracted) | **OPEN** for CORE only |
| **CEO / Product** | **Accept with conditions** (C2–C8; C1 = retracted identity lock) | **HOLD SCOPE** · CORE provisional open |
| **Security (AuthZ)** | **Accept with conditions** (S-AR-1..5) — docs gate satisfied (PR 68) | Conditions land **with** CORE code |
| **Architecture** | **Accept** on CORE (1..N vessels; bounce list) | Formal stamp 2026-08-26 |
| **UI** | **Accept** on CORE (new receive loop; 1..N) | Formal stamp 2026-08-26 |
| **Scientific CSO** | **N/A for CORE** | No assay/results/QC in this slice; prior packet Accept stands for later results |

**Leadership team:** **APPROVE CORE for implement** against PRD RQ-AR-* / SPEC §3. Results-entry, intake-profile engine, and work_order remain **out**.

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

## Scope freeze (unchanged)

**IN:** Identity + **1..N vessels** (primary + optional additional barcodes), one txn, system sample name, Available for Testing, sticky required project, tube off form, AuthZ = sample create + project RLS, new receive UI, docs/UAT with ship.

**OUT:** Results-entry as CORE must-pass; aliquot/derivative; profile engine; work_order/routing; wizard revival; FieldDefinitions on AR body; second receive API.

---

## Same-phase conditions (must land with code)

| Source | IDs | Essence |
|--------|-----|---------|
| Lab Ops | **L2–L4** | Sticky required project; default tube off form; asked-for tests Assigned/Pending + DELETE-with-results → 400 |
| CEO | **C2–C8** | = L2–L4 + multi-vessel honesty + results carve + AuthZ + docs/UAT |
| Security | **S-AR-1..5** | Same AuthZ as sample create; RLS in service; one API/txn; refuse orphan multi-call; no client bypass |

---

## Implement gate

```
LEADERSHIP TEAM: APPROVE CORE
IMPLEMENT GATE: OPEN (CORE only — identity + 1..N vessels)
MODE: HOLD SCOPE
LAB OPS: Accept with conditions (L2–L4)
CEO: Accept with conditions (HOLD SCOPE)
SECURITY: Accept with conditions (S-AR-1..5 land with code)
ARCHITECTURE: Accept on CORE
UI: Accept on CORE
NOT OPEN: results-entry · profile engine · work_order · extract-hold · IC50
```

---

## Team comment (for ISSUES)

**Leadership team (formal):** Lab Ops + CEO Accept-with-conditions on PRD/SPEC CORE; Architecture + UI **Accept** on CORE (1..N, not first vessel); implement gate **OPEN** for identity + 1..N vessels only; L2–L4 / C2–C8 / S-AR-1..5 same phase; results carve stands; HOLD SCOPE — do not revive wizard or smuggle work_order/results into the AR PR.
