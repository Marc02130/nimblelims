# Containers — decision log

**Status:** Core inventory model **Decided** (2026-08-11). Design Group fold **2026-08-23 / 2026-08-24** (§5) — Sample vs Contents vs 1×1 Container SoT; Lab Ops L1 locked; L2 + Hans Result picker **LOCKED**.  
**Related:** [experiments.md](experiments.md) (aliquot/pool), [ideas/containers-model-update.md](../ideas/containers-model-update.md) (implement slice), [ideas/materials-and-lot-tracking.md](../ideas/materials-and-lot-tracking.md), [tech-sketch/experiment-template-entries.md](../tech-sketch/experiment-template-entries.md) §0.8, **[tech-sketch/mass-concentration-contents.md](../tech-sketch/mass-concentration-contents.md)** (Design Group agree + four write-back targets)

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

**2026-08-24 (does not replace the list):** total vs sum is **mandatory** (`Container.amount` = Σ `Contents.amount`, same-txn or derived — bounce independent total). Inventory conc SoT is 1×1 `Container.concentration`. Sample has no mass/conc. Details: **§5**.

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
| Sample has no mass / no concentration | **Decided** (2026-08-24 Marc) |
| `Contents.amount` = per-row mass; 1×1 `Container.amount` = total = Σ contents | **Decided** (2026-08-24 Marc; bounce independent total vs sum) |
| 1×1 `Container.concentration` = vessel inventory conc SoT | **Decided** (2026-08-24 Marc) |
| Put-away / storage browse (Lab Ops L1) | **Decided** (2026-08-24 Deiter) |
| Result publish write-through + normalize picker (Lab Ops L2) | **Decided** (2026-08-24 Deiter + Hans) |
| Which Result for normalize; unit mismatch refuse | **Decided** (2026-08-24 Hans CSO) |

---

## 4. History

| Date | Event |
|------|--------|
| 2026-08-11 | Locked Option A, consistency rules, rows×columns type shape, contents only on single-element containers |
| 2026-08-23 / 2026-08-24 | Design Group fold (§5): Sample ≠ inventory; Contents per-row mass; 1×1 Container total mass + inventory conc; Deiter L1 Accept; L2 + Hans Result picker LOCKED. Sketch: [mass-concentration-contents.md](../tech-sketch/mass-concentration-contents.md) |

---

## 5. Design Group locks (2026-08-23 / 2026-08-24)

**Does not replace §0.** Option A, nesting, rows×columns, Contents-only-on-1×1, and volume-not-stored stay as locked 2026-08-11. This section names **where mass and concentration live**, how total vs per-row stay consistent, and Lab Ops conditions.

Canonical sketch (why + four write-back targets + dest FieldDefinitions): [`.docs/tech-sketch/mass-concentration-contents.md`](../tech-sketch/mass-concentration-contents.md). **Not IC50.** Coding not unpaused by this fold.

### 5.1 Sample is not inventory (Marc)

**Sample** = identity + type + lineage (`parent_sample_id`) only. **No mass. No concentration.** Execute may set type / parent on mint. Bounce Sample columns and Sample write-back of mass or conc.

### 5.2 SoT split — Contents vs 1×1 Container (Marc)

| Field | Where | Meaning |
|-------|--------|---------|
| `Contents.amount` (+ units FK) | Each content row on a **1×1** vessel | **Per-content mass** (solute mass or count). Pool = one row per contribution. |
| `Container.amount` (+ units FK) | **1×1 Container only** | **Total mass** of solute of interest in that vessel. |
| `Container.concentration` (+ units FK) | **1×1 Container only** | **Vessel inventory concentration** SoT (working stock \( C \) for \( V = m / C \)). |
| Multi-element parent (plate/rack/box) | Structure only | **No** `Contents`. **No** amount. **No** concentration. Inventory lives on 1×1 children. |

### 5.3 Total mass = sum of contents (same txn)

On a 1×1 vessel:

\[
\texttt{Container.amount} = \sum \texttt{Contents.amount}
\]

(same mass basis / convertible units.)

**Maintain in the same transaction** as content-row edits **or** treat container total as **derived**. **Bounce** independent edit of `Container.amount` that disagrees with the sum. Aliquot / pool / dilute execute already must update content amounts and vessel amount/conc **together** (§0.3 item 7) — this names the equality.

### 5.4 Concentration — vessel SoT; do not fork on Contents

| Case | Rule |
|------|------|
| **Result write-through** | Inventory conc lands on the **1×1 Container** (`Container.concentration`), not on Sample. |
| **Single-content tube** | Do **not** let `Contents.concentration` and `Container.concentration` diverge. `Contents.concentration` is **optional / read-only** or a **same-txn mirror** of the vessel. Vessel remains SoT. |
| **Multi-content pool** | Vessel conc on **Container only**. **Bounce** inventing mixture concentration by summing or averaging content concs. Per-row mass stays on Contents; there is no per-row inventory conc SoT for the pool. |

Assay concentration remains a **Result**. Inventory conc is not the assay number (L2 + Hans §5.8 locked).

### 5.5 Four write-back targets (Heidi) — pointer

Do not duplicate the table here. **Sample** (identity + allowlist), **Contents** (per-row mass), **1×1 Container** (total mass + inventory conc + location), **entry cells** (capture or RO projection — **never a second ledger**). Dest FieldDefinitions after mint: RO of the matching SoT unless same-txn write-through. Full table: [mass-concentration-contents.md](../tech-sketch/mass-concentration-contents.md) §6.

### 5.6 Lab Ops (Deiter)

**L1 — put-away / storage (Accept / locked):**

- Put-away write-through is **optional one-shot** onto Container location.
- Storage browse lives **outside** experiments.
- **Bounce storage-as-entry.**

**L2 — Result vs normalize (LOCKED with Hans 2026-08-24):**

- Result publish write-throughs **inventory conc onto the 1×1 Container**, **same transaction**.
- Aliquot plan / normalize offers **that prior Result only** (picker §5.8) — **never** vessel (`Container.concentration`) or contents conc as the assay number.
- Result unit ≠ inventory conc unit → **refuse** (no silent convert).

### 5.7 Bounce bars added by this fold

| Bounce | Why |
|--------|-----|
| Mass/conc on Sample | Identity ≠ inventory |
| Independent `Container.amount` ≠ Σ `Contents.amount` | Total is sum (or derived); not a second mass ledger |
| Mixture conc by summing content concs | Vessel conc on Container only |
| Divergent Contents.conc vs Container.conc on a single-content tube | Vessel SoT; mirror or RO |
| Inventory on multi-element parent | Structure only |
| Storage-as-entry | L1 |
| Normalize from vessel/contents conc | L2 + Hans: prior Result only (§5.8) |
| Result outside same analysis / concentration analyte | Hans §5.8 |
| Silent unit convert Result → inventory conc | Hans: refuse |

### 5.8 Hans CSO locks (2026-08-24) — **LOCKED**

No longer OPEN. Hans **Accept**. Canonical wording also in [mass-concentration-contents.md](../tech-sketch/mass-concentration-contents.md) §10.

| Lock | Rule |
|------|------|
| **Which Result** | Same **analysis** (or that analysis’s **concentration analyte**) only. If an **approved/reviewed** row exists → use it; else **latest by entry date**. **Zero matching → refuse** normalize. |
| **Unit mismatch** | Result unit ≠ 1×1 `Container.concentration` unit → **refuse**. No silent convert. |
| **L2 / stale** | Result publish write-throughs inventory conc onto the **1×1 Container** (same txn). Aliquot plan offers **only that Result** as the assay number — never vessel conc. |

Unchanged SoT (Marc): Sample has no mass/conc; `Contents.amount` = per-row mass; `Container.amount` = Σ contents; `Container.concentration` = vessel inventory conc.
