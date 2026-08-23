# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** (docs) — Architecture + UI Accept on atomic-pair fold. Coding stays Grok Build unless Marc/Rolf asks.  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest type on `aliquot_pool_plan` (entry default + line override); daughters on `aliquots_pools` after execute. Entry `method` is a **concrete method** that implies exactly one mint op (aliquot XOR pool). Method picker and dest type are **separate** controls. Catalog + L1 + start allow-list. Adding aliquot/pool creates the **atomic pair** (plan + dest-sample entries) together.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| **A + line override:** entry = method + default dest type; lines may clear/override within catalog; resolve line → entry default → parent | Marc 2026-08-23 |
| **One mint op per entry:** aliquot XOR pool; no mid-flight method change — **cancel experiment** (no warn/wipe); cancel does **not** un-mint already-minted daughters | Marc + Heidi + Mathilda |
| Bounce: dual mint; silent reshape after lines exist | Marc + Heidi |
| **Method ≠ dest type:** separate controls; method drives columns + mint op; dest type is independent catalog control | Marc 2026-08-23 |
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
| Header-pins-to-top | Parked — separate entries docs fold |
| Not IC50 | Marc |

## 3. Concrete methods (IN)

| Mint op | Method id (sketch) | Display |
|---------|--------------------|---------|
| aliquot | `aliquot_by_volume` | by volume |
| aliquot | `aliquot_by_target_amount` | by target amount |
| aliquot | `aliquot_by_target_concentration` | by target concentration (normalization) |
| aliquot | `aliquot_n_way_equal_split` | N-way equal split |
| pool | `pool_by_volume_per_source` | by volume per source |
| pool | `pool_equal_volume_each` | equal volume from each |
| pool | `pool_by_target_amount_per_source` | by target amount per source |
| pool | `pool_consolidate_remaining` | consolidate remaining |

**CUT (out of this packet):** fraction; contribution ratio; plate map; serial dilution.

## 4. Goals

- **Atomic pair on add:** one “Add aliquot/pool” action creates both `aliquot_pool_plan` and `aliquots_pools` together (template or ad hoc); UI never offers plan-only or dest-only add.
- Dest-sample entry present from add, **empty until after execute**.
- Entry: concrete method + optional default dest type (template or add-time).
- Lines: optional dest type clear/override if catalog allows.
- Execute resolve: line → entry default → parent; no re-prompt.
- Cancel experiment to change method; already-minted daughters stay minted.
- Normalization method enforces parent conc from prior result + dest vol or target amount.

## 5. Non-goals

Dual mint; mid-flight method warn/wipe; un-mint on cancel; method/type on `aliquots_pools`; new experiment-plan object; adding only one of the pair; Header-pins-to-top (parked); equimolar-by-size (parked until size/bp path); CUT methods above; Sample/`material_class`; matrix drop; if-blood-then; IC50.

## 6. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | `aliquot_pool_plan` + `aliquots_pools` only; no new plan object. |
| AC1b | Adding aliquot/pool (template or ad hoc) always creates **both** entries as an atomic pair; UI does not offer plan-only or dest-only; one “Add aliquot/pool” → pair. |
| AC1c | Dest-sample entry (`aliquots_pools`) stays empty until after execute. |
| AC2 | Entry config has concrete `method` (implies exactly one `mint_op`) + optional default dest type. |
| AC3 | Method picker and dest-type control are separate (Method ≠ dest type). |
| AC4 | Plan line optional `dest_sample_type` clear/override within catalog. |
| AC5 | Execute resolve line → default → parent; catalog enforce; no re-prompt (L2). |
| AC6 | Mid-flight method change refused — cancel experiment only (no warn/wipe); cancel does not un-mint daughters. |
| AC7 | Dual mint refused / not offered. |
| AC8 | `aliquots_pools` after-execute daughters only — no method/type controls. |
| AC9 | METHOD_CATALOG IN set only; CUT methods not offered. |
| AC10 | Normalization: parent conc required from prior result (not free type-in); dest vol or target amount required. |
| AC11 | Equimolar labeled/stored as target-amount method; no size/bp requirement in this packet. |
| AC12 | L1/S1 join; pool same-type; S3 config:edit; both seeds; start `accepted_sample_types`; C2 key off `sample_type`. |
| AC13 | No Sample/`material_class` column. |

## 7. Path exercised

Add aliquot/pool → both entries created (dest empty) → plan entry method=`aliquot_by_volume`, default DNA → execute → daughters on `aliquots_pools` → separate add for pool creates another atomic pair with method=`pool_equal_volume_each` for DNA→pooled DNA.

## 8. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — A + line override; concrete methods + Method≠dest type; **atomic pair on add** (Rolf CEO + Heidi + Mathilda 2026-08-23) |
| Architecture | **Accept** (Heidi re-stamp 2026-08-23 on atomic-pair) |
| UI | **Accept** (Mathilda re-stamp 2026-08-23 on atomic-pair) |
| Lab Ops | **Accept** (L1 Met; L2); Deiter cut list folded |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN** (docs). Coding stays Grok Build unless Marc/Rolf asks. Not IC50.
