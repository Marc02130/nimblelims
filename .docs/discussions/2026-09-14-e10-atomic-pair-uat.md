# 2026-09-14 — E-10 atomic pair UAT punch (Marc / Rolf)

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** `feat/e10-aliquot-atomic-pair`  
**Product SHA:** **`e5a8fdd`** (`e5a8fdd50538e23e67c1425dadb3e505171b987f`) tip of `feat/e10-aliquot-atomic-pair` (includes `hasAliquotPair` nullability fix).  
**Tobias dogfood Ready=Yes** on **`feat/e10-aliquot-atomic-pair`** (2026-09-14 21:23 ET; `/workspace/dogfood-e10-e5a8fdd/READY.md`). Paths **1–5 Pass**. Clean FE **Docker**/CRA build green; no local patch. **Rolf Confirm: No Hold.** Ready=Yes stands on **`e5a8fdd`** (dogfood). Formal **§7 Result: Fail** (Tobias QA, 2026-09-14 21:31 ET). Packet 7.1–7.8 Pass; overall Fail = Deiter double-Add (API uniqueness). Do **not** invent overall §7 Pass. Prior Ready=No on **`9312c54`** (TS2345) stays history — superseded by Ready=Yes.  
**Not IC50.** Does **not** restamp dest-container-type §§1–6 (`008baf2` Pass). Does **not** invent overall §7 Pass. Does **not** touch named-slot / OQ-WO-7 / C2/C3 unsigned stamps.

## Punch

Rolf 2026-09-14: fold Marc’s E-10 UAT rows. **Still unsigned until Tobias.** Dogfood first was on **`9312c54`**; current product for §7 is **`e5a8fdd`**.

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

Stamp of record: [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../UAT_Scripts/uat-extract-hold-dest-type.md) section 7 (**Fail** overall; 7.1–7.8 Pass). Requirements AC1b: [`.docs/review/requirements/extract-hold-dest-type.md`](../review/requirements/extract-hold-dest-type.md). Operator: [`manuals/experiments.md`](../../manuals/experiments.md), [`manuals/HOWTO.md`](../../manuals/HOWTO.md).

## Addendum — Tobias dogfood Ready=No · 2026-09-14 20:26 ET

**Ready for UAT section 7?** **No** on **`feat/e10-aliquot-atomic-pair`**. Paths **1–5 Pass** on product **`9312c54`**. Clean FE **Docker** build fails **TS2345** `hasAliquotPair` nullability. Local one-line patch was walk-only — **not landed**. Formal **§7 Unsigned**. **Rolf Hold §7 UAT**. Do **not** invent Ready=Yes or Tobias §7 Pass/Fail. Docs tip **`50b878a`**. Product owns TS2345 (this fold is docs only). Does **not** restamp §§1–6 (`008baf2`). Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

**History.** Superseded by Ready=Yes on **`e5a8fdd`** (addendum below). Do not treat this Ready=No as current.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```

## Addendum — Tobias dogfood Ready=Yes · 2026-09-14 21:23 ET

**Ready for UAT section 7?** **Yes** on **`feat/e10-aliquot-atomic-pair`**. Product **`e5a8fdd`**. Paths **1–5 Pass**. Clean FE **Docker**/CRA build green; no local patch; working tree clean. **Rolf Confirm: No Hold.** Ready=Yes stands on **`e5a8fdd`**. Tobias proceeds with formal §7. Formal **§7 Unsigned** until Tobias stamps Pass/Fail. Ready=Yes is **not** §7 Pass. Do **not** invent §7 Pass from dogfood or from §6 / `008baf2`. Prior Ready=No on **`9312c54`** stays history. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-e5a8fdd/READY.md`; artifacts `/workspace/dogfood-e10-e5a8fdd/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 21:23 ET
**Who:** Tobias (dogfood restamp)
**SHA:** `e5a8fdd50538e23e67c1425dadb3e505171b987f` (e5a8fdd) tip of `feat/e10-aliquot-atomic-pair` (includes hasAliquotPair nullability fix).

**Clean FE build:** Yes — `docker build --no-cache` frontend from this SHA; CRA Compiled successfully; no local patch; working tree clean.

**Ready for UAT section 7?** Yes — clean FE Docker/CRA build green on tip `e5a8fdd`, and dogfood paths 1–5 Pass (single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). Not formal §7. Do **not** invent Pass from §6 / 008baf2. Not IC50.

Artifacts: `/workspace/dogfood-e10-e5a8fdd/`
```

## Addendum — Rolf Confirm: No Hold · 2026-09-14

**Rolf Confirm: No Hold.** Ready=Yes stands on **`e5a8fdd`**. Tobias proceeds with formal §7. Formal **§7 Unsigned** until Tobias stamps Pass/Fail. Evidence: `/workspace/dogfood-e10-e5a8fdd/READY.md`. Does **not** invent §7 Pass. Does **not** restamp §§1–6 (`008baf2`). Not IC50.

## Addendum — Tobias formal §7 Fail · 2026-09-14 21:31 ET

**Result: Fail** (Tobias QA) · SHA `e5a8fdd50538e23e67c1425dadb3e505171b987f` · `feat/e10-aliquot-atomic-pair` · Compose down.

Packet **7.1–7.8 Pass**. Overall **Fail** because of Deiter Lab Ops EXTRA **double-Add** bar: concurrent double POST → 2 plans + 2 dests; sequential 2nd POST → 2 plans + 1 dest. FE hide/disable present; API lacks single-pair uniqueness. Reload/refresh orphan **Pass**. Mint-early before execute **Pass**. **Blocking:** API allows a second plan POST while a pair (or half) exists. Server-side uniqueness needed before Pass.

Do **not** invent Pass for overall §7. **Ready=Yes** on `e5a8fdd` stands (dogfood). Product owns the API uniqueness fix before restamp. §§1–6 stay `008baf2`. Not IC50.

Artifacts: `/workspace/uat-e10-section7-e5a8fdd/`.