# Requirements: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Spec **Accept with conditions** on P2 (`feat/work-order-p2` @ `3b56cfb`, 2026-08-28 room). **P1 shipped** on `main` (PR 81; UAT Pass). **Hold merge until UAT.** Punches: publish-refuse-whole-run, first-start-wins, one process definition, P2-4 read visibility, list-key. Not IC50.  
**Stem:** `post-receive-work-spine`  
**Leadership sequencing (2026-08-28):** order (asked-for) → work_order → results → SOP+AI → process → instrument import config  
**Do not implement P2+ until those phase reviews Accept / Accept-with-conditions and open questions that block the named phase are Decided.**

**Room locks (2026-08-28):**

11. **P2-4:** if a tech can instantiate the mapped process, she can **read** that definition and its steps (existing process AuthZ). Mutate stays. Route is not admin-only. “No steps” from hidden RLS is not `route_sample_type`.
12. **P2-2/3:** routing map and receive share the `sample_types` list. Empty select from `sample_type` vs `sample_types` is a list-key bug.

| **RQ-WO-7** | Instantiating **that** process definition uses **existing process AuthZ** (`experiment:manage`). **P2-4:** Route / type-gate / start **read** the mapped definition and its steps under that same AuthZ — including admin-created or null `created_by`. Mutate stays. Route is not admin-only. Invisible def → “no steps” is not `route_sample_type`. |

20. Admin-only Route / RLS that hides a mapped def from a tech who can run it
21. “No steps” / invisible def presented as `route_sample_type`
22. Routing map `sample_type` vs receive `sample_types` (empty select / list-key)

| AC-P2-4 | alice Routes a mapped def created by admin and can read its steps; not admin-only Route |
| AC-P2-5 | Publish with a missing Test → 422 the whole run, not published |
| AC-P2-6 | Routing type select uses `sample_types` (same list as receive); not empty from `sample_type` |
