# Sample receive (intake)

**Status:** The three-step `/accessioning` wizard is **removed**. There is one intake UI.

**Receive SoT:** [atomic-receive.md](atomic-receive.md)  
**UI:** `/receive` (sidebar **Receive**)  
**API:** `POST /samples/receive`  
**UAT:** [`uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md)

Old bookmarks to `/accessioning` redirect to `/receive`.

Do not assign analyses on receive. Non-empty `analysis_ids` on `POST /samples/receive` → **422**. Empty or omit → zero Tests. Params / `analysis_param_defs` are **not** on receive.

After receive, samples are **Available for Testing**. Record **requested analysis** on **Asked-for** (`/asked-for`) or the sample-detail Asked-for section — [asked-for.md](asked-for.md). That does **not** mint a Test and does **not** start work. Route / work_orders / WO-7 are **out** of the P1 stamp.

Classic Tests (`/tests` / TestForm) still exist for typing a number on an **existing** Test. That is **not** the request path.
