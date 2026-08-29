# Tech sketch: Post-receive work spine

**Date:** 2026-08-28  
**Stem:** `post-receive-work-spine`  
**Status:** P2 room-locked 2026-08-28. Architecture / UI / Spec **Accept with conditions** on `feat/work-order-p2` @ `3b56cfb`. **Hold merge until UAT.** Punches before merge: publish-refuse-whole-run, first-start-wins, one process definition, P2-4 read visibility, list-key. Not IC50.  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Process:** [`.docs/review/development-process/README.md`](../development-process/README.md)

P1 is on `main`. P2 is on `feat/work-order-p2` (Accept with conditions). Do not code P3–P5 in the P2 PR. Coding stays Grok Build.

**Lab Ops 2026-08-28:** Accept with conditions. P1 implementable if **L1** is in the UI/copy. **P2 coding closed until L2–L4 are in this sketch** (folded below). **L5** binds P4 copy. Artifact: [lab-ops-review/post-receive-work-spine.md](../lab-ops-review/post-receive-work-spine.md).

**Room locks (2026-08-28):**

1. **P1 lake** = asked-for records **requested analysis + TAT + params**. Bounce Test / Result / Process / Experiment / LimsRun / work_order mint, second workflow engine, analysis picker on `/receive`, silent Order→work.
2. **Heidi:** `GET /asked-for` `list()` must **dual-belt `has_project_access`** (same as create), **not RLS-only**. `analysis_param_defs` RLS may be any logged-in user; mutate stays `config:edit` in the router. P1 must **not** write status `routed` (`routed` is P2). Type × analysis eligibility is **P2 (L2)**, not this PR.
3. **Params** on `asked_for` are **order capture**, not the Test snapshot. Freeze still happens at LimsRun start (WO-7 / P2). Bounce Start/Execute CTA, silent Order→work, analysis picker on `/receive`, README that equates asked-for with Test assign. Classic `/tests` type-a-number stays.
4. **Mathilda U1 / U2:** asked-for ≠ Test assign. Label params as order capture, not Test snapshot.
5. Architecture / UI / Spec **Accept with conditions** on P2 @ `3b56cfb`. Hold merge until UAT. Not IC50.
6. **Receive freeze:** non-empty `analysis_ids` still **422**.
7. **P2 one process (Heidi / Mathilda U1):** `routing_map` and `work_order` hold **one** process definition (typed Exp/LimsRun steps). Bounce process-of-processes, `uuid[]` chain, completing N starts N+1, `start` of `[0]` only.
8. **WO-7 publish:** refuse the **whole** publish (**422**) if a Test is missing. Swallow `ensure_test` 422 into `plan.errors` and mark published is skip-and-complete — bounce.
9. **Freeze:** first LimsRun start wins. `_mint_tests_at_start` must **not** overwrite `asked_for_params` on an existing Test.
10. **P2-4 visibility (QA Fail):** if a tech can instantiate the mapped process (`experiment:manage` / existing process AuthZ), she can **read** that definition and its steps — including admin-created or null `created_by`. Mutate stays where it is. Route is **not** admin-only. Invisible def → “no steps” is **not** `route_sample_type`.
11. **P2-2/3 list-key:** routing map and receive use the **same** sample-type list (`sample_types`). `sample_type` vs `sample_types` empty select is a list-key bug, not a type gate.
