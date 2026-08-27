# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Updated:** 2026-08-26 (CORE locks folded — 1..N + **refuse `analysis_ids`**) · 2026-08-26 (multi-container) · 2026-08-24 (AuthZ, PR 68)  
**Stem:** `atomic-receive`  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../requirements/atomic-receive.md)  
**Process:** [`.docs/review/development-process/README.md`](../development-process/README.md)  
**AuthZ docs gate:** **Satisfied** — Heidi/Günter **Accept with conditions** on §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md) (PR 68). Receive = sample create + project RLS; one txn; no parallel path.  
**Architecture:** **Accept** on CORE — [architecture-review/atomic-receive.md](../architecture-review/atomic-receive.md) — **with conditions** in §0.  
**UI:** **Accept** on CORE — [ui-review/atomic-receive.md](../ui-review/atomic-receive.md) — **with conditions** in §0.  
**WO-7:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md) — Test at **LimsRun start**, not receive.  
**Leadership:** [`.docs/discussions/2026-08-26-ar-core-plan-leadership.md`](../../discussions/2026-08-26-ar-core-plan-leadership.md)

**Status:** CORE locks folded. Implement follows **1..N** + **refuse `analysis_ids`**. PR 71 stays **draft** pending UAT + dogfood. Not IC50.

C1 (`samples.name` = barcode = `containers.name`) is **gone**. Two identities.

## 0. CORE locks (normative)

Implement follows PRD **1..N**, not the stale “first vessel” stamp. Coding stays Grok Build. **Hold merge** until UAT + dogfood; **PR 71 stays draft**. Architecture Accept + UI Accept on CORE are **with these conditions**.

| # | Lock |
|---|------|
| **1** | CORE = one `POST /samples/receive`, **one txn**: Sample + **1..N** 1×1 Containers + Contents **all pointing at that Sample**. Extra barcodes = more 1×1 Contents on the **same** Sample, **not** daughter Samples. |
| **2** | Any barcode collision (in the request or in the DB) → **409 + full rollback**. |
| **3** | AuthZ = sample create + project RLS (PR 68) on the **whole txn**. |
| **4** | **WO-7 hole closed for CORE.** `_create_asked_for_tests` is a **fail**. Empty `analysis_ids` as happy path is **not** enough. CORE **refuses** `analysis_ids` — **no Test mint at receive**. **Refuse (sketch pick):** if `analysis_ids` is present and non-empty → **422** (do not mint Tests, do not persist asked-for analyses). Empty or omitted is the only accepted path. Do **not** ignore. Do not add `work_order` or a new asked-for store in this packet. Classic Test+Result with no LimsRun still exists — do not silently kill it in stories. Test row at LimsRun start is **WO-7**, a later packet. |
| **5** | UI = **new receive loop**, not the wizard. Scan primary + optional extra barcodes. Sticky project / type / matrix. No sample-ID, no tube picker, no analysis-as-work-plan, no Received hop. Collision → **409**, stay on the scan well. |
| **6** | Hold merge until UAT + dogfood. PR 71 stays draft. |

## 1. Problem

Receive must create sample + **one or more** 1×1 containers + contents in **one DB transaction**, or a mid-rack failure orphans rows. Extra tubes for the same material are extra vessels, not new samples. Techs scan; they do not pick status, type a sample ID, or define a work plan at CORE receive.

## 2. Goals and non-goals

**Goals (locked — AR CORE)**

- One POST: sample + **1..N** 1×1 containers + contents for each, one transaction. All Contents → **that Sample**.
- Extra barcodes = more 1×1 vessels on the **same** Sample — not daughter Samples, not aliquot.
- UX: **primary barcode** required + **optional additional barcodes** on the same commit.
- **Two identities (C1 dropped, Lab Ops L1 retracted):**
  - `containers.name` = scanned barcode. Any collision (request or DB) → **409 + full rollback**.
  - `samples.name` = system-assigned sample ID from the **existing name template/sequence**. Tech does **not** type it.
  - `samples.name` 409 only if that sample ID itself collides.
- Receive screen: **no sample-ID field**. Lookup is scan the tube. Keyboard still works on the barcode field.
- Receive body: required primary `container_barcode`, `sample_type`, `matrix`, `project_id`; optional `additional_container_barcodes[]`, `temperature`, `client_sample_id`. **`analysis_ids`:** omitted or empty only; present and non-empty → **422**.
- Project required and sticky. Never auto-create per tube (L2).
- Container type = default tube, **off the form** (L3) — applies to all vessels on the call.
- One status on commit: **Available for Testing**. No Received hop. Receipt is existing `received_date`. No `status_history` table. Techs do not pick status.
- CORE receive creates **zero Tests**. **Refuse** non-empty `analysis_ids` (422). `_create_asked_for_tests` is a fail. A-15 asked-for / work-plan is parked. **Refuse DELETE** if an independently created test has results (A-14 + CSO). Classic Test+Result with no LimsRun still exists — not this packet.
- AuthZ = sample create + project RLS (PR 68) on the whole txn.
- Stay on receive after success: toast, clear barcode field(s), sticky type/matrix/project, focus primary barcode. No sample-detail redirect. No aliquot dialog.
- Mass/conc stay off Sample.

**Follow-on design SoT (not CORE ship)**

- **Results persist (Architecture same-phase lock for the results slice):** typed number lands in `results.reported_result` and `results.qualifiers`. `raw_result` **may copy the same value**. Unit from `analytes.units_default`; if missing, **422**. Do **not** add `results.unit_id`. No unit picker. **Not** a CORE UAT or ship blocker.
- Test row at **LimsRun start** (WO-7). Not accession. Not publish-ensure.

**Non-goals (CORE / this packet)**

- No new tables. No new columns. No wizard.
- No aliquot UI. Aliquot **later** (new dest vessel after process) remains separate from **multi-tube receive at intake**. Derivative **later** = new sample with `parent_sample_id`.
- No `work_order` / routing / extract-hold / intake-profile engine / second receive API / new asked-for store.
- No Test mint at receive. No ignore-and-continue for non-empty `analysis_ids`.
- No ELN, parsers, IC50, dose-response, method/QC/review ceremony, US-28 batch, manifests, materials, multi-tenant.
- Mass/conc stay off Sample. Method ≠ dest.

## 2b. CORE bounce (this packet / PR 71)

Normative. Architecture and UI **Accept** on CORE **only** if these stay out:

1. Orphan multi-call (create sample → create container → link)
2. Single-vessel-only (A-18 / “first vessel” stamp)
3. Sample-ID field / user-typed sample name / C1
4. Received hop or status picker
5. Project auto-create / optional project
6. Tube picker on the scan loop
7. Analysis as work plan / `_create_asked_for_tests` / mint Tests at receive / ignore non-empty `analysis_ids`
8. `work_order` / extract-hold / wizard revival
9. Second receive API
10. Results as CORE ship
11. New tables / `results.unit_id` / `status_history`
12. Extra vessels as daughter Samples
13. Mass/conc on Sample
14. Method = dest
15. IC50 / dose-response / parsers / ELN
16. Partial commit on barcode collision
17. AuthZ regression vs PR 68

## 3. Data model (existing tables only)

```
samples.name              ← name template/sequence (not the barcode)
samples.status            ← Available for Testing (one write)
samples.received_date     ← now()
samples.project_id        ← required, sticky
containers.name           ← scanned barcode (unique; 409 on duplicate)
containers.type_id        ← default tube (off form)
contents                  ← sample_id + container_id  (1..N rows → same sample)
tests                     ← no rows created by CORE receive
```

**Follow-on (results slice — not CORE):**

```
results.reported_result   ← typed number (Architecture persist lock)
results.qualifiers        ← optional <LOD / ND
results.raw_result        ← may copy the same typed value
                          no unit_id column
```

Make `samples.temperature` nullable if it is not already. Unique constraint on `containers.name` if missing. Do not add `status_history` or `results.unit_id`. Do not put mass/conc on Sample.

## 4. Contracts

### POST /api/samples/receive

```python
class SampleReceiveRequest(BaseModel):
    container_barcode: str                    # primary vessel (required)
    additional_container_barcodes: list[str] = []  # optional extra vessels, same sample
    sample_type: UUID
    matrix: UUID
    project_id: UUID                # required, sticky; never auto-create
    analysis_ids: list[UUID] | None = None  # omitted or [] only; present and non-empty → 422
    temperature: float | None = None
    client_sample_id: str | None = None
    # no status, no sample name, no container_type_id, no client_id
```

**`analysis_ids` refuse (sketch pick, WO-7 CORE hole closed):**

| Payload | Result |
|---------|--------|
| omitted | Accept. Zero Tests. |
| `[]` | Accept. Zero Tests. |
| present and non-empty | **422**. Do not mint Tests. Do not persist asked-for analyses. Full refuse (no partial receive). |

`_create_asked_for_tests` is a **fail**. Ignore is **not** the CORE pick. Empty/omitted happy path without the 422 is **not** enough.

In one transaction: assign `samples.name` from the existing name template; set status Available for Testing and `received_date`; for **primary + each additional** barcode insert 1×1 container (`name = barcode`) + contents → **same sample**. Any barcode collision (request or DB) → **409 + full rollback**. Do not insert Tests. Extra barcodes are extra vessels, not new Samples.

AuthZ = sample create + project RLS on the **whole txn** (PR 68).

### POST /api/samples/{id}/tests  and  DELETE /api/samples/{id}/tests/{test_id}

Not CORE receive. Classic Test+Result with no LimsRun **still exists** — do not silently kill it in stories. DELETE → 400 if any `results` exist for that test (A-14 + CSO). Light-ride — not a reason to pull results-entry or Test mint into CORE receive.

### POST /api/tests/{id}/results  (follow-on slice — not CORE)

```python
class ResultEntryRequest(BaseModel):
    analyte_id: UUID                # must belong to test.analysis
    reported_result: str            # typed number — persist lock
    qualifier: UUID | None = None   # <LOD, ND
    # no unit_id; no raw_result in the request
```

Service: write `results.reported_result` and `results.qualifiers`. `raw_result` may copy `reported_result`. Unit from `analytes.units_default`; missing → 422. No unit picker. No `results.unit_id`. **Not** a CORE ship / UAT blocker.

## 4b. AuthZ and receive path (Leadership 2026-08-24)

**AuthZ docs gate:** **Satisfied** (this section + [security-review/atomic-receive.md](../security-review/atomic-receive.md), PR 68). Heidi/Günter **Accept with conditions**. Conditions land with CORE code on the **draft** PR. Merge waits on UAT + dogfood.

| Lock | Detail |
|------|--------|
| **Permission** | `POST /api/samples/receive` uses the **same AuthZ as sample create** + **project RLS** (`has_project_access` / `lims_app`). |
| **No parallel path** | No separate receive permission, no client-only bypass, no second AuthZ spine. |
| **One API** | One receive endpoint. Bounce a parallel orphan multi-call (create sample → create container → link) and bounce a second receive API. |
| **One txn** | Sample + **1..N** 1×1 Containers + Contents each in a **single DB transaction**. CORE creates **zero Tests**. Clients that drop mid-sequence are refused by design — there is no safe multi-call substitute. |
| **Containers at receive** | All intake vessels for this sample share that same txn (not follow-up calls). Primary + optional additional barcodes. True extra vessels, not daughter Samples. |
| **AuthZ scope** | Sample-create permission + project RLS apply to the **whole txn** (every vessel). |

Implementers: enforce AuthZ/RLS **inside** the receive service before/with the txn; do not rely on the UI to gate project access.

Formal CSO stamp: [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md).

## 5. Receive loop (UI)

1. Scan (or type) **primary** barcode. **No sample-ID field.** Optionally add more barcodes for the same sample.
2. Sticky sample type, matrix, project. Temperature optional. **No analyses picker.** No work-plan.
3. Submit.
4. Stay on the screen. Toast. Clear barcode field(s). Keep sticky fields. Focus primary barcode.
5. Next sample (or next primary tube).

Do not redirect to sample detail. Do not open an aliquot dialog. Duplicate barcode → **409** toast, **stay on the scan well** (no partial commit). Formal UI stamp: [ui-review/atomic-receive.md](../ui-review/atomic-receive.md).

## 6. Locked vs parked later

| Locked now (CORE) | Later, not CORE |
|-------------------|-----------------|
| One sample + **1..N** 1×1 containers + contents, **zero Tests**, one txn | Asked-for / work-plan (A-15); Test at LimsRun start (**WO-7**) |
| Extra vessels = same Sample, not daughters | Aliquot **after** process (new dest vessel); derivative + `parent_sample_id` |
| **Refuse** non-empty `analysis_ids` → 422 | `work_order` / extract-hold / intake-profile engine |
| System sample ID + container barcode | Aliquot UI |
| Scan lookup, no sample-ID field | Classic Test+Result path (still exists — not killed) |
| AuthZ = sample create + project RLS on whole txn | Typed number → `reported_result` + `qualifiers` — results slice |
| | Review/release ceremony |

## 7. Reviews

| Review | Verdict |
|--------|--------|
| Lab Ops | L2–L3 hold. **L1 retracted.** **L4 Test-at-receive superseded:** CORE mints zero Tests; DELETE-with-results still stands for independently created tests. Two IDs correct. Receive must not show a sample-ID field. **1..N vessels** (not first-tube). |
| CSO | Accept. DELETE-with-results is data integrity. Classic results only. N/A for CORE assay/QC. Classic Test+Result with no LimsRun **still exists**. |
| Security (Heidi/Günter AuthZ) | **Accept with conditions** (PR 68). AuthZ **docs** gate **satisfied** — sketch §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md). Receive = sample create + project RLS on the **whole txn**; one API; one txn; no parallel path. Conditions land with CORE code. |
| Architecture | **Accept on CORE** — [architecture-review/atomic-receive.md](../architecture-review/atomic-receive.md). Historical PR 30 Accept stands (C1 gone; two IDs; 409 on `Container.name`; system `samples.name`; Available for Testing; no new tables). **CORE fold:** 1..N vessels, not first vessel; **refuse `analysis_ids`**; bounce list in §2b. Persist lock is follow-on SoT, not CORE ship. **Conditions:** hold merge until UAT + dogfood; PR 71 stays draft. |
| UI | **Accept on CORE** — [ui-review/atomic-receive.md](../ui-review/atomic-receive.md). New receive loop, not AccessioningForm / wizard. Scan primary + optional extra barcodes. Sticky type/matrix/project. No sample-ID, no tube picker, no analysis-as-work-plan, no Received hop. Collision → 409, stay on the scan well. **Conditions:** hold merge until UAT + dogfood; PR 71 stays draft. |
| CEO | **Accept with conditions** (HOLD SCOPE). One sample + **1..N** vessels. No aliquot UI, no ELN, no IC50. **Refuse** non-empty `analysis_ids`. Heidi bounces tables, a sample-ID field, a Received hop, or `results.unit_id`. **PR 71 stays draft** pending UAT + dogfood. |

```
STATUS: CORE locks folded. Implement follows 1..N + refuse analysis_ids.
PR 71 stays draft pending UAT + dogfood. Not IC50.
```
