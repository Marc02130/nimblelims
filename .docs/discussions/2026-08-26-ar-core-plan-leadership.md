# Leadership gate — Atomic receive CORE (requirements + spec)

**Date:** 2026-08-26  
**Updated:** 2026-08-26 (CORE locks folded — **1..N** + **refuse `analysis_ids`**; hold merge / PR 71 draft)  
**Role:** Leadership (CEO scope + Lab Ops bench truth + security-gate consumer)  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../review/requirements/atomic-receive.md)  
**Sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../review/tech-sketch/atomic-receive.md)  
**WO-7:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../decision-logs/framework-stamps-2026-08-26.md)

---

## Verdict

**APPROVE WITH CHANGES** — CORE locks folded.

CORE = identity + **1..N** vessels only. Implement follows PRD **1..N**, not “first vessel.” Results entry is a **follow-on** slice. **Refuse `analysis_ids`** (sketch pick). **Hold merge** until UAT + dogfood. **PR 71 stays draft.**

---

## In / out (ruthless)

**IN:** One `POST /samples/receive`; one txn; Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample**; primary + optional additional barcodes; Available for Testing; sticky required project; system sample name; tube off form; AuthZ = sample create + project RLS on the whole txn; new receive UI; docs/UAT/dogfood with ship.

**OUT:** Results-entry as CORE must-pass; aliquot/derivative; intake-profile engine; FieldDefinitions on AR body; `work_order` / routing / A-15; wizard revival; second receive API; Test mint at receive; ignore non-empty `analysis_ids`; new asked-for store; Method = dest; IC50.

**WO-7 hole closed for CORE:** `_create_asked_for_tests` is a **fail**. Empty `analysis_ids` as happy path is **not** enough. CORE **refuses** `analysis_ids` — **no Test mint at receive**. **Refuse:** if `analysis_ids` is present and non-empty → **422** (do not mint Tests, do not persist asked-for analyses). Empty or omitted is the only accepted path. Classic Test+Result with no LimsRun still exists — do not silently kill it in stories. Test row at LimsRun start is **WO-7**, a later packet.

---

## Marc green-light

**Provisional coding open for this CORE only** (identity + 1..N vessels + refuse `analysis_ids` + field align + docs/UAT). Coding stays Grok Build.

**Merge hold:** UAT + dogfood required. **PR 71 stays draft.** Does **not** reopen full PR 30 results bundle, profile engine, or processing.

---

## Bounce conditions (implement PR fails Leadership)

1. Orphan multi-call  
2. Single-vessel-only  
3. Sample-ID field / C1  
4. Received hop  
5. Project auto-create  
6. Tube picker  
7. Analysis as work plan / `_create_asked_for_tests` / ignore non-empty `analysis_ids`  
8. `work_order` / extract-hold / wizard revival  
9. Second receive API  
10. Results as CORE ship  
11. New tables  
12. Extra vessels as daughter Samples  
13. Mass/conc on Sample  
14. Method = dest  
15. IC50  
16. Partial commit on barcode collision  
17. AuthZ regression vs PR 68  

---

## Sequencing

1. Docs fold (this packet) — 1..N + refuse `analysis_ids`; Architecture/UI Accept with conditions  
2. Implement against CORE sketch + requirements (draft PR 71)  
3. Dogfood + UAT (AR script = happy path; 422 on non-empty `analysis_ids`)  
4. Merge to `main` **only after** UAT + dogfood  
5. Results-entry slice (separate requirements open)  
6. Work-order + routing; Test at LimsRun start (WO-7)  
7. Intake-profile engine when a second real profile exists  

---

## Team comment (for ISSUES)

**Leadership:** APPROVE WITH CHANGES — AR CORE is identity + **1..N** vessels in one txn; **refuse** present non-empty `analysis_ids` (422); `_create_asked_for_tests` is a fail; PR 71 stays draft pending UAT + dogfood; not results, not aliquot, not profile engine, not work_order; fix “first vessel” stamp drift; Receive ≠ order ≠ work_order ≠ Process/Exp/LimsRun — don’t revive the wizard. Not IC50.
