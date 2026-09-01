# Sample receive (intake)

**Status:** The three-step `/accessioning` wizard is **removed**. There is one intake UI.

**Receive SoT:** [atomic-receive.md](atomic-receive.md)  
**UI:** `/receive` (sidebar **Receive**)  
**API:** `POST /samples/receive`  
**UAT:** [`uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md)

Old bookmarks to `/accessioning` redirect to `/receive`.

Do not assign analyses on receive. Non-empty `analysis_ids` on `POST /samples/receive` → **422**. Empty or omit → zero Tests. Params / `analysis_param_defs` are **not** on receive.

Receive ends on the form: commit, then scan the next tube. Samples sit **Available for Testing** and nothing at the bench is owed next.

Separately, **Asked-for** records requested analysis + TAT without minting work. Later Route yields 422 for zero acceptable rows, 409 when two saved rows both accept current type and the asked-for analysis, and snapshots an ordered process route only when exactly one accepts. Start instantiates its first process only. See [asked-for.md](asked-for.md). All remain **out of Receive**.

Classic Tests (`/tests` / TestForm) still exist for typing a number on an **existing** Test. That is **not** the request path.
