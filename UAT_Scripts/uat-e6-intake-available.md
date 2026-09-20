# UAT: E-6 intake Available for Testing

**Stem:** `e6-intake-available`  
**Branch:** `feat/e6-intake-available-for-testing`  
**SHA:** product `a73a51c` · tip `7bd4f84` (docs tip; product under it)  
**Scope:** Leftover **accession** and **bulk-accession** write **Available for Testing**, matching CORE receive. Decision #24 start gate can then see a freshly accessioned sample.

**Pass** (Tobias QA) · **Rolf Confirm** · **E-6 Met**. Do **not** restamp atomic-receive **AR-ST-01**. Process assign still does **not** change Sample.status (Decision #24). Not E-7. Not dest-follow. Not IC50. Marc owns merge.

Wizard `/accessioning` is retired (redirects to `/receive`). There is **no** bulk-accession UI. Steps 2–3 are **API**. Step 1 is a receive smoke only.

## Prerequisites

1. Local compose on **this feature branch**. Frontend `http://localhost:3000`. API `http://localhost:8000`.
2. Log in as Admin (`admin` / `admin123`) with `sample:create` and `experiment:manage`.
3. Sample status list includes **Received** and **Available for Testing**.
4. At least one Blood sample type, matrix, project, and 1×1 container type.

## 1. CORE receive (smoke only — AR-ST-01 already Pass)

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 1.1 | `/receive` one Blood sample. Open `/samples` (or GET the sample). | Status **Available for Testing**. No Received hop. Zero Tests. | Unsigned this packet (AR-ST-01 already Pass on `uat-atomic-receive`) |

## 2. Legacy accession (API)

`/accessioning` redirects to `/receive`. Do not score a wizard.

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 2.1 | `POST /samples/accession` for a Blood sample (project, type, matrix, dates). | **200**. `status` is Available for Testing, **not** Received. Sample exists. | **Pass** |
| 2.2 | `/experiments` → ad hoc (no process) → Start with that sample. | Sample is eligible. Start succeeds. Cohort locks. | **Pass** |

## 3. Bulk accession (API)

Bulk UI cases in `uat-bulk-enhancements.md` are retired. Score the API only.

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 3.1 | `POST /samples/bulk-accession` two samples (shared type/matrix/project + unique names/containers). | **200**. Both rows **Available for Testing**, not Received. | **Pass** |

## 4. Process assign does not promote

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 4.1 | On `/samples/:id`, set status to **Received**. Assign that sample to a process. Reload the sample. | Sample.status stays **Received**. | **Pass** |
| 4.2 | Process accordion → Start the experiment step. | Dual-list: that sample is **ineligible** (status). Assign did not flip it to Available for Testing. | **Pass** |

**Fail:** accession or bulk still writes Received; assign-to-process silently flips status; CORE receive regresses off AFT; `/accessioning` no longer redirects to `/receive`.

## Pass criteria

- Formal packet: steps **2.1–2.2**, **3.1**, **4.1–4.2**. **Pass** (Tobias QA, 2026-09-20 14:33:58 ET, product `a73a51c`, tip `7bd4f84`); **Rolf Confirm**; **E-6 Met**.
- Step **1.1** is smoke only. CORE receive AR-ST-01 stays the [`uat-atomic-receive.md`](uat-atomic-receive.md) stamp. Do not restamp it here.
- Decision #24: process assign does **not** change Sample.status.

## Stamp log

### 2026-09-20 · product `a73a51c` · tip `7bd4f84` · `feat/e6-intake-available-for-testing`

**Result: Pass** (Tobias QA) · 2026-09-20 14:33:58 ET · product `a73a51c` · tip `7bd4f84` · **Dogfood Ready=Yes** · **Rolf Confirm** · **E-6 Met**. Scored **2.1–2.2**, **3.1**, **4.1–4.2**. Step **1.1** smoke only — do **not** restamp AR-ST-01. Decision #24: assign does not promote. Evidence (cite only): `/workspace/uat-e6-7bd4f84/{RESULT.md,tobias-stamp.json,acs.md,dogfood/READY.md}`. Marc owns merge. Critical path E-10/E-12/E-14/E-7/E-6 looks closed after merge. Not IC50.
