# 2026-09-14 — E-10 atomic pair UAT punch (Marc / Rolf)

**Stem:** `extract-hold-dest-type` (atomic pair)  
**Branch:** product on `main` (PR **129**)  
**Product SHA (overall §7 / uniqueness):** **`dc7ee92`** (`dc7ee92c086558420c16edffe301773975f17234`). Merge tip **`e56a89f`** (`e56a89fe01656b416cfcae885b6ade605e8cf38e`).  
**Live state:** formal **§7 Result: Pass** (Tobias QA, 2026-09-14 22:28 ET, **`dc7ee92`**) — **7.1–7.8 Pass** on `e5a8fdd` (not rescored) **plus** Deiter **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`). Prior overall **Fail** on `e5a8fdd` is **history**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). Living uniqueness: **409** `wrapper_at_capacity` (not a blocker). **Tobias dogfood Ready=Yes** on `dc7ee92` (`/workspace/dogfood-e10-dc7ee92/READY.md`). Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay history.  
**Not IC50.** Does **not** restamp dest-container-type §§1–6 (`008baf2` Pass). Does **not** teach overall §7 Fail or Hold merge as current. Does **not** touch named-slot / OQ-WO-7 / C2/C3 unsigned stamps.

## Punch

Rolf 2026-09-14: fold Marc’s E-10 UAT rows. The punch was unsigned at that point; Tobias stamped §7 **Fail** on **`e5a8fdd`** (21:31 ET), then overall **Pass** on **`dc7ee92`** (22:28 ET). Dogfood first was on **`9312c54`**; living dogfood / uniqueness SHA is **`dc7ee92`**.

**Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14). Confirm of the punch, **not** the double-Add Met.

| Row | Lock |
|-----|------|
| **7.3b** | Delete dest → both disappear (same as delete plan) |
| **7.6b** | API POST dest-only (`aliquots_pools`) → **201**; GET includes plan |
| **7.7b** | API DELETE dest → both inactive |
| **7.8** | After the pair is gone, **+ Aliquot/pool** / Add re-enables (one pair at a time — not a lifetime lock) |

**Pass criteria this packet = 7.1–7.8** (on `e5a8fdd`) **plus** Deiter double-Add (on `dc7ee92`). Steps **1–6** stay the `008baf2` dest-container-type stamp (Pass).

## Honesty (operator + AC)

- Delete either half removes the pair.
- POST either side creates the pair.
- DELETE either inactivates both.
- Add re-enables after the pair is gone.
- Second instance while the wrapper exists is **409** `wrapper_at_capacity` (no half-pair; concurrent 201+409 → 1+1).

Stamp of record: [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../UAT_Scripts/uat-extract-hold-dest-type.md) section 7 (**Pass** overall). Requirements AC1b: [`.docs/review/requirements/extract-hold-dest-type.md`](../review/requirements/extract-hold-dest-type.md). Operator: [`manuals/experiments.md`](../../manuals/experiments.md), [`manuals/HOWTO.md`](../../manuals/HOWTO.md).

## Addendum — Tobias dogfood Ready=No · 2026-09-14 20:26 ET

**Ready for UAT section 7?** **No** on **`feat/e10-aliquot-atomic-pair`**. Paths **1–5 Pass** on product **`9312c54`**. Clean FE **Docker** build fails **TS2345** `hasAliquotPair` nullability. Local one-line patch was walk-only — **not landed**. Formal **§7 Unsigned** at that time. **History.** Superseded by Ready=Yes on **`e5a8fdd`**, then living Ready=Yes on **`dc7ee92`**. Does **not** restamp §§1–6 (`008baf2`). Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```

## Addendum — Tobias dogfood Ready=Yes · 2026-09-14 21:23 ET · dogfood history

**Ready for UAT section 7?** **Yes** on **`e5a8fdd`**. Paths **1–5 Pass**. Clean FE **Docker**/CRA. Living Ready=Yes is on **`dc7ee92`**. This SHA’s Ready=Yes is history. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

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

## Addendum — Rolf Confirm: No Hold on starting §7 · 2026-09-14 · history

**Rolf Confirm: No Hold** lifted the Hold on **starting** formal §7 after Ready=Yes on **`e5a8fdd`**. Evidence: `/workspace/dogfood-e10-e5a8fdd/READY.md`. It was never a UAT Pass.

**History.** Later 21:31 ET overall **Fail** brought **Hold merge**. Living gate is **Hold merge lifted** (product on `main` @ `e56a89f`, PR **129**).

## Addendum — Tobias formal §7 Fail · 2026-09-14 21:31 ET · history

**Result: Fail** (Tobias QA) · SHA `e5a8fdd50538e23e67c1425dadb3e505171b987f`.

Packet **7.1–7.8 Pass**. Overall **Fail** on this SHA because of Deiter Lab Ops EXTRA **double-Add**: concurrent double POST → 2 plans + 2 dests; sequential 2nd POST → 2 plans + 1 dest. **Then-blocking (history):** API second plan POST while pair/half exists. Closed by uniqueness on `dc7ee92`. §§1–6 stay `008baf2`. Not IC50.

Evidence (cite only):
- `/workspace/uat-e10-section7-e5a8fdd/RESULT.md`
- `/workspace/uat-e10-section7-e5a8fdd/acs.md`
- `/workspace/uat-e10-section7-e5a8fdd/stamp.json`

## Addendum — Rolf Confirm of the Fail: Hold merge · 2026-09-14 · history

**Rolf Confirm** of Tobias's §7 **Fail** on **`e5a8fdd`** was **Hold merge**. Lifted after uniqueness restamp + overall Pass. Product merged to `main` via PR **129** at `e56a89f`. Do **not** teach Hold merge as current. Not IC50.

## Addendum — Tobias dogfood Ready=Yes · `dc7ee92` · current dogfood

**Ready for UAT section 7?** **Yes** on **`dc7ee92`**. Clean FE Docker/CRA; paths **1–5 Pass**. Evidence: `/workspace/dogfood-e10-dc7ee92/READY.md`. Formal overall Pass is 22:28 ET (below). §§1–6 stay `008baf2`. Not IC50.

## Addendum — Deiter double-Add Pass · `dc7ee92` · Lab Ops Met

**Deiter Lab Ops EXTRA double-Add: Pass** on `dc7ee92`. Sequential second plan POST → **409** `wrapper_at_capacity`; second dest POST → **409**; GET still **1 plan + 1 dest**. Concurrent double POST → **201 + 409**; after counts **1 plan + 1 dest**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. Prior Fail on `e5a8fdd` is history. **7.9 / 7.9b Pass** from this uniqueness honesty. §§1–6 stay `008baf2`. Not IC50.

Evidence:
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`

## Addendum — Tobias overall §7 Pass · 2026-09-14 22:28 ET · current

**Result: Pass** (Tobias QA) · SHA `dc7ee92c086558420c16edffe301773975f17234` (`dc7ee92`).

**7.1–7.8 Pass** on `e5a8fdd` (not rescored) + Deiter **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`) **closes** prior overall Fail on `e5a8fdd`. **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). §§1–6 stay `008baf2`. Not IC50.

Evidence:
- `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`
- `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`
- `/workspace/dogfood-e10-dc7ee92/READY.md`

## Addendum — Rolf Confirm: Hold merge lifted · E-10 Met · `main` `e56a89f` (PR 129)

**Rolf Confirm:** Hold merge **lifted**. E-10 **Met**. Product already on `main` at `e56a89fe01656b416cfcae885b6ade605e8cf38e` (PR **129**). Fold overall §7 **Pass** honesty onto `main`. Do **not** teach Hold merge as current. Not IC50.
