# 2026-09-10 — extract-hold dest container type UAT (section 6)

**Stem:** `extract-hold-dest-type`  
**SHA:** `008baf2705beb4238e434f893e3a06b53cac1145` (`008baf2`) · `feat/dest-container-type`  
**Not IC50.** Does **not** rewrite 1.7 / AC-P2-C3 / AC-P2-C2, named-slot, OQ-WO-7, Leadership overall P2, or receive first vessel.

**Result: Pass** (Tobias QA). **Rolf Confirm** 2026-09-10: full extract-hold dest-container-type §6 fold on `feat/dest-container-type` tip `008baf2`. Do **not** invent 6.1 from FE unit alone.

| Stamp | What |
|-------|------|
| 2026-09-10 21:53 ET | Live API Pass **6.2–6.8** + sections **1–5 smoke**. Alembic `0079`. Compose down. `pytest_dest_container` Skip (DinD) — not a Fail. |
| 2026-09-10 21:59 ET | Browser **6.1 Pass**. Three controls; Same as source. + 1×1; no 96-well / plates. Did not re-score 6.2–6.8. |
| 2026-09-10 | **Rolf Confirm** of the combined Pass. |

**Locks held:** plan control; dest init does not prompt; 1×1 only; Method ≠ dest sample type ≠ dest container type.

**Evidence (cite only; do not commit binaries):** `/workspace/uat-dest-container-type-008baf2-ui61/` and `/workspace/uat-dest-container-type-008baf2/{RESULT.md,tobias-stamp.json,acs.md}`.

Stamp of record: [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../UAT_Scripts/uat-extract-hold-dest-type.md) section 6.
