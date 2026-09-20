# Dogfood: E-12 template dest type + E-14 transition catalog

**Stem:** `extract-hold-dest-type`  
**Branch:** `feat/e12-e14-dest-type-transitions`  
**When:** After the stack is up, before Tobias UAT §§8–9.  
**Not a UAT Result.** Do not invent Pass. Do not restamp §§1–7.

## Env

Local compose. `config:edit` (admin) and `experiment:manage`.

## Paths

1. Admin → **Dest-type transitions**. Seeded rows visible. Add a row; duplicate → 409.
2. Lab tech without config:edit: page redirects; API POST **403**.
3. Experiment Templates → aliquot/pool plan: **Default dest sample type** next to method and dest container. Set DNA, save, start experiment → runtime default is DNA.
4. Clear to Same as parent, save, start → runtime default blank.

## Ready for UAT?

Unsigned until Tobias. Do not invent Ready=Yes.
