# 2026-09-14 — E-10 atomic pair UAT punch (Marc / Rolf)

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**Product SHA for dogfood / unsigned UAT §7:** **`9312c54`** (`9312c54ddd3999963abd3070c76b0057b62e5d4c`). `feat/e10` tip may have moved; do not cite later docs tips as the dogfood product.  
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
