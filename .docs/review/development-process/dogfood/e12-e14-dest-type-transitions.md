# Dogfood: E-12 template dest type + E-14 transition catalog

**Stem:** `extract-hold-dest-type`  
**Branch:** `feat/e12-e14-dest-type-transitions`  
**When:** After the stack is up, before Tobias UAT §§8–9.  
**Ready for UAT?** **Yes** (Tobias, 2026-09-20, `c4c899d`; evidence `/workspace/uat-e12-e14-c4c899d/dogfood/READY.md`). Product on `main` (PR **131**, `811e966`). Ready=Yes is not a substitute for the formal §§8–9 Pass (already stamped). Do **not** restamp §§1–7.

## Env

Local compose. `config:edit` (admin) and `experiment:manage`.

## Paths

1. Admin → **Dest-type transitions**. Seeded rows visible. Add a row; duplicate → 409.
2. Lab tech without config:edit: page redirects; API POST **403**.
3. Experiment Templates → aliquot/pool plan: **Default dest sample type** next to method and dest container. Set DNA, save, start experiment → runtime default is DNA.
4. Clear to Same as parent, save, start → runtime default blank.

## Ready for UAT?

**Yes** on `c4c899d` (Tobias, 2026-09-20). Formal §§8–9 **Pass** on the same SHA. Product on `main` @ `811e966` (PR **131**). Do **not** invent a second Pass from this file.
