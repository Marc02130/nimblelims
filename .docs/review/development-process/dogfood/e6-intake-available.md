# Dogfood: E-6 intake Available for Testing

**Stem:** `e6-intake-available`  
**Branch:** `feat/e6-intake-available-for-testing`  
**SHA:** `a73a51c` (product; update if the tip moved)  
**When:** After this branch is up, **before** Tobias UAT in [`UAT_Scripts/uat-e6-intake-available.md`](../../../../UAT_Scripts/uat-e6-intake-available.md).  
**Not a UAT Result.** Do not invent Pass. Do **not** restamp AR-ST-01. Not E-7. Not dest-follow. Not IC50.

CORE receive already writes Available for Testing (AR-ST-01). This packet is leftover **accession** and **bulk-accession**. `/accessioning` redirects to `/receive`. There is no bulk-accession UI.

Maps to UAT **2.1–2.2**, **3.1**, **4.1–4.2**.

## Env

Local compose on **this feature branch**. Frontend `http://localhost:3000`. API `http://localhost:8000`.

| Role | Login | Use for |
|------|--------|---------|
| Admin | `admin` / `admin123` | Receive, accession API, sample edit, process assign, start |
| Lab tech | `lab-tech` / `labtech123` | Start dialog (`experiment:manage`) |

Need a project, Blood sample type, matrix, and 1×1 container type. Sample status list includes **Received** and **Available for Testing**.

Do not prune the DB volume unless you want a wipe.

## Pages

| Path | What to look at |
|------|-----------------|
| `/receive` | CORE intake. Status is not a field. After submit, sample is Available for Testing. |
| `/accessioning` | Redirects to `/receive`. No wizard. |
| `/samples` / `/samples/:id` | Status chip. Manager can set Received for path 4. |
| `/experiments` | Ad hoc Start with an accessioned sample (2.2). |
| `/experiments/processes` | Assign + Start dialog ineligible when status is Received (4.2). |

## Paths

1. **Receive smoke (1.1).** `/receive` one Blood. Sample status **Available for Testing**. No Received hop.
2. **Accession API (2.1).** `POST /samples/accession` → **200**, `status` = Available for Testing, not Received.
3. **Start after accession (2.2).** Ad hoc experiment, no process. Start with that sample → eligible, cohort locks.
4. **Bulk API (3.1).** `POST /samples/bulk-accession` two samples → both Available for Testing.
5. **Assign does not promote (4.1–4.2).** Edit a sample to **Received**. Assign to a process. Status stays Received. Start dialog: ineligible (status). Do not expect assign to flip it.

### API (same SHA; supporting)

Login then (dates in the past if the validator refuses “now”):

```http
POST /samples/accession
{
  "name": "E6-ACC-1",
  "received_date": "2026-01-01T00:00:00",
  "due_date": "2026-01-15T00:00:00",
  "sample_type": "<uuid>",
  "matrix": "<uuid>",
  "client_id": "<uuid>",
  "project_id": "<uuid>",
  "assigned_tests": []
}
→ 200  status = Available for Testing (not Received)

POST /samples/bulk-accession
{
  "received_date": "2026-01-01T00:00:00",
  "due_date": "2026-01-15T00:00:00",
  "sample_type": "<uuid>",
  "matrix": "<uuid>",
  "client_id": "<uuid>",
  "project_id": "<uuid>",
  "container_type_id": "<uuid>",
  "uniques": [
    {"name": "E6-B-1", "container_name": "E6-C-1"},
    {"name": "E6-B-2", "container_name": "E6-C-2"}
  ]
}
→ 200  both rows Available for Testing
```

pytest `tests/test_e6_intake_status.py` (2 passed on `a73a51c`) is **supporting only** — not the dogfood stamp.

## Fail bars

- Accession or bulk still writes Received.
- Assign-to-process silently sets Available for Testing.
- `/receive` writes Received (CORE regression).
- `/accessioning` no longer redirects to `/receive`.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| | | Fill after the walk |

## Ready for UAT?

Fill after a walk. Do **not** invent Ready=Yes.

**Date:**  
**Who:**  
**SHA:** `a73a51c` (update if the tip moved)  
**Env:** local compose on `feat/e6-intake-available-for-testing`  
**Ready for UAT?** Unsigned until Tobias.

Ready=Yes is dogfood, not a substitute for formal Pass. Do **not** restamp AR-ST-01.
