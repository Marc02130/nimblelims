# Temporary issues — Containers

**Status:** Synced 2026-08-26 (PRD/SPEC framework-first + Leadership/BA/Dev)  
**PRD:** [PRD.md](PRD.md) · **Spec:** [../../specs/containers/SPEC.md](../../specs/containers/SPEC.md)  
**Decisions:** `.docs/review/open-questions/containers.md`  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Team notes:** [../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md](../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md)

---

## Framework posture (from PRD §0)

| Fixed spine | Configurable (`config:edit`) |
|-------------|------------------------------|
| Option A inventory; 1×1 Contents only; nesting; empty-dest on aliquot; RLS | Container **types** catalog; units; sidebar active type packs (FW-1b pattern) |

Do **not** make Option A / nesting a soft “profile.”

---

## Team comments (2026-08-26)

| Team | Comment |
|------|---------|
| **Leadership** | Types = framework config; physics fixed. Compound/lots stay on this spine later (WO-5/6) — no second LIMS |
| **BA** | AC should separate “type admin” vs “runtime inventory rules.” Label barcode ≠ sample ID in stories |
| **Dev** | Pair **C-1 + C-8** with AR first-vessel work; enforce 1×1 Contents server-side; don’t wait on C-9 |

---

## A. Product vs schema lag

| ID | Issue | Why | Next |
|----|-------|-----|------|
| **C-1** | Free-text `dimensions` vs locked **rows × columns** | Wrong model in admin | **Next schema slice** |
| **C-2** | Option A only partial in UI/API | Volume language leaks | Align labels + validation |
| **C-3** | `Contents.concentration` not inventory SoT | Dual story | RO/legacy; stop new SoT writes |
| **C-4** | Vessel amount vs Σ contents not enforced | Ledger drift | Same-txn or derived-only |

## B. Create-path (ties to AR)

| ID | Issue | Why | Next |
|----|-------|-----|------|
| **C-5** | Empty-container hard on aliquot; soft in Container Mgmt | Ops confusion | Align create with OQ-S11a |
| **C-6** | AR default tube off-form vs wizard type + barcode suffix | Intake/inventory diverge | **With AR P0** |
| **C-7** | Multi-call accession vs single-txn receive | Orphans | **Prefer single-txn only** |
| **C-16** | AR must create **1..N containers** per sample in one txn (primary + optional additional barcodes) | Multi-tube receive is common | **P0 lock 2026-08-26** — align Container create path with AR body |

## C. Nesting / contents

| ID | Issue | Why | Next |
|----|-------|-----|------|
| **C-8** | API may allow Contents on multi-element | Violates lock | **Server enforce 1×1** |
| ~~C-9~~ | Auto-spawn children on multi-element create | Incomplete plate story | **Parked** — decide later |
| ~~C-10~~ | Sample vs container in experiment queue | Processing bind | **Parked** — separate packet |

## D. Docs

| ID | Issue | Next |
|----|-------|------|
| C-11 | Manuals still dimensions-centric | Sync after C-1 |
| C-12 | Sample name ≠ barcode not obvious in UI | Labels with AR / forms |
| C-13 | Paths still saying `.docs/review` in old notes | Use `.docs/review/` |

## E. Deferred (framework later)

| ID | Issue | Disposition |
|----|-------|-------------|
| C-14 | Compound lot as child sample (WO-6) | **Deferred** with registration packet |
| C-15 | Materials / diluent lots | **Deferred** |

---

## Priority

1. **C-6 / C-7** with accessioning AR P0  
2. **C-1 + C-8** (shape + contents eligibility)  
3. **C-2 + C-4 + C-5** (inventory + empty rule UX)  
4. Docs **C-11–C-13**  
5. Park **C-9, C-10, C-14, C-15**  

Formal OQ home: `.docs/review/open-questions/containers.md`
