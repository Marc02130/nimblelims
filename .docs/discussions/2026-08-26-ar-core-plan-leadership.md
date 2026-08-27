# Leadership gate — Atomic receive CORE (requirements + spec)

**Date:** 2026-08-26  
**Role:** Leadership (CEO scope + Lab Ops bench truth + security-gate consumer)  
**Requirements:** [`.docs/internal/prd/sample-accessioning/PRD.md`](../internal/prd/sample-accessioning/PRD.md) (RQ-AR-*)  
**Spec:** [`.docs/internal/specs/sample-accessioning/SPEC.md`](../internal/specs/sample-accessioning/SPEC.md) (§3 + AC-AR-*)  
**Issues:** [`.docs/internal/prd/sample-accessioning/ISSUES.md`](../internal/prd/sample-accessioning/ISSUES.md)

---

## Verdict

**APPROVE WITH CHANGES**

CORE as scoped in **PRD requirements** (RQ-AR-1…13) and **SPEC** (§3 + AC-AR-*) is the right product wedge. Freeze CORE as **identity + 1..N vessels only.** Results entry is a **follow-on** slice — not CORE acceptance (**NR-AR-1**). Stamps that still say “first vessel” must be corrected before or with the implement PR.

**2026-08-26 chat punch (recorded here, not a new quote):** CORE must **refuse or ignore** `analysis_ids` — **no Test mint at receive**. Empty `analysis_ids` as the happy path is **not** enough. Wilhelmina pick: **refuse**. Non-empty `analysis_ids` → **422**. Do not call `_create_asked_for_tests`. Architecture/UI **Accept** holds only with refuse-or-ignore (no Test mint). PR 71 stays draft until UAT + dogfood. Not IC50.

---

## In / out (ruthless)

**IN:** RQ-AR-1…13 — `POST /samples/receive` + new receive UI; one txn; primary + optional additional barcodes; Available for Testing; sticky required project; system sample name; tube off form; omit legacy body junk; **omit `analysis_ids` (empty `[]` OK); non-empty → 422; zero Tests at receive**; AuthZ = sample create + project RLS; docs/UAT with ship.

**OUT:** NR-AR-1…7 — Results-entry API/UI as CORE must-pass; aliquot/derivative; intake-profile engine (A-1–A-4); FieldDefinitions on AR body (A-12); work_order / routing / A-15; wizard revival; second receive API; manifest/bulk-as-mode; sidebar activate shell; Test mint at receive / `_create_asked_for_tests` / `analysis_ids` as work plan.

**A-14** may ride lightly with CORE; it is not a reason to pull results into CORE. Classic Test+Result with no LimsRun still exists — do not kill it in stories. Test row at LimsRun start is WO-7 (later packet, not CORE).

---

## Marc green-light

**Provisional open for this CORE only** (PRD RQ-AR-* / SPEC §3 — identity + 1..N vessels + field align + docs/UAT with ship).

Does **not** reopen full PR 30 results bundle, profile engine, or processing. Coding stays Grok Build. Hold merge until UAT + dogfood.

---

## Bounce conditions (implement PR fails Leadership)

See **PRD §3.3** / **SPEC §10** (same list). Highlights:

1. Multi-call still the supported receive story  
2. Single-vessel-only (A-18 / RQ-AR-3 ignored)  
3. Sample-ID field / user-typed sample name / C1  
4. Received hop or status picker  
5. Project auto-create / optional project  
6. Container type picker on scan loop  
7. Analysis as “what’s next” / work plan  
8. Test mint at receive / `_create_asked_for_tests` / `analysis_ids` as work plan / ignore or silent-drop of `analysis_ids` (must **422** if non-empty)  
9. work_order / routing / Process·Exp·LimsRun / aliquot in the AR PR  
10. Intake-profile engine or second receive API/permission  
11. Results-entry treated as CORE ship blocker  
12. New tables / `results.unit_id` / `status_history`  
13. AuthZ regression vs PR 68  
14. Partial commit on barcode collision  
15. Wizard kept as forever receive path  
16. IC50 / dose-response / parsers / ELN  

---

## Sequencing

1. Docs drift patch (first vessel → 1..N; CORE vs results carve; 422-refuse `analysis_ids`)  
2. Implement against **PRD RQ-AR-*** / **SPEC §3**  
3. Docs sync + dogfood + UAT (AR script = happy path)  
4. Merge to `main` (hold until UAT + dogfood; PR 71 stays draft)  
5. Results-entry slice (separate requirements open)  
6. Work-order + routing  
7. Intake-profile engine when a second real profile exists  

---

## Team comment (for ISSUES)

**Leadership:** APPROVE WITH CHANGES — AR CORE is identity + **1..N** vessels in one txn (PRD RQ-AR-* / SPEC AC-AR-*), not results, not aliquot, not profile engine, not work_order; **no Test mint at receive** (2026-08-26 chat punch; Wilhelmina pick **refuse** — non-empty `analysis_ids` → **422**); provisional Marc open for that CORE only; fix “first vessel” stamp drift; results persist stays a later slice; Receive ≠ order ≠ work_order ≠ Process/Exp/LimsRun — don’t revive the wizard. PR 71 stays draft until UAT + dogfood. Not IC50.
