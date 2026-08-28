# Sample receive (intake)

**Status:** The three-step `/accessioning` wizard is **removed**. There is one intake UI.

**Receive SoT:** [atomic-receive.md](atomic-receive.md)  
**UI:** `/receive` (sidebar **Receive**)  
**API:** `POST /samples/receive`  
**UAT:** [`uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md)

Old bookmarks to `/accessioning` redirect to `/receive`.

Do not assign analyses on receive. After receive, samples are **Available for Testing**. Record requested analyses on **Asked-for** (`/asked-for`) or the sample-detail Asked-for section. That does **not** mint a Test. Classic Tests (`/tests` / TestForm) still exist for the WO-4 type-a-number path.
