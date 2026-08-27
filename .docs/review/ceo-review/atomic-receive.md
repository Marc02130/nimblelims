# CEO / Product Review: Atomic receive (AR CORE)

**Date:** 2026-08-26  
**Leadership lock:** 2026-08-26 — CORE receive creates zero Tests; non-empty `analysis_ids` → **422** (refuse, do not ignore); A-15 asked-for/work-plan is parked
**Status:** Accept with conditions  
**Mode:** HOLD SCOPE  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Lab Ops:** [`.docs/review/lab-ops-review/atomic-receive.md`](../lab-ops-review/atomic-receive.md) — **Accept with conditions** (L2–L4; L1 retracted); **1..N vessels** language present (not stale first-tube)  
**Requirements:** [`.docs/internal/prd/sample-accessioning/PRD.md`](../../internal/prd/sample-accessioning/PRD.md) (RQ-AR-*, NR-AR-*)  
**Spec:** [`.docs/internal/specs/sample-accessioning/SPEC.md`](../../internal/specs/sample-accessioning/SPEC.md) (§3 + AC-AR-*)  
**Gate memo:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)  
**Stamps:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md)  
**Security (AuthZ):** [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md) — docs gate satisfied (PR 68)

---

## Executive summary

Atomic receive CORE is the right product wedge for intake: **identity + 1..N vessels in one transaction**, scan-first, two identities (system sample ID ≠ tube barcode), sticky required project, Available for Testing on commit, AuthZ = sample create + project RLS.

HOLD SCOPE. Do **not** pull test creation, results-entry, intake-profile engine, or `work_order` / routing into this slice. The 2026-08-26 Heidi punch supersedes ignore/silent-drop: receive creates **zero Tests**. Non-empty `analysis_ids` → **422**. Do not ignore. Silent drop would hide a client that still thinks Tests were created.

Lab Ops is not Hold/Revise. Gate clears for CEO Accept-with-conditions on the **requirements + spec CORE packet**. Historical packet design Accept (PR 30) remains; this review is the **CORE vs results** product freeze on the updated RQ-AR / SPEC.

**Premise (HOLD):** If we did nothing, labs keep orphan-risk multi-call create and an unfinished wizard as “receive.” That is real pain. The plan is the direct fix. Completeness inside CORE = primary + additional barcodes in one txn (not “first tube only, multi later”).

---

## Scope freeze (v1 / CORE)

Matches PRD **RQ-AR-*** (In) and **NR-AR-*** (Out). Do not expand.

| In (must ship for CORE) | Out (not CORE — ideas / later packets) |
|-------------------------|----------------------------------------|
| **RQ-AR-1** — `POST /api/samples/receive` + **new** receive UI loop | **NR-AR-1** — Results entry (`POST /tests/{id}/results`) / AR-RES as CORE must-pass |
| **RQ-AR-2** — Sample + **1..N** Containers + Contents, **one DB txn**; no partial commit | **NR-AR-2** — Aliquot UI / derivative sample mint |
| **RQ-AR-3** — Primary barcode required + optional additional barcodes (0..N) | **NR-AR-3** — Intake-profile engine / modes / manifest / bulk-as-mode (A-1–A-4) |
| **RQ-AR-4** — Each barcode → `containers.name`; any dup → **409** + full rollback | **NR-AR-4** — FieldDefinitions on default receive body (A-12) |
| **RQ-AR-5** — `samples.name` from name template; **no sample-ID field** | **NR-AR-5** — Work orders / routing / A-15 / Process·Exp·LimsRun |
| **RQ-AR-6** — Status → **Available for Testing** only; `received_date`; no Received hop / picker | **NR-AR-6** — Wizard revival as framework |
| **RQ-AR-7** — `project_id` required + sticky; never auto-create project per tube | **NR-AR-7** — Sidebar multi-config activate shell (FW-1b UX) |
| **RQ-AR-8** — Default tube type for all vessels, **off the form** | Profile engine beyond OOB narrative |
| **RQ-AR-9** — Omit `due_date`, `qc_type`, `client_id` from body | Results persist lock as **implement** in this PR |
| **RQ-AR-10** — Non-empty `analysis_ids` → **422**; receive creates **zero Tests** | Asked-for analyses / A-15 / work-plan creation; compound registration / lots (WO-5 / WO-6) |
| **RQ-AR-11** — AuthZ = sample create + project RLS; one API; no orphan multi-call substitute | Second receive permission / client bypass |
| **RQ-AR-12** — Stay on receive: toast, clear barcodes, sticky, focus primary | Sample-detail redirect; aliquot dialog |
| **RQ-AR-13** — Docs/UAT with ship: `uat-atomic-receive.md` happy path | Treating wizard UAT as receive SoT |

**Light ride (optional, not a scope expander):** A-14 legacy DELETE-with-results → 400 if the same test path is touched.

**Bounce:** PRD §3.3 / SPEC §10. Implement PR that violates those fails Leadership/CEO CORE acceptance. Ignore/silent-drop of `analysis_ids` also fails.

---

## CORE provisional implement open vs results carve

| Slice | Status | What it means |
|-------|--------|----------------|
| **AR CORE** (identity + **1..N** vessels + field align + AuthZ conditions + docs/UAT) | **Provisional implement open** (Leadership 2026-08-26; this CEO stamp) | May code against PRD RQ-AR-* / SPEC §3. AuthZ conditions from PR 68 land **with** CORE. |
| **Results-entry / persist lock** | **Design SoT only** — **follow-on** requirements packet | Typed number → `reported_result` + `qualifiers`; no `results.unit_id`. **Not** a CORE UAT or ship blocker (**NR-AR-1**). Do not reopen full PR 30 results bundle under CORE. |
| **Intake-profile engine** | Gated | After AR CORE works; FW-1 OOB = AR only until a second real profile exists. |
| **`work_order` / routing** | Gated (processing domain) | WO-* stamps stand; sequencing after CORE (+ results slice). Receive ≠ order ≠ work_order ≠ Process/Exp/LimsRun. |

**Explicit:** Do **not** treat historical “PR 30 Implement gate OPEN” or results language in the tech sketch as license to ship results-entry inside the AR CORE PR. Sketch product line already says provisional open for CORE only — enforce it.

---

## Conditions

Align with Lab Ops **L2–L4**. Product accepts those lab conditions as same-phase. Additional C* lock the CORE carve and multi-vessel honesty.

| ID | Condition | Aligns |
|----|-----------|--------|
| **C1** | **Historical identity (retracted).** `samples.name` is **not** the barcode. Two identities: tube = `containers.name` (scan); material = system sample ID from name template. Receive UI has **no sample-ID field**. | Lab Ops **L1 retracted**; sketch C1 gone |
| **C2** | Project **required** and **session-sticky**. Never auto-create a project per tube (or per vessel). | Lab Ops **L2** / RQ-AR-7 |
| **C3** | Container type = lab **default tube**, applied to **all** vessels on the call, **off the form** (no type picker on the scan loop). | Lab Ops **L3** / RQ-AR-8 |
| **C4** | CORE receive creates **zero Tests**. Non-empty `analysis_ids` → **422** (refuse, do not ignore, do not mint). Hide the analyses picker. A-15/work-plan is parked. **DELETE** of an independently created test with results → **400** (A-14 light ride OK). | Heidi 2026-08-26 / RQ-AR-10 |
| **C5** | **1..N vessels** in one txn (primary + optional additional barcodes). Single-vessel-only API/UI fails CORE (RQ-AR-2, RQ-AR-3, A-18). Any barcode collision → **409** + **full rollback**. | Leadership gate / SPEC AC-AR-2..4 |
| **C6** | **Results carve.** Results-entry API/UI and AR-RES UAT are **not** CORE acceptance. Persist-lock design may remain in the sketch as follow-on SoT only. | NR-AR-1 / gate memo |
| **C7** | AuthZ identical to **sample create** + **project RLS**; enforce in receive service; one receive API; refuse orphan multi-call as receive substitute; no client bypass. Conditions from security Accept-with-conditions land with CORE code. | RQ-AR-11 / PR 68 |
| **C8** | With ship: `UAT_Scripts/uat-atomic-receive.md` is receive happy path; wizard UAT demoted as receive SoT; docs paths under `.docs/review/` + `.docs/internal/`. Fix any remaining “first vessel only” stamp drift in the same docs pass. | RQ-AR-13 |

---

## HOLD SCOPE rigor (no expansion)

- **Complexity:** One new receive service + request model + one new UI loop. Reuse name template, default tube resolution, sample-create AuthZ, existing tables. Do not invent profile tables or results writers in this PR.
- **Minimum that ships value:** Primary-only receive works; multi-barcode receive works; dup → 409; non-empty `analysis_ids` → 422; sticky project; stay on form. That is the lake for CORE.
- **Deferred without blocking CORE:** Results persist implement, profile engine, work_order, aliquot UI, FieldDefinitions on body, sidebar activate shell.
- **Dream-state delta (note only):** 12-month ideal includes configurable intake profiles and work_order routing. This plan moves **toward** that by fixing identity/vessels first (FW-1 / sequencing stamp). Expanding those into CORE would move **away** from honesty.

**NOT expanding into CORE (will bounce):**

- `work_order`, routing keys, Process / Experiment / LimsRun instantiation  
- Intake-profile engine / multi-mode wizard revival  
- Results-entry as CORE ship/UAT blocker  
- New tables, `results.unit_id`, `status_history`  
- Aliquot / derivative UI  
- Ignore or silent-drop of `analysis_ids`  

---

## Lab Ops note

Current Lab Ops artifact is **Accept with conditions** (L2–L4; L1 retracted) and already states CORE creates one sample plus **1..N tubes** (primary + optional additional). **Not stale first-tube language.** If a parallel edit reintroduces “first vessel only,” treat that as drift against Leadership gate and **C5** / **C8**. L4 ignore language is superseded: non-empty `analysis_ids` → **422**.

CEO does not replace Lab Ops. Product accepts L2–L4 as C2–C4.

---

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Mode** | **HOLD SCOPE** |
| **Date** | 2026-08-26 |
| **CORE implement** | **Provisional open** — identity + **1..N** vessels + field align + AuthZ with ship + docs/UAT |
| **Results** | **Carve out** — follow-on slice; not CORE acceptance |
| **Profile engine / work_order** | **Out of CORE** — later packets per framework stamps |
| **Lab Ops gate** | Clear for this stamp (Accept with conditions; 1..N current) |
| **Same-phase conditions** | **C1** (retracted identity lock) · **C2–C4** (= L2–L4, L4 = 422-refuse) · **C5** (multi-vessel) · **C6** (results carve) · **C7** (AuthZ) · **C8** (docs/UAT) |

**Bottom line:** Freeze CORE as RQ-AR-1…13. Ship that. Do not smuggle results, profiles, or work orders into the AR PR. Do not ignore `analysis_ids`.
