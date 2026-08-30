# PRD: Containers

**Domain:** Containers  
**Status:** Framework-first (Leadership 2026-08-26)  
**Spec:** [../../specs/containers/SPEC.md](../../specs/containers/SPEC.md)  
**Umbrella:** [../nimblelims-prd.md](../nimblelims-prd.md)  
**Framework stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Decisions:** [`.docs/review/open-questions/containers.md`](../../../review/open-questions/containers.md)  
**Team:** Leadership owns intent; Dev owns schema implementability  

---

## 0. Framework posture (Leadership)

Containers are a **fixed scientific/ops spine** with **configurable joints**:

| Fixed (not “profile away”) | Configurable in DB |
|----------------------------|--------------------|
| Sample ≠ vessel identity | Container **types** (rows×columns, material, capacity) |
| Option A inventory (solute mass/count; no stored volume) | Lists/units for amount & concentration |
| 1×1 only may hold Contents | Name templates for containers where used |
| Nesting: multi-element = structure; 1×1 = liquid unit | Admin activate which type catalogs appear (sidebar / `config:edit`) |
| Empty-dest rule on aliquot mint | — |
| RLS via contents → sample → project | — |

Container types and related catalogs are framework config (`config:edit`). Runtime inventory rules are **not** soft preferences.

---

## 1. Problem

Labs need a clear model for **where material lives** and **how much solute is in a vessel**, separate from **sample identity**. Code/UI lag (free-text dimensions, fuzzy amount ownership) fights the locked model and confuses accessioning + processing.

## 2. Goals

### 2.1 Framework

| ID | Goal |
|----|------|
| F1 | Type catalog and units are **DB-configured**; mutate = `config:edit` |
| F2 | Inventory/nesting/contents eligibility are **fixed spine** (FW-0) |
| F3 | Create paths used by intake/processing respect the same spine (AR first vessel; aliquot dest atomic) |

### 2.2 Domain

| ID | Goal |
|----|------|
| G1 | Separate Sample identity from vessel inventory. **Process assignment is Contents** (sample in a container), not sample-only |
| G2 | Nest plates/racks/boxes as structure; tubes/wells as liquid units |
| G3 | Solute mass/count + vessel concentration; never store volume |
| G4 | Only 1×1 vessels may have Contents |
| G5 | Receive / aliquot dest do not commit barren tubes |
| G6 | Tenancy via contents → sample → project (RLS) |

## 3. Non-goals

- Materials / diluent lots (deferred; compound lots → WO-5/6 later)  
- Polymorphic contents beyond samples  
- Softening process assignment back to sample-only (process holds **Contents**; see [sample-processing PRD](../sample-processing/PRD.md) §4.1)  
- Experiment start-cohort queue sample-vs-container bind beyond process assignment (Decision #24 still names samples; process grain is container-with-sample)  
- Softening Option A via “profile”

## 4. Product model (locked)

```text
Multi-element Container (plate / rack / box)   — structure only; NO Contents
  └── Single-element Container (1×1)           — liquid unit of account
        └── Contents[]                         — sample + per-row solute mass/count
```

Identities: `containers.name` = barcode; `samples.name` = lab ID — **not the same**.

**Process (critical):** A sample may occupy **many** containers. Only a **sample in a container** (a Contents row) is assigned to a process. See [sample-processing PRD §4.1](../sample-processing/PRD.md).

## 5. Leadership notes

| Persona | Note |
|---------|------|
| CEO | Containers stay on the sample/container spine for compounds/lots later — no second LIMS |
| Lab Ops | Types admin-owned; bench never invents inventory rules mid-rack |
| Security CSO | Type mutate = `config:edit`; RLS unchanged |
| Sci CSO | Option A + lineage fixed across intake and processing |

## 6. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Multi-element types cannot receive Contents |
| AC2 | Amount = Option A |
| AC3 | Volume not stored as inventory |
| AC4 | Type shape = rows×columns |
| AC5 | Aliquot dest atomic with contents |
| AC6 | Sample ID ≠ container barcode |
| AC7 | RLS: INSERT via created_by; visibility via project-through-contents |

## 7. Shipped vs lag

| Area | Status |
|------|--------|
| APIs / UI / RLS 0062/0064 | Shipped |
| Aliquot empty-dest rule | Shipped on execute |
| rows×columns replacing dimensions | Decided — implement lag |
| Strict Option A everywhere | Decided — partial |

## 8. References

- `.docs/review/open-questions/containers.md`  
- `.docs/review/tech-sketch/mass-concentration-contents.md` (if present)  
- `.docs/internal/prd/containers/ISSUES.md`  
