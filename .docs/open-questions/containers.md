# Containers — decision log

**Status:** Core inventory model **Decided** (2026-08-11)  
**Related:** [experiments.md](experiments.md) (aliquot/pool), [ideas/containers-model-update.md](../ideas/containers-model-update.md) (implement slice), [ideas/materials-and-lot-tracking.md](../ideas/materials-and-lot-tracking.md), tech sketch §0.8 containers/amount/aliquot

## Gate rule

Do not implement diluent-as-mass, stored volume as amount, multi-element contents, or free-text `dimensions` as the grid shape. Use the locks below.

---

## 0. Locked decisions (2026-08-11)

### 0.1 Amount model — Option A (solute mass)

| Rule | Detail |
|------|--------|
| **What is amount** | **Mass of solute** (or **count** for cells/colonies) — never volume, never diluent mass |
| **Liquid / diluent** | **Not mass.** Diluent/buffer/solvent does not contribute to stored amount |
| **Concentration** | Mass/volume (or equivalent) of the defined solute at the vessel |
| **Volume** | **Never stored.** Derive when useful: \( V = m_{\text{solute}} / C \) with consistent units |
| **Inbound volume** | Volume + concentration → compute mass, store amount + conc; drop volume |

**Rejected:** Option B (solution total mass / density-based volume).

### 0.2 Nesting

```
Container (multi-element parent)     e.g. plate, rack, box
  └── Container (single-element)     e.g. well, tube  (1×1 type)
        └── Contents[]               samples / compounds-as-samples only on 1×1
```

| Level | Role |
|-------|------|
| **Multi-element container** | Structural only (holds child containers). No liquid inventory. |
| **Single-element container** | Liquid-bearing unit of account (tube, well, vial). |
| **Contents** | Identity + solute mass (or count) of each sample in that vessel. |

### 0.3 Consistency rules (locked)

1. **Well / tube** is the liquid unit of account; **plate / rack / box** is parent structure only.  
2. **`Contents.amount`** = mass (or count) of **that** sample in the single-element container.  
3. **Container.amount** (on a single-element vessel) = **total solute mass of interest** in that vessel (often \( \sum \) content amounts for pools of the same mass basis).  
4. **Container.concentration** (on a single-element vessel) = concentration used for \( V = m / C \).  
5. **Never store volume** on container or contents; compute when units convert cleanly.  
6. **Multi-element containers** do not hold amount/concentration inventory and **must not** have `Contents` rows.  
7. On aliquot / dilute / transfer **execute**: update content amount(s) and vessel amount/conc **together** so derived volume stays consistent.  
8. **Diluent actions** change **concentration** (and thus derived volume); they do **not** increase stored solute amount. Sample mass on contents stays unless sample is transferred out.

### 0.4 Container type shape — rows × columns (not dimensions)

| Field | Role |
|-------|------|
| **`rows`** | Integer ≥ 1 — number of element rows in this type |
| **`columns`** | Integer ≥ 1 — number of element columns in this type |
| **`dimensions`** | **Remove** from product model (was free-text e.g. `"8x12"` / `"15x100mm"`). Physical size strings are not the grid. |

| Kind (examples) | rows × columns | Elements | May have Contents? |
|-----------------|----------------|----------|--------------------|
| Plate, rack, box | e.g. 8×12, 1×10 | Multi | **No** |
| Tube, well, vial | **1×1** | Single | **Yes** |

Derived:

- `element_count = rows * columns`  
- **Single-element** ⇔ `rows = 1` AND `columns = 1`  
- **Only single-element container types** may receive `Contents`  
- Multi-element instances get **child containers** (one per position), not contents on the parent  

**Instance position:** existing `Container.row` / `Container.column` remain the position of a child within its parent (1-based). Valid ranges constrained by parent type’s `rows` / `columns`.

### 0.5 Capacity, material, preservative

Unchanged intent for now:

- **capacity** — vessel capacity in configured base units (optional; not a substitute for rows/columns)  
- **material** — vessel composition (plastic/glass) — **not** reagent material  
- **preservative** — optional vessel preservative note  

Reagents / diluent lots → materials idea (separate), not `container_types.material`.

### 0.6 Contents eligibility (locked)

| Container type | Contents allowed |
|----------------|------------------|
| Single-element (`rows=1`, `columns=1`) | Yes |
| Multi-element (`rows*columns > 1`) | **No** — use child single-element containers |

Pooling = multiple `Contents` rows on **one single-element** container (e.g. pool tube), not contents on a plate.

### 0.7 Diluent (inventory implication)

- No diluent mass column.  
- No stored diluent volume as amount.  
- Dilute: keep solute mass on contents / vessel; update **concentration**; UI may show derived volume.  
- Lot traceability for PBS/etc. is **materials** (out of this lock).  

---

## 1. Schema / product delta (not yet implemented)

Tracked for a future containers schema slice:

| Change | Notes |
|--------|--------|
| `container_types.dimensions` → drop | Migrate any useful free-text elsewhere if needed; do not keep as grid |
| Add `container_types.rows` INTEGER NOT NULL | Default/backfill: parse old dimensions where possible, else 1 |
| Add `container_types.columns` INTEGER NOT NULL | Same |
| Enforce Contents only on 1×1 types | API + DB check (preferred) |
| Clear amount/conc semantics | Single-element vessel = solute total + conc; multi-element ignore/null |
| Admin UI / forms | Rows + columns instead of Dimensions |
| Seeds / UAT / tests | Update tube=1×1, 96-well plate=8×12, well=1×1 |

**Status of implementation:** Decided product rules; **code still has `dimensions`**. Implement slice tracked as [ideas/containers-model-update.md](../ideas/containers-model-update.md) (migration + API + admin UI + tests).

---

## 2. Alignment with aliquot/pool (experiments)

Unchanged and consistent:

- Aliquot methods may accept **inbound volume** only as input; store mass.  
- `target_concentration` updates dest concentration without treating diluent as mass.  
- Execute reduces/increases **content** solute amounts; vessel amount/conc must stay consistent with §0.3.  

Open for implement slice (non-blocking for this decision): whether multi-element create auto-spawns child 1×1 containers.

---

## 3. Status labels

| Topic | Status |
|-------|--------|
| Option A (solute mass; diluent not mass) | **Decided** |
| Volume never stored; \( V = m/C \) | **Decided** |
| Nesting plate → well → contents | **Decided** |
| Consistency rules §0.3 | **Decided** |
| Type rows/columns; remove dimensions | **Decided** (implement pending) |
| Contents only on 1×1 types | **Decided** (enforce pending) |
| Materials/diluent lots | **Deferred** (idea) |
| Polymorphic contents beyond sample | **Deferred** (sketch later) |

---

## 4. History

| Date | Event |
|------|--------|
| 2026-08-11 | Locked Option A, consistency rules, rows×columns type shape, contents only on single-element containers |
