# QA Review: Atomic receive

**Date:** 2026-08-20  
**Status:** Accept with conditions  
**Reviewer persona:** Testing / QA Lead (Tobias)  
**Tech sketch:** [PR 30](https://github.com/Marc02130/nimblelims/pull/30) — `.docs/tech-sketch/atomic-receive.md` (C1 dropped; ignore merged #28)  
**Related reviews:** Lab Ops L2–L4 (L1 retracted); CSO Accept; Architecture re-read requested; CEO open  
**Stories:** [PR 32](https://github.com/Marc02130/nimblelims/pull/32) reconciles US-30 / US-7 / US-8 / US-10 / US-31 / US-38 to the two-ID sketch  
**UAT script:** [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md)  
**Test data IDs:** shared with Anton (AR-HV / AR-DUP / AR-ID / AR-ST / AR-TST / AR-RES / AR-RBAC / AR-MU)

## Executive summary

The PR 30 sketch is testable. Receive is a high-volume scan loop: one transaction, two identities, one status (**Available for Testing**), stay on the screen. [PR 32](https://github.com/Marc02130/nimblelims/pull/32) aligns US-30 and test-create status with that sketch. UAT is written from the sketch + PR 32, **not** old US-30. Implement gate stays **CLOSED** until Heidi signs and CEO passes.

Architecture lock on result persist: typed number → `results.reported_result` + `qualifiers`. `raw_result` may copy the same value. UAT asserts `reported_result`, not a new column.

QA review is not a substitute for the post-implement UAT pass.

## Testability and coverage

| Dimension | Notes |
|-----------|--------|
| Testability | Every locked goal maps to a shared AR-* case or a pytest txn-rollback gate. |
| Sample lifecycle | Receive → Available for Testing → optional tests → result entry. No Received hop. |
| Negative paths | Duplicate barcode 409, missing required field 422, missing units_default 422, DELETE-with-results 400, RLS 403. |
| UAT readiness | Lab-tech happy path + client/foreign-project denial. Manager override is out of this packet. |
| Docs and Cursor | Implement prompt must update receive manuals and `uat-atomic-receive.md` (QA10). |
| Story alignment | US-30 / US-7 / US-31 / US-38 reconciled on PR 32. **US-1** still describes the old wizard. |
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

**Not P0:** AR-MU-02 (US-10 second-person review, catalog-only until Q2 has a schema home).

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

## Remaining BA gap

**US-1** still describes typed sample name, status picker, review-to-Available, 3-step wizard, aliquot dialog. That is `uat-sample-accessioning`. This packet’s happy path is `uat-atomic-receive`. US-1 should be rewritten or marked superseded when PR 32 lands.

US-30, US-7, US-31, US-38, Q3, Q5: treated as resolved on PR 32.

**Merge note:** PR 31 and PR 32 both edit `.docs/open-questions/sop-sample-identity-audit.md`. Keep Q1 (Tobias, decided provisional parallel) from 31 and Q2/Q3/Q5 updates from 32.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | Accept with conditions |
| **Date** | 2026-08-20 |
| **Implement gate** | CLOSED until Heidi signs and CEO passes |
| **UAT pass** | Still required after implement, before merge |
