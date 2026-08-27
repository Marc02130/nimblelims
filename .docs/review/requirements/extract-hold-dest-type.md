# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** (docs) — Architecture + UI Accept on METHOD_CATALOG dual-map. Coding stays Grok Build unless Marc/Rolf asks.  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/review/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/review/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/review/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold source:** [`.docs/review/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest type on `aliquot_pool_plan` (entry default + line override); daughters on `aliquots_pools` after execute. Entry `method` is a **concrete method** that implies exactly one mint op (aliquot XOR pool). Method picker and dest type are **separate** controls. **METHOD_CATALOG owns both maps:** (1) plan-line columns on `aliquot_pool_plan`, (2) dest-sample FieldDefinitions on `aliquots_pools` — attached **automatically** on method select (not optional later wiring). Dest fields are entry FieldDefinitions (`experiment_sample_data`), **not** Sample columns. Catalog + L1 + start allow-list. Adding aliquot/pool creates the **atomic pair** (plan + dest-sample entries) together.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| **A + line override:** entry = method + default dest type; lines may clear/override within catalog; resolve line → entry default → parent | Marc 2026-08-23 |
| **One mint op per entry:** aliquot XOR pool; no mid-flight method change — **cancel experiment** (no warn/wipe); cancel does **not** un-mint already-minted daughters | Marc + Heidi + Mathilda |
| Bounce: dual mint; silent reshape after lines exist | Marc + Heidi |
| **Method ≠ dest type:** separate controls; method drives columns + mint op + dest FieldDefinitions; dest type is independent catalog control | Marc 2026-08-23 |
| **METHOD_CATALOG owns both maps:** (1) plan-line columns on `aliquot_pool_plan`; (2) dest-sample FieldDefinitions on paired `aliquots_pools` entry; method select attaches **both immediately** — not optional later wiring | Heidi + Mathilda 2026-08-23 |
| **Dest fields = entry FieldDefinitions:** amount / volume / concentration (as appropriate per method) live on `aliquots_pools` (`experiment_sample_data`), **not** new Sample columns | Heidi + Mathilda 2026-08-23 |
| Bounce: new Sample columns; optional/later wiring of plan columns or dest FieldDefinitions; mid-flight method change (still cancel) | Heidi + Mathilda 2026-08-23 |
| **Concrete methods (Deiter cut list):** entry `method` is concrete id → exactly one `mint_op`; CUT fraction / contribution ratio / plate map / serial dilution | Deiter + Marc 2026-08-23 |
| **Normalization:** parent concentration required; prefer prior result on that sample (not free type-in); dest vol **or** target amount required | Marc 2026-08-23 |
| **Equimolar (Hans):** rename equimolar → **by target amount** for this packet (no size/bp path yet); Hans gate if size/bp lands later | Hans + Marc 2026-08-23 |
| **Atomic pair (add):** adding aliquot/pool to template or ad hoc creates **both** entries together — plan (`aliquot_pool_plan` / `experiment_data`) **and** dest-sample (`aliquots_pools` / `experiment_sample_data`); UI must not offer adding only one; one “Add aliquot/pool” action → pair; dest entry stays empty until after execute; no new plan object | Rolf CEO + Heidi + Mathilda 2026-08-23 |
| Two keys: `aliquot_pool_plan` / `aliquots_pools`; no new plan object | Prior map |
| `dest_sample_type` must land on plan line/config (Heidi bounce vs main copy-parent) | Heidi |
| Seeds Blood×aliquot→DNA, DNA×pool→pooled DNA; S3 config:edit; L1/S1; L2; start allow-list; catalog many-to-many; pool same-type | Prior |
| Bounce Sample/`material_class`, matrix drop, receive/mid-entry gates, if-blood-then, transitions on `template_definition` | Prior |
| Architecture Accept on atomic-pair fold | Heidi 2026-08-23 |
| UI Accept on atomic-pair fold | Mathilda 2026-08-23 |
| Architecture Accept on METHOD_CATALOG dual-map | Heidi 2026-08-23 |
| UI Accept on METHOD_CATALOG dual-map | Mathilda 2026-08-23 |
| Header-pins-to-top | Parked — separate entries docs fold |
| Not IC50 | Marc |

## 3. Concrete methods (IN) — sketch columns + dest FieldDefinitions

Each method id has `mint_op`, plan-line columns (required/optional), **and** dest-sample FieldDefinitions attached on the paired `aliquots_pools` entry when method is selected. Tables below are **sketch-level** — aligned with Deiter IN methods; not product schema invention beyond the FieldDefinition attachment pattern. Dest FieldDefinitions live on the dest entry, not Sample.

| Mint op | Method id (sketch) | Display | Plan-line columns (sketch) | Dest FieldDefinitions on `aliquots_pools` (sketch) |
|---------|--------------------|---------|----------------------------|-----------------------------------------------------|
| aliquot | `aliquot_by_volume` | by volume | **req:** source_volume, dest_volume | **req:** volume; **opt:** amount, concentration |
| aliquot | `aliquot_by_target_amount` | by target amount | **req:** target_amount; **opt:** vol/conc as needed | **req:** amount; **opt:** volume, concentration |
| aliquot | `aliquot_by_target_concentration` | by target concentration (normalization) | **req:** target_concentration; dest vol **or** target amount | **req:** concentration; **opt:** volume, amount |
| aliquot | `aliquot_n_way_equal_split` | N-way equal split | **req:** N, equal_split fields | **req:** volume; **opt:** amount, concentration |
| pool | `pool_by_volume_per_source` | by volume per source | **req:** per_source_volume | **req:** volume; **opt:** amount, concentration |
| pool | `pool_equal_volume_each` | equal volume from each | **req:** shared_volume | **req:** volume; **opt:** amount, concentration |
| pool | `pool_by_target_amount_per_source` | by target amount per source | **req:** per_source_target_amount | **req:** amount; **opt:** volume, concentration |
| pool | `pool_consolidate_remaining` | consolidate remaining | **req:** remaining / consolidate fields | **req:** volume; **opt:** amount, concentration |

**CUT (out of this packet):** fraction; contribution ratio; plate map; serial dilution.

## 4. Goals

- **Atomic pair on add:** one “Add aliquot/pool” action creates both `aliquot_pool_plan` and `aliquots_pools` together (template or ad hoc); UI never offers plan-only or dest-only add.
- Dest-sample entry present from add, **empty until after execute**.
- **METHOD_CATALOG dual map:** method select attaches plan-line columns + dest FieldDefinitions **immediately** (Heidi + Mathilda); not optional later wiring.
- Dest amount/volume/concentration (per method) are **entry FieldDefinitions** on `aliquots_pools` — never new Sample columns.
- Entry: concrete method + optional default dest type (template or add-time).
- Lines: optional dest type clear/override if catalog allows.
- Execute resolve: line → entry default → parent; no re-prompt.
- Cancel experiment to change method; already-minted daughters stay minted.
- Normalization method enforces parent conc from prior result + dest vol or target amount.

## 5. Non-goals

Dual mint; mid-flight method warn/wipe; un-mint on cancel; method/type on `aliquots_pools`; new experiment-plan object; adding only one of the pair; **new Sample columns** for dest fields; **optional/later wiring** of catalog-owned columns/FieldDefinitions; Header-pins-to-top (parked); equimolar-by-size (parked until size/bp path); CUT methods above; Sample/`material_class`; matrix drop; if-blood-then; IC50.

## 6. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | `aliquot_pool_plan` + `aliquots_pools` only; no new plan object. |
| AC1b | Adding aliquot/pool (template or ad hoc) always creates **both** entries as an atomic pair; UI does not offer plan-only or dest-only; one “Add aliquot/pool” → pair. |
| AC1c | Dest-sample entry (`aliquots_pools`) stays empty until after execute. |
| AC2 | Entry config has concrete `method` (implies exactly one `mint_op`) + optional default dest type. |
| AC3 | Method picker and dest-type control are separate (Method ≠ dest type). |
| AC3b | METHOD_CATALOG owns **both** maps: plan-line columns on `aliquot_pool_plan` **and** dest-sample FieldDefinitions on `aliquots_pools`. |
| AC3c | Method select attaches plan columns + dest FieldDefinitions **immediately** — not optional later wiring. |
| AC3d | Dest FieldDefinitions (amount / volume / concentration as appropriate) live on the dest entry (`experiment_sample_data`); **no** new Sample columns. |
| AC4 | Plan line optional `dest_sample_type` clear/override within catalog. |
| AC5 | Execute resolve line → default → parent; catalog enforce; no re-prompt (L2). |
| AC6 | Mid-flight method change refused — cancel experiment only (no warn/wipe); cancel does not un-mint daughters. |
| AC7 | Dual mint refused / not offered. |
| AC8 | `aliquots_pools` after-execute daughters only — no method/type controls. |
| AC9 | METHOD_CATALOG IN set only; CUT methods not offered. |
| AC10 | Normalization: parent conc required from prior result (not free type-in); dest vol or target amount required. |
| AC11 | Equimolar labeled/stored as target-amount method; no size/bp requirement in this packet. |
| AC12 | L1/S1 join; pool same-type; S3 config:edit; both seeds; start `accepted_sample_types`; C2 key off `sample_type`. |
| AC13 | No Sample/`material_class` column; no new Sample columns for dest amount/vol/conc. |

## 7. Path exercised

Add aliquot/pool → both entries created (dest empty) → plan entry method=`aliquot_by_volume` (catalog attaches volume plan columns + dest volume FieldDefinition) , default DNA → execute → daughters on `aliquots_pools` → separate add for pool creates another atomic pair with method=`pool_equal_volume_each` for DNA→pooled DNA.

## 8. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — A + line override; concrete methods + Method≠dest type; **atomic pair on add**; METHOD_CATALOG dual-map |
| Architecture | **Accept** (Heidi re-stamp 2026-08-23 on dual-map) |
| UI | **Accept** (Mathilda re-stamp 2026-08-23 on dual-map) |
| Lab Ops | **Accept** (L1 Met; L2); Deiter cut list folded |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN** (docs). Coding stays Grok Build unless Marc/Rolf asks. Not IC50.
