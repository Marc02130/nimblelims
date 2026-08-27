# Lab Ops Review (SVP): Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept with conditions** (L2–L3; L1 retracted; L4 superseded by 2026-08-27 Leadership lock)
**Reviewer persona:** SVP Lab Ops  
**Scope of this stamp:** **AR CORE only** — identity + **1..N vessels** + field align + docs/UAT with ship  
**Packet:**  
- Requirements: [`.docs/internal/prd/sample-accessioning/PRD.md`](../../internal/prd/sample-accessioning/PRD.md) (RQ-AR-*, NR-AR-*, bounce, AC)  
- Spec: [`.docs/internal/specs/sample-accessioning/SPEC.md`](../../internal/specs/sample-accessioning/SPEC.md) (§3 contract, AC-AR-*, AuthZ)  
- Tech sketch: [tech-sketch/atomic-receive.md](../tech-sketch/atomic-receive.md)  
**Related:**  
- Leadership gate: [discussions/2026-08-26-ar-core-plan-leadership.md](../../discussions/2026-08-26-ar-core-plan-leadership.md) (**APPROVE WITH CHANGES**)  
- Framework stamps: [decision-logs/framework-stamps-2026-08-26.md](../../decision-logs/framework-stamps-2026-08-26.md)  
- Prior Lab Ops (2026-08-20): superseded by this re-review for CORE carve  

---

## 1. Executive summary

**CORE as now expressed in PRD + SPEC is bench-real for high-volume receive.** A tech scans a **primary** barcode, optionally adds **additional** barcodes for the same material, keeps sticky type/matrix/project, commits once, stays on the form, and goes to the next specimen. That is how racks actually move.

**Two identities remain correct lab practice (L1 stays retracted):**

| Identity | Field | Receive |
|----------|--------|---------|
| Tube / vessel | `containers.name` | Scanned barcode. Any duplicate (request or DB) → **409** and full rollback. |
| Material | `samples.name` | System-assigned from the existing name template. Tech does **not** type it. Receive UI has **no sample-ID field**. |

**Multi-tube at intake is not aliquot UI.** Same sample, multiple vessels on one receive commit (blood + EDTA, paired plasma tubes, kit replicates) is ordinary accessioning. Aliquot after process and derivative mint (`parent_sample_id`) stay later — correctly out of CORE (**NR-AR-2**).

**Results-entry OUT of CORE is correct for Lab Ops.** Receive dogfood does not need a results path. A tech can verify identity, multi-vessel commit, sticky loop, status, and AuthZ without typing a number. Persist lock stays design SoT for a **follow-on** slice (**NR-AR-1**). Do not block CORE UAT on AR-RES.

**Language:** Prefer **primary + additional barcodes** / **1..N vessels**. Do **not** use outdated “first tube / first vessel only” framing. Single-vessel-only API/UI fails the product bounce (PRD §3.3 #2).

**Verdict: Accept with conditions** (L2–L4). Conditions are already normative in PRD/SPEC/sketch and must land with CORE implement.

---

## 2. Focus answers (this re-review)

### 2.1 Is CORE (identity + 1..N vessels) bench-real for high-volume receive?

**Yes.** The loop matches bench truth:

1. Scan / type **primary** barcode (no sample-ID field).  
2. Optionally add **additional** barcodes before submit (same sample).  
3. Sticky type / matrix / project (required project — never auto-create).  
4. Default tube type off the form for all vessels on the call.  
5. One commit → Available for Testing + `received_date`; toast; clear barcode field(s); focus primary; **stay on receive**.  

No status picker, no sample-detail redirect, no aliquot dialog, no container-type picker on the scan loop. That keeps the keyboard/scanner rhythm intact for volume.

### 2.2 Are multi-tube receive requirements clear enough?

**Yes — clear enough to implement and UAT.** Normative chain:

| Source | Clarity |
|--------|---------|
| **RQ-AR-2 / RQ-AR-3 / G7** | Primary required + additional 0..N; one txn; Contents → same sample |
| **SPEC §3.1–3.2** | `container_barcode` + `additional_container_barcodes[]`; default tube for all vessels; 409 + full rollback on any collision |
| **AC-AR-1 / AC-AR-2 / AC-AR-3** | Primary-only, primary+K, and dup paths are testable |
| **Bounce #2 / #13** | Single-vessel-only and partial commit fail CORE acceptance |

No Lab Ops gap that blocks coding. Watch item only: UI must make “add another barcode before submit” obvious without implying aliquot/split — see §4.

### 2.3 Results-entry OUT of CORE — Lab Ops confirm

**Confirmed correct.** Receive ≠ order ≠ execute ≠ results. Techs dogfood receive by scanning vessels and checking sample/container integrity — not by entering analyte values. The 2026-08-27 Leadership lock supersedes L4: CORE creates zero Tests, ignores legacy `analysis_ids`, and hides the analyses picker. A-15 is parked.

**Do not** pull `POST /tests/{id}/results` into CORE ship/UAT blockers so that “receive can be dogfooded.” That path is unnecessary for accessioning acceptance.

---

## 3. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| **Bench reality** | **9** | Scan loop + sticky session + stay-on-form is high-volume receive. Primary + additional on one commit matches multi-tube kits. |
| **Material & sample integrity** | **8** | Two IDs; Contents links every vessel to one sample; one txn prevents orphan samples without vessels. Aliquot/derivative correctly later. |
| **Chemistry / sequencing** | **N/A (7 contextual)** | Not in CORE scope. No indexing/pooling/reagent inventiveness required for intake identity. |
| **Gating & compliance habits** | **8** | Forced Available for Testing; no status picker; DELETE refused if results exist (L4 / A-14 light-ride); AuthZ = sample create + project RLS. |
| **Template → instance** | **7** | OOB = atomic receive (FW-1). Intake-profile engine deferred — correct; do not invent modes in this PR. |
| **Competitive floor** | **8** | Atomic multi-vessel receive with system sample ID is table-stakes vs commercial LIMS; wizard orphan path is not. |
| **Containers / amount** | **7** | Vessels + default tube locked. Amount/volume/pool multi-content not CORE intake — OK. |
| **Cohort / queue** | **N/A (6 contextual)** | Per-commit receive, not a started cohort/queue. Fine for accessioning wedge. |
| **Instrument boundary** | **N/A (9 contextual)** | Correctly out: Process / Exp / LimsRun / parsers not in AR PR. Receive ≠ work_order (WO-*). |

---

## 4. Conditions (must land with CORE implement)

| ID | Condition | Why | Status vs PRD/SPEC |
|----|-----------|-----|---------------------|
| **L1** | **Retracted.** Barcode ≠ sample ID. Two identities. | Sample ID is material; barcode is the tube. | Retracted (2026-08-20); still retracted |
| **L2** | Project **required** and **session-sticky**. Never auto-create a project per tube / commit. | Auto-create dumps garbage projects and breaks RLS hygiene. | **RQ-AR-7** / SPEC §3 |
| **L3** | Container type = **lab default tube**, applied to **all** vessels on the call, **off the form** (no type picker on the scan loop). | Asking type on every scan (or per additional barcode) breaks the loop. | **RQ-AR-8** / SPEC §3.2 |
| **L4** | **Superseded 2026-08-27:** CORE receive creates zero Tests and ignores legacy `analysis_ids`. **DELETE** remains refused if an independently created test has results. | Receive does not imply an order or work plan; A-15 is parked. | Leadership lock / A-14 light-ride |

No new L* required for multi-tube: **RQ-AR-2/3** and bounce #2 already encode Lab Ops intent (primary + additional; not single-vessel-only).

---

## 5. Locked for CORE (do not reopen)

- One `POST /api/samples/receive`, one DB transaction: sample + **1..N containers** + contents each; zero Tests
- UX: **primary barcode required** + **optional additional barcodes** on the same commit
- After success: stay on receive; toast; clear barcode field(s); sticky type/matrix/project; focus **primary** barcode
- No sample-detail redirect; no aliquot dialog; no sample-ID field; no status picker; no container-type picker
- Status on commit: **Available for Testing** only; receipt = `received_date`; no `status_history`
- No analyses picker. Omit `analysis_ids`; legacy values are ignored. A-15/work-plan remains parked.
- AuthZ identical to sample create + project RLS; no second receive API; no client bypass; no orphan multi-call substitute
- Existing tables only; no `results.unit_id`; no new tables for CORE
- **OUT of CORE:** results-entry as ship blocker; aliquot/derivative UI; intake-profile engine; work_order / routing / Process·Exp·LimsRun; wizard as forever receive path

---

## 6. Risks / watch items (non-blocking)

1. **Additional-barcode UX copy** — Label as “additional tube / barcode for this sample,” not “aliquot” or “split,” so techs do not invent a derivative workflow at intake.  
2. **Which barcode collided** — 409 toast should identify the offending barcode when practical (primary vs an additional) so the rack can be fixed without retyping the whole set.  
3. **Default tube resolution** — Lab must have a resolvable default tube type in env; missing default is an ops/config failure, not a reason to put type on the scan form.  
4. **Stamp drift** — Any remaining “first vessel only” language in older notes is obsolete; implement and UAT against **1..N** / primary + additional.  
5. **Results persist lock** — Remains valid design for a later slice; do not quietly re-bundle into CORE UAT.

---

## 7. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L2–L4; L1 retracted) |
| **CORE scope** | Identity + **1..N vessels** + field align + docs/UAT — **approved for Lab Ops** |
| **Results-entry** | **OUT of CORE** — confirmed correct; follow-on slice |
| **Multi-tube** | Requirements **clear enough**; primary + additional; bounce single-vessel-only |
| **Date** | 2026-08-26 |
| **Implement gate (CORE only)** | **OPEN** — L2–L4 already accepted into PRD/SPEC/sketch; land with code |
| **Not licensed by this stamp** | Results-entry implement, intake-profile engine, work_order / routing, aliquot UI |

---

## 8. Prior stamp delta (2026-08-20 → 2026-08-26)

| Item | Change |
|------|--------|
| Packet SoT | Re-review against **PRD RQ-AR-*** + **SPEC §3**, not plan-doc alone |
| Vessels | Explicit **1..N** / primary + additional (A-18); retract “first tube only” framing |
| Results | Explicitly **NR-AR-1** — out of CORE acceptance |
| L1–L4 | Unchanged: L1 retracted; L2–L4 still required same-phase |
| Implement gate | **OPEN for CORE only** (aligned with Leadership provisional open 2026-08-26) |
