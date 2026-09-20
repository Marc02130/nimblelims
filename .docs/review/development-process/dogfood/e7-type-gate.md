# Dogfood: E-7 type gate on experiment / LimsRun start

**Stem:** `extract-hold-dest-type`  
**Branch:** `feat/e7-type-gate-experiment-limsrun`  
**When:** After the stack is up, before Tobias UAT §10.  
**Not a UAT Result.** Do not invent Pass. Do not restamp §§1–9.

## Env

Local compose. Process definition with accepted types. `experiment:manage`.

## Paths

1. Process definition experiment step: accepted types DNA only. Instantiate. Start step (empty). Assign Blood. Start experiment with Blood → **422** `route_sample_type`.
2. Remove Blood. Assign DNA. Start experiment → cohort locks.
3. LimsRun step DNA-only. Start the run with Blood → **422**.
4. Ad hoc experiment (no process). Start with Blood → succeeds.
5. Experiment Templates: no accepted-types control. POST `accepted_sample_types` on the template → **422**.
6. Eligible list: Blood ineligible (type); DNA eligible.

## Ready for UAT?

Unsigned until Tobias. Do not invent Ready=Yes.
