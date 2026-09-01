# Temporary issues — Sample accessioning

**Status:** Synced 2026-08-26 · Requirements/Spec SoT for CORE · **Leadership team formal: IMPLEMENT GATE OPEN (CORE only)**  
**PRD (requirements):** [PRD.md](PRD.md) · **Spec:** [../../specs/sample-accessioning/SPEC.md](../../specs/sample-accessioning/SPEC.md)  
**Formal reviews:** [lab-ops](../../../review/lab-ops-review/atomic-receive.md) · [ceo](../../../review/ceo-review/atomic-receive.md) · [security](../../../review/security-review/atomic-receive.md) · [team rollup](../../../discussions/2026-08-26-ar-core-leadership-team-review.md)  
**Formal design SoT:** `.docs/review/tech-sketch/atomic-receive.md`  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Team notes:** [../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md](../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md) · [../../../discussions/2026-08-26-ar-core-plan-leadership.md](../../../discussions/2026-08-26-ar-core-plan-leadership.md)

---

## Leadership locks (current)

| Lock | Detail |
|------|--------|
| **FW-1** | OOB intake = **atomic receive only**; labs configure own intake configs later; sidebar active configs = admin |
| **FW-1b** | Activate configs = **`config:edit` only** |
| **FW-2** | Intake profiles ≠ Workflow Templates |
| **P0 path** | Scan → **one txn** (Sample + **1..N Containers** + Contents each) → **Available for Testing** → stay on form. Primary barcode + optional additional barcodes |
| **Analysis at receive** | Prefer **omit** on default; if present = “asked for” only — **not** work plan (G5 / A-15) |
| **AuthZ** | Receive = sample create + project RLS |
| **Code** | **Provisional Marc open for AR CORE only** — see PRD RQ-AR-* / SPEC §3; not results, not profile engine, not work_order |

---

## Team comments (2026-08-26)

| Team | Comment |
|------|---------|
| **Leadership** | **Formal team review:** Lab Ops + CEO **Accept with conditions**; **IMPLEMENT GATE OPEN (CORE only)** on PRD RQ-AR-* / SPEC §3; L2–L4 / C2–C8 / S-AR-1..5 same phase; results / profile / work_order **out**; HOLD SCOPE — don’t revive wizard |
| **BA** | AC must not imply “assign analysis = what’s next”; stories split receive vs order vs work |
| **Dev** | One receive service; no intake-profile engine in P0; no dual orphan APIs |

---

## A. Intake profiles / modes — **DEFERRED** (after AR)

| ID | Issue | Disposition |
|----|-------|-------------|
| ~~A-1~~ | Modes not modeled as DB profiles | **Deferred** — FW-1; engine after AR |
| ~~A-2~~ | Dual-entry vs AR no sample-ID | **Deferred** |
| ~~A-3~~ | Manifest / verify receive | **Deferred** |
| ~~A-4~~ | Bulk as mode architecture | **Deferred** — secondary path |

## B. Atomic receive — **CORE open** (gaps vs PRD/SPEC)

| ID | Issue | Why | Requirement |
|----|-------|-----|-------------|
| A-5 | `POST /samples/receive` + UI missing | US-1 blocked | **RQ-AR-1** |
| A-6 | Multi-call create + barcode suffix hacks | Orphans; barcode ≠ scan | **RQ-AR-2, RQ-AR-4** |
| **A-18** | Receive must support **1..N containers** per sample | Multi-tube common | **RQ-AR-2, RQ-AR-3** |
| A-7 | Wizard Received / In Process vs AR Available for Testing | Breaks Decision #24 start | **RQ-AR-6** |
| A-8 | Project auto-create vs sticky required | Accidental projects | **RQ-AR-7** |

## C. Fields / identity — **CORE align**

| ID | Issue | Requirement |
|----|-------|-------------|
| A-9 | User-typed sample ID | **RQ-AR-5** |
| A-10 | Container type on form | **RQ-AR-8** |
| A-11 | due_date / qc_type / client_id on legacy body | **RQ-AR-9** |
| A-12 | FieldDefinitions on receive form | **NR-AR-4** (out of CORE) |

## D. Tests / work model

| ID | Issue | Disposition |
|----|-------|-------------|
| A-13 | Wizard forces test assignment | **RQ-AR-10** |
| A-14 | DELETE / Assigned-Pending on legacy | Light-ride OK with CORE (SPEC §4) |
| **A-15** | Tests vs process work (X-5) | **NR-AR-5** — processing; WO-1…WO-7 |

## E. Docs / paths

| ID | Issue | Requirement |
|----|-------|-------------|
| A-16 | Stale `.docs` paths in older notes | **RQ-AR-13** |
| A-17 | Dual UAT scripts (wizard vs AR) | **RQ-AR-13** / SPEC §9 |

---

## Priority

1. Close **A-5–A-8 + A-18** against PRD RQ-AR-* / SPEC §3  
2. Close **A-9–A-11, A-13** field align  
3. **A-16 / A-17** with ship  
4. **Results-entry** — separate requirements later (**NR-AR-1**)  
5. **A-1–A-4** intake-profile engine (post-AR)  
6. **A-15** — tracking only; see processing ISSUES  

Related: `.docs/review/tech-sketch/atomic-receive.md`, `.docs/review/security-review/atomic-receive.md`
