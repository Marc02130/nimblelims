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

**Date:**  
**Who:**  
**SHA:**  
**Ready for UAT section 6?** Yes / No — why
