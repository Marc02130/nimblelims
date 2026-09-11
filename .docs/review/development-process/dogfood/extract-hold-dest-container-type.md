# Dogfood: dest container type on aliquot/pool plan

**Stem:** `extract-hold-dest-type` (container-type control)  
**Branch:** `feat/dest-container-type`  
**When:** After this branch is up, **before** Tobias UAT section 6 in [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md).  
**Not a UAT Result.** Not dest-follow recode. Not IC50.

## Env

Local compose on **this feature branch**. `experiment:manage`. 1×1 container types in catalog (Cryovial / tube). Do not prune the DB volume unless you want a wipe.

## Paths to try

1. Plan entry: confirm **three** controls — Method, Default dest sample type, Default dest container type.
2. Same as source (empty default + inherit) → execute → dest vessel matches source type.
3. Entry default to another 1×1 type → inherit → dest uses that type.
4. Line **Same as source** overrides entry default.
5. Line picks a 1×1 type.
6. Template default dest container type survives experiment create.
7. Confirm dest init never prompts for container type.
8. Confirm 96-well is not in the dest mint picker.

## Ready for UAT?

Fill after a walk:

**Date:** 2026-09-10  
**Who:** Tobias  
**SHA:** `008baf2705beb4238e434f893e3a06b53cac1145` (`008baf2`), alembic `0079`, local compose (down after the run)  
**Ready for UAT section 6?** **Yes — UAT section 6 is Pass (Tobias QA).** Path 1 / 8 (three controls; 96-well absent) is **browser Pass** 21:59 ET. Paths 2–7 are **live API Pass** 21:53 ET. Stamp of record: [`UAT_Scripts/uat-extract-hold-dest-type.md`](../../../../UAT_Scripts/uat-extract-hold-dest-type.md) section 6. Evidence (cite only; do not commit screenshots): `/workspace/uat-dest-container-type-008baf2-ui61/` and `/workspace/uat-dest-container-type-008baf2/{RESULT.md,tobias-stamp.json,acs.md}`.
