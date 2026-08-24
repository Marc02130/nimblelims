# Tech sketch: Mass and concentration live on Contents and 1×1 Container (not Sample)

**Date:** 2026-08-24  
**Status:** **Draft for Design Group agree** — Design Group review  
**Audience:** Design Group — Heidi (Architecture), Hans (Scientific CSO), Deiter (Lab Ops); CEO Rolf  
**Stem:** `mass-concentration-contents`  
**This PR:** docs only. No application/product code. **Not IC50.**  
**Coding:** stays Grok Build / paused unless Marc instructs.

**Related (do not duplicate; fold locks):**

| Doc | Role |
|-----|------|
| [`.docs/open-questions/containers.md`](../open-questions/containers.md) | Option A; nesting; Contents on 1×1 only; **§5 Design Group SoT** (Sample ≠ inventory; Contents per-row mass; 1×1 total mass + vessel conc) |
| [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 | Same container/amount/aliquot spine |
| [`.docs/tech-sketch/configurable-entries-framework.md`](configurable-entries-framework.md) | Two kinds; dest FieldDefinitions not Sample schema |
| [`.docs/tech-sketch/extract-hold-dest-type.md`](extract-hold-dest-type.md) | Aliquot/pool execute; dest fields on dest entry; normalization bounce free type-in |
| [`.docs/ideas/containers-model-update.md`](../ideas/containers-model-update.md) | Implement slice still pending for rows×columns / 1×1 enforce |

This document **does not invent** past those locks. It states **why** per-row amount/mass lives on **Contents**, why **total mass** and **inventory concentration** live on the **1×1 parent Container**, why Contents always hang on that Container, and how write-back / dest fields / normalization must not put mass or concentration on **Sample**.

**Marc lock (2026-08-24, critical refine):** Mass **can** live on **Contents** (per content row — e.g. each pool contribution). The **1×1 Container** stores **total mass** (sum of contents for pools) **and concentration**. Sample still has neither. Multi-element containers remain structure only.

**Deiter Lab Ops (2026-08-24):** **Accept with conditions** — L1 locked; L2 now **LOCKED with Hans** (§10).

**Hans CSO (2026-08-24):** **Accept** with §10 locks (which Result; unit mismatch refuse; L2/stale write-through). No longer OPEN.

---

## 0. Why this sketch exists

Labs talk about “the sample’s concentration” and “how much DNA we have.” Those phrases mix **identity** with **inventory in a vessel**. If mass or concentration lives on Sample:

- Aliquot / dilute / transfer rewrite identity instead of the vessel.
- Dest FieldDefinitions become a second ledger (or get written onto Sample columns — already bounced).
- Normalization free-types a number that is neither a Result nor inventory.
- A plate looks like it “contains” liquid, so pooling and well-level inventory break.

If **all** mass **and** concentration were forced onto Contents only, a pool tube would have no single total-mass / working-concentration SoT, and per-contribution rows would be asked to carry a vessel-level concentration they do not own.

**Ask of this review:** agree that **Sample has no mass and no concentration**; **Contents** hold **per-row mass** (each contribution in the vessel); the **1×1 parent Container** holds **total mass** (sum of contents for pools) **and inventory concentration**; dest entry cells are capture or RO projection, never a second ledger.

---

## 1. Locked spine (fold)

| # | Lock | Source |
|---|------|--------|
| 1 | **Sample** = identity + `sample_type` + lineage (`parent_sample_id`). **No mass. No concentration.** | This agree; extract-hold bounce of new Sample columns for amount/vol/conc; **Marc 2026-08-24** |
| 2 | Something *in a vessel* has **per-row mass/amount** → that is **Contents** (units FK). Example: each pool contribution. | **Marc 2026-08-24**; containers.md content rows |
| 3 | Contents always hang on a **1×1 parent Container** (`rows=1`, `columns=1`): tube, well, vial, test tube. Multi-element (plate/rack/box) = **structure only**; **no liquid inventory on plates/racks as parents**; contents only on children. | containers.md §0.2–0.6; experiment-template-entries §0.8; **Marc 2026-08-24** |
| 4 | That **1×1 Container** stores **total mass** (sum of contents for pools) **and inventory concentration** (units FKs). | **Marc 2026-08-24**; containers.md §0.3 vessel total + conc |
| 5 | **Volume is not primary SoT** when mass + conc allow \( V = m / C \) (**Option A**). Inbound volume + conc → store mass + conc; drop volume. **Do not reopen.** | containers.md §0.1 |
| 6 | Four write-back targets (Heidi), SoT split per §5 | This agree; Marc refine |
| 7 | Dest FieldDefinitions after mint: **RO projections of the matching SoT** by default (per-row mass ← Contents; total mass + inventory conc ← 1×1 Container); writable only if write-through to that SoT **same txn**. **Bounce Sample write-back of mass/conc.** | This agree; extract-hold dest fields on `aliquots_pools`; Marc refine |
| 8 | Normalization (`aliquot_by_target_concentration`): assay number is **prior Result** only, picker per **§10** (same analysis / concentration analyte; approved else latest by entry date; zero match → refuse). **Never** offer container/contents conc as the assay number. **Bounce free type-in.** | extract-hold §4.1; **Hans §10 LOCK**; Deiter L2 |
| 9 | Hans CSO §10 — **LOCKED** (2026-08-24): which Result; unit mismatch refuse; L2/stale write-through to 1×1 Container. | **Hans Accept** |
| 10 | Pool multi-source **lineage** still **open** (composition on plan; one `parent_sample_id` is not full lineage) — pointer only. Per-row **mass** on Contents is locked; lineage graph is not. | extract-hold mint; experiments Q18; Marc lock |
| 11 | Put-away: optional **one-shot** write-through; storage browse **outside** experiments; **bounce storage-as-entry**. | **Deiter L1** (locked) |
| 12 | Not IC50. Coding paused / Grok Build unless Marc instructs. | This packet |

---

## 2. Why per-row mass lives on Contents

**Sample answers “what is this material?”** Type, identity, parent lineage. Those facts survive a move between tubes and a split into daughters. Putting grams or ng/µL on Sample pretends inventory is a property of identity.

**Contents answers “how much of *this identity* is in *this* vessel *now*?”** One row per sample-in-vessel. Amount/mass on that row is **solute mass (or count) of that contribution** — Option A — with a units FK. Dilute does not increase that solute amount. Transfer/aliquot execute mutates source and dest **content rows** (and the 1×1 vessel totals — §3), not Sample identity fields.

**Pooling.** Multiple Contents rows on **one** 1×1 vessel (pool tube), each row = one source sample’s solute mass in that tube. Sample cannot hold “the pool’s mass” without erasing per-source inventory. Contents **can** hold those contribution masses — that is the Marc refine.

**Assay concentration is not inventory concentration.** A Qubit (or other analysis) **Result** is a measurement event. Inventory conc lives on the **1×1 Container** (§3), not on Sample and not as the assay number in the normalize picker (**Hans §10 / L2 locked**).

---

## 3. Why the 1×1 Container holds total mass and inventory concentration

A pool (or any multi-content vessel) is one physical liquid body. Pipette-from, \( V = m / C \), and “what is the stock concentration?” need **one** total mass and **one** inventory concentration for that vessel.

| Quantity | SoT | Why |
|----------|-----|-----|
| Per-contribution mass | **Contents** row | Each source’s solute in the vessel (pool contributions). |
| **Total mass** | **1×1 Container** | Sum of contents masses for pools; the vessel’s solute total for \( V = m / C \). |
| **Inventory concentration** | **1×1 Container** | Working stock \( C \) of the defined solute at that vessel. Not Sample. Not the assay Result. |
| Assay concentration | **Result** | Measurement event. Normalize reads this (Hans §10 / L2 locked). |

This matches [containers.md](../open-questions/containers.md) §0.3 and **§5** (2026-08-23/24) and **does not reopen Option A**. It **does** correct an earlier draft of this sketch that over-stated “all mass and conc only on Contents.”

### 3.1 Total mass = Σ contents (same txn)

On a 1×1 vessel, `Container.amount` **must equal** `sum(Contents.amount)` (same mass basis / convertible units). Maintain that equality **in the same transaction** as content-row edits, **or** treat the container total as **derived**. **Bounce** independent edit of vessel total vs the sum — that would be a second mass ledger (Heidi).

Aliquot / pool / dilute execute already updates content amounts and vessel amount/conc **together** (containers.md §0.3 item 7).

### 3.2 Inventory concentration — vessel only

| Case | Rule |
|------|------|
| Result write-through | Inventory conc → **1×1 `Container.concentration`** (same txn as publish — **L2 locked**). Not Sample. Not Contents as SoT. |
| Single-content tube | Do **not** let `Contents.concentration` and `Container.concentration` diverge. Contents conc is **optional / RO** or a **same-txn mirror**. Vessel remains SoT. |
| Multi-content pool | Vessel conc on **Container only**. **Bounce** inventing mixture conc by summing or averaging content concs. |

Assay conc remains a **Result**. Normalize never offers vessel/contents conc as the assay number (**L2 locked**).

---

## 4. Why Contents always need a parent Container

Contents is **not** a free-floating inventory row. Per-row mass without a vessel has no location, no barcode, no well coordinate, and no unit of account for put-away or pipette-from. Total mass and inventory concentration have nowhere to live without that 1×1 vessel.

| Layer | Role | Holds Contents? | Liquid inventory? |
|-------|------|-----------------|-------------------|
| Multi-element Container (plate, rack, box) | Structure: child positions (`row`/`column` on children). | **No** | **No** — not on the parent |
| **1×1 Container** (tube, plate well, vial, test tube) | Liquid-bearing unit of account. **Total mass + inventory conc.** Location (put-away per L1). | **Yes** | **Yes** |
| **Contents** | Sample in that vessel + **per-row mass** (+ units FK). | — | Per-row mass only |

A 96-well plate is not a bottle. Liquid lives in **wells** (1×1 children). Pooling is many contents on one 1×1 tube, not contents (or conc) on the plate.

Atomic receive already creates **sample + first container + contents** in one transaction. Aliquot/pool execute creates dest 1×1 containers and dest contents (and dest samples with `parent_sample_id` per extract-hold). There is no “contents without a tube.”

---

## 5. Sample does not have mass or concentration

| On Sample | Not on Sample |
|-----------|----------------|
| Identity (`samples.name` / system ID) | Per-row amount / mass (that is Contents) |
| `sample_type` | Total mass (that is 1×1 Container) |
| `parent_sample_id` (single parent; pool composition still open) | Inventory concentration (that is 1×1 Container) |
| Allowlisted attributes (write-back map — never mass/conc) | Assay concentration (that is Result); volume as stored SoT |

Execute may set `sample_type` / `parent_sample_id` on mint. It must **not** write mass or concentration onto Sample.

Existing product bounce (extract-hold / framework): dest amount/volume/concentration are **entry FieldDefinitions** on `aliquots_pools`, not Sample schema and not a Sample/`material_class` column. This sketch adds the SoT behind those fields: **Contents** (per-row mass) and **1×1 Container** (total mass + inventory conc), via RO projection or same-txn write-through.

---

## 6. Four write-back targets (Heidi) — SoT split

Exactly four. Entry cells are not a fifth inventory table.

| Target | Owns | Does not own |
|--------|------|----------------|
| **Sample** | Identity + **allowlisted** attributes. Execute sets `sample_type` / `parent_sample_id`. | Mass (row or total), inventory conc, volume, location |
| **Contents** | **SoT for per-row mass/amount** (units FK). Aliquot execute **mutates content rows**. Pool = one row per contribution. | Inventory concentration; vessel total mass; identity; assay Result; storage browse tree |
| **Container** (1×1 only for inventory) | **SoT for total mass** (sum of contents for pools) **and inventory concentration**. Location; optional **put-away write-through** (L1). Storage browse lives **outside** experiments. | Per-row contribution mass (Contents); Sample identity; assay Result |
| **Entry cells** | Process **capture** **or** **RO projection** of the matching SoT. | A second ledger of mass/conc |

**Bounce:** Sample write-back of mass or concentration. Last-write-wins Sample allowlist (experiments Q4) does not grow to include mass/conc.

**Dest FieldDefinitions after mint:** default **read-only projections** of the matching SoT (per-row mass ← Contents; total mass + inventory conc ← 1×1 Container). Writable **only** if the same transaction write-throughs to that SoT. Otherwise operators edit a ghost number that execute and storage will not see.

**Do not read this table as “all mass and conc only on Contents.”** That wording conflicted with Marc’s refine and with containers.md §0.3.

---

## 7. Deiter Lab Ops conditions

### L1 — put-away and storage browse (**locked**)

| Rule | Detail |
|------|--------|
| Put-away write-through | **Optional one-shot.** Execute may write location onto the Container when the operator puts away; it is not a standing storage UI inside the experiment. |
| Storage browse | Lives **outside** experiments. |
| Bounce | **Storage-as-entry** — do not model the freezer/rack tree as an experiment entry kind. |

### L2 — Result publish vs normalize picker (**LOCKED** — Hans 2026-08-24)

| Rule | Detail |
|------|--------|
| Result publish | Write-throughs **inventory concentration onto the 1×1 Container**, **same transaction** as Result publish. |
| Aliquot plan / normalize UI | Offers **only that prior Result** as the assay number (picker in §10). **Never** vessel (`Container.concentration`) or contents conc as the assay number. |
| Unit mismatch | Result unit ≠ inventory conc unit → **refuse**. Do **not** convert silently. |
| Status | **Locked** (Deiter L2 + Hans CSO). Not OPEN. |

---

## 8. Option A (mention only — already locked)

Canonical: [`.docs/open-questions/containers.md`](../open-questions/containers.md) §0.1. Design Group SoT split: same file **§5**.

- Amount = **solute mass** (or count for cells/colonies) — never volume, never diluent mass.
- Volume **never stored** as primary SoT; derive \( V = m_{\text{solute}} / C \) when units convert cleanly. \( m \) here is **1×1 Container total mass**; \( C \) is **1×1 Container inventory conc**.
- Diluent changes **concentration** on the 1×1 Container (derived volume); does **not** increase stored solute amount on contents rows.

**Do not reopen Option B** (solution total mass / density-based volume). This sketch does not change that lock.

---

## 9. Normalization (`aliquot_by_target_concentration`)

Fold extract-hold §4.1; do not duplicate METHOD_CATALOG tables.

| Rule | Detail |
|------|--------|
| Parent / source assay conc | **Required** |
| Source of that number | **Prior Result** only — picker **§10**. **Not** free type-in, **not** 1×1 container inventory conc, **not** a contents row conc |
| On execute | Mutate dest/source **content masses** and 1×1 **total mass + inventory conc** as the method requires, or **refuse** if zero matching Result |
| Dest FieldDefinitions | Projection / write-through per §6 — not Sample |

**Bounce:** typing a concentration on the plan because “we know it from the Qubit printout.” Zero matching Result → refuse.

L2 **locked:** Result publish write-throughs inventory conc onto the 1×1 Container (same txn). The aliquot plan offers only the §10 Result as the assay number — never vessel conc.

---

## 10. Hans CSO locks — **LOCKED** (2026-08-24)

No longer OPEN. Hans **Accept** with these rules. Pool **lineage** (§11) stays open; these inventory/normalize rules do not.

### 10.1 Which Result for normalize

Restrict to Results for **the same analysis** (or **that analysis’s concentration analyte**) only.

Then pick:

1. If an **approved / reviewed** row exists in that set → use it.
2. Else → **latest by entry date**.
3. **Zero matching** → **refuse** normalize (do not invent a pick; do not free type-in).

### 10.2 Unit mismatch

Result unit ≠ 1×1 Container inventory conc unit → **refuse**. **No silent convert.**

### 10.3 L2 / stale inventory conc

**Locked** with Deiter L2:

- Result publish write-throughs **inventory conc onto the 1×1 Container**, **same transaction**.
- Aliquot plan / normalize offers **only that prior Result** as the assay number — **never** vessel conc (or contents conc) as the assay number.
- Do **not** write-through inventory conc onto Contents as SoT.

---

## 11. Pool multi-source lineage — pointer only

**Open.** Pool execute mints a dest sample with **one** `parent_sample_id`. That is not full multi-source lineage. Composition belongs on the **plan** (source lines) until a lineage/composition model is agreed.

Per-row **mass** on Contents for each contribution is **locked** (Marc). Lineage graph is not. Do not invent a composition table, JSON parent list, or “primary parent” rule in this sketch. See extract-hold mint/pool rules and experiments Q18 as related open work. **Not blocking this agree** on Contents vs 1×1 Container vs Sample.

---

## 12. Bounce bars (this agree)

| Bounce | Why |
|--------|-----|
| Mass or concentration columns on **Sample** | Identity ≠ inventory (Marc) |
| Sample write-back of mass/conc | Wrong target (Heidi §6) |
| All mass **and** conc only on Contents | Conflicts Marc: conc + total mass on 1×1 Container; Contents = per-row mass |
| Independent `Container.amount` ≠ Σ `Contents.amount` | Total is sum (or derived); not a second mass ledger (Heidi) |
| Mixture conc by summing/averaging content concs | Vessel conc on Container only |
| Divergent Contents.conc vs Container.conc on a single-content tube | Vessel SoT; Contents conc optional/RO or same-txn mirror |
| Contents or liquid inventory on multi-element parent (plate/rack) | Structure only; inventory on 1×1 children (Marc) |
| Contents with no parent Container | No vessel = no inventory |
| Dest FieldDefinitions as a writable second ledger | Must RO-project or same-txn write-through to the matching SoT |
| Storage-as-entry | Deiter L1: browse outside experiments; put-away optional one-shot |
| Free type-in parent conc on normalization | Prior Result or refuse |
| Offering container or contents conc as the assay number in normalize | Hans §10 / L2 locked: prior Result only |
| Silent unit conversion Result → inventory conc | Hans §10.2: refuse |
| Picking a Result outside the same analysis / concentration analyte | Hans §10.1 |
| Reopening Option A / storing volume as SoT | Locked 2026-08-11 |
| Treating Hans §10 as still OPEN | Locked 2026-08-24 |
| Closing pool **lineage** in this PR | Still OPEN (§11) |
| IC50 / coding this packet | Docs only; Grok Build unless Marc instructs |

---

## 13. Status and coding gate

| Item | Value |
|------|--------|
| Status | **Draft for Design Group agree** |
| Status line | **Design Group review** |
| IC50 | **Not IC50** |
| Code in this PR | **None** (docs only) |
| Application coding | **Grok Build / paused** unless Marc instructs |
| Lab Ops | **Accept with conditions** (L1 locked; L2 **LOCKED** with Hans §10) |
| CSO | **Accept** (Hans §10 locks) |

Schema implement for rows×columns / 1×1 Contents enforce remains the containers idea slice — **not** unpaused by this agree.

---

## 14. Reviews

| Review | Reviewer | Verdict | Date | Notes |
|--------|----------|---------|------|-------|
| **CEO** | Rolf | _pending_ | | |
| **Architecture** | Heidi | _pending_ | | Four write-back targets; SoT split Contents (per-row mass) vs 1×1 Container (total mass + inventory conc); dest projection/write-through |
| **Lab Ops** | Deiter | **Accept with conditions** | 2026-08-24 | **L1 locked:** optional one-shot put-away write-through; storage browse outside experiments; bounce storage-as-entry. **L2 locked with Hans:** Result publish write-throughs inventory conc onto the 1×1 Container (same txn); normalize offers only the §10 Result — never vessel/contents conc as the assay number; unit mismatch refuse. |
| **CSO** | Hans | **Accept** | 2026-08-24 | **§10 locked:** same analysis (or that analysis’s concentration analyte) only; approved/reviewed else latest by entry date; zero match → refuse. Unit mismatch refuse (no silent convert). L2/stale: Result publish write-throughs inventory conc onto 1×1 Container (same txn); aliquot plan offers only that Result — never vessel conc as assay number. |

**Implement gate for this agree:** closed until remaining Design Group (Heidi) + CEO stamp. This PR does not unpause application coding.
