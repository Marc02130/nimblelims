# QA Review: Atomic receive

**Date:** 2026-08-20  
**Status:** Accept with conditions  
**Reviewer persona:** Testing / QA Lead (Tobias)  
**Tech sketch:** [PR 30](https://github.com/Marc02130/nimblelims/pull/30) — `.docs/tech-sketch/atomic-receive.md` (C1 dropped; ignore merged #28)  
**Related reviews:** Lab Ops L2–L4 (L1 retracted); CSO Accept; Architecture re-read requested; CEO Accept (PR 30 merged; stamp [PR 33](https://github.com/Marc02130/nimblelims/pull/33))  
**Stories:** [PR 32](https://github.com/Marc02130/nimblelims/pull/32) **merged** — full catalog on `main`. US-1 / US-7 / US-8 / US-30 match the receive loop.  
**UAT script:** [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md)  
**Test data IDs:** shared with Anton (AR-HV / AR-DUP / AR-ID / AR-ST / AR-TST / AR-RES / AR-RBAC / AR-MU)

## Executive summary

The PR 30 sketch is testable. Receive is a high-volume scan loop: one transaction, two identities, one status (**Available for Testing**), stay on the screen. US-1 is that happy path (no wizard, no sample-ID box, no status picker). US-7 / US-8 start tests at Assigned/Pending. US-30 is two identities. US-31 / US-33 / US-34 are parked for AR-01–AR-15.

Implement gate is **OPEN** (CEO merged PR 30). QA review is not a substitute for the post-implement UAT pass. Human UAT uses the merged PR 32 catalog on `main`. No third identity.

Architecture lock on result persist: typed number → `results.reported_result` + `qualifiers`. `raw_result` may copy the same value. UAT asserts `reported_result`, not a new column.

## Testability and coverage

| Dimension | Notes |
|-----------|--------|
| Testability | Every locked goal maps to a shared AR-* case or a pytest txn-rollback gate. |
| Sample lifecycle | Receive → Available for Testing → optional tests → result entry. No Received hop. |
| Negative paths | Duplicate barcode 409, missing required field 422, missing units_default 422, DELETE-with-results 400, RLS 403. |
| UAT readiness | Lab-tech happy path + client/foreign-project denial. Manager override is out of this packet. |
| Docs and Cursor | Implement prompt must update receive manuals and `uat-atomic-receive.md` (QA10). |
| Story alignment | US-1 / US-7 / US-8 / US-30 match the sketch on merged PR 32. |
| Results persist | Assert `reported_result` + `qualifiers`. Do not require a new column. |

## Conditions (must land with implement)

| ID | Condition | Why |
|----|-----------|-----|
| QA1 | One DB transaction. Forced failure after sample insert, or unique-container 409, leaves zero sample, container, contents, and tests. | Mid-rack orphan is the original defect. |
| QA2 | Receive UI has **no sample-ID field**. `samples.name` comes from the existing name template. `containers.name` = scanned barcode. They may differ. | C1 dropped. Two identities. |
| QA3 | Duplicate `containers.name` → **409**. Whole txn rolls back. No second sample. | Mix-up prevention. |
| QA4 | Commit writes Sample.status = **Available for Testing** only. Sets `received_date`. Request has no status field. No Received hop. | System-owned status. |
| QA5 | After success: stay on receive, toast, clear barcode, sticky type/matrix/project, focus barcode. No sample-detail redirect. No aliquot dialog. | High-volume loop. |
| QA6 | Tests optional at receive; status **assigned/pending**, not In Process. POST add later. DELETE without results ok. DELETE with results → **400**. | L4 + CSO. |
| QA7 | Typed number persists to `results.reported_result` + `qualifiers`. `raw_result` may copy the same value. Assert `reported_result`, not a new column. Unit from `analytes.units_default`. Missing default → **422**. No unit picker. No `results.unit_id`. | Architecture lock. |
| QA8 | `sample:create` required. Project list/API scoped by `project_users`. Client cannot receive. Foreign project → **403**, no row. Two techs keep separate sticky projects. | RLS. |
| QA9 | Seed: Available for Testing; Assigned/Pending (or agreed slug); default tube; sample name template that assigns without a typed name; unique `containers.name`. | Otherwise UAT is blocked on data. |
| QA10 | Cursor implement prompt updates receive/accessioning manuals **and** `UAT_Scripts/uat-atomic-receive.md`. After ship, `uat-sample-accessioning.md` is not the receive happy path. | Docs + UAT gate. |

Automated gate (pytest, not a human case): QA1 rollback after sample insert, before container commit.

## Suggested UAT scenarios

Must-pass in [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md): AR-HV-01–05, AR-VAL-01, AR-DUP-01, AR-ID-01, AR-ST-01, AR-TST-01–03, AR-RES-01–02, AR-RBAC-01, AR-MU-01.

**Not P0:** AR-MU-02 (US-10 second-person review).

## Out of this packet

Do **not** fail atomic-receive UAT on:

- US-31 receipt condition / manifest / disposition UI
- US-32 Quarantined / Rejected / Discarded
- US-33 / US-34 append-only audit event table
- US-36 / US-37 amendment and retest
- US-38 aliquot remaining quantity (no aliquot UI)
- ELN, LimsRuns, dose-response, parsers
- Sample.status = Reviewed or Reported (see Q1)
- US-10 second-person review (AR-MU-02)

## BA gaps (Wilhelmina)

Resolved on merged PR 32. No third identity.

| Was | Now |
|-----|-----|
| US-1 old wizard | Atomic-receive happy path. AR-01–AR-15 replaces it. |
| US-7 In Process at create | Assigned/Pending at receive/add-test. |
| US-30 lab_id on sample | Two identities. No `lab_id` column. |
| US-31 / US-33 new tables | Parked. Not in AR-01–AR-15. |
| Q3 user-entered lab_id | Closed. System sample ID + container barcode. |

Q1 (Tobias): this packet only sets **Available for Testing**. Dual path until US-10 result-level review UAT records a pass, then retire Reviewed/Reported on Sample.status.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | Accept with conditions |
| **Date** | 2026-08-20 |
| **Implement gate** | **OPEN** (CEO merged PR 30; stamp PR 33) |
| **UAT pass** | Still required after implement, before merge. Source: merged PR 32 catalog on `main`. |
