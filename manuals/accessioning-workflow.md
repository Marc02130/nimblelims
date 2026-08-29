# Sample receive (intake)

**Status:** The three-step `/accessioning` wizard is **removed**. There is one intake UI.

**Receive SoT:** [atomic-receive.md](atomic-receive.md)  
**UI:** `/receive` (sidebar **Receive**)  
**API:** `POST /samples/receive`  
**UAT:** [`uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md)

Old bookmarks to `/accessioning` redirect to `/receive`.

Do not assign analyses on receive. Non-empty `analysis_ids` on `POST /samples/receive` → **422**. Empty or omit → zero Tests. Params / `analysis_param_defs` are **not** on receive.

Receive ends on the form: commit, then scan the next tube. Samples sit **Available for Testing** and nothing at the bench is owed next.

Separately — a **later look-up**, not the click after a commit — **Asked-for** (`/asked-for`) or the sample-detail Asked-for section records **requested analysis + TAT** — [asked-for.md](asked-for.md). That save does **not** mint a Test or work order and does **not** start work. P2 Route is another later action: an explicit match may mint a queued work order, and WO-7 creates or attaches the Test only when a LimsRun starts. Route, work orders, and WO-7 all remain **out of Receive**.

Classic Tests (`/tests` / TestForm) still exist for typing a number on an **existing** Test. That is **not** the request path.
