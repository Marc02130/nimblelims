# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Updated:** 2026-08-26 (multi-container receive: 1..N vessels) · 2026-08-24 (AuthZ fold, PR 68)  
**Stem:** `atomic-receive`  
**Process:** [`.docs/review/development-process/README.md`](../development-process/README.md)  
**AuthZ docs gate:** **Satisfied** — Heidi/Günter **Accept with conditions** on §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md) (PR 68). Receive = sample create + project RLS; one txn; no parallel path.  
**Product implement:** **Provisional open for AR CORE only** (Leadership 2026-08-26) — identity + **1..N vessels** + field align + docs/UAT. Do **not** treat PR 30 “Implement gate OPEN” as license for results-entry / profile engine / work_order.  
**Packet design (historical, still stands):** CEO Accept (PR 30 merged). Lab Ops L2–L4 + L1 retracted. Scientific CSO Accept. Architecture Accept. UI Accept. Results persist lock remains **design SoT for a follow-on slice**, not CORE UAT blocker.  
**Multi-container (2026-08-26):** One sample + **1..N containers** in the same txn (primary barcode + optional additional barcodes). Not limited to a single vessel.

C1 (`samples.name` = barcode = `containers.name`) is **gone**. Two identities.

## 1. Problem

Receive must create sample + **one or more** containers + contents (+ optional tests) in **one DB transaction**, or a mid-rack failure orphans rows. It is common to receive more than one tube for the same sample. Techs scan; they do not pick status and they do not type a sample ID.

## 2. Goals and non-goals

**Goals (locked)**

- One POST: sample + **1..N containers** + contents for each (+ optional tests), one transaction.
- UX: **primary barcode** required + **optional additional barcodes** on the same commit.
- **Two identities (C1 dropped, Lab Ops L1 retracted):**
  - `containers.name` = scanned barcode. Duplicate scan → **409 on container only**.
  - `samples.name` = system-assigned sample ID from the **existing name template/sequence**. Tech does **not** type it.
  - `samples.name` 409 only if that sample ID itself collides.
- Receive screen: **no sample-ID field**. Lookup is scan the tube. Keyboard still works on the barcode field.
- Receive body: required primary `container_barcode`, `sample_type`, `matrix`, `project_id`; optional `additional_container_barcodes[]`, `analysis_ids`, `temperature`, `client_sample_id`.
- Project required and sticky. Never auto-create per tube (L2).
- Container type = default tube, **off the form** (L3) — applies to all vessels on the call.
- One status on commit: **Available for Testing**. No Received hop. Receipt is existing `received_date`. No `status_history` table. Techs do not pick status.
- Tests optional at receive (prefer omit as work plan). If present: assigned/pending, not In Process (L4). **Refuse DELETE** if the test has results (L4 + CSO).
- **Results persist (Architecture same-phase lock):** typed number lands in `results.reported_result` and `results.qualifiers`. `raw_result` **may copy the same value**. Unit from `analytes.units_default`; if missing, **422**. Do **not** add `results.unit_id`. No unit picker.
- Stay on receive after success: toast, clear barcode field(s), sticky type/matrix/project, focus primary barcode. No sample-detail redirect. No aliquot dialog.

**Non-goals (this packet)**

- No new tables. No new columns. No wizard.
- No aliquot UI. Aliquot **later** (new dest vessel after process) remains separate from **multi-tube receive at intake**. Derivative **later** = new sample with `parent_sample_id`.
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
    container_barcode: str                    # primary vessel (required)
    additional_container_barcodes: list[str] = []  # optional extra vessels, same sample
    sample_type: UUID
    matrix: UUID
    project_id: UUID                # required, sticky; never auto-create
    analysis_ids: list[UUID] = []   # optional; prefer omit as work plan
    temperature: float | None = None
    client_sample_id: str | None = None
    # no status, no sample name, no container_type_id, no client_id
```

In one transaction: assign `samples.name` from the existing name template; set status Available for Testing and `received_date`; for **primary + each additional** barcode insert container (`name = barcode`, 409 on any duplicate) + contents → same sample; insert optional tests as assigned/pending.

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

## 4b. AuthZ and receive path (Leadership 2026-08-24)

**AuthZ docs gate:** **Satisfied** (this section + [security-review/atomic-receive.md](../security-review/atomic-receive.md), PR 68). Heidi/Günter **Accept with conditions**. **Product code:** provisional open for **AR CORE** (identity + 1..N vessels); AuthZ conditions land with that implement.

| Lock | Detail |
|------|--------|
| **Permission** | `POST /api/samples/receive` uses the **same AuthZ as sample create** + **project RLS** (`has_project_access` / `lims_app`). |
| **No parallel path** | No separate receive permission, no client-only bypass, no second AuthZ spine. |
| **One API** | One receive endpoint. Bounce a parallel orphan multi-call (create sample → create container → link) and bounce a second receive API. |
| **One txn** | Sample + **1..N Containers** + Contents each (+ optional tests) in a **single DB transaction**. Clients that drop mid-sequence are refused by design — there is no safe multi-call substitute. |
| **Containers at receive** | All intake vessels for this sample share that same txn (not follow-up calls). Primary + optional additional barcodes. |

Implementers: enforce AuthZ/RLS **inside** the receive service before/with the txn; do not rely on the UI to gate project access.

Formal CSO stamp: [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md).

## 5. Receive loop (UI)

1. Scan (or type) **primary** barcode. **No sample-ID field.** Optionally add more barcodes for the same sample.
2. Sticky sample type, matrix, project. Temperature optional. Prefer no test assignment on default profile.
3. Submit.
4. Stay on the screen. Toast. Clear barcode field(s). Keep sticky fields. Focus primary barcode.
5. Next sample (or next primary tube).

Do not redirect to sample detail. Do not open an aliquot dialog. Duplicate barcode → 409 toast, stay on screen (no partial commit).

## 6. Locked vs parked later

| Locked now | Later, not this packet |
|------------|------------------------|
| One sample + **1..N containers** + contents (+ optional tests), one txn | Aliquot **after** process (new dest vessel) — distinct from multi-tube **receive** |
| System sample ID + container barcode | Derivative: new sample + `parent_sample_id` |
| Scan lookup, no sample-ID field on receive | Aliquot UI |
| Typed number → `reported_result` + `qualifiers` (`raw_result` may copy) | Review/release ceremony |

## 7. Reviews

| Review | Verdict |
|--------|--------|
| Lab Ops | L2–L4 hold. **L1 retracted.** Two IDs correct. Receive must not show a sample-ID field. |
| CSO | Accept. DELETE-with-results is data integrity. Classic results only. |
| Security (Heidi/Günter AuthZ) | **Accept with conditions** (PR 68). AuthZ **docs** gate **satisfied** — sketch §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md). Receive = sample create + project RLS; one API; one txn; no parallel path. **CORE provisional open** — AuthZ conditions land with CORE code. |
| Architecture | **Accept on PR 30.** C1 gone. Two IDs. 409 on `Container.name`. System-assigned `samples.name`. One status: Available for Testing. Short receive body. No new tables / no `results.unit_id`. **Persist lock:** typed number → `reported_result` + `qualifiers`; `raw_result` may copy. Packet signed. |
| UI | **Accept.** New receive loop, not AccessioningForm. Scan writes the tube. Sticky type/matrix/project. No sample-ID, status, or tube-type field. Stay on screen. Bounce a sample-ID box, wizard, sample-detail redirect, or timestamp-suffix. |
| CEO | **Accept. PR 30 merged** (packet **design**). One sample + **1..N vessels**. No aliquot UI, no ELN, no IC50. Heidi bounces tables, a sample-ID field, a Received hop, or `results.unit_id`. **CORE provisional open** (Leadership 2026-08-26); results-entry is a follow-on slice. |
