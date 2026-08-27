# Manual: Atomic receive (OOB / CORE)

**Status:** CORE implement (Phases 1–4 on `feat/atomic-receive-core`)  
**UI:** `/receive` — sidebar **Receive** (`frontend/src/pages/AtomicReceive.tsx`)  
**API:** `POST /samples/receive` (`backend/app/services/atomic_receive_service.py`)  
**UAT:** [`UAT_Scripts/uat-atomic-receive.md`](../../UAT_Scripts/uat-atomic-receive.md)  
**Requirements:** `.docs/internal/prd/sample-accessioning/PRD.md` (RQ-AR-*) · SPEC §3  
**Sketch:** `.docs/review/tech-sketch/atomic-receive.md`

---

## Purpose

High-volume intake: register specimen identity + **1..N vessels** in **one transaction**. Lab sample ID is system-assigned. Tube barcode is the vessel. Status on commit is **Available for Testing**. Work plan / work orders / results entry are **out of receive**.

Legacy wizard at `/accessioning` is **not** the happy path (see [accessioning-workflow.md](accessioning-workflow.md) for historical wizard docs).

---

## Who

| Role | Access |
|------|--------|
| Lab tech / manager with `sample:create` | Receive UI + API |
| Client | No receive (403 / no nav) |
| Users without project access | Foreign project → 403 |

---

## UI loop (`/receive`)

1. Set sticky **sample type**, **matrix**, **project** (session-sticky).  
2. Scan / type **primary barcode** (required).  
3. Optionally **Add** additional barcodes for the **same sample** (not aliquot).  
4. Optionally omit asked-for analyses (preferred) or select analyses (Assigned/Pending only).  
5. Optional temperature / client sample ID.  
6. **Receive** → toast → barcodes clear → sticky fields remain → focus primary.  
7. Stay on the page for the next specimen.

**Not on the form:** sample ID, status, container type, aliquot dialog, redirect to sample detail.

---

## API contract

```http
POST /samples/receive
```

```json
{
  "container_barcode": "NBIO-AR-0001",
  "additional_container_barcodes": ["NBIO-AR-0001B"],
  "sample_type": "<uuid>",
  "matrix": "<uuid>",
  "project_id": "<uuid>",
  "analysis_ids": [],
  "temperature": null,
  "client_sample_id": null
}
```

**Forbidden body fields (422):** `name`, `status`, `container_type_id`, `due_date`, `qc_type`, `client_id`, …

**Server (one txn):**

1. AuthZ = sample create + project access/RLS  
2. Default tube type off-form for all vessels  
3. System `samples.name` via name template  
4. Sample status → Available for Testing; set `received_date`  
5. For each barcode → Container + Contents → same sample  
6. Optional tests → Assigned/Pending  

**Errors:** duplicate barcode → **409** (full rollback); missing required → **422**; no project access / client → **403**.

**Response (minimum):** `sample_id`, `sample_name`, `status`, `project_id`, `containers[]`, `tests[]`.

---

## Identities

| Identity | Field | Rule |
|----------|--------|------|
| Vessel | `containers.name` | Scanned barcode; unique; 409 on collision |
| Material | `samples.name` | System template; tech does not type it |

---

## Tests at receive

- Prefer **omit** `analysis_ids`.  
- If present = **asked for** only (Assigned/Pending), not In Process, not the work plan.  
- Later: add/remove tests from sample.  
- `DELETE /tests/{id}` → **400** if results exist (A-14).

---

## Related docs

- API index: [api-endpoints.md](api-endpoints.md)  
- Containers: [containers.md](containers.md)  
- Legacy wizard: [accessioning-workflow.md](accessioning-workflow.md)  
- Navigation: [navigation.md](navigation.md)  
