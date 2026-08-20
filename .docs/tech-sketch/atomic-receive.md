# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Status:** **Architecture Accept (PR 30 + persist lock). Lab Ops L2–L4 + L1 retracted. CSO Accept. Packet signed. No product code until CEO passes.**  
**Stem:** `atomic-receive`  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

C1 (`samples.name` = barcode = `containers.name`) is **gone**. Two identities.

## 1. Problem

Receive must create sample + first container + contents + optional tests in **one DB transaction**, or a mid-rack failure orphans rows. Techs scan; they do not pick status and they do not type a sample ID.

## 2. Goals and non-goals

**Goals (locked)**

- One POST: sample + first container + contents + optional tests, one transaction.
- **Two identities (C1 dropped, Lab Ops L1 retracted):**
  - `containers.name` = scanned barcode. Duplicate scan → **409 on container only**.
  - `samples.name` = system-assigned sample ID from the **existing name template/sequence**. Tech does **not** type it.
  - `samples.name` 409 only if that sample ID itself collides.
- Receive screen: **no sample-ID field**. Lookup is scan the tube. Keyboard still works on the barcode field.
- Receive body, exact: required `barcode`, `sample_type`, `matrix`, `project_id`; optional `analysis_ids`, `temperature`, `client_sample_id`.
- Project required and sticky. Never auto-create per tube (L2).
- Container type = default tube, **off the form** (L3).
- One status on commit: **Available for Testing**. No Received hop. Receipt is existing `received_date`. No `status_history` table. Techs do not pick status.
- Tests optional at receive. Status = assigned/pending, not In Process (L4). **Refuse DELETE** if the test has results (L4 + CSO).
- **Results persist (Architecture same-phase lock):** typed number lands in `results.reported_result` and `results.qualifiers`. `raw_result` **may copy the same value**. Unit from `analytes.units_default`; if missing, **422**. Do **not** add `results.unit_id`. No unit picker.
- Stay on receive after success: toast, clear barcode, sticky type/matrix/project, focus barcode. No sample-detail redirect. No aliquot dialog.

**Non-goals (this packet)**

- No new tables. No new columns. No wizard.
- No aliquot UI. Aliquot **later** = another container + another contents row on the **same** sample. Derivative **later** = new sample with `parent_sample_id`.
- No ELN, parsers, IC50, dose-response, method/QC/review ceremony, US-28 batch, manifests, materials, multi-tenant.

## 3. Data model (existing tables only)

```
samples.name              ← name template/sequence (not the barcode)
samples.status            ← Available for Testing (one write)
samples.received_date     ← now()
samples.project_id        ← required, sticky
containers.name           ← scanned barcode (unique; 409 on duplicate)
containers.type_id        ← default tube (off form)
contents                  ← sample_id + container_id
tests                     ← optional; status assigned/pending
results.reported_result   ← typed number (Architecture persist lock)
results.qualifiers        ← optional <LOD / ND
results.raw_result        ← may copy the same typed value
                          no unit_id column
```

Make `samples.temperature` nullable if it is not already. Unique constraint on `containers.name` if missing. Do not add `status_history` or `results.unit_id`.

## 4. Contracts

### POST /api/samples/receive

```python
class SampleReceiveRequest(BaseModel):
    container_barcode: str          # scan or keyboard → containers.name
    sample_type: UUID
    matrix: UUID
    project_id: UUID                # required, sticky; never auto-create
    analysis_ids: list[UUID] = []   # optional
    temperature: float | None = None
    client_sample_id: str | None = None
    # no status, no sample name, no container_type_id, no client_id
```

In one transaction: assign `samples.name` from the existing name template; set status Available for Testing and `received_date`; insert container with `name = barcode` (409 on duplicate); insert contents; insert optional tests as assigned/pending.

### POST /api/samples/{id}/tests  and  DELETE /api/samples/{id}/tests/{test_id}

No wizard. DELETE → 400 if any `results` exist for that test.

### POST /api/tests/{id}/results

```python
class ResultEntryRequest(BaseModel):
    analyte_id: UUID                # must belong to test.analysis
    reported_result: str            # typed number — persist lock
    qualifier: UUID | None = None   # <LOD, ND
    # no unit_id; no raw_result in the request
```

Service: write `results.reported_result` and `results.qualifiers`. `raw_result` may copy `reported_result`. Unit from `analytes.units_default`; missing → 422. No unit picker. No `results.unit_id`.

## 5. Receive loop (UI)

1. Scan (or type) barcode. **No sample-ID field.**
2. Sticky sample type, matrix, project. Optional tests. Temperature optional.
3. Submit.
4. Stay on the screen. Toast. Clear barcode. Keep sticky fields. Focus barcode.
5. Next tube.

Do not redirect to sample detail. Do not open an aliquot dialog. Duplicate barcode → 409 toast, stay on screen.

## 6. Locked vs parked later

| Locked now | Later, not this packet |
|------------|------------------------|
| One sample + first container + contents + optional tests, one txn | Aliquot: another container + contents on same sample |
| System sample ID + container barcode | Derivative: new sample + `parent_sample_id` |
| Scan lookup, no sample-ID field on receive | Aliquot UI |
| Typed number → `reported_result` + `qualifiers` (`raw_result` may copy) | Review/release ceremony |

## 7. Reviews

| Review | Verdict |
|--------|--------|
| Lab Ops | L2–L4 hold. **L1 retracted.** Two IDs correct. Receive must not show a sample-ID field. |
| CSO | Accept. DELETE-with-results is data integrity. Classic results only. |
| Architecture | **Accept on PR 30.** C1 gone. Two IDs. 409 on `Container.name`. System-assigned `samples.name`. One status: Available for Testing. Short receive body. No new tables / no `results.unit_id`. **Persist lock:** typed number → `reported_result` + `qualifiers`; `raw_result` may copy. Packet signed. |
| CEO | Open. No product code until CEO passes. |
