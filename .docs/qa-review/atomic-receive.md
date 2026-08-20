# QA Review: Atomic receive

**Date:** 2026-08-20  
**Status:** Accept with conditions  
**Reviewer persona:** Testing / QA Lead (Tobias)  
**Tech sketch:** [PR 30](https://github.com/Marc02130/nimblelims/pull/30) — `.docs/tech-sketch/atomic-receive.md` (C1 dropped; ignore merged #28)  
**Related reviews:** Lab Ops L2–L4 (L1 retracted); CSO Accept; Architecture re-read requested; CEO open  
**Stories:** [PR 29](https://github.com/Marc02130/nimblelims/pull/29) — US-2, US-10, US-30–US-38 in `.docs/user-stories/nimblelims-user.md`  
**UAT script:** [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md)

## Executive summary

The PR 30 sketch is testable. Receive is a high-volume scan loop: one transaction, two identities, one status (**Available for Testing**), stay on the screen. Living stories still describe the old accessioning wizard (typed sample name, Received hop, In Process tests). That drift is a BA gap, not a third design. Implement gate stays **CLOSED** until Heidi signs PR 30 and CEO passes.

QA review is not a substitute for the post-implement UAT pass.

## Testability and coverage

| Dimension | Notes |
|-----------|--------|
| Testability | Every locked goal maps to an AR-* case or a pytest txn-rollback gate. |
| Sample lifecycle | Receive → Available for Testing → optional tests → result entry. No Received hop. |
| Negative paths | Duplicate barcode 409, missing required field 422, missing units_default 422, DELETE-with-results 400, RLS 403. |
| UAT readiness | Lab-tech happy path + client/foreign-project denial. Manager override is out of this packet. |
| Docs and Cursor | Implement prompt must update receive manuals and `uat-atomic-receive.md` (QA10). |
| Story alignment | US-1, US-7, US-30 still contradict the sketch. Do not UAT a hybrid. |

## Conditions (must land with implement)

| ID | Condition | Why |
|----|-----------|-----|
| QA1 | One DB transaction. Forced failure after sample insert, or unique-container 409, leaves zero sample, container, contents, and tests. | Mid-rack orphan is the original defect. |
| QA2 | Receive UI has **no sample-ID field**. `samples.name` comes from the existing name template. `containers.name` = scanned barcode. They may differ. | C1 dropped. Two identities. |
| QA3 | Duplicate `containers.name` → **409**. Whole txn rolls back. No second sample. | Mix-up prevention. |
| QA4 | Commit writes Sample.status = **Available for Testing** only. Sets `received_date`. Request has no status field. No Received hop. | System-owned status. |
| QA5 | After success: stay on receive, toast, clear barcode, sticky type/matrix/project, focus barcode. No sample-detail redirect. No aliquot dialog. | High-volume loop. |
| QA6 | Tests optional at receive; status **assigned/pending**, not In Process. POST add later. DELETE without results ok. DELETE with results → **400**. | L4 + CSO. |
| QA7 | Result: raw value + optional qualifier. Unit from `analytes.units_default`. Missing default → **422**. No unit picker. No `results.unit_id`. | Classic results only. |
| QA8 | `sample:create` required. Project list/API scoped by `project_users`. Client cannot receive. Foreign project → **403**, no row. | RLS. |
| QA9 | Seed: Available for Testing; Assigned/Pending (or agreed slug); default tube; sample name template that assigns without a typed name; unique `containers.name`. | Otherwise UAT is blocked on data. |
| QA10 | Cursor implement prompt updates receive/accessioning manuals **and** `UAT_Scripts/uat-atomic-receive.md`. After ship, `uat-sample-accessioning.md` is not the receive happy path. | Docs + UAT gate. |

Automated gate (pytest, not a human case): QA1 rollback after sample insert, before container commit.

## Suggested UAT scenarios

Must-pass AR-01–AR-15 in [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md): scan and keyboard receive, sticky second tube, 409 no orphan, two IDs, add/remove tests, DELETE-with-results 400, unit default or 422, client/RLS denial.

## Out of this packet

Do **not** fail atomic-receive UAT on:

- US-31 receipt condition / manifest / disposition UI
- US-32 Quarantined / Rejected / Discarded
- US-33 / US-34 append-only audit event table
- US-36 / US-37 amendment and retest
- US-38 aliquot remaining quantity (no aliquot UI)
- ELN, LimsRuns, dose-response, parsers
- Sample.status = Reviewed or Reported (see Q1)

## BA gaps (Wilhelmina)

Resolve before implement. QA will not invent a third model.

1. **US-30** puts `lab_id` on the sample. Sketch: barcode = `containers.name`, `samples.name` = name template. UAT treats lab barcode = `containers.name` until the story is rewritten.
2. **US-7** AC still says tests start **In Process**. L4 is **assigned/pending**.
3. **US-1** still describes typed sample name, status picker, review-to-Available, 3-step wizard, aliquot dialog. That is `uat-sample-accessioning`. This packet replaces that happy path.
4. **US-31 / US-33** need new events or tables. Sketch says none. Confirm parked for this packet.
5. **Q3** provisional “user-entered lab_id” vs system-assigned `samples.name`. Same as (1).

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | Accept with conditions |
| **Date** | 2026-08-20 |
| **Implement gate** | CLOSED until Heidi signs PR 30 and CEO passes |
| **UAT pass** | Still required after implement, before merge |
