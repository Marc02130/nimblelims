# Tech sketch: Mass and concentration live on Contents (not Sample)

**Date:** 2026-08-24  
**Status:** **Draft for Design Group agree** — Design Group review  
**Audience:** Design Group — Heidi (Architecture), Hans (Scientific CSO), Deiter (Lab Ops); CEO Rolf  
**Stem:** `mass-concentration-contents`  
**This PR:** docs only. No application/product code. **Not IC50.**  
**Coding:** stays Grok Build / paused unless Marc instructs.

**Related (do not duplicate; fold locks):**

| Doc | Role |
|-----|------|
| [`.docs/open-questions/containers.md`](../open-questions/containers.md) | Option A (solute mass); nesting; Contents only on 1×1; volume not stored |
| [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 | Same container/amount/aliquot spine |
| [`.docs/tech-sketch/configurable-entries-framework.md`](configurable-entries-framework.md) | Two kinds; dest FieldDefinitions not Sample schema |
| [`.docs/tech-sketch/extract-hold-dest-type.md`](extract-hold-dest-type.md) | Aliquot/pool execute; dest fields on dest entry; normalization bounce free type-in |
| [`.docs/ideas/containers-model-update.md`](../ideas/containers-model-update.md) | Implement slice still pending for rows×columns / 1×1 enforce |

This document **does not invent** past those locks. It states **why** amount/mass and **inventory** concentration belong on **Contents**, why Contents always hang on a parent **Container**, and how write-back / dest fields / normalization must not put mass or concentration on **Sample**.

---

## 0. Why this sketch exists

Labs talk about “the sample’s concentration” and “how much DNA we have.” Those phrases mix **identity** with **inventory in a vessel**. If mass or concentration lives on Sample:

- Aliquot / dilute / transfer rewrite identity instead of the vessel contents.
- Dest FieldDefinitions become a second ledger (or get written onto Sample columns — already bounced).
- Normalization free-types a number that is neither a Result nor inventory.
- A plate looks like it “contains” liquid, so pooling and well-level inventory break.

**Ask of this review:** agree that **Sample has no mass and no concentration**; **Contents** (always on a 1×1 parent Container) is the inventory SoT for amount/mass and inventory concentration (with units FKs); dest entry cells are capture or RO projection, never a second ledger.

---

## 1. Locked spine (fold)

| # | Lock | Source |
|---|------|--------|
| 1 | **Sample** = identity + `sample_type` + lineage (`parent_sample_id`). **No mass. No concentration.** | This agree; extract-hold bounce of new Sample columns for amount/vol/conc |
| 2 | Something *in a vessel* has mass/amount and possibly concentration → that is **Contents** (units FKs). | containers.md; this agree (inventory SoT on Contents) |
| 3 | Contents always hang on a **1×1 parent Container** (`rows=1`, `columns=1`): tube, well, vial, test tube. Multi-element (plate/rack/box) = **structure only**; contents only on children. | containers.md §0.2–0.6; experiment-template-entries §0.8 |
| 4 | **Volume is not primary SoT** when mass + conc allow \( V = m / C \) (**Option A**). Inbound volume + conc → store mass + conc; drop volume. **Do not reopen.** | containers.md §0.1 |
| 5 | Four write-back targets (Heidi) — §5 | This agree |
| 6 | Dest FieldDefinitions after mint: **RO projections of contents** by default; writable only if write-through to contents **same txn**. **Bounce Sample write-back of mass/conc.** | This agree; extract-hold dest fields on `aliquots_pools` |
| 7 | Normalization (`aliquot_by_target_concentration`): read **prior Result** (assay conc); on execute write-through to contents (or **refuse** if no Result). **Bounce free type-in.** | extract-hold §4.1 |
| 8 | Hans holes — **OPEN**, do not fake-close — §8 | This agree |
| 9 | Pool multi-source lineage still **open** (composition on plan; one `parent_sample_id` is not full lineage) — pointer only | extract-hold mint; experiments Q18 |
| 10 | Not IC50. Coding paused / Grok Build unless Marc instructs. | This packet |

---

## 2. Why amount/mass and inventory concentration live on Contents

**Sample answers “what is this material?”** Type, identity, parent lineage. Those facts survive a move between tubes and a split into daughters. Putting grams or ng/µL on Sample pretends inventory is a property of identity.

**Contents answers “how much of that identity is in *this* vessel *now*?”** Amount/mass (solute mass or count — Option A) and inventory concentration (mass/volume of the defined solute at that vessel), each with units FKs. Dilute changes concentration, not solute amount. Transfer/aliquot execute mutates source and dest **contents**, not Sample rows’ identity fields.

**Assay concentration is not inventory concentration.** A Qubit (or other analysis) **Result** is a measurement event. Inventory conc on Contents is the working stock number used for \( V = m / C \) and aliquot math. Collapsing both onto Sample (or treating `contents.concentration` as the assay number) is how stale Qubit vs stock happens — Hans hole, §8.

**Pooling.** Multiple Contents rows on **one** 1×1 vessel (pool tube), each row = one source sample’s solute in that tube. Sample cannot hold “the pool’s mass” without erasing per-source inventory. Vessel-level total on Container (containers.md §0.3) stays a **consistency** rule with contents sums — **not** a second independent ledger and **not** Sample. This sketch does not reopen that 2026-08-11 consistency row and does not move inventory SoT off Contents.

---

## 3. Why Contents always need a parent Container

Contents is **not** a free-floating inventory row. Mass/concentration without a vessel has no location, no barcode, no well coordinate, and no unit of account for put-away or pipette-from.

| Layer | Role | Holds Contents? |
|-------|------|-----------------|
| Multi-element Container (plate, rack, box) | Structure: child positions (`row`/`column` on children). | **No** |
| **1×1 Container** (tube, plate well, vial, test tube) | Liquid-bearing unit of account. Location (and optional put-away write-through). | **Yes** |
| **Contents** | Sample in that vessel + amount/mass + inventory conc + units FKs. | — |

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

Existing product bounce (extract-hold / framework): dest amount/volume/concentration are **entry FieldDefinitions** on `aliquots_pools`, not Sample schema and not a Sample/`material_class` column. This sketch adds the SoT behind those fields: **Contents**, via RO projection or same-txn write-through.

---

## 5. Four write-back targets (Heidi)

Exactly four. Entry cells are not a fifth inventory table.

| Target | Owns | Does not own |
|--------|------|----------------|
| **Sample** | Identity + **allowlisted** attributes. Execute sets `sample_type` / `parent_sample_id`. | Mass, inventory conc, volume, location |
| **Contents** | **SoT** for mass/amount, inventory concentration, units FKs. Aliquot execute **mutates contents**. | Identity, assay Result, storage browse tree |
| **Container** | Location; optional **put-away write-through**. Storage browse lives **outside** experiments. | Inventory SoT (contents); Sample identity |
| **Entry cells** | Process **capture** **or** **RO projection** of SoT. | A second ledger of mass/conc |

**Bounce:** Sample write-back of mass or concentration. Last-write-wins Sample allowlist (experiments Q4) does not grow to include mass/conc.

**Dest FieldDefinitions after mint:** default **read-only projections** of contents. Writable **only** if the same transaction write-throughs to contents. Otherwise operators edit a ghost number that execute and storage will not see.

---

## 6. Option A (mention only — already locked)

Canonical: [`.docs/open-questions/containers.md`](../open-questions/containers.md) §0.1.

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
| Source of that number | **Prior Result** on that sample — **not** free type-in on the plan line |
| On execute | Write-through inventory to **contents** (dest amount/conc as the method requires), or **refuse** if no Result |
| Dest FieldDefinitions | Projection / write-through per §5 — not Sample |

**Bounce:** typing a concentration on the plan because “we know it from the Qubit printout.” If the Result is missing, execute refuses.

---

## 8. Hans open holes — **OPEN** (do not fake-close)

These block a clean implement of normalization + inventory conc. Design Group may decide later; this PR does **not** pick winners.

| Hole | Why it is open | Must not do until decided |
|------|----------------|---------------------------|
| **Which Result when replicates exist?** Latest vs approved vs same analysis only. | Extract-hold says “prior result”; replicate / review semantics are unspecified. | Invent a silent pick (e.g. “newest float named concentration”). |
| **Result unit ≠ contents unit** | Assay units and inventory units FKs can disagree. | **Refuse.** Do **not** convert silently. |
| **Stale `contents.conc` between Qubit publish and next aliquot** | Result publish and inventory SoT can diverge. | Either: Result entry/path **also write-throughs inventory** on Contents, **or** UI **never** treats `contents.concentration` as the assay number. Pick one in a later agree — both remain OPEN here. |

---

## 9. Pool multi-source lineage — pointer only

**Open.** Pool execute mints a dest sample with **one** `parent_sample_id`. That is not full multi-source lineage. Composition belongs on the **plan** (source lines) until a lineage/composition model is agreed.

Do not invent a composition table, JSON parent list, or “primary parent” rule in this sketch. See extract-hold mint/pool rules and experiments Q18 (aliquot child samples / volume) as related open work. **Not blocking this agree** on Contents vs Sample.

---

## 10. Bounce bars (this agree)

| Bounce | Why |
|--------|-----|
| Mass or concentration columns on **Sample** | Identity ≠ inventory |
| Sample write-back of mass/conc | Wrong target (Heidi §5) |
| Contents on multi-element parent (plate/rack) | Structure only; contents on 1×1 children |
| Contents with no parent Container | No vessel = no inventory |
| Dest FieldDefinitions as a writable second ledger | Must RO-project or same-txn write-through to contents |
| Free type-in parent conc on normalization | Prior Result or refuse |
| Silent unit conversion Result → contents | Hans: refuse |
| Reopening Option A / storing volume as SoT | Locked 2026-08-11 |
| Closing Hans holes or pool composition in this PR | Stay OPEN |
| IC50 / coding this packet | Docs only; Grok Build unless Marc instructs |

---

## 11. Status and coding gate

| Item | Value |
|------|--------|
| Status | **Draft for Design Group agree** |
| Status line | **Design Group review** |
| IC50 | **Not IC50** |
| Code in this PR | **None** (docs only) |
| Application coding | **Grok Build / paused** unless Marc instructs |

Schema implement for rows×columns / 1×1 Contents enforce remains the containers idea slice — **not** unpaused by this agree.

---

## 12. Reviews

Empty stamps for Design Group + CEO to fill later. Do not treat this table as Accept until stamped.

| Review | Reviewer | Verdict | Date | Notes |
|--------|----------|---------|------|-------|
| **CEO** | Rolf | _pending_ | | |
| **Architecture** | Heidi | _pending_ | | Four write-back targets; Contents SoT; dest projection/write-through |
| **Lab Ops** | Deiter | _pending_ | | 1×1 vessel; contents not on plates |
| **CSO** | Hans | _pending_ | | Holes in §8 remain OPEN |

**Implement gate for this agree:** closed until Design Group + CEO stamp. This PR does not unpause application coding.
