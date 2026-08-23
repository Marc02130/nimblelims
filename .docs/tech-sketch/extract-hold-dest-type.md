# Tech sketch: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate HOLD** (docs) — shape moved: METHOD_CATALOG owns plan columns **and** dest-sample FieldDefinitions. Pending Architecture + UI re-stamp (Heidi + Mathilda). Coding stays Grok Build unless Marc/Rolf asks. Land S3 + L2 + seeds + `dest_sample_type` + METHOD_CATALOG (both maps) + atomic pair on add.  
**Stem:** `extract-hold-dest-type`  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Spine:** [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) §0.8 / §0.9  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem

Aliquot/pool execute creates a dest that inherits parent identity and does not join `eln_process_samples`. Dest type must be chosen on the **plan entry** before execute. Main today: no `dest_sample_type` on plan lines; execute copies `parent.sample_type` — Heidi bounce. Entry method must be **concrete** (not only aliquot|pool) so columns, dest FieldDefinitions, and mint op stay coherent. Adding aliquot/pool must create **both** plan and dest-sample entries together (atomic pair). METHOD_CATALOG owns **both** attachment maps (plan-line columns + dest-sample FieldDefinitions) and attaches them on method select — not optional later wiring.

## 2. Two entries (no plan object) — atomic pair

| Role | `predefined_entry_key` | Kind | When | Owns |
|------|------------------------|------|------|------|
| **Plan entry** | `aliquot_pool_plan` | `experiment_data` | Before / at execute | Entry config + plan lines (columns from METHOD_CATALOG) |
| **Dest sample entry** | `aliquots_pools` | `experiment_sample_data` | Created at add (empty); populated **AFTER execute only** | Lists minted daughters. Dest FieldDefinitions from METHOD_CATALOG live **on this entry** (not Sample columns). No method/type picker. |

**Atomic pair on add (Rolf CEO + Heidi + Mathilda 2026-08-23):** When adding aliquot/pool to a **template** or **ad hoc** experiment, **both** entries are created together. UI must not offer adding only one. One “Add aliquot/pool” action → pair. Dest entry stays **empty until after execute**. No new plan object.

**Flow:** Add → both entries exist (dest empty) → operator selects method → METHOD_CATALOG attaches plan columns + dest FieldDefinitions immediately → Execute reads `aliquot_pool_plan` → mints dests → L1/S1 join → `aliquots_pools` lists them (with attached FieldDefinitions). **No re-prompt.** No new experiment-plan object.

**Parked (separate entries docs fold):** Header-pins-to-top (Add Header → always pins to top of entries list; no drag below). Not this packet.

## 3. A + line override (Marc lock 2026-08-23)

### Entry config (`aliquot_pool_plan`)

| Field | Rule |
|-------|------|
| **Method** | Concrete method id from METHOD_CATALOG. Implies exactly one `mint_op` ∈ {aliquot, pool}. Drives **plan-line columns** + **dest-sample FieldDefinitions** + which mint op. Set at template or add-time. |
| **Default dest type** | Optional. **Separate** control from method (Method ≠ dest type). Template pre-fill OK or prompt at add-time. Catalog limits. Blank/clear = Same as parent. |

**One mint op per entry.** Aliquot XOR pool — never both.

**No mid-flight method change.** Once the entry exists with lines, changing method is **not** warn/wipe — **cancel the experiment**. Cancel does **not** un-mint already-minted daughters. Ops do not rewind.

### Plan lines

| Field | Rule |
|-------|------|
| `dest_sample_type` | Optional **line override**. May clear (= Same as parent) or set another catalog-allowed dest for this source × entry `mint_op`. Independent of method. |
| Method columns | Shape from `METHOD_CATALOG[method].plan_columns` — required/optional per method. Attached on method select. |

**Resolve at execute:**

```text
mint_op = METHOD_CATALOG[entry.method].mint_op   # exactly one
type_id =
  line.dest_sample_type if set
  else entry.default_dest_sample_type if set
  else source.sample_type   # Same as parent
if type_id != source.sample_type and no catalog_row(source, mint_op, type_id): refuse
```

### Bounce bars (Marc + Heidi + Mathilda; atomic pair Rolf CEO + Heidi + Mathilda; METHOD_CATALOG dual-map Heidi + Mathilda 2026-08-23)

- One entry minting **both** aliquot and pool (dual mint).
- **Silent reshape** of columns/mint/FieldDefinitions after lines already exist (method change mid-flight).
- Warn/wipe instead of cancel.
- Un-minting daughters on cancel.
- Collapsing method and dest type into one control.
- Method/type picker on `aliquots_pools`.
- New experiment-plan object.
- **Adding only one of the pair** (plan-only or dest-only); UI offering separate add for each.
- Offering CUT methods (fraction, contribution ratio, plate map, serial dilution).
- Free type-in parent concentration on normalization.
- Equimolar-by-size without a size/bp sample/result path (Hans gate).
- **New Sample columns** for dest amount/volume/concentration — dest fields are **entry FieldDefinitions** on `aliquots_pools` (`experiment_sample_data`), not Sample schema.
- **Optional / later wiring** of plan columns or dest FieldDefinitions after method select — catalog attaches **immediately** and automatically.
- Sample/`material_class` column; matrix drop; receive/mid-entry type gate; if-blood-then; transitions on `template_definition`.

## 4. METHOD_CATALOG (Deiter cut list) — owns both maps

Entry `method` is a concrete id. Each catalog row owns:

1. `mint_op` ∈ {aliquot, pool} — exactly one
2. **Plan-line columns** on `aliquot_pool_plan` (required / optional)
3. **Dest-sample FieldDefinitions** on the paired `aliquots_pools` entry (`experiment_sample_data`) — attached when method is selected

**UX (Heidi + Mathilda 2026-08-23):** Method select → METHOD_CATALOG attaches plan columns **and** dest FieldDefinitions **immediately**. Not optional later wiring. Method ≠ dest type (dest type stays a separate control).

**Dest FieldDefinitions live on the dest entry**, not on Sample. Sketch-level required fields below — not product schema invention beyond the FieldDefinition attachment pattern.

### 4.0 Catalog shape (sketch)

```python
METHOD_CATALOG = {
    "<method_id>": {
        "mint_op": "aliquot" | "pool",
        "plan_columns": [  # on aliquot_pool_plan lines
            {"key": "...", "required": True|False, "role": "..."},
            ...
        ],
        "dest_field_definitions": [  # on aliquots_pools entry (experiment_sample_data)
            {"key": "...", "required": True|False, "role": "..."},
            ...
        ],
    },
    ...
}
```

### Aliquot (IN)

| method id | Display | `mint_op` | Plan-line columns (sketch) | Dest FieldDefinitions on `aliquots_pools` (sketch) |
|-----------|---------|-----------|----------------------------|-----------------------------------------------------|
| `aliquot_by_volume` | by volume | aliquot | **req:** source_volume, dest_volume | **req:** volume; **opt:** amount, concentration |
| `aliquot_by_target_amount` | by target amount | aliquot | **req:** target_amount; **opt:** volume or concentration as needed | **req:** amount; **opt:** volume, concentration |
| `aliquot_by_target_concentration` | by target concentration (normalization) | aliquot | see §4.1 | **req:** concentration; **opt:** volume, amount |
| `aliquot_n_way_equal_split` | N-way equal split | aliquot | **req:** N, equal_split fields | **req:** volume (per equal part); **opt:** amount, concentration |

### Pool (IN)

| method id | Display | `mint_op` | Plan-line columns (sketch) | Dest FieldDefinitions on `aliquots_pools` (sketch) |
|-----------|---------|-----------|----------------------------|-----------------------------------------------------|
| `pool_by_volume_per_source` | by volume per source | pool | **req:** per_source_volume | **req:** volume; **opt:** amount, concentration |
| `pool_equal_volume_each` | equal volume from each | pool | **req:** shared_volume | **req:** volume; **opt:** amount, concentration |
| `pool_by_target_amount_per_source` | by target amount per source | pool | **req:** per_source_target_amount | **req:** amount; **opt:** volume, concentration |
| `pool_consolidate_remaining` | consolidate remaining | pool | **req:** remaining / consolidate fields | **req:** volume; **opt:** amount, concentration |

### CUT (out of this packet)

| Out | Notes |
|-----|-------|
| fraction | Parked |
| contribution ratio | Parked |
| plate map | Parked |
| serial dilution | Parked |

### 4.1 Normalization (`aliquot_by_target_concentration`)

| Rule | Detail |
|------|--------|
| Parent concentration | **Required** |
| Source of conc | Prefer **prior result on that sample** — **not** free type-in |
| Dest vol **or** target amount | At least one required on plan line |
| Dest FieldDefinitions | concentration required on dest entry; volume/amount optional as filled by execute |

### 4.2 Equimolar (Hans lock)

**Sketch stance (this packet):** rename equimolar → **`aliquot_by_target_amount`** (“by target amount”). No size/bp required on sample/result path today, so equimolar-by-size is **not** a separate IN method.

**Hans gate:** if size/bp later exists on the sample/result path, Leadership may re-open a distinct equimolar-by-size method; until then, target amount covers the need.

## 5. Goals (remainder)

- **Atomic pair:** one “Add aliquot/pool” → both entries; dest empty until execute.
- **METHOD_CATALOG dual map:** method select attaches plan columns + dest FieldDefinitions immediately (Heidi + Mathilda).
- Catalog many-to-many; multi-hop = process steps.
- Pool: one shared source `sample_type` or refuse; then catalog lookup for entry `mint_op`.
- L1/S1 join; L2 no execute re-prompt; S3 `config:edit` on catalog; C2 key off `sample_type`.
- **Seed:** Blood × aliquot → DNA; DNA × pool → pooled DNA.

## 6. Data model

```
samples.sample_type / parent_sample_id / matrix   ← existing (matrix unchanged)
eln_process_samples                               ← L1/S1 join
template_definition.accepted_sample_types         ← start entry allow-list
sample_type_transitions                           ← NEW catalog (many-to-many)
aliquot_pool_plan entry config:
  method                                          ← concrete METHOD_CATALOG id
  default_dest_sample_type                        ← optional (separate from method)
AliquotPlanLine.dest_sample_type                  ← optional line override (MUST land)
AliquotPlanLine.<plan_columns>                    ← from METHOD_CATALOG[method].plan_columns
aliquots_pools entry FieldDefinitions             ← from METHOD_CATALOG[method].dest_field_definitions
                                                  ← on experiment_sample_data entry — NOT Sample columns
```

```python
# mint_op + both maps implied by method — never Literal["aliquot","pool"] alone on the entry
METHOD_CATALOG = {
    "aliquot_by_volume": {
        "mint_op": "aliquot",
        "plan_columns": [{"key": "source_volume", "required": True}, {"key": "dest_volume", "required": True}],
        "dest_field_definitions": [{"key": "volume", "required": True}, {"key": "amount", "required": False}, {"key": "concentration", "required": False}],
    },
    "aliquot_by_target_amount": {
        "mint_op": "aliquot",
        "plan_columns": [{"key": "target_amount", "required": True}],
        "dest_field_definitions": [{"key": "amount", "required": True}, {"key": "volume", "required": False}, {"key": "concentration", "required": False}],
    },
    "aliquot_by_target_concentration": {
        "mint_op": "aliquot",
        "plan_columns": [{"key": "target_concentration", "required": True}, {"key": "dest_volume_or_target_amount", "required": True}],
        "dest_field_definitions": [{"key": "concentration", "required": True}, {"key": "volume", "required": False}, {"key": "amount", "required": False}],
    },
    "aliquot_n_way_equal_split": {
        "mint_op": "aliquot",
        "plan_columns": [{"key": "N", "required": True}, {"key": "equal_split", "required": True}],
        "dest_field_definitions": [{"key": "volume", "required": True}, {"key": "amount", "required": False}, {"key": "concentration", "required": False}],
    },
    "pool_by_volume_per_source": {
        "mint_op": "pool",
        "plan_columns": [{"key": "per_source_volume", "required": True}],
        "dest_field_definitions": [{"key": "volume", "required": True}, {"key": "amount", "required": False}, {"key": "concentration", "required": False}],
    },
    "pool_equal_volume_each": {
        "mint_op": "pool",
        "plan_columns": [{"key": "shared_volume", "required": True}],
        "dest_field_definitions": [{"key": "volume", "required": True}, {"key": "amount", "required": False}, {"key": "concentration", "required": False}],
    },
    "pool_by_target_amount_per_source": {
        "mint_op": "pool",
        "plan_columns": [{"key": "per_source_target_amount", "required": True}],
        "dest_field_definitions": [{"key": "amount", "required": True}, {"key": "volume", "required": False}, {"key": "concentration", "required": False}],
    },
    "pool_consolidate_remaining": {
        "mint_op": "pool",
        "plan_columns": [{"key": "consolidate_remaining", "required": True}],
        "dest_field_definitions": [{"key": "volume", "required": True}, {"key": "amount", "required": False}, {"key": "concentration", "required": False}],
    },
    # CUT: fraction, contribution_ratio, plate_map, serial_dilution — not in catalog
}

class AliquotPoolPlanConfig(BaseModel):
    method: str  # concrete method id; implies mint_op + both maps
    default_dest_sample_type: UUID | None = None  # blank = Same as parent
# mint_op = METHOD_CATALOG[method].mint_op  # exactly one
# plan columns + dest FieldDefinitions attached on method select — not later wiring

class AliquotPlanLine(BaseModel):
    source_sample_id: UUID
    # … amount / dest container fields (shape from METHOD_CATALOG[entry.method].plan_columns) …
    dest_sample_type: UUID | None = None  # override or clear → Same as parent
```

Transition catalog rows still key off `mint_op` (aliquot|pool), not concrete method id.

## 7. Execute

```text
mint_op = METHOD_CATALOG[entry.method].mint_op  # never dual mint
validate method-specific required plan_columns (incl. normalization rules)
Read aliquot_pool_plan lines
for each line:
  if mint_op is pool and sources do not share one sample_type: refuse
  type_id = line.dest_sample_type or entry.default_dest_sample_type or source.sample_type
  if type_id != source.sample_type and no catalog_row(source, mint_op, type_id): refuse
  mint dest; L1/S1 join if under process
Populate aliquots_pools  # dest entry already exists (atomic pair); was empty until here
# dest FieldDefinitions already attached at method select; values filled after mint
# never prompt for dest type at execute
# never change entry.method mid-flight — cancel experiment instead
# cancel does not un-mint already-minted daughters
```

## 8. Entry setup UX

| Surface | Rule |
|---------|------|
| Entry add / template | **One** “Add aliquot/pool” action creates **both** entries (atomic pair). No plan-only or dest-only add. Concrete method picker **and** default dest type (two controls); catalog limits dest |
| Method select | METHOD_CATALOG attaches **plan-line columns** on `aliquot_pool_plan` **and** **dest FieldDefinitions** on `aliquots_pools` **immediately** (Heidi + Mathilda). Not optional later wiring |
| Dest entry at add | Present, **empty** until after execute; FieldDefinitions attached on method select |
| Plan lines | May clear/override dest type within catalog; columns follow method |
| After lines exist | Method locked — change requires cancel experiment (no warn/wipe reshape; no un-mint) |
| `aliquots_pools` | After-execute daughters only; no method/type picker; dest amount/volume/concentration are **entry FieldDefinitions**, not Sample columns |

## 9. Tests

| Case | Expect |
|------|--------|
| Add aliquot/pool (template or ad hoc) | Both `aliquot_pool_plan` and `aliquots_pools` created together |
| UI offer plan-only or dest-only add | Not offered / bounce |
| Dest entry before execute | Empty |
| Method select | Plan columns + dest FieldDefinitions attached immediately |
| Optional/later wiring of fields after method select | Bounce — catalog owns both maps |
| New Sample columns for dest amount/vol/conc | Bounce — FieldDefinitions on dest entry only |
| Entry method `aliquot_by_volume`; default DNA; line blank | Dest DNA |
| Entry default DNA; line clears | Dest = parent (Same as parent) |
| Line overrides to catalog-allowed type | That type |
| Line overrides off-catalog | Refuse |
| Dual mint (aliquot+pool one entry) | Bounce |
| Mid-flight method change | Refuse / cancel path — no silent reshape |
| Cancel after partial mint | Daughters remain minted |
| Method picker vs dest type | Independent controls |
| CUT method selected | Not offered / refuse |
| Normalization without prior conc result | Refuse (no free type-in) |
| Normalization missing dest vol and target amount | Refuse |
| Equimolar / target amount | Stored as `aliquot_by_target_amount`; no size/bp required |
| Seeds Blood×aliquot→DNA; DNA×pool→pooled DNA | OK |
| Catalog mutate without config:edit | 403 |

## 10. Reviews

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — A + line override; concrete methods + Method≠dest type; **atomic pair on add** (Rolf CEO + Heidi + Mathilda 2026-08-23); METHOD_CATALOG dual-map fold pending Architecture/UI re-stamp |
| Architecture | **Pending re-stamp** (Heidi) — prior Accept on atomic-pair stands until re-stamp; shape moved: METHOD_CATALOG owns plan columns **and** dest FieldDefinitions; attach on method select; bounce new Sample columns + later wiring |
| UI | **Pending re-stamp** (Mathilda) — prior Accept on atomic-pair stands until re-stamp; same dual-map UX; Header-pins-to-top parked for separate entries fold |
| Lab Ops | **Accept** (L1 Met; L2); Deiter cut list folded |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **HOLD** (docs) pending Architecture + UI re-stamp. Coding stays Grok Build unless Marc/Rolf asks. Not IC50.

## 11. Relationship to Hold

Lifts Extract-then-Qubit Hold once implemented. Not SOP+AI → live process (PR 51).
