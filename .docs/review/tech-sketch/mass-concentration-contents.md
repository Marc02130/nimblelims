# Tech sketch: Mass and concentration ownership (not Sample)

**Date:** 2026-08-24  
**Status:** **Draft — Design Group coherence fold; pending re-stamp**
**Audience:** Design Group — Heidi (Architecture), Hans (Scientific CSO), Deiter (Lab Ops); CEO Rolf  
**Stem:** `mass-concentration-contents`  
**This PR:** docs only. No application/product code. **Not IC50.**  
**Coding:** stays Grok Build / paused unless Marc instructs.

**Related (do not duplicate; fold locks):**

| Doc | Role |
|-----|------|
| [`.docs/review/open-questions/containers.md`](../open-questions/containers.md) | Option A (solute mass); nesting; Contents only on 1×1; volume not stored |
| [`.docs/review/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 | Same container/amount/aliquot spine |
| [`.docs/review/tech-sketch/configurable-entries-framework.md`](configurable-entries-framework.md) | Two kinds; dest FieldDefinitions not Sample schema |
| [`.docs/review/tech-sketch/extract-hold-dest-type.md`](extract-hold-dest-type.md) | Aliquot/pool execute; dest fields on dest entry; normalization bounce free type-in |
| local `.docs/internal/ideas/containers-model-update.md` (not committed) | Implement slice still pending for rows×columns / 1×1 enforce |

This document folds the existing container locks with the Result decisions recorded for this packet. It states why per-sample amount belongs on **Contents**, why vessel total amount and inventory concentration belong on the **1×1 Container**, and why write-back / destination fields / normalization must not put mass or concentration on **Sample**.

---

## 0. Why this sketch exists

Labs talk about “the sample’s concentration” and “how much DNA we have.” Those phrases mix **identity** with **inventory in a vessel**. If mass or concentration lives on Sample:

- Aliquot / dilute / transfer rewrite identity instead of the vessel contents.
- Dest FieldDefinitions become a second ledger (or get written onto Sample columns — already bounced).
- Normalization free-types a number that is neither a Result nor inventory.
- A plate looks like it “contains” liquid, so pooling and well-level inventory break.

**Ask of this review:** re-stamp the coherent ownership model: **Sample has no mass and no concentration**; `Contents.amount` is per-row mass/count; 1×1 `Container.amount` is the compatible-unit sum of Contents rows; 1×1 `Container.concentration` is vessel inventory concentration; destination entry cells are capture or RO projection/write-through, never a second ledger.

---

## 1. Locked spine (fold)

| # | Lock | Source |
|---|------|--------|
| 1 | **Sample** = identity + `sample_type` + lineage (`parent_sample_id`). **No mass. No concentration.** | This agree; extract-hold bounce of new Sample columns for amount/vol/conc |
| 2 | **`Contents.amount`** is the per-row mass/count for one Sample in the vessel. `Contents.concentration` is **not** the inventory-concentration SoT. | containers.md; Marc fold |
| 3 | Contents always hang on a **1×1 parent Container** (`rows=1`, `columns=1`): tube, well, vial, test tube. Multi-element (plate/rack/box) = **structure only**; contents only on children. | containers.md §0.2–0.6; experiment-template-entries §0.8 |
| 4 | **Volume is not primary SoT** when mass + conc allow \( V = m / C \) (**Option A**). Inbound volume + conc → store mass + conc; drop volume. **Do not reopen.** | containers.md §0.1 |
| 5 | **1×1 `Container.amount`** = compatible-unit sum of `Contents.amount`; **1×1 `Container.concentration`** = vessel inventory concentration. Update with Contents in the same transaction or derive; never maintain an independent conflicting total. | containers.md; Marc fold |
| 6 | Four write-back targets (Heidi) — §5 | This fold |
| 7 | Dest FieldDefinitions after mint: **RO projections** by default; writable only with a same-transaction write-through to the owning Contents or Container field. **Bounce Sample write-back of mass/conc.** | This fold; extract-hold dest fields on `aliquots_pools` |
| 8 | Normalization and Result publication follow **Hans §10 LOCKED**. | Hans fold |
| 9 | Pool multi-source lineage still **open** (composition on plan; one `parent_sample_id` is not full lineage) — pointer only | extract-hold mint; experiments Q18 |
| 10 | Not IC50. Coding paused / Grok Build unless Marc instructs. | This packet |

---

## 2. Why amount is per Contents row and concentration is vessel-scoped

**Sample answers “what is this material?”** Type, identity, parent lineage. Those facts survive a move between tubes and a split into daughters. Putting grams or ng/µL on Sample pretends inventory is a property of identity.

**Contents answers “how much of that identity is in this vessel now?”** `Contents.amount` is the per-row solute mass or count for one Sample. Transfer/aliquot execute mutates the affected Contents rows and updates the 1×1 vessel totals in the same transaction.

**The 1×1 Container answers “what is true of the vessel as a whole?”** `Container.amount` is the compatible-unit sum of its Contents rows. `Container.concentration` is the vessel inventory concentration used for \( V = m / C \) and transfer math. **Bounce `Contents.concentration` as the inventory-concentration SoT.**

**Assay concentration is not inventory concentration.** A Qubit (or other analysis) **Result** is a measurement event. Result publication may update the bound 1×1 vessel inventory concentration under §10, but normalization still selects the Result, not a vessel or Contents value.

**Pooling.** Multiple Contents rows on one 1×1 vessel preserve each source Sample’s contribution. The Container total is the sum, not a separately editable second ledger. Sample cannot hold the pool’s mass without erasing per-source inventory.

---

## 3. Why Contents always need a parent Container

Contents is **not** a free-floating inventory row. Amount without a vessel has no location, no barcode, no well coordinate, and no unit of account for put-away or pipette-from.

| Layer | Role | Holds Contents? |
|-------|------|-----------------|
| Multi-element Container (plate, rack, box) | Structure: child positions (`row`/`column` on children). | **No** |
| **1×1 Container** (tube, plate well, vial, test tube) | Liquid-bearing unit of account. Location (and optional put-away write-through). | **Yes** |
| **Contents** | Sample in that vessel + per-row amount/mass/count + unit FK. | — |

A 96-well plate is not a bottle. Liquid lives in **wells** (1×1 children). Pooling is many contents on one 1×1 tube, not contents on the plate.

Atomic receive already creates **sample + first container + contents** in one transaction. Aliquot/pool execute creates dest 1×1 containers and dest contents (and dest samples with `parent_sample_id` per extract-hold). There is no “contents without a tube.”

---

## 4. Sample does not have mass or concentration

| On Sample | Not on Sample |
|-----------|----------------|
| Identity (`samples.name` / system ID) | Amount / mass |
| `sample_type` | Inventory concentration |
| `parent_sample_id` (single parent; pool composition still open) | Volume as stored SoT |
| Allowlisted attributes (write-back map — never mass/conc) | Dest aliquot numbers as Sample columns |

Execute may set `sample_type` / `parent_sample_id` on mint. It must **not** write mass or concentration onto Sample.

Existing product bounce (extract-hold / framework): destination amount/volume/concentration are **entry FieldDefinitions** on `aliquots_pools`, not Sample schema and not a Sample/`material_class` column. This sketch states the owners behind those cells: per-row mass/count projects or writes through to Contents; total mass and vessel concentration project or write through to the 1×1 Container.

---

## 5. Four write-back targets (Heidi)

Exactly four. Entry cells are not a fifth inventory table.

| Target | Owns | Does not own |
|--------|------|----------------|
| **Sample** | Identity + **allowlisted** attributes. Execute sets `sample_type` / `parent_sample_id`. | Mass, inventory conc, volume, location |
| **Contents** | Per-row mass/count and amount unit FK. Aliquot execute mutates source/destination rows. | Identity, vessel concentration, assay Result, storage browse tree |
| **Container** | 1×1 total amount (= compatible-unit sum of Contents), vessel inventory concentration, location, and optional one-shot put-away write-through. Storage browse lives **outside** experiments. | Per-source contribution; Sample identity |
| **Entry cells** | Process **capture** **or** **RO projection** of SoT. | A second ledger of mass/conc |

**Bounce:** Sample write-back of mass or concentration. Last-write-wins Sample allowlist (experiments Q4) does not grow to include mass/conc.

**Destination FieldDefinitions after mint:** default **read-only projections**. Per-row mass/count projects `Contents.amount`; total mass and vessel concentration project the 1×1 Container. A writable cell is allowed only when the same transaction writes through to the owning field and preserves `Container.amount = Σ Contents.amount`. Otherwise the operator would edit a ghost number that execute and storage cannot trust.

---

## 6. Option A (mention only — already locked)

Canonical: [`.docs/review/open-questions/containers.md`](../open-questions/containers.md) §0.1.

- Amount = **solute mass** (or count for cells/colonies) — never volume, never diluent mass.
- Volume **never stored** as primary SoT; derive \( V = m_{\text{solute}} / C \) when units convert cleanly.
- Diluent changes **concentration** (derived volume); does **not** increase stored solute amount.

**Do not reopen Option B** (solution total mass / density-based volume). This sketch does not change that lock.

---

## 7. Normalization (`aliquot_by_target_concentration`)

Fold extract-hold §4.1; do not duplicate METHOD_CATALOG tables.

| Rule | Detail |
|------|--------|
| Parent / source assay conc | **Required** |
| Source of that number | Eligible **prior Result** selected under §10 — not free type-in, `Contents.concentration`, or `Container.concentration` |
| On execute | Use the selected Result; update destination Contents amount and 1×1 Container amount/concentration in the same transaction, or refuse |
| Dest FieldDefinitions | Projection / write-through per §5 — not Sample |

**Bounce:** typing a concentration on the plan because “we know it from the Qubit printout.” If the Result is missing, execute refuses.

---

## 8. Result questions superseded by §10

The earlier draft left Result choice, units, and stale inventory concentration open. Those questions are now resolved by **Hans §10 LOCKED**. Pool multi-source lineage remains open in §9.

---

## 9. Pool multi-source lineage — pointer only

**Open.** Pool execute mints a dest sample with **one** `parent_sample_id`. That is not full multi-source lineage. Composition belongs on the **plan** (source lines) until a lineage/composition model is agreed.

Do not invent a composition table, JSON parent list, or “primary parent” rule in this sketch. See extract-hold mint/pool rules and experiments Q18 (aliquot child samples / volume) as related open work. **Not blocking this agree** on Contents vs Sample.

---

## 10. Hans §10 LOCKED — Result publication and normalization

These four rules are visible here and in [open-questions/containers.md](../open-questions/containers.md). Implement them as one contract:

1. **Which Result:** normalization may select only a concentration Result from the **same analysis** (or that analysis’s designated concentration analyte) for the source Sample. Prefer an approved/reviewed matching Result; if none is approved/reviewed, use the latest matching Result by entry date. Zero matches → **refuse**.
2. **Units:** if the selected Result unit does not equal the configured vessel inventory-concentration unit, **refuse**. Do not silently convert.
3. **Publish write-through:** publishing that Result writes its concentration and unit to the bound **1×1 `Container.concentration`** in the same transaction. It does not write concentration to Sample or make `Contents.concentration` the SoT.
4. **Normalization picker:** `aliquot_by_target_concentration` offers eligible **Results only**. It never offers free text, `Contents.concentration`, or `Container.concentration` as the assay measurement.

---

## 11. Bounce bars (this agree)

| Bounce | Why |
|--------|-----|
| Mass or concentration columns on **Sample** | Identity ≠ inventory |
| Sample write-back of mass/conc | Wrong target (Heidi §5) |
| Contents on multi-element parent (plate/rack) | Structure only; contents on 1×1 children |
| Contents with no parent Container | No vessel = no inventory |
| `Contents.concentration` as inventory-concentration SoT | Vessel inventory concentration belongs on the 1×1 Container |
| Independently editable `Container.amount` | It must equal the compatible-unit sum of `Contents.amount` |
| Dest FieldDefinitions as a writable second ledger | Must RO-project or same-txn write-through to the owning Contents/Container field |
| Free type-in parent conc on normalization | Prior Result or refuse |
| Normalization from vessel/Contents concentration | Picker offers eligible Results only |
| Silent Result-unit conversion | Hans: refuse |
| Reopening Option A / storing volume as SoT | Locked 2026-08-11 |
| Inventing pool composition in this PR | Pool lineage stays OPEN |
| IC50 / coding this packet | Docs only; Grok Build unless Marc instructs |

---

## 12. Status and coding gate

| Item | Value |
|------|--------|
| Status | **Draft — Design Group coherence fold** |
| Status line | **Pending re-stamp after fold** |
| IC50 | **Not IC50** |
| Code in this PR | **None** (docs only) |
| Application coding | **Grok Build / paused** unless Marc instructs |

Schema implement for rows×columns / 1×1 Contents enforce remains the containers idea slice — **not** unpaused by this agree.

---

## 13. Reviews

Pending Design Group re-stamp after the body was corrected from Contents concentration to 1×1 Container concentration. Heidi’s prior Architecture verdict was **Revise until the sketch matched**; the body now matches and awaits her new verdict. Do not infer Accept from the fold.

| Review | Reviewer | Verdict | Date | Notes |
|--------|----------|---------|------|-------|
| **CEO** | Rolf | _pending re-stamp_ | | |
| **Architecture** | Heidi | _pending re-stamp_ | | Prior Revise condition addressed: per-row Contents amount; vessel total/concentration |
| **Lab Ops** | Deiter | _pending re-stamp_ | | Storage outside experiments; one-shot put-away only |
| **CSO** | Hans | _pending re-stamp_ | | §10 locked Result contract folded |

**Implement gate for this agree:** closed until Design Group + CEO stamp. This PR does not unpause application coding.
