# Tech sketch: Atomic receive

**Date:** 2026-08-20  
**Updated:** 2026-08-26 (422 if `analysis_ids` non-empty — refuse, do not ignore; 2026-08-26 chat punch) · 2026-08-27 (CORE creates zero Tests; A-15 parked) · 2026-08-26 (Architecture/UI Accept + 1..N vessels) · 2026-08-24 (AuthZ fold, PR 68)
**Stem:** `atomic-receive`  
**Process:** [`.docs/review/development-process/README.md`](../development-process/README.md)  
**AuthZ docs gate:** **Satisfied** — Heidi/Günter **Accept with conditions** on §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md) (PR 68). Receive = sample create + project RLS; one txn; no parallel path.  
**Architecture:** **Accept** on CORE — [architecture-review/atomic-receive.md](../architecture-review/atomic-receive.md). Accept holds only with refuse-or-ignore (no Test mint). Condition from the **2026-08-26 chat punch**: Wilhelmina pick **refuse** — **422 if `analysis_ids` non-empty**.  
**UI:** **Accept** on CORE — [ui-review/atomic-receive.md](../ui-review/atomic-receive.md). Same **2026-08-26 chat punch** condition: receive never offers analysis and never sends `analysis_ids`; API **422** if non-empty.  
**Product implement:** **Provisional open for AR CORE only** (Leadership 2026-08-26) — identity + **1..N vessels** + field align + docs/UAT. Coding stays Grok Build. Do **not** treat PR 30 “Implement gate OPEN” as license for results-entry / profile engine / work_order / extract-hold / IC50. PR 71 stays draft until UAT + dogfood.  
**Packet design (historical, still stands):** CEO Accept (PR 30 merged). Lab Ops L2–L4 + L1 retracted. Scientific CSO Accept.  
**CORE restamp (2026-08-26):** Architecture **Accept** + UI **Accept** on CORE. Implement follows PRD **1..N**, not “first vessel.” **`analysis_ids` non-empty → 422** (refuse, do not ignore, do not mint). Results persist lock remains **design SoT for a follow-on slice**, not CORE UAT blocker.  
**Multi-container (2026-08-26):** One sample + **1..N containers** in the same txn (primary barcode + optional additional barcodes). True extra vessels, **not** daughter Samples.

C1 (`samples.name` = barcode = `containers.name`) is **gone**. Two identities.

## 1. Problem

Receive must create sample + **one or more** containers + contents in **one DB transaction**, or a mid-rack failure orphans rows. It is common to receive more than one tube for the same sample. Techs scan; they do not pick status, type a sample ID, or define a work plan during CORE receive.

## 2. Goals and non-goals

**Goals (locked — AR CORE)**

- One POST: sample + **1..N containers** + contents for each, one transaction. **Zero Tests. Zero Results.**
- Extra vessels are **1×1 Containers + Contents all pointing at that Sample** — not daughter Samples, not aliquot.
- UX: **primary barcode** required + **optional additional barcodes** on the same commit.
- **Two identities (C1 dropped, Lab Ops L1 retracted):**
  - `containers.name` = scanned barcode. Any collision (request or DB) → **409 + full rollback**.
  - `samples.name` = system-assigned sample ID from the **existing name template/sequence**. Tech does **not** type it.
  - `samples.name` 409 only if that sample ID itself collides.
- Receive screen: **no sample-ID field**. Lookup is scan the tube. Keyboard still works on the barcode field. **No analysis picker.** UI never sends `analysis_ids`.
- Receive body: required primary `container_barcode`, `sample_type`, `matrix`, `project_id`; optional `additional_container_barcodes[]`, `temperature`, `client_sample_id`.
- **`analysis_ids`:** if present and **non-empty → 422**. Refuse, do **not** ignore, do **not** mint Tests, do **not** persist asked-for analyses. Silent drop would hide a client that still thinks Tests were created. Empty or omitted is the only accepted path — still zero Tests.
- Project required and sticky. Never auto-create per tube (L2).
- Container type = default tube, **off the form** (L3) — applies to all vessels on the call.
- One status on commit: **Available for Testing**. No Received hop. Receipt is existing `received_date`. No `status_history` table. Techs do not pick status.
- CORE receive creates **zero Tests**. `_create_asked_for_tests` is a WO-7 fail. A-15 asked-for/work-plan is parked. **Refuse DELETE** if an independently created test has results (A-14 + CSO). Classic Test+Result with no LimsRun still exists — do not kill it in stories. Test row at LimsRun start is WO-7 (later packet).
- AuthZ = sample create + project RLS (PR 68).
- Stay on receive after success: toast, clear barcode field(s), sticky type/matrix/project, focus primary barcode. No sample-detail redirect. No aliquot dialog.
- Mass/conc stay off Sample.

**Follow-on design SoT (not CORE ship)**

- **Results persist (Architecture same-phase lock for the results slice):** typed number lands in `results.reported_result` and `results.qualifiers`. `raw_result` **may copy the same value**. Unit from `analytes.units_default`; if missing, **422**. Do **not** add `results.unit_id`. No unit picker. **Not** a CORE UAT or ship blocker.

**Non-goals (CORE / this packet)**

- No new tables. No new columns. No wizard.
- No aliquot UI. Aliquot **later** (new dest vessel after process) remains separate from **multi-tube receive at intake**. Derivative **later** = new sample with `parent_sample_id`.
- No `work_order` / routing / extract-hold / intake-profile engine / second receive API.
- No ELN, parsers, IC50, dose-response, method/QC/review ceremony, US-28 batch, manifests, materials, multi-tenant.
- Mass/conc stay off Sample.

## 2b. CORE bounce (implement PR fails this packet)

Normative with Leadership 2026-08-26 / CEO C5–C8. Architecture and UI **Accept** on CORE **only** if these stay out:

1. Orphan multi-call (create sample → create container → link) as the supported receive story
2. Single-vessel-only (A-18 / RQ-AR-3 ignored — “first vessel” is folded)
3. Sample-ID field / user-typed sample name / C1
4. Received hop or status picker
5. Project auto-create / optional project
6. Container type / tube picker on the scan loop
7. Analysis as “what’s next” / work plan
8. Test mint at receive / `_create_asked_for_tests` / `analysis_ids` as work plan / **ignore or silent-drop of `analysis_ids`** (must **422** if non-empty)
9. `work_order` / routing / Process·Exp·LimsRun / extract-hold / aliquot in the AR PR
10. Intake-profile engine or second receive API/permission
11. Results-entry treated as CORE ship blocker
12. New tables / `results.unit_id` / `status_history` / mass-conc on Sample
13. AuthZ regression vs PR 68
14. Partial commit on barcode collision
15. Wizard kept as the forever receive path
16. IC50 / dose-response / parsers / ELN

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
    analysis_ids: list[UUID] = []   # if non-empty → 422; do not ignore; do not mint
    temperature: float | None = None
    client_sample_id: str | None = None
    # no status, no sample name, no container_type_id, no client_id
```

Validate **before** the txn: if `analysis_ids` is present and non-empty → **422**. Do not ignore. Do not call `_create_asked_for_tests`. Do not persist asked-for analyses.

In one transaction: assign `samples.name` from the existing name template; set status Available for Testing and `received_date`; for **primary + each additional** barcode insert container (`name = barcode`, 409 on any duplicate) + contents → same sample. Do not insert Tests or Results. Extra barcodes are extra vessels of **that** Sample, not new Samples.

### POST /api/samples/{id}/tests  and  DELETE /api/samples/{id}/tests/{test_id}

No wizard. DELETE → 400 if any `results` exist for that test. Light-ride (A-14) — not a reason to pull results-entry into CORE.

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

**AuthZ docs gate:** **Satisfied** (this section + [security-review/atomic-receive.md](../security-review/atomic-receive.md), PR 68). Heidi/Günter **Accept with conditions**. **Product code:** provisional open for **AR CORE** (identity + 1..N vessels); AuthZ conditions land with that implement.

| Lock | Detail |
|------|--------|
| **Permission** | `POST /api/samples/receive` uses the **same AuthZ as sample create** + **project RLS** (`has_project_access` / `lims_app`). |
| **No parallel path** | No separate receive permission, no client-only bypass, no second AuthZ spine. |
| **One API** | One receive endpoint. Bounce a parallel orphan multi-call (create sample → create container → link) and bounce a second receive API. |
| **One txn** | Sample + **1..N Containers** + Contents each in a **single DB transaction**. CORE creates zero Tests. Clients that drop mid-sequence are refused by design — there is no safe multi-call substitute. |
| **Containers at receive** | All intake vessels for this sample share that same txn (not follow-up calls). Primary + optional additional barcodes. True extra vessels, not daughter Samples. |
| **`analysis_ids`** | Non-empty → **422** (2026-08-26 chat punch; Wilhelmina pick: refuse). Do not ignore. Do not mint. |

Implementers: enforce AuthZ/RLS **inside** the receive service before/with the txn; do not rely on the UI to gate project access.

Formal CSO stamp: [`.docs/review/security-review/atomic-receive.md`](../security-review/atomic-receive.md).

## 5. Receive loop (UI)

1. Scan (or type) **primary** barcode. **No sample-ID field.** Optionally add more barcodes for the same sample.
2. Sticky sample type, matrix, project. Temperature optional. **No analyses picker.** Never send `analysis_ids`.
3. Submit. If the body has non-empty `analysis_ids` → **422** (API; UI does not send them).
4. Stay on the screen. Toast. Clear barcode field(s). Keep sticky fields. Focus primary barcode.
5. Next sample (or next primary tube).

Do not redirect to sample detail. Do not open an aliquot dialog. Duplicate barcode → 409 toast, stay on screen (no partial commit). Formal UI stamp: [ui-review/atomic-receive.md](../ui-review/atomic-receive.md).

## 6. Locked vs parked later

| Locked now (CORE) | Later, not CORE |
|-------------------|-----------------|
| One sample + **1..N containers** + contents, zero Tests, one txn | Asked-for/work-plan (A-15); Test at LimsRun start (WO-7) |
| Non-empty `analysis_ids` → **422** | Aliquot **after** process (new dest vessel) |
| System sample ID + container barcode | Derivative: new sample + `parent_sample_id` |
| Scan lookup, no sample-ID field, no analysis picker | Aliquot UI |
| AuthZ = sample create + project RLS | `work_order` / extract-hold / intake-profile engine |
| | Typed number → `reported_result` + `qualifiers` (`raw_result` may copy) — results slice |
| | Review/release ceremony |

## 7. Reviews

| Review | Verdict |
|--------|--------|
| Lab Ops | L2–L4 hold. **L1 retracted.** Two IDs correct. Receive must not show a sample-ID field. **1..N vessels** (not first-tube). |
| CSO | Accept. DELETE-with-results is data integrity. Classic results only. N/A for CORE assay/QC. |
| Security (Heidi/Günter AuthZ) | **Accept with conditions** (PR 68). AuthZ **docs** gate **satisfied** — sketch §4b + [security-review/atomic-receive.md](../security-review/atomic-receive.md). Receive = sample create + project RLS; one API; one txn; no parallel path. **CORE provisional open** — AuthZ conditions land with CORE code. |
| Architecture | **Accept on CORE** — [architecture-review/atomic-receive.md](../architecture-review/atomic-receive.md). **Accept holds only with refuse-or-ignore (no Test mint).** Recorded from the **2026-08-26 chat punch**. Locked pick: **refuse** — non-empty `analysis_ids` → **422**. 1..N vessels; bounce list in §2b. Persist lock is follow-on SoT, not CORE ship. |
| UI | **Accept on CORE** — [ui-review/atomic-receive.md](../ui-review/atomic-receive.md). Same **2026-08-26 chat punch** condition (refuse-or-ignore, no Test mint). New receive loop. Scan primary + optional extra barcodes. No analysis picker; never send `analysis_ids`. Bounce a sample-ID box, wizard, single-vessel-only UI, or analysis-as-work-plan. |
| CEO | **Accept with conditions** (HOLD SCOPE). One sample + **1..N vessels**. No aliquot UI, no ELN, no IC50. Heidi bounces tables, a sample-ID field, a Received hop, or `results.unit_id`. **CORE shipped + UAT Pass 2026-08-27** (`ebac94e` / stamp `618fbbf`); PR 71 closed (landed via main merge). Results-entry remains follow-on (**NR-AR-1**). |
