# Dogfood: E-10 aliquot/pool atomic pair

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** product on `main` (merged PR **129**)  
**Product SHA (dogfood / uniqueness / overall §7):** **`dc7ee92`** (`dc7ee92c086558420c16edffe301773975f17234`) — API uniqueness / `wrapper_at_capacity`. Merge tip **`e56a89f`** (`e56a89fe01656b416cfcae885b6ade605e8cf38e`).  
**When:** Dogfood **Ready=Yes** on `dc7ee92` then Tobias overall **§7 Pass** (2026-09-14 22:28 ET) in [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md).  
**Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14) — **not** the double-Add Met. **Lab Ops: Deiter Met** on double-Add 2026-09-14.  
**Live state:** formal **§7 Result: Pass** (Tobias QA, 2026-09-14 22:28 ET, `dc7ee92`) — **7.1–7.8 Pass** on `e5a8fdd` (not rescored) **plus** Deiter **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`). Prior overall **Fail** on `e5a8fdd` is **history**. **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). Living uniqueness: **409** `wrapper_at_capacity` (not a blocker).  
**Tobias dogfood Ready=Yes** on **`dc7ee92`** (evidence `/workspace/dogfood-e10-dc7ee92/READY.md`): clean FE **Docker**/CRA, paths **1–5 Pass**. Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay history. §§1–6 stay `008baf2` (not restamped).  
**Not dest-follow recode.** Not IC50.

## Env

Local compose on product **`dc7ee92`** (merged to `main` as PR **129** / `e56a89f`). `experiment:manage`.

## Paths to try

1. Template Tables & forms: only **+ Aliquot/pool** (no separate plan / dest presets).
2. Click it → plan + dest entries. Add **disables while the wrapper is at capacity** (one `aliquot_pool` instance, not forever).
3. Delete **plan** → both gone; add enables. Add again; delete **dest** → both gone; add enables.
4. Save template, start experiment → both instantiate; dest empty before execute.
5. Ad hoc experiment → **Add aliquot/pool** on Entries → same pair.
6. With the pair present, API POST another `aliquot_pool_plan` → **409** `wrapper_at_capacity`. After delete, POST succeeds again.

## Ready for UAT?

Tobias stamp of record (cite `/workspace/dogfood-e10-dc7ee92/READY.md`; artifacts `/workspace/dogfood-e10-dc7ee92/`):

**Date:** 2026-09-14 ~22:27 ET  
**Who:** Tobias (dogfood)  
**SHA:** product / tip `dc7ee92` (`dc7ee92c086558420c16edffe301773975f17234`)  
**Clean FE build:** Yes (Docker/CRA). Paths **1–5 Pass**.  
**Ready for UAT section 7?** **Yes**. Formal overall **§7 Result: Pass** (2026-09-14 22:28 ET) is the living UAT stamp. Ready=Yes is dogfood, not a substitute for that Pass.

### History — Ready=Yes on `e5a8fdd` (superseded as living dogfood)

Prior restamp (2026-09-14 21:23 ET) stays history. Verbatim from `/workspace/dogfood-e10-e5a8fdd/READY.md`; artifacts `/workspace/dogfood-e10-e5a8fdd/`:

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 21:23 ET
**Who:** Tobias (dogfood restamp)
**SHA:** `e5a8fdd50538e23e67c1425dadb3e505171b987f` (e5a8fdd) tip of `feat/e10-aliquot-atomic-pair` (includes hasAliquotPair nullability fix).

**Clean FE build:** Yes — `docker build --no-cache` frontend from this SHA; CRA Compiled successfully; no local patch; working tree clean.

**Ready for UAT section 7?** Yes — clean FE Docker/CRA build green on tip `e5a8fdd`, and dogfood paths 1–5 Pass (single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). Not formal §7. Do **not** invent Pass from §6 / 008baf2. Not IC50.

Artifacts: `/workspace/dogfood-e10-e5a8fdd/`
```

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

That Ready=No (TS2345 `hasAliquotPair` on **`9312c54`**) is **superseded** by Ready=Yes on **`e5a8fdd`**, then living Ready=Yes on **`dc7ee92`**.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| History (resolved) | Clean frontend **Docker** image build from product **`9312c54`** failed **TS2345** on `hasAliquotPair` nullability. Walk used a local uncommitted one-line patch. | Landed on **`e5a8fdd`**. Ready=No on `9312c54` stays history. |
| Pass (dogfood paths) | Paths **1–5 Pass** on **`dc7ee92`** (and earlier on `e5a8fdd`). Clean FE Docker/CRA **Yes**. | Living Ready=Yes on `dc7ee92`. Does **not** replace formal overall §7 Pass. Do **not** invent Pass from §6 / `008baf2`. |
| History (closed) | Formal §7 **Fail** (Tobias QA, 2026-09-14 21:31 ET, `e5a8fdd`). Packet 7.1–7.8 Pass. Deiter EXTRA double-Add **Fail** on that SHA: concurrent 2+2; sequential 2 plans + 1 dest. **Then-blocking:** API second plan POST while pair/half exists. | Closed by uniqueness **409** `wrapper_at_capacity` + double-Add **Pass** on `dc7ee92` and overall **Pass** 22:28 ET. Evidence of the Fail stays `/workspace/uat-e10-section7-e5a8fdd/`. |
| Pass (living) | Deiter EXTRA double-Add **Pass** on `dc7ee92`: sequential second plan POST **409**; second dest POST **409**; GET **1+1**; concurrent **201 + 409** → **1 plan + 1 dest**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. | Overall §7 **Pass**. **Hold merge lifted**. **E-10 Met**. |

## Closeout — Hold merge lifted · E-10 Met

**Rolf Confirm: Hold merge lifted.** Product is on `main` @ `e56a89f` (PR **129**). **E-10 Met**. Formal **§7 Result: Pass** (Tobias QA, 2026-09-14 22:28 ET, `dc7ee92`). Living uniqueness: **409** `wrapper_at_capacity` — not a current blocker. Do **not** restamp §§1–6 off `008baf2`. Not IC50.

Evidence (cite only):
- `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`
- `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`
- `/workspace/dogfood-e10-dc7ee92/READY.md`
