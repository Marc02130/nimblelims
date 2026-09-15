# 2026-09-14 — E-10 atomic pair UAT punch (Marc / Rolf)

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**Product SHA:** **`9312c54`** (`9312c54ddd3999963abd3070c76b0057b62e5d4c`). Docs tip **`50b878a`** is not the dogfood product.  
**Tobias dogfood Ready=No** (2026-09-14 20:26 ET; `/workspace/dogfood-e10-9312c54/READY.md`). **Rolf Hold §7** until TS2345 `hasAliquotPair` is on the tip. Formal **§7 Unsigned**. Do **not** invent Ready=Yes.  
**Not IC50.** Does **not** restamp dest-container-type §§1–6 (`008baf2` Pass). Does **not** invent Tobias Pass/Fail for §7. Does **not** touch named-slot / OQ-WO-7 / C2/C3 unsigned stamps.

## Punch

Rolf 2026-09-14: fold Marc’s E-10 UAT rows. **Still unsigned until Tobias. Dogfood first** on **`9312c54`**.

**Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14). Confirm of the punch, **not** a UAT Pass.

| Row | Lock |
|-----|------|
| **7.3b** | Delete dest → both disappear (same as delete plan) |
| **7.6b** | API POST dest-only (`aliquots_pools`) → **201**; GET includes plan |
| **7.7b** | API DELETE dest → both inactive |
| **7.8** | After the pair is gone, **+ Aliquot/pool** / Add re-enables (one pair at a time — not a lifetime lock) |

**Pass criteria this packet = 7.1–7.8.** Steps **1–6** stay the `008baf2` dest-container-type stamp (Pass).

## Honesty (operator + AC)

- Delete either half removes the pair.
- POST either side creates the pair.
- DELETE either inactivates both.
- Add re-enables after the pair is gone.

Stamp of record: [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../UAT_Scripts/uat-extract-hold-dest-type.md) section 7 (Unsigned). Requirements AC1b: [`.docs/review/requirements/extract-hold-dest-type.md`](../review/requirements/extract-hold-dest-type.md). Operator: [`manuals/experiments.md`](../../manuals/experiments.md), [`manuals/HOWTO.md`](../../manuals/HOWTO.md).

## Addendum — Tobias dogfood Ready=No · 2026-09-14 20:26 ET

**Ready for UAT section 7?** **No.** Formal **§7 Unsigned**. **Rolf Hold §7** until the TS2345 `hasAliquotPair` fix is on the tip (or CRA build green). Do **not** invent Ready=Yes or Tobias §7 Pass/Fail. Product **`9312c54`**; docs tip **`50b878a`**. Product owns TS2345 (this fold is docs only). Does **not** restamp §§1–6 (`008baf2`). Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```
