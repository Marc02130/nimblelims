# Dogfood: E-10 aliquot/pool atomic pair

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**Product SHA:** **`e5a8fdd`** (`e5a8fdd50538e23e67c1425dadb3e505171b987f`) tip of `feat/e10-aliquot-atomic-pair` (includes `hasAliquotPair` nullability fix). Cite this SHA for current dogfood / unsigned UAT §7.  
**When:** After this branch is up, **before** Tobias UAT section 7 in [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md). Tobias is starting formal §7.  
**Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14) — **not** a UAT Pass.  
**Tobias dogfood Ready=Yes** on **`feat/e10-aliquot-atomic-pair`** (2026-09-14 21:23 ET restamp). Clean FE **Docker**/CRA build green on **`e5a8fdd`**. Paths **1–5 Pass**. **Rolf Hold §7 UAT lifts** (Tobias starting formal §7 unless Rolf Holds again). Formal **§7 stays Unsigned** until Tobias stamps Pass/Fail. Ready=Yes is **not** §7 Pass. Do **not** invent §7 Pass. Prior Ready=No on **`9312c54`** (TS2345) stays history — superseded by this restamp. §§1–6 stay `008baf2`.  
**Not a UAT Result.** Not dest-follow recode. Not IC50.

## Env

Local compose on product **`e5a8fdd`**. `experiment:manage`.

## Paths to try

1. Template Tables & forms: only **+ Aliquot/pool** (no separate plan / dest presets).
2. Click it → plan + dest entries. Add **disables while the pair exists** (one pair at a time, not forever).
3. Delete **plan** → both gone; add enables. Add again; delete **dest** → both gone; add enables.
4. Save template, start experiment → both instantiate; dest empty before execute.
5. Ad hoc experiment → **Add aliquot/pool** on Entries → same pair.

## Ready for UAT?

Tobias stamp of record (verbatim from `/workspace/dogfood-e10-e5a8fdd/READY.md`; artifacts `/workspace/dogfood-e10-e5a8fdd/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 21:23 ET
**Who:** Tobias (dogfood restamp)
**SHA:** `e5a8fdd50538e23e67c1425dadb3e505171b987f` (e5a8fdd) tip of `feat/e10-aliquot-atomic-pair` (includes hasAliquotPair nullability fix).

**Clean FE build:** Yes — `docker build --no-cache` frontend from this SHA; CRA Compiled successfully; no local patch; working tree clean.

**Ready for UAT section 7?** Yes — clean FE Docker/CRA build green on tip `e5a8fdd`, and dogfood paths 1–5 Pass (single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). Not formal §7. Do **not** invent Pass from §6 / 008baf2. Not IC50.

Artifacts: `/workspace/dogfood-e10-e5a8fdd/`
```

**Date:** 2026-09-14 21:23 ET  
**Who:** Tobias (dogfood restamp)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**SHA:** product / tip `e5a8fdd`  
**Ready for UAT section 7?** **Yes** (verbatim READY.md). Formal **§7 Unsigned**. Ready=Yes is **not** §7 Pass. Do **not** invent §7 Pass.

### History — Ready=No on `9312c54` (superseded)

Prior stamp (2026-09-14 20:26 ET) stays history. Verbatim from `/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`:

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```

That Ready=No (TS2345 `hasAliquotPair` on **`9312c54`**; walk patch not landed; **Rolf Hold §7 UAT**) is **superseded** by Ready=Yes on **`e5a8fdd`**.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| History (resolved) | Clean frontend **Docker** image build from product **`9312c54`** failed **TS2345** on `hasAliquotPair` nullability. Walk used a local uncommitted one-line patch. | Landed on tip **`e5a8fdd`**. Ready=No on `9312c54` stays history. |
| Pass (dogfood paths, not UAT) | Paths **1–5 Pass** on product **`e5a8fdd`** (single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). Clean FE Docker/CRA **Yes**. No local patch. | **Rolf Hold lifts.** Tobias starting formal §7 unless Rolf Holds again. Does **not** sign formal §7. Formal §7 stays **Unsigned**. Do **not** invent Pass from §6 / `008baf2`. |
