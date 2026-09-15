# Dogfood: E-10 aliquot/pool atomic pair

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**Product SHA:** **`9312c54`** (`9312c54ddd3999963abd3070c76b0057b62e5d4c`). Cite this SHA for dogfood / unsigned UAT §7. Docs tip **`50b878a`** is not the product.  
**When:** After this branch is up, **before** Tobias UAT section 7 in [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md).  
**Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14) — **not** a UAT Pass.  
**Tobias dogfood Ready=No** on **`feat/e10-aliquot-atomic-pair`** (2026-09-14 20:26 ET). Paths **1–5 Pass** on product **`9312c54`**. Clean FE **Docker** build fails **TS2345** `hasAliquotPair` nullability. Local one-line patch was used for the walk **only** — **not landed**. **Rolf Hold §7 UAT** until that fix is on the tip (or CRA / Docker FE image green). Formal **§7 stays Unsigned**. Do **not** invent Ready=Yes or §7 Pass. §§1–6 stay `008baf2`.  
**Not a UAT Result.** Not dest-follow recode. Not IC50.

## Env

Local compose on product **`9312c54`**. `experiment:manage`.

## Paths to try

1. Template Tables & forms: only **+ Aliquot/pool** (no separate plan / dest presets).
2. Click it → plan + dest entries. Add **disables while the pair exists** (one pair at a time, not forever).
3. Delete **plan** → both gone; add enables. Add again; delete **dest** → both gone; add enables.
4. Save template, start experiment → both instantiate; dest empty before execute.
5. Ad hoc experiment → **Add aliquot/pool** on Entries → same pair.

## Ready for UAT?

Tobias stamp of record (verbatim from `/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```

**Date:** 2026-09-14 20:26 ET  
**Who:** Tobias (dogfood)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**SHA:** product `9312c54`; HEAD / docs tip `50b878a`  
**Ready for UAT section 7?** **No** (verbatim READY.md). Do **not** invent Ready=Yes.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| Blocker | Clean frontend **Docker** image build from product **`9312c54`** fails **TS2345** on `hasAliquotPair` nullability. | Product owns the fix. Land on `feat/e10-aliquot-atomic-pair` (or confirm CRA / Docker FE image green) before formal §7. **Rolf Hold §7 UAT.** |
| Walk-only | Local uncommitted one-line patch used so the dogfood UI image could walk paths 1–5. | **Not landed.** Do not treat the walk patch as shipped product. |
| Pass (dogfood paths, not UAT) | Paths **1–5 Pass** on product **`9312c54`** (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). | Does **not** sign formal §7. Formal §7 stays **Unsigned**. Do **not** invent Pass from §6 / `008baf2`. |
